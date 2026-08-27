"""
==============================================================================
  ANTIGRAVITY AI BRAIN — ₹1 CRORE IN 1 YEAR UTBOT CONFIGURATION OPTIMIZER
==============================================================================
  Sweeps parameters to find the exact configuration that turns capital into
  ₹1,00,00,000 (INR 1 Crore) within 1 Single Year (250 Trading Days).

  Parameter Dimensions:
    - Position Slots: [2, 3, 5] (50%, 33%, 20% allocation per slot)
    - Take Profit:    [1.0%, 1.5%, 2.0%, 2.5%, 3.0%]
    - Stop Loss:      [0.5%, 1.0%, 1.5%]
==============================================================================
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000.0  # ₹1 Lakh
TARGET_CRORE    = 10000000.0 # ₹1 Crore Target
LOOKBACK_PERIOD = "1y"
MAX_WORKERS     = 20

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))

def load_top_nse_tickers():
    possible_paths = [
        os.path.join(ANALYSIS_DIR, "..", "data", "EQUITY_L.csv"),
        os.path.join(ANALYSIS_DIR, "..", "EQUITY_L.csv"),
        "EQUITY_L.csv"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "DIXON.NS", "SOLARINDS.NS"]

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
    return buy, sell

def process_single_stock(sym):
    try:
        df = yf.download(sym, period=LOOKBACK_PERIOD, interval="1d", progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        df.index = df.index.normalize()

        buy, sell = compute_utbot(df["Close"], key=2.4, atr_period=9)
        df["UT_BUY"]  = buy
        df["UT_SELL"] = sell
        return sym, df
    except Exception:
        return None

def run_1yr_simulation(stock_data, tp_pct, sl_pct, max_positions, start_cap=100000.0):
    cash = start_cap
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(set(d for df in stock_data.values() for d in df.index))

    for current_date in dates:
        # Exits
        for ticker in list(positions.keys()):
            df = stock_data[ticker]
            if current_date not in df.index: continue
            row = df.loc[current_date]
            pos = positions[ticker]

            entry_p  = pos["entry_price"]
            tp_price = entry_p * (1.0 + tp_pct)
            sl_price = entry_p * (1.0 - sl_pct)

            exit_trade = False
            exit_price = row["Close"]

            if row["High"] >= tp_price:
                exit_trade = True; exit_price = tp_price
            elif row["Low"] <= sl_price:
                exit_trade = True; exit_price = sl_price
            elif bool(row["UT_SELL"]):
                exit_trade = True; exit_price = row["Close"]

            if exit_trade:
                proceeds = pos["shares"] * exit_price
                profit   = proceeds - pos["invested"]
                cash    += proceeds
                trade_log.append(profit)
                del positions[ticker]

        # Entries
        slots = max_positions - len(positions)
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

    if len(equity_curve) == 0: return 0, 0, 0, 0, 0

    eq = np.array(equity_curve)
    final_cap = eq[-1]
    ret_pct   = (final_cap / start_cap - 1) * 100.0
    peak      = np.maximum.accumulate(eq)
    mdd       = abs(((eq - peak) / peak).min()) * 100.0
    n_trades  = len(trade_log)
    win_rate  = (sum(1 for p in trade_log if p > 0) / max(1, n_trades)) * 100.0

    return final_cap, ret_pct, win_rate, mdd, n_trades

def main():
    t0 = time.time()
    print("=" * 85)
    print("  ₹1 CRORE IN 1 YEAR UTBOT CONFIGURATION OPTIMIZER")
    print("=" * 85)

    tickers = load_top_nse_tickers()
    print(f"\n[1/3] Loading 1-year daily market data for {len(tickers)} stocks into RAM...")

    stock_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_single_stock, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                stock_data[res[0]] = res[1]

    print(f"      Loaded {len(stock_data)} active stocks in {time.time()-t0:.1f}s.")

    # Sweep Parameters
    TP_LIST    = [0.010, 0.015, 0.020, 0.025, 0.030]
    SL_LIST    = [0.005, 0.010, 0.015]
    SLOTS_LIST = [2, 3, 5]
    CAPS       = [100000.0, 200000.0, 500000.0]

    print("\n[2/3] Sweeping configurations to find ₹1 Crore in 1 Year formulas...")

    results = []
    for start_cap in CAPS:
        for slots in SLOTS_LIST:
            for tp in TP_LIST:
                for sl in SL_LIST:
                    final_cap, ret_pct, wr, mdd, trades = run_1yr_simulation(stock_data, tp, sl, slots, start_cap)
                    hit_crore = final_cap >= TARGET_CRORE
                    results.append({
                        "StartCap": start_cap,
                        "Slots": slots,
                        "Alloc%": round(100.0 / slots, 1),
                        "TP%": tp * 100,
                        "SL%": sl * 100,
                        "1YrFinalCap": final_cap,
                        "Return%": ret_pct,
                        "WinRate%": wr,
                        "MaxDD%": mdd,
                        "Trades": trades,
                        "HitCrore": hit_crore
                    })

    df_res = pd.DataFrame(results)
    df_res.sort_values(by="1YrFinalCap", ascending=False, inplace=True)

    print("\n" + "=" * 95)
    print("  🏆 TOP CONFIGURATIONS TO REACH ₹1 CRORE IN 1 YEAR")
    print("=" * 95)
    print(f"  {'Start Cap':<11} {'Slots':<6} {'Alloc%':<7} {'TP%':<6} {'SL%':<6} | {'1-Yr Final Capital':>18} {'Return %':>12} {'Win Rate':>9} {'Max DD':>9}")
    print("  " + "-" * 93)

    for rank, (_, r) in enumerate(df_res.head(10).iterrows(), 1):
        crore_badge = "🏆 (CRORE ACHIEVED!)" if r['HitCrore'] else ""
        print(f"  ₹{r['StartCap']:<10,.0f} {r['Slots']:<6.0f} {r['Alloc%']:<6.1f}% {r['TP%']:<5.1f}% {r['SL%']:<5.1f}% | "
              f"₹{r['1YrFinalCap']:>17,.2f} +{r['Return%']:>11,.1f}% {r['WinRate%']:>8.1f}% -{r['MaxDD%']:>8.1f}% {crore_badge}")

    print("=" * 95)

    out_csv = os.path.join(ANALYSIS_DIR, "crore_in_one_year_configurations.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\n[3/3] Report saved to: {out_csv}")

if __name__ == "__main__":
    main()
