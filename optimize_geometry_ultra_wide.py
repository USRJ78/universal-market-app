"""
==============================================================================
  ANTIGRAVITY AI BRAIN — ULTRA-WIDE GEOMETRY HYPER-PARAMETER OPTIMIZER
==============================================================================
  Unrestricted, wide-spectrum parameter optimization for geometry.ipynb.
  
  SEARCH SPECTRUM:
    - Stop Loss:       2% to 20%  (step 1%)
    - Take Profit:     10% to 100% (step 5%)
    - Max Slots:       2 to 30 positions
    - Vol Window:      10 to 50 days
    - Comp Window:     15 to 60 days
    - Vector Step:     2 to 10 days
    - Score Gate:      40% to 90% (0.40 to 0.90)

  Runs 500 Random Search parameter profiles on pre-cached market data in RAM.
==============================================================================
"""

import os, sys, warnings, time, random
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000
LOOKBACK_PERIOD = "10y"
MAX_WORKERS     = 20
TOTAL_TRIALS    = 500  # 500 wide-spectrum trial combinations

def load_nse_tickers():
    possible_paths = [
        "data/EQUITY_L.csv", "EQUITY_L.csv",
        r"C:\Users\USER\OneDrive\Documents\universal-market-app\data\EQUITY_L.csv",
        r"C:\Users\USER\OneDrive\Documents\universal-market-app\EQUITY_L.csv"
    ]
    path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not path:
        raise FileNotFoundError("EQUITY_L.csv not found")

    df = pd.read_csv(path)
    symbols = df["SYMBOL"].dropna().astype(str).str.strip().unique().tolist()
    return [s + ".NS" for s in symbols if "&" not in s]

def normalize_index(df):
    idx = df.index
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    df.index = idx.normalize()
    return df

def fetch_stock_raw(ticker):
    try:
        df = yf.download(ticker, period=LOOKBACK_PERIOD, progress=False)
        if df.empty or len(df) < 200:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = normalize_index(df)
        return ticker, df
    except Exception:
        return None

def compute_geometry_signals(df, vol_win, comp_win, vec_win, score_thresh):
    df = df.copy()
    df["Returns"]    = df["Close"].pct_change()
    df["Volatility"] = df["Returns"].rolling(vol_win).std()
    
    vol_min = df["Volatility"].rolling(comp_win).min()
    vol_max = df["Volatility"].rolling(comp_win).max()
    df["Vol_Compression"] = (df["Volatility"] - vol_min) / (vol_max - vol_min + 1e-9)

    df["Vol_Expansion"]    = df["Volatility"] / (df["Volatility"].rolling(comp_win).mean() + 1e-9)
    df["Velocity"]         = df["Close"].diff(vec_win)
    df["Acceleration"]     = df["Velocity"].diff()
    df["Curvature"]        = df["Acceleration"].diff()
    df["Vector_Magnitude"] = np.sqrt(df["Velocity"]**2 + df["Acceleration"]**2)
    df["Vector_Angle"]     = np.arctan2(df["Acceleration"], df["Velocity"])

    c1 = df["Vol_Compression"].shift(1) < 0.20
    c2 = df["Vol_Expansion"] > 1.10
    c3 = df["Curvature"] > 0.05
    c4 = df["Vector_Magnitude"] > (df["Vector_Magnitude"].rolling(50).mean() * 0.60)
    c5 = df["Vector_Angle"] > 0

    df["Geometry_Score"] = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int) + c5.astype(int)) / 5.0
    df["BUY_SIGNAL"]     = df["Geometry_Score"] >= score_thresh
    df["SELL_SIGNAL"]    = df["Vol_Compression"] > 0.80
    return df

def run_backtest_fast(all_data, stop_loss_pct, take_profit_pct, max_positions):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(set(d for df in all_data.values() for d in df.index))

    for current_date in dates:
        # Exits
        for ticker in list(positions.keys()):
            df = all_data[ticker]
            if current_date not in df.index: continue
            row = df.loc[current_date]
            pos = positions[ticker]
            stop_price = pos["entry_price"] * (1 - stop_loss_pct)
            tp_price   = pos["entry_price"] * (1 + take_profit_pct)

            exit_trade = False
            reason = ""
            if row["Close"] <= stop_price:
                exit_trade = True; reason = "STOP"
            elif row["Close"] >= tp_price:
                exit_trade = True; reason = "TARGET"
            elif row["SELL_SIGNAL"]:
                exit_trade = True; reason = "EXIT"

            if exit_trade:
                proceeds = pos["shares"] * row["Close"]
                profit   = proceeds - pos["invested"]
                cash    += proceeds
                trade_log.append(profit)
                del positions[ticker]

        # Entries
        slots = max_positions - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in all_data.items():
                if ticker in positions: continue
                if current_date not in df.index: continue
                row = df.loc[current_date]
                if bool(row["BUY_SIGNAL"]):
                    candidates.append((ticker, row["Geometry_Score"], row))

            candidates.sort(key=lambda x: x[1], reverse=True)
            for ticker, score, row in candidates[:slots]:
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
            df = all_data[ticker]
            if current_date in df.index:
                pv += pos["shares"] * df.loc[current_date]["Close"]
        equity_curve.append(pv)

    if len(equity_curve) == 0:
        return 0, 0, 0, 0, 0, 0

    eq = np.array(equity_curve)
    final_cap = eq[-1]
    ret_pct   = (final_cap / INITIAL_CAPITAL - 1) * 100.0
    peak      = np.maximum.accumulate(eq)
    mdd       = abs(((eq - peak) / peak).min()) * 100.0
    n_trades  = len(trade_log)
    win_rate  = (sum(1 for p in trade_log if p > 0) / max(1, n_trades)) * 100.0

    # Pareto Score: Rewards Win Rate + Capital Growth, penalizes Drawdown heavily
    pareto_score = win_rate + min(np.log10(max(final_cap, 1)) * 10.0, 100.0) - (mdd * 1.2)

    return final_cap, ret_pct, win_rate, mdd, pareto_score, n_trades

