import pandas as pd
import os

def analyze_monthly():
    if not os.path.exists('trades.csv'):
        print("Error: trades.csv not found. Please run main.py first.")
        return

    df = pd.read_csv('trades.csv')
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['month'] = df['entry_time'].dt.strftime('%Y-%m')

    # Calculate monthly PnL and Win Rate
    monthly_stats = df.groupby('month').agg({
        'pnl_abs': 'sum',
        'pnl_pct': 'count'
    }).rename(columns={'pnl_pct': 'trade_count'})

    monthly_stats['win_rate'] = df.groupby('month').apply(lambda x: (x['pnl_abs'] > 0).mean() * 100)

    # Compute cumulative equity to get monthly % return
    from config import Config
    initial_capital = Config.INITIAL_CAPITAL
    equity = initial_capital
    monthly_pct = {}
    for month in sorted(monthly_stats.index):
        month_pnl = monthly_stats.loc[month, 'pnl_abs']
        pct = (month_pnl / equity) * 100
        monthly_pct[month] = pct
        equity += month_pnl
    monthly_stats['pnl_pct_return'] = pd.Series(monthly_pct)

    print("\n=== Monthly Performance Analysis ===")
    print(f"{'Month':<10} {'PnL ($)':<20} {'PnL %':<12} {'Trades':<10} {'Win Rate':<10}")
    print("-" * 67)

    for month, row in monthly_stats.iterrows():
        print(f"{month:<10} ${row['pnl_abs']:<19,.2f} {row['pnl_pct_return']:>+8.2f}%   {int(row['trade_count']):<10} {row['win_rate']:<10.2f}%")

    print("-" * 67)
    total_pct = (df['pnl_abs'].sum() / initial_capital) * 100
    print(f"Total Net PnL: ${df['pnl_abs'].sum():,.2f}  ({total_pct:+.2f}% on initial capital)")

if __name__ == "__main__":
    analyze_monthly()
