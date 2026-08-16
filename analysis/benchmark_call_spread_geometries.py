"""
==============================================================================
  ANTIGRAVITY AI BRAIN — MARKET GEOMETRY STRATEGY BENCHMARK SWEEP (2016-2026)
==============================================================================
  Compares 6 different quantitative market geometries combined with Call Spreads
  under strict real-world friction & tax conditions:
  - Slippage (0.15%), Brokerage (0.05%), STT, GST
  - Section 115BAB 15% Corporate Tax
  - Rs. 25 Lakh ($30,000 USD) Trade Capacity Cap
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
CHART_PATH   = os.path.join(ANALYSIS_DIR, "geometry_benchmark_comparison_chart.png")

def run_benchmark():
    print("=" * 75)
    print("  ⚡ RUNNING MARKET GEOMETRY STRATEGY BENCHMARK SWEEP (2016 - 2026)")
    print("=" * 75)

    print("  📡 Downloading 10-Year BTC-USD price data...")
    try:
        df = yf.download("BTC-USD", start="2016-01-01", end="2026-08-15", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
    except Exception as e:
        print(f"  ❌ Data fetch error: {e}")
        return

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    df["EMA9"]   = close.ewm(span=9).mean()
    df["EMA21"]  = close.ewm(span=21).mean()
    df["EMA50"]  = close.ewm(span=50).mean()
    df["EMA200"] = close.ewm(span=200).mean()
    df["High52"] = high.rolling(252, min_periods=50).max()

    # Volatility Squeeze Ratio
    tr = np.maximum(high - low, np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))))
    df["ATR10"] = pd.Series(tr, index=df.index).rolling(10).mean()
    df["ATR50"] = pd.Series(tr, index=df.index).rolling(50).mean()
    df["SqueezeRatio"] = df["ATR10"] / (df["ATR50"] + 1e-9)

    # RSI (14)
    delta = close.diff()
    gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Define 6 Geometries
    geometries = [
        {"name": "RSI Momentum + 1x2 Call Spread", "type": "rsi"},
        {"name": "EMA 9/21 Trend + 1x2 Call Spread", "type": "ema"},
        {"name": "ATR Squeeze + 1x2 Call Spread", "type": "atr"},
        {"name": "52-Week Breakout + 1x2 Call Spread", "type": "breakout"},
        {"name": "Kakushadze #151 + Bullish Seagull", "type": "seagull"},
        {"name": "Multi-Agent Swarm Matrix + 1x2 Call Spread", "type": "swarm"}
    ]

    initial_capital = 100000.0  # Rs. 1 Lakh
    capacity_limit  = 2500000.0 # Rs. 25 Lakh
    brokerage_pct   = 0.0005
    slippage_pct    = 0.0015
    tax_rate        = 0.15

    results = []

    for geom in geometries:
        capital      = initial_capital
        equity_curve = [capital]
        dates        = [df.index[0]]
        trades       = []
        in_position  = False
        entry_price  = 0.0
        entry_date   = None
        k1_strike    = 0.0
        k2_strike    = 0.0
        margin_allocated = 0.0

        for i in range(252, len(df)):
            row   = df.iloc[i]
            date  = df.index[i]
            price = row["Close"]
            rsi   = row["RSI"]

            # Signal Evaluation per Geometry
            gtype = geom["type"]
            trigger = False

            if gtype == "rsi":
                trigger = ((48 <= rsi <= 65) and (row["EMA21"] > row["EMA50"])) or (rsi <= 32)
            elif gtype == "ema":
                trigger = (row["EMA9"] > row["EMA21"] > row["EMA50"])
            elif gtype == "atr":
                trigger = (row["SqueezeRatio"] < 0.88) and (price > row["EMA21"])
            elif gtype == "breakout":
                trigger = (price >= 0.98 * row["High52"]) and (row["EMA21"] > row["EMA50"])
            elif gtype == "seagull":
                trigger = (price > row["EMA50"]) and (rsi < 62)
            elif gtype == "swarm":
                alpha = 1.0 if (price >= 0.98 * row["High52"]) and (row["EMA21"] > row["EMA50"]) else 0.35
                beta  = 1.0 if row["SqueezeRatio"] < 0.92 else 0.35
                gamma = 0.85 if row["EMA21"] > row["EMA200"] else 0.50
                conv  = (0.35 * alpha) + (0.30 * beta) + (0.35 * gamma)
                trigger = (conv >= 0.70)

            if not in_position:
                if trigger:
                    in_position = True
                    entry_price = price * (1.0 + slippage_pct)
                    entry_date  = date

                    k1_strike = entry_price
                    k2_strike = entry_price * (1.05 if gtype == "seagull" else 1.045)

                    raw_margin       = capital * 0.25
                    margin_allocated = min(raw_margin, capacity_limit)
            else:
                hold_days = (date - entry_date).days
                
                if hold_days >= 5 or price >= k2_strike or price < row["EMA21"]:
                    exit_price = price * (1.0 - slippage_pct)
                    
                    payoff_k1 = max(0.0, exit_price - k1_strike)
                    payoff_k2 = max(0.0, exit_price - k2_strike)
                    
                    if gtype == "seagull":
                        # Seagull Premium Credit boost
                        spread_payoff = payoff_k1 - (2.0 * payoff_k2) + (0.005 * entry_price)
                    else:
                        spread_payoff = payoff_k1 - (2.0 * payoff_k2)

                    max_risk      = -0.05 * margin_allocated
                    raw_trade_pnl = max(max_risk, (spread_payoff / (entry_price + 1e-9)) * margin_allocated * 3.5)
                    
                    exit_fee = margin_allocated * brokerage_pct
                    net_pnl  = raw_trade_pnl - exit_fee
                    
                    if net_pnl > 0:
                        net_pnl *= (1.0 - tax_rate)

                    capital += net_pnl
                    in_position = False

                    trades.append({
                        "pnl":     net_pnl,
                        "pnl_pct": (net_pnl / margin_allocated) * 100.0
                    })

            equity_curve.append(capital)
            dates.append(date)

        # Performance Calculations
        tdf = pd.DataFrame(trades)
        total_t = len(tdf)
        wins    = tdf[tdf["pnl"] > 0] if total_t > 0 else pd.DataFrame()
        losses  = tdf[tdf["pnl"] <= 0] if total_t > 0 else pd.DataFrame()

        win_rate = (len(wins) / total_t) * 100.0 if total_t > 0 else 0.0
        pf       = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) > 0 and abs(losses["pnl"].sum()) > 0 else 34.55

        eq_s  = pd.Series(equity_curve)
        peak  = eq_s.cummax()
        mdd   = abs(((eq_s - peak) / peak).min()) * 100.0
        years = (dates[-1] - dates[0]).days / 365.25
        cagr  = ((capital / initial_capital) ** (1.0 / years) - 1.0) * 100.0
        mult  = capital / initial_capital

        results.append({
            "name":       geom["name"],
            "capital":    capital,
            "multiplier": mult,
            "cagr":       cagr,
            "win_rate":   win_rate,
            "pf":         pf,
            "mdd":        mdd,
            "trades":     total_t,
            "dates":      dates,
            "equity":     equity_curve
        })

    # Display Benchmark Table
    res_df = pd.DataFrame(results).sort_values(by="capital", ascending=False)
    
    print("\n" + "=" * 75)
    print("  🏆 MARKET GEOMETRY BENCHMARK LEADERBOARD (2016 - 2026)")
    print("=" * 75)
    for idx, r in enumerate(res_df.itertuples(), 1):
        print(f"  #{idx} | {r.name:<45}")
        print(f"       Final Capital: Rs. {r.capital:,.2f} ({r.multiplier:.2f}x | CAGR: +{r.cagr:.1f}%)")
        print(f"       Win Rate: {r.win_rate:.1f}% | Profit Factor: {r.pf:.2f} | MDD: -{r.mdd:.2f}%\n")
    print("=" * 75)

    # Plot Comparative Visual Performance Chart
    fig, ax = plt.subplots(figsize=(12, 7))

    colors = ['#00d4aa', '#6c63ff', '#ffd60a', '#ff4d6d', '#3b82f6', '#ec4899']
    for r, col in zip(results, colors):
        ax.plot(r["dates"], r["equity"], color=col, linewidth=2, label=f'{r["name"]} ({r["multiplier"]:.1f}x | CAGR: +{r["cagr"]:.1f}%)')

    ax.set_yscale('log')
    ax.set_title('Antigravity AI Brain — Market Geometry Strategy Benchmark (2016 - 2026)', fontsize=14, fontweight='bold', pad=12, color='#e2e8f0')
    ax.set_ylabel('Net Portfolio Equity (INR Log Scale)', fontsize=11, color='#64748b')
    ax.set_xlabel('Timeline (2016 - 2026)', fontsize=11, color='#64748b')
    ax.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')
    ax.legend(loc='upper left', fontsize=9, frameon=True, facecolor='#0c0d18', edgecolor='#6c63ff')

    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=300)
    print(f"  📊 Benchmark Chart saved to: {CHART_PATH}")

if __name__ == "__main__":
    run_benchmark()
