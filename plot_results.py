import os
import sys
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.data.mock_data import generate_intraday_data
from execution.simulate_random_orders import generate_random_orders
from execution.core.order import Order
from execution.strategies.twap import TWAPStrategy
from execution.strategies.vwap import VWAPStrategy
from execution.backtest.engine import BacktestEngine
from execution.metrics.costs import calculate_implementation_shortfall, calculate_interval_vwap_slippage

def run_simulation_and_plot(num_orders=100):
    print("Generating simulated trade sequence...")
    df = generate_intraday_data(symbol="AAPL", start_price=150.0, num_bins=390, volatility=0.002)
    start_time = pd.to_datetime("2023-10-25 09:30:00")
    end_time = pd.to_datetime("2023-10-25 11:30:00") # 2 hour execution window
    
    arrival_price = df[df['timestamp'] == start_time].iloc[0]['open']
    daily_adv = df['volume'].sum() * 5.0
    
    random_orders = generate_random_orders(num_orders, df, start_time, arrival_price)
    engine = BacktestEngine(df)
    historical_volume_profile = df.set_index('timestamp')['volume']
    
    results = []
    
    twap_cumulative_pnl = 0
    vwap_cumulative_pnl = 0
    
    for config in random_orders:
        twap_order = Order(symbol="AAPL", quantity=config["quantity"], side=config["side"], 
                           order_id="T_" + config["order_id"], arrival_price=config["arrival_price"], 
                           arrival_timestamp=start_time)
        twap_strategy = TWAPStrategy(twap_order, start_time, end_time, interval_minutes=5)
        engine.run(twap_strategy, apply_impact=True, daily_adv=daily_adv)
        
        vwap_order = Order(symbol="AAPL", quantity=config["quantity"], side=config["side"], 
                           order_id="V_" + config["order_id"], arrival_price=config["arrival_price"], 
                           arrival_timestamp=start_time)
        vwap_strategy = VWAPStrategy(vwap_order, start_time, end_time, volume_profile=historical_volume_profile)
        engine.run(vwap_strategy, apply_impact=True, daily_adv=daily_adv)
        
        t_is = calculate_implementation_shortfall(twap_order)
        v_is = calculate_implementation_shortfall(vwap_order)
        
        # PnL logic: positive means we saved money over arrival price, negative means it cost us.
        # Shortfall is calculated directly as positive = profit (worse price for buy = neg IS... wait).
        # Our IS is (exec_price - arrival_price)/arrival_price * 10000 for BUY.
        # If exec > arrival, slip is positive, meaning cost is positive. 
        # So PnL (dollars) is - (slip / 10000) * arrival_value
        arrival_val = config["quantity"] * config["arrival_price"]
        t_pnl = -(t_is / 10000) * arrival_val
        v_pnl = -(v_is / 10000) * arrival_val
        
        twap_cumulative_pnl += t_pnl
        vwap_cumulative_pnl += v_pnl
        
        results.append({
            "order_id": config["order_id"],
            "size": config["quantity"],
            "twap_is": t_is,
            "vwap_is": v_is,
            "twap_cum_pnl": twap_cumulative_pnl,
            "vwap_cum_pnl": vwap_cumulative_pnl
        })
        
    df_res = pd.DataFrame(results)
    
    # ---------------- PLOTTING ----------------
    sns.set_theme(style="whitegrid", palette="muted")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 1. Distribution of Slippage
    sns.kdeplot(df_res['twap_is'], fill=True, label="TWAP", ax=axes[0], color="coral", alpha=0.5)
    sns.kdeplot(df_res['vwap_is'], fill=True, label="VWAP", ax=axes[0], color="steelblue", alpha=0.5)
    axes[0].set_title("1. Implementation Shortfall Distribution", fontsize=14)
    axes[0].set_xlabel("Implementation Shortfall (bps)")
    axes[0].legend()
    
    # 2. Execution Cost vs Order Size
    sns.scatterplot(x='size', y='twap_is', data=df_res, label="TWAP", ax=axes[1], color="coral", alpha=0.7)
    sns.lineplot(x='size', y='twap_is', data=df_res, ax=axes[1], color="coral", alpha=0.3)
    sns.scatterplot(x='size', y='vwap_is', data=df_res, label="VWAP", ax=axes[1], color="steelblue", alpha=0.7)
    sns.lineplot(x='size', y='vwap_is', data=df_res, ax=axes[1], color="steelblue", alpha=0.3)
    
    # Optional: Plot trendlines
    sns.regplot(x='size', y='twap_is', data=df_res, scatter=False, ax=axes[1], line_kws={"color":"red", "linestyle":"--"})
    sns.regplot(x='size', y='vwap_is', data=df_res, scatter=False, ax=axes[1], line_kws={"color":"blue", "linestyle":"--"})
    
    axes[1].set_title("2. Market Impact: Cost vs Order Size", fontsize=14)
    axes[1].set_xlabel("Order Quantity")
    axes[1].set_ylabel("Execution Cost (bps)")
    
    # 3. Cumulative PnL
    axes[2].plot(df_res.index, df_res['twap_cum_pnl'], label='TWAP PnL', color="coral", linewidth=2)
    axes[2].plot(df_res.index, df_res['vwap_cum_pnl'], label='VWAP PnL', color="steelblue", linewidth=2)
    axes[2].set_title("3. Cumulative Execution Cost / PnL", fontsize=14)
    axes[2].set_xlabel("Order Sequence (Time)")
    axes[2].set_ylabel("Cumulative PnL ($ relative to benchmark)")
    axes[2].legend()

    plt.tight_layout()
    plot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "execution_analysis.png")
    plt.savefig(plot_path, dpi=300, facecolor='w', edgecolor='w', bbox_inches='tight')
    print(f"Plot saved successfully to {plot_path}")

if __name__ == "__main__":
    run_simulation_and_plot(50)
