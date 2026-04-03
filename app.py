import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mock_data import generate_intraday_data
from core.order import Order
from strategies.twap import TWAPStrategy
from strategies.vwap import VWAPStrategy
from backtest.engine import BacktestEngine
from metrics.costs import calculate_implementation_shortfall, calculate_interval_vwap_slippage
from simulate_random_orders import generate_random_orders

# 針對 Mac 設定 Matplotlib 中文字體顯示
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="演算法執行策略平台", layout="wide")

st.title("📈 演算法執行策略分析平台")
st.markdown("透過動態暫時性市場衝擊模型，比較 TWAP 與 VWAP 演算法的執行效能。")

st.sidebar.header("🕹️ 參數設定")
sim_mode = st.sidebar.radio("模式", ["單一訂單執行", "批量模擬與圖表分析"])

symbol = st.sidebar.text_input("交易標的碼", "AAPL")
volatility = st.sidebar.slider("市場波動率", 0.001, 0.010, 0.002, 0.001)
ADV_factor = st.sidebar.slider("日均交易量(ADV)倍數", 1.0, 20.0, 5.0, 1.0)
apply_impact = st.sidebar.checkbox("套用市場衝擊模型", True)

if sim_mode == "單一訂單執行":
    st.header("單一訂單模擬器")
    
    col1, col2 = st.columns(2)
    with col1:
        order_size = st.number_input("訂單數量 (股)", 1000, 10000000, 100000, step=10000)
    with col2:
        order_side_ui = st.selectbox("買賣方向", ["買入 (BUY)", "賣出 (SELL)"])
        order_side = "BUY" if "BUY" in order_side_ui else "SELL"
        
    twap_interval = st.slider("TWAP 拆單間隔 (分鐘)", 1, 30, 5)
    
    if st.button("▶️ 開始執行"):
        with st.spinner("正在生成日內交易數據與撮合引擎..."):
            df = generate_intraday_data(symbol=symbol, start_price=150.0, num_bins=390, volatility=volatility)
            daily_adv = df['volume'].sum() * ADV_factor
            
            start_time = pd.to_datetime("2023-10-25 09:30:00")
            end_time = pd.to_datetime("2023-10-25 11:30:00")
            arrival_price = df[df['timestamp'] == start_time].iloc[0]['open']
            
            engine = BacktestEngine(df)
            historical_volume_profile = df.set_index('timestamp')['volume']
            
            # TWAP
            twap_order = Order(symbol=symbol, quantity=order_size, side=order_side, order_id="TWAP_1", arrival_price=arrival_price, arrival_timestamp=start_time)
            twap_strategy = TWAPStrategy(twap_order, start_time, end_time, interval_minutes=twap_interval)
            engine.run(twap_strategy, apply_impact=apply_impact, daily_adv=daily_adv)
            
            # VWAP
            vwap_order = Order(symbol=symbol, quantity=order_size, side=order_side, order_id="VWAP_1", arrival_price=arrival_price, arrival_timestamp=start_time)
            vwap_strategy = VWAPStrategy(vwap_order, start_time, end_time, volume_profile=historical_volume_profile)
            engine.run(vwap_strategy, apply_impact=apply_impact, daily_adv=daily_adv)
            
            # Metrics
            t_is = calculate_implementation_shortfall(twap_order)
            v_is = calculate_implementation_shortfall(vwap_order)
            
            st.success("訂單執行完成！")
            
            m1, m2 = st.columns(2)
            m1.metric("TWAP 執行落差 (IS)", f"{t_is:.2f} bps", delta=f"成交數量: {twap_order.filled_quantity:,.0f}", delta_color="off")
            m2.metric("VWAP 執行落差 (IS)", f"{v_is:.2f} bps", delta=f"成交數量: {vwap_order.filled_quantity:,.0f}", delta_color="off")
            
            st.info("💡 提示：負數基點 (bps) 代表成交價優於到達價；正數代表產生了滑價成本。")

