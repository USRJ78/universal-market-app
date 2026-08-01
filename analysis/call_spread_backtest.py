"""
==============================================================================
  BULL CALL SPREAD TIMING ENGINE — NSE 300 Stock Scanner + Backtester
==============================================================================

STRATEGY:
  - Scan 300 NSE stocks daily for 5 timing signals
  - Enter 30-day ATM/5%OTM bull call spread when 3+ signals align
  - Simulate spread pricing with Black-Scholes (using 20d HV as IV proxy)
  - Track outcome at expiry: win if stock closes above breakeven

5 TIMING SIGNALS:
  1. IV Rank < 30%      — volatility cheap, debit is low
  2. Trend Confirmed    — UTBot buy OR price > 50 EMA
  3. RSI Momentum       — RSI(14) crossing above 45 from below
  4. Volume Spike       — Volume > 1.5x 20-day average
  5. ATR Expansion      — Volatility expanding after compression

ENTRY RULE:
  Score = sum of signals. Enter if Score >= 3.

SPREAD PARAMETERS:
  - Long Call  : ATM strike (≈ current close)
  - Short Call : 5% OTM strike (≈ close × 1.05)
  - Expiry     : 30 calendar days (~21 trading days)
  - Risk-free  : 6.5% (RBI repo rate proxy)

OUTPUTS:
  - call_spread_results.xlsx  — full trade log + summary by signal combo
  - call_spread_equity.png    — cumulative P&L curve
  - call_spread_winrate.png   — win rate by signal score
==============================================================================
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy.stats import norm
from itertools import combinations

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────
INITIAL_CAPITAL   = 100_000   # INR
RISK_PER_TRADE    = 0.02      # 2% of capital per spread
SPREAD_WIDTH_PCT  = 0.05      # 5% between strikes
DTE               = 30        # days to expiry (calendar)
RISK_FREE         = 0.065     # 6.5% annualised
MIN_SCORE         = 3         # minimum signals to enter
MAX_POSITIONS     = 5         # concurrent open spreads
TICKERS_LIMIT     = 100       # stocks to scan (keep fast)
OUTPUT_DIR        = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────
# HELPERS — Black-Scholes
# ─────────────────────────────────────────────
def bs_call(S, K, T_years, r, sigma):
    """Price a European call via Black-Scholes."""
    if T_years <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T_years) / (sigma * np.sqrt(T_years))
    d2 = d1 - sigma * np.sqrt(T_years)
    return float(S * norm.cdf(d1) - K * np.exp(-r * T_years) * norm.cdf(d2))


def bull_spread_debit(S, K1, K2, T_days, r, sigma):
    """Net debit to enter a bull call spread (long K1, short K2)."""
    T = T_days / 365.0
    return bs_call(S, K1, T, r, sigma) - bs_call(S, K2, T, r, sigma)


def spread_payoff(S_T, K1, K2, debit):
    """Payoff at expiry (net of debit paid)."""
    intrinsic = max(0.0, min(S_T - K1, K2 - K1))
    return intrinsic - debit


# ─────────────────────────────────────────────
# HELPERS — Technical Indicators
# ─────────────────────────────────────────────
def compute_atr(df, period=14):
    hl  = df["High"] - df["Low"]
    hc  = (df["High"] - df["Close"].shift()).abs()
    lc  = (df["Low"]  - df["Close"].shift()).abs()
    tr  = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_rsi(close, period=14):
    delta    = close.diff()
    gain     = delta.clip(lower=0).rolling(period).mean()
    loss     = (-delta.clip(upper=0)).rolling(period).mean()
    rs       = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_utbot_buy(df, key_value=3, atr_period=14):
    """Returns boolean series: True on UTBot buy cross."""
    atr    = compute_atr(df, atr_period)
    nLoss  = key_value * atr
    close  = df["Close"]
    trail  = [0.0] * len(df)
    for i in range(1, len(df)):
        prev = trail[i - 1]
        c    = close.iloc[i]
        pc   = close.iloc[i - 1]
        nl   = nLoss.iloc[i] if not np.isnan(nLoss.iloc[i]) else 0
        if c > prev and pc > prev:
            trail[i] = max(prev, c - nl)
        elif c < prev and pc < prev:
            trail[i] = min(prev, c + nl)
        elif c > prev:
            trail[i] = c - nl
        else:
            trail[i] = c + nl
    trail_s = pd.Series(trail, index=df.index)
    buy = (close > trail_s) & (close.shift(1) <= trail_s.shift(1))
    return buy


def compute_hv(close, window=20):
    """20-day historical volatility, annualised."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252)


def compute_iv_rank(hv, lookback=252):
    """Percentile rank of current HV vs trailing lookback."""
    return hv.rolling(lookback).apply(lambda x: (x[-1] > x[:-1]).mean(), raw=True)


