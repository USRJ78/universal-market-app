"""
==============================================================================
  BULL CALL SPREAD TIMING ENGINE V2 — High-Conviction Breakout Filter
==============================================================================

V2 PHILOSOPHY:
  Quality over quantity. Instead of firing on generic momentum signals,
  we look for RARE, high-conviction breakout setups where:
    - The stock is already in a strong bull trend (both EMAs)
    - It is JUST breaking out to new 52-week highs (momentum ignition)
    - Volume confirms institutional buying (2x average)
    - RSI is above 60 (not overbought, but confirmed strength)
    - Market regime is bullish (Nifty above 200 EMA)
    - The spread debit is cheap (<1.5% of stock price)

  ALL 6 conditions must fire simultaneously for an entry.

SPREAD PARAMETERS:
  - Long Call  : ATM strike  (current close, rounded to nearest 5)
  - Short Call : 5% OTM strike
  - Expiry     : 30 calendar days (~21 trading days)
  - Risk-free  : 6.5%

OUTPUTS:
  - call_spread_v2_results.xlsx
  - call_spread_v2_results.csv
  - call_spread_v2_chart.png
==============================================================================
"""

import os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy.stats import norm

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────
INITIAL_CAPITAL   = 100_000
RISK_PER_TRADE    = 0.02        # 2% capital per spread
SPREAD_WIDTH_PCT  = 0.05        # 5% OTM short strike
DTE               = 30          # calendar days
RISK_FREE         = 0.065
MAX_DEBIT_PCT     = 0.015       # debit must be < 1.5% of stock price
TICKERS_LIMIT     = 150
NIFTY_TICKER      = "^NSEI"
OUTPUT_DIR        = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────
# BLACK-SCHOLES
# ─────────────────────────────────────────────
def bs_call(S, K, T_years, r, sigma):
    if T_years <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T_years) / (sigma * np.sqrt(T_years))
    d2 = d1 - sigma * np.sqrt(T_years)
    return float(S * norm.cdf(d1) - K * np.exp(-r * T_years) * norm.cdf(d2))


def bull_spread_debit(S, K1, K2, T_days, r, sigma):
    T = T_days / 365.0
    return bs_call(S, K1, T, r, sigma) - bs_call(S, K2, T, r, sigma)


def spread_payoff(S_T, K1, K2, debit):
    intrinsic = max(0.0, min(S_T - K1, K2 - K1))
    return intrinsic - debit


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_hv(close, window=20):
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252)


