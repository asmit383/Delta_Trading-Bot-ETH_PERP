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

    print("\n=== Monthly Performance Analysis ===")
    print(f"{'Month':<10} {'PnL ($)':<20} {'Trades':<10} {'Win Rate':<10}")
    print("-" * 55)

    for month, row in monthly_stats.iterrows():
        print(f"{month:<10} ${row['pnl_abs']:<19,.2f} {int(row['trade_count']):<10} {row['win_rate']:<10.2f}%")
        
    print("-" * 55)
    print(f"Total Net PnL: ${df['pnl_abs'].sum():,.2f}")

if __name__ == "__main__":
    analyze_monthly()
