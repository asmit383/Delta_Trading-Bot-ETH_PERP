import pandas as pd
from config import Config

def run_backtest(df: pd.DataFrame, cfg: Config) -> tuple:
    """
    Mean-reversion backtest.
    Signal candle: body >= REVERSAL_CANDLE_PCT → enter opposite direction at close + slippage.
    Exit: TP (limit) / SL (stop-market + slippage) / TIME (market close).
    """
    trades       = []
    equity       = cfg.INITIAL_CAPITAL
    equity_curve = [(df['timestamp'].iloc[0] if 'timestamp' in df.columns else 0, equity)]

    in_trade    = False
    trade_dir   = 0
    entry_price = 0.0
    entry_time  = None
    entry_idx   = 0
    trade_qty   = 0.0

    def _check_exit(trade_dir, entry_price, c_high, c_low, c_close, bars_held):
        if trade_dir == 1:  # LONG
            sl_price = entry_price * (1.0 - cfg.STOP_LOSS_PCT)
            tp_price = entry_price * (1.0 + cfg.TAKE_PROFIT_PCT)
            if c_low <= sl_price:
                return sl_price * (1.0 - cfg.SL_SLIPPAGE_PCT), "SL"
            elif c_high >= tp_price:
                return tp_price, "TP"
            elif bars_held >= cfg.TIME_EXIT_CANDLES:
                return c_close, "TIME"
        else:  # SHORT
            sl_price = entry_price * (1.0 + cfg.STOP_LOSS_PCT)
            tp_price = entry_price * (1.0 - cfg.TAKE_PROFIT_PCT)
            if c_high >= sl_price:
                return sl_price * (1.0 + cfg.SL_SLIPPAGE_PCT), "SL"
            elif c_low <= tp_price:
                return tp_price, "TP"
            elif bars_held >= cfg.TIME_EXIT_CANDLES:
                return c_close, "TIME"
        return 0.0, ""

    def _record_exit(exit_price, exit_reason, timestamp):
        nonlocal equity, in_trade
        if trade_dir == 1:
            gross_pnl_pct = (exit_price - entry_price) / entry_price
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price

        net_pnl_pct = gross_pnl_pct - cfg.ENTRY_FEE_PCT - cfg.EXIT_FEE_PCT
        pnl_abs     = trade_qty * net_pnl_pct * entry_price

        equity += pnl_abs
        equity_curve.append((timestamp, equity))
        trades.append({
            'entry_time':  entry_time,
            'exit_time':   timestamp,
            'direction':   'LONG' if trade_dir == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price':  exit_price,
            'pnl_abs':     pnl_abs,
            'pnl_pct':     net_pnl_pct,
            'reason':      exit_reason,
        })
        in_trade = False

    for i in range(len(df)):
        row       = df.iloc[i]
        timestamp = row['timestamp'] if 'timestamp' in df.columns else i
        c_high    = row['high']
        c_low     = row['low']
        c_close   = row['close']

        # ── Check exit on current candle if in trade ──────────────────────────
        if in_trade:
            bars_held  = i - entry_idx
            exit_price, exit_reason = _check_exit(
                trade_dir, entry_price, c_high, c_low, c_close, bars_held
            )
            if exit_reason:
                _record_exit(exit_price, exit_reason, timestamp)

        # ── Check entry signal on current candle ──────────────────────────────
        if not in_trade and row['signal'] != 0:
            trade_dir   = row['signal']
            # Market entry at close + slippage
            if trade_dir == 1:
                entry_price = c_close * (1.0 + cfg.SLIPPAGE_PCT)
            else:
                entry_price = c_close * (1.0 - cfg.SLIPPAGE_PCT)
            entry_time  = timestamp
            entry_idx   = i
            trade_qty   = (equity * cfg.LEVERAGE) / entry_price
            in_trade    = True

    # ── Close any open trade at end of data ───────────────────────────────────
    if in_trade:
        row       = df.iloc[-1]
        timestamp = row['timestamp'] if 'timestamp' in df.columns else len(df) - 1
        _record_exit(row['close'], 'END_OF_DATA', timestamp)

    return trades, equity_curve
