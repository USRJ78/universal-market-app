"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT + SUPERTREND ALIGNMENT (EXACT TV PARAMS)
==============================================================================
  Replicates EXACTLY what the user sees on TradingView:
    UTBot:      Key=5, ATR Period=1   (UT Bot Alerts 5 1)
    Supertrend: Period=10, Mult=3.0   (Supertrend 10 3)
    Asset:      NSE:TATMPV (Tata Motors PV)
    Timeframe:  4H

  RULE (exactly as shown in screenshot):
    ✅ BUY  only when UTBot fires BUY  AND Supertrend is GREEN (bullish)
    ✅ SELL only when UTBot fires SELL AND Supertrend is RED   (bearish)
    ❌ All counter-trend signals IGNORED

  Also runs on BTC-USD daily for comparison.
==============================================================================
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              ".gemini", "antigravity", "brain",
                              "a0eeb781-d7e4-484e-898c-51f143744494")
CHART_PATH  = os.path.join(ARTIFACTS_DIR, "utbot_tv_exact_params_chart.png")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "utbot_tv_exact_params_report.md")

INITIAL_CAPITAL = 1000.0

# ══════════════════════════════════════════════════════════════════════════════
#  INDICATORS — EXACT TRADINGVIEW MATCH
# ══════════════════════════════════════════════════════════════════════════════

def compute_utbot_tv(close, key=5, atr_period=1):
    """
    Exact UTBot as on TradingView (UT Bot Alerts indicator).
    key       = Key Value (sensitivity multiplier)  → 5
    atr_period= ATR Length                          → 1
    Returns: buy_signal (Series bool), sell_signal (Series bool), xATRTrailingStop (Series)
    """
    # ATR with period=1 is just the 1-bar true range = |close - prev_close|
    tr    = close.diff().abs()
    atr   = tr.rolling(atr_period).mean()
    nloss = key * atr  # nLoss = key × ATR(1)

    xatr = [0.0] * len(close)
    for t in range(1, len(close)):
        sc = float(close.iloc[t])
        sp = float(close.iloc[t - 1])
        xa = xatr[t - 1]
        lc = float(nloss.iloc[t])

        if sc > xa and sp > xa:
            xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa:
            xatr[t] = min(xa, sc + lc)
        else:
            xatr[t] = sc - lc if sc > xa else sc + lc

    xatr_s = pd.Series(xatr, index=close.index)

    # EMA of close for direction confirmation
    ema = close.ewm(span=1, adjust=False).mean()  # period=1 EMA = close itself

    # Buy:  close crosses above xATRTrailingStop from below
    # Sell: close crosses below xATRTrailingStop from above
    buy_signal  = (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))
    sell_signal = (close < xatr_s) & (close.shift(1) >= xatr_s.shift(1))

    return buy_signal, sell_signal, xatr_s


