from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
from core.order import Order

class BaseStrategy(ABC):
    def __init__(self, parent_order: Order, start_time: pd.Timestamp, end_time: pd.Timestamp):
        self.parent_order = parent_order
        self.start_time = start_time
        self.end_time = end_time
        
        # Keep track of the current market state
        self.current_time: Optional[pd.Timestamp] = None

    @abstractmethod
    def on_market_data(self, row: pd.Series) -> List[dict]:
        """
        Called when new market data arrives.
        Should return a list of child order requests to be executed.
        Returns:
            List of dicts representing child orders, e.g.:
            [{'quantity': 100, 'type': 'MARKET'}]
        """
        pass
    
    @property
    def is_finished(self) -> bool:
        """Returns True if the strategy is done executing the parent order."""
        return self.parent_order.is_filled or (self.current_time is not None and self.current_time >= self.end_time)
