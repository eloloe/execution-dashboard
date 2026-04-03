import os
import sys
import random
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.data.mock_data import generate_intraday_data
from execution.core.order import Order
from execution.strategies.twap import TWAPStrategy
from execution.strategies.vwap import VWAPStrategy
from execution.backtest.engine import BacktestEngine
from execution.metrics.costs import calculate_implementation_shortfall, calculate_interval_vwap_slippage

def generate_random_orders(num_orders, df, start_time, base_price):
    """Randomly generate orders with varying sizes and directions."""
    random.seed(101) # constant seed for reproducibility
    np.random.seed(101)
    
    orders = []
    for i in range(num_orders):
        size = int(np.random.lognormal(mean=9, sigma=1)) # Ranging sizes
        direction = random.choice(["BUY", "SELL"])
        
        orders.append({
            "order_id": f"ORD_{i+1}",
            "quantity": size,
            "side": direction,
            "arrival_price": base_price,
            "arrival_timestamp": start_time
        })
    return orders
    
def run_simulation(num_orders=5):
    print("Initializing environment and mock intraday data...")
    df = generate_intraday_data(symbol="AAPL", start_price=150.0, num_bins=390, volatility=0.002)
    
    start_time = pd.to_datetime("2023-10-25 09:30:00")
    end_time = pd.to_datetime("2023-10-25 10:30:00") # 1 hour execution window
    
    arrival_price = df[df['timestamp'] == start_time].iloc[0]['open']
    daily_adv = df['volume'].sum() * 5.0
    
    random_order_configs = generate_random_orders(num_orders, df, start_time, arrival_price)
    
    engine = BacktestEngine(df)
    historical_volume_profile = df.set_index('timestamp')['volume']
    
    twap_metrics = []
    vwap_metrics = []
    
    print(f"\nRunning {num_orders} random execution simulations...\n")
    print(f"{'ID':<10} | {'Side':<5} | {'Size':<10} | {'TWAP IS (bps)':<15} | {'VWAP IS (bps)':<15} | {'TWAP Slip':<15} | {'VWAP Slip':<15}")
    print("-" * 100)
    
    for config in random_order_configs:
        # TWAP Order
        twap_order = Order(
            symbol="AAPL", quantity=config["quantity"], side=config["side"], 
            order_id="T_" + config["order_id"], arrival_price=config["arrival_price"], 
            arrival_timestamp=start_time
        )
        twap_strategy = TWAPStrategy(twap_order, start_time, end_time, interval_minutes=5)
        engine.run(twap_strategy, apply_impact=True, daily_adv=daily_adv)
        
        # VWAP Order
        vwap_order = Order(
            symbol="AAPL", quantity=config["quantity"], side=config["side"], 
            order_id="V_" + config["order_id"], arrival_price=config["arrival_price"], 
            arrival_timestamp=start_time
        )
        vwap_strategy = VWAPStrategy(vwap_order, start_time, end_time, volume_profile=historical_volume_profile)
        engine.run(vwap_strategy, apply_impact=True, daily_adv=daily_adv)
        
        # Collect Metrics
        t_is = calculate_implementation_shortfall(twap_order)
        v_is = calculate_implementation_shortfall(vwap_order)
        t_slip = calculate_interval_vwap_slippage(twap_order, df, start_time, end_time)
        v_slip = calculate_interval_vwap_slippage(vwap_order, df, start_time, end_time)
        
        twap_metrics.append({"is": t_is, "slip": t_slip})
        vwap_metrics.append({"is": v_is, "slip": v_slip})
        
        print(f"{config['order_id']:<10} | {config['side']:<5} | {config['quantity']:<10} | {t_is:<15.2f} | {v_is:<15.2f} | {t_slip:<15.2f} | {v_slip:<15.2f}")
    
    print("-" * 100)
    avg_twap_is = sum(m["is"] for m in twap_metrics) / num_orders
    avg_vwap_is = sum(m["is"] for m in vwap_metrics) / num_orders
    
    print(f"\nOVERALL PERFORMANCE (Averages across {num_orders} orders)")
    print(f"TWAP Avg Implementation Shortfall: {avg_twap_is:.2f} bps")
    print(f"VWAP Avg Implementation Shortfall: {avg_vwap_is:.2f} bps")
    
if __name__ == "__main__":
    run_simulation(10)
