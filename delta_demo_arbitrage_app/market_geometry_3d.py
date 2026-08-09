"""
====================================================================
        MARKET GEOMETRY ENGINE — 3D VECTOR FIELD BACKTEST
====================================================================

IDEA
----
We transform stock movement into a geometric trajectory:

    X = Time
    Y = Price Movement
    Z = Volatility / Pressure

Then we detect:

    • Volatility Compression
    • Expansion Breakouts
    • Curvature Inflections
    • Vector Magnitude Surges
    • Trajectory Angles
    • Regime Transitions

This attempts to detect:
    → Smart money accumulation
    → HFT positioning
    → Liquidity release
    → Pre-breakout geometry

====================================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import os
warnings.filterwarnings("ignore")

# ============================================================
# SETTINGS
# ============================================================

INITIAL_CAPITAL = 100000
LOOKBACK_PERIOD = "10y"
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.15
TAKE_PROFIT_PCT = 0.3
MAX_WORKERS = 20

# Resolve absolute paths to avoid FileNotFoundError when running from different subdirs
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
    symbols = (
        df["SYMBOL"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    # Only return symbols that exist in the local Parquet cache directory
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
# GEOMETRY ENGINE
# ============================================================

def compute_geometry_features(
    df,
    vol_window=20,
    compression_window=30,
    vector_window=5
):
    df = df.copy()

    # ========================================================
    # RETURNS
    # ========================================================
    df["Returns"] = df["Close"].pct_change()

    # ========================================================
    # VOLATILITY
    # ========================================================
    df["Volatility"] = (
        df["Returns"]
        .rolling(vol_window)
        .std()
    )

    # ========================================================
    # VOLATILITY COMPRESSION
    # ========================================================
    vol_ma = (
        df["Volatility"]
        .rolling(compression_window)
        .mean()
    )
    df["Compression_Ratio"] = (
        df["Volatility"]
        /
        vol_ma
    )

    # ========================================================
    # VELOCITY
    # ========================================================
    df["Price_Velocity"] = (
        df["Close"]
        .pct_change(vector_window)
    )
    df["Vol_Velocity"] = (
        df["Volatility"]
        .diff(vector_window)
    )

    # ========================================================
    # ACCELERATION
    # ========================================================
    df["Acceleration"] = (
        df["Price_Velocity"]
        .diff()
    )

    # ========================================================
    # CURVATURE
    # ========================================================
    df["Curvature"] = (
        df["Acceleration"]
        .diff()
    )

    # ========================================================
    # VECTOR MAGNITUDE
    # ========================================================
    df["Vector_Magnitude"] = np.sqrt(
        (df["Price_Velocity"] ** 2)
        +
        (df["Vol_Velocity"] ** 2)
    )

    # ========================================================
    # TRAJECTORY ANGLE
    # ========================================================
    df["Trajectory_Angle"] = np.arctan2(
        df["Vol_Velocity"],
        df["Price_Velocity"]
    )

    # ========================================================
    # VOLUME PRESSURE
    # ========================================================
    vol_ma20 = df["Volume"].rolling(20).mean()
    df["Volume_Pressure"] = (
        df["Volume"]
        /
        vol_ma20
    )

    # ========================================================
    # VOLATILITY EXPANSION
    # ========================================================
    df["Vol_Expansion"] = (
        df["Volatility"]
        /
        df["Volatility"].shift(5)
    )

    return df

# ============================================================
# BUILD SIGNALS
# ============================================================

def build_geometry_signals(
    df,
    compression_threshold=0.20,
    expansion_threshold=1.10,
    curvature_threshold=0.05,
    magnitude_threshold=0.60,
    angle_threshold=0,
    geometry_score_threshold=0.60
):
    df = df.copy()

    # ========================================================
    # FEATURE SCORES
    # ========================================================
    compression_score = np.where(
        df["Compression_Ratio"] < compression_threshold,
        1,
        0
    )

    expansion_score = np.where(
        df["Vol_Expansion"] > expansion_threshold,
        1,
        0
    )

    curvature_score = np.where(
        df["Curvature"] > curvature_threshold,
        1,
        0
    )

    magnitude_score = np.where(
        df["Vector_Magnitude"].rank(pct=True) > magnitude_threshold,
        1,
        0
    )

    angle_score = np.where(
        df["Trajectory_Angle"] > angle_threshold,
        1,
        0
    )

    volume_score = np.where(
        df["Volume_Pressure"] > 1.2,
        1,
        0
    )

    # ========================================================
    # FINAL GEOMETRY SCORE
    # ========================================================
    df["Geometry_Score"] = (
        0.25 * compression_score +
        0.20 * expansion_score +
        0.20 * curvature_score +
        0.15 * magnitude_score +
        0.10 * angle_score +
        0.10 * volume_score
    )

    # ========================================================
    # SIGNALS
    # ========================================================
    df["BUY_SIGNAL"] = (
        df["Geometry_Score"] >= geometry_score_threshold
    )

    # ========================================================
    # EXIT SIGNAL
    # ========================================================
    df["SELL_SIGNAL"] = (
        (df["Geometry_Score"] < geometry_score_threshold * 0.5)
        |
        (df["Curvature"] < 0)
    )

    return df

# ============================================================
# FETCH STOCK
# ============================================================

def fetch_stock(ticker, params):
    try:
        # Optimization: Try to load from local Parquet cache first
        parquet_path = os.path.join(HISTORICAL_DIR, f"{ticker}.parquet")
        if os.path.exists(parquet_path):
            df = pd.read_parquet(parquet_path)
        else:
            df = yf.download(
                ticker,
                period=LOOKBACK_PERIOD,
                auto_adjust=True,
                progress=False
            )

        if df.empty or len(df) < 250:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = normalize_index(df)

        df = compute_geometry_features(
            df,
            vol_window=params["vol_window"],
            compression_window=params["compression_window"],
            vector_window=params["vector_window"]
        )

        df = build_geometry_signals(
            df,
            compression_threshold=params["compression_threshold"],
            expansion_threshold=params["expansion_threshold"],
            curvature_threshold=params["curvature_threshold"],
            magnitude_threshold=params["magnitude_threshold"],
            angle_threshold=params["angle_threshold"],
            geometry_score_threshold=params["geometry_score_threshold"]
        )

        return ticker, df

    except Exception as e:
        return None

# ============================================================
# LOAD DATA
# ============================================================

def load_all_data(tickers, params):
    all_data = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(fetch_stock, t, params): t
            for t in tickers
        }
        for fut in as_completed(futures):
            result = fut.result()
            if result is not None:
                ticker, df = result
                all_data[ticker] = df
                print("Loaded:", ticker)
    return all_data

# ============================================================
# BACKTEST
# ============================================================

def run_backtest(all_data):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(
        set(
            d
            for df in all_data.values()
            for d in df.index
        )
    )

    for current_date in dates:
        # ====================================================
        # EXITS
        # ====================================================
        for ticker in list(positions.keys()):
            df = all_data[ticker]
            if current_date not in df.index:
                continue

            row = df.loc[current_date]
            pos = positions[ticker]

            stop_price = (
                pos["entry_price"]
                * (1 - STOP_LOSS_PCT)
            )

            tp_price = (
                pos["entry_price"]
                * (1 + TAKE_PROFIT_PCT)
            )

            exit_trade = False
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
                proceeds = (
                    pos["shares"]
                    * row["Close"]
                )
                profit = (
                    proceeds
                    - pos["invested"]
                )
                cash += proceeds
                trade_log.append({
                    "Stock": ticker,
                    "Entry Date": pos["entry_date"],
                    "Exit Date": current_date,
                    "Entry Price": pos["entry_price"],
                    "Exit Price": row["Close"],
                    "Profit": profit,
                    "Return %": (profit / pos["invested"]) * 100,
                    "Reason": reason
                })
                del positions[ticker]

        # ====================================================
        # ENTRIES
        # ====================================================
        slots = MAX_POSITIONS - len(positions)
        if slots > 0:
            candidates = []
            for ticker, df in all_data.items():
                if ticker in positions:
                    continue
                if current_date not in df.index:
                    continue
                row = df.loc[current_date]
                if bool(row["BUY_SIGNAL"]):
                    score = row["Geometry_Score"]
                    candidates.append(
                        (ticker, score, row)
                    )

            candidates.sort(
                key=lambda x: x[1],
                reverse=True
            )

            for ticker, score, row in candidates[:slots]:
                allocation = cash / slots
                if allocation <= 0:
                    continue
                shares = allocation / row["Close"]
                cash -= allocation
                positions[ticker] = {
                    "entry_date": current_date,
                    "entry_price": row["Close"],
                    "shares": shares,
                    "invested": allocation
                }

        # ====================================================
        # EQUITY
        # ====================================================
        pv = cash
        for ticker, pos in positions.items():
            df = all_data[ticker]
            if current_date in df.index:
                pv += (
                    pos["shares"]
                    * df.loc[current_date]["Close"]
                )
        equity_curve.append(pv)

    return pd.DataFrame(trade_log), equity_curve

# ============================================================
# EVALUATE
# ============================================================

def evaluate_strategy(trades, equity_curve):
    if len(equity_curve) == 0:
        return {
            "Final Capital": INITIAL_CAPITAL,
            "Return %": 0,
            "Sharpe": 0,
            "Max Drawdown %": 0,
            "Win Rate %": 0,
            "Trades": 0
        }

    eq = np.array(equity_curve)
    final_capital = eq[-1]
    returns = pd.Series(eq).pct_change().dropna()

    sharpe = 0
    if returns.std() > 0:
        sharpe = (
            returns.mean()
            /
            returns.std()
        ) * np.sqrt(252)

    peak = np.maximum.accumulate(eq)
    dd = ((eq - peak) / peak).min()

    if len(trades) > 0:
        win_rate = (
            (trades["Profit"] > 0).mean()
            * 100
        )
    else:
        win_rate = 0

    total_return = (
        final_capital
        / INITIAL_CAPITAL
        - 1
    ) * 100

    return {
        "Final Capital": round(final_capital, 2),
        "Return %": round(total_return, 2),
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
    # Use first 1000 tickers as specified
    tickers = tickers[:1000]

    params = {
        "vol_window": 20,
        "compression_window": 30,
        "vector_window": 5,
        "compression_threshold": 0.20,
        "expansion_threshold": 1.10,
        "curvature_threshold": 0.05,
        "magnitude_threshold": 0.60,
        "angle_threshold": 0,
        "geometry_score_threshold": 0.60
    }

    print("\nLoading stock data...\n")
    all_data = load_all_data(tickers, params)

    print("\nRunning Geometry Strategy...\n")
    trades, equity_curve = run_backtest(all_data)

    results = evaluate_strategy(trades, equity_curve)

    print("\n================ RESULTS ================\n")
    for k, v in results.items():
        print(f"{k}: {v}")

    # ========================================================
    # SAVE EXCEL
    # ========================================================
    excel_path = "market_geometry_results.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame([results]).to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )
        trades.to_excel(
            writer,
            sheet_name="Trades",
            index=False
        )
    print(f"\nSaved: {excel_path}")

    # ========================================================
    # PLOT EQUITY CURVE
    # ========================================================
    plt.figure(figsize=(15, 7))
    plt.plot(equity_curve, label="Geometry 3D Vector Field Strategy")
    plt.title("Market Geometry Equity Curve")
    plt.xlabel("Time (Steps)")
    plt.ylabel("Portfolio Value (INR)")
    plt.grid(True)
    plt.legend()
    
    chart_path = "market_geometry_equity_curve.png"
    plt.savefig(chart_path, dpi=300)
    print(f"Saved: {chart_path}")
    
    # Do not call plt.show() to prevent blocking in background tasks
    # plt.show()
