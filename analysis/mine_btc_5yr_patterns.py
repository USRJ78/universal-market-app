"""
==============================================================================
  ANTIGRAVITY AI BRAIN — 5-YEAR BTC CHART PATTERN MINING & WIN RATE ENGINE
==============================================================================
  Systematically scans 5 Years of BTC price charts (2021-2026) to detect:
  1. Bull Flags & Pennants
  2. Double Bottoms (W-Bottoms)
  3. ATR Volatility Squeezes
  4. EMA 20/50 Golden Crosses
  5. RSI Oversold Bounces
  6. Ascending Triangles
  
  Outputs frequency counts, win rates %, average yields, and profit factors.
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "btc_5yr_pattern_mining_chart.png")

def run_pattern_mining():
    print("=" * 75)
    print("  🔍 MINING 5-YEAR BTC CHART PATTERNS (2021 - 2026)...")
    print("=" * 75)

    try:
        df = yf.download("BTC-USD", start="2021-01-01", end="2026-08-15", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
    except Exception as e:
        print(f"  ❌ Data fetch error: {e}")
        return

    print(f"  Downloaded {len(df)} daily price bars ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')})")

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # Calculate Indicators
    df["EMA20"] = close.ewm(span=20).mean()
    df["EMA50"] = close.ewm(span=50).mean()
    df["EMA200"] = close.ewm(span=200).mean()

    tr = np.maximum(high - low, np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))))
    df["ATR10"] = pd.Series(tr, index=df.index).rolling(10).mean()
    df["ATR50"] = pd.Series(tr, index=df.index).rolling(50).mean()
    df["SqueezeRatio"] = df["ATR10"] / (df["ATR50"] + 1e-9)

    delta = close.diff()
    gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Pattern Recognition Solvers
    patterns = {
        "Bull Flag / Consolidation Breakout": [],
        "Double Bottom (W-Reversal)": [],
        "ATR Volatility Squeeze": [],
        "EMA 20/50 Golden Cross": [],
        "RSI Oversold Bounce (RSI <= 30)": [],
        "Ascending Triangle Breakout": []
    }

    # Target profit: +4.5% within 5 days (1x2 Call Spread sweet spot)
    for i in range(50, len(df) - 5):
        date = df.index[i]
        p_now = close.iloc[i]
        p_future = close.iloc[i+1:i+6].max() # 5-day max high
        p_drop   = close.iloc[i+1:i+6].min()

        trade_win = (p_future - p_now) / p_now >= 0.045
        trade_pnl = ((p_future - p_now) / p_now) * 100.0 if trade_win else ((p_drop - p_now) / p_now) * 100.0

        # Pattern 1: Bull Flag (Sharp move up 3 days ago, consolidation now)
        if (close.iloc[i-3] - close.iloc[i-7]) / close.iloc[i-7] > 0.08 and abs(close.iloc[i] - close.iloc[i-3]) / close.iloc[i-3] < 0.02:
            patterns["Bull Flag / Consolidation Breakout"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

        # Pattern 2: Double Bottom (Low near low of 15 days ago with RSI higher)
        if abs(low.iloc[i] - low.iloc[i-15:i-5].min()) / low.iloc[i] < 0.015 and df["RSI"].iloc[i] > df["RSI"].iloc[i-15:i-5].min():
            patterns["Double Bottom (W-Reversal)"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

        # Pattern 3: ATR Volatility Squeeze (Ratio < 0.85)
        if df["SqueezeRatio"].iloc[i] < 0.85 and close.iloc[i] > df["EMA20"].iloc[i]:
            patterns["ATR Volatility Squeeze"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

        # Pattern 4: EMA 20/50 Cross (EMA20 crosses above EMA50 today)
        if df["EMA20"].iloc[i] > df["EMA50"].iloc[i] and df["EMA20"].iloc[i-1] <= df["EMA50"].iloc[i-1]:
            patterns["EMA 20/50 Golden Cross"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

        # Pattern 5: RSI Oversold Bounce (RSI <= 30 turning up)
        if df["RSI"].iloc[i-1] <= 30 and df["RSI"].iloc[i] > df["RSI"].iloc[i-1]:
            patterns["RSI Oversold Bounce (RSI <= 30)"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

        # Pattern 6: Ascending Triangle (Equal highs, higher lows)
        if abs(high.iloc[i-10:i].max() - high.iloc[i]) / high.iloc[i] < 0.01 and low.iloc[i] > low.iloc[i-5] > low.iloc[i-10]:
            patterns["Ascending Triangle Breakout"].append({"date": date, "win": trade_win, "pnl": trade_pnl})

    # Compile Summary Table
    summary = []
    for name, occurrences in patterns.items():
        if occurrences:
            total_occ = len(occurrences)
            wins      = sum(1 for x in occurrences if x["win"])
            win_rate  = (wins / total_occ) * 100.0
            avg_pnl   = np.mean([x["pnl"] for x in occurrences])
            summary.append({
                "Pattern Name": name,
                "Frequency (Count)": total_occ,
                "Win Rate %": round(win_rate, 1),
                "Average Return %": round(avg_pnl, 2),
                "Wins": wins,
                "Losses": total_occ - wins
            })

    sum_df = pd.DataFrame(summary).sort_values(by="Frequency (Count)", ascending=False)

    print("\n" + "=" * 75)
    print("  🏆 5-YEAR BTC CHART PATTERN MINING LEADERBOARD (2021 - 2026)")
    print("=" * 75)
    for idx, r in enumerate(sum_df.itertuples(), 1):
        print(f"  #{idx} | {r._1:<42}")
        print(f"       Frequency: {r._2} Occurrences (Ranked by Count)")
        print(f"       Win Rate : {r._3}% ({r.Wins} Wins / {r.Losses} Losses)")
        print(f"       Avg Return: +{r._4}%\n")
    print("=" * 75)

    # Plot 4-Panel Graphic
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('⚡ 5-YEAR BTC CHART PATTERN RECOGNITION & FREQUENCY STUDY (2021-2026)', 
                 fontsize=15, fontweight='bold', color='#00d4aa', y=0.96)

    # PANEL 1: Occurrence Frequency Bar Chart
    names = [x[:22] for x in sum_df["Pattern Name"]]
    ax1.barh(names, sum_df["Frequency (Count)"], color='#6c63ff')
    ax1.set_title('Panel 1: Pattern Occurrence Frequency (5-Year Count)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax1.set_xlabel('Total Occurrences Count', fontsize=10, color='#64748b')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')
    for bar in ax1.patches:
        ax1.annotate(f'{int(bar.get_width())}', (bar.get_width() + 3, bar.get_y() + bar.get_height()/2),
                     ha='left', va='center', fontsize=9, fontweight='bold', color='#00d4aa')

    # PANEL 2: Win Rate % Comparison Bar Chart
    colors = ['#00d4aa' if w > 50 else '#ff4d6d' for w in sum_df["Win Rate %"]]
    ax2.bar(names, sum_df["Win Rate %"], color=colors)
    ax2.axhline(50.0, color='#ffd60a', linestyle='--', label='50% Benchmark Line')
    ax2.set_title('Panel 2: Pattern Win Rate % Comparison (+4.5% Target in 5 Days)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax2.set_ylabel('Win Rate %', fontsize=10, color='#64748b')
    ax2.tick_params(axis='x', rotation=30)
    ax2.grid(True, linestyle='--', alpha=0.2, color='#00d4aa')
    ax2.legend(loc='upper right', fontsize=8, frameon=True, facecolor='#0c0d18', edgecolor='#ffd60a')
    for bar in ax2.patches:
        if bar.get_height() > 0:
            ax2.annotate(f'{bar.get_height():.1f}%', (bar.get_x() + bar.get_width()/2, bar.get_height() + 1),
                         ha='center', va='bottom', fontsize=8, fontweight='bold', color='#e2e8f0')

    # PANEL 3: Scatter Plot (Frequency vs Win Rate)
    ax3.scatter(sum_df["Frequency (Count)"], sum_df["Win Rate %"], color='#ffd60a', s=120, edgecolors='#00d4aa', linewidth=2)
    for idx, row in sum_df.iterrows():
        ax3.annotate(row["Pattern Name"].split()[0], (row["Frequency (Count)"] + 4, row["Win Rate %"]), fontsize=8, color='#e2e8f0')
    ax3.set_title('Panel 3: Frequency vs Win Rate Scatter Efficiency', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax3.set_xlabel('Frequency Count', fontsize=10, color='#64748b')
    ax3.set_ylabel('Win Rate %', fontsize=10, color='#64748b')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#ffd60a')

    # PANEL 4: Summary Decision Table
    ax4.axis('off')
    tbl_data = [["Rank", "Pattern Name", "Count", "Win Rate %", "Avg PnL %"]]
    for idx, r in enumerate(sum_df.itertuples(), 1):
        tbl_data.append([f"#{idx}", r._1[:25], str(r._2), f"{r._3}%", f"+{r._4}%"])
    
    table = ax4.table(cellText=tbl_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.2, 1.7)

    for (r_idx, c_idx), cell in table.get_celld().items():
        if r_idx == 0:
            cell.set_facecolor('#6c63ff')
            cell.set_text_props(weight='bold', color='#ffffff')
        else:
            cell.set_facecolor('#0c0d18')
            cell.set_text_props(color='#e2e8f0')
            if c_idx == 3:
                cell.set_text_props(weight='bold', color='#00d4aa')

    ax4.set_title('Panel 4: 5-Year Pattern Mining Summary Database', fontsize=11, fontweight='bold', color='#e2e8f0', pad=15)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_PATH, dpi=300)
    print(f"  📊 Pattern Mining Graphic saved to: {CHART_PATH}")

if __name__ == "__main__":
    run_pattern_mining()
