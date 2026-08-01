"""
==============================================================================
  QUANTITATIVE MODEL: TRAPPED CAPITAL & LIQUIDITY SWEEP DETECTION ENGINE
==============================================================================

CONCEPT:
  1. TRAPPED CAPITAL CLUSTER (Bagholder Node):
     Identifies price zones where high volume was traded, followed by a sharp
     downward displacement. Buyers in this zone are "trapped" underwater.

  2. BREAKEVEN EXIT LIQUIDITY SWEEP:
     Measures impulse rallies ("pumps") back up into the trapped supply cluster.
     As trapped traders scramble to exit at or near breakeven, their sell orders
     absorb buying pressure, creating an ideal institutional short entry or
     predictable market reversal ("dump").

ASSETS EVALUATED:
  - Bitcoin (BTC-USD)
  - Ethereum (ETH-USD)
  - Nifty 50 (^NSEI)
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def detect_trapped_capital(df, vol_window=30, drop_thresh=0.04, retest_window=10):
    df = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # 1. Volume Profile / High Volume Nodes
    vol_sma = vol.rolling(vol_window).mean()
    rel_vol = vol / (vol_sma + 1e-9)

    # 2. Downward Displacement after High Volume (Trapped Longs)
    # Price dropped by > drop_thresh % within 5 bars after high volume cluster
    ret_5d = close.pct_change(5)
    trapped_node = (rel_vol > 1.3) & (ret_5d.shift(-5) < -drop_thresh)

    df["Trapped_Node"] = trapped_node
    df["Trapped_Price"] = np.where(trapped_node, close, np.nan)
    df["Trapped_Price"] = df["Trapped_Price"].ffill(limit=20)  # Active trapped supply zone for 20 bars

    # 3. Liquidity Sweep (Pump into Trapped Zone)
    # High reaches trapped price level after being underwater
    was_underwater = (close.shift(1) < df["Trapped_Price"] * 0.97)
    pump_into_trapped = (high >= df["Trapped_Price"] * 0.99) & (high <= df["Trapped_Price"] * 1.03) & was_underwater

    df["Sweep_Signal"] = pump_into_trapped

    # 4. Measure Post-Sweep Reversal (3-day and 5-day returns following the sweep)
    df["Fwd_Ret_3D"] = close.pct_change(3).shift(-3)
    df["Fwd_Ret_5D"] = close.pct_change(5).shift(-5)

    return df


def run_trapped_liquidity_study():
    tickers = ["BTC-USD", "ETH-USD", "^NSEI"]
    summary_results = []

    print("=" * 75)
    print("  TRAPPED CAPITAL & LIQUIDITY SWEEP RESEARCH SCAN (2020 - 2026)")
    print("=" * 75)

    for ticker in tickers:
        try:
            df = yf.download(ticker, start="2020-01-01", end="2026-07-27", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = detect_trapped_capital(df)

            sweeps = df[df["Sweep_Signal"]].copy()
            num_sweeps = len(sweeps)
            win_rate_dump = (sweeps["Fwd_Ret_5D"] < 0).mean() * 100 if num_sweeps > 0 else 0.0
            avg_dump_5d   = sweeps["Fwd_Ret_5D"].mean() * 100 if num_sweeps > 0 else 0.0

            clean_ticker = ticker.replace("^NSEI", "NIFTY50")
            print(f"\n[ASSET: {clean_ticker}]")
            print(f"  Total Trapped Supply Sweeps Detected: {num_sweeps}")
            print(f"  5-Day Reversal ('Dump') Accuracy   : {win_rate_dump:.1f}%")
            print(f"  Avg 5-Day Post-Sweep Reversal Return: {avg_dump_5d:+.2f}%")

            summary_results.append({
                "Ticker": clean_ticker,
                "Sweeps_Detected": num_sweeps,
                "Reversal_Accuracy_%": round(win_rate_dump, 1),
                "Avg_5D_Reversal_%": round(avg_dump_5d, 2)
            })

            # Plot example chart for BTC
            if ticker == "BTC-USD":
                plot_trapped_capital_chart(df, clean_ticker)

        except Exception as e:
            print(f"  Error analyzing {ticker}: {e}")

    df_summary = pd.DataFrame(summary_results)
    out_csv = os.path.join(OUTPUT_DIR, "trapped_capital_study_summary.csv")
    df_summary.to_csv(out_csv, index=False)
    print(f"\n[OK] Summary saved -> {out_csv}")
    return df_summary


def plot_trapped_capital_chart(df, ticker):
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor(p["bg"])

    ax1.set_facecolor(p["panel"])
    ax2.set_facecolor(p["panel"])

    recent_df = df.iloc[-500:].copy()  # Last ~1.5 years

    ax1.plot(recent_df.index, recent_df["Close"], color=p["text"], lw=1.2, label="Price ($)")
    
    # Highlight Trapped Price Overhang
    ax1.plot(recent_df.index, recent_df["Trapped_Price"], color=p["yellow"], ls="--", lw=1.0, label="Trapped Capital Supply Zone")

    # Mark Liquidity Sweep Reversals
    sweeps = recent_df[recent_df["Sweep_Signal"]]
    ax1.scatter(sweeps.index, sweeps["High"], color=p["red"], s=90, marker="v", zorder=5, label="Breakeven Liquidity Sweep (Exit Zone)")

    ax1.set_title(f"{ticker} — Trapped Capital Supply Nodes & Breakeven Liquidity Sweeps", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax1.set_ylabel("Price ($)", color=p["muted"])
    ax1.tick_params(colors=p["muted"])
    ax1.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    # Volume
    cols = [p["green"] if c >= o else p["red"] for c, o in zip(recent_df["Close"], recent_df["Open"])]
    ax2.bar(recent_df.index, recent_df["Volume"], color=cols, alpha=0.6)
    ax2.set_ylabel("Volume", color=p["muted"])
    ax2.tick_params(colors=p["muted"])

    out_png = os.path.join(OUTPUT_DIR, "trapped_capital_chart.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Chart saved -> {out_png}")


if __name__ == "__main__":
    run_trapped_liquidity_study()
