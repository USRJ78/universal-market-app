"""
==============================================================================
  ANTIGRAVITY AI BRAIN — STOCKFISH x GEOMETRY MAX RETURN PARAMETER OPTIMIZER
==============================================================================
  Sweeps TakeProfit (3% to 50%), StopLoss (2% to 10%), and MaxSlots (3, 5, 10)
  across ALL 2,000+ NSE equities in EQUITY_L.csv to find the HIGHEST RETURN setting.
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

INITIAL_CAPITAL = 100000.0
LOOKBACK_PERIOD = "10y"
MAX_WORKERS     = 20

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))

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
    return max(0.0, min(1.0, (score + 0.45) / 1.15))

def process_single_stock(sym):
    try:
        df = yf.download(sym, period=LOOKBACK_PERIOD, progress=False)
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

        sf_scores = []
        for i in range(len(df)):
            c   = float(df["Close"].iloc[i])
            s50 = float(df["SMA50"].iloc[i])
            s200= float(df["SMA200"].iloc[i])
            rsi = float(df["RSI14"].iloc[i])
            vr  = float(df["VolRatio"].iloc[i])
            sf_scores.append(evaluate_fen_fast(c, s50, s200, rsi, vr))
        df["SF_Score"] = sf_scores

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

        df["Fusion_Score"] = 0.50 * df["SF_Score"] + 0.50 * df["Geom_Score"]
        df["Vol_Comp"]     = vol_comp

        return sym, df
    except Exception:
        return None

def run_fast_backtest(all_data, stop_loss_pct, take_profit_pct, max_positions):
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
            if row["Close"] <= stop_price:
                exit_trade = True
            elif row["Close"] >= tp_price:
                exit_trade = True
            elif row["Vol_Comp"] > 0.80 or row["Fusion_Score"] < 0.30:
                exit_trade = True

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
                if row["Fusion_Score"] >= 0.60:
                    candidates.append((ticker, row["Fusion_Score"], row))

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
        return 0, 0, 0, 0, 0

    eq = np.array(equity_curve)
    final_cap = eq[-1]
    ret_pct   = (final_cap / INITIAL_CAPITAL - 1) * 100.0
    peak      = np.maximum.accumulate(eq)
    mdd       = abs(((eq - peak) / peak).min()) * 100.0
    n_trades  = len(trade_log)
    win_rate  = (sum(1 for p in trade_log if p > 0) / max(1, n_trades)) * 100.0

    return final_cap, ret_pct, win_rate, mdd, n_trades

def main():
    t0 = time.time()
    print("=" * 85)
    print("  STOCKFISH x GEOMETRY MAX RETURN PARAMETER OPTIMIZER")
    print("=" * 85)

    tickers = load_all_nse_tickers()
    print(f"\n[1/3] Pre-loading market data for {len(tickers)} NSE tickers into RAM...")

    all_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_single_stock, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                all_data[res[0]] = res[1]

    print(f"      Loaded {len(all_data)} active tickers in {time.time()-t0:.1f}s.\n")

    # ── PARAMETER GRID SWEEP ──
    TP_GRID    = [0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50]
    SL_GRID    = [0.02, 0.04, 0.06, 0.08, 0.10]
    SLOTS_GRID = [3, 5]

    print("[2/3] Sweeping parameter combinations to find HIGHEST RETURN profile...")

    results = []
    tot_combos = len(TP_GRID) * len(SL_GRID) * len(SLOTS_GRID)
    cnt = 0

    for tp in TP_GRID:
        for sl in SL_GRID:
            for slots in SLOTS_GRID:
                cnt += 1
                final_cap, ret_pct, wr, mdd, trades = run_fast_backtest(all_data, sl, tp, slots)
                rec = {
                    "TakeProfit": tp,
                    "StopLoss": sl,
                    "MaxSlots": slots,
                    "FinalCapital": final_cap,
                    "Return%": ret_pct,
                    "WinRate%": wr,
                    "MaxDD%": mdd,
                    "Trades": trades
                }
                results.append(rec)
                if cnt % 10 == 0 or cnt == tot_combos:
                    print(f"      Processed {cnt}/{tot_combos} combinations...")

    df_res = pd.DataFrame(results)
    df_res.sort_values(by="FinalCapital", ascending=False, inplace=True)

    print("\n" + "=" * 95)
    print("  🏆 TOP 5 PARAMETER COMBINATIONS PRODUCING THE ABSOLUTE HIGHEST RETURNS")
    print("=" * 95)
    print(f"  {'Rank':<5} {'TP%':<6} {'SL%':<6} {'Slots':<6} {'Final Capital':>18} {'Return %':>12} {'Win Rate':>9} {'Max DD':>9} {'Trades':>8}")
    print("  " + "-" * 93)

    for rank, (_, r) in enumerate(df_res.head(5).iterrows(), 1):
        print(f"  #{rank:<4d} {r['TakeProfit']*100:<5.0f}% {r['StopLoss']*100:<5.0f}% {r['MaxSlots']:<6.0f} "
              f"₹{r['FinalCapital']:>17,.2f} +{r['Return%']:>11,.1f}% {r['WinRate%']:>8.1f}% -{r['MaxDD%']:>8.1f}% {r['Trades']:>8.0f}")
    print("=" * 95)

    out_csv = os.path.join(ANALYSIS_DIR, "stockfish_geometry_max_return_grid.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\n[3/3] Results saved to: {out_csv}")
    print(f"      Total execution time: {time.time()-t0:.1f}s.")

if __name__ == "__main__":
    main()
