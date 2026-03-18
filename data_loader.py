import pandas as pd
import numpy as np

def load_data(file_path):
    """
    Load OHLCV data from a CSV file.
    Expected columns: timestamp, open, high, low, close, volume (optional)
    """
    df = pd.read_csv(file_path)
    # Ensure timestamp is datetime and sorted
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
    return df

def generate_dummy_data():
    """Generate some dummy data if CSV is not present for quick testing."""
    dates = pd.date_range("2023-01-01", periods=10000, freq="1min")
    close = 2000.0 + np.random.randn(10000).cumsum() * 2
    open_p = np.roll(close, 1)
    open_p[0] = 2000.0
    high = np.maximum(open_p, close) + np.random.rand(10000) * 2
    low = np.minimum(open_p, close) - np.random.rand(10000) * 2
    return pd.DataFrame({
        'timestamp': dates,
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.rand(10000) * 10
    })
