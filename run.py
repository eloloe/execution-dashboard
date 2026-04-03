import os
import sys
# Add current working directory to path to allow absolute imports starting with 'execution'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from execution.data.mock_data import generate_intraday_data
from execution.core.order import Order
from execution.strategies.twap import TWAPStrategy
from execution.strategies.vwap import VWAPStrategy
from execution.backtest.engine import BacktestEngine
from execution.metrics.costs import calculate_implementation_shortfall, calculate_interval_vwap_slippage

def main():
    print("Generating mock intraday data...")
    df = generate_intraday_data(symbol="AAPL", start_price=150.0, num_bins=390, volatility=0.001)
    
    # We will simulate a trade over the first 2 hours (120 minutes)
    start_time = pd.to_datetime("2023-10-25 09:30:00")
    end_time = pd.to_datetime("2023-10-25 11:30:00")
    total_quantity = 100000
    
    # Arrival price is the open price of the start bin
    start_row = df[df['timestamp'] == start_time].iloc[0]
    arrival_price = start_row['open']
    
    # Initialize Engine
    engine = BacktestEngine(df)
    
    print("\n--- Running TWAP Strategy ---")
    twap_order = Order(
        symbol="AAPL", 
        quantity=total_quantity, 
        side="BUY", 
        order_id="TWAP_1",
        arrival_price=arrival_price,
        arrival_timestamp=start_time
    )
    twap_strategy = TWAPStrategy(twap_order, start_time, end_time, interval_minutes=5)
    engine.run(twap_strategy)
    
    print(f"TWAP Executed Qty: {twap_order.filled_quantity}")
    print(f"TWAP Avg Price: {twap_order.average_execution_price:.4f}")
    print(f"TWAP IS (bps): {calculate_implementation_shortfall(twap_order):.2f}")
    print(f"TWAP Interval VWAP Slippage (bps): {calculate_interval_vwap_slippage(twap_order, df, start_time, end_time):.2f}")
    
    
    print("\n--- Running VWAP Strategy ---")
    # For VWAP, we need a volume profile. For a simple mock, we just take the actual volume profile 
    # of the data itself (acting as perfect foresight expected volume curve)
    historical_volume_profile = df.set_index('timestamp')['volume']
    
    vwap_order = Order(
        symbol="AAPL", 
        quantity=total_quantity, 
        side="BUY", 
        order_id="VWAP_1",
        arrival_price=arrival_price,
        arrival_timestamp=start_time
    )
    vwap_strategy = VWAPStrategy(vwap_order, start_time, end_time, volume_profile=historical_volume_profile)
    engine.run(vwap_strategy)
    
    print(f"VWAP Executed Qty: {vwap_order.filled_quantity}")
    print(f"VWAP Avg Price: {vwap_order.average_execution_price:.4f}")
    print(f"VWAP IS (bps): {calculate_implementation_shortfall(vwap_order):.2f}")
    print(f"VWAP Interval VWAP Slippage (bps): {calculate_interval_vwap_slippage(vwap_order, df, start_time, end_time):.2f}")

if __name__ == "__main__":
    main()
