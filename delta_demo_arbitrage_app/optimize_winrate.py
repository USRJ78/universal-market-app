"""
====================================================================
           GEOMETRY ENGINE — WIN RATE OPTIMIZATION BACKTEST
====================================================================
Goal: Test various quantitative enhancements to increase the win rate
      of the 3D Vector Geometry strategy on 1,000 Indian stocks (2016-2026).
      Optimized for memory efficiency to prevent OOM errors.
====================================================================
"""

import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# SETTINGS
# ============================================================

INITIAL_CAPITAL = 100000
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.15
TAKE_PROFIT_PCT = 0.3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORICAL_DIR = os.path.join(DATA_DIR, "nse_historical")

# ============================================================
# LOAD NSE TICKERS
# ============================================================

def load_nse_tickers():
    path = os.path.join(DATA_DIR, "EQUITY_L.csv")
    df = pd.read_csv(path)
    symbols = df["SYMBOL"].dropna().astype(str).str.strip().unique().tolist()
    valid_symbols = []
    for s in symbols:
        if "&" in s:
            continue
        ticker = s + ".NS"
        parquet_path = os.path.join(HISTORICAL_DIR, f"{ticker}.parquet")
        if os.path.exists(parquet_path):
            valid_symbols.append(ticker)
    return valid_symbols

# ============================================================
# NORMALIZE INDEX
# ============================================================

def normalize_index(df):
    idx = df.index
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    df.index = idx.normalize()
    return df

# ============================================================
# GEOMETRY FEATURES (LOAD ONCE)
# ============================================================

def compute_geometry_features(df, vol_window=20, compression_window=30, vector_window=5):
    df = df.copy()
    df["Returns"] = df["Close"].pct_change()
    df["Volatility"] = df["Returns"].rolling(vol_window).std()
    vol_ma = df["Volatility"].rolling(compression_window).mean()
    df["Compression_Ratio"] = df["Volatility"] / vol_ma
    df["Price_Velocity"] = df["Close"].pct_change(vector_window)
    df["Vol_Velocity"] = df["Volatility"].diff(vector_window)
    df["Acceleration"] = df["Price_Velocity"].diff()
    df["Curvature"] = df["Acceleration"].diff()
    df["Vector_Magnitude"] = np.sqrt((df["Price_Velocity"] ** 2) + (df["Vol_Velocity"] ** 2))
    df["Trajectory_Angle"] = np.arctan2(df["Vol_Velocity"], df["Price_Velocity"])
    vol_ma20 = df["Volume"].rolling(20).mean()
    df["Volume_Pressure"] = df["Volume"] / vol_ma20
    df["Vol_Expansion"] = df["Volatility"] / df["Volatility"].shift(5)
    return df

# ============================================================
# FETCH DATA FROM CACHE (LOADS RAW FEATURES ONCE)
# ============================================================

def load_stock(ticker):
    try:
        parquet_path = os.path.join(HISTORICAL_DIR, f"{ticker}.parquet")
        df = pd.read_parquet(parquet_path)
        if df.empty or len(df) < 250:
            return None
        df = normalize_index(df)
        df = compute_geometry_features(df)
        # Drop columns we don't need to save memory
        df = df[['Close', 'Volume', 'Compression_Ratio', 'Vol_Expansion', 
                 'Curvature', 'Vector_Magnitude', 'Trajectory_Angle', 'Volume_Pressure']]
        return ticker, df
    except:
        return None

def load_all_data(tickers):
    all_data = {}
    print(f"Loading raw features for {len(tickers)} tickers once...")
    # Use max_workers=4 to prevent context switching/GIL overhead
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(load_stock, t): t for t in tickers}
        for idx, fut in enumerate(as_completed(futures)):
            result = fut.result()
            if result is not None:
                ticker, df = result
                all_data[ticker] = df
            if idx % 200 == 0:
                print(f"   Processed {idx}/{len(tickers)} tickers...")
    return all_data

# ============================================================
# BUILD SIGNALS ON THE FLY FOR A BACKTEST
# ============================================================

