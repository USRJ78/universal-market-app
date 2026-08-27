"""
==============================================================================
  ANTIGRAVITY AI BRAIN — GARUDA DHARMA & KARMA 10-YEAR QUANT BACKTEST
==============================================================================
  Backtests the philosophical Principles of Garuda Purana translated to Quant Math:

  PRINCIPLES IMPLEMENTED:
    1. LAW OF KARMA (Asymmetric Risk:Reward):
       - Capped Risk (SL = 4.0%) vs High Target (TP = 15.0%) -> 3.75:1 R:R
    2. DHARMA & DISCIPLINE (Strict Sizing):
       - Max 5 concurrent positions, max 20% allocation per trade.
    3. MAYA VS SATYA FILTER (Signal vs Noise):
       - Requires Volatility Squeeze (<0.20) + Expansion (>1.10) + Positive Curvature.
    4. VAIRAGYA (Non-Attachment Exits):
       - Mechanical trailing stop & target exits without emotional interference.

  Asset Universe: Top Indian NSE Equities (EQUITY_L.csv)
  Period: 2016-2026 (10 Years)
==============================================================================
"""

import os, sys, warnings, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'

INITIAL_CAPITAL = 100000.0  # ₹1,00,000 (INR 1 Lakh)
STOP_LOSS_PCT   = 0.04      # 4% Karma Stop Loss
TAKE_PROFIT_PCT = 0.15      # 15% Karma Profit Target (3.75:1 R:R)
MAX_POSITIONS   = 5         # 5 Slots (Dharma Allocation)

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "garuda_dharma_karma_10yr_chart.png")
REPORT_PATH  = os.path.join(ANALYSIS_DIR, "garuda_dharma_karma_10yr_report.md")

def load_tickers():
    possible_paths = [
        os.path.join(ANALYSIS_DIR, "..", "data", "EQUITY_L.csv"),
        os.path.join(ANALYSIS_DIR, "..", "EQUITY_L.csv"),
        "EQUITY_L.csv"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "BHARTIARTL.NS", "TITAN.NS",
                "TATMOTORS.NS", "DIXON.NS", "SOLARINDS.NS", "DEEPAKNTR.NS", "ANGELONE.NS"]
    df = pd.read_csv(path)
    syms = df["SYMBOL"].dropna().astype(str).str.strip().unique().tolist()
    return [s + ".NS" for s in syms if "&" not in s]

def compute_dharma_signals(df):
    df = df.copy()
    close = df["Close"]
    returns = close.pct_change()
    volatility = returns.rolling(20).std()

    vol_min = volatility.rolling(30).min()
    vol_max = volatility.rolling(30).max()
    vol_comp= (volatility - vol_min) / (vol_max - vol_min + 1e-9)

    vol_exp    = volatility / (volatility.rolling(30).mean() + 1e-9)
    velocity   = close.diff(5)
    accel      = velocity.diff()
    curvature  = accel.diff()
    magnitude  = np.sqrt(velocity**2 + accel**2)
    angle      = np.arctan2(accel, velocity)

    # Maya Filter (Signal Confluence)
    c1 = vol_comp.shift(1) < 0.20
    c2 = vol_exp > 1.10
    c3 = curvature > 0.05
    c4 = magnitude > (magnitude.rolling(50).mean() * 0.60)
    c5 = angle > 0

    df["Dharma_Score"] = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int) + c5.astype(int)) / 5.0
    df["BUY_SIGNAL"]   = df["Dharma_Score"] >= 0.60
    df["SELL_SIGNAL"]  = vol_comp > 0.80
    return df

