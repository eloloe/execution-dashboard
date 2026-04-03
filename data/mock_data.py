import pandas as pd
import numpy as np

def generate_intraday_data(symbol="AAPL", start_price=150.0, num_bins=390, volatility=0.001):
    """
    Generate mock intraday price and volume data.
    Assumes 390 one-minute bins (e.g. 9:30 AM to 4:00 PM).
    """
    np.random.seed(42) # For reproducibility
    
    # Generate prices using geometric brownian motion
    returns = np.random.normal(loc=0, scale=volatility, size=num_bins)
    price_paths = start_price * np.exp(np.cumsum(returns))
    
    # Typical U-shape volume profile (high at start/end, lower in middle)
    x = np.linspace(-1, 1, num_bins)
    base_volume = 1000 * (1.5 + x**2)
    noise_volume = np.random.lognormal(mean=0, sigma=0.2, size=num_bins)
    volumes = (base_volume * noise_volume).astype(int)
    
    # High, Low, Open, Close approximations
    opens = price_paths - np.random.choice([0, 1], size=num_bins) * np.random.uniform(0, 0.1, size=num_bins)
    closes = price_paths
    highs = np.maximum(opens, closes) + np.random.uniform(0, 0.1, size=num_bins)
    lows = np.minimum(opens, closes) - np.random.uniform(0, 0.1, size=num_bins)
    
    # Typical VWAP approximation per bin
    bin_vwaps = (highs + lows + closes) / 3

    # Generate timestamps
    timestamps = pd.date_range(start="2023-10-25 09:30:00", periods=num_bins, freq="min")
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": symbol,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "vwap": bin_vwaps,
        "volume": volumes
    })
    
    return df
