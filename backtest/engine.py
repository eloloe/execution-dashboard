import pandas as pd
from typing import List
from core.order import Order, Fill
from strategies.base import BaseStrategy
from metrics.costs import calculate_market_impact

class BacktestEngine:
    def __init__(self, data: pd.DataFrame):
        """
        data: DataFrame containing columns: timestamp, open, high, low, close, vwap, volume
        """
        self.data = data.sort_values(by='timestamp').reset_index(drop=True)

    def run(self, strategy: BaseStrategy, apply_impact: bool = False, daily_adv: float = None):
        # Filter data to strategy interval to save time
        run_data = self.data[
            (self.data['timestamp'] >= strategy.start_time) & 
            (self.data['timestamp'] <= strategy.end_time)
        ]
        
        for _, row in run_data.iterrows():
            if strategy.is_finished:
                break
                
            # Feed market data to strategy
            child_orders = strategy.on_market_data(row)
            
            # Execute child orders
            for child in child_orders:
                qty = child['quantity']
                # Simplistic execution model: Execute exactly at the bin's VWAP price
                exec_price = row['vwap']
                
                if apply_impact and daily_adv and daily_adv > 0:
                    # Apply temporary market impact
                    impact_fraction = calculate_market_impact(qty, daily_adv)
                    if strategy.parent_order.side == "BUY":
                        exec_price *= (1 + impact_fraction)
                    else:
                        exec_price *= (1 - impact_fraction)

                
                # Check for capacity constraints: We cannot execute more than market volume.
                # In reality we'd have a participation rate limit. Here, for simplicity, we just cap
                # at total market volume.
                if qty > row['volume']:
                    # Partial fill or slippage penalty could be applied.
                    qty = row['volume'] 
                
                fill = Fill(
                    timestamp=row['timestamp'],
                    quantity=qty,
                    price=exec_price
                )
                strategy.parent_order.add_fill(fill)
        
        return strategy.parent_order
