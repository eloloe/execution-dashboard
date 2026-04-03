import pandas as pd
from execution.core.order import Order

def calculate_implementation_shortfall(order: Order) -> float:
    """
    Returns the implementation shortfall in basis points.
    IS = (Execution Price - Arrival Price) / Arrival Price * 10000 
    For a BUY order. For a SELL, the sign is flipped.
    """
    if order.filled_quantity == 0 or order.arrival_price == 0:
        return 0.0
        
    avg_price = order.average_execution_price
    
    if order.side == "BUY":
        slip = (avg_price - order.arrival_price) / order.arrival_price
    else:
        slip = (order.arrival_price - avg_price) / order.arrival_price
        
    return slip * 10000

def calculate_interval_vwap_slippage(order: Order, data: pd.DataFrame, start_time: pd.Timestamp, end_time: pd.Timestamp) -> float:
    """
    Calculates the slippage against the market VWAP for the same interval.
    Returns slippage in basis points.
    """
    interval_data = data[(data['timestamp'] >= start_time) & (data['timestamp'] <= end_time)]
    
    if interval_data.empty:
        return 0.0
        
    total_dollar_volume = (interval_data['vwap'] * interval_data['volume']).sum()
    total_volume = interval_data['volume'].sum()
    
    market_vwap = total_dollar_volume / total_volume
    avg_price = order.average_execution_price
    
    if order.side == "BUY":
        slip = (avg_price - market_vwap) / market_vwap
    else:
        slip = (market_vwap - avg_price) / market_vwap
        
    return slip * 10000

def calculate_market_impact(child_qty: float, daily_adv: float, volatility: float = 0.01, alpha: float = 0.5, beta: float = 0.6) -> float:
    """
    Returns the estimated temporary market impact in basis points.
    Formula: impact = alpha * (size / ADV)^beta * volatility
    
    Returns the impact as a fraction (e.g. 0.0010 = 10 bps).
    """
    if daily_adv <= 0 or child_qty <= 0:
        return 0.0
        
    size_adv_ratio = child_qty / daily_adv
    
    impact = alpha * (size_adv_ratio ** beta) * volatility
    
    return impact
