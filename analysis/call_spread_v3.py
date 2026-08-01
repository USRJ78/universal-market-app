"""
==============================================================================
  BULL CALL SPREAD TIMING ENGINE V3 — Breakout Core + Flexible Filters
==============================================================================

V3 CHANGES FROM V2:
  - 52-week high breakout + Nifty regime = MANDATORY (2 must-have filters)
  - RSI, Volume, Trend = need 2 of these 3 (flexible combo)
  - DTE extended from 30 -> 45 days (more time for move)
  - Short strike tightened from 5% -> 3% OTM (breakeven closer = easier win)
  - Debit cap removed (let the model breathe)
  - Targets ~200-500 trades for statistical significance

SPREAD STRUCTURE:
  - Long  Call : ATM (current close)
  - Short Call : 3% OTM
  - Expiry     : 45 calendar days (~31 trading days)
  - R/F rate   : 6.5%

OUTPUTS:
  - call_spread_v3_results.xlsx / .csv
  - call_spread_v3_chart.png
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
INITIAL_CAPITAL  = 100_000
RISK_PER_TRADE   = 0.02
SPREAD_WIDTH_PCT = 0.03       # 3% OTM short strike (tighter than V2's 5%)
DTE              = 45         # 45 calendar days (~31 trading days)
RISK_FREE        = 0.065
NIFTY_TICKER     = "^NSEI"
TICKERS_LIMIT    = 200        # scan more stocks
OUTPUT_DIR       = os.path.dirname(os.path.abspath(__file__))


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
    return np.log(close / close.shift(1)).rolling(window).std() * np.sqrt(252)


def compute_signals_v3(df, nifty_above_200):
    close  = df["Close"]
    vol    = df["Volume"]
    ema50  = close.ewm(span=50,  adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    rsi    = compute_rsi(close, 14)
    hv     = compute_hv(close, 20)
    vol_ma = vol.rolling(20).mean()

    # ── MANDATORY 1: 52-week high breakout
    high_252    = close.shift(1).rolling(252).max()
    m1_breakout = (close > high_252).astype(int)

    # ── MANDATORY 2: Nifty bull regime
    nifty_sig = nifty_above_200.reindex(df.index, method="ffill").fillna(False)
    m2_regime = nifty_sig.astype(int)

    # ── FLEXIBLE 1: RSI 55–80
    f1_rsi = ((rsi >= 55) & (rsi <= 80)).astype(int)

    # ── FLEXIBLE 2: Volume > 1.5x 20-day avg
    f2_vol = (vol > vol_ma * 1.5).astype(int)

    # ── FLEXIBLE 3: Strong trend — above both EMAs
    f3_trend = ((close > ema50) & (close > ema200)).astype(int)

    # Flexible score (need >= 2 of 3)
    flex_score = f1_rsi + f2_vol + f3_trend
    flex_ok    = (flex_score >= 2).astype(int)

    # ENTRY = both mandatory + 2+ flexible
    entry = (m1_breakout & m2_regime & flex_ok).astype(int)

    return pd.DataFrame({
        "Close":       close,
        "HV":          hv,
        "RSI":         rsi,
        "EMA50":       ema50,
        "EMA200":      ema200,
        "High252":     high_252,
        "M1_Breakout": m1_breakout,
        "M2_Regime":   m2_regime,
        "F1_RSI":      f1_rsi,
        "F2_Volume":   f2_vol,
        "F3_Trend":    f3_trend,
        "FlexScore":   flex_score,
        "Entry":       entry,
    }, index=df.index)


# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
def load_nse_tickers():
    try:
        eq   = pd.read_csv(
            "C:/Users/USER/OneDrive/Documents/universal-market-app/EQUITY_L.csv")
        syms = eq["SYMBOL"].dropna().tolist()
        return [s + ".NS" for s in syms]
    except Exception:
        return ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
                "ITC.NS","SBIN.NS","BHARTIARTL.NS","LT.NS","WIPRO.NS"]


def load_data(tickers, period="5y"):
    data = {}
    ok = 0
    for t in tickers:
        try:
            df = yf.download(t, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            if df is not None and len(df) > 400:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[t] = df
                ok += 1
                if ok % 25 == 0:
                    print(f"  Loaded {ok} stocks ...")
        except Exception:
            pass
    print(f"[OK] {ok} stocks loaded")
    return data


def load_nifty(period="5y"):
    try:
        df = yf.download(NIFTY_TICKER, period=period, interval="1d",
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close  = df["Close"]
        ema200 = close.ewm(span=200, adjust=False).mean()
        return (close > ema200)
    except Exception:
        print("  [WARN] Nifty load failed - regime filter disabled")
        return pd.Series(dtype=bool)


# ─────────────────────────────────────────────
# BACKTEST
# ─────────────────────────────────────────────
def run_backtest(stock_data, nifty_regime):
    trades  = []
    capital = float(INITIAL_CAPITAL)
    trading_days = int(DTE * 5 / 7)  # ~31 for 45 cal days

    for ticker, df in stock_data.items():
        try:
            sigs = compute_signals_v3(df, nifty_regime)
        except Exception:
            continue

        for entry_date in sigs.index[sigs["Entry"] == 1]:
            loc      = df.index.get_loc(entry_date)
            exit_loc = loc + trading_days
            if exit_loc >= len(df):
                continue

            S  = float(sigs.loc[entry_date, "Close"])
            hv = float(sigs.loc[entry_date, "HV"])
            if S <= 0 or np.isnan(hv) or hv <= 0:
                continue

            K1 = max(round(S / 5) * 5, 5)
            K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 5) * 5, K1 + 5)

            debit = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
            if debit <= 0:
                continue

            units      = max(1, int((capital * RISK_PER_TRADE) / debit))
            total_deb  = debit * units

            exit_date  = df.index[exit_loc]
            S_T        = float(df.loc[exit_date, "Close"])
            pnl_unit   = spread_payoff(S_T, K1, K2, debit)
            pnl_total  = pnl_unit * units
            win        = pnl_unit > 0
            ret_pct    = pnl_unit / debit * 100
            capital   += pnl_total

            row = sigs.loc[entry_date]
            trades.append({
                "Ticker":      ticker,
                "Entry_Date":  entry_date,
                "Exit_Date":   exit_date,
                "S_entry":     round(S, 2),
                "K1_Long":     K1,
                "K2_Short":    K2,
                "Breakeven":   round(K1 + debit, 2),
                "S_expiry":    round(S_T, 2),
                "HV":          round(hv, 4),
                "RSI":         round(float(row["RSI"]), 1),
                "Debit/unit":  round(debit, 2),
                "Debit_pct":   round(debit / S * 100, 3),
                "Units":       units,
                "PnL/unit":    round(pnl_unit, 2),
                "PnL_Total":   round(pnl_total, 2),
                "Return_%":    round(ret_pct, 2),
                "Win":         win,
                "M1_Breakout": int(row["M1_Breakout"]),
                "M2_Regime":   int(row["M2_Regime"]),
                "F1_RSI":      int(row["F1_RSI"]),
                "F2_Volume":   int(row["F2_Volume"]),
                "F3_Trend":    int(row["F3_Trend"]),
                "FlexScore":   int(row["FlexScore"]),
                "Capital":     round(capital, 2),
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# ANALYSE
# ─────────────────────────────────────────────
def analyse(df):
    if df.empty:
        print("[WARN] No trades generated.")
        return {}

    df = df.sort_values("Entry_Date").reset_index(drop=True)
    total  = len(df)
    wr     = df["Win"].mean() * 100
    avg_r  = df["Return_%"].mean()
    sharpe = (df["Return_%"].mean() / df["Return_%"].std()
              * np.sqrt(252 / trading_days())
              if df["Return_%"].std() > 0 else 0)
    final  = df["Capital"].iloc[-1]
    cagr   = ((final / INITIAL_CAPITAL) ** (1/5) - 1) * 100

    print("\n" + "=" * 60)
    print("  BULL CALL SPREAD V3 — RESULTS")
    print("=" * 60)
    print(f"  Total Trades      : {total}")
    print(f"  Win Rate          : {wr:.1f}%")
    print(f"  Avg Return/Spread : {avg_r:.1f}%")
    print(f"  Best Trade        : {df['Return_%'].max():.1f}%")
    print(f"  Worst Trade       : {df['Return_%'].min():.1f}%")
    print(f"  Sharpe Ratio      : {sharpe:.2f}")
    print(f"  Final Capital     : Rs.{final:,.0f}")
    print(f"  CAGR (5yr)        : {cagr:.1f}%")
    print("=" * 60)

    # By flex score
    print("\n  WIN RATE BY FLEX SCORE:")
    by_fs = (df.groupby("FlexScore")
               .agg(Trades=("Win","count"),
                    WinRate=("Win", lambda x: round(x.mean()*100,1)),
                    AvgRet=("Return_%","mean"))
               .reset_index())
    print(by_fs.to_string(index=False))

    # Top tickers
    top = (df.groupby("Ticker")
             .agg(Trades=("Win","count"),
                  WinRate=("Win", lambda x: round(x.mean()*100,1)),
                  AvgRet=("Return_%","mean"))
             .query("Trades >= 2")
             .sort_values("WinRate", ascending=False)
             .head(15))
    print(f"\n  TOP TICKERS (min 2 trades):\n{top.to_string()}")

    return {"total":total,"win_rate":wr,"avg_return":avg_r,"sharpe":sharpe,"final":final}


def trading_days():
    return int(DTE * 5 / 7)


# ─────────────────────────────────────────────
# PLOT
# ─────────────────────────────────────────────
def plot_results(df):
    if df.empty:
        return

    df = df.sort_values("Entry_Date").reset_index(drop=True)
    p = {"bg":"#0d1117","panel":"#161b22","green":"#39d353","red":"#f85149",
         "blue":"#58a6ff","yellow":"#e3b341","text":"#c9d1d9","muted":"#8b949e"}

    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor(p["bg"])
    gs  = gridspec.GridSpec(3, 3, hspace=0.55, wspace=0.38)

    def sa(ax, title):
        ax.set_facecolor(p["panel"])
        ax.tick_params(colors=p["muted"], labelsize=9)
        ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # Equity
    ax1 = fig.add_subplot(gs[0, :])
    sa(ax1, "Equity Curve  |  V3 Bull Call Spread  |  3% OTM  |  45-Day Expiry  |  5 Years")
    ax1.plot(df.index, df["Capital"], color=p["blue"], lw=1.8, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital"],
                     where=(df["Capital"] >= INITIAL_CAPITAL),
                     alpha=0.15, color=p["green"])
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["Capital"],
                     where=(df["Capital"] < INITIAL_CAPITAL),
                     alpha=0.20, color=p["red"])
    fin = df["Capital"].iloc[-1]
    ax1.annotate(f"Rs.{fin:,.0f}", xy=(df.index[-1], fin),
                 xytext=(-80, 12), textcoords="offset points",
                 color=p["green"] if fin >= INITIAL_CAPITAL else p["red"],
                 fontsize=11, fontweight="bold")
    ax1.set_ylabel("Capital (Rs.)", color=p["muted"])
    ax1.yaxis.label.set_color(p["muted"])

    # Return distribution
    ax2 = fig.add_subplot(gs[1, 0])
    sa(ax2, "Return Distribution")
    w = df[df["Win"]]["Return_%"]
    l = df[~df["Win"]]["Return_%"]
    ax2.hist(l, bins=25, color=p["red"],   alpha=0.75, label=f"Loss (n={len(l)})")
    ax2.hist(w, bins=25, color=p["green"], alpha=0.75, label=f"Win  (n={len(w)})")
    ax2.axvline(0, color=p["muted"], lw=1)
    ax2.set_xlabel("Return %", color=p["muted"])
    ax2.xaxis.label.set_color(p["muted"])
    ax2.legend(facecolor=p["panel"], labelcolor=p["text"],
               edgecolor="#30363d", fontsize=8)

    # Win rate by FlexScore
    ax3 = fig.add_subplot(gs[1, 1])
    sa(ax3, "Win Rate by Flexible Signal Count")
    by_fs = df.groupby("FlexScore")["Win"].agg(["mean","count"])
    cols = [p["green"] if v >= 0.5 else p["red"] for v in by_fs["mean"]]
    bars = ax3.bar(by_fs.index.astype(str), by_fs["mean"]*100,
                   color=cols, edgecolor="#30363d", lw=0.5)
    for bar, (idx, row) in zip(bars, by_fs.iterrows()):
        ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=9, color=p["muted"])
    ax3.set_xlabel("Flexible Signals Fired (of 3)", color=p["muted"])
    ax3.set_ylabel("Win Rate %", color=p["muted"])
    ax3.xaxis.label.set_color(p["muted"])
    ax3.yaxis.label.set_color(p["muted"])
    ax3.set_ylim(0, 115)

    # Win rate by RSI bucket
    ax4 = fig.add_subplot(gs[1, 2])
    sa(ax4, "Win Rate by RSI at Entry")
    df["RSI_b"] = pd.cut(df["RSI"], bins=[55,60,65,70,75,80],
                          labels=["55-60","60-65","65-70","70-75","75-80"])
    rb = df.groupby("RSI_b", observed=True)["Win"].agg(["mean","count"])
    rc = [p["green"] if v >= 0.5 else p["red"] for v in rb["mean"]]
    bars4 = ax4.bar(rb.index.astype(str), rb["mean"]*100,
                    color=rc, edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars4, rb.iterrows()):
        ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=p["muted"])
    ax4.set_ylabel("Win Rate %", color=p["muted"])
    ax4.yaxis.label.set_color(p["muted"])
    ax4.set_ylim(0, 115)

    # Monthly trades
    ax5 = fig.add_subplot(gs[2, :2])
    sa(ax5, "Monthly Entry Signals (Trade Count + Win Rate)")
    df["Month"] = pd.to_datetime(df["Entry_Date"]).dt.to_period("M")
    monthly = df.groupby("Month").agg(Count=("Win","count"), WR=("Win","mean"))
    x = range(len(monthly))
    bars5 = ax5.bar(x, monthly["Count"],
                    color=[p["green"] if w >= 0.5 else p["red"] for w in monthly["WR"]],
                    alpha=0.8, edgecolor="#30363d", lw=0.4)
    ax5.set_xticks(list(x))
    ax5.set_xticklabels(monthly.index.astype(str), rotation=45, ha="right", fontsize=7)
    ax5.set_ylabel("# Trades", color=p["muted"])
    ax5.yaxis.label.set_color(p["muted"])

    # Top tickers
    ax6 = fig.add_subplot(gs[2, 2])
    sa(ax6, "Top Tickers by Win Rate (min 2 trades)")
    top = (df.groupby("Ticker")
             .agg(Trades=("Win","count"), WR=("Win","mean"))
             .query("Trades >= 2")
             .sort_values("WR", ascending=True)
             .tail(12))
    if not top.empty:
        tc = [p["green"] if v >= 0.5 else p["red"] for v in top["WR"]]
        ax6.barh(top.index.str.replace(".NS",""), top["WR"]*100,
                 color=tc, edgecolor="#30363d", lw=0.4)
        ax6.axvline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.6)
        ax6.set_xlabel("Win Rate %", color=p["muted"])
        ax6.xaxis.label.set_color(p["muted"])

    plt.suptitle("BULL CALL SPREAD V3  |  52-WK BREAKOUT + BULL REGIME CORE  |  3% OTM  |  45-DAY",
                 color=p["text"], fontsize=12, fontweight="bold", y=0.99)

    out = os.path.join(OUTPUT_DIR, "call_spread_v3_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Chart -> {out}")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
def save_results(df):
    if df.empty:
        return
    df = df.sort_values("Entry_Date")

    by_ticker = (df.groupby("Ticker")
                   .agg(Trades=("Win","count"),
                        WinRate=("Win", lambda x: round(x.mean()*100,1)),
                        AvgReturn=("Return_%","mean"),
                        AvgDebitPct=("Debit_pct","mean"))
                   .sort_values("WinRate", ascending=False)
                   .reset_index())

    out_xlsx = os.path.join(OUTPUT_DIR, "call_spread_v3_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "call_spread_v3_results.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="All Trades", index=False)
        by_ticker.to_excel(w, sheet_name="By Ticker", index=False)
        df[df["Win"]].to_excel(w, sheet_name="Winners Only", index=False)

    df.to_csv(out_csv, index=False)
    print(f"[OK] Excel -> {out_xlsx}")
    print(f"[OK] CSV   -> {out_csv}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  BULL CALL SPREAD V3 — BREAKOUT CORE TIMING ENGINE")
    print("=" * 60)

    print("\n[1] Nifty regime ...")
    nifty = load_nifty("5y")

    print("\n[2] Loading stocks ...")
    tickers    = load_nse_tickers()[:TICKERS_LIMIT]
    stock_data = load_data(tickers, "5y")

    print(f"\n[3] Backtesting {len(stock_data)} stocks ...")
    df = run_backtest(stock_data, nifty)

    analyse(df)
    plot_results(df)
    save_results(df)

    print("\n[DONE]")
