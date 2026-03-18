import matplotlib.pyplot as plt
import pandas as pd

def plot_results(df, trades, equity_curve):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # Plot Price
    ax1.plot(df['timestamp'], df['close'], label='Close Price', color='grey', alpha=0.5)
    
    # Plot Trades
    df_trades = pd.DataFrame(trades)
    if not df_trades.empty:
        longs = df_trades[df_trades['direction'] == 'LONG']
        shorts = df_trades[df_trades['direction'] == 'SHORT']
        
        ax1.scatter(longs['entry_time'], longs['entry_price'], marker='^', color='green', s=100, label='Long Entry')
        ax1.scatter(shorts['entry_time'], shorts['entry_price'], marker='v', color='red', s=100, label='Short Entry')
        
    ax1.set_title('Price & Trades')
    ax1.set_ylabel('Price')
    ax1.legend()
    
    # Plot Equity Curve
    eq_times = [t for t, eq in equity_curve]
    eq_vals = [eq for t, eq in equity_curve]
    ax2.plot(eq_times, eq_vals, label='Equity', color='blue')
    ax2.set_title('Equity Curve')
    ax2.set_ylabel('Capital')
    ax2.legend()
    
    plt.tight_layout()
    # Save the plot instead of show to avoid blocking and headless issues
    plt.savefig('backtest_results.png')
    print("Plot saved to backtest_results.png")
