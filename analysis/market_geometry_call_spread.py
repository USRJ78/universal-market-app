"""
==============================================================================
  MARKET GEOMETRY BULL CALL SPREAD TIMING ENGINE
==============================================================================

THEORY:
  In Jim Simons / Differential Geometry framework, market state is modeled
  as a dynamic vector field on a differential manifold.

  Option spreads require:
    1. Low Entry Volatility  --> Potential Energy Compression (cheap debit)
    2. Positive Acceleration --> Kinetic Thrust Vector (S moves through strike K1 to K2)
    3. Positive Curvature    --> Convexity Inflection Point (trend acceleration)
    4. Volume Density        --> Manifold Mass Accumulation

  GEOMETRIC INDICATORS:
    - Velocity (v): 5-day rolling mean log return
    - Acceleration (a): 1st derivative of velocity (da/dt)
    - Curvature (k): 2nd derivative of velocity (d^2v/dt^2)
    - Volatility Potential (V_pot): ATR(10) / ATR(50) [Compression metric]
    - Mass Accumulation (M): Volume / Rolling 20d Volume

  GEOMETRIC ENTRY RULE:
    - Volatility Potential < 0.85 (Volatility Squeeze / Compression)
    - Acceleration > 0 AND Curvature > 0 (Positive Inflection Vector)
    - Trend Persistence > 0.60 (Directional Vector Field alignment)
    - Volume Density > 1.2 (Energy Input)

  DYNAMIC STRIKE GEOMETRY:
    - Long Call K1  : ATM (S)
    - Short Call K2 : S * (1 + 1.0 * Vol_30d * sqrt(30/365))  [1-Sigma Geometric Band]
    - Expiry DTE    : 30 days

OUTPUTS:
  - market_geometry_call_spread_results.xlsx / .csv
  - market_geometry_call_spread_chart.png
==============================================================================
"""

import os, sys, warnings, datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy.stats import norm, binomtest

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────
INITIAL_CAPITAL  = 100_000     # Base capital
RISK_PER_TRADE   = 0.02        # 2% fixed risk per spread
DTE              = 30          # 30 calendar days
RISK_FREE        = 0.065
OUTPUT_DIR       = os.path.dirname(os.path.abspath(__file__))

NSE_TOP_GEOMETRY_STOCKS = [
    "ANANTRAJ.NS", "ABB.NS", "ABREL.NS", "ANGELONE.NS", "APOLLO.NS",
    "APARINDS.NS", "AIIL.NS", "ANANDRATHI.NS", "ABCAPITAL.NS", "AJMERA.NS",
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "BAJFINANCE.NS", "TITAN.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "LTIM.NS"
]


# ─────────────────────────────────────────────
# BLACK-SCHOLES
# ─────────────────────────────────────────────
def bs_call(S, K, T_years, r, sigma):
    if T_years <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T_years) / (sigma * np.sqrt(T_years))
    d2 = d1 - sigma * np.sqrt(T_years)
    return float(S * norm.cdf(d1) - K * np.exp(-r * T_years) * norm.cdf(d2))


def spread_debit(S, K1, K2, T_days, r, sigma):
    T = T_days / 365.0
    return max(bs_call(S, K1, T, r, sigma) - bs_call(S, K2, T, r, sigma), 0.0)


def spread_payoff_pct(S_T, K1, K2, debit):
    intrinsic = min(max(S_T - K1, 0.0), K2 - K1)
    return ((intrinsic - debit) / debit * 100.0) if debit > 0 else 0.0