else:
    st.header("批量模擬與圖表分析")
    
    num_orders = st.slider("隨機生成的訂單數量", 10, 200, 50, step=10)
    
    if st.button("▶️ 執行批量模擬並繪圖"):
        with st.spinner(f"正在模擬 {num_orders} 筆隨機訂單..."):
            df = generate_intraday_data(symbol=symbol, start_price=150.0, num_bins=390, volatility=volatility)
            start_time = pd.to_datetime("2023-10-25 09:30:00")
            end_time = pd.to_datetime("2023-10-25 11:30:00")
            arrival_price = df[df['timestamp'] == start_time].iloc[0]['open']
            daily_adv = df['volume'].sum() * ADV_factor
            
            random_orders = generate_random_orders(num_orders, df, start_time, arrival_price)
            engine = BacktestEngine(df)
            historical_volume_profile = df.set_index('timestamp')['volume']
            
            results = []
            twap_cumulative_pnl = 0
            vwap_cumulative_pnl = 0
            
            for config in random_orders:
                twap_o = Order(symbol=symbol, quantity=config["quantity"], side=config["side"], order_id="T_"+config["order_id"], arrival_price=config["arrival_price"], arrival_timestamp=start_time)
                engine.run(TWAPStrategy(twap_o, start_time, end_time, interval_minutes=5), apply_impact=apply_impact, daily_adv=daily_adv)
                
                vwap_o = Order(symbol=symbol, quantity=config["quantity"], side=config["side"], order_id="V_"+config["order_id"], arrival_price=config["arrival_price"], arrival_timestamp=start_time)
                engine.run(VWAPStrategy(vwap_o, start_time, end_time, volume_profile=historical_volume_profile), apply_impact=apply_impact, daily_adv=daily_adv)
                
                t_is = calculate_implementation_shortfall(twap_o)
                v_is = calculate_implementation_shortfall(vwap_o)
                
                arrival_val = config["quantity"] * config["arrival_price"]
                t_pnl = -(t_is / 10000) * arrival_val
                v_pnl = -(v_is / 10000) * arrival_val
                
                twap_cumulative_pnl += t_pnl
                vwap_cumulative_pnl += v_pnl
                
                results.append({
                    "size": config["quantity"],
                    "twap_is": t_is,
                    "vwap_is": v_is,
                    "twap_cum_pnl": twap_cumulative_pnl,
                    "vwap_cum_pnl": vwap_cumulative_pnl
                })
                
            df_res = pd.DataFrame(results)
            
            # PLOTS
            sns.set_theme(style="whitegrid", palette="muted")
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            
            sns.kdeplot(df_res['twap_is'], fill=True, label="TWAP", ax=axes[0], color="coral", alpha=0.5)
            sns.kdeplot(df_res['vwap_is'], fill=True, label="VWAP", ax=axes[0], color="steelblue", alpha=0.5)
            axes[0].set_title("執行落差 (IS) 分佈", fontdict={'family': 'Arial Unicode MS'})
            axes[0].set_xlabel("執行落差 (基點)", fontdict={'family': 'Arial Unicode MS'})
            axes[0].legend(prop={'family': 'Arial Unicode MS'})
            
            sns.scatterplot(x='size', y='twap_is', data=df_res, label="TWAP", ax=axes[1], color="coral", alpha=0.7)
            sns.scatterplot(x='size', y='vwap_is', data=df_res, label="VWAP", ax=axes[1], color="steelblue", alpha=0.7)
            axes[1].set_title("市場衝擊：執行成本 vs 訂單大小", fontdict={'family': 'Arial Unicode MS'})
            axes[1].set_xlabel("訂單數量", fontdict={'family': 'Arial Unicode MS'})
            axes[1].set_ylabel("執行成本 (基點)", fontdict={'family': 'Arial Unicode MS'})
            axes[1].legend(prop={'family': 'Arial Unicode MS'})
            
            axes[2].plot(df_res.index, df_res['twap_cum_pnl'], label='TWAP PnL', color="coral")
            axes[2].plot(df_res.index, df_res['vwap_cum_pnl'], label='VWAP PnL', color="steelblue")
            axes[2].set_title("累積執行成本 / 損益 (PnL)", fontdict={'family': 'Arial Unicode MS'})
            axes[2].set_xlabel("訂單時間序列", fontdict={'family': 'Arial Unicode MS'})
            axes[2].set_ylabel("累積損益 (相對於基準價之美元價值)", fontdict={'family': 'Arial Unicode MS'})
            axes[2].legend(prop={'family': 'Arial Unicode MS'})

            plt.tight_layout()
            st.pyplot(fig)
            
            avg_t = df_res['twap_is'].mean()
            avg_v = df_res['vwap_is'].mean()
            st.write(f"**平均 TWAP 執行落差:** {avg_t:.2f} 基點 (bps)  |  **平均 VWAP 執行落差:** {avg_v:.2f} 基點 (bps)")