def compute_signals_v2(df, nifty_200ema):
    """
    6 high-conviction filters. All must be True for entry.
    Returns a DataFrame with signal columns + composite boolean.
    """
    close = df["Close"]
    vol   = df["Volume"]

    ema50  = close.ewm(span=50,  adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    rsi    = compute_rsi(close, 14)
    hv     = compute_hv(close, 20)
    vol_ma = vol.rolling(20).mean()

    # ── Signal 1: 52-week breakout — close > highest close of last 252 days
    high_252 = close.shift(1).rolling(252).max()
    sig1_breakout = (close > high_252).astype(int)

    # ── Signal 2: Strong trend — price above BOTH 50 & 200 EMA
    sig2_trend = ((close > ema50) & (close > ema200)).astype(int)

    # ── Signal 3: RSI momentum — RSI between 60 and 80 (strong, not overbought)
    sig3_rsi = ((rsi >= 60) & (rsi <= 80)).astype(int)

    # ── Signal 4: Volume confirmation — volume > 2x 20-day average
    sig4_volume = (vol > vol_ma * 2.0).astype(int)

    # ── Signal 5: Bull market regime — Nifty above its 200 EMA
    nifty_signal = nifty_200ema.reindex(df.index, method="ffill")
    sig5_regime  = nifty_signal.astype(int)

    # ── Signal 6: Cheap debit — computed later per trade, stored as placeholder
    # (evaluated in backtester against MAX_DEBIT_PCT)

    # All 5 structural signals must fire (debit check in backtester)
    all_structural = (sig1_breakout & sig2_trend & sig3_rsi & sig4_volume & sig5_regime)

    return pd.DataFrame({
        "Close":          close,
        "HV":             hv,
        "RSI":            rsi,
        "EMA50":          ema50,
        "EMA200":         ema200,
        "High252":        high_252,
        "Sig1_Breakout":  sig1_breakout,
        "Sig2_Trend":     sig2_trend,
        "Sig3_RSI":       sig3_rsi,
        "Sig4_Volume":    sig4_volume,
        "Sig5_Regime":    sig5_regime,
        "AllStructural":  all_structural.astype(int),
    }, index=df.index)


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
def load_nse_tickers():
    try:
        eq   = pd.read_csv(
            "C:/Users/USER/OneDrive/Documents/universal-market-app/EQUITY_L.csv"
        )
        syms = eq["SYMBOL"].dropna().tolist()
        return [s + ".NS" for s in syms]
    except Exception:
        return [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
            "LT.NS","WIPRO.NS","HCLTECH.NS","AXISBANK.NS","ASIANPAINT.NS",
            "MARUTI.NS","NESTLEIND.NS","ULTRACEMCO.NS","TITAN.NS","BAJFINANCE.NS",
        ]


def load_data(tickers, period="5y"):
    data = {}
    ok, fail = 0, 0
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            if df is not None and len(df) > 400:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[ticker] = df
                ok += 1
                if ok % 25 == 0:
                    print(f"  Loaded {ok} stocks ...")
        except Exception:
            fail += 1
    print(f"[OK] Loaded {ok} stocks ({fail} skipped)")
    return data


def load_nifty_regime(period="5y"):
    """Returns boolean Series: True when Nifty is above its 200 EMA."""
    try:
        nifty = yf.download(NIFTY_TICKER, period=period, interval="1d",
                            auto_adjust=True, progress=False)
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)
        close   = nifty["Close"]
        ema200  = close.ewm(span=200, adjust=False).mean()
        return (close > ema200)
    except Exception:
        print("  [WARN] Could not load Nifty — regime filter OFF")
        return pd.Series(dtype=bool)


