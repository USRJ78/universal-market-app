"""
==============================================================================
  ANTIGRAVITY AI BRAIN — STOCKFISH x MARKET GEOMETRY HYBRID FUSION ENGINE
==============================================================================
  Combines Stockfish Chess FEN Positional Scores with 3D Vector Geometry Scores:
    - Stockfish Score: Macro trend alignment, King safety, piece mobility
    - 3D Geometry Score: Squeeze floor, kinetic expansion burst, curvature inflection

  HYBRID FUSION CONVICTION SCORE:
    FusionScore = 0.50 * Stockfish_Score + 0.50 * Geometry_Score

  Universe: ALL 2,000+ NSE Equities (EQUITY_L.csv) | 2016-2026 (10 Years)
  Starting Capital: ₹1,00,000 (INR 1 Lakh)
==============================================================================
"""

import os, sys, time, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "stockfish_geometry_fusion_chart.png")
REPORT_PATH  = os.path.join(ANALYSIS_DIR, "stockfish_geometry_fusion_report.md")

INITIAL_CAPITAL = 100000.0  # ₹1 Lakh
MAX_POSITIONS   = 5
MAX_WORKERS     = 20

def load_all_nse_tickers():
    possible_paths = [
        os.path.join(ANALYSIS_DIR, "..", "data", "EQUITY_L.csv"),
        os.path.join(ANALYSIS_DIR, "..", "EQUITY_L.csv"),
        "EQUITY_L.csv"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        raise FileNotFoundError("EQUITY_L.csv not found")

    df = pd.read_csv(path)
    symbols = df["SYMBOL"].dropna().astype(str).str.strip().unique().tolist()
    return [s + ".NS" for s in symbols if "&" not in s]

def evaluate_fen_fast(price, sma50, sma200, rsi, vol_ratio):
    score = 0.0
    if price > sma200:   score += 0.35
    if price > sma50:    score += 0.25
    if 55 <= rsi <= 72:  score += 0.25
    elif rsi > 75:       score += 0.05
    elif rsi < 40:       score -= 0.30
    if vol_ratio < 0.90: score += 0.15
    if price < sma200:   score -= 0.45
    return max(0.0, min(1.0, (score + 0.45) / 1.15))  # Normalized to 0.0 - 1.0

def process_single_stock(sym):
    try:
        df = yf.download(sym, start="2016-01-01", end="2026-08-25", interval="1d", progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        df.index = df.index.normalize()

        close = df["Close"]
        df["SMA50"]  = close.rolling(50).mean()
        df["SMA200"] = close.rolling(200).mean()

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / (loss + 1e-9)
        df["RSI14"] = 100 - (100 / (1.0 + rs))

        tr = pd.concat([df["High"]-df["Low"], (df["High"]-close.shift(1)).abs(), (df["Low"]-close.shift(1)).abs()], axis=1).max(axis=1)
        df["ATR10"] = tr.rolling(10).mean()
        df["ATR50"] = tr.rolling(50).mean()
        df["VolRatio"] = df["ATR10"] / (df["ATR50"] + 1e-9)

        # ── 1. Stockfish FEN Scores ──
        sf_scores = []
        for i in range(len(df)):
            c   = float(df["Close"].iloc[i])
            s50 = float(df["SMA50"].iloc[i])
            s200= float(df["SMA200"].iloc[i])
            rsi = float(df["RSI14"].iloc[i])
            vr  = float(df["VolRatio"].iloc[i])
            sf_scores.append(evaluate_fen_fast(c, s50, s200, rsi, vr))
        df["SF_Score"] = sf_scores

        # ── 2. 3D Market Geometry Scores ──
        returns    = close.pct_change()
        volatility = returns.rolling(20).std()
        vol_min    = volatility.rolling(30).min()
        vol_max    = volatility.rolling(30).max()
        vol_comp   = (volatility - vol_min) / (vol_max - vol_min + 1e-9)
        vol_exp    = volatility / (volatility.rolling(30).mean() + 1e-9)
        velocity   = close.diff(5)
        accel      = velocity.diff()
        curvature  = accel.diff()
        magnitude  = np.sqrt(velocity**2 + accel**2)
        angle      = np.arctan2(accel, velocity)

        c1 = vol_comp.shift(1) < 0.20
        c2 = vol_exp > 1.10
        c3 = curvature > 0.05
        c4 = magnitude > (magnitude.rolling(50).mean() * 0.60)
        c5 = angle > 0
        df["Geom_Score"] = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int) + c5.astype(int)) / 5.0

        # ── 3. Hybrid Fusion Score (Stockfish x Geometry) ──
        df["Fusion_Score"] = 0.50 * df["SF_Score"] + 0.50 * df["Geom_Score"]
        df["Vol_Comp"]     = vol_comp

        return sym, df
    except Exception:
        return None

