import pandas as pd
from config import Config

def compute_signals(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    Mean-reversion strategy:
      - Candle body >= REVERSAL_CANDLE_PCT → enter opposite direction at close (market order)
      - Bullish candle (close > open) → SHORT signal
      - Bearish candle (close < open) → LONG signal
    Entry is market order at close price + slippage.
    """
    df = df.copy()
    body_pct = (df['close'] - df['open']) / df['open']
    df['signal'] = 0
    df.loc[body_pct >=  cfg.REVERSAL_CANDLE_PCT, 'signal'] = -1  # short on big green
    df.loc[body_pct <= -cfg.REVERSAL_CANDLE_PCT, 'signal'] =  1  # long on big red
    return df
