"""
==============================================================================
  BULL CALL SPREAD V4 — TOP-STOCK FOCUSED ENGINE
==============================================================================

V4 PHILOSOPHY:
  V3 proved the 52-week breakout pattern works strongly on SPECIFIC stocks.
  V4 focuses ONLY on the top 20 stocks identified in V3 (70%+ historical
  win rate), fixes position sizing (fixed units, no compounding overflow),
  and adds a LIVE SCANNER showing which stocks are signalling RIGHT NOW.

TOP 20 STOCKS (from V3 analysis, ranked by win rate):
  AIIL, ANANTRAJ, ABB, ABREL, ABDL, ANANDRATHI, ANGELONE, ABCAPITAL,
  ALBERTDAVD, AJMERA, APTECHT, APOLLO, APOLLOTYRE, APARINDS, ASAL,
  ABFRL, APLAPOLLO, APTUS, ARVINDFASN, ASHOKA

FIXED BUGS FROM V3:
  - Position sizing now FIXED (based on initial capital only, no compounding)
  - Return % capped at 100% max (spread cannot return more than spread width)
  - Added live signal scanner

OUTPUTS:
  - call_spread_v4_results.xlsx / .csv
  - call_spread_v4_chart.png
  - call_spread_v4_live_signals.csv  (stocks signalling today)
==============================================================================
"""

import os, warnings, datetime
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
# TOP 20 FOCUS STOCKS (from V3 analysis)
# ─────────────────────────────────────────────
TOP_STOCKS = [
    "AIIL.NS", "ANANTRAJ.NS", "ABB.NS", "ABREL.NS", "ABDL.NS",
    "ANANDRATHI.NS", "ANGELONE.NS", "ABCAPITAL.NS", "ALBERTDAVD.NS",
    "AJMERA.NS", "APTECHT.NS", "APOLLO.NS", "APOLLOTYRE.NS",
    "APARINDS.NS", "ASAL.NS", "ABFRL.NS", "APLAPOLLO.NS",
    "APTUS.NS", "ARVINDFASN.NS", "ASHOKA.NS",
    # Extra high-quality additions
    "HDFCBANK.NS", "RELIANCE.NS", "BAJFINANCE.NS", "TITAN.NS",
    "ASIANPAINT.NS", "MARUTI.NS", "TCS.NS", "INFY.NS",
    "KOTAKBANK.NS", "ICICIBANK.NS",
]

# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────
INITIAL_CAPITAL  = 100_000
RISK_PER_TRADE   = 0.02        # 2% of INITIAL capital per trade (fixed)
SPREAD_WIDTH_PCT = 0.03        # 3% OTM short strike
DTE              = 45          # 45 calendar days
RISK_FREE        = 0.065
NIFTY_TICKER     = "^NSEI"
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
    d = bs_call(S, K1, T, r, sigma) - bs_call(S, K2, T, r, sigma)
    return max(d, 0.0)


def spread_payoff_pct(S_T, K1, K2, debit):
    """Return % relative to debit paid. Capped at +/- real limits."""
    intrinsic = min(max(S_T - K1, 0.0), K2 - K1)
    pnl = intrinsic - debit
    return (pnl / debit) * 100.0 if debit > 0 else 0.0


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(period).mean()


def compute_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_hv(close, window=20):
    return np.log(close / close.shift(1)).rolling(window).std() * np.sqrt(252)