# ─────────────────────────────────────────────
# MARKET GEOMETRY VECTOR MANIFOLD
# ─────────────────────────────────────────────
def compute_market_geometry(df):
    close = df["Close"]
    vol   = df["Volume"]

    log_ret = np.log(close / close.shift(1))

    # 1. Kinematics (Velocity, Acceleration, Curvature)
    velocity     = log_ret.rolling(5).mean()
    acceleration = velocity.diff(2)
    curvature    = acceleration.diff(2)

    # 2. Volatility Compression Manifold (ATR Ratio)
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)

    atr10 = tr.rolling(10).mean()
    atr50 = tr.rolling(50).mean()
    vol_potential = atr10 / (atr50 + 1e-9)   # < 0.95 indicates vol compression (squeeze)

    # 3. 20d Historical Volatility
    hv20 = log_ret.rolling(20).std() * np.sqrt(252)

    # 4. Trend Persistence Vector (Ratio of positive return days over lookback)
    persistence = (log_ret > 0).rolling(15).mean()

    # 5. Mass Density (Volume Anomaly)
    vol_ma = vol.rolling(20).mean()
    mass_density = vol / (vol_ma + 1e-9)

    # 6. Geometric Signals
    sig_squeeze     = (vol_potential < 0.90)              # Volatility potential energy compressed
    sig_pos_accel   = (acceleration > 0)                  # Positive kinetic acceleration
    sig_pos_curv    = (curvature > 0)                     # Convex inflection point
    sig_persistence = (persistence >= 0.53)               # Vector field directional alignment
    sig_mass        = (mass_density >= 1.15)              # Mass density accumulation

    # Composite Vector Score (0 to 5)
    vector_score = (sig_squeeze.astype(int) +
                    sig_pos_accel.astype(int) +
                    sig_pos_curv.astype(int) +
                    sig_persistence.astype(int) +
                    sig_mass.astype(int))

    # High Geometry Conviction Entry Rule
    entry = (vector_score >= 3) & sig_pos_accel & sig_persistence

    return pd.DataFrame({
        "Close":         close,
        "HV20":          hv20,
        "Velocity":      velocity,
        "Acceleration":  acceleration,
        "Curvature":     curvature,
        "VolPotential":  vol_potential,
        "Persistence":   persistence,
        "MassDensity":   mass_density,
        "VectorScore":   vector_score,
        "Entry":         entry.astype(int)
    }, index=df.index)


