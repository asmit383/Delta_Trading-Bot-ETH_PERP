# MicroScalp Delta

A mean-reversion micro-scalping bot for **ETHUSD Perpetual** on [Delta Exchange India](https://india.delta.exchange), with a full backtesting pipeline.

---

## Strategy

Fades large single-candle moves on the 1-minute timeframe:

- **Big green candle** (body ≥ threshold) → **SHORT**
- **Big red candle** (body ≥ threshold) → **LONG**

Exits via bracket order:
| Exit | Condition |
|------|-----------|
| TP | Limit order at +0.25% |
| SL | Stop-market at -0.05% (+ 0.03% slippage modeled) |
| TIME | Market close after 3 candles regardless of P&L |

---

## Project Structure

```
├── config.py            # All strategy & trading parameters
├── secret.py            # API keys (gitignored — never commit)
├── main.py              # Run backtest
├── strategy.py          # Signal logic
├── backtester.py        # Sequential trade simulator
├── optimizer.py         # Grid search over parameter combinations
├── metrics.py           # Win rate, PnL, drawdown, profit factor
├── plotter.py           # Equity curve + trade chart
├── data_loader.py       # Load/generate OHLCV data
├── fetch_delta_data.py  # Pull historical candles from Delta Exchange API
├── analyze_monthly.py   # Monthly P&L breakdown from trades.csv
├── live_trader.py       # Live trading bot (WebSocket + REST)
├── test_delta_api.py    # Verify API connectivity & product IDs
└── test_ws.py           # Verify WebSocket connectivity
```

---

## Setup

**1. Install dependencies**
```bash
pip install -r requ.txt
```

**2. Add API credentials**

Create `secret.py` (already gitignored):
```python
API_KEY    = "your_api_key"
API_SECRET = "your_api_secret"
ETH_PRODUCT_ID = 3136
```

Get keys from: Delta Exchange India → Settings → API Keys

---

## Backtesting

**Fetch fresh data (default: 240 days of 1m candles):**
```bash
python fetch_delta_data.py
```

**Run backtest:**
```bash
python main.py
```

**Optimize parameters:**
```bash
python optimizer.py
```

**Monthly breakdown:**
```bash
python analyze_monthly.py
```

---

## Live Trading

**Configure** `config.py` before running:
```python
REVERSAL_CANDLE_PCT = 0.17 / 100.0   # signal threshold
TAKE_PROFIT_PCT     = 0.25 / 100.0
STOP_LOSS_PCT       = 0.05 / 100.0
TIME_EXIT_CANDLES   = 3
LEVERAGE            = 5.0
ORDER_SIZE          = 2               # fixed lot size (contracts)
```

**Run:**
```bash
python live_trader.py
```

### How it works

1. Connects to Delta Exchange India WebSocket
2. Sets leverage on the exchange at startup
3. Syncs open position state via REST on every connect/reconnect
4. At **T-400ms before candle close**, checks if body ≥ 0.17%
5. If yes → fires a single bracket order (entry + SL + TP atomically)
6. Monitors `orders` channel for TP/SL fills
7. Falls back to market close after 3 candles if bracket hasn't triggered
8. Auto-reconnects on WebSocket drop, preserving position state

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `REVERSAL_CANDLE_PCT` | 0.17% | Min candle body to trigger signal |
| `TAKE_PROFIT_PCT` | 0.25% | TP distance from entry |
| `STOP_LOSS_PCT` | 0.05% | SL distance from entry |
| `TIME_EXIT_CANDLES` | 3 | Max candles to hold trade |
| `LEVERAGE` | 5x | Exchange leverage |
| `ORDER_SIZE` | 2 | Contracts per trade (1 contract = 0.01 ETH) |
| `SL_SLIPPAGE_PCT` | 0.03% | SL slippage modeled in backtest |

---

## Backtest Results (sample — 120 days)

| Metric | Value |
|--------|-------|
| Total Trades | ~6300 |
| Win Rate | ~34.5% |
| Profit Factor | ~1.26 |
| Max Drawdown | ~15% |

> ⚠️ Results use compounding leverage on full equity. Real returns will differ based on fixed position sizing and live execution quality.

---

## Risk Warning

This is experimental software. Crypto perpetual futures trading with leverage carries significant risk of loss. Never trade with funds you cannot afford to lose. Past backtest performance does not guarantee future results.