def compute_signals(df):
    """
    Returns a DataFrame with 5 binary signal columns + composite score.
    """
    close = df["Close"]
    vol   = df["Volume"]

    hv      = compute_hv(close, 20)
    iv_rank = compute_iv_rank(hv, 252)
    rsi     = compute_rsi(close, 14)
    ema50   = close.ewm(span=50, adjust=False).mean()
    atr     = compute_atr(df, 14)
    utbot   = compute_utbot_buy(df)

    # ── Signal 1: Cheap vol (IV rank < 30th percentile)
    sig1 = (iv_rank < 0.30).astype(int)

    # ── Signal 2: Trend confirmation (UTBot buy cross OR above 50 EMA)
    sig2 = (utbot | (close > ema50)).astype(int)

    # ── Signal 3: RSI momentum cross above 45
    sig3 = ((rsi >= 45) & (rsi.shift(1) < 45)).astype(int)

    # ── Signal 4: Volume spike > 1.5× 20-day mean
    vol_ma = vol.rolling(20).mean()
    sig4   = (vol > vol_ma * 1.5).astype(int)

    # ── Signal 5: ATR expansion after compression (ATR > min of last 10 days × 1.2)
    atr_min = atr.rolling(10).min()
    sig5    = (atr > atr_min * 1.2).astype(int)

    score = sig1 + sig2 + sig3 + sig4 + sig5

    out = pd.DataFrame({
        "Close":    close,
        "HV":       hv,
        "IV_Rank":  iv_rank,
        "RSI":      rsi,
        "ATR":      atr,
        "Sig1_CheapVol": sig1,
        "Sig2_Trend":    sig2,
        "Sig3_RSI":      sig3,
        "Sig4_Volume":   sig4,
        "Sig5_ATR":      sig5,
        "Score":         score,
    }, index=df.index)
    return out


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
def load_nse_tickers():
    try:
        eq = pd.read_csv(
            "C:/Users/USER/OneDrive/Documents/universal-market-app/EQUITY_L.csv"
        )
        syms = eq["SYMBOL"].dropna().tolist()
        return [s + ".NS" for s in syms]
    except Exception:
        # fallback: Nifty 100 sample
        return [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
            "LT.NS","WIPRO.NS","HCLTECH.NS","AXISBANK.NS","ASIANPAINT.NS",
            "MARUTI.NS","NESTLEIND.NS","ULTRACEMCO.NS","TITAN.NS","BAJFINANCE.NS",
            "SUNPHARMA.NS","TATAMOTORS.NS","NTPC.NS","POWERGRID.NS","ONGC.NS",
        ]


def load_stock_data(tickers, period="3y"):
    """Download OHLCV for list of tickers; return dict ticker→DataFrame."""
    data = {}
    ok, fail = 0, 0
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            if df is not None and len(df) > 300:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[ticker] = df
                ok += 1
                if ok % 20 == 0:
                    print(f"  Loaded {ok} stocks …")
        except Exception:
            fail += 1
    print(f"✔ Loaded {ok} stocks ({fail} failed/skipped)")
    return data


