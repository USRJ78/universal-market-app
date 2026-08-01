"""
==============================================================================
  BTC BULL CALL SPREAD TIMING ENGINE
==============================================================================

APPROACH (Different from NSE):
  BTC is cycle-driven, high-volatility, and macro-sensitive.
  Instead of 52-week breakouts, we use BTC-SPECIFIC signals:

  1. MACRO REGIME    — BTC above its 200-week MA (confirmed bull market)
  2. CYCLE POSITION  — Not in top 30% of 4yr cycle (avoid blow-off tops)
  3. WEEKLY MACD     — Bullish crossover on weekly timeframe (trend ignition)
  4. REALIZED VOL    — 30d HV below 80th percentile (vol not in panic mode)
  5. MOMENTUM        — 4-week return positive AND RSI(14) 50-75

  BTC SPREAD STRUCTURE:
    - Long  Call : ATM
    - Short Call : 15% OTM  (BTC moves big — wider spread = more room)
    - DTE        : 30 days
    - Risk-free  : 5% (USD)

  ALL 3 core signals (1, 2, 3) must fire.
  At least 1 of 2 secondary signals (4, 5) must fire.

OUTPUTS:
  - btc_call_spread_results.xlsx / .csv
  - btc_call_spread_chart.png
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
# SETTINGS
# ─────────────────────────────────────────────
INITIAL_CAPITAL  = 10_000       # USD (typical crypto portfolio)
RISK_PER_TRADE   = 0.03         # 3% per spread (crypto = higher risk tolerance)
SPREAD_WIDTH_PCT = 0.15         # 15% OTM short strike (BTC is volatile!)
DTE              = 30           # 30 calendar days
RISK_FREE        = 0.05         # 5% USD risk-free
TICKER           = "BTC-USD"
OUTPUT_DIR       = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────
# BLACK-SCHOLES
# ─────────────────────────────────────────────
def bs_call(S, K, T_years, r, sigma):
    if T_years <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T_years) / (sigma*np.sqrt(T_years))
    d2 = d1 - sigma*np.sqrt(T_years)
    return float(S*norm.cdf(d1) - K*np.exp(-r*T_years)*norm.cdf(d2))


def spread_debit(S, K1, K2, T_days, r, sigma):
    T = T_days / 365.0
    return max(bs_call(S, K1, T, r, sigma) - bs_call(S, K2, T, r, sigma), 0.0)


def spread_payoff_pct(S_T, K1, K2, debit):
    intrinsic = min(max(S_T - K1, 0.0), K2 - K1)
    return ((intrinsic - debit) / debit * 100.0) if debit > 0 else 0.0


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close, fast=12, slow=26, signal=9):
    ema_fast   = close.ewm(span=fast,   adjust=False).mean()
    ema_slow   = close.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def compute_hv(close, window=30):
    return np.log(close / close.shift(1)).rolling(window).std() * np.sqrt(365)


def resample_weekly(df):
    """Resample daily OHLCV to weekly for MACD calculation."""
    weekly = df.resample("W").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna()
    return weekly


# ─────────────────────────────────────────────
# BTC-SPECIFIC SIGNALS
# ─────────────────────────────────────────────
def compute_btc_signals(df):
    """
    5 BTC-specific timing signals.

    CORE (all 3 must fire):
      S1 - Macro Regime   : Daily close > 200-week MA
      S2 - Cycle Position : Not in top 30% of trailing 4-year price range
      S3 - Weekly MACD    : Bullish crossover (MACD > Signal, was below)

    SECONDARY (1 of 2 must fire):
      S4 - Calm Vol       : 30d HV below 80th percentile of trailing year
      S5 - Momentum       : 4-week return > 0 AND RSI(14) 50-75
    """
    close  = df["Close"]
    vol    = df["Volume"]

    # ── Compute 200-week MA (1400 days)
    ma200w = close.rolling(1400).mean()

    # ── S1: Macro regime — above 200-week MA
    s1_regime = (close > ma200w).astype(int)

    # ── S2: Cycle position — NOT in top 30% of 4-year (1460-day) high
    high_4yr = close.rolling(1460).max()
    low_4yr  = close.rolling(1460).min()
    cycle_pct = (close - low_4yr) / (high_4yr - low_4yr + 1e-9)
    s2_cycle  = (cycle_pct < 0.70).astype(int)   # avoid top 30%

    # ── S3: Weekly MACD bullish crossover (computed on weekly data)
    weekly  = resample_weekly(df)
    wmacd, wsig = compute_macd(weekly["Close"], fast=12, slow=26, signal=9)
    # MACD above signal = weekly bullish
    w_bullish = (wmacd > wsig).astype(int)
    # Reindex to daily (forward fill) and cast to int to avoid float & int TypeError
    s3_macd = w_bullish.reindex(df.index, method="ffill").fillna(0).astype(int)

    # ── S4: Calm vol — 30d HV below 80th percentile of trailing year
    hv30   = compute_hv(close, 30)
    hv_pct = hv30.rolling(365).apply(lambda x: (x[-1] > x[:-1]).mean(), raw=True)
    s4_vol = (hv_pct < 0.80).astype(int)

    # ── S5: Momentum — 4-week return positive AND RSI 50-75
    ret_4w = close.pct_change(28) * 100
    rsi14  = compute_rsi(close, 14)
    s5_mom = ((ret_4w > 0) & (rsi14 >= 50) & (rsi14 <= 75)).astype(int)

    # ── Entry logic (all int series now — no TypeError)
    core_ok      = (s1_regime.astype(int) & s2_cycle.astype(int) & s3_macd)
    secondary_ok = ((s4_vol + s5_mom) >= 1).astype(int)
    entry        = (core_ok.astype(bool) & secondary_ok.astype(bool)).astype(int)

    return pd.DataFrame({
        "Close":      close,
        "Volume":     vol,
        "HV30":       hv30,
        "RSI14":      rsi14,
        "MA200W":     ma200w,
        "Cycle_Pct":  cycle_pct,
        "Ret_4W_pct": ret_4w,
        "S1_Regime":  s1_regime,
        "S2_Cycle":   s2_cycle,
        "S3_MACD":    s3_macd,
        "S4_Vol":     s4_vol,
        "S5_Mom":     s5_mom,
        "Core_OK":    core_ok.astype(int),
        "Entry":      entry,
    }, index=df.index)


# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
def load_btc(period="10y"):
    print(f"  Downloading {TICKER} ({period}) ...")
    df = yf.download(TICKER, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    print(f"  [OK] {len(df)} daily bars loaded")
    return df.dropna()


# ─────────────────────────────────────────────
# BACKTEST
# ─────────────────────────────────────────────
def run_backtest(df, sigs):
    trades      = []
    fixed_risk  = INITIAL_CAPITAL * RISK_PER_TRADE
    trading_days = int(DTE * 7 / 7)   # for crypto: calendar days ~ same as trading days

    # Avoid overlapping trades (one trade at a time per signal)
    last_exit = df.index[0]

    entry_dates = sigs.index[sigs["Entry"] == 1]

    for entry_date in entry_dates:
        # Skip if still in a previous trade
        if entry_date <= last_exit:
            continue

        loc      = df.index.get_loc(entry_date)
        exit_loc = loc + DTE
        if exit_loc >= len(df):
            continue

        S  = float(sigs.loc[entry_date, "Close"])
        hv = float(sigs.loc[entry_date, "HV30"])
        if S <= 0 or np.isnan(hv) or hv <= 0 or hv > 10.0:
            continue

        # BTC strikes — round to nearest 500
        K1 = max(round(S / 500) * 500, 500)
        K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 500) * 500, K1 + 500)

        debit = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
        if debit <= 0 or debit >= (K2 - K1):
            continue

        # Fixed sizing
        units     = max(0.001, fixed_risk / debit)   # fractional BTC units OK
        total_deb = debit * units

        exit_date  = df.index[exit_loc]
        S_T        = float(df.loc[exit_date, "Close"])
        ret_pct    = spread_payoff_pct(S_T, K1, K2, debit)
        pnl_total  = (ret_pct / 100.0) * total_deb
        win        = ret_pct > 0
        last_exit  = exit_date

        row = sigs.loc[entry_date]
        trades.append({
            "Entry_Date":  entry_date,
            "Exit_Date":   exit_date,
            "BTC_Entry":   round(S, 0),
            "K1_Long":     K1,
            "K2_Short":    K2,
            "Breakeven":   round(K1 + debit, 0),
            "BTC_Expiry":  round(S_T, 0),
            "Move_%":      round((S_T - S) / S * 100, 2),
            "HV30":        round(hv, 4),
            "RSI14":       round(float(row["RSI14"]), 1),
            "Cycle_Pct":   round(float(row["Cycle_Pct"]), 3),
            "Ret_4W_%":    round(float(row["Ret_4W_pct"]), 2),
            "Debit_USD":   round(debit, 2),
            "Debit_%BTC":  round(debit / S * 100, 3),
            "Units":       round(units, 4),
            "PnL_USD":     round(pnl_total, 2),
            "Return_%":    round(ret_pct, 2),
            "Win":         win,
            "S1_Regime":   int(row["S1_Regime"]),
            "S2_Cycle":    int(row["S2_Cycle"]),
            "S3_MACD":     int(row["S3_MACD"]),
            "S4_Vol":      int(row["S4_Vol"]),
            "S5_Mom":      int(row["S5_Mom"]),
        })

    return pd.DataFrame(trades)


# ─────────────────────────────────────────────
# LIVE SIGNAL
# ─────────────────────────────────────────────
def check_live_signal(df, sigs):
    last = sigs.iloc[-1]
    print("\n" + "="*55)
    print("  LIVE BTC SIGNAL STATUS (TODAY)")
    print("="*55)
    print(f"  BTC Price     : ${float(last['Close']):,.0f}")
    print(f"  200-Week MA   : ${float(last['MA200W']):,.0f}")
    print(f"  Cycle Pct     : {float(last['Cycle_Pct'])*100:.1f}% of 4yr range")
    print(f"  RSI(14)       : {float(last['RSI14']):.1f}")
    print(f"  4W Return     : {float(last['Ret_4W_pct']):.1f}%")
    print(f"  30d HV        : {float(last['HV30'])*100:.1f}%")
    print(f"  S1 Regime     : {'YES' if last['S1_Regime'] else 'NO'}")
    print(f"  S2 Cycle OK   : {'YES' if last['S2_Cycle'] else 'NO'}")
    print(f"  S3 MACD Bull  : {'YES' if last['S3_MACD'] else 'NO'}")
    print(f"  S4 Calm Vol   : {'YES' if last['S4_Vol'] else 'NO'}")
    print(f"  S5 Momentum   : {'YES' if last['S5_Mom'] else 'NO'}")
    print(f"  --")

    if last["Entry"]:
        S  = float(last["Close"])
        hv = float(last["HV30"])
        K1 = max(round(S / 500) * 500, 500)
        K2 = max(round(S * (1 + SPREAD_WIDTH_PCT) / 500) * 500, K1 + 500)
        deb = spread_debit(S, K1, K2, DTE, RISK_FREE, hv)
        exp = (datetime.date.today() + datetime.timedelta(days=DTE)).isoformat()
        print(f"  *** SIGNAL ACTIVE — ENTER NOW ***")
        print(f"  Buy  CALL  K1 = ${K1:,.0f}")
        print(f"  Sell CALL  K2 = ${K2:,.0f}")
        print(f"  Est. Debit    = ${deb:,.0f}")
        print(f"  Breakeven     = ${K1+deb:,.0f}")
        print(f"  Expiry (~)    = {exp}")
    else:
        missing = []
        if not last["S1_Regime"]: missing.append("S1 (BTC below 200W MA)")
        if not last["S2_Cycle"]:  missing.append("S2 (too high in 4yr cycle)")
        if not last["S3_MACD"]:   missing.append("S3 (weekly MACD bearish)")
        if not last["S4_Vol"] and not last["S5_Mom"]:
            missing.append("S4/S5 (vol too high or momentum weak)")
        print(f"  NO SIGNAL — missing: {', '.join(missing)}")
    print("="*55)


# ─────────────────────────────────────────────
# ANALYSE
# ─────────────────────────────────────────────
def analyse(df_t):
    if df_t.empty:
        print("No trades found.")
        return {}

    total = len(df_t)
    wins  = int(df_t["Win"].sum())
    wr    = wins / total * 100
    avg_r = df_t["Return_%"].mean()
    std_r = df_t["Return_%"].std()
    sharpe = avg_r / std_r * np.sqrt(365 / DTE) if std_r > 0 else 0
    total_pnl = df_t["PnL_USD"].sum()
    final = INITIAL_CAPITAL + total_pnl
    cagr  = ((final / INITIAL_CAPITAL) ** (1/10) - 1) * 100

    binom_p = binomtest(wins, total, p=0.5, alternative="greater").pvalue

    print("\n" + "="*58)
    print("  BTC BULL CALL SPREAD — BACKTEST RESULTS (10 YEARS)")
    print("="*58)
    print(f"  Total Trades        : {total}")
    print(f"  Win Rate            : {wr:.1f}%")
    print(f"  Avg Return/Spread   : {avg_r:.1f}%")
    print(f"  Best Trade          : {df_t['Return_%'].max():.1f}%")
    print(f"  Worst Trade         : {df_t['Return_%'].min():.1f}%")
    print(f"  Sharpe Ratio        : {sharpe:.2f}")
    print(f"  Total PnL           : ${total_pnl:,.0f}")
    print(f"  Final Capital       : ${final:,.0f}")
    print(f"  CAGR (10yr)         : {cagr:.1f}%")
    print(f"  Binomial p-value    : {binom_p:.4f} "
          f"({'SIGNIFICANT' if binom_p < 0.05 else 'not significant'})")
    print("="*58)

    # By year
    df_t["Year"] = pd.to_datetime(df_t["Entry_Date"]).dt.year
    by_yr = (df_t.groupby("Year")
               .agg(Trades=("Win","count"),
                    WinRate=("Win", lambda x: round(x.mean()*100,1)),
                    AvgReturn=("Return_%","mean"),
                    PnL=("PnL_USD","sum"))
               .reset_index())
    print(f"\n  BY YEAR:\n{by_yr.to_string(index=False)}")

    return {"total":total,"win_rate":wr,"avg_return":avg_r,
            "sharpe":sharpe,"final":final,"cagr":cagr,"binom_p":binom_p}


# ─────────────────────────────────────────────
# PLOT
# ─────────────────────────────────────────────
def plot_results(df_raw, df_t):
    if df_t.empty:
        return

    df_t = df_t.sort_values("Entry_Date").reset_index(drop=True)
    df_t["CumPnL"] = df_t["PnL_USD"].cumsum() + INITIAL_CAPITAL

    p = {"bg":"#0d1117","panel":"#161b22","green":"#39d353","red":"#f85149",
         "blue":"#58a6ff","yellow":"#e3b341","orange":"#f0883e",
         "text":"#c9d1d9","muted":"#8b949e","purple":"#a371f7"}

    fig = plt.figure(figsize=(20, 16))
    fig.patch.set_facecolor(p["bg"])
    gs  = gridspec.GridSpec(4, 3, hspace=0.60, wspace=0.38)

    def sa(ax, title):
        ax.set_facecolor(p["panel"])
        ax.tick_params(colors=p["muted"], labelsize=9)
        ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
        for s in ax.spines.values():
            s.set_edgecolor("#30363d")

    # ── Row 0: BTC Price + trade markers (full width)
    ax0 = fig.add_subplot(gs[0, :])
    sa(ax0, "BTC/USD Price (10 Years)  |  Green = Spread Entry  |  200-Week MA in Orange")
    ax0.plot(df_raw.index, df_raw["Close"], color=p["blue"], lw=1.2, alpha=0.9, zorder=2)
    ma200w = df_raw["Close"].rolling(1400).mean()
    ax0.plot(df_raw.index, ma200w, color=p["orange"], lw=1.5, ls="--", alpha=0.7,
             label="200-Week MA")
    # Entry markers
    for _, row in df_t.iterrows():
        col = p["green"] if row["Win"] else p["red"]
        ax0.axvline(row["Entry_Date"], color=col, alpha=0.3, lw=0.8)
    ax0.set_yscale("log")
    ax0.set_ylabel("BTC Price (USD, log)", color=p["muted"])
    ax0.yaxis.label.set_color(p["muted"])
    ax0.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d", fontsize=9)

    # ── Row 1 Left: Equity curve
    ax1 = fig.add_subplot(gs[1, :2])
    sa(ax1, "Strategy Equity Curve  |  $10,000 Initial Capital  |  3% Risk Per Trade")
    ax1.plot(df_t.index, df_t["CumPnL"], color=p["blue"], lw=2, zorder=3)
    ax1.axhline(INITIAL_CAPITAL, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax1.fill_between(df_t.index, INITIAL_CAPITAL, df_t["CumPnL"],
                     where=(df_t["CumPnL"] >= INITIAL_CAPITAL), alpha=0.15, color=p["green"])
    ax1.fill_between(df_t.index, INITIAL_CAPITAL, df_t["CumPnL"],
                     where=(df_t["CumPnL"] < INITIAL_CAPITAL),  alpha=0.20, color=p["red"])
    fin = df_t["CumPnL"].iloc[-1]
    ax1.annotate(f"${fin:,.0f}", xy=(df_t.index[-1], fin),
                 xytext=(-90, 14), textcoords="offset points",
                 color=p["green"] if fin >= INITIAL_CAPITAL else p["red"],
                 fontsize=12, fontweight="bold")
    ax1.set_ylabel("Capital (USD)", color=p["muted"])
    ax1.yaxis.label.set_color(p["muted"])

    # ── Row 1 Right: Return distribution
    ax2 = fig.add_subplot(gs[1, 2])
    sa(ax2, "Return Distribution")
    w = df_t[df_t["Win"]]["Return_%"]
    l = df_t[~df_t["Win"]]["Return_%"]
    ax2.hist(l, bins=20, color=p["red"],   alpha=0.75, label=f"Loss (n={len(l)})")
    ax2.hist(w, bins=20, color=p["green"], alpha=0.75, label=f"Win  (n={len(w)})")
    ax2.axvline(0, color=p["muted"], lw=1)
    ax2.axvline(df_t["Return_%"].mean(), color=p["yellow"], lw=1.5, ls="--",
                label=f"Avg={df_t['Return_%'].mean():.1f}%")
    ax2.set_xlabel("Return %", color=p["muted"])
    ax2.xaxis.label.set_color(p["muted"])
    ax2.legend(facecolor=p["panel"], labelcolor=p["text"],
               edgecolor="#30363d", fontsize=8)

    # ── Row 2 Left: Win rate by year
    ax3 = fig.add_subplot(gs[2, 0])
    sa(ax3, "Win Rate by Year")
    df_t["Year"] = pd.to_datetime(df_t["Entry_Date"]).dt.year
    yr = df_t.groupby("Year")["Win"].agg(["mean","count"])
    yc = [p["green"] if v >= 0.6 else p["yellow"] if v >= 0.5 else p["red"]
          for v in yr["mean"]]
    bars = ax3.bar(yr.index.astype(str), yr["mean"]*100, color=yc,
                   edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars, yr.iterrows()):
        ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=p["muted"])
    ax3.axhline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax3.axhline(70, color=p["green"], ls="--", lw=0.8, alpha=0.4)
    ax3.set_ylabel("Win Rate %", color=p["muted"])
    ax3.yaxis.label.set_color(p["muted"])
    ax3.set_ylim(0, 115)
    ax3.tick_params(axis="x", labelrotation=30)

    # ── Row 2 Mid: Win rate by cycle position
    ax4 = fig.add_subplot(gs[2, 1])
    sa(ax4, "Win Rate by BTC Cycle Position")
    df_t["CycBucket"] = pd.cut(df_t["Cycle_Pct"],
                                bins=[0, 0.2, 0.35, 0.5, 0.65, 0.7],
                                labels=["0-20%","20-35%","35-50%","50-65%","65-70%"])
    cb = df_t.groupby("CycBucket", observed=True)["Win"].agg(["mean","count"])
    cc = [p["green"] if v >= 0.6 else p["yellow"] if v >= 0.5 else p["red"]
          for v in cb["mean"]]
    bars4 = ax4.bar(cb.index.astype(str), cb["mean"]*100, color=cc,
                    edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars4, cb.iterrows()):
        ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=p["muted"])
    ax4.axhline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax4.set_xlabel("Cycle Position (% of 4yr Range)", color=p["muted"])
    ax4.set_ylabel("Win Rate %", color=p["muted"])
    ax4.xaxis.label.set_color(p["muted"])
    ax4.yaxis.label.set_color(p["muted"])
    ax4.set_ylim(0, 115)

    # ── Row 2 Right: Win rate by RSI
    ax5 = fig.add_subplot(gs[2, 2])
    sa(ax5, "Win Rate by RSI at Entry")
    df_t["RSI_b"] = pd.cut(df_t["RSI14"], bins=[50,55,60,65,70,75],
                            labels=["50-55","55-60","60-65","65-70","70-75"])
    rb = df_t.groupby("RSI_b", observed=True)["Win"].agg(["mean","count"])
    rc = [p["green"] if v>=0.6 else p["yellow"] if v>=0.5 else p["red"] for v in rb["mean"]]
    bars5 = ax5.bar(rb.index.astype(str), rb["mean"]*100, color=rc,
                    edgecolor="#30363d", lw=0.5)
    for bar, (_, row) in zip(bars5, rb.iterrows()):
        ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                 f"n={int(row['count'])}", ha="center", fontsize=8, color=p["muted"])
    ax5.axhline(50, color=p["muted"], ls="--", lw=0.8, alpha=0.5)
    ax5.set_ylabel("Win Rate %", color=p["muted"])
    ax5.yaxis.label.set_color(p["muted"])
    ax5.set_ylim(0, 115)

    # ── Row 3: BTC move at expiry distribution
    ax6 = fig.add_subplot(gs[3, :])
    sa(ax6, "BTC Move (%) by Expiry  |  Green = Spread Won  |  Red = Spread Lost")
    w_moves = df_t[df_t["Win"]]["Move_%"]
    l_moves  = df_t[~df_t["Win"]]["Move_%"]
    ax6.hist(l_moves, bins=30, color=p["red"],   alpha=0.75, label=f"Loss (n={len(l_moves)})")
    ax6.hist(w_moves, bins=30, color=p["green"], alpha=0.75, label=f"Win  (n={len(w_moves)})")
    ax6.axvline(0,  color=p["muted"], lw=1)
    ax6.axvline(SPREAD_WIDTH_PCT * 100, color=p["yellow"], lw=1.5, ls="--",
                label=f"Short Strike (+{SPREAD_WIDTH_PCT*100:.0f}%)")
    ax6.set_xlabel("BTC Move % at Expiry", color=p["muted"])
    ax6.set_ylabel("Frequency", color=p["muted"])
    ax6.xaxis.label.set_color(p["muted"])
    ax6.yaxis.label.set_color(p["muted"])
    ax6.legend(facecolor=p["panel"], labelcolor=p["text"],
               edgecolor="#30363d", fontsize=9)

    wr_overall = df_t["Win"].mean() * 100
    plt.suptitle(
        f"BTC BULL CALL SPREAD  |  15% OTM  |  30-Day  |  Cycle-Aware  |  "
        f"Win Rate: {wr_overall:.1f}%  |  {len(df_t)} Trades  |  10 Years",
        color=p["text"], fontsize=12, fontweight="bold", y=0.99)

    out = os.path.join(OUTPUT_DIR, "btc_call_spread_chart.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Chart -> {out}")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
def save_results(df_t):
    if df_t.empty:
        return
    df_t = df_t.sort_values("Entry_Date")

    out_xlsx = os.path.join(OUTPUT_DIR, "btc_call_spread_results.xlsx")
    out_csv  = os.path.join(OUTPUT_DIR, "btc_call_spread_results.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_t.to_excel(w, sheet_name="All Trades", index=False)
        df_t[df_t["Win"]].to_excel(w, sheet_name="Winners", index=False)
        df_t[~df_t["Win"]].to_excel(w, sheet_name="Losers", index=False)

    df_t.to_csv(out_csv, index=False)
    print(f"[OK] Excel -> {out_xlsx}")
    print(f"[OK] CSV   -> {out_csv}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("="*58)
    print("  BTC BULL CALL SPREAD TIMING ENGINE")
    print("="*58)

    print("\n[1] Loading BTC data ...")
    df = load_btc("10y")

    print("\n[2] Computing BTC-specific signals ...")
    sigs = compute_btc_signals(df)

    total_entries = sigs["Entry"].sum()
    print(f"  Entry signals found: {total_entries} days over 10 years")

    print("\n[3] Running backtest ...")
    df_trades = run_backtest(df, sigs)

    print(f"  Trades simulated: {len(df_trades)}")

    print("\n[4] Live signal check ...")
    check_live_signal(df, sigs)

    analyse(df_trades)
    plot_results(df, df_trades)
    save_results(df_trades)

    print("\n[DONE]")
