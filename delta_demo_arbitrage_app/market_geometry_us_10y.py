"""
====================================================================
  MARKET GEOMETRY ENGINE — 10-YEAR S&P 500 BACKTEST (US STOCKS)
====================================================================

Goal: Test if the 3D Vector Field Market Geometry Strategy works on 
      American stocks (S&P 500 index components) over the last 10 years.
Denomination: USD
Parameters:
  - Max positions: 5
  - Stop loss: -15%
  - Take profit: +30%
  - Friction: 0.0 (Zero friction to isolate strategy dynamics)
====================================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import urllib.request
import os
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# SETTINGS
# ============================================================

INITIAL_CAPITAL = 100000
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.15
TAKE_PROFIT_PCT = 0.3
FRICTION = 0.0

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# LOAD S&P 500 TICKERS
# ============================================================

def load_sp500_tickers():
    print("Scraping S&P 500 tickers from Wikipedia...")
    try:
        req = urllib.request.Request(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        html = urllib.request.urlopen(req).read()
        tables = pd.read_html(html)
        df = tables[0]
        # Replace '.' with '-' for class formatting in yfinance (e.g., BRK.B -> BRK-B)
        tickers = [s.replace('.', '-') for s in df['Symbol'].tolist()]
        return tickers
    except Exception as e:
        print("Error scraping Wikipedia S&P 500 list, using fallback top-50 list:", e)
        # Fallback list of top market cap S&P 500 tickers
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                "PG", "JPM", "UNH", "MA", "HD", "XOM", "ABBV", "LLY", "MRK", "BAC", 
                "AVGO", "ORCL", "COST", "PEP", "ADBE", "TMO", "CSCO", "CRM", "WMT", "NKE", 
                "CMCSA", "AMD", "CVX", "ACN", "ABT", "PEP", "NFLX", "DIS", "PM", "INTC"]

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

def compute_geometry_features(df, vol_window=20, compression_window=30, vector_window=5):
    df = df.copy()

    # Returns
    df["Returns"] = df["Close"].pct_change()

    # Volatility
    df["Volatility"] = df["Returns"].rolling(vol_window).std()

    # Volatility Compression
    vol_ma = df["Volatility"].rolling(compression_window).mean()
    df["Compression_Ratio"] = df["Volatility"] / vol_ma

    # Velocity
    df["Price_Velocity"] = df["Close"].pct_change(vector_window)
    df["Vol_Velocity"] = df["Volatility"].diff(vector_window)

    # Acceleration
    df["Acceleration"] = df["Price_Velocity"].diff()

    # Curvature
    df["Curvature"] = df["Acceleration"].diff()

    # Vector Magnitude
    df["Vector_Magnitude"] = np.sqrt(
        (df["Price_Velocity"] ** 2) + (df["Vol_Velocity"] ** 2)
    )

    # Trajectory Angle
    df["Trajectory_Angle"] = np.arctan2(df["Vol_Velocity"], df["Price_Velocity"])

    # Volume Pressure
    vol_ma20 = df["Volume"].rolling(20).mean()
    df["Volume_Pressure"] = df["Volume"] / vol_ma20

    # Volatility Expansion
    df["Vol_Expansion"] = df["Volatility"] / df["Volatility"].shift(5)

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
    angle_threshold=0.0,
    geometry_score_threshold=0.60
):
    df = df.copy()

    # Feature Scores
    compression_score = np.where(df["Compression_Ratio"] < compression_threshold, 1, 0)
    expansion_score = np.where(df["Vol_Expansion"] > expansion_threshold, 1, 0)
    curvature_score = np.where(df["Curvature"] > curvature_threshold, 1, 0)
    magnitude_score = np.where(df["Vector_Magnitude"].rank(pct=True) > magnitude_threshold, 1, 0)
    angle_score = np.where(df["Trajectory_Angle"] > angle_threshold, 1, 0)
    volume_score = np.where(df["Volume_Pressure"] > 1.2, 1, 0)

    # Final Geometry Score
    df["Geometry_Score"] = (
        0.25 * compression_score +
        0.20 * expansion_score +
        0.20 * curvature_score +
        0.15 * magnitude_score +
        0.10 * angle_score +
        0.10 * volume_score
    )

    # Signals
    df["BUY_SIGNAL"] = df["Geometry_Score"] >= geometry_score_threshold

    # Exit Signal
    df["SELL_SIGNAL"] = (
        (df["Geometry_Score"] < geometry_score_threshold * 0.5)
        | (df["Curvature"] < 0)
    )

    return df

# ============================================================
# LOAD DATA IN BATCHES
# ============================================================

def load_all_data(tickers, params):
    all_data = {}
    batch_size = 100
    total_tickers = len(tickers)
    
    print(f"Downloading {total_tickers} tickers in batches of {batch_size} for 10 years...")
    for i in range(0, total_tickers, batch_size):
        batch = tickers[i:i+batch_size]
        print(f"   Batch {i//batch_size + 1}/{int(np.ceil(total_tickers/batch_size))}: downloading {len(batch)} tickers...")
        try:
            df_batch = yf.download(
                batch,
                start="2016-07-16",
                end="2026-07-16",
                group_by="ticker",
                auto_adjust=True,
                progress=False
            )
            
            for t in batch:
                if t in df_batch:
                    df_t = df_batch[t].dropna(subset=['Close'])
                    if df_t.empty or len(df_t) < 250:
                        continue
                    
                    df_t = normalize_index(df_t)
                    df_t = compute_geometry_features(
                        df_t,
                        vol_window=params["vol_window"],
                        compression_window=params["compression_window"],
                        vector_window=params["vector_window"]
                    )
                    df_t = build_geometry_signals(
                        df_t,
                        compression_threshold=params["compression_threshold"],
                        expansion_threshold=params["expansion_threshold"],
                        curvature_threshold=params["curvature_threshold"],
                        magnitude_threshold=params["magnitude_threshold"],
                        angle_threshold=params["angle_threshold"],
                        geometry_score_threshold=params["geometry_score_threshold"]
                    )
                    all_data[t] = df_t
        except Exception as e:
            print(f"   Error in batch starting at {i}: {e}")
            
    print(f"Successfully loaded data for {len(all_data)} tickers.")
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

    print(f"\nRunning backtest across {len(dates)} dates...")
    
    # Pre-align all dataframes to the master dates index to speed up indexing 100x
    print("Pre-aligning dataframes to master dates index...")
    aligned_data = {}
    for ticker, df in all_data.items():
        aligned_data[ticker] = df.reindex(dates)
        
    for idx, current_date in enumerate(dates):
        # ====================================================
        # EXITS
        # ====================================================
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
                proceeds = gross
                profit = proceeds - pos["invested"]
                
                cash += proceeds
                holding_days = (current_date - pos["entry_date"]).days
                
                trade_record = {
                    "Stock": ticker,
                    "Entry Date": pos["entry_date"],
                    "Exit Date": current_date,
                    "Entry Price": pos["entry_price"],
                    "Exit Price": row["Close"],
                    "Profit": profit,
                    "Return %": (profit / pos["invested"]) * 100,
                    "Reason": reason,
                    "Holding_Days": holding_days
                }
                trade_log.append(trade_record)
                
                del positions[ticker]

        # ====================================================
        # ENTRIES
        # ====================================================
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
                        "invested": allocation_per_slot
                    }

        # ====================================================
        # EQUITY
        # ====================================================
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

    win_rate = (trades["Profit"] > 0).mean() * 100 if len(trades) > 0 else 0
    total_return = (final_capital / INITIAL_CAPITAL - 1) * 100

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
    tickers = load_sp500_tickers()
    # Test on full S&P 500 tickers list
    tickers = tickers[:500]

    params = {
        "vol_window": 20,
        "compression_window": 30,
        "vector_window": 5,
        "compression_threshold": 0.20,
        "expansion_threshold": 1.10,
        "curvature_threshold": 0.05,
        "magnitude_threshold": 0.60,
        "angle_threshold": 0.0,
        "geometry_score_threshold": 0.60
    }

    print("\n[1/3] Loading stock data for S&P 500 tickers...")
    all_data = load_all_data(tickers, params)

    print("\n[2/3] Running Geometry Strategy on US stocks...")
    trades, equity_curve = run_backtest(all_data)

    results = evaluate_strategy(trades, equity_curve)

    print("\n================ RESULTS (S&P 500 10-YEAR) ================\n")
    for k, v in results.items():
        if k == "Final Capital":
            print(f"{k}: USD {v:,.2f}")
        else:
            print(f"{k}: {v}")
    print("============================================================\n")

    # ========================================================
    # SAVE EXCEL
    # ========================================================
    excel_path = "market_geometry_us_results.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame([results]).to_excel(writer, sheet_name="Summary", index=False)
        trades.to_excel(writer, sheet_name="Trades", index=False)
    print(f"Saved results Excel to: {excel_path}")

    # ========================================================
    # PLOT EQUITY CURVE
    # ========================================================
    plt.figure(figsize=(15, 7))
    plt.plot(equity_curve, color="#ff007f", lw=2, label="Geometry 3D Vector Field (S&P 500)")
    plt.axhline(INITIAL_CAPITAL, color="gray", lw=1, ls="--", label="Initial Capital")
    plt.yscale("log")
    plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"${x/1e6:.1f}M" if x >= 1e6 else (f"${x/1e3:.0f}k" if x >= 1e3 else f"${x:.0f}")
    ))
    plt.title("10-Year S&P 500 Market Geometry Equity Curve (Log Scale)")
    plt.xlabel("Time (Trading Days)")
    plt.ylabel("Portfolio Value (USD)")
    plt.grid(True, color="#222", ls=":")
    plt.legend()
    
    chart_path = "market_geometry_us_equity_curve.png"
    plt.savefig(chart_path, dpi=300, facecolor="#06060e")
    print(f"Saved equity curve chart to: {chart_path}")