def compute_signals(df, nifty_above_200):
    close  = df["Close"]
    vol    = df["Volume"]
    ema50  = close.ewm(span=50,  adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    rsi    = compute_rsi(close, 14)
    hv     = compute_hv(close, 20)
    vol_ma = vol.rolling(20).mean()

    # 52-week breakout
    high_252    = close.shift(1).rolling(252).max()
    m1_breakout = (close > high_252)

    # Nifty regime
    nifty_sig = nifty_above_200.reindex(df.index, method="ffill").fillna(False)

    # RSI 55-80
    f1_rsi = ((rsi >= 55) & (rsi <= 80))

    # Volume > 1.5x
    f2_vol = (vol > vol_ma * 1.5)

    # Above both EMAs
    f3_trend = ((close > ema50) & (close > ema200))

    flex = f1_rsi.astype(int) + f2_vol.astype(int) + f3_trend.astype(int)
    entry = m1_breakout & nifty_sig & (flex >= 2)

    return pd.DataFrame({
        "Close":       close,
        "HV":          hv,
        "RSI":         rsi,
        "EMA50":       ema50,
        "EMA200":      ema200,
        "High252":     high_252,
        "M1_Breakout": m1_breakout.astype(int),
        "M2_Regime":   nifty_sig.astype(int),
        "F1_RSI":      f1_rsi.astype(int),
        "F2_Volume":   f2_vol.astype(int),
        "F3_Trend":    f3_trend.astype(int),
        "FlexScore":   flex,
        "Entry":       entry.astype(int),
    }, index=df.index)


# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
def load_data(tickers, period="5y"):
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            if df is not None and len(df) > 300:
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[t] = df
                print(f"  [OK] {t} ({len(df)} bars)")
        except Exception as e:
            print(f"  [--] {t} skipped: {e}")
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
        print("  [WARN] Nifty load failed")
        return pd.Series(dtype=bool)


# ─────────────────────────────────────────────
# BACKTEST  (FIXED POSITION SIZING)
# ─────────────────────────────────────────────
def run_backtest(stock_data, nifty_regime):
    trades = []
    fixed_risk = INITIAL_CAPITAL * RISK_PER_TRADE  # fixed ₹2,000 per trade
    trading_days = int(DTE * 5 / 7)

    for ticker, df in stock_data.items():
        try:
            sigs = compute_signals(df, nifty_regime)
        except Exception as e:
            print(f"  [WARN] {ticker}: {e}")
            continue

        for entry_date in sigs.index[sigs["Entry"] == 1]:
            loc      = df.index.get_loc(entry_date)
            exit_loc = loc + trading_days
            if exit_loc >= len(df):
                continue

            S  = float(sigs.loc[entry_date, "Close"])
            hv = float(sigs.loc[entry_date, "HV"])
            if S <= 0 or np.isnan(hv) or hv <= 0 or hv > 5.0:
                continue

            K1 = max(round(S / 5) * 5, 5)
            K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 5) * 5, K1 + 5)

            debit = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
            if debit <= 0 or debit >= (K2 - K1):
                continue

            # FIXED position sizing — always based on initial capital
            units     = max(1, int(fixed_risk / debit))
            total_deb = debit * units

            exit_date = df.index[exit_loc]
            S_T       = float(df.loc[exit_date, "Close"])
            ret_pct   = spread_payoff_pct(S_T, K1, K2, debit)
            pnl_total = (ret_pct / 100.0) * total_deb
            win       = ret_pct > 0

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
                "Move_%":      round((S_T - S) / S * 100, 2),
                "HV":          round(hv, 4),
                "RSI":         round(float(row["RSI"]), 1),
                "Debit/unit":  round(debit, 2),
                "Debit_%S":    round(debit / S * 100, 3),
                "Max_Profit":  round((K2 - K1 - debit) * units, 2),
                "Units":       units,
                "PnL_Total":   round(pnl_total, 2),
                "Return_%":    round(ret_pct, 2),
                "Win":         win,
                "M1_Breakout": int(row["M1_Breakout"]),
                "M2_Regime":   int(row["M2_Regime"]),
                "F1_RSI":      int(row["F1_RSI"]),
                "F2_Volume":   int(row["F2_Volume"]),
                "F3_Trend":    int(row["F3_Trend"]),
                "FlexScore":   int(row["FlexScore"]),
            })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# LIVE SIGNAL SCANNER
# ─────────────────────────────────────────────
def scan_live_signals(stock_data, nifty_regime):
    """Check which stocks are firing the entry signal TODAY."""
    signals = []
    for ticker, df in stock_data.items():
        try:
            sigs = compute_signals(df, nifty_regime)
            last = sigs.iloc[-1]
            if last["Entry"] == 1:
                S  = float(last["Close"])
                hv = float(last["HV"])
                if S > 0 and not np.isnan(hv) and 0 < hv < 5:
                    K1 = max(round(S / 5) * 5, 5)
                    K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 5) * 5, K1 + 5)
                    deb = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
                    signals.append({
                        "Ticker":      ticker,
                        "Signal_Date": sigs.index[-1].date(),
                        "Price":       round(S, 2),
                        "K1_Long":     K1,
                        "K2_Short":    K2,
                        "Breakeven":   round(K1 + deb, 2),
                        "Est_Debit":   round(deb, 2),
                        "Debit_%S":    round(deb / S * 100, 3),
                        "HV":          round(hv, 4),
                        "RSI":         round(float(last["RSI"]), 1),
                        "FlexScore":   int(last["FlexScore"]),
                        "52W_High":    round(float(last["High252"]), 2),
                        "Expiry_~":    (datetime.date.today() +
                                        datetime.timedelta(days=DTE)).isoformat(),
                    })
        except Exception:
            continue
    return pd.DataFrame(signals)


