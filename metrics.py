import pandas as pd

def calculate_metrics(trades, equity_curve):
    if not trades:
        return {}
        
    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    winning_trades = df_trades[df_trades['pnl_abs'] > 0]
    losing_trades = df_trades[df_trades['pnl_abs'] <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    
    total_pnl_abs = df_trades['pnl_abs'].sum()
    
    initial_equity = equity_curve[0][1]
    final_equity = equity_curve[-1][1]
    total_pnl_pct = (final_equity - initial_equity) / initial_equity
    
    avg_win = winning_trades['pnl_abs'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl_abs'].mean() if len(losing_trades) > 0 else 0
    
    gross_profit = winning_trades['pnl_abs'].sum()
    gross_loss = abs(losing_trades['pnl_abs'].sum())
    
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max Drawdown
    equity_values = [eq for t, eq in equity_curve]
    peak = equity_values[0]
    max_dd = 0
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd
            
    # Exit reasons distribution
    exit_reasons = df_trades['reason'].value_counts().to_dict()
            
    return {
        'Total Trades': total_trades,
        'Win Rate (%)': win_rate * 100,
        'Total PnL (Absolute)': total_pnl_abs,
        'Total PnL (%)': total_pnl_pct * 100,
        'Average Win': avg_win,
        'Average Loss': avg_loss,
        'Max Drawdown (%)': max_dd * 100,
        'Profit Factor': profit_factor,
        'Exit Reasons': exit_reasons
    }

def print_metrics(metrics):
    print("=== Backtest Results ===")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print("========================")