def build_signals_for_backtest(df, params):
    df = df.copy()

    compression_score = np.where(df["Compression_Ratio"] < params["compression_threshold"], 1, 0)
    expansion_score = np.where(df["Vol_Expansion"] > params["expansion_threshold"], 1, 0)
    curvature_score = np.where(df["Curvature"] > params["curvature_threshold"], 1, 0)
    magnitude_score = np.where(df["Vector_Magnitude"].rank(pct=True) > params["magnitude_threshold"], 1, 0)
    angle_score = np.where(df["Trajectory_Angle"] > params["angle_threshold"], 1, 0)
    
    vol_threshold = params.get("volume_pressure_threshold", 1.2)
    volume_score = np.where(df["Volume_Pressure"] > vol_threshold, 1, 0)

    # Geometry Score
    df["Geometry_Score"] = (
        0.25 * compression_score +
        0.20 * expansion_score +
        0.20 * curvature_score +
        0.15 * magnitude_score +
        0.10 * angle_score +
        0.10 * volume_score
    )

    df["BUY_SIGNAL"] = df["Geometry_Score"] >= params["geometry_score_threshold"]
    df["SELL_SIGNAL"] = (
        (df["Geometry_Score"] < params["geometry_score_threshold"] * 0.5)
        | (df["Curvature"] < 0)
    )

    return df

# ============================================================
# MEMORY EFFICIENT BACKTEST
# ============================================================

def run_backtest(all_data, params, use_breakeven=False):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []
    
    # Get master dates
    dates = sorted(set(d for df in all_data.values() for d in df.index))
    
    # Pre-align dataframes with signals computed on the fly
    aligned_data = {}
    for ticker, df in all_data.items():
        df_sig = build_signals_for_backtest(df, params)
        aligned_data[ticker] = df_sig.reindex(dates)
        
    for idx, current_date in enumerate(dates):
        # EXITS
        for ticker in list(positions.keys()):
            df = aligned_data[ticker]
            row = df.iloc[idx]
            if pd.isna(row["Close"]):
                continue

            pos = positions[ticker]
            
            if use_breakeven:
                if row["Close"] > pos["highest_price"]:
                    pos["highest_price"] = row["Close"]
                
                # If price went up by 15%, stop loss moves to entry price
                if pos["highest_price"] >= pos["entry_price"] * 1.15:
                    stop_price = pos["entry_price"]
                else:
                    stop_price = pos["entry_price"] * (1 - STOP_LOSS_PCT)
            else:
                stop_price = pos["entry_price"] * (1 - STOP_LOSS_PCT)
                
            tp_price = pos["entry_price"] * (1 + TAKE_PROFIT_PCT)

            exit_trade = False
            reason = ""
            
            if row["Close"] <= stop_price:
                exit_trade = True
                reason = "STOP"
            elif row["Close"] >= tp_price:
                exit_trade = True
                reason = "TARGET"
            elif row["SELL_SIGNAL"]:
                exit_trade = True
                reason = "GEOMETRY_EXIT"

            if exit_trade:
                proceeds = pos["shares"] * row["Close"]
                profit = proceeds - pos["invested"]
                cash += proceeds
                trade_log.append({
                    "Stock": ticker,
                    "Profit": profit,
                    "Return %": (profit / pos["invested"]) * 100,
                    "Reason": reason
                })
                del positions[ticker]

        # ENTRIES
        slots = MAX_POSITIONS - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in aligned_data.items():
                if ticker in positions:
                    continue
                row = df.iloc[idx]
                if pd.isna(row["Close"]):
                    continue
                if bool(row["BUY_SIGNAL"]):
                    score = row["Geometry_Score"]
                    candidates.append((ticker, score, row))

            candidates.sort(key=lambda x: x[1], reverse=True)

            if candidates[:slots] and cash > 0:
                allocation_per_slot = cash / slots
                for ticker, score, row in candidates[:slots]:
                    if allocation_per_slot <= 0:
                        continue
                    shares = allocation_per_slot / row["Close"]
                    cash -= allocation_per_slot
                    positions[ticker] = {
                        "entry_date": current_date,
                        "entry_price": row["Close"],
                        "shares": shares,
                        "invested": allocation_per_slot,
                        "highest_price": row["Close"]
                    }

        # EQUITY
        pv = cash
        for ticker, pos in positions.items():
            df = aligned_data[ticker]
            row = df.iloc[idx]
            if not pd.isna(row["Close"]):
                pv += pos["shares"] * row["Close"]
            else:
                pv += pos["shares"] * pos["entry_price"]
        equity_curve.append(pv)

    return pd.DataFrame(trade_log), equity_curve

# ============================================================
# EVALUATE
# ============================================================

