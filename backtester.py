import pandas as pd
from config import Config

def run_backtest(df: pd.DataFrame, cfg: Config) -> tuple:
    """
    Simulate trades sequentially.
    Only 1 trade at a time.
    Returns:
        trades: list of dictionaries with trade info
        equity_curve: list of (timestamp, equity)
    """
    trades = []
    equity = cfg.INITIAL_CAPITAL
    equity_curve = [(df['timestamp'].iloc[0] if 'timestamp' in df.columns else 0, equity)]
    
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    entry_time = None
    entry_idx = 0
    trade_qty = 0.0
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        timestamp = row['timestamp'] if 'timestamp' in df else i
        
        # If in a trade, check exit conditions
        if in_trade:
            # Current candle high, low, close for intra-candle simulation
            c_high = row['high']
            c_low = row['low']
            c_close = row['close']
            
            exit_price = 0.0
            exit_reason = ""
            
            bars_held = i - entry_idx
            
            # Simple simulation: in a real backtester, to be conservative, we check SL first
            if trade_dir == 1: # LONG
                stop_price = entry_price * (1.0 - cfg.STOP_LOSS_PCT)
                take_profit_price = entry_price * (1.0 + cfg.TAKE_PROFIT_PCT)
                
                if c_low <= stop_price:
                    exit_price = stop_price * (1.0 - cfg.SL_SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif c_high >= take_profit_price:
                    exit_price = take_profit_price
                    exit_reason = "TP"
                elif bars_held >= cfg.TIME_EXIT_CANDLES:
                    exit_price = c_close
                    exit_reason = "TIME"
                    
            elif trade_dir == -1: # SHORT
                stop_price = entry_price * (1.0 + cfg.STOP_LOSS_PCT)
                take_profit_price = entry_price * (1.0 - cfg.TAKE_PROFIT_PCT)
                
                if c_high >= stop_price:
                    exit_price = stop_price * (1.0 + cfg.SL_SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif c_low <= take_profit_price:
                    exit_price = take_profit_price
                    exit_reason = "TP"
                elif bars_held >= cfg.TIME_EXIT_CANDLES:
                    exit_price = c_close
                    exit_reason = "TIME"
            
            if exit_reason != "":
                # Calculate PnL
                if trade_dir == 1:
                    gross_pnl_pct = (exit_price - entry_price) / entry_price
                else:
                    gross_pnl_pct = (entry_price - exit_price) / entry_price
                    
                net_pnl_pct = gross_pnl_pct - cfg.ENTRY_FEE_PCT - cfg.EXIT_FEE_PCT
                pnl_abs = trade_qty * net_pnl_pct * entry_price
                
                equity += pnl_abs
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'direction': 'LONG' if trade_dir == 1 else 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_abs': pnl_abs,
                    'pnl_pct': net_pnl_pct,
                    'reason': exit_reason
                })
                
                equity_curve.append((timestamp, equity))
                in_trade = False
                
        # If not in trade, check signals from previous candle
        if not in_trade:
            signal = prev_row['signal']
            if signal != 0:
                in_trade = True
                trade_dir = signal
                
                # Apply slippage to entry price
                raw_entry = row['open']
                if trade_dir == 1: # Buying
                    entry_price = raw_entry * (1.0 + cfg.SLIPPAGE_PCT)
                else: # Selling
                    entry_price = raw_entry * (1.0 - cfg.SLIPPAGE_PCT)
                
                entry_time = timestamp
                entry_idx = i
                
                # Apply leverage to quantity
                trade_qty = (equity * cfg.LEVERAGE) / entry_price
    
    # Close any open trade at the end
    if in_trade:
        row = df.iloc[-1]
        exit_price = row['close']
        if trade_dir == 1:
            gross_pnl_pct = (exit_price - entry_price) / entry_price
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price
            
        net_pnl_pct = gross_pnl_pct - cfg.ENTRY_FEE_PCT - cfg.EXIT_FEE_PCT
        pnl_abs = trade_qty * net_pnl_pct * entry_price
        
        equity += pnl_abs
        trades.append({
            'entry_time': entry_time,
            'exit_time': row['timestamp'] if 'timestamp' in df else len(df)-1,
            'direction': 'LONG' if trade_dir == 1 else 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_abs': pnl_abs,
            'pnl_pct': net_pnl_pct,
            'reason': 'END_OF_DATA'
        })
        equity_curve.append((row['timestamp'] if 'timestamp' in df else len(df)-1, equity))
                
    return trades, equity_curve