# ─────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────
def run_geometry_backtest(stock_data):
    trades = []
    fixed_risk = INITIAL_CAPITAL * RISK_PER_TRADE

    for ticker, df in stock_data.items():
        geom = compute_market_geometry(df)

        entry_dates = geom.index[geom["Entry"] == 1]

        for entry_date in entry_dates:
            loc = df.index.get_loc(entry_date)
            exit_loc = loc + 21  # ~30 calendar days
            if exit_loc >= len(df):
                continue

            S  = float(geom.loc[entry_date, "Close"])
            hv = float(geom.loc[entry_date, "HV20"])
            if S <= 0 or np.isnan(hv) or hv <= 0 or hv > 5.0:
                continue

            # Geometric strike positioning: 1-Sigma Expected Move
            sigma_30d = hv * np.sqrt(30 / 365.0)
            target_pct = max(0.02, min(0.08, sigma_30d))

            K1 = max(round(S / 5) * 5, 5)
            K2 = max(round(S * (1 + target_pct) / 5) * 5, K1 + 5)

            debit = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
            if debit <= 0 or debit >= (K2 - K1):
                continue

            units = max(1, int(fixed_risk / debit))
            total_debit = debit * units

            exit_date = df.index[exit_loc]
            S_T = float(df.loc[exit_date, "Close"])
            ret_pct = spread_payoff_pct(S_T, K1, K2, debit)
            pnl_total = (ret_pct / 100.0) * total_debit
            win = ret_pct > 0

            row = geom.loc[entry_date]
            trades.append({
                "Ticker":       ticker,
                "Entry_Date":   entry_date,
                "Exit_Date":    exit_date,
                "S_entry":      round(S, 2),
                "K1_Long":      K1,
                "K2_Short":     K2,
                "Breakeven":    round(K1 + debit, 2),
                "S_expiry":     round(S_T, 2),
                "Move_%":       round((S_T - S) / S * 100, 2),
                "HV20":         round(hv, 4),
                "VolPotential": round(float(row["VolPotential"]), 3),
                "VectorScore":  int(row["VectorScore"]),
                "Debit/unit":   round(debit, 2),
                "Debit_%S":     round(debit / S * 100, 3),
                "Units":        units,
                "PnL_Total":    round(pnl_total, 2),
                "Return_%":     round(ret_pct, 2),
                "Win":          win,
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# LIVE GEOMETRY SCANNER
# ─────────────────────────────────────────────
def scan_live_geometry(stock_data):
    live_signals = []
    for ticker, df in stock_data.items():
        geom = compute_market_geometry(df)
        last = geom.iloc[-1]
        if last["Entry"] == 1:
            S  = float(last["Close"])
            hv = float(last["HV20"])
            if S > 0 and not np.isnan(hv) and 0 < hv < 5:
                sigma_30d = hv * np.sqrt(30 / 365.0)
                target_pct = max(0.02, min(0.08, sigma_30d))
                K1 = max(round(S / 5) * 5, 5)
                K2 = max(round(S * (1 + target_pct) / 5) * 5, K1 + 5)
                deb = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
                live_signals.append({
                    "Ticker":        ticker,
                    "Signal_Date":   geom.index[-1].date(),
                    "Price":         round(S, 2),
                    "K1_Long":       K1,
                    "K2_Short":      K2,
                    "Est_Debit":     round(deb, 2),
                    "VectorScore":   int(last["VectorScore"]),
                    "VolPotential":  round(float(last["VolPotential"]), 3),
                    "Acceleration":  round(float(last["Acceleration"]), 5),
                })
    return pd.DataFrame(live_signals)


# ─────────────────────────────────────────────
# ANALYSIS & PLOTTING
# ─────────────────────────────────────────────
def analyse_and_plot(df_trades, stock_data):
    if df_trades.empty:
        print("[WARN] No trades generated.")
        return

    df_trades = df_trades.sort_values("Entry_Date").reset_index(drop=True)
    df_trades["CumPnL"] = df_trades["PnL_Total"].cumsum() + INITIAL_CAPITAL

    total   = len(df_trades)
    wins    = int(df_trades["Win"].sum())
    wr      = wins / total * 100
    avg_r   = df_trades["Return_%"].mean()
    sharpe  = avg_r / df_trades["Return_%"].std() * np.sqrt(252 / 21) if df_trades["Return_%"].std() > 0 else 0
    tot_pnl = df_trades["PnL_Total"].sum()
    final   = INITIAL_CAPITAL + tot_pnl

    binom_p = binomtest(wins, total, p=0.5, alternative="greater").pvalue

    print("\n" + "=" * 62)
    print("  MARKET GEOMETRY BULL CALL SPREAD — RESULTS")
    print("=" * 62)
    print(f"  Total Trades        : {total}")
    print(f"  Win Rate            : {wr:.1f}%")
    print(f"  Avg Return/Spread   : {avg_r:.1f}%")
    print(f"  Sharpe Ratio        : {sharpe:.2f}")
    print(f"  Total PnL           : Rs.{tot_pnl:,.0f}")
    print(f"  Final Capital       : Rs.{final:,.0f}")
    print(f"  Binomial p-value    : {binom_p:.4f} "
          f"({'SIGNIFICANT' if binom_p < 0.05 else 'not significant'})")
    print("=" * 62)

    # Breakdown by Stock
    by_t = (df_trades.groupby("Ticker")
                     .agg(Trades=("Win", "count"),
                          WinRate=("Win", lambda x: round(x.mean() * 100, 1)),
                          AvgRet=("Return_%", "mean"),
                          TotalPnL=("PnL_Total", "sum"))
                     .sort_values("WinRate", ascending=False))
    print(f"\n  PER-STOCK BREAKDOWN:\n{by_t.to_string()}")

    # Plot
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig = plt.figure(figsize=(18, 12))
    fig.patch.set_facecolor(p["bg"])
    gs  = gridspec.GridSpec(2, 2, hspace=0.45, wspace=0.35)

    def sa(ax, title):
        ax.set_facecolor(p["panel"])
        ax.tick_params(colors=p["muted"], labelsize=9)
        ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # 1. Equity Curve
    ax1 = fig.add_subplot(gs[0, :])
    sa(ax1, "Market Geometry Call Spread — Cumulative Performance")
    ax1.plot(df_trades.index, df_trades["CumPnL"], color=p["blue"], lw=2, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8)
    ax1.fill_between(df_trades.index, INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] >= INITIAL_CAPITAL), alpha=0.15, color=p["green"])
    ax1.fill_between(df_trades.index, INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] < INITIAL_CAPITAL), alpha=0.20, color=p["red"])
    ax1.set_ylabel("Capital (Rs.)", color=p["muted"])

    # 2. Win rate by Vector Score
    ax2 = fig.add_subplot(gs[1, 0])
    sa(ax2, "Win Rate by Market Geometry Vector Score")
    by_score = df_trades.groupby("VectorScore")["Win"].agg(["mean", "count"]).reset_index()
    cols = [p["green"] if w >= 0.55 else p["red"] for w in by_score["mean"]]
    bars = ax2.bar(by_score["VectorScore"].astype(str), by_score["mean"] * 100, color=cols, edgecolor="#30363d")
    for bar, (_, row) in zip(bars, by_score.iterrows()):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"n={int(row['count'])}",
                 ha="center", fontsize=8, color=p["muted"])
    ax2.set_xlabel("Vector Score (3-5)", color=p["muted"])
    ax2.set_ylabel("Win Rate %", color=p["muted"])

    # 3. Win Rate per Ticker
    ax3 = fig.add_subplot(gs[1, 1])
    sa(ax3, "Win Rate by Stock")
    by_t_plot = by_t.query("Trades >= 3").sort_values("WinRate", ascending=True)
    if not by_t_plot.empty:
        t_cols = [p["green"] if w >= 60 else p["yellow"] if w >= 50 else p["red"] for w in by_t_plot["WinRate"]]
        ax3.barh(by_t_plot.index.str.replace(".NS", ""), by_t_plot["WinRate"], color=t_cols, edgecolor="#30363d")
        ax3.axvline(50, color=p["muted"], ls="--", lw=0.8)
        ax3.set_xlabel("Win Rate %", color=p["muted"])

    plt.suptitle("MARKET GEOMETRY VECTOR MANIFOLD  |  BULL CALL SPREAD TIMING", color=p["text"], fontsize=12, fontweight="bold", y=0.99)
    out = os.path.join(OUTPUT_DIR, "market_geometry_call_spread_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Chart saved -> {out}")

    # Save Excel/CSV
    out_xlsx = os.path.join(OUTPUT_DIR, "market_geometry_call_spread_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "market_geometry_call_spread_results.csv")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_trades.to_excel(w, sheet_name="Trades", index=False)
        by_t.to_excel(w, sheet_name="By Stock", index=False)
    df_trades.to_csv(out_csv, index=False)
    print(f"[OK] Excel saved -> {out_xlsx}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 62)
    print("  MARKET GEOMETRY VECTOR FIELD — BULL CALL SPREAD ENGINE")
    print("=" * 62)

    stock_data = {}
    print(f"\n[1] Downloading data for {len(NSE_TOP_GEOMETRY_STOCKS)} stocks ...")
    for ticker in NSE_TOP_GEOMETRY_STOCKS:
        try:
            df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
            if df is not None and len(df) > 300:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                stock_data[ticker] = df
                print(f"  [OK] {ticker}")
        except Exception:
            pass

    print(f"\n[2] Running Market Geometry Backtest across {len(stock_data)} stocks ...")
    trades_df = run_geometry_backtest(stock_data)

    print("\n[3] Checking LIVE Market Geometry signals for TODAY ...")
    live_df = scan_live_geometry(stock_data)
    if not live_df.empty:
        print(f"  *** {len(live_df)} LIVE GEOMETRY SIGNALS TODAY ***")
        print(live_df.to_string(index=False))
    else:
        print("  No live geometry signals today.")

    analyse_and_plot(trades_df, stock_data)
    print("\n[DONE]")
