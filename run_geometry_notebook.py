import os, sys, warnings
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000
LOOKBACK_PERIOD = "10y"
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.08
TAKE_PROFIT_PCT = 0.25
MAX_WORKERS = 20

def load_nse_tickers():
    possible_paths = [
        "data/EQUITY_L.csv",
        "EQUITY_L.csv",
        r"C:\Users\USER\OneDrive\Documents\universal-market-app\data\EQUITY_L.csv",
        r"C:\Users\USER\OneDrive\Documents\universal-market-app\EQUITY_L.csv"
    ]
    path = None
    for p in possible_paths:
        if os.path.exists(p):
            path = p
            break
    if path is None:
        raise FileNotFoundError("EQUITY_L.csv not found")

    df = pd.read_csv(path)
    symbols = (
        df["SYMBOL"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    return [s + ".NS" for s in symbols if "&" not in s]

def normalize_index(df):
    idx = df.index
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    df.index = idx.normalize()
    return df

def compute_geometry_features(df, vol_window=20, compression_window=30, vector_window=5):
    df = df.copy()
    df["Returns"] = df["Close"].pct_change()
    df["Volatility"] = df["Returns"].rolling(vol_window).std()
    
    vol_min = df["Volatility"].rolling(compression_window).min()
    vol_max = df["Volatility"].rolling(compression_window).max()
    df["Vol_Compression"] = (df["Volatility"] - vol_min) / (vol_max - vol_min + 1e-9)

    df["Vol_Expansion"] = df["Volatility"] / (df["Volatility"].rolling(compression_window).mean() + 1e-9)
    df["Velocity"] = df["Close"].diff(vector_window)
    df["Acceleration"] = df["Velocity"].diff()
    df["Curvature"] = df["Acceleration"].diff()
    df["Vector_Magnitude"] = np.sqrt(df["Velocity"]**2 + df["Acceleration"]**2)
    df["Vector_Angle"] = np.arctan2(df["Acceleration"], df["Velocity"])
    return df

def generate_geometry_signals(df, params):
    df = compute_geometry_features(
        df,
        vol_window=params["vol_window"],
        compression_window=params["compression_window"],
        vector_window=params["vector_window"]
    )
    c1 = df["Vol_Compression"].shift(1) < params["compression_threshold"]
    c2 = df["Vol_Expansion"] > params["expansion_threshold"]
    c3 = df["Curvature"] > params["curvature_threshold"]
    c4 = df["Vector_Magnitude"] > (df["Vector_Magnitude"].rolling(50).mean() * params["magnitude_threshold"])
    c5 = df["Vector_Angle"] > params["angle_threshold"]

    df["Geometry_Score"] = (
        c1.astype(int) +
        c2.astype(int) +
        c3.astype(int) +
        c4.astype(int) +
        c5.astype(int)
    ) / 5.0

    df["BUY_SIGNAL"] = df["Geometry_Score"] >= params["geometry_score_threshold"]
    df["SELL_SIGNAL"] = df["Vol_Compression"] > 0.80
    return df

def fetch_stock(ticker, params):
    try:
        df = yf.download(ticker, period=LOOKBACK_PERIOD, progress=False)
        if df.empty or len(df) < 200:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = normalize_index(df)
        df = generate_geometry_signals(df, params)
        return ticker, df
    except Exception as e:
        return None

def load_all_data(tickers, params):
    all_data = {}
    print(f"Loading data for ALL {len(tickers)} tickers using {MAX_WORKERS} workers...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_stock, t, params): t for t in tickers}
        for fut in as_completed(futures):
            result = fut.result()
            if result is not None:
                ticker, df = result
                all_data[ticker] = df
    print(f"Successfully loaded {len(all_data)} tickers.")
    return all_data

def run_backtest(all_data):
    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []

    dates = sorted(set(d for df in all_data.values() for d in df.index))

    for current_date in dates:
        for ticker in list(positions.keys()):
            df = all_data[ticker]
            if current_date not in df.index:
                continue
            row = df.loc[current_date]
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
                proceeds = pos["shares"] * row["Close"]
                profit = proceeds - pos["invested"]
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
                    candidates.append((ticker, score, row))

            candidates.sort(key=lambda x: x[1], reverse=True)
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

        pv = cash
        for ticker, pos in positions.items():
            df = all_data[ticker]
            if current_date in df.index:
                pv += pos["shares"] * df.loc[current_date]["Close"]
        equity_curve.append(pv)

    return pd.DataFrame(trade_log), equity_curve

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
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)

    peak = np.maximum.accumulate(eq)
    dd = ((eq - peak) / peak).min()

    if len(trades) > 0:
        win_rate = (trades["Profit"] > 0).mean() * 100
    else:
        win_rate = 0

    total_return = (final_capital / INITIAL_CAPITAL - 1) * 100

    return {
        "Final Capital": round(final_capital, 2),
        "Return %": round(total_return, 2),
        "Sharpe": round(sharpe, 2),
        "Max Drawdown %": round(dd * 100, 2),
        "Win Rate %": round(win_rate, 2),
        "Trades": len(trades)
    }

if __name__ == "__main__":
    tickers = load_nse_tickers()
    print(f"Total tickers from EQUITY_L.csv: {len(tickers)}")

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

    print("\nLoading ALL stock data from Yahoo Finance...\n")
    all_data = load_all_data(tickers, params)

    print("\nRunning Geometry Strategy across full universe...\n")
    trades, equity_curve = run_backtest(all_data)

    results = evaluate_strategy(trades, equity_curve)

    print("\n================ FULL UNIVERSE RESULTS ================\n")
    for k, v in results.items():
        print(f"{k}: {v}")
