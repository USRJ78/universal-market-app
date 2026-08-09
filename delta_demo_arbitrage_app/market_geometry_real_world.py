"""
====================================================================
           GEOMETRY ENGINE — REAL-WORLD REALISTIC BACKTEST
====================================================================
Goal: Find the realistic real-world return of the 3D Vector Geometry
      strategy on Indian stocks (2016-2026) by implementing:
        1. 0.20% transaction friction (slippage + brokerage + taxes)
        2. A Rs 10 Crore Portfolio Capacity Cap (excess withdrawn)
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
REAL_WORLD_FRICTION = 0.0020  # 0.20% per trade (slippage + taxes + brokerage)
CAPACITY_CAP = 100000000       # Rs 10 Crore capacity cap

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
# GEOMETRY FEATURES
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
# FETCH DATA
# ============================================================

def load_stock(ticker):
    try:
        parquet_path = os.path.join(HISTORICAL_DIR, f"{ticker}.parquet")
        df = pd.read_parquet(parquet_path)
        if df.empty or len(df) < 250:
            return None
        df = normalize_index(df)
        df = compute_geometry_features(df)
        df = df[['Close', 'Volume', 'Compression_Ratio', 'Vol_Expansion', 
                 'Curvature', 'Vector_Magnitude', 'Trajectory_Angle', 'Volume_Pressure']]
        return ticker, df
    except:
        return None

def load_all_data(tickers):
    all_data = {}
    print(f"Loading raw features for {len(tickers)} tickers...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(load_stock, t): t for t in tickers}
        for idx, fut in enumerate(as_completed(futures)):
            result = fut.result()
            if result is not None:
                ticker, df = result
                all_data[ticker] = df
    return all_data

# ============================================================
# BUILD SIGNALS ON THE FLY
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
# REAL WORLD BACKTEST
# ============================================================

def run_real_world_backtest(all_data, params):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []
    withdrawn_profits = 0.0
    
    dates = sorted(set(d for df in all_data.values() for d in df.index))
    
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
                gross = pos["shares"] * row["Close"]
                # Apply exit friction (0.10%)
                proceeds = gross * (1 - REAL_WORLD_FRICTION / 2)
                profit = proceeds - pos["invested"]
                
                cash += proceeds
                trade_log.append({
                    "Stock": ticker,
                    "Profit": profit,
                    "Return %": (profit / pos["invested"]) * 100,
                    "Reason": reason
                })
                del positions[ticker]

        # CAPACITY CAP CHECK & WITHDRAWAL
        # Calculate current portfolio value (cash + positions valued at close)
        pv = cash
        for ticker, pos in positions.items():
            df = aligned_data[ticker]
            row = df.iloc[idx]
            if not pd.isna(row["Close"]):
                pv += pos["shares"] * row["Close"]
            else:
                pv += pos["shares"] * pos["entry_price"]
                
        if pv > CAPACITY_CAP:
            excess = pv - CAPACITY_CAP
            withdrawn_profits += excess
            cash -= excess  # Withdraw excess from cash pool
            pv = CAPACITY_CAP

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
                    # Apply entry friction (0.10% execution fee/slippage on entry)
                    effective_allocation = allocation_per_slot * (1 - REAL_WORLD_FRICTION / 2)
                    shares = effective_allocation / row["Close"]
                    
                    cash -= allocation_per_slot
                    positions[ticker] = {
                        "entry_date": current_date,
                        "entry_price": row["Close"],
                        "shares": shares,
                        "invested": allocation_per_slot
                    }

        # RE-CALCULATE EQUITY FOR CURVE
        pv_final = cash
        for ticker, pos in positions.items():
            df = aligned_data[ticker]
            row = df.iloc[idx]
            if not pd.isna(row["Close"]):
                pv_final += pos["shares"] * row["Close"]
            else:
                pv_final += pos["shares"] * pos["entry_price"]
        equity_curve.append(pv_final + withdrawn_profits)

    return pd.DataFrame(trade_log), equity_curve, withdrawn_profits

# ============================================================
# EVALUATE
# ============================================================

def evaluate(trades, equity_curve, withdrawn_profits):
    eq = np.array(equity_curve)
    final_capital = eq[-1]
    returns = pd.Series(eq).pct_change().dropna()
    
    sharpe = 0
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        
    peak = np.maximum.accumulate(eq)
    dd = ((eq - peak) / peak).min()
    
    win_rate = (trades["Profit"] > 0).mean() * 100 if len(trades) > 0 else 0.0
    
    return {
        "Final Portfolio Value": round(eq[-1] - withdrawn_profits, 2),
        "Total Withdrawn Profits": round(withdrawn_profits, 2),
        "Total Return (With Withdrawals)": round((final_capital / INITIAL_CAPITAL - 1) * 100, 2),
        "Sharpe": round(sharpe, 2),
        "Max Drawdown %": round(dd * 100, 2),
        "Win Rate %": round(win_rate, 2),
        "Trades": len(trades)
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    tickers = load_nse_tickers()
    tickers = tickers[:1000]

    # Use optimal Selective params
    params = {
        "vol_window": 20,
        "compression_window": 30,
        "vector_window": 5,
        "compression_threshold": 0.20,
        "expansion_threshold": 1.10,
        "curvature_threshold": 0.05,
        "magnitude_threshold": 0.60,
        "angle_threshold": 0.0,
        "geometry_score_threshold": 0.70,
        "volume_pressure_threshold": 2.0  # optimized volume
    }

    all_data = load_all_data(tickers)
    
    print("\nRunning Real-World backtest (0.20% friction + Rs 10 Crore Capacity Cap)...")
    trades, equity_curve, withdrawn = run_real_world_backtest(all_data, params)
    
    results = evaluate(trades, equity_curve, withdrawn)
    
    print("\n================ REAL WORLD RESULTS (10-YEAR) ================\n")
    for k, v in results.items():
        if "Capital" in k or "Value" in k or "Profits" in k:
            print(f"{k}: Rs {v:,.2f}")
        else:
            print(f"{k}: {v}")
    print("==============================================================\n")