def evaluate(trades, equity_curve):
    if len(equity_curve) == 0:
        return 0.0, 0.0, 0
    eq = np.array(equity_curve)
    final_capital = eq[-1]
    win_rate = (trades["Profit"] > 0).mean() * 100 if len(trades) > 0 else 0.0
    return win_rate, final_capital, len(trades)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    tickers = load_nse_tickers()
    tickers = tickers[:1000]

    # Baseline params
    base_params = {
        "vol_window": 20,
        "compression_window": 30,
        "vector_window": 5,
        "compression_threshold": 0.20,
        "expansion_threshold": 1.10,
        "curvature_threshold": 0.05,
        "magnitude_threshold": 0.60,
        "angle_threshold": 0.0,
        "geometry_score_threshold": 0.60,
        "volume_pressure_threshold": 1.2
    }

    # Load data ONCE
    all_data = load_all_data(tickers)

    # 1. Base Backtest
    print("\nRunning Base Strategy...")
    trades_base, eq_base = run_backtest(all_data, base_params, use_breakeven=False)
    wr_base, cap_base, tr_base = evaluate(trades_base, eq_base)

    # 2. Selective Selection (Score Threshold = 0.70)
    print("Running Score Threshold = 0.70...")
    params_sel = base_params.copy()
    params_sel["geometry_score_threshold"] = 0.70
    trades_sel, eq_sel = run_backtest(all_data, params_sel, use_breakeven=False)
    wr_sel, cap_sel, tr_sel = evaluate(trades_sel, eq_sel)

    # 3. High-Conviction Selection (Score Threshold = 0.80)
    print("Running Score Threshold = 0.80...")
    params_hc = base_params.copy()
    params_hc["geometry_score_threshold"] = 0.80
    trades_hc, eq_hc = run_backtest(all_data, params_hc, use_breakeven=False)
    wr_hc, cap_hc, tr_hc = evaluate(trades_hc, eq_hc)

    # 4. Breakeven Stop-Loss
    print("Running Breakeven Stop-Loss...")
    trades_be, eq_be = run_backtest(all_data, base_params, use_breakeven=True)
    wr_be, cap_be, tr_be = evaluate(trades_be, eq_be)

    # 5. Volume-Backed Breakout (Volume Pressure > 2.0)
    print("Running Volume-Backed Breakout (Volume Pressure > 2.0)...")
    params_vol = base_params.copy()
    params_vol["volume_pressure_threshold"] = 2.0
    trades_vol, eq_vol = run_backtest(all_data, params_vol, use_breakeven=False)
    wr_vol, cap_vol, tr_vol = evaluate(trades_vol, eq_vol)

    # 6. Hybrid Optimization (Threshold = 0.75 + Breakeven)
    print("Running Hybrid Optimization (Threshold = 0.75 + Breakeven)...")
    params_hyb = base_params.copy()
    params_hyb["geometry_score_threshold"] = 0.75
    trades_hyb, eq_hyb = run_backtest(all_data, params_hyb, use_breakeven=True)
    wr_hyb, cap_hyb, tr_hyb = evaluate(trades_hyb, eq_hyb)

    # Print Comparison Table
    print("\n================ WIN RATE OPTIMIZATION RESULTS ================\n")
    print(f"{'Strategy Configuration':<45} | {'Win Rate %':<10} | {'Final Capital (INR)':<20} | {'Total Trades':<12}")
    print("-" * 99)
    print(f"{'1. Base Strategy (Score >= 0.60)':<45} | {wr_base:<10.2f}% | Rs {cap_base:<17,.2f} | {tr_base:<12}")
    print(f"{'2. Selective (Score >= 0.70)':<45} | {wr_sel:<10.2f}% | Rs {cap_sel:<17,.2f} | {tr_sel:<12}")
    print(f"{'3. High-Conviction (Score >= 0.80)':<45} | {wr_hc:<10.2f}% | Rs {cap_hc:<17,.2f} | {tr_hc:<12}")
    print(f"{'4. Base + Breakeven Stop-Loss (at +15%)':<45} | {wr_be:<10.2f}% | Rs {cap_be:<17,.2f} | {tr_be:<12}")
    print(f"{'5. Base + High Volume (> 2.0x)':<45} | {wr_vol:<10.2f}% | Rs {cap_vol:<17,.2f} | {tr_vol:<12}")
    print(f"{'6. Hybrid (Score >= 0.75 + Breakeven)':<45} | {wr_hyb:<10.2f}% | Rs {cap_hyb:<17,.2f} | {tr_hyb:<12}")
    print("===============================================================\n")
