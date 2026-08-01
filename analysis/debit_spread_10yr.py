"""
==============================================================================
  10-YEAR BULL CALL DEBIT SPREAD BACKTESTER (2016 - 2026)
==============================================================================

PURPOSE:
  Run a rigorous 10-year backtest of the Bull Call Debit Spread strategy
  across top liquid NSE stocks & Nifty 50 to evaluate long-term robustness,
  CAGR, Max Drawdown, and Year-by-Year performance.

STRATEGY RULES:
  1. Entry Trigger:
     - Market Regime: Price > 200-day EMA (Bullish Trend)
     - Volatility Squeeze: ATR(10) / ATR(50) < 0.95 (Low IV Entry)
     - Momentum: RSI(14) between 50 and 75

  2. Spread Structure:
     - Long Call (K1)  : ATM Strike
     - Short Call (K2) : 3% - 5% OTM Strike (1.0 Sigma Expected Move)
     - Expiry          : 30 Calendar Days (21 Trading Days)

  3. Risk Management:
     - Fixed Risk: 2% of initial capital per trade
     - Max Loss per trade: Limited to Net Debit paid

OUTPUTS:
  - debit_spread_10yr_results.xlsx / .csv
  - debit_spread_10yr_chart.png
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
# CONFIGURATION
# ─────────────────────────────────────────────
INITIAL_CAPITAL  = 100_000     # Rs. 1,000,000 base capital
RISK_PER_TRADE   = 0.02        # 2% fixed risk per spread
DTE              = 30          # 30 calendar days
RISK_FREE        = 0.065       # 6.5% interest rate
OUTPUT_DIR       = os.path.dirname(os.path.abspath(__file__))

STOCKS_10YR = [
    "^NSEI",         # Nifty 50 Index
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "BHARTIARTL.NS",
    "TITAN.NS",
    "BAJFINANCE.NS",
    "LT.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS"
]


# ─────────────────────────────────────────────
# BLACK-SCHOLES PRICING ENGINE
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
# INDICATORS & SIGNALS
# ─────────────────────────────────────────────
def compute_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_signals(df):
    close  = df["Close"]
    ema200 = close.ewm(span=200, adjust=False).mean()
    rsi14  = compute_rsi(close, 14)

    # Volatility Squeeze (10d ATR vs 50d ATR)
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)

    atr10 = tr.rolling(10).mean()
    atr50 = tr.rolling(50).mean()
    vol_potential = atr10 / (atr50 + 1e-9)

    # 20-day Realized Volatility
    log_ret = np.log(close / close.shift(1))
    hv20    = log_ret.rolling(20).std() * np.sqrt(252)

    # Signal Rules
    sig_trend   = (close > ema200)
    sig_squeeze = (vol_potential < 0.95)
    sig_rsi     = (rsi14 >= 50) & (rsi14 <= 75)

    entry = sig_trend & sig_squeeze & sig_rsi

    return pd.DataFrame({
        "Close":        close,
        "EMA200":       ema200,
        "RSI14":        rsi14,
        "VolPotential": vol_potential,
        "HV20":         hv20,
        "Entry":        entry.astype(int)
    }, index=df.index)


# ─────────────────────────────────────────────
# 10-YEAR BACKTEST ENGINE
# ─────────────────────────────────────────────
def run_10yr_backtest(stock_data):
    trades = []
    fixed_risk = INITIAL_CAPITAL * RISK_PER_TRADE

    for ticker, df in stock_data.items():
        sigs = compute_signals(df)
        entry_dates = sigs.index[sigs["Entry"] == 1]

        last_exit = df.index[0]

        for entry_date in entry_dates:
            if entry_date <= last_exit:
                continue

            loc = df.index.get_loc(entry_date)
            exit_loc = loc + 21  # 21 trading days ~ 30 calendar days
            if exit_loc >= len(df):
                continue

            S  = float(sigs.loc[entry_date, "Close"])
            hv = float(sigs.loc[entry_date, "HV20"])
            if S <= 0 or np.isnan(hv) or hv <= 0 or hv > 5.0:
                continue

            # Calculate 1-Sigma Expected Move for short strike (capped 3-6%)
            sigma_30d = hv * np.sqrt(30 / 365.0)
            target_pct = max(0.03, min(0.06, sigma_30d))

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

            last_exit = exit_date

            row = sigs.loc[entry_date]
            trades.append({
                "Ticker":       ticker.replace("^NSEI", "NIFTY50"),
                "Entry_Date":   entry_date,
                "Exit_Date":    exit_date,
                "Year":         entry_date.year,
                "S_entry":      round(S, 2),
                "K1_Long":      K1,
                "K2_Short":     K2,
                "Breakeven":    round(K1 + debit, 2),
                "S_expiry":     round(S_T, 2),
                "Move_%":       round((S_T - S) / S * 100, 2),
                "HV20":         round(hv, 4),
                "RSI14":        round(float(row["RSI14"]), 1),
                "VolPotential": round(float(row["VolPotential"]), 3),
                "Debit/unit":   round(debit, 2),
                "Debit_%S":     round(debit / S * 100, 3),
                "Units":        units,
                "PnL_Total":    round(pnl_total, 2),
                "Return_%":     round(ret_pct, 2),
                "Win":          win,
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# STATISTICAL ANALYSIS & VISUALIZATION
# ─────────────────────────────────────────────
def analyse_and_plot(df_trades):
    if df_trades.empty:
        print("[WARN] No trades generated.")
        return

    df_trades = df_trades.sort_values("Entry_Date").reset_index(drop=True)
    df_trades["CumPnL"] = df_trades["PnL_Total"].cumsum() + INITIAL_CAPITAL

    total     = len(df_trades)
    wins      = int(df_trades["Win"].sum())
    wr        = wins / total * 100
    avg_r     = df_trades["Return_%"].mean()
    std_r     = df_trades["Return_%"].std()
    sharpe    = avg_r / std_r * np.sqrt(252 / 21) if std_r > 0 else 0
    tot_pnl   = df_trades["PnL_Total"].sum()
    final_cap = INITIAL_CAPITAL + tot_pnl

    start_yr  = df_trades["Year"].min()
    end_yr    = df_trades["Year"].max()
    num_years = max(1, end_yr - start_yr + 1)
    cagr      = ((final_cap / INITIAL_CAPITAL) ** (1.0 / num_years) - 1) * 100

    # Drawdown calculation
    peak = df_trades["CumPnL"].cummax()
    dd = (df_trades["CumPnL"] - peak) / peak * 100
    max_dd = dd.min()

    binom_p = binomtest(wins, total, p=0.5, alternative="greater").pvalue

    print("\n" + "=" * 65)
    print(f"  10-YEAR BULL CALL DEBIT SPREAD BACKTEST ({start_yr} - {end_yr})")
    print("=" * 65)
    print(f"  Total Trades        : {total}")
    print(f"  Win Rate            : {wr:.1f}%")
    print(f"  Avg Return / Spread : {avg_r:.1f}%")
    print(f"  10-Year CAGR        : {cagr:.1f}%")
    print(f"  Max Drawdown        : {max_dd:.1f}%")
    print(f"  Sharpe Ratio        : {sharpe:.2f}")
    print(f"  Initial Capital     : Rs.{INITIAL_CAPITAL:,.0f}")
    print(f"  Final Capital       : Rs.{final_cap:,.0f}")
    print(f"  Total Profit        : Rs.{tot_pnl:,.0f}")
    print(f"  Binomial p-value    : {binom_p:.4f} "
          f"({'SIGNIFICANT' if binom_p < 0.05 else 'not significant'})")
    print("=" * 65)

    # Breakdown by Year
    by_yr = (df_trades.groupby("Year")
                      .agg(Trades=("Win", "count"),
                           WinRate=("Win", lambda x: round(x.mean() * 100, 1)),
                           AvgReturn=("Return_%", "mean"),
                           PnL=("PnL_Total", "sum"))
                      .reset_index())
    print(f"\n  YEAR-BY-YEAR PERFORMANCE:\n{by_yr.to_string(index=False)}")

    # Breakdown by Stock
    by_t = (df_trades.groupby("Ticker")
                     .agg(Trades=("Win", "count"),
                          WinRate=("Win", lambda x: round(x.mean() * 100, 1)),
                          AvgReturn=("Return_%", "mean"),
                          TotalPnL=("PnL_Total", "sum"))
                     .sort_values("WinRate", ascending=False)
                     .reset_index())
    print(f"\n  TICKER BREAKDOWN:\n{by_t.to_string(index=False)}")

    # ─────────────────────────────────────────
    # PLOT CHART
    # ─────────────────────────────────────────
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor(p["bg"])
    gs  = gridspec.GridSpec(3, 2, hspace=0.45, wspace=0.32)

    def sa(ax, title):
        ax.set_facecolor(p["panel"])
        ax.tick_params(colors=p["muted"], labelsize=9)
        ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # 1. Equity Curve
    ax1 = fig.add_subplot(gs[0, :])
    sa(ax1, f"10-Year Cumulative Equity Curve  |  CAGR: {cagr:.1f}%  |  Win Rate: {wr:.1f}%  |  Max DD: {max_dd:.1f}%")
    ax1.plot(df_trades["Entry_Date"], df_trades["CumPnL"], color=p["blue"], lw=2, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8)
    ax1.fill_between(df_trades["Entry_Date"], INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] >= INITIAL_CAPITAL), alpha=0.15, color=p["green"])
    ax1.fill_between(df_trades["Entry_Date"], INITIAL_CAPITAL, df_trades["CumPnL"],
                     where=(df_trades["CumPnL"] < INITIAL_CAPITAL), alpha=0.20, color=p["red"])
    ax1.set_ylabel("Capital (Rs.)", color=p["muted"])

    # 2. Win Rate by Year
    ax2 = fig.add_subplot(gs[1, 0])
    sa(ax2, "Win Rate by Year (2016 - 2026)")
    cols = [p["green"] if w >= 55 else p["yellow"] if w >= 45 else p["red"] for w in by_yr["WinRate"]]
    bars = ax2.bar(by_yr["Year"].astype(str), by_yr["WinRate"], color=cols, edgecolor="#30363d")
    for bar, (_, row) in zip(bars, by_yr.iterrows()):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"n={int(row['Trades'])}",
                 ha="center", fontsize=8, color=p["muted"])
    ax2.axhline(50, color=p["muted"], ls="--", lw=0.8)
    ax2.set_xlabel("Year", color=p["muted"])
    ax2.set_ylabel("Win Rate %", color=p["muted"])
    ax2.set_ylim(0, 110)

    # 3. PnL by Year
    ax3 = fig.add_subplot(gs[1, 1])
    sa(ax3, "Net Profit / Loss (Rs.) by Year")
    pnl_cols = [p["green"] if pnl >= 0 else p["red"] for pnl in by_yr["PnL"]]
    ax3.bar(by_yr["Year"].astype(str), by_yr["PnL"], color=pnl_cols, edgecolor="#30363d")
    ax3.axhline(0, color=p["muted"], lw=0.8)
    ax3.set_xlabel("Year", color=p["muted"])
    ax3.set_ylabel("PnL (Rs.)", color=p["muted"])

    # 4. Win Rate by Ticker
    ax4 = fig.add_subplot(gs[2, 0])
    sa(ax4, "Win Rate by Ticker")
    by_t_sorted = by_t.sort_values("WinRate", ascending=True)
    t_cols = [p["green"] if w >= 55 else p["yellow"] if w >= 45 else p["red"] for w in by_t_sorted["WinRate"]]
    ax4.barh(by_t_sorted["Ticker"], by_t_sorted["WinRate"], color=t_cols, edgecolor="#30363d")
    ax4.axvline(50, color=p["muted"], ls="--", lw=0.8)
    ax4.set_xlabel("Win Rate %", color=p["muted"])

    # 5. Return Distribution
    ax5 = fig.add_subplot(gs[2, 1])
    sa(ax5, "Return % Distribution per Spread")
    wins_dist = df_trades[df_trades["Win"]]["Return_%"]
    loss_dist = df_trades[~df_trades["Win"]]["Return_%"]
    ax5.hist(loss_dist, bins=25, color=p["red"], alpha=0.7, label=f"Loss (n={len(loss_dist)})")
    ax5.hist(wins_dist, bins=25, color=p["green"], alpha=0.7, label=f"Win (n={len(wins_dist)})")
    ax5.axvline(0, color=p["muted"], lw=1)
    ax5.axvline(avg_r, color=p["yellow"], lw=1.5, ls="--", label=f"Avg={avg_r:.1f}%")
    ax5.set_xlabel("Return %", color=p["muted"])
    ax5.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d", fontsize=8)

    plt.suptitle(f"10-YEAR BULL CALL DEBIT SPREAD BACKTEST (2016-2026)  |  Overall Win Rate: {wr:.1f}%  |  {total} Trades",
                 color=p["text"], fontsize=12, fontweight="bold", y=0.99)

    out_chart = os.path.join(OUTPUT_DIR, "debit_spread_10yr_chart.png")
    plt.savefig(out_chart, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] 10-Yr Chart saved -> {out_chart}")

    # Save Excel & CSV
    out_xlsx = os.path.join(OUTPUT_DIR, "debit_spread_10yr_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "debit_spread_10yr_results.csv")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_trades.to_excel(w, sheet_name="All Trades", index=False)
        by_yr.to_excel(w, sheet_name="By Year", index=False)
        by_t.to_excel(w, sheet_name="By Ticker", index=False)
    df_trades.to_csv(out_csv, index=False)
    print(f"[OK] 10-Yr Excel saved -> {out_xlsx}")


# ─────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  10-YEAR BULL CALL DEBIT SPREAD BACKTESTER (2016 - 2026)")
    print("=" * 65)

    stock_data = {}
    print(f"\n[1] Downloading 10-Year historical data for {len(STOCKS_10YR)} tickers ...")
    for ticker in STOCKS_10YR:
        try:
            df = yf.download(ticker, period="10y", interval="1d", auto_adjust=True, progress=False)
            if df is not None and len(df) > 1000:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                stock_data[ticker] = df
                print(f"  [OK] {ticker} ({len(df)} daily bars)")
        except Exception as e:
            print(f"  [--] {ticker} failed: {e}")

    print(f"\n[2] Running 10-Year Backtest across {len(stock_data)} tickers ...")
    df_trades = run_10yr_backtest(stock_data)

    analyse_and_plot(df_trades)
    print("\n[DONE] 10-Year Backtest Complete.")