def generate_random_params():
    return {
        "vol_window":             random.choice([10, 14, 20, 30, 40]),
        "compression_window":     random.choice([15, 20, 30, 45, 60]),
        "vector_window":          random.choice([2, 3, 5, 7, 10]),
        "geometry_score_thresh":  random.choice([0.40, 0.50, 0.60, 0.70, 0.80]),
        "stop_loss_pct":          round(random.uniform(0.02, 0.15), 2),
        "take_profit_pct":        round(random.uniform(0.10, 0.80), 2),
        "max_positions":          random.choice([2, 3, 5, 8, 10, 15, 20, 25]),
    }

def main():
    t0 = time.time()
    print("=" * 85)
    print("  ANTIGRAVITY AI BRAIN — ULTRA-WIDE ULTRA-SPECTRUM OPTIMIZER")
    print("=" * 85)

    tickers = load_nse_tickers()
    print(f"\n[1/3] Pre-loading market data for {len(tickers)} tickers into RAM...")

    raw_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_stock_raw, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                raw_data[res[0]] = res[1]

    print(f"      Pre-loaded {len(raw_data)} active tickers in {time.time()-t0:.1f}s\n")

    print(f"[2/3] Sweeping {TOTAL_TRIALS} wide-spectrum random trials...\n")
    print(f"  {'Trial':<6} {'SL%':<5} {'TP%':<5} {'Slots':<6} {'VolW':<5} {'CompW':<6} {'VecW':<5} {'Score':<6} | {'Final Capital':>16} {'WinRate':>9} {'MaxDD':>9} {'Pareto':>8}")
    print("  " + "-" * 95)

    results = []
    
    # Cache processed signals per feature combination to avoid recalculation
    feature_cache = {}

    for i in range(1, TOTAL_TRIALS + 1):
        p = generate_random_params()
        f_key = (p["vol_window"], p["compression_window"], p["vector_window"], p["geometry_score_thresh"])
        
        if f_key not in feature_cache:
            feature_cache[f_key] = {
                t: compute_geometry_signals(df, p["vol_window"], p["compression_window"], p["vector_window"], p["geometry_score_thresh"])
                for t, df in raw_data.items()
            }

        processed_data = feature_cache[f_key]

        final_cap, ret_pct, wr, mdd, pareto, trades = run_backtest_fast(
            processed_data, p["stop_loss_pct"], p["take_profit_pct"], p["max_positions"]
        )

        res = {
            "Trial": i,
            "StopLoss": p["stop_loss_pct"],
            "TakeProfit": p["take_profit_pct"],
            "MaxSlots": p["max_positions"],
            "VolWindow": p["vol_window"],
            "CompWindow": p["compression_window"],
            "VectorWindow": p["vector_window"],
            "ScoreThresh": p["geometry_score_thresh"],
            "FinalCapital": final_cap,
            "Return%": ret_pct,
            "WinRate%": wr,
            "MaxDD%": mdd,
            "Trades": trades,
            "ParetoScore": pareto
        }
        results.append(res)

        if i % 10 == 0 or pareto > 70:
            print(f"  #{i:<5d} {p['stop_loss_pct']*100:<4.0f}% {p['take_profit_pct']*100:<4.0f}% {p['max_positions']:<6d} "
                  f"{p['vol_window']:<5d} {p['compression_window']:<6d} {p['vector_window']:<5d} {p['geometry_score_thresh']:<6.2f} | "
                  f"₹{final_cap:15,.2f} {wr:8.1f}% -{mdd:7.1f}% {pareto:7.1f}")

    df_res = pd.DataFrame(results)
    df_res.sort_values(by="ParetoScore", ascending=False, inplace=True)

    print("\n" + "=" * 100)
    print("  🏆 ABSOLUTE TOP 10 OPTIMAL PARAMETER PROFILES ACROSS ULTRA-WIDE SPECTRUM")
    print("=" * 100)
    print(f"  {'Rank':<5} {'SL%':<5} {'TP%':<5} {'Slots':<6} {'VolW':<5} {'CompW':<6} {'VecW':<5} {'Score':<6} {'Final Capital':>16} {'Return %':>12} {'Win Rate':>9} {'Max DD':>9}")
    print("  " + "-" * 98)

    for rank, (_, r) in enumerate(df_res.head(10).iterrows(), 1):
        print(f"  #{rank:<4d} {r['StopLoss']*100:<4.0f}% {r['TakeProfit']*100:<4.0f}% {r['MaxSlots']:<6.0d} "
              f"{r['VolWindow']:<5.0d} {r['CompWindow']:<6.0d} {r['VectorWindow']:<5.0d} {r['ScoreThresh']:<6.2f} "
              f"₹{r['FinalCapital']:>15,.2f} +{r['Return%']:>11,.1f}% {r['WinRate%']:>8.1f}% -{r['MaxDD%']:>8.1f}%")
    print("=" * 100)

    out_csv = "analysis/geometry_ultra_wide_optimization.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\n[3/3] Full ultra-wide search saved to: {out_csv}")
    print(f"      Total execution time: {time.time()-t0:.1f} seconds.")

if __name__ == "__main__":
    main()
