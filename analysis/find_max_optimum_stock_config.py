"""
==============================================================================
  ANTIGRAVITY AI BRAIN — MAXIMUM PROFIT STOCK CONFIGURATION OPTIMIZER
==============================================================================
  Sweeps all position slot counts, option spread payoff targets, stop loss levels,
  and conviction thresholds across Indian Stocks to extract the SINGLE MAXIMUM
  PROFIT CONFIGURATION for Indian Equities.
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
LOOKBACK_PERIOD = "10y"      # 10 Years
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
        if df.empty or len(df) < 100: return None
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

def run_stock_simulation(stock_data, tp_pct, sl_pct, max_positions, mult=2.5):
    cash = INITIAL_CAPITAL
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
            eff_tp     = tp_pct * mult
            eff_sl     = sl_pct

            if row["High"] >= tp_price:
                exit_trade = True; exit_price = entry_p * (1.0 + eff_tp)
            elif row["Low"] <= sl_price:
                exit_trade = True; exit_price = entry_p * (1.0 - eff_sl)
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
    ret_pct   = (final_cap / INITIAL_CAPITAL - 1) * 100.0
    peak      = np.maximum.accumulate(eq)
    mdd       = abs(((eq - peak) / peak).min()) * 100.0
    n_trades  = len(trade_log)
    win_rate  = (sum(1 for p in trade_log if p > 0) / max(1, n_trades)) * 100.0
    years     = max((dates[-1] - dates[0]).days / 365.25, 0.1)
    cagr      = ((final_cap / INITIAL_CAPITAL) ** (1 / years) - 1) * 100.0

    return final_cap, ret_pct, cagr, win_rate, mdd, n_trades

def main():
    t0 = time.time()
    print("=" * 85)
    print("  MAXIMUM PROFIT INDIAN STOCK CONFIGURATION OPTIMIZER")
    print("=" * 85)

    tickers = load_top_nse_tickers()
    print(f"\n[1/3] Loading 10-year market data for {len(tickers)} Indian equities into RAM...")

    stock_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_single_stock, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                stock_data[res[0]] = res[1]

    print(f"      Loaded {len(stock_data)} active stocks in {time.time()-t0:.1f}s.")

    # Sweep Parameters
    TP_LIST    = [0.03, 0.045, 0.08, 0.125, 0.15, 0.25, 0.50]
    SL_LIST    = [0.01, 0.015, 0.02, 0.04, 0.08]
    SLOTS_LIST = [1, 2, 3]

    print("\n[2/3] Sweeping configurations to find ABSOLUTE MAXIMUM PROFIT profile for Stocks...")

    results = []
    for slots in SLOTS_LIST:
        for tp in TP_LIST:
            for sl in SL_LIST:
                final_cap, ret_pct, cagr, wr, mdd, trades = run_stock_simulation(
                    stock_data, tp, sl, slots, mult=2.5
                )
                results.append({
                    "Slots": slots,
                    "Alloc%": round(100.0 / slots, 1),
                    "UnderlyingTP%": tp * 100,
                    "EffectiveOptionsTP%": tp * 100 * 2.5,
                    "StopLoss%": sl * 100,
                    "FinalCapital": final_cap,
                    "TotalReturn%": ret_pct,
                    "CAGR%": cagr,
                    "WinRate%": wr,
                    "MaxDD%": mdd,
                    "Trades": trades
                })

    df_res = pd.DataFrame(results)
    df_res.sort_values(by="FinalCapital", ascending=False, inplace=True)

    print("\n" + "=" * 110)
    print("  🏆 TOP 5 ABSOLUTE MAXIMUM PROFIT CONFIGURATIONS FOR INDIAN STOCKS")
    print("=" * 110)
    print(f"  {'Rank':<5} {'Slots':<6} {'Alloc%':<7} {'Stock TP%':<10} {'Options TP%':<12} {'SL%':<6} | {'Final Capital (INR)':>22} {'CAGR %':>10} {'Win Rate':>9} {'Max DD':>9}")
    print("  " + "-" * 108)

    for rank, (_, r) in enumerate(df_res.head(5).iterrows(), 1):
        print(f"  #{rank:<4d} {r['Slots']:<6.0f} {r['Alloc%']:<6.1f}% {r['UnderlyingTP%']:<9.1f}% {r['EffectiveOptionsTP%']:<11.1f}% {r['StopLoss%']:<5.1f}% | "
              f"₹{r['FinalCapital']:>21,.2f} +{r['CAGR%']:>9.1f}% {r['WinRate%']:>8.1f}% -{r['MaxDD%']:>8.1f}%")

    print("=" * 110)

    out_csv = os.path.join(ANALYSIS_DIR, "max_optimum_stock_configuration.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\n[3/3] Report saved to: {out_csv}")
    print(f"      Total execution time: {time.time()-t0:.1f}s.")

if __name__ == "__main__":
    main()
