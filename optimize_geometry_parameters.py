"""
==============================================================================
  ANTIGRAVITY AI BRAIN — GEOMETRY ENGINE HYPER-PARAMETER OPTIMIZER
==============================================================================
  Optimizes geometry.ipynb parameters to find the exact combination that:
    1. Maximizes Final Capital / Return %
    2. Maximizes Win Rate %
    3. Minimizes Max Drawdown %

  Pre-downloads stock data ONCE to RAM for hyper-fast grid evaluation.
==============================================================================
"""

import os, sys, warnings, time
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000
LOOKBACK_PERIOD = "10y"
MAX_WORKERS = 20

# ── SEARCH GRID ───────────────────────────────────────────────────────────────
PARAM_GRID = {
    "STOP_LOSS_PCT":             [0.04, 0.05, 0.06, 0.08],
    "TAKE_PROFIT_PCT":           [0.15, 0.20, 0.25, 0.30],
    "MAX_POSITIONS":             [5, 10, 15],
    "geometry_score_threshold":  [0.60, 0.80],
}

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

def fetch_raw_stock(ticker):
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

def compute_signals_fast(df, score_thresh):
    df = df.copy()
    df["Returns"] = df["Close"].pct_change()
    df["Volatility"] = df["Returns"].rolling(20).std()
    
    vol_min = df["Volatility"].rolling(30).min()
    vol_max = df["Volatility"].rolling(30).max()
    df["Vol_Compression"] = (df["Volatility"] - vol_min) / (vol_max - vol_min + 1e-9)

    df["Vol_Expansion"] = df["Volatility"] / (df["Volatility"].rolling(30).mean() + 1e-9)
    df["Velocity"] = df["Close"].diff(5)
    df["Acceleration"] = df["Velocity"].diff()
    df["Curvature"] = df["Acceleration"].diff()
    df["Vector_Magnitude"] = np.sqrt(df["Velocity"]**2 + df["Acceleration"]**2)
    df["Vector_Angle"] = np.arctan2(df["Acceleration"], df["Velocity"])

    c1 = df["Vol_Compression"].shift(1) < 0.20
    c2 = df["Vol_Expansion"] > 1.10
    c3 = df["Curvature"] > 0.05
    c4 = df["Vector_Magnitude"] > (df["Vector_Magnitude"].rolling(50).mean() * 0.60)
    c5 = df["Vector_Angle"] > 0

    df["Geometry_Score"] = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int) + c5.astype(int)) / 5.0
    df["BUY_SIGNAL"]     = df["Geometry_Score"] >= score_thresh
    df["SELL_SIGNAL"]    = df["Vol_Compression"] > 0.80
    return df

def run_fast_backtest(all_processed_data, stop_loss_pct, take_profit_pct, max_positions):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(set(d for df in all_processed_data.values() for d in df.index))

    for current_date in dates:
        # Exits
        for ticker in list(positions.keys()):
            df = all_processed_data[ticker]
            if current_date not in df.index:
                continue
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
            for ticker, df in all_processed_data.items():
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
            df = all_processed_data[ticker]
            if current_date in df.index:
                pv += pos["shares"] * df.loc[current_date]["Close"]
        equity_curve.append(pv)

    if len(equity_curve) == 0:
        return 0, 0, 0, 0, 0

    eq = np.array(equity_curve)
    final_cap = eq[-1]
    ret_pct   = (final_cap / INITIAL_CAPITAL - 1) * 100.0
    peak      = np.maximum.accumulate(eq)
    mdd       = abs(((eq - peak) / peak).min()) * 100.0

    n_trades = len(trade_log)
    win_rate = (sum(1 for p in trade_log if p > 0) / max(1, n_trades)) * 100.0

    # Pareto Score: Balances Win Rate + Return vs MDD Penalty
    pareto_score = win_rate + min(ret_pct * 0.01, 100.0) - (mdd * 1.5)

    return final_cap, ret_pct, win_rate, mdd, pareto_score, n_trades


def main():
    t0 = time.time()
    print("=" * 80)
    print("  GEOMETRY ENGINE HYPER-PARAMETER OPTIMIZER")
    print("=" * 80)

    tickers = load_nse_tickers()
    print(f"\n[1/3] Downloading raw market data for {len(tickers)} tickers...")
    
    raw_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_stock_raw, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                raw_data[res[0]] = res[1]

    print(f"      Downloaded {len(raw_data)} active tickers in {time.time()-t0:.1f}s\n")

    # ── Grid Search ───────────────────────────────────────────────────────────
    print("[2/3] Running Grid Search across parameter combinations...\n")

    grid_results = []
    
    for score_thresh in PARAM_GRID["geometry_score_threshold"]:
        # Precompute signals for this score_thresh
        processed_data = {
            t: compute_signals_fast(df, score_thresh)
            for t, df in raw_data.items()
        }

        for sl in PARAM_GRID["STOP_LOSS_PCT"]:
            for tp in PARAM_GRID["TAKE_PROFIT_PCT"]:
                for slots in PARAM_GRID["MAX_POSITIONS"]:

                    final_cap, ret_pct, wr, mdd, pareto, trades = run_fast_backtest(
                        processed_data, sl, tp, slots
                    )

                    rec = {
                        "ScoreThresh": score_thresh,
                        "StopLoss": sl,
                        "TakeProfit": tp,
                        "MaxSlots": slots,
                        "FinalCapital": final_cap,
                        "Return%": ret_pct,
                        "WinRate%": wr,
                        "MaxDD%": mdd,
                        "Trades": trades,
                        "ParetoScore": pareto
                    }
                    grid_results.append(rec)

                    print(f"  Thresh:{score_thresh:.2f} SL:{sl*100:02.0f}% TP:{tp*100:02.0f}% Slots:{slots:02d} | "
                          f"Final: ₹{final_cap:14,.2f}  Ret:+{ret_pct:9,.1f}%  WR:{wr:5.1f}%  MDD:-{mdd:5.1f}%  Score:{pareto:6.1f}")

    df_res = pd.DataFrame(grid_results)
    df_res.sort_values(by="ParetoScore", ascending=False, inplace=True)

    print("\n" + "=" * 90)
    print("  🏆 TOP 5 OPTIMAL PARAMETER SETTINGS (BALANCED PROFIT + WIN RATE + LOW MDD)")
    print("=" * 90)
    print(f"  {'Thresh':<8} {'SL%':<6} {'TP%':<6} {'Slots':<6} {'Final Capital':>16} {'Return %':>12} {'Win Rate':>10} {'Max DD':>10} {'Trades':>8}")
    print("  " + "-" * 88)

    for _, r in df_res.head(5).iterrows():
        print(f"  {r['ScoreThresh']:<8.2f} {r['StopLoss']*100:<6.0f}% {r['TakeProfit']*100:<6.0f}% {r['MaxSlots']:<6.0d} "
              f"₹{r['FinalCapital']:>15,.2f} +{r['Return%']:>11,.1f}% {r['WinRate%']:>9.1f}% -{r['MaxDD%']:>9.1f}% {r['Trades']:>8.0f}")
    print("=" * 90)

    out_csv = "analysis/geometry_optimal_parameters.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\n[3/3] Full grid optimization saved to: {out_csv}")
    print(f"      Total execution time: {time.time()-t0:.1f} seconds.")

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

if __name__ == "__main__":
    main()
