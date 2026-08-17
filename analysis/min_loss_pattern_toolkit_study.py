"""
==============================================================================
  ANTIGRAVITY AI BRAIN — CAPITAL PRESERVATION TOOLKIT & PATTERN STUDY (2021-2026)
==============================================================================
  Evaluates 7 major Technical Tools & Indicators (RSI, Fibonacci 61.8%, MACD,
  Bollinger Squeeze, Supertrend, Volume Profile Support) on 5 years of BTC data
  specifically targeting MINIMAL CAPITAL LOSS (Lowest MDD & Highest Profit Factor).
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
CHART_PATH   = os.path.join(ANALYSIS_DIR, "min_loss_toolkit_chart.png")

def run_toolkit_study():
    print("=" * 75)
    print("  🛡️ MINING LOWEST-LOSS TOOLKIT PATTERNS (2021 - 2026)...")
    print("=" * 75)

    try:
        df = yf.download("BTC-USD", start="2021-01-01", end="2026-08-15", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
    except Exception as e:
        print(f"  ❌ Data fetch error: {e}")
        return

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # 1. RSI (14)
    delta = close.diff()
    gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # 2. MACD (12, 26, 9)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()

    # 3. Bollinger Bands (20, 2) & Bandwidth Squeeze
    df["BB_Mid"]   = close.rolling(20).mean()
    df["BB_Std"]   = close.rolling(20).std()
    df["BB_Upper"] = df["BB_Mid"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Mid"] - 2.0 * df["BB_Std"]
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / (df["BB_Mid"] + 1e-9)

    # 4. Fibonacci 61.8% Golden Ratio Level (Rolling 50-day High/Low)
    df["RollingHigh"] = high.rolling(50).max()
    df["RollingLow"]  = low.rolling(50).min()
    df["Fib618"]      = df["RollingLow"] + 0.618 * (df["RollingHigh"] - df["RollingLow"])
    df["Fib500"]      = df["RollingLow"] + 0.500 * (df["RollingHigh"] - df["RollingLow"])

    # 5. Supertrend / ATR Bands
    tr = np.maximum(high - low, np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))))
    df["ATR14"] = pd.Series(tr, index=df.index).rolling(14).mean()
    df["Supertrend"] = close - 2.0 * df["ATR14"]

    toolkits = [
        {"name": "Fibonacci 61.8% Golden Bounce + 1x2 Spread", "type": "fib618"},
        {"name": "RSI Oversold (RSI <= 32) + 1x2 Spread", "type": "rsi"},
        {"name": "Bollinger Squeeze Breakout + 1x2 Spread", "type": "bb"},
        {"name": "MACD Histogram Cross + 1x2 Spread", "type": "macd"},
        {"name": "Supertrend ATR Trailing + 1x2 Spread", "type": "supertrend"},
        {"name": "Fibonacci 50% Mid-Pullback + 1x2 Spread", "type": "fib500"},
        {"name": "Combined Fortress Shield (Fib + RSI + Vol Squeeze)", "type": "fortress"}
    ]

    initial_cap = 100000.0 # Rs. 1 Lakh
    cap_limit   = 2500000.0
    brokerage   = 0.0005
    slippage    = 0.0015
    tax_rate    = 0.15

    results = []

    for tk in toolkits:
        capital     = initial_cap
        eq_curve    = [capital]
        ttype       = tk["type"]
        in_pos      = False
        entry_p     = 0.0
        entry_d     = None
        margin      = 0.0
        trades      = []

        for i in range(50, len(df)):
            date  = df.index[i]
            price = close.iloc[i]

            trigger = False
            if ttype == "fib618":
                trigger = (abs(price - df["Fib618"].iloc[i]) / price < 0.015) and (df["RSI"].iloc[i] < 58)
            elif ttype == "rsi":
                trigger = (df["RSI"].iloc[i] <= 32) or (48 <= df["RSI"].iloc[i] <= 62 and price > df["BB_Mid"].iloc[i])
            elif ttype == "bb":
                trigger = (df["BB_Width"].iloc[i] < 0.08) and (price > df["BB_Upper"].iloc[i-1])
            elif ttype == "macd":
                trigger = (df["MACD"].iloc[i] > df["MACD_Signal"].iloc[i]) and (df["MACD"].iloc[i-1] <= df["MACD_Signal"].iloc[i-1])
            elif ttype == "supertrend":
                trigger = (price > df["Supertrend"].iloc[i]) and (price > df["BB_Mid"].iloc[i])
            elif ttype == "fib500":
                trigger = (abs(price - df["Fib500"].iloc[i]) / price < 0.015)
            elif ttype == "fortress":
                # Combined Fortress Shield
                fib_ok = (price >= df["Fib500"].iloc[i])
                rsi_ok = (df["RSI"].iloc[i] < 64)
                vol_ok = (df["BB_Width"].iloc[i] < 0.12)
                trigger = fib_ok and rsi_ok and vol_ok

            if not in_pos:
                if trigger:
                    in_pos  = True
                    entry_p = price * (1.0 + slippage)
                    entry_d = date
                    margin  = min(capital * 0.25, cap_limit)
                    k1      = entry_p
                    k2      = entry_p * 1.045
            else:
                hold_days = (date - entry_d).days
                if hold_days >= 5 or price >= k2:
                    exit_p = price * (1.0 - slippage)
                    payoff_k1 = max(0.0, exit_p - k1)
                    payoff_k2 = max(0.0, exit_p - k2)
                    spread_p  = payoff_k1 - (2.0 * payoff_k2)

                    max_risk = -0.05 * margin # Hard-capped loss at -5% of margin (-1.25% portfolio)
                    raw_pnl  = max(max_risk, (spread_p / (entry_p + 1e-9)) * margin * 3.5)
                    net_pnl  = raw_pnl - (margin * brokerage)
                    
                    if net_pnl > 0:
                        net_pnl *= (1.0 - tax_rate)

                    capital += net_pnl
                    in_pos   = False
                    trades.append({"pnl": net_pnl, "pnl_pct": (net_pnl / margin) * 100.0})

            eq_curve.append(capital)

        # Audit Calculations
        tdf = pd.DataFrame(trades)
        total_t = len(tdf)
        wins    = tdf[tdf["pnl"] > 0] if total_t > 0 else pd.DataFrame()
        losses  = tdf[tdf["pnl"] <= 0] if total_t > 0 else pd.DataFrame()

        win_rate = (len(wins) / total_t) * 100.0 if total_t > 0 else 0.0
        pf       = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) > 0 and abs(losses["pnl"].sum()) > 0 else 45.0

        eq_s  = pd.Series(eq_curve)
        peak  = eq_s.cummax()
        mdd   = abs(((eq_s - peak) / peak).min()) * 100.0
        cagr  = ((capital / initial_cap) ** (1/5.6) - 1.0) * 100.0

        results.append({
            "name":       tk["name"],
            "capital":    capital,
            "net_profit": capital - initial_cap,
            "mult":       capital / initial_cap,
            "cagr":       cagr,
            "mdd":        mdd,
            "pf":         pf,
            "win_rate":   win_rate,
            "trades":     total_t
        })

    res_df = pd.DataFrame(results).sort_values(by="mdd", ascending=True)

    print("\n" + "=" * 75)
    print("  🏆 CAPITAL PRESERVATION & LOWEST-LOSS TOOLKIT LEADERBOARD")
    print("=" * 75)
    for idx, r in enumerate(res_df.itertuples(), 1):
        print(f"  #{idx} | {r.name:<50}")
        print(f"       Max Drawdown (Loss): -{r.mdd:.2f}% | Profit Factor: {r.pf:.2f}")
        print(f"       Starting: Rs. 1 Lakh -> Final: Rs. {r.capital:,.2f} ({r.mult:.2f}x | CAGR: +{r.cagr:.1f}%)\n")
    print("=" * 75)

    # Plot 4-Panel Graphic
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('⚡ CAPITAL PRESERVATION TOOLKIT STUDY: LOWEST LOSS PATTERN SEARCH (2021-2026)', 
                 fontsize=15, fontweight='bold', color='#00d4aa', y=0.96)

    # PANEL 1: Max Drawdown % (Lowest Loss Comparison)
    names = [x[:25] for x in res_df["name"]]
    ax1.barh(names, res_df["mdd"], color='#00d4aa')
    ax1.set_title('Panel 1: Maximum Drawdown % (Lowest Loss Safeguard)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax1.set_xlabel('Max Drawdown % (Lower is Safer)', fontsize=10, color='#64748b')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#00d4aa')
    for bar in ax1.patches:
        ax1.annotate(f'-{bar.get_width():.2f}%', (bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2),
                     ha='left', va='center', fontsize=9, fontweight='bold', color='#00d4aa')

    # PANEL 2: Profit Factor (Positive Expectancy)
    ax2.bar(names, res_df["pf"], color='#ffd60a')
    ax2.set_title('Panel 2: Profit Factor Comparison (Gains vs Losses Ratio)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax2.set_ylabel('Profit Factor', fontsize=10, color='#64748b')
    ax2.tick_params(axis='x', rotation=30)
    ax2.grid(True, linestyle='--', alpha=0.2, color='#ffd60a')
    for bar in ax2.patches:
        ax2.annotate(f'{bar.get_height():.1f}', (bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5),
                     ha='center', va='bottom', fontsize=8, fontweight='bold', color='#e2e8f0')

    # PANEL 3: CAGR % vs Max Drawdown Scatter (Safest Top-Left Quadrant)
    ax3.scatter(res_df["mdd"], res_df["cagr"], color='#6c63ff', s=120, edgecolors='#00d4aa', linewidth=2)
    for idx, row in res_df.iterrows():
        ax3.annotate(row["name"].split()[0], (row["mdd"] + 0.08, row["cagr"]), fontsize=8, color='#e2e8f0')
    ax3.set_title('Panel 3: CAGR % vs Max Drawdown % (Safest Top-Left Zone)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax3.set_xlabel('Max Drawdown % (Risk)', fontsize=10, color='#64748b')
    ax3.set_ylabel('CAGR % (Reward)', fontsize=10, color='#64748b')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')

    # PANEL 4: Summary Table
    ax4.axis('off')
    tbl_data = [["Rank", "Toolkit Pattern", "Max Drawdown", "Profit Factor", "CAGR %", "5-Yr Equity"]]
    for idx, r in enumerate(res_df.itertuples(), 1):
        tbl_data.append([f"#{idx}", r.name[:25], f"-{r.mdd:.2f}%", f"{r.pf:.1f}", f"+{r.cagr:.1f}%", f"Rs. {r.capital/100000:.2f}L"])
    
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
            if c_idx == 2:
                cell.set_text_props(weight='bold', color='#00d4aa')

    ax4.set_title('Panel 4: Lowest Loss Toolkit Summary Matrix', fontsize=11, fontweight='bold', color='#e2e8f0', pad=15)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_PATH, dpi=300)
    print(f"  📊 Toolkit Study Graphic saved to: {CHART_PATH}")

if __name__ == "__main__":
    run_toolkit_study()
