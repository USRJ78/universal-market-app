"""
==============================================================================
  MARKET GEOMETRY V2 — HIGH CONVICTION VECTOR FIELD ENGINE
==============================================================================

WHAT CHANGED FROM GEOMETRY V1:
  1. Strict Vector Score requirement: VectorScore >= 4 (Max alignment of Vol Squeeze,
     Acceleration, Curvature, Mass Density, and Persistence).
  2. Strict Squeeze Filter: VolPotential <= 0.88 (Ensures cheap debit entry).
  3. Positive Acceleration & Positive Curvature MANDATORY (Inflection Point).
  4. Top Geometry Stocks: Focus on assets with proven geometric momentum.

OUTPUTS:
  - market_geometry_v2_results.xlsx / .csv
  - market_geometry_v2_chart.png
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
INITIAL_CAPITAL  = 100_000
RISK_PER_TRADE   = 0.02
DTE              = 30
RISK_FREE        = 0.065
OUTPUT_DIR       = os.path.dirname(os.path.abspath(__file__))

GEOMETRY_V2_STOCKS = [
    "ANANTRAJ.NS", "ANANDRATHI.NS", "AIIL.NS", "APARINDS.NS", "ABREL.NS",
    "TITAN.NS", "ABCAPITAL.NS", "ANGELONE.NS", "BHARTIARTL.NS", "APOLLO.NS",
    "ABB.NS", "AJMERA.NS", "BAJFINANCE.NS", "RELIANCE.NS", "TCS.NS"
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
# MARKET GEOMETRY V2 ENGINE
# ─────────────────────────────────────────────
def compute_geometry_v2(df):
    close = df["Close"]
    vol   = df["Volume"]

    log_ret = np.log(close / close.shift(1))

    # Kinematics
    velocity     = log_ret.rolling(5).mean()
    acceleration = velocity.diff(2)
    curvature    = acceleration.diff(2)

    # Volatility Squeeze
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)

    atr10 = tr.rolling(10).mean()
    atr50 = tr.rolling(50).mean()
    vol_potential = atr10 / (atr50 + 1e-9)

    hv20 = log_ret.rolling(20).std() * np.sqrt(252)
    persistence = (log_ret > 0).rolling(15).mean()

    vol_ma = vol.rolling(20).mean()
    mass_density = vol / (vol_ma + 1e-9)

    # Sub-signals
    sig_squeeze     = (vol_potential <= 0.88)
    sig_pos_accel   = (acceleration > 0)
    sig_pos_curv    = (curvature > 0)
    sig_persistence = (persistence >= 0.53)
    sig_mass        = (mass_density >= 1.20)

    vector_score = (sig_squeeze.astype(int) +
                    sig_pos_accel.astype(int) +
                    sig_pos_curv.astype(int) +
                    sig_persistence.astype(int) +
                    sig_mass.astype(int))

    # STRICT V2 GEOMETRIC ENTRY
    entry = (vector_score >= 4) & sig_squeeze & sig_pos_accel & sig_pos_curv

    return pd.DataFrame({
        "Close":        close,
        "HV20":         hv20,
        "Velocity":     velocity,
        "Acceleration": acceleration,
        "Curvature":    curvature,
        "VolPotential": vol_potential,
        "Persistence":  persistence,
        "MassDensity":  mass_density,
        "VectorScore":  vector_score,
        "Entry":        entry.astype(int)
    }, index=df.index)


# ─────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────
def run_backtest_v2(stock_data):
    trades = []
    fixed_risk = INITIAL_CAPITAL * RISK_PER_TRADE

    for ticker, df in stock_data.items():
        geom = compute_geometry_v2(df)
        entry_dates = geom.index[geom["Entry"] == 1]

        for entry_date in entry_dates:
            loc = df.index.get_loc(entry_date)
            exit_loc = loc + 21   # 30 calendar days ~ 21 trading days
            if exit_loc >= len(df):
                continue

            S  = float(geom.loc[entry_date, "Close"])
            hv = float(geom.loc[entry_date, "HV20"])
            if S <= 0 or np.isnan(hv) or hv <= 0 or hv > 5.0:
                continue

            # 1.0 Sigma Band for Short Strike
            sigma_30d = hv * np.sqrt(30 / 365.0)
            target_pct = max(0.03, min(0.08, sigma_30d))

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
# LIVE GEOMETRY SCANNER V2
# ─────────────────────────────────────────────
def scan_live_geometry_v2(stock_data):
    live_signals = []
    for ticker, df in stock_data.items():
        geom = compute_geometry_v2(df)
        last = geom.iloc[-1]
        if last["Entry"] == 1:
            S  = float(last["Close"])
            hv = float(last["HV20"])
            if S > 0 and not np.isnan(hv) and 0 < hv < 5:
                sigma_30d = hv * np.sqrt(30 / 365.0)
                target_pct = max(0.03, min(0.08, sigma_30d))
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
# ANALYSE & PLOT
# ─────────────────────────────────────────────
def analyse_and_plot(df_trades):
    if df_trades.empty:
        print("[WARN] No V2 trades generated. Filters might be too strict.")
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
    print("  MARKET GEOMETRY V2 — STRICT HIGH CONVICTION RESULTS")
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

    # Equity Curve
    ax1 = fig.add_subplot(gs[0, :])
    sa(ax1, f"Market Geometry V2 Equity Curve  |  Win Rate: {wr:.1f}%  |  {total} High-Conviction Trades")
    ax1.plot(df_trades.index, df_trades["CumPnL"], color=p["blue"], lw=2, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8)
    ax1.fill_between(df_trades.index, INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] >= INITIAL_CAPITAL), alpha=0.15, color=p["green"])
    ax1.fill_between(df_trades.index, INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] < INITIAL_CAPITAL), alpha=0.20, color=p["red"])
    ax1.set_ylabel("Capital (Rs.)", color=p["muted"])

    # Win rate by Volatility Potential Squeeze
    ax2 = fig.add_subplot(gs[1, 0])
    sa(ax2, "Win Rate by Volatility Squeeze (VolPotential)")
    df_trades["SqueezeBucket"] = pd.cut(df_trades["VolPotential"], bins=[0, 0.70, 0.80, 0.88, 1.0],
                                        labels=["<0.70", "0.70-0.80", "0.80-0.88", ">0.88"])
    by_sq = df_trades.groupby("SqueezeBucket", observed=True)["Win"].agg(["mean", "count"]).reset_index()
    cols = [p["green"] if w >= 0.55 else p["red"] for w in by_sq["mean"]]
    bars = ax2.bar(by_sq["SqueezeBucket"].astype(str), by_sq["mean"] * 100, color=cols, edgecolor="#30363d")
    for bar, (_, row) in zip(bars, by_sq.iterrows()):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"n={int(row['count'])}",
                 ha="center", fontsize=8, color=p["muted"])
    ax2.set_xlabel("VolPotential Ratio (ATR10 / ATR50)", color=p["muted"])
    ax2.set_ylabel("Win Rate %", color=p["muted"])

    # Win Rate per Ticker
    ax3 = fig.add_subplot(gs[1, 1])
    sa(ax3, "Win Rate by Stock (V2 Engine)")
    by_t_plot = by_t.sort_values("WinRate", ascending=True)
    if not by_t_plot.empty:
        t_cols = [p["green"] if w >= 60 else p["yellow"] if w >= 50 else p["red"] for w in by_t_plot["WinRate"]]
        ax3.barh(by_t_plot.index.str.replace(".NS", ""), by_t_plot["WinRate"], color=t_cols, edgecolor="#30363d")
        ax3.axvline(50, color=p["muted"], ls="--", lw=0.8)
        ax3.set_xlabel("Win Rate %", color=p["muted"])

    plt.suptitle("MARKET GEOMETRY V2  |  STRICT VECTOR MANIFOLD SQUEEZE ENGINE", color=p["text"], fontsize=12, fontweight="bold", y=0.99)
    out = os.path.join(OUTPUT_DIR, "market_geometry_v2_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] V2 Chart saved -> {out}")

    out_xlsx = os.path.join(OUTPUT_DIR, "market_geometry_v2_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "market_geometry_v2_results.csv")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_trades.to_excel(w, sheet_name="Trades", index=False)
        by_t.to_excel(w, sheet_name="By Stock", index=False)
    df_trades.to_csv(out_csv, index=False)
    print(f"[OK] V2 Excel saved -> {out_xlsx}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 62)
    print("  MARKET GEOMETRY V2 — STRICT VECTOR FIELD ENGINE")
    print("=" * 62)

    stock_data = {}
    print(f"\n[1] Downloading data for {len(GEOMETRY_V2_STOCKS)} stocks ...")
    for ticker in GEOMETRY_V2_STOCKS:
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

    print(f"\n[2] Running Market Geometry V2 Backtest across {len(stock_data)} stocks ...")
    trades_df = run_backtest_v2(stock_data)

    print("\n[3] Checking LIVE Market Geometry V2 signals ...")
    live_df = scan_live_geometry_v2(stock_data)
    if not live_df.empty:
        print(f"  *** {len(live_df)} LIVE GEOMETRY V2 SIGNALS TODAY ***")
        print(live_df.to_string(index=False))
    else:
        print("  No live geometry V2 signals today.")

    analyse_and_plot(trades_df)
    print("\n[DONE]")