# ─────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────
def run_backtest(stock_data):
    """
    For each stock, scan for entry days (Score >= MIN_SCORE),
    simulate a 30-day bull call spread, record outcomes.
    """
    trades = []
    capital = INITIAL_CAPITAL

    for ticker, df in stock_data.items():
        sigs = compute_signals(df)

        # Need at least DTE forward bars for outcome
        entry_idx = sigs.index[sigs["Score"] >= MIN_SCORE]

        for entry_date in entry_idx:
            # Find exit date ~ DTE calendar days ahead
            loc = df.index.get_loc(entry_date)
            exit_loc = loc + int(DTE * 5 / 7)  # ~21 trading days for 30 cal days
            if exit_loc >= len(df):
                continue

            S        = float(sigs.loc[entry_date, "Close"])
            hv       = float(sigs.loc[entry_date, "HV"])
            if S <= 0 or np.isnan(hv) or hv <= 0:
                continue

            # Strikes
            K1 = round(S / 5) * 5          # nearest ₹5 (ATM)
            K2 = round(S * (1 + SPREAD_WIDTH_PCT) / 5) * 5  # 5% OTM

            # Price spread at entry
            debit = bull_spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
            if debit <= 0:
                continue

            # Risk sizing
            max_loss   = debit          # per unit
            units      = max(1, int((capital * RISK_PER_TRADE) / max_loss))
            total_debit = debit * units

            # Outcome at expiry
            exit_date = df.index[exit_loc]
            S_T       = float(df.loc[exit_date, "Close"])
            pnl_unit  = spread_payoff(S_T, K1, K2, debit)
            pnl_total = pnl_unit * units

            breakeven   = K1 + debit
            max_profit  = (K2 - K1 - debit) * units
            win         = pnl_unit > 0
            return_pct  = pnl_unit / debit * 100

            capital += pnl_total

            # Extract which signals fired
            row = sigs.loc[entry_date]
            trades.append({
                "Ticker":       ticker,
                "Entry Date":   entry_date,
                "Exit Date":    exit_date,
                "S_entry":      round(S, 2),
                "K1_Long":      K1,
                "K2_Short":     K2,
                "HV":           round(hv, 4),
                "IV_Rank":      round(float(row["IV_Rank"]), 3) if not np.isnan(row["IV_Rank"]) else np.nan,
                "Debit/unit":   round(debit, 2),
                "Units":        units,
                "Total Debit":  round(total_debit, 2),
                "S_expiry":     round(S_T, 2),
                "Breakeven":    round(breakeven, 2),
                "PnL/unit":     round(pnl_unit, 2),
                "PnL Total":    round(pnl_total, 2),
                "Return %":     round(return_pct, 2),
                "Win":          win,
                "Score":        int(row["Score"]),
                "Sig1_CheapVol": int(row["Sig1_CheapVol"]),
                "Sig2_Trend":    int(row["Sig2_Trend"]),
                "Sig3_RSI":      int(row["Sig3_RSI"]),
                "Sig4_Volume":   int(row["Sig4_Volume"]),
                "Sig5_ATR":      int(row["Sig5_ATR"]),
                "Capital_After": round(capital, 2),
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────
def analyse(df):
    """Print and return summary statistics."""
    if df.empty:
        print("No trades generated.")
        return {}

    total   = len(df)
    wins    = df["Win"].sum()
    wr      = wins / total * 100
    avg_ret = df["Return %"].mean()
    best    = df["Return %"].max()
    worst   = df["Return %"].min()
    sharpe  = df["Return %"].mean() / df["Return %"].std() * np.sqrt(252 / 21) if df["Return %"].std() > 0 else 0

    print("\n" + "="*55)
    print("  BULL CALL SPREAD BACKTEST — SUMMARY")
    print("="*55)
    print(f"  Total Trades  : {total}")
    print(f"  Win Rate      : {wr:.1f}%")
    print(f"  Avg Return    : {avg_ret:.1f}% per spread")
    print(f"  Best Trade    : {best:.1f}%")
    print(f"  Worst Trade   : {worst:.1f}%")
    print(f"  Sharpe Ratio  : {sharpe:.2f}")
    print(f"  Final Capital : ₹{df['Capital_After'].iloc[-1]:,.0f}")
    print("="*55)

    # By score
    print("\n  WIN RATE BY SIGNAL SCORE:")
    by_score = df.groupby("Score").agg(
        Trades=("Win", "count"),
        WinRate=("Win", lambda x: x.mean() * 100),
        AvgReturn=("Return %", "mean")
    ).reset_index()
    print(by_score.to_string(index=False))

    # By signal combo — which signals matter most?
    sig_cols = ["Sig1_CheapVol","Sig2_Trend","Sig3_RSI","Sig4_Volume","Sig5_ATR"]
    print("\n  WIN RATE BY INDIVIDUAL SIGNAL:")
    for s in sig_cols:
        fired = df[df[s] == 1]
        if len(fired) > 10:
            print(f"    {s:20s}: WR={fired['Win'].mean()*100:.1f}%  n={len(fired)}")

    return {
        "total": total, "win_rate": wr, "avg_return": avg_ret,
        "sharpe": sharpe, "final_capital": df["Capital_After"].iloc[-1]
    }


# ─────────────────────────────────────────────
# PLOTTING
# ─────────────────────────────────────────────
def plot_results(df):
    if df.empty:
        return

    df = df.sort_values("Entry Date").reset_index(drop=True)
    df["Cumulative PnL"] = df["PnL Total"].cumsum()
    df["Cumulative PnL %"] = (df["Capital_After"] / INITIAL_CAPITAL - 1) * 100

    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor("#0d1117")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    palette = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353",
               "red": "#f85149", "blue": "#58a6ff", "text": "#c9d1d9",
               "muted": "#8b949e"}

    def style_ax(ax, title):
        ax.set_facecolor(palette["panel"])
        ax.tick_params(colors=palette["muted"], labelsize=9)
        ax.title.set_color(palette["text"])
        ax.title.set_fontsize(11)
        ax.title.set_fontweight("bold")
        ax.set_title(title, pad=10)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

    # ── 1. Equity Curve
    ax1 = fig.add_subplot(gs[0, :])
    style_ax(ax1, "📈  Equity Curve — Bull Call Spread Portfolio")
    ax1.plot(df.index, df["Capital_After"], color=palette["blue"], lw=1.5)
    ax1.axhline(INITIAL_CAPITAL, color=palette["muted"], ls="--", lw=0.8, alpha=0.5)
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital_After"],
                     where=(df["Capital_After"] >= INITIAL_CAPITAL),
                     alpha=0.15, color=palette["green"])
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital_After"],
                     where=(df["Capital_After"] < INITIAL_CAPITAL),
                     alpha=0.15, color=palette["red"])
    ax1.set_ylabel("Capital (₹)", color=palette["muted"])
    ax1.yaxis.label.set_color(palette["muted"])

    # ── 2. Win Rate by Score
    ax2 = fig.add_subplot(gs[1, 0])
    style_ax(ax2, "🎯  Win Rate by Signal Score")
    by_score = df.groupby("Score")["Win"].agg(["mean","count"]).reset_index()
    colors = [palette["green"] if w >= 0.6 else palette["red"] for w in by_score["mean"]]
    bars = ax2.bar(by_score["Score"].astype(str), by_score["mean"] * 100,
                   color=colors, edgecolor="#30363d", linewidth=0.5)
    ax2.axhline(60, color=palette["muted"], ls="--", lw=0.8, alpha=0.7)
    ax2.axhline(90, color=palette["green"], ls="--", lw=0.8, alpha=0.7)
    for bar, (_, row) in zip(bars, by_score.iterrows()):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=palette["muted"])
    ax2.set_xlabel("Signal Score (0–5)", color=palette["muted"])
    ax2.set_ylabel("Win Rate %", color=palette["muted"])
    ax2.set_ylim(0, 110)
    ax2.xaxis.label.set_color(palette["muted"])
    ax2.yaxis.label.set_color(palette["muted"])

    # ── 3. Return Distribution
    ax3 = fig.add_subplot(gs[1, 1])
    style_ax(ax3, "📊  Return Distribution per Spread")
    wins_data  = df[df["Win"] == True]["Return %"]
    losses_data = df[df["Win"] == False]["Return %"]
    ax3.hist(losses_data, bins=30, color=palette["red"],   alpha=0.7, label=f"Loss  (n={len(losses_data)})")
    ax3.hist(wins_data,   bins=30, color=palette["green"], alpha=0.7, label=f"Win   (n={len(wins_data)})")
    ax3.axvline(0, color=palette["muted"], lw=1)
    ax3.set_xlabel("Return per Spread (%)", color=palette["muted"])
    ax3.set_ylabel("Frequency", color=palette["muted"])
    ax3.xaxis.label.set_color(palette["muted"])
    ax3.yaxis.label.set_color(palette["muted"])
    legend = ax3.legend(facecolor=palette["panel"], edgecolor="#30363d",
                        labelcolor=palette["text"], fontsize=9)

    plt.suptitle("BULL CALL SPREAD — TIMING ENGINE BACKTEST",
                 color=palette["text"], fontsize=14, fontweight="bold", y=0.98)

    out_path = os.path.join(OUTPUT_DIR, "call_spread_equity.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=palette["bg"])
    plt.close()
    print(f"\n✔ Plot saved → {out_path}")


# ─────────────────────────────────────────────
# SAVE RESULTS
# ─────────────────────────────────────────────
def save_results(df, summary):
    if df.empty:
        return

    out_xlsx = os.path.join(OUTPUT_DIR, "call_spread_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "call_spread_results.csv")

    # Summary by score
    by_score = df.groupby("Score").agg(
        Trades   =("Win","count"),
        WinRate  =("Win", lambda x: round(x.mean()*100,1)),
        AvgReturn=("Return %","mean"),
        AvgDebit =("Debit/unit","mean"),
    ).reset_index()

    # Best combo: filter score >= 4
    best = df[df["Score"] >= 4].copy()

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Trades", index=False)
        by_score.to_excel(writer, sheet_name="By Score", index=False)
        best.to_excel(writer, sheet_name="High Score (4+)", index=False)

    df.to_csv(out_csv, index=False)
    print(f"✔ Results saved → {out_xlsx}")
    print(f"✔ CSV saved     → {out_csv}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  BULL CALL SPREAD TIMING ENGINE — STARTING")
    print("=" * 55)

    tickers = load_nse_tickers()[:TICKERS_LIMIT]
    print(f"\n► Scanning {len(tickers)} NSE stocks …\n")

    stock_data = load_stock_data(tickers, period="3y")
    print(f"\n► Running backtest …")

    trades_df = run_backtest(stock_data)
    summary   = analyse(trades_df)

    plot_results(trades_df)
    save_results(trades_df, summary)

    print("\n✅ DONE — all outputs saved to analysis/ folder")