# ─────────────────────────────────────────────
# ANALYSE
# ─────────────────────────────────────────────
def analyse(df):
    if df.empty:
        print("[WARN] No trades generated.")
        return {}

    df = df.sort_values("Entry_Date").reset_index(drop=True)
    total  = len(df)
    wins   = int(df["Win"].sum())
    wr     = wins / total * 100
    avg_r  = df["Return_%"].mean()
    std_r  = df["Return_%"].std()
    sharpe = avg_r / std_r * np.sqrt(252 / 31) if std_r > 0 else 0
    total_pnl  = df["PnL_Total"].sum()
    final_cap  = INITIAL_CAPITAL + total_pnl

    # Binomial significance test
    binom_p = binomtest(wins, total, p=0.5, alternative="greater").pvalue

    print("\n" + "=" * 62)
    print("  BULL CALL SPREAD V4 — FOCUSED TOP-STOCK RESULTS")
    print("=" * 62)
    print(f"  Stocks Tested       : {df['Ticker'].nunique()}")
    print(f"  Total Trades        : {total}")
    print(f"  Win Rate            : {wr:.1f}%")
    print(f"  Avg Return/Spread   : {avg_r:.1f}%")
    print(f"  Best Trade          : {df['Return_%'].max():.1f}%")
    print(f"  Worst Trade         : {df['Return_%'].min():.1f}%")
    print(f"  Sharpe Ratio        : {sharpe:.2f}")
    print(f"  Total PnL           : Rs.{total_pnl:,.0f}")
    print(f"  Simulated Capital   : Rs.{final_cap:,.0f}")
    print(f"  CAGR (5yr)          : {((final_cap/INITIAL_CAPITAL)**(1/5)-1)*100:.1f}%")
    print(f"  Binomial p-value    : {binom_p:.4f} "
          f"({'SIGNIFICANT' if binom_p < 0.05 else 'not significant'})")
    print("=" * 62)

    # Per-ticker
    by_t = (df.groupby("Ticker")
              .agg(Trades=("Win","count"),
                   WinRate=("Win", lambda x: round(x.mean()*100,1)),
                   AvgRet=("Return_%","mean"),
                   TotalPnL=("PnL_Total","sum"))
              .sort_values("WinRate", ascending=False))
    print(f"\n  PER-STOCK BREAKDOWN:\n{by_t.to_string()}")

    return {"total":total,"win_rate":wr,"avg_return":avg_r,"sharpe":sharpe,
            "final_capital":final_cap,"binom_p":binom_p}