# ─────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────
def run_backtest(stock_data, nifty_regime):
    trades  = []
    capital = float(INITIAL_CAPITAL)

    for ticker, df in stock_data.items():
        try:
            sigs = compute_signals_v2(df, nifty_regime)
        except Exception:
            continue

        entry_idx = sigs.index[sigs["AllStructural"] == 1]

        for entry_date in entry_idx:
            loc      = df.index.get_loc(entry_date)
            exit_loc = loc + 21   # ~30 calendar days
            if exit_loc >= len(df):
                continue

            S  = float(sigs.loc[entry_date, "Close"])
            hv = float(sigs.loc[entry_date, "HV"])
            if S <= 0 or np.isnan(hv) or hv <= 0:
                continue

            # Strikes
            K1 = max(round(S / 5) * 5, 5)
            K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 5) * 5, K1 + 5)

            # Debit check (Signal 6)
            debit = bull_spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
            if debit <= 0:
                continue
            if debit / S > MAX_DEBIT_PCT:   # debit too expensive — skip
                continue

            # Position sizing
            units       = max(1, int((capital * RISK_PER_TRADE) / debit))
            total_debit = debit * units

            # Outcome
            exit_date  = df.index[exit_loc]
            S_T        = float(df.loc[exit_date, "Close"])
            pnl_unit   = spread_payoff(S_T, K1, K2, debit)
            pnl_total  = pnl_unit * units
            win        = pnl_unit > 0
            ret_pct    = pnl_unit / debit * 100
            breakeven  = K1 + debit

            capital += pnl_total

            row = sigs.loc[entry_date]
            trades.append({
                "Ticker":         ticker,
                "Entry Date":     entry_date,
                "Exit Date":      exit_date,
                "S_entry":        round(S, 2),
                "K1_Long":        K1,
                "K2_Short":       K2,
                "Breakeven":      round(breakeven, 2),
                "S_expiry":       round(S_T, 2),
                "HV":             round(hv, 4),
                "RSI_entry":      round(float(row["RSI"]), 1),
                "Debit/unit":     round(debit, 2),
                "Debit_pct_S":    round(debit / S * 100, 3),
                "Units":          units,
                "Total_Debit":    round(total_debit, 2),
                "PnL/unit":       round(pnl_unit, 2),
                "PnL_Total":      round(pnl_total, 2),
                "Return_%":       round(ret_pct, 2),
                "Win":            win,
                "Sig1_Breakout":  int(row["Sig1_Breakout"]),
                "Sig2_Trend":     int(row["Sig2_Trend"]),
                "Sig3_RSI":       int(row["Sig3_RSI"]),
                "Sig4_Volume":    int(row["Sig4_Volume"]),
                "Sig5_Regime":    int(row["Sig5_Regime"]),
                "Capital_After":  round(capital, 2),
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────
def analyse(df):
    if df.empty:
        print("No trades generated — filters too strict or insufficient data.")
        return {}

    total  = len(df)
    wins   = df["Win"].sum()
    wr     = wins / total * 100
    avg_r  = df["Return_%"].mean()
    sharpe = df["Return_%"].mean() / df["Return_%"].std() * np.sqrt(252/21) \
             if df["Return_%"].std() > 0 else 0
    final  = df["Capital_After"].iloc[-1]

    print("\n" + "=" * 55)
    print("  BULL CALL SPREAD V2 — SUMMARY")
    print("=" * 55)
    print(f"  Total Trades    : {total}")
    print(f"  Win Rate        : {wr:.1f}%")
    print(f"  Avg Return      : {avg_r:.1f}% per spread")
    print(f"  Best Trade      : {df['Return_%'].max():.1f}%")
    print(f"  Worst Trade     : {df['Return_%'].min():.1f}%")
    print(f"  Sharpe Ratio    : {sharpe:.2f}")
    print(f"  Final Capital   : Rs.{final:,.0f}")
    print(f"  CAGR (approx)   : {((final/INITIAL_CAPITAL)**(1/5)-1)*100:.1f}%")
    print("=" * 55)

    # Top 10 tickers by win rate
    by_ticker = (df.groupby("Ticker")
                   .agg(Trades=("Win","count"),
                        WinRate=("Win", lambda x: round(x.mean()*100,1)),
                        AvgReturn=("Return_%","mean"))
                   .query("Trades >= 3")
                   .sort_values("WinRate", ascending=False)
                   .head(10))
    if not by_ticker.empty:
        print("\n  TOP 10 TICKERS BY WIN RATE (min 3 trades):")
        print(by_ticker.to_string())

    return {"total": total, "win_rate": wr, "avg_return": avg_r,
            "sharpe": sharpe, "final": final}


# ─────────────────────────────────────────────
# PLOTTING
# ─────────────────────────────────────────────
def plot_results(df):
    if df.empty:
        return

    df = df.sort_values("Entry Date").reset_index(drop=True)

    palette = {
        "bg":    "#0d1117", "panel":  "#161b22",
        "green": "#39d353", "red":    "#f85149",
        "blue":  "#58a6ff", "yellow": "#e3b341",
        "text":  "#c9d1d9", "muted":  "#8b949e",
    }

    fig = plt.figure(figsize=(18, 13))
    fig.patch.set_facecolor(palette["bg"])
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.55, wspace=0.38)

    def style_ax(ax, title):
        ax.set_facecolor(palette["panel"])
        ax.tick_params(colors=palette["muted"], labelsize=9)
        ax.set_title(title, color=palette["text"], fontsize=10,
                     fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # ── 1. Equity Curve (full width top)
    ax1 = fig.add_subplot(gs[0, :])
    style_ax(ax1, "Equity Curve  |  Bull Call Spread V2  |  150 NSE Stocks  |  5 Years")
    ax1.plot(df.index, df["Capital_After"], color=palette["blue"], lw=1.8, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=palette["muted"], ls="--", lw=0.8, alpha=0.6)
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital_After"],
                     where=(df["Capital_After"] >= INITIAL_CAPITAL),
                     alpha=0.15, color=palette["green"])
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital_After"],
                     where=(df["Capital_After"] < INITIAL_CAPITAL),
                     alpha=0.20, color=palette["red"])
    final_cap = df["Capital_After"].iloc[-1]
    color_final = palette["green"] if final_cap >= INITIAL_CAPITAL else palette["red"]
    ax1.annotate(f"Rs.{final_cap:,.0f}", xy=(df.index[-1], final_cap),
                 xytext=(-60, 10), textcoords="offset points",
                 color=color_final, fontsize=10, fontweight="bold")
    ax1.set_ylabel("Capital (Rs.)", color=palette["muted"])
    ax1.yaxis.label.set_color(palette["muted"])

    # ── 2. Win vs Loss distribution
    ax2 = fig.add_subplot(gs[1, 0])
    style_ax(ax2, "Return Distribution")
    wins   = df[df["Win"]]["Return_%"]
    losses = df[~df["Win"]]["Return_%"]
    ax2.hist(losses, bins=25, color=palette["red"],   alpha=0.75, label=f"Loss (n={len(losses)})")
    ax2.hist(wins,   bins=25, color=palette["green"], alpha=0.75, label=f"Win  (n={len(wins)})")
    ax2.axvline(0, color=palette["muted"], lw=1)
    ax2.set_xlabel("Return per Spread (%)", color=palette["muted"])
    ax2.xaxis.label.set_color(palette["muted"])
    ax2.legend(facecolor=palette["panel"], labelcolor=palette["text"],
               edgecolor="#30363d", fontsize=8)

    # ── 3. Win rate by RSI bucket
    ax3 = fig.add_subplot(gs[1, 1])
    style_ax(ax3, "Win Rate by RSI at Entry")
    df["RSI_bucket"] = pd.cut(df["RSI_entry"], bins=[60,65,70,75,80],
                               labels=["60-65","65-70","70-75","75-80"])
    rsi_wr = df.groupby("RSI_bucket", observed=True)["Win"].agg(["mean","count"])
    colors = [palette["green"] if w >= 0.5 else palette["red"]
              for w in rsi_wr["mean"]]
    bars = ax3.bar(rsi_wr.index.astype(str), rsi_wr["mean"]*100,
                   color=colors, edgecolor="#30363d", lw=0.5)
    for bar, (idx, row) in zip(bars, rsi_wr.iterrows()):
        ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8,
                 color=palette["muted"])
    ax3.set_ylabel("Win Rate %", color=palette["muted"])
    ax3.yaxis.label.set_color(palette["muted"])
    ax3.set_ylim(0, 110)

    # ── 4. Win rate by debit % of stock price
    ax4 = fig.add_subplot(gs[1, 2])
    style_ax(ax4, "Win Rate by Debit Cost (% of S)")
    df["Debit_bucket"] = pd.cut(df["Debit_pct_S"],
                                 bins=[0, 0.5, 0.75, 1.0, 1.25, 1.5],
                                 labels=["<0.5%","0.5-0.75%","0.75-1%","1-1.25%","1.25-1.5%"])
    d_wr = df.groupby("Debit_bucket", observed=True)["Win"].agg(["mean","count"])
    colors2 = [palette["green"] if w >= 0.5 else palette["red"] for w in d_wr["mean"]]
    bars2 = ax4.bar(d_wr.index.astype(str), d_wr["mean"]*100,
                    color=colors2, edgecolor="#30363d", lw=0.5)
    for bar, (idx, row) in zip(bars2, d_wr.iterrows()):
        ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8,
                 color=palette["muted"])
    ax4.set_ylabel("Win Rate %", color=palette["muted"])
    ax4.yaxis.label.set_color(palette["muted"])
    ax4.tick_params(axis="x", labelrotation=30)
    ax4.set_ylim(0, 110)

    # ── 5. Monthly trade count
    ax5 = fig.add_subplot(gs[2, :2])
    style_ax(ax5, "Monthly Trades Generated (Entry Signals)")
    df["Month"] = pd.to_datetime(df["Entry Date"]).dt.to_period("M")
    monthly = df.groupby("Month").size()
    ax5.bar(monthly.index.astype(str), monthly.values,
            color=palette["blue"], alpha=0.75, edgecolor="#30363d", lw=0.4)
    ax5.set_ylabel("# Trades", color=palette["muted"])
    ax5.yaxis.label.set_color(palette["muted"])
    ax5.tick_params(axis="x", labelrotation=45, labelsize=7)

    # ── 6. Top 10 tickers
    ax6 = fig.add_subplot(gs[2, 2])
    style_ax(ax6, "Top 10 Tickers by Win Rate")
    top = (df.groupby("Ticker")
             .agg(Trades=("Win","count"), WinRate=("Win","mean"))
             .query("Trades >= 3")
             .sort_values("WinRate", ascending=True)
             .tail(10))
    if not top.empty:
        colors3 = [palette["green"] if w >= 0.5 else palette["red"]
                   for w in top["WinRate"]]
        ax6.barh(top.index.str.replace(".NS",""), top["WinRate"]*100,
                 color=colors3, edgecolor="#30363d", lw=0.4)
        ax6.axvline(50, color=palette["muted"], ls="--", lw=0.8, alpha=0.6)
        ax6.set_xlabel("Win Rate %", color=palette["muted"])
        ax6.xaxis.label.set_color(palette["muted"])

    plt.suptitle("BULL CALL SPREAD V2  |  HIGH-CONVICTION BREAKOUT TIMING ENGINE",
                 color=palette["text"], fontsize=13, fontweight="bold", y=0.99)

    out = os.path.join(OUTPUT_DIR, "call_spread_v2_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=palette["bg"])
    plt.close()
    print(f"[OK] Chart saved -> {out}")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
def save_results(df):
    if df.empty:
        return

    # Best trades — debit < 1%, win rate analysis
    df_sorted = df.sort_values("Entry Date")

    # by-ticker summary
    by_ticker = (df.groupby("Ticker")
                   .agg(Trades=("Win","count"),
                        WinRate=("Win", lambda x: round(x.mean()*100,1)),
                        AvgReturn=("Return_%","mean"),
                        AvgDebit=("Debit_pct_S","mean"))
                   .sort_values("WinRate", ascending=False)
                   .reset_index())

    out_xlsx = os.path.join(OUTPUT_DIR, "call_spread_v2_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "call_spread_v2_results.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_sorted.to_excel(writer, sheet_name="All Trades", index=False)
        by_ticker.to_excel(writer, sheet_name="By Ticker", index=False)
        df[df["Debit_pct_S"] < 0.75].to_excel(
            writer, sheet_name="Cheap Debit <0.75pct", index=False)

    df_sorted.to_csv(out_csv, index=False)
    print(f"[OK] Excel  -> {out_xlsx}")
    print(f"[OK] CSV    -> {out_csv}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  BULL CALL SPREAD V2 TIMING ENGINE")
    print("=" * 55)

    print("\n[1] Loading Nifty regime filter ...")
    nifty_regime = load_nifty_regime(period="5y")

    print("\n[2] Loading NSE stock data ...")
    tickers    = load_nse_tickers()[:TICKERS_LIMIT]
    stock_data = load_data(tickers, period="5y")

    print(f"\n[3] Running backtest on {len(stock_data)} stocks ...")
    trades_df = run_backtest(stock_data, nifty_regime)

    summary = analyse(trades_df)
    plot_results(trades_df)
    save_results(trades_df)

    print("\n[DONE] All outputs saved to analysis/ folder")
