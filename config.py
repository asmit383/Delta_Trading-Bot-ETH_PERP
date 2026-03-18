class Config:
    # Data Params
    SYMBOL = 'ETH/USDT'
    TIMEFRAME = '1m'
    DATA_PATH = 'data.csv'

    # Strategy Params
    # Reverse trade if single candle body >= 0.15%
    REVERSAL_CANDLE_PCT = 0.17 / 100.0

    # Exit Params
    TAKE_PROFIT_PCT    = 0.25 / 100.0
    STOP_LOSS_PCT      = 0.05 / 100.0
    TIME_EXIT_CANDLES  = 3

    # Realistic Market Params
    SLIPPAGE_PCT       = 0.02 / 100.0  # 0.02% slippage on entry
    SL_SLIPPAGE_PCT    = 0.02 / 100.0  # 0.03% slippage on SL fill (stop market)
    LEVERAGE           = 5.0           # 1x for safe testing, up to 5x later

    # Fees (Delta Exchange maker/taker)
    ENTRY_FEE_PCT = 0.02 / 100.0
    EXIT_FEE_PCT  = 0.0  / 100.0

    # Initial Capital
    INITIAL_CAPITAL = 1000.0

    # Live Trading
    ORDER_SIZE = 2  # fixed lot size (contracts) for live orders