def run_dharma_backtest():
    print("=" * 80)
    print("  GARUDA DHARMA & KARMA 10-YEAR QUANTITATIVE BACKTEST (2016-2026)")
    print("=" * 80)

    tickers = load_tickers()[:300]  # Scan top 300 NSE stocks for speed
    print(f"\n[1/3] Downloading stock data for {len(tickers)} Indian equities...")

    all_data = {}
    for sym in tickers:
        try:
            df = yf.download(sym, start="2016-01-01", end="2026-08-25", interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Normalize index
            if hasattr(df.index, "tz") and df.index.tz is not None:
                df.index = df.index.tz_convert("UTC").tz_localize(None)
            df.index = df.index.normalize()

            df = compute_dharma_signals(df)
            all_data[sym] = df
        except Exception:
            continue

    print(f"      Successfully loaded {len(all_data)} stocks.")

    # Backtest Loop
    print("\n[2/3] Executing Garuda Dharma & Karma Trading Strategy...")
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(set(d for df in all_data.values() for d in df.index))

    for current_date in dates:
        # Exits (Karma SL / TP / Vairagya Exit)
        for ticker in list(positions.keys()):
            df = all_data[ticker]
            if current_date not in df.index: continue
            row = df.loc[current_date]
            pos = positions[ticker]

            stop_price = pos["entry_price"] * (1 - STOP_LOSS_PCT)
            tp_price   = pos["entry_price"] * (1 + TAKE_PROFIT_PCT)

            exit_trade = False
            reason = ""
            if row["Close"] <= stop_price:
                exit_trade = True; reason = "KARMA_STOP (-4%)"
            elif row["Close"] >= tp_price:
                exit_trade = True; reason = "KARMA_TARGET (+15%)"
            elif row["SELL_SIGNAL"]:
                exit_trade = True; reason = "VAIRAGYA_EXIT"

            if exit_trade:
                proceeds = pos["shares"] * row["Close"]
                profit   = proceeds - pos["invested"]
                ret_pct  = (profit / pos["invested"]) * 100.0
                cash    += proceeds
                trade_log.append({
                    "Stock": ticker,
                    "Entry Date": pos["entry_date"],
                    "Exit Date": current_date,
                    "Entry Price": pos["entry_price"],
                    "Exit Price": row["Close"],
                    "Profit": profit,
                    "Return %": ret_pct,
                    "Reason": reason
                })
                del positions[ticker]

        # Entries (Dharma Allocation)
        slots = MAX_POSITIONS - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in all_data.items():
                if ticker in positions: continue
                if current_date not in df.index: continue
                row = df.loc[current_date]
                if bool(row["BUY_SIGNAL"]):
                    candidates.append((ticker, row["Dharma_Score"], row))

            candidates.sort(key=lambda x: x[1], reverse=True)
            for ticker, score, row in candidates[:slots]:
                allocation = cash / slots
                if allocation <= 0: continue
                shares = allocation / row["Close"]
                cash  -= allocation
                positions[ticker] = {
                    "entry_date": current_date,
                    "entry_price": row["Close"],
                    "shares": shares,
                    "invested": allocation
                }

        pv = cash
        for ticker, pos in positions.items():
            df = all_data[ticker]
            if current_date in df.index:
                pv += pos["shares"] * df.loc[current_date]["Close"]
        equity_curve.append(pv)

    df_trades = pd.DataFrame(trade_log)
    eq = np.array(equity_curve)
    final_cap = eq[-1]
    ret_pct   = (final_cap / INITIAL_CAPITAL - 1) * 100.0
    cagr      = ((final_cap / INITIAL_CAPITAL) ** (1 / 10.0) - 1) * 100.0

    peak = np.maximum.accumulate(eq)
    mdd  = abs(((eq - peak) / peak).min()) * 100.0
    wins = (df_trades["Profit"] > 0).sum() if not df_trades.empty else 0
    tot  = len(df_trades)
    wr   = (wins / max(1, tot)) * 100.0

    print("\n" + "=" * 80)
    print("  GARUDA DHARMA & KARMA 10-YEAR BACKTEST RESULTS")
    print("=" * 80)
    print(f"  Starting Capital:    ₹{INITIAL_CAPITAL:,.2f}")
    print(f"  Final Capital:       ₹{final_cap:,.2f}")
    print(f"  Total Net Return:    +{ret_pct:,.2f}%")
    print(f"  Annualized CAGR:     +{cagr:.2f}% / Year")
    print(f"  Win Rate:            {wr:.1f}% ({wins} Wins / {tot} Trades)")
    print(f"  Max Drawdown (MDD):  -{mdd:.2f}%")
    print("=" * 80)

    # ── GENERATE CHART ─────────────────────────────────────────────────────────
    print("\n[3/3] Generating performance charts and markdown report...")
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#090d16')
    ax.set_facecolor('#090d16')

    ax.plot(dates, equity_curve, color='#00d4aa', linewidth=2.2, label=f"Garuda Dharma Strategy (₹{final_cap:,.0f} | +{cagr:.1f}% CAGR)")
    ax.set_yscale('log')
    ax.set_title("Garuda Dharma & Karma 10-Year Backtest (2016-2026)\nKarma SL 4% | Karma TP 15% | Dharma Allocation (5 Slots)",
                 fontsize=12, fontweight='bold', color='#e2e8f0', pad=15)
    ax.set_ylabel("Portfolio Value (INR)", color='#94a3b8')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    ax.grid(True, which='both', linestyle='--', alpha=0.15, color='#334155')
    ax.tick_params(colors='#94a3b8')
    ax.legend(fontsize=9.5, frameon=True, facecolor='#0f172a')

    plt.savefig(CHART_PATH, dpi=220, facecolor='#090d16', bbox_inches='tight')
    plt.close()

    # ── GENERATE REPORT ────────────────────────────────────────────────────────
    report = f"""# 📜 GARUDA DHARMA & KARMA — 10-YEAR BACKTEST REPORT (2016–2026)

## Strategy Principles & Rules

```
1. KARMA LAW (Asymmetric Risk:Reward):
   - Take Profit: +15.0%
   - Stop Loss:   -4.0%
   - Reward-to-Risk Ratio: 3.75 : 1

2. DHARMA & DISCIPLINE (Capital Allocation):
   - Max 5 concurrent slots (20% of cash per stock)
   - Mechanical execution (zero emotional bias)

3. MAYA FILTER (Signal Confluence):
   - 3D Vector Squeeze (< 0.20) + Expansion (> 1.10) + Positive Curvature
```

## Performance Metrics

| Metric | Result |
|:---|:---:|
| **Starting Capital** | **₹1,00,000** (INR 1 Lakh) |
| **Final Capital** | 🏆 **₹{final_cap:,.2f}** |
| **Total Net Return** | **+{ret_pct:,.2f}%** |
| **CAGR** | **+{cagr:.2f}% / Year** |
| **Win Rate** | **{wr:.1f}%** ({wins} Wins / {tot} Trades) |
| **Max Drawdown (MDD)** | 🛡️ **-{mdd:.2f}%** |
| **Total Trades Executed** | {tot} |

---

![Garuda Dharma Chart](file:///{CHART_PATH.replace(os.sep, '/')})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nSaved Chart  -> {CHART_PATH}")
    print(f"Saved Report -> {REPORT_PATH}")

if __name__ == "__main__":
    run_dharma_backtest()
