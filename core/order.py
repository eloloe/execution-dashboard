from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class Fill:
    timestamp: datetime
    quantity: float
    price: float
    
    @property
    def value(self):
        return self.quantity * self.price

@dataclass
class Order:
    symbol: str
    quantity: float
    side: str # 'BUY' or 'SELL'
    order_id: str
    arrival_price: float = 0.0 # Price when the order was created/received
    arrival_timestamp: datetime = None
    fills: List[Fill] = field(default_factory=list)

    @property
    def filled_quantity(self) -> float:
        return sum(f.quantity for f in self.fills)

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        return self.remaining_quantity <= 0

    @property
    def average_execution_price(self) -> float:
        if self.filled_quantity == 0:
            return 0.0
        total_value = sum(f.value for f in self.fills)
        return total_value / self.filled_quantity
    
    def add_fill(self, fill: Fill):
        self.fills.append(fill)

