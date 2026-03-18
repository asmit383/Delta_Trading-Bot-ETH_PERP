import pandas as pd
import matplotlib.pyplot as plt
import os

def analyze_hours():
    if not os.path.exists('trades.csv'):
        print("Error: trades.csv not found. Run main.py first.")
        return

    df = pd.read_csv('trades.csv')
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['entry_time'] = df['entry_time'] + pd.Timedelta(hours=5, minutes=30)  # UTC → IST
    df['hour'] = df['entry_time'].dt.hour

    def avg_rr(x):
        wins  = x[x > 0].mean()
        losses = x[x < 0].abs().mean()
        return round(wins / losses, 2) if losses > 0 and wins > 0 else 0

    hourly = df.groupby('hour').agg(
        total_pnl   = ('pnl_abs', 'sum'),
        trades      = ('pnl_abs', 'count'),
        win_rate    = ('pnl_abs', lambda x: (x > 0).mean() * 100),
        avg_pnl     = ('pnl_abs', 'mean'),
        rr_ratio    = ('pnl_abs', avg_rr),
    ).reset_index()

    hourly['hour_label'] = hourly['hour'].apply(lambda h: f"{h:02d}:00")

    print("\n=== Hourly Performance ===")
    print(f"{'Hour':<8} {'PnL ($)':<14} {'Trades':<10} {'Win Rate':<12} {'Avg PnL':<12} {'RR Ratio'}")
    print("-" * 68)
    for _, r in hourly.sort_values('total_pnl', ascending=False).iterrows():
        print(f"{r['hour_label']:<8} ${r['total_pnl']:<13,.2f} {int(r['trades']):<10} {r['win_rate']:<11.1f}% ${r['avg_pnl']:<11.2f} {r['rr_ratio']:.2f}x")

    print("\n=== Top 3 Hours ===")
    for _, r in hourly.nlargest(3, 'total_pnl').iterrows():
        print(f"  {r['hour_label']}  →  ${r['total_pnl']:,.2f}  |  {r['win_rate']:.1f}% win rate  |  {int(r['trades'])} trades")

    print("\n=== Worst 3 Hours ===")
    for _, r in hourly.nsmallest(3, 'total_pnl').iterrows():
        print(f"  {r['hour_label']}  →  ${r['total_pnl']:,.2f}  |  {r['win_rate']:.1f}% win rate  |  {int(r['trades'])} trades")

    # ── Session ranges (IST) ──────────────────────────────────────────────────
    sessions = {
        "Asia          (05:30 - 11:30)": range(5, 12),
        "London        (13:30 - 19:30)": range(13, 20),
        "New York      (19:30 - 01:30)": list(range(19, 24)) + list(range(0, 2)),
        "Dead Hours    (02:00 - 05:30)": range(2, 6),
    }

    print("\n=== Session Performance (IST) ===")
    print(f"{'Session':<30} {'PnL ($)':<14} {'Trades':<10} {'Win Rate':<12} {'Avg PnL':<12} {'RR Ratio'}")
    print("-" * 82)
    for name, hours in sessions.items():
        seg = df[df['hour'].isin(hours)]
        if seg.empty:
            continue
        total   = seg['pnl_abs'].sum()
        trades  = len(seg)
        wr      = (seg['pnl_abs'] > 0).mean() * 100
        avg     = seg['pnl_abs'].mean()
        wins    = seg[seg['pnl_abs'] > 0]['pnl_abs'].mean()
        losses  = seg[seg['pnl_abs'] < 0]['pnl_abs'].abs().mean()
        rr      = round(wins / losses, 2) if wins > 0 and losses > 0 else 0
        print(f"{name:<30} ${total:<13,.2f} {trades:<10} {wr:<11.1f}% ${avg:<11.2f} {rr:.2f}x")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    colors = ['green' if x >= 0 else 'red' for x in hourly['total_pnl']]
    ax1.bar(hourly['hour_label'], hourly['total_pnl'], color=colors)
    ax1.axhline(0, color='black', linewidth=0.8)
    ax1.set_title('Total PnL by Hour')
    ax1.set_ylabel('PnL ($)')
    ax1.tick_params(axis='x', rotation=45)

    ax2.bar(hourly['hour_label'], hourly['win_rate'], color='steelblue')
    ax2.axhline(50, color='red', linewidth=0.8, linestyle='--', label='50%')
    ax2.set_title('Win Rate by Hour')
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend()

    plt.tight_layout()
    plt.savefig('hourly_analysis.png')
    print("\nChart saved to hourly_analysis.png")

if __name__ == "__main__":
    analyze_hours()
