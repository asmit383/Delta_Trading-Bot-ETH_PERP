import pandas as pd
import numpy as np
import itertools
from config import Config

cfg = Config()

# ---- Mean-Reversion Backtest (vectorized) ------------------------------------
#
# Signal: candle body >= reversal_pct → enter opposite direction at close + slippage
# Entry = market order (taker fee), SL = stop-market + slippage, TP = limit
# TIME exit after time_exit candles

def run_backtest_vec(opens, highs, lows, closes,
                     rev_pct, tp_pct, sl_pct, sl_slip_pct, slippage_pct,
                     time_exit, leverage=10.0, initial_capital=1000.0):
    n       = len(opens)
    equity  = initial_capital
    in_trade  = False
    trade_dir = 0
    entry_price = 0.0
    entry_idx   = 0
    trade_qty   = 0.0

    wins = 0; losses = 0
    gross_profit = 0.0; gross_loss = 0.0
    equity_arr = [equity]

    for i in range(n):
        c_open  = opens[i]
        c_high  = highs[i]
        c_low   = lows[i]
        c_close = closes[i]

        # ── Exit check ────────────────────────────────────────────────────────
        if in_trade:
            bars_held   = i - entry_idx
            exit_price  = 0.0
            exit_reason = 0

            if trade_dir == 1:
                sp       = entry_price * (1.0 - sl_pct)
                tp_price = entry_price * (1.0 + tp_pct)
                if c_low <= sp:
                    exit_price = sp * (1.0 - sl_slip_pct); exit_reason = 1
                elif c_high >= tp_price:
                    exit_price = tp_price; exit_reason = 2
                elif bars_held >= time_exit:
                    exit_price = c_close; exit_reason = 3
            else:
                sp       = entry_price * (1.0 + sl_pct)
                tp_price = entry_price * (1.0 - tp_pct)
                if c_high >= sp:
                    exit_price = sp * (1.0 + sl_slip_pct); exit_reason = 1
                elif c_low <= tp_price:
                    exit_price = tp_price; exit_reason = 2
                elif bars_held >= time_exit:
                    exit_price = c_close; exit_reason = 3

            if exit_reason:
                if trade_dir == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price
                pnl_pct -= cfg.ENTRY_FEE_PCT + cfg.EXIT_FEE_PCT
                pnl = trade_qty * pnl_pct * entry_price
                equity += pnl
                if pnl > 0: wins += 1; gross_profit += pnl
                else:        losses += 1; gross_loss += abs(pnl)
                equity_arr.append(equity)
                in_trade = False

        # ── Entry check ───────────────────────────────────────────────────────
        if not in_trade:
            body_pct = (c_close - c_open) / c_open
            if body_pct >=  rev_pct:
                trade_dir = -1  # short on big green candle
            elif body_pct <= -rev_pct:
                trade_dir = 1   # long on big red candle
            else:
                continue

            if trade_dir == 1:
                entry_price = c_close * (1.0 + slippage_pct)
            else:
                entry_price = c_close * (1.0 - slippage_pct)

            entry_idx = i
            trade_qty = (equity * leverage) / entry_price
            in_trade  = True

    total_trades = wins + losses
    if total_trades < 10:
        return None

    win_rate = wins / total_trades * 100
    peak = initial_capital; max_dd = 0.0
    for eq in equity_arr:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd: max_dd = dd

    pf            = gross_profit / gross_loss if gross_loss > 0 else 999.0
    total_pnl_pct = (equity - initial_capital) / initial_capital * 100

    return {
        'win_rate':         win_rate,
        'total_pnl_pct':    total_pnl_pct,
        'profit_factor':    pf,
        'max_drawdown_pct': max_dd * 100,
        'total_trades':     total_trades,
    }


# ---- Load Data ---------------------------------------------------------------
print("Loading data...")
df_raw = pd.read_csv("data.csv")
if 'timestamp' in df_raw.columns:
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    df_raw = df_raw.sort_values('timestamp').reset_index(drop=True)

opens  = df_raw['open'].values.astype(np.float64)
highs  = df_raw['high'].values.astype(np.float64)
lows   = df_raw['low'].values.astype(np.float64)
closes = df_raw['close'].values.astype(np.float64)

# ---- Parameter Grid ----------------------------------------------------------
reversal_pcts = [0.10, 0.15, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50]
tp_pcts       = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
sl_pcts       = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
time_exits    = [2, 3, 5, 7]

total = len(reversal_pcts) * len(tp_pcts) * len(sl_pcts) * len(time_exits)
print(f"Total combinations: {total}")
print("Running grid search...\n")

results = []

for rev, tp, sl, te in itertools.product(reversal_pcts, tp_pcts, sl_pcts, time_exits):
    if tp <= sl:
        continue
    res = run_backtest_vec(
        opens, highs, lows, closes,
        rev_pct      = rev / 100.0,
        tp_pct       = tp  / 100.0,
        sl_pct       = sl  / 100.0,
        sl_slip_pct  = cfg.SL_SLIPPAGE_PCT,
        slippage_pct = cfg.SLIPPAGE_PCT,
        time_exit    = te,
    )
    if res:
        results.append({'reversal_pct': rev, 'tp_pct': tp, 'sl_pct': sl, 'time_exit': te, **res})

df_res = pd.DataFrame(results)
df_res = df_res.sort_values(['profit_factor', 'win_rate'], ascending=[False, False])

pd.set_option('display.float_format', '{:.4f}'.format)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 220)

print("=== TOP 15 CONFIGURATIONS ===")
print(df_res.head(15).to_string(index=False))

best = df_res.iloc[0]
print(f"""
=== BEST CONFIG TO PLUG INTO config.py ===

  REVERSAL_CANDLE_PCT = {best['reversal_pct']:.2f} / 100.0
  TAKE_PROFIT_PCT     = {best['tp_pct']:.2f} / 100.0
  STOP_LOSS_PCT       = {best['sl_pct']:.2f} / 100.0
  TIME_EXIT_CANDLES   = {int(best['time_exit'])}

  Win Rate            : {best['win_rate']:.2f}%
  Profit Factor       : {best['profit_factor']:.4f}
  Total PnL %         : {best['total_pnl_pct']:.4f}%
  Max Drawdown %      : {best['max_drawdown_pct']:.4f}%
  Total Trades        : {int(best['total_trades'])}
""")
