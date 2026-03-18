import pandas as pd
from config import Config
from data_loader import load_data, generate_dummy_data
from strategy import compute_signals
from backtester import run_backtest
from metrics import calculate_metrics, print_metrics
from plotter import plot_results
import os

def main():
    cfg = Config()
    
    print("Loading data...")
    if os.path.exists(cfg.DATA_PATH):
        df = load_data(cfg.DATA_PATH)
        print(f"Loaded {len(df)} rows from {cfg.DATA_PATH}")
    else:
        print(f"File '{cfg.DATA_PATH}' not found. Generating dummy data for testing...")
        df = generate_dummy_data()
        df.to_csv(cfg.DATA_PATH, index=False)
        print(f"Dummy data generated and saved to '{cfg.DATA_PATH}'.")
        
    print("Computing signals...")
    df = compute_signals(df, cfg)
    
    print("Running backtest...")
    trades, equity_curve = run_backtest(df, cfg)
    
    print("Calculating metrics...")
    metrics = calculate_metrics(trades, equity_curve)
    
    if metrics:
        print_metrics(metrics)
    else:
        print("No trades were executed. Try adjusting the parameters or provide more data.")
    
    # Optionally save trades to CSV
    if trades:
        pd.DataFrame(trades).to_csv('trades.csv', index=False)
        print("Trades saved to 'trades.csv'")
        
        print("Generating plot...")
        plot_results(df, trades, equity_curve)

if __name__ == "__main__":
    main()