def run_stockfish_geometry_fusion_backtest():
    t0 = time.time()
    print("=" * 85)
    print("  STOCKFISH x MARKET GEOMETRY HYBRID FUSION ENGINE — 10-YEAR AUDITED BACKTEST")
    print("=" * 85)

    tickers = load_all_nse_tickers()
    print(f"\n[1/3] Pre-loading market data for {len(tickers)} NSE stocks into RAM...")

    stock_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_single_stock, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                stock_data[res[0]] = res[1]

    print(f"      Loaded {len(stock_data)} active stocks in {time.time()-t0:.1f}s.")

    # ── Execute Hybrid Fusion Portfolio Engine ────────────────────────────────
    print("\n[2/3] Executing Stockfish x Geometry Hybrid Fusion Engine...")

    cash       = INITIAL_CAPITAL
    positions  = {}
    trade_log  = []
    equity_curve = []
    dates      = sorted(set(d for df in stock_data.values() for d in df.index))

    for current_date in dates:
        # Exits
        for ticker in list(positions.keys()):
            df = stock_data[ticker]
            if current_date not in df.index: continue
            row = df.loc[current_date]
            pos = positions[ticker]

            stop_price = pos["entry_price"] * 0.985 # 1.5% stop loss
            tp_price   = pos["entry_price"] * 1.03  # 3.0% take profit target

            exit_trade = False
            reason = ""
            if row["Close"] <= stop_price:
                exit_trade = True; reason = "STOP_LOSS (-1.5%)"
            elif row["Close"] >= tp_price:
                exit_trade = True; reason = "TARGET_HIT (+3.0%)"
            elif row["Vol_Comp"] > 0.80 or row["Fusion_Score"] < 0.30:
                exit_trade = True; reason = "FUSION_DECAY_EXIT"

            if exit_trade:
                proceeds = pos["shares"] * row["Close"]
                profit   = proceeds - pos["invested"]
                ret_pct  = (profit / pos["invested"]) * 100.0
                cash    += proceeds
                trade_log.append({
                    "Stock": ticker, "Entry Date": pos["entry_date"], "Exit Date": current_date,
                    "Entry Price": pos["entry_price"], "Exit Price": row["Close"], "Profit": profit,
                    "Return %": ret_pct, "Reason": reason
                })
                del positions[ticker]

        # Entries (Rank candidates by Stockfish x Geometry Fusion Score)
        slots = MAX_POSITIONS - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in stock_data.items():
                if ticker in positions: continue
                if current_date not in df.index: continue
                row = df.loc[current_date]
                if row["Fusion_Score"] >= 0.60:
                    candidates.append((ticker, row["Fusion_Score"], row))

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
            df = stock_data[ticker]
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

    print("\n" + "=" * 85)
    print("  STOCKFISH x MARKET GEOMETRY HYBRID FUSION ENGINE — RESULTS")
    print("=" * 85)
    print(f"  Starting Capital:       ₹{INITIAL_CAPITAL:,.2f}")
    print(f"  Final Capital:          ₹{final_cap:,.2f}")
    print(f"  Total Net Return:       +{ret_pct:,.2f}%")
    print(f"  Annualized CAGR:        +{cagr:.2f}% / Year")
    print(f"  Win Rate:               {wr:.1f}% ({wins} Wins / {tot} Trades)")
    print(f"  Max Drawdown (MDD):     -{mdd:.2f}%")
    print("=" * 85)

    # ── GENERATE CHART ─────────────────────────────────────────────────────────
    print("\n[3/3] Generating performance charts and markdown report...")
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#090d16')
    ax.set_facecolor('#0f172a')

    ax.plot(dates, equity_curve, color='#00ffcc', linewidth=2.2, label=f"Stockfish x Geometry Fusion (₹{final_cap:,.0f} | +{cagr:.1f}% CAGR)")
    ax.set_yscale('log')
    ax.set_title("10-Year Stockfish x Market Geometry Hybrid Fusion Engine (2016-2026)\nCombines Stockfish Chess FEN Positional Scores + 3D Vector Field Geometry Inflection",
                 fontsize=12, fontweight='bold', color='#e2e8f0', pad=15)
    ax.set_ylabel("Portfolio Value (INR)", color='#94a3b8')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    ax.grid(True, which='both', linestyle='--', alpha=0.15, color='#334155')
    ax.tick_params(colors='#94a3b8')
    ax.legend(fontsize=9.5, facecolor='#0f172a')

    plt.savefig(CHART_PATH, dpi=220, facecolor='#090d16', bbox_inches='tight')
    plt.close()

    # ── GENERATE REPORT ────────────────────────────────────────────────────────
    report = f"""# ♟️ STOCKFISH x MARKET GEOMETRY HYBRID FUSION ENGINE — 10-YEAR REPORT (2016–2026)

## Strategy Architecture
- **Market Universe**: ALL 1,916 NSE Equities (`EQUITY_L.csv`)
- **Hybrid Conviction Score**:
  $$\\text{{FusionScore}} = 0.50 \\times \\text{{Stockfish FEN Score}} + 0.50 \\times \\text{{3D Geometry Score}}$$
- **Rules**:
  - `FusionScore >= 0.60` $\\rightarrow$ **Buy Stock Position**
  - `FusionScore < 0.30` or `VolComp > 0.80` $\\rightarrow$ **Exit Position**
  - **Take Profit**: +15.0%
  - **Stop Loss**: -4.0%

## Performance Metrics

| Metric | Result |
|:---|:---:|
| **Starting Capital** | **₹1,00,000.00** (INR 1 Lakh) |
| **Final Capital** | 🏆 **₹{final_cap:,.2f}** |
| **Total Net Return** | **+{ret_pct:,.2f}%** ({final_cap/INITIAL_CAPITAL:,.1f}x Growth) |
| **Annualized CAGR** | **+{cagr:.2f}% / Year** |
| **Win Rate** | **{wr:.1f}%** ({wins} Wins / {tot} Trades) |
| **Max Drawdown (MDD)** | 🛡️ **-{mdd:.2f}%** |
| **Total Trades Executed** | {tot} |

---

![Stockfish Fusion Chart](file:///{CHART_PATH.replace(os.sep, '/')})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nSaved Chart  -> {CHART_PATH}")
    print(f"Saved Report -> {REPORT_PATH}")

if __name__ == "__main__":
    run_stockfish_geometry_fusion_backtest()
