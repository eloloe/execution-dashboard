import pandas as pd
from typing import List
from strategies.base import BaseStrategy
from core.order import Order

class TWAPStrategy(BaseStrategy):
    def __init__(self, parent_order: Order, start_time: pd.Timestamp, end_time: pd.Timestamp, interval_minutes: int = 1):
        super().__init__(parent_order, start_time, end_time)
        self.interval_minutes = interval_minutes
        
        # Calculate schedule
        duration = end_time - start_time
        self.num_intervals = int(duration.total_seconds() / 60 / interval_minutes)
        if self.num_intervals <= 0:
            raise ValueError("Duration is too short for the interval.")
            
        self.interval_quantity = self.parent_order.quantity / self.num_intervals
        self.intervals_executed = 0

    def on_market_data(self, row: pd.Series) -> List[dict]:
        self.current_time = row['timestamp']
        
        if self.is_finished:
            return []

        # We only execute if we are within the start and end times
        if not (self.start_time <= self.current_time <= self.end_time):
            return []
            
        # Expected intervals passed based on time
        time_elapsed = self.current_time - self.start_time
        expected_intervals = int(time_elapsed.total_seconds() / 60 / self.interval_minutes) + 1
        
        # We cap expected_intervals to the maximum number
        expected_intervals = min(expected_intervals, self.num_intervals)
        
        intervals_to_catch_up = expected_intervals - self.intervals_executed
        
        if intervals_to_catch_up > 0:
            # We need to execute parts
            self.intervals_executed += intervals_to_catch_up
            
            # Check if this is the final interval, to avoid float precision issues
            if self.intervals_executed == self.num_intervals:
                qty = self.parent_order.remaining_quantity
            else:
                qty = self.interval_quantity * intervals_to_catch_up
                
            return [{'quantity': qty, 'type': 'MARKET'}]
            
        return []
