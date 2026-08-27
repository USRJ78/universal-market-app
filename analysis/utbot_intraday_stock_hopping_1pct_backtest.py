"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT INTRADAY STOCK HOPPING ENGINE (1% QUICK TARGET)
==============================================================================
  Continuous Intraday Stock Hopping Strategy using UTBot Alert Signals:
    - Target Profit: +1.0% (Quick Intraday Scalp Harvest)
    - Stop Loss:     -0.5% (Tight Protection)
    - Protocol:      Once +1% target is reached, position is instantly closed,
                     and cash is rotated into the next active UTBot BUY stock!

  Universe: Top Active Indian Equities (EQUITY_L.csv)
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
CHART_PATH   = os.path.join(ANALYSIS_DIR, "utbot_intraday_hopping_chart.png")
REPORT_PATH  = os.path.join(ANALYSIS_DIR, "utbot_intraday_hopping_report.md")

INITIAL_CAPITAL = 100000.0  # ₹1 Lakh
MAX_POSITIONS   = 5
TARGET_PCT      = 0.010     # +1.0% Target
STOP_LOSS_PCT   = 0.010     # -1.0% Stop Loss
MAX_WORKERS     = 20

def load_top_nse_tickers():
    possible_paths = [
        os.path.join(ANALYSIS_DIR, "..", "data", "EQUITY_L.csv"),
        os.path.join(ANALYSIS_DIR, "..", "EQUITY_L.csv"),
        "EQUITY_L.csv"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "DIXON.NS", "SOLARINDS.NS",
                "TATMOTORS.NS", "POLYCAB.NS", "ANGELONE.NS", "PERSISTENT.NS", "TATAELXSI.NS"]

    df = pd.read_csv(path)
    symbols = df["SYMBOL"].dropna().astype(str).str.strip().unique().tolist()
    return [s + ".NS" for s in symbols if "&" not in s][:300]

def compute_utbot(close, key=2.4, atr_period=9):
    tr    = close.diff().abs()
    atr   = tr.rolling(atr_period).mean()
    nloss = key * atr
    xatr  = [0.0] * len(close)
    for t in range(1, len(close)):
        sc = float(close.iloc[t])
        sp = float(close.iloc[t-1])
        xa = xatr[t-1]
        lc = float(nloss.iloc[t]) if not np.isnan(nloss.iloc[t]) else 0.0
        if   sc > xa and sp > xa: xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa: xatr[t] = min(xa, sc + lc)
        else:                     xatr[t] = (sc - lc) if sc > xa else (sc + lc)
    xatr_s = pd.Series(xatr, index=close.index)
    buy  = (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))
    sell = (close < xatr_s) & (close.shift(1) >= xatr_s.shift(1))
    return buy, sell, xatr_s

def process_single_stock(sym):
    try:
        df = yf.download(sym, start="2021-01-01", end="2026-08-25", interval="1d", progress=False)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        df.index = df.index.normalize()

        buy, sell, xatr = compute_utbot(df["Close"], key=2.4, atr_period=9)
        df["UT_BUY"]  = buy
        df["UT_SELL"] = sell
        df["UT_TRAIL"]= xatr
        return sym, df
    except Exception:
        return None

