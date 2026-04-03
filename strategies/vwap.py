import pandas as pd
from typing import List
from execution.strategies.base import BaseStrategy
from execution.core.order import Order

class VWAPStrategy(BaseStrategy):
    def __init__(self, parent_order: Order, start_time: pd.Timestamp, end_time: pd.Timestamp, volume_profile: pd.Series):
        """
        volume_profile: A pandas Series where index ranges by time (or time-of-day) 
                        and values are the expected historical volumes.
        """
        super().__init__(parent_order, start_time, end_time)
        
        # Filter volume profile to the strategy's time window bounds
        self.volume_profile = volume_profile.loc[
            (volume_profile.index >= start_time) & 
            (volume_profile.index <= end_time)
        ]
        
        if self.volume_profile.empty or self.volume_profile.sum() == 0:
            raise ValueError("Invalid or empty volume profile provided.")
            
        # Calculate expected total volume
        self.total_expected_volume = self.volume_profile.sum()
        self.executed_qty = 0.0
        self.intervals_executed = 0

    def on_market_data(self, row: pd.Series) -> List[dict]:
        self.current_time = row['timestamp']
        
        if self.is_finished:
            return []

        if not (self.start_time <= self.current_time <= self.end_time):
            return []
            
        if self.current_time in self.volume_profile.index:
            # Look up expected volume fraction for this specific bin
            bin_expected_volume = self.volume_profile.loc[self.current_time]
            fraction = bin_expected_volume / self.total_expected_volume
            
            target_qty = self.parent_order.quantity * fraction
            
            # Check if it's the last bin in our profile
            # We can use index.get_loc to see if it's the final element
            is_last = self.current_time == self.volume_profile.index[-1]
            
            if is_last:
                qty = self.parent_order.remaining_quantity
            else:
                qty = target_qty
                
            self.executed_qty += qty
            return [{'quantity': qty, 'type': 'MARKET'}]

        return []
