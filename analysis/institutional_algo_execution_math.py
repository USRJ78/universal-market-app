"""
==============================================================================
  INSTITUTIONAL ALGORITHMIC ORDER EXECUTION MATH MODEL
==============================================================================

MATHEMATICAL INVARIANTS FOR ALGO ENTRY & EXIT ZONES:

1. ANCHORED VWAP STDEV BANDS (ALMGREN-CHRISS EXECUTION BENCHMARK):
   - Algo Accumulation Zone: P <= VWAP - 2 * sigma
   - Algo Distribution/Exit Zone: P >= VWAP + 2 * sigma
   - Math: VWAP = sum(Price * Volume) / sum(Volume)
           sigma = sqrt( sum(Volume * (Price - VWAP)^2) / sum(Volume) )

2. VALUE AREA & VOLUME POINT OF CONTROL (VPVR / POC):
   - Institutional Icebergs cluster at POC (Point of Control) and VAL/VAH (Value Area Low/High).
   - 68% Volume Envelope around POC represents fair value.
   - Price escaping VAH/VAL triggers algo momentum expansion.

3. HURST EXPONENT (REGIME SHIFT DETECTOR):
   - H < 0.45: Mean-Reverting (Algos execute Grid / Market-Making strategies).
   - H > 0.55: Trending / Directional (Algos execute VWAP Sweep / Momentum).

4. GAMMA EXPOSURE (GEX) REVERSAL BOUNDARIES:
   - Identifies zero-gamma inflection zones where options market maker hedging flips
     from volatility dampening (long gamma) to volatility acceleration (short gamma).
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

def calculate_hurst_exponent(ts, max_lag=20):
    """Calculates Hurst Exponent for time-series ts."""
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0


def compute_algo_execution_zones(df):
    df = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # 1. Rolling Anchored VWAP & Standard Deviation Bands (30-bar rolling)
    window = 30
    pv = close * vol
    vwap = pv.rolling(window).sum() / (vol.rolling(window).sum() + 1e-9)
    
    # Weighted Standard Deviation
    var = (vol * (close - vwap)**2).rolling(window).sum() / (vol.rolling(window).sum() + 1e-9)
    vwap_std = np.sqrt(var)

    df["VWAP"] = vwap
    df["VWAP_Upper_2s"] = vwap + 2.0 * vwap_std
    df["VWAP_Lower_2s"] = vwap - 2.0 * vwap_std
    df["VWAP_Upper_3s"] = vwap + 3.0 * vwap_std
    df["VWAP_Lower_3s"] = vwap - 3.0 * vwap_std

    # 2. Institutional Algo Signals based on VWAP StDev Thresholds
    # Accumulation (Algo Buying Zone below -2s)
    df["Algo_Accumulation_Zone"] = close <= df["VWAP_Lower_2s"]
    # Distribution / Exit (Algo Selling Zone above +2s)
    df["Algo_Exit_Zone"]         = close >= df["VWAP_Upper_2s"]

    # 3. Rolling Hurst Exponent (Regime Filter)
    hurst_vals = []
    close_vals = close.values
    for i in range(len(close_vals)):
        if i < 40:
            hurst_vals.append(0.50)
        else:
            ts_slice = close_vals[i-30:i]
            try:
                h = calculate_hurst_exponent(ts_slice)
                hurst_vals.append(clamp(h, 0.1, 0.9))
            except Exception:
                hurst_vals.append(0.50)

    df["Hurst_Exponent"] = hurst_vals
    df["Regime"] = np.where(df["Hurst_Exponent"] > 0.55, "TREND", np.where(df["Hurst_Exponent"] < 0.45, "MEAN_REVERT", "NEUTRAL"))

    # 4. Measure Reversal Accuracy at Algo Execution Zones
    df["Ret_3D"] = close.pct_change(3).shift(-3)

    # Accumulation Zone Reversal: Returns positive over 3 days
    accum_success = df[df["Algo_Accumulation_Zone"]]["Ret_3D"] > 0
    # Exit Zone Reversal: Returns negative over 3 days
    exit_success  = df[df["Algo_Exit_Zone"]]["Ret_3D"] < 0

    return df, accum_success, exit_success


def clamp(val, min_v, max_v):
    return max(min_v, min(val, max_v))


def run_institutional_algo_study():
    tickers = ["BTC-USD", "ETH-USD", "^NSEI"]
    print("=" * 75)
    print("  INSTITUTIONAL ALGO EXECUTION ZONES & MATHEMATICAL INVARIANTS")
    print("=" * 75)

    summary = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, start="2022-01-01", end="2026-07-27", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df, accum_succ, exit_succ = compute_algo_execution_zones(df)

            accum_count = df["Algo_Accumulation_Zone"].sum()
            exit_count  = df["Algo_Exit_Zone"].sum()

            accum_win = (accum_succ.mean() * 100) if len(accum_succ) > 0 else 0.0
            exit_win  = (exit_succ.mean() * 100) if len(exit_succ) > 0 else 0.0

            clean_ticker = ticker.replace("^NSEI", "NIFTY50")

            print(f"\n[ASSET: {clean_ticker}]")
            print(f"  Algo Accumulation Signals (-2 sigma VWAP) : {accum_count} bars | Reversal Accuracy: {accum_win:.1f}%")
            print(f"  Algo Distribution/Exit Signals (+2 sigma VWAP): {exit_count} bars | Reversal Accuracy: {exit_win:.1f}%")

            summary.append({
                "Ticker": clean_ticker,
                "Accumulation_Signals": accum_count,
                "Accumulation_Accuracy_%": round(accum_win, 1),
                "Exit_Signals": exit_count,
                "Exit_Accuracy_%": round(exit_win, 1)
            })

            if ticker == "BTC-USD":
                plot_algo_execution_chart(df, clean_ticker)

        except Exception as e:
            print(f"  Error analyzing {ticker}: {e}")

    df_sum = pd.DataFrame(summary)
    out_csv = os.path.join(OUTPUT_DIR, "institutional_algo_summary.csv")
    df_sum.to_csv(out_csv, index=False)
    print(f"\n[OK] Institutional Algo Study saved -> {out_csv}")


def plot_algo_execution_chart(df, ticker):
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "purple": "#bc8cff", "text": "#c9d1d9", "muted": "#8b949e"}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor(p["bg"])
    ax1.set_facecolor(p["panel"])
    ax2.set_facecolor(p["panel"])

    recent = df.iloc[-400:].copy()

    # Price & VWAP StDev Bands
    ax1.plot(recent.index, recent["Close"], color=p["text"], lw=1.2, label="Price ($)")
    ax1.plot(recent.index, recent["VWAP"], color=p["blue"], lw=1.5, label="Anchored VWAP Benchmark")
    ax1.plot(recent.index, recent["VWAP_Upper_2s"], color=p["red"], ls="--", lw=1.0, label="Algo Exit Band (+2σ VWAP)")
    ax1.plot(recent.index, recent["VWAP_Lower_2s"], color=p["green"], ls="--", lw=1.0, label="Algo Accumulation Band (-2σ VWAP)")

    # Highlight Execution Points
    accum_pts = recent[recent["Algo_Accumulation_Zone"]]
    exit_pts  = recent[recent["Algo_Exit_Zone"]]

    ax1.scatter(accum_pts.index, accum_pts["Low"] * 0.99, color=p["green"], s=70, marker="^", zorder=5, label="Algo Accumulation Entry (-2σ)")
    ax1.scatter(exit_pts.index, exit_pts["High"] * 1.01, color=p["red"], s=70, marker="v", zorder=5, label="Algo Distribution Exit (+2σ)")

    ax1.set_title(f"{ticker} — Institutional Algorithmic Execution Bands (VWAP ± 2σ Benchmark Invariants)", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax1.set_ylabel("Price ($)", color=p["muted"])
    ax1.tick_params(colors=p["muted"])
    ax1.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    # Hurst Exponent (Regime Indicator)
    ax2.plot(recent.index, recent["Hurst_Exponent"], color=p["purple"], lw=1.2, label="Hurst Exponent (Regime Detector)")
    ax2.axhline(0.55, color=p["green"], ls=":", lw=1.0, label="Trending (>0.55)")
    ax2.axhline(0.45, color=p["red"], ls=":", lw=1.0, label="Mean-Reverting (<0.45)")
    ax2.set_ylabel("Hurst (H)", color=p["muted"])
    ax2.tick_params(colors=p["muted"])
    ax2.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    out_png = os.path.join(OUTPUT_DIR, "institutional_algo_chart.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Algo Execution Chart saved -> {out_png}")


if __name__ == "__main__":
    run_institutional_algo_study()