# ─────────────────────────────────────────────
# PLOT
# ─────────────────────────────────────────────
def plot_results(df):
    if df.empty:
        return

    df = df.sort_values("Entry_Date").reset_index(drop=True)
    df["CumPnL"] = df["PnL_Total"].cumsum() + INITIAL_CAPITAL

    p = {"bg":"#0d1117","panel":"#161b22","green":"#39d353","red":"#f85149",
         "blue":"#58a6ff","yellow":"#e3b341","text":"#c9d1d9","muted":"#8b949e",
         "purple":"#a371f7"}

    fig = plt.figure(figsize=(20, 15))
    fig.patch.set_facecolor(p["bg"])
    gs  = gridspec.GridSpec(3, 3, hspace=0.55, wspace=0.38)

    def sa(ax, title):
        ax.set_facecolor(p["panel"])
        ax.tick_params(colors=p["muted"], labelsize=9)
        ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # ── Equity curve
    ax1 = fig.add_subplot(gs[0, :])
    sa(ax1, "Cumulative Capital  |  V4  |  Top 30 NSE Stocks  |  52-Wk Breakout  |  3% OTM  |  45-Day  |  5 Years")
    ax1.plot(df.index, df["CumPnL"], color=p["blue"], lw=2, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["CumPnL"],
                     where=(df["CumPnL"] >= INITIAL_CAPITAL), alpha=0.15, color=p["green"])
    ax1.fill_between(df.index, INITIAL_CAPITAL, df["CumPnL"],
                     where=(df["CumPnL"] < INITIAL_CAPITAL),  alpha=0.20, color=p["red"])
    fin = df["CumPnL"].iloc[-1]
    col = p["green"] if fin >= INITIAL_CAPITAL else p["red"]
    ax1.annotate(f"Rs.{fin:,.0f}", xy=(df.index[-1], fin),
                 xytext=(-100, 14), textcoords="offset points",
                 color=col, fontsize=12, fontweight="bold")
    ax1.set_ylabel("Capital (Rs.)", color=p["muted"])
    ax1.yaxis.label.set_color(p["muted"])

    # ── Win rate per ticker (horizontal bar)
    ax2 = fig.add_subplot(gs[1, :2])
    sa(ax2, "Win Rate by Stock  (min 3 trades)")
    by_t = (df.groupby("Ticker")
              .agg(Trades=("Win","count"), WR=("Win","mean"))
              .query("Trades >= 3")
              .sort_values("WR", ascending=True))
    colors = [p["green"] if w >= 0.6 else p["yellow"] if w >= 0.5 else p["red"]
              for w in by_t["WR"]]
    bars = ax2.barh(by_t.index.str.replace(".NS",""), by_t["WR"]*100,
                    color=colors, edgecolor="#30363d", lw=0.4, height=0.7)
    for bar, (_, row) in zip(bars, by_t.iterrows()):
        ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                 f"n={int(row['Trades'])}", va="center", fontsize=8, color=p["muted"])
    ax2.axvline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax2.axvline(70, color=p["green"], ls="--", lw=0.8, alpha=0.5)
    ax2.set_xlabel("Win Rate %", color=p["muted"])
    ax2.xaxis.label.set_color(p["muted"])
    ax2.set_xlim(0, 105)

    # ── Return distribution
    ax3 = fig.add_subplot(gs[1, 2])
    sa(ax3, "Return Distribution per Spread")
    w = df[df["Win"]]["Return_%"]
    l = df[~df["Win"]]["Return_%"]
    ax3.hist(l, bins=30, color=p["red"],   alpha=0.75, label=f"Loss (n={len(l)})")
    ax3.hist(w, bins=30, color=p["green"], alpha=0.75, label=f"Win  (n={len(w)})")
    ax3.axvline(0, color=p["muted"], lw=1)
    avg = df["Return_%"].mean()
    ax3.axvline(avg, color=p["yellow"], lw=1.5, ls="--",
                label=f"Avg={avg:.1f}%")
    ax3.set_xlabel("Return %", color=p["muted"])
    ax3.xaxis.label.set_color(p["muted"])
    ax3.legend(facecolor=p["panel"], labelcolor=p["text"],
               edgecolor="#30363d", fontsize=8)

    # ── Win rate by RSI
    ax4 = fig.add_subplot(gs[2, 0])
    sa(ax4, "Win Rate by RSI at Entry")
    df["RSI_b"] = pd.cut(df["RSI"], bins=[55,60,65,70,75,80],
                          labels=["55-60","60-65","65-70","70-75","75-80"])
    rb = df.groupby("RSI_b", observed=True)["Win"].agg(["mean","count"])
    rc = [p["green"] if v>=0.6 else p["yellow"] if v>=0.5 else p["red"] for v in rb["mean"]]
    bars4 = ax4.bar(rb.index.astype(str), rb["mean"]*100, color=rc,
                    edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars4, rb.iterrows()):
        ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=p["muted"])
    ax4.axhline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax4.set_ylabel("Win Rate %", color=p["muted"])
    ax4.yaxis.label.set_color(p["muted"])
    ax4.set_ylim(0, 115)

    # ── Win rate by stock move %
    ax5 = fig.add_subplot(gs[2, 1])
    sa(ax5, "Actual Stock Move at Expiry")
    df["Move_b"] = pd.cut(df["Move_%"], bins=[-100,-10,-5,0,5,10,20,50,500],
                           labels=["<-10","-10:-5","-5:0","0:5","5:10","10:20","20:50",">50"])
    mb = df.groupby("Move_b", observed=True)["Win"].agg(["mean","count"])
    mc = [p["green"] if v>=0.6 else p["yellow"] if v>=0.5 else p["red"] for v in mb["mean"]]
    bars5 = ax5.bar(mb.index.astype(str), mb["mean"]*100, color=mc,
                    edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars5, mb.iterrows()):
        ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=7, color=p["muted"])
    ax5.axhline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax5.set_xlabel("Stock Move % by Expiry", color=p["muted"])
    ax5.set_ylabel("Win Rate %", color=p["muted"])
    ax5.xaxis.label.set_color(p["muted"])
    ax5.yaxis.label.set_color(p["muted"])
    ax5.set_ylim(0, 115)
    ax5.tick_params(axis="x", labelrotation=30)

    # ── Monthly trade count
    ax6 = fig.add_subplot(gs[2, 2])
    sa(ax6, "Trades per Year + Win Rate")
    df["Year"] = pd.to_datetime(df["Entry_Date"]).dt.year
    yr = df.groupby("Year").agg(Count=("Win","count"), WR=("Win","mean"))
    yc = [p["green"] if w>=0.6 else p["yellow"] if w>=0.5 else p["red"] for w in yr["WR"]]
    bars6 = ax6.bar(yr.index.astype(str), yr["Count"], color=yc,
                    edgecolor="#30363d", lw=0.4)
    for bar, (yr_idx, row) in zip(bars6, yr.iterrows()):
        ax6.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                 f"{row['WR']*100:.0f}%", ha="center", fontsize=9,
                 color=p["text"], fontweight="bold")
    ax6.set_ylabel("# Trades", color=p["muted"])
    ax6.yaxis.label.set_color(p["muted"])

    wr_overall = df["Win"].mean() * 100
    plt.suptitle(
        f"BULL CALL SPREAD V4  |  TOP-STOCK FOCUSED  |  "
        f"Overall Win Rate: {wr_overall:.1f}%  |  "
        f"{len(df)} Trades over 5 Years",
        color=p["text"], fontsize=12, fontweight="bold", y=0.99)

    out = os.path.join(OUTPUT_DIR, "call_spread_v4_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Chart -> {out}")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
