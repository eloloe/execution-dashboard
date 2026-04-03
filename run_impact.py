import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from execution.data.mock_data import generate_intraday_data
from execution.core.order import Order
from execution.strategies.twap import TWAPStrategy
from execution.strategies.vwap import VWAPStrategy
from execution.backtest.engine import BacktestEngine
from execution.metrics.costs import calculate_implementation_shortfall

def main():
    print("Generating mock intraday data...")
    df = generate_intraday_data(symbol="AAPL", start_price=150.0, num_bins=390, volatility=0.001)
    
    # Let's say ADV is simply the total volume of the day mock data * 10 
    # to simulate the order being a certain chunk of ADV
    daily_adv = df['volume'].sum() * 5.0  # ADV is ~5x the mock day volume
    
    start_time = pd.to_datetime("2023-10-25 09:30:00")
    end_time = pd.to_datetime("2023-10-25 10:30:00") # 1 hour
    
    # We choose a massive order to force market impact difference
    total_quantity = 500000
    
    start_row = df[df['timestamp'] == start_time].iloc[0]
    arrival_price = start_row['open']
    
    engine = BacktestEngine(df)
    
    print(f"Total Order Size: {total_quantity}, Daily ADV: {daily_adv:.0f}")
    
    # TWAP: tries to punch massive blocks every 10 mins (fewer slices = higher size/ADV = higher impact)
    print("\n--- Running TWAP (10-min slices) with Impact ---")
    twap_order = Order(symbol="AAPL", quantity=total_quantity, side="BUY", order_id="TWAP_1", arrival_price=arrival_price)
    twap_strategy = TWAPStrategy(twap_order, start_time, end_time, interval_minutes=10)
    engine.run(twap_strategy, apply_impact=True, daily_adv=daily_adv)
    
    print(f"TWAP Executed Qty: {twap_order.filled_quantity}")
    print(f"TWAP Avg Price: {twap_order.average_execution_price:.4f}")
    print(f"TWAP IS (bps): {calculate_implementation_shortfall(twap_order):.2f}")
    
    # VWAP: punches very small blocks every minute (smaller slices = lower size/ADV = lower impact)
    print("\n--- Running VWAP (1-min slices) with Impact ---")
    historical_volume_profile = df.set_index('timestamp')['volume']
    vwap_order = Order(symbol="AAPL", quantity=total_quantity, side="BUY", order_id="VWAP_1", arrival_price=arrival_price)
    vwap_strategy = VWAPStrategy(vwap_order, start_time, end_time, volume_profile=historical_volume_profile)
    engine.run(vwap_strategy, apply_impact=True, daily_adv=daily_adv)
    
    print(f"VWAP Executed Qty: {vwap_order.filled_quantity}")
    print(f"VWAP Avg Price: {vwap_order.average_execution_price:.4f}")
    print(f"VWAP IS (bps): {calculate_implementation_shortfall(vwap_order):.2f}")


if __name__ == "__main__":
    main()