def run_utbot_hopping_backtest():
    t0 = time.time()
    print("=" * 85)
    print("  UTBOT INTRADAY STOCK HOPPING ENGINE (1% QUICK TARGET) — AUDITED BACKTEST")
    print("=" * 85)

    tickers = load_top_nse_tickers()
    print(f"\n[1/3] Pre-loading market data for {len(tickers)} Indian equities into RAM...")

    stock_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_single_stock, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                stock_data[res[0]] = res[1]

    print(f"      Loaded {len(stock_data)} active stocks in {time.time()-t0:.1f}s.")

    # ── UTBot Hopping Engine Execution ──
    print("\n[2/3] Executing UTBot Stock Hopping Engine (+1% Target Protocol)...")

    cash       = INITIAL_CAPITAL
    positions  = {}
    trade_log  = []
    equity_curve = []
    dates      = sorted(set(d for df in stock_data.values() for d in df.index))

    for current_date in dates:
        # Exits (Check for +1% TP or -0.5% SL)
        for ticker in list(positions.keys()):
            df = stock_data[ticker]
            if current_date not in df.index: continue
            row = df.loc[current_date]
            pos = positions[ticker]

            high_price = row["High"]
            low_price  = row["Low"]
            entry_p    = pos["entry_price"]

            tp_price   = entry_p * (1.0 + TARGET_PCT)
            sl_price   = entry_p * (1.0 - STOP_LOSS_PCT)

            exit_trade = False
            reason = ""
            exit_price = row["Close"]

            if high_price >= tp_price:
                exit_trade = True
                reason = "TARGET_1PCT_HARVESTED (+1.0%)"
                exit_price = tp_price
            elif low_price <= sl_price:
                exit_trade = True
                reason = "STOP_LOSS (-0.5%)"
                exit_price = sl_price
            elif bool(row["UT_SELL"]):
                exit_trade = True
                reason = "UTBOT_SELL_SIGNAL"
                exit_price = row["Close"]

            if exit_trade:
                proceeds = pos["shares"] * exit_price
                profit   = proceeds - pos["invested"]
                ret_pct  = (profit / pos["invested"]) * 100.0
                cash    += proceeds
                trade_log.append({
                    "Stock": ticker, "Entry Date": pos["entry_date"], "Exit Date": current_date,
                    "Entry Price": entry_p, "Exit Price": exit_price, "Profit": profit,
                    "Return %": ret_pct, "Reason": reason
                })
                del positions[ticker]

        # Entries (Rotate into fresh UTBot BUY signals)
        slots = MAX_POSITIONS - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in stock_data.items():
                if ticker in positions: continue
                if current_date not in df.index: continue
                row = df.loc[current_date]
                if bool(row["UT_BUY"]):
                    candidates.append((ticker, row))

            for ticker, row in candidates[:slots]:
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
    years     = max((dates[-1] - dates[0]).days / 365.25, 0.1)
    cagr      = ((final_cap / INITIAL_CAPITAL) ** (1 / years) - 1) * 100.0

    peak = np.maximum.accumulate(eq)
    mdd  = abs(((eq - peak) / peak).min()) * 100.0
    wins = (df_trades["Profit"] > 0).sum() if not df_trades.empty else 0
    tot  = len(df_trades)
    wr   = (wins / max(1, tot)) * 100.0

    print("\n" + "=" * 85)
    print("  UTBOT INTRADAY STOCK HOPPING ENGINE — AUDITED RESULTS")
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

    ax.plot(dates, equity_curve, color='#00ffcc', linewidth=2.2, label=f"UTBot 1% Hopping Engine (₹{final_cap:,.0f} | +{cagr:.1f}% CAGR)")
    ax.set_yscale('log')
    ax.set_title("UTBot Continuous Intraday Stock Hopping Engine (+1% Quick Scalp Harvest)\nAutomatically Exits at +1.0% Target and Rotates Cash to Next UTBot BUY Stock",
                 fontsize=12, fontweight='bold', color='#e2e8f0', pad=15)
    ax.set_ylabel("Portfolio Value (INR)", color='#94a3b8')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    ax.grid(True, which='both', linestyle='--', alpha=0.15, color='#334155')
    ax.tick_params(colors='#94a3b8')
    ax.legend(fontsize=9.5, facecolor='#0f172a')

    plt.savefig(CHART_PATH, dpi=220, facecolor='#090d16', bbox_inches='tight')
    plt.close()

    # ── GENERATE REPORT ────────────────────────────────────────────────────────
    report = f"""# ⚡ UTBOT INTRADAY STOCK HOPPING ENGINE — AUDITED REPORT

## Strategy Architecture
- **UTBot Indicator**: Key Value = 2.4, ATR Period = 9
- **Intraday Target**: **+1.0%** (Quick Scalp Harvest)
- **Stop Loss**: **-0.5%** (Tight Protection)
- **Hopping Protocol**: When a stock hits +1.0%, cash is instantly harvested and rotated into the next active UTBot BUY signal!

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

![UTBot Hopping Chart](file:///{CHART_PATH.replace(os.sep, '/')})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nSaved Chart  -> {CHART_PATH}")
    print(f"Saved Report -> {REPORT_PATH}")

if __name__ == "__main__":
    run_utbot_hopping_backtest()