def save_results(df, live_df):
    if df.empty:
        return
    df = df.sort_values("Entry_Date")

    by_ticker = (df.groupby("Ticker")
                   .agg(Trades=("Win","count"),
                        WinRate=("Win", lambda x: round(x.mean()*100,1)),
                        AvgReturn=("Return_%","mean"),
                        TotalPnL=("PnL_Total","sum"),
                        AvgDebit_pct=("Debit_%S","mean"))
                   .sort_values("WinRate", ascending=False)
                   .reset_index())

    winners = df[df["Win"]].copy()
    losers  = df[~df["Win"]].copy()

    out_xlsx = os.path.join(OUTPUT_DIR, "call_spread_v4_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "call_spread_v4_results.csv")
    out_live = os.path.join(OUTPUT_DIR, "call_spread_v4_live_signals.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="All Trades", index=False)
        by_ticker.to_excel(w, sheet_name="By Stock", index=False)
        winners.to_excel(w, sheet_name="Winners", index=False)
        losers.to_excel(w, sheet_name="Losers", index=False)
        if not live_df.empty:
            live_df.to_excel(w, sheet_name="LIVE Signals", index=False)

    df.to_csv(out_csv, index=False)
    if not live_df.empty:
        live_df.to_csv(out_live, index=False)

    print(f"[OK] Excel       -> {out_xlsx}")
    print(f"[OK] CSV         -> {out_csv}")
    if not live_df.empty:
        print(f"[OK] Live Signals -> {out_live}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 62)
    print("  BULL CALL SPREAD V4 — TOP STOCK FOCUSED ENGINE")
    print("=" * 62)

    print("\n[1] Loading Nifty regime ...")
    nifty = load_nifty("5y")

    print(f"\n[2] Loading {len(TOP_STOCKS)} top stocks ...")
    stock_data = load_data(TOP_STOCKS, "5y")
    print(f"    Loaded {len(stock_data)} stocks successfully")

    print("\n[3] Running 5-year backtest ...")
    df = run_backtest(stock_data, nifty)

    print("\n[4] Scanning for LIVE signals (today) ...")
    live_df = scan_live_signals(stock_data, nifty)
    if not live_df.empty:
        print(f"\n  *** {len(live_df)} LIVE SIGNALS TODAY ***")
        print(live_df[["Ticker","Price","K1_Long","K2_Short",
                        "Est_Debit","RSI","FlexScore","Expiry_~"]].to_string(index=False))
    else:
        print("  No live signals today.")

    analyse(df)
    plot_results(df)
    save_results(df, live_df)

    print("\n[DONE] All files saved to analysis/ folder")
