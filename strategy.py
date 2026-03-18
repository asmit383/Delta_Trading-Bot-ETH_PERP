import pandas as pd
import numpy as np
from config import Config

def compute_signals(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    Compute entry signals based on strategy logic.
    Returns the dataframe with a 'signal' column:
     1 for LONG
    -1 for SHORT
     0 for NO SIGNAL
    """
    df = df.copy()
    
    df['signal'] = 0
    
    # Calculate candle characteristics
    df['body_pct'] = (df['close'] - df['open']) / df['open']
    df['body_abs_pct'] = df['body_pct'].abs()
    
    # Valid setup if the single candle's body size percentage exceeds the required threshold
    valid_setup = df['body_abs_pct'] >= cfg.REVERSAL_CANDLE_PCT
    
    # Generate signals: Reverse trade logic
    # If the large candle is positive (Green) -> Take SHORT (-1)
    # If the large candle is negative (Red) -> Take LONG (1)
    df.loc[valid_setup & (df['body_pct'] > 0), 'signal'] = -1
    df.loc[valid_setup & (df['body_pct'] < 0), 'signal'] = 1
    
    return df