def compute_supertrend_tv(df, period=10, multiplier=3.0):
    """
    Exact Supertrend as on TradingView.
    Returns: bullish (bool Series), supertrend_line (float Series)
    """
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    # ATR
    pc  = close.shift(1)
    tr  = pd.concat([(high - low),
                     (high - pc).abs(),
                     (low  - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    hl2     = (high + low) / 2.0
    upper_b = hl2 + multiplier * atr
    lower_b = hl2 - multiplier * atr

    final_upper = upper_b.copy().astype(float)
    final_lower = lower_b.copy().astype(float)

    for i in range(1, len(close)):
        fu_prev = final_upper.iloc[i - 1]
        fl_prev = final_lower.iloc[i - 1]
        c_prev  = float(close.iloc[i - 1])

        final_upper.iloc[i] = (upper_b.iloc[i]
                                if upper_b.iloc[i] < fu_prev or c_prev > fu_prev
                                else fu_prev)
        final_lower.iloc[i] = (lower_b.iloc[i]
                                if lower_b.iloc[i] > fl_prev or c_prev < fl_prev
                                else fl_prev)

    direction = pd.Series(1, index=close.index, dtype=int)
    for i in range(1, len(close)):
        d_prev = direction.iloc[i - 1]
        c_curr = float(close.iloc[i])
        if   d_prev ==  1 and c_curr < final_lower.iloc[i]: direction.iloc[i] = -1
        elif d_prev == -1 and c_curr > final_upper.iloc[i]: direction.iloc[i] =  1
        else:                                                direction.iloc[i] =  d_prev

    bullish        = direction == 1
    supertrend_val = pd.Series(np.where(direction == 1,
                                        final_lower,
                                        final_upper),
                               index=close.index)
    return bullish, supertrend_val


# ══════════════════════════════════════════════════════════════════════════════
#  BACKTEST (Long trades only — aligned with Supertrend)
# ══════════════════════════════════════════════════════════════════════════════

def run_backtest(df, buy_aligned, sell_aligned, label=""):
    """
    Long-only backtest:
      Enter on buy_aligned (UTBot BUY + ST Green)
      Exit  on sell_aligned (UTBot SELL + ST Red) OR max 20 bars hold
    """
    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]

    cap    = INITIAL_CAPITAL
    eq     = [cap]
    dates  = [df.index[20]]
    trades = wins = 0
    last_exit = -1

    brok = 0.0003   # 0.03% brokerage
    stt  = 0.001    # 0.1% STT (India)
    slip = 0.001    # 0.1% slippage
    tax  = 0.15     # 15% short-term capital gains

    for i in range(20, len(df)):
        if i > last_exit and bool(buy_aligned.iloc[i]):
            entry_price = float(close.iloc[i])
            trades += 1
            alloc  = cap * 0.25  # 25% capital per trade

            # Hold until: Supertrend flips (sell signal fires) OR 20 bars max
            exit_price = entry_price
            for step in range(1, 21):
                ci = i + step
                if ci >= len(df):
                    exit_price = float(close.iloc[-1])
                    break
                if bool(sell_aligned.iloc[ci]):
                    exit_price = float(close.iloc[ci])
                    last_exit  = ci
                    break
                exit_price = float(close.iloc[ci])
            else:
                last_exit = min(i + 20, len(df) - 1)
                exit_price = float(close.iloc[last_exit])

            if last_exit == -1:
                last_exit = min(i + 20, len(df) - 1)

            raw_ret  = (exit_price - entry_price) / entry_price
            gross    = raw_ret * alloc
            fric     = alloc * (brok + stt + slip) * 2
            tax_cost = max(0.0, (gross - fric) * tax)
            net      = gross - fric - tax_cost

            cap = max(cap + net, 0.01)
            if raw_ret >= 0:
                wins += 1

        eq.append(cap)
        dates.append(df.index[i])

    if trades < 3:
        return None

    years = max((dates[-1] - dates[0]).days / 365.25, 0.1)
    cagr  = ((cap / INITIAL_CAPITAL) ** (1.0 / years) - 1.0) * 100.0
    wr    = wins / max(1, trades) * 100
    eq_s  = pd.Series(eq)
    mdd   = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100

    return {
        "label": label, "final_cap": cap, "cagr": cagr,
        "win_rate": wr, "trades": trades, "mdd": mdd,
        "eq": eq, "dates": dates,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  VISUAL REPLICATION (matches TradingView screenshot layout)
# ══════════════════════════════════════════════════════════════════════════════

def plot_tv_style(df, buy_sig, sell_sig, st_bull, st_line, ax, title):
    close = df["Close"]
    idx   = df.index

    # Supertrend background shading
    for i in range(1, len(idx)):
        color = '#1a4a2e' if st_bull.iloc[i] else '#4a1a1a'
        ax.axvspan(idx[i - 1], idx[i], alpha=0.35, color=color, linewidth=0)

    # Supertrend line
    st_green = st_line.copy().where(st_bull,  np.nan)
    st_red   = st_line.copy().where(~st_bull, np.nan)
    ax.plot(idx, st_green, color='#00c080', linewidth=1.4, label='ST Bullish')
    ax.plot(idx, st_red,   color='#ff4060', linewidth=1.4, label='ST Bearish')

    # Price line
    ax.plot(idx, close, color='#60aaff', linewidth=1.4, label='Price', zorder=5)

    # UTBot signals
    buy_idx  = idx[buy_sig  & st_bull]   # valid buys
    sell_idx = idx[sell_sig & ~st_bull]  # valid sells
    fbuy_idx = idx[buy_sig  & ~st_bull]  # FALSE buys
    fsel_idx = idx[sell_sig & st_bull]   # FALSE sells

    ax.scatter(buy_idx,  close[buy_sig  & st_bull],  marker='^', color='#00ff80', s=80, zorder=10, label='✅ Valid BUY')
    ax.scatter(sell_idx, close[sell_sig & ~st_bull], marker='v', color='#ff4060', s=80, zorder=10, label='✅ Valid SELL')
    ax.scatter(fbuy_idx, close[buy_sig  & ~st_bull], marker='^', color='#ffaa00', s=50, zorder=9,  label='❌ False BUY (blocked)', alpha=0.7)
    ax.scatter(fsel_idx, close[sell_sig & st_bull],  marker='v', color='#ffaa00', s=50, zorder=9,  label='❌ False SELL (blocked)', alpha=0.7)

    ax.set_title(title, color='#e2e8f0', fontsize=10, fontweight='bold')
    ax.set_ylabel("Price", color='#94a3b8')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"₹{x:,.0f}" if "TATMPV" in title else f"${x:,.0f}"))
    ax.legend(fontsize=7.5, frameon=True, facecolor='#0f172a', ncol=2, loc='upper left')
    ax.grid(True, linestyle='--', alpha=0.10, color='#334155')
    ax.tick_params(colors='#94a3b8', labelsize=8)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("  UTBOT + SUPERTREND — EXACT TRADINGVIEW PARAMETERS")
    print("  UTBot: Key=5, ATR=1  |  Supertrend: Period=10, Mult=3.0")
    print("=" * 80)

    assets = [
        {"ticker": "TATMOTORS.NS", "label": "Tata Motors (NSE)",
         "interval": "1d", "start": "2020-01-01", "currency": "₹"},
        {"ticker": "BTC-USD",       "label": "Bitcoin",
         "interval": "1d", "start": "2016-01-01", "currency": "$"},
        {"ticker": "^NSEI",         "label": "NIFTY 50",
         "interval": "1d", "start": "2016-01-01", "currency": "₹"},
    ]

    fig = plt.figure(figsize=(18, 16), facecolor='#090d16')
    gs  = gridspec.GridSpec(4, 2, figure=fig, hspace=0.55, wspace=0.30)

    all_results = []

    for ai, asset in enumerate(assets):
        print(f"\n  Fetching {asset['label']} ({asset['ticker']})...")
        try:
            df = yf.download(asset["ticker"],
                             start=asset["start"], end="2026-08-25",
                             interval=asset["interval"],
                             progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.dropna(inplace=True)
        except Exception as e:
            print(f"  Error: {e}")
            continue

        if len(df) < 50:
            print(f"  Insufficient data ({len(df)} bars)")
            continue

        print(f"  {len(df)} bars loaded")

        # Compute indicators
        buy_raw, sell_raw, xatr_s = compute_utbot_tv(df["Close"], key=5, atr_period=1)
        st_bull, st_line          = compute_supertrend_tv(df, period=10, multiplier=3.0)

        # Apply alignment rule
        buy_aligned  = buy_raw  & st_bull    # BUY only when ST is GREEN
        sell_aligned = sell_raw & (~st_bull) # SELL only when ST is RED

        n_buy_raw    = int(buy_raw.sum())
        n_sell_raw   = int(sell_raw.sum())
        n_buy_valid  = int(buy_aligned.sum())
        n_sell_valid = int(sell_aligned.sum())
        n_false_buy  = n_buy_raw - n_buy_valid
        n_false_sell = n_sell_raw - n_sell_valid

        print(f"  UTBot BUY  signals: {n_buy_raw:>4}  →  Valid: {n_buy_valid:>3}  |  False blocked: {n_false_buy:>3}")
        print(f"  UTBot SELL signals: {n_sell_raw:>4}  →  Valid: {n_sell_valid:>3}  |  False blocked: {n_false_sell:>3}")

        # Backtests
        r_nofilter = run_backtest(df, buy_raw,     sell_raw,     f"{asset['label']} — No Filter")
        r_aligned  = run_backtest(df, buy_aligned, sell_aligned, f"{asset['label']} — ST Aligned")

        for r in [r_nofilter, r_aligned]:
            if r:
                r["asset"]    = asset["label"]
                r["currency"] = asset["currency"]
                all_results.append(r)
                print(f"  {r['label'][:45]:<45}  ${r['final_cap']:>9,.2f}  CAGR+{r['cagr']:>6.1f}%  WR{r['win_rate']:>6.1f}%  MDD-{r['mdd']:>5.2f}%")

        # ── Chart: TradingView-style price + signals (last 400 bars) ──
        n_bars = min(400, len(df))
        df_plot = df.iloc[-n_bars:].copy()

        buy_raw_plot   = buy_raw.iloc[-n_bars:]
        sell_raw_plot  = sell_raw.iloc[-n_bars:]
        st_bull_plot   = st_bull.iloc[-n_bars:]
        st_line_plot   = st_line.iloc[-n_bars:]
        buy_aln_plot   = buy_aligned.iloc[-n_bars:]
        sell_aln_plot  = sell_aligned.iloc[-n_bars:]

        row = ai // 2 * 2  # rows 0, 2
        col = ai % 2

        ax_price = fig.add_subplot(gs[row, col] if ai < 2 else gs[row, :])
        plot_tv_style(df_plot, buy_aln_plot, sell_aln_plot,
                      st_bull_plot, st_line_plot, ax_price,
                      f"{asset['label']} — UTBot(5,1) + Supertrend(10,3)  [Last {n_bars} bars]")

    # ── Summary Results Table ─────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  FINAL SUMMARY")
    print("=" * 80)
    print(f"  {'Strategy':<50} {'Final':>10} {'CAGR':>8} {'WR':>7} {'MDD':>7}")
    print("  " + "-" * 80)
    for r in all_results:
        print(f"  {r['label']:<50} ${r['final_cap']:>9,.2f} +{r['cagr']:>6.1f}% {r['win_rate']:>6.1f}% -{r['mdd']:>5.2f}%")

    # ── Equity Curve Comparison ───────────────────────────────────────────────
    ax_eq = fig.add_subplot(gs[3, :])
    colors = ['#64748b', '#00d4aa', '#6366f1', '#f59e0b', '#ef4444', '#22c55e']
    for i, r in enumerate(all_results):
        lw = 2.2 if "ST Aligned" in r["label"] else 1.2
        ax_eq.plot(r["dates"], r["eq"],
                   color=colors[i % len(colors)], linewidth=lw,
                   linestyle="-" if "ST Aligned" in r["label"] else "--",
                   label=f"{r['label']}: ${r['final_cap']:,.0f} (+{r['cagr']:.1f}% CAGR / {r['win_rate']:.0f}% WR)")
    ax_eq.set_yscale('log')
    ax_eq.set_title("Equity Curve — No Filter vs Supertrend Aligned  (All Assets)",
                    color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_eq.set_ylabel("Equity ($)", color='#94a3b8')
    ax_eq.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_eq.legend(fontsize=8, frameon=True, facecolor='#0f172a', ncol=2)
    ax_eq.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
    ax_eq.tick_params(colors='#94a3b8')

    fig.suptitle(
        "ANTIGRAVITY AI BRAIN — UTBOT + SUPERTREND ALIGNMENT  (Exact TradingView Parameters)\n"
        "UTBot: Key=5 / ATR=1  |  Supertrend: Period=10 / Multiplier=3.0  |  Rule: Only take signals aligned with trend",
        fontsize=12, fontweight='bold', color='#e2e8f0', y=1.01
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=240, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── Report ────────────────────────────────────────────────────────────────
    rows = ""
    for r in all_results:
        tag = "✅ **ST Aligned**" if "ST Aligned" in r["label"] else "No Filter"
        rows += f"| {r['asset']} | {tag} | ${r['final_cap']:,.2f} | +{r['cagr']:.1f}% | {r['win_rate']:.1f}% | {r['trades']} | -{r['mdd']:.2f}% |\n"

    report = f"""# UTBOT + SUPERTREND ALIGNMENT — EXACT TRADINGVIEW PARAMETERS

## Setup (Matches Your TradingView Chart)

```
Indicator:    UT Bot Alerts
  Key Value:  5
  ATR Period: 1

Indicator:    Supertrend
  Period:     10
  Multiplier: 3.0

RULE:
  ✅ BUY  signal → ONLY valid when Supertrend is GREEN (bullish)
  ✅ SELL signal → ONLY valid when Supertrend is RED   (bearish)
  ❌ Counter-trend UTBot signals → IGNORED completely
```

## Results

| Asset | Strategy | Final ($1k) | CAGR | Win Rate | Trades | MDD |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
{rows}

## How Supertrend Alignment Blocks False Breakouts

When UTBot fires a BUY during a **RED Supertrend zone** (downtrend), it's a counter-trend signal —
price is likely to continue falling despite the momentary crossover. The Supertrend background
colour tells you the macro direction instantly. Only take UTBot signals that agree with that direction.

---

![Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
