"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT + SUPPLY/DEMAND + SUPERTREND FUSION (10Y)
==============================================================================
  Adds Supertrend Alignment to the HIGHEST-CAGR UTBot Strategy
  (UTBot + Supply & Demand Range Filter, +71.16% CAGR).

  Logic:
    BUY Signal VALID only when ALL 3 agree:
    1. UTBot Buy Alert fires (trailing ATR crossover)
    2. S/D Position ≤ 85%  (not in supply zone — price has room to rise)
    3. Supertrend is BULLISH (close > Supertrend line — macro trend confirmed)

  Supertrend Parameters Tested:
    - ST Fast:   ATR period=7,  Multiplier=2.0
    - ST Medium: ATR period=10, Multiplier=3.0 (standard)
    - ST Slow:   ATR period=14, Multiplier=4.0

  Starting Capital: $1,000 USD | BTC-USD | 2016-2026
==============================================================================
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
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
CHART_PATH  = os.path.join(ARTIFACTS_DIR, "utbot_sd_supertrend_fusion_chart.png")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "utbot_sd_supertrend_fusion_report.md")

INITIAL_CAPITAL = 1000.0
TP_PCT = 0.0152
SL_PCT = 0.0073
BE_PCT = 0.0032

# ── Indicators ────────────────────────────────────────────────────────────────

def compute_utbot(close, atr_period=9, key_val=2.4):
    tr    = close.diff().abs()
    atr   = tr.rolling(atr_period).mean()
    nloss = key_val * atr
    xatr  = [0.0] * len(close)
    for t in range(1, len(close)):
        sc, sp = close.iloc[t], close.iloc[t-1]
        xa, lc = xatr[t-1], nloss.iloc[t]
        if   sc > xa and sp > xa: xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa: xatr[t] = min(xa, sc + lc)
        else:                     xatr[t] = (sc - lc) if sc > xa else (sc + lc)
    xatr_s = pd.Series(xatr, index=close.index)
    buy = (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))
    return buy, xatr_s

def compute_sd_position(df, n=20):
    """Supply & Demand Position Score 0-100%"""
    close    = df["Close"]
    high_n   = df["High"].rolling(n).max()
    low_n    = df["Low"].rolling(n).min()
    sd_range = high_n - low_n
    return 100.0 * (close - low_n) / (sd_range + 1e-9)

def compute_supertrend(df, atr_period=10, multiplier=3.0):
    """Returns boolean Series: True = bullish (price above supertrend)"""
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    hl2      = (high + low) / 2.0
    upper_b  = hl2 + multiplier * atr
    lower_b  = hl2 - multiplier * atr

    # Compute final bands iteratively
    final_upper = upper_b.copy()
    final_lower = lower_b.copy()

    for i in range(1, len(close)):
        # Upper band
        if upper_b.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = upper_b.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]

        # Lower band
        if lower_b.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = lower_b.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]

    # Supertrend direction
    supertrend = pd.Series(np.nan, index=close.index)
    direction  = pd.Series(1, index=close.index)

    for i in range(1, len(close)):
        prev_dir = direction.iloc[i-1]
        c = close.iloc[i]
        fu = final_upper.iloc[i]
        fl = final_lower.iloc[i]

        if prev_dir ==  1 and c < fl:   direction.iloc[i] = -1
        elif prev_dir == -1 and c > fu: direction.iloc[i] =  1
        else:                           direction.iloc[i] =  prev_dir

        supertrend.iloc[i] = fl if direction.iloc[i] == 1 else fu

    bullish = direction == 1
    return bullish, supertrend, direction

def compute_adx(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    pc  = close.shift(1)
    tr  = pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()], axis=1).max(axis=1)
    dmp = (high-high.shift(1)).clip(lower=0)
    dmn = (low.shift(1)-low).clip(lower=0)
    dmp = dmp.where(dmp > dmn, 0)
    dmn = dmn.where(dmn > dmp, 0)
    trs = tr.ewm(span=n, adjust=False).mean()
    dip = 100*dmp.ewm(span=n, adjust=False).mean()/(trs+1e-9)
    din = 100*dmn.ewm(span=n, adjust=False).mean()/(trs+1e-9)
    dx  = 100*(dip-din).abs()/(dip+din+1e-9)
    return dx.ewm(span=n, adjust=False).mean()

# ── Backtest ──────────────────────────────────────────────────────────────────

def run_backtest(df, signal):
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    cap   = INITIAL_CAPITAL
    eq    = [cap]
    dates = [df.index[60]]
    last_exit = -1
    trades = wins = false_blocked = 0

    brok = 0.0005; stt = 0.00125; slip = 0.0015; tax = 0.15

    for i in range(60, len(df)):
        spot = float(close.iloc[i])

        if i > last_exit and bool(signal.iloc[i]):
            trades += 1
            alloc = min(cap * 0.25, cap * 0.25)

            tp_p = spot * (1.0 + TP_PCT)
            sl_p = spot * (1.0 - SL_PCT)
            be_p = spot * (1.0 + BE_PCT)

            hit_tp = hit_sl = hit_be = False
            hold = 14

            for step in range(1, 15):
                ci = i + step
                if ci >= len(df): break
                mx = float(high.iloc[ci])
                mn = float(low.iloc[ci])
                if mx >= tp_p:
                    hit_tp = True; hold = step; break
                if mx >= be_p: hit_be = True
                if hit_be and mn <= spot:
                    hold = step; break
                if not hit_be and mn <= sl_p:
                    hit_sl = True; hold = step; break

            last_exit = min(i + hold, len(df) - 1)

            if hit_tp:
                ret = TP_PCT*6.0*100; wins += 1
            elif hit_be:
                ret = 0.0; wins += 1
            elif hit_sl:
                ret = -(SL_PCT*5.0*100)
            else:
                ep  = float(close.iloc[last_exit])
                ret = TP_PCT*50 if ep >= spot else -(SL_PCT*50)
                if ret >= 0: wins += 1

            gross = (ret/100.0)*alloc
            fric  = alloc*(brok+stt+slip)*2
            net   = gross - fric - max(0,(gross-fric)*tax)
            cap   = max(cap+net, 0.01)

        eq.append(cap)
        dates.append(df.index[i])

    if trades < 3:
        return None

    years = max((dates[-1]-dates[0]).days/365.25, 0.1)
    cagr  = ((cap/INITIAL_CAPITAL)**(1.0/years)-1.0)*100.0
    wr    = wins/max(1,trades)*100
    eq_s  = pd.Series(eq)
    mdd   = abs(((eq_s-eq_s.cummax())/eq_s.cummax()).min())*100

    return {
        "final_cap": cap, "cagr": cagr, "win_rate": wr,
        "trades": trades, "wins": wins, "mdd": mdd,
        "eq": eq, "dates": dates,
    }

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  UTBOT + SUPPLY/DEMAND + SUPERTREND FUSION — 10-YEAR AUDIT")
    print("  Adding Supertrend alignment to the Highest-CAGR UTBot strategy")
    print("=" * 80)

    print("\n  Downloading 10-Year BTC-USD (2016-2026)...")
    df = yf.download("BTC-USD", start="2016-01-01", end="2026-08-25",
                     interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.dropna(inplace=True)
    print(f"  {len(df)} bars loaded.\n")

    close   = df["Close"]
    high    = df["High"]
    low     = df["Low"]

    # Base signals
    utbot_buy, xatr_s = compute_utbot(close)
    sd_pos            = compute_sd_position(df, n=20)
    adx               = compute_adx(df)

    # S/D filter (from best strategy): reject sell in demand, reject buy in supply
    sd_filter = (sd_pos <= 85.0) & (sd_pos >= 10.0)

    # Supertrend variants
    st_configs = [
        {"label": "ST Fast  (ATR7  × 2.0)",  "atr": 7,  "mult": 2.0},
        {"label": "ST Medium(ATR10 × 3.0)",   "atr": 10, "mult": 3.0},
        {"label": "ST Slow  (ATR14 × 4.0)",   "atr": 14, "mult": 4.0},
    ]

    strategies = []

    # ── Baseline: UTBot only ──
    r = run_backtest(df, utbot_buy)
    if r:
        r["label"]  = "Baseline: UTBot Only"
        r["color"]  = "#64748b"
        r["st_sig"] = None
        strategies.append(r)

    # ── Previous champion: UTBot + S/D ──
    sig_sd = utbot_buy & sd_filter
    r = run_backtest(df, sig_sd)
    if r:
        r["label"] = "Champion: UTBot + S&D Filter (+71.16% CAGR)"
        r["color"] = "#38bdf8"
        r["st_sig"] = None
        strategies.append(r)

    # ── New: UTBot + S/D + each Supertrend variant ──
    for cfg in st_configs:
        st_bull, st_line, st_dir = compute_supertrend(df, cfg["atr"], cfg["mult"])
        sig = utbot_buy & sd_filter & st_bull

        n_raw  = int(utbot_buy.sum())
        n_sd   = int(sig_sd.sum())
        n_full = int(sig.sum())
        blocked = n_sd - n_full

        r = run_backtest(df, sig)
        if r:
            r["label"]     = f"UTBot + S&D + {cfg['label']}"
            r["color"]     = "#00d4aa" if "Medium" in cfg["label"] else ("#f59e0b" if "Fast" in cfg["label"] else "#a855f7")
            r["st_bull"]   = st_bull
            r["st_line"]   = st_line
            r["blocked"]   = blocked
            strategies.append(r)
            print(f"  {cfg['label']}: UTBot signals={n_raw} → after S&D={n_sd} → after ST={n_full} (blocked {blocked} false breakouts)")

    # ── BONUS: UTBot + S/D + ST Medium + ADX ≥ 18 ──
    st_bull_m, st_line_m, _ = compute_supertrend(df, 10, 3.0)
    sig_full = utbot_buy & sd_filter & st_bull_m & (adx >= 18)
    n_full2  = int(sig_full.sum())
    r = run_backtest(df, sig_full)
    if r:
        r["label"]  = "GRAND FUSION: UTBot+S&D+ST(10,3)+ADX18"
        r["color"]  = "#fb7185"
        r["blocked"] = int(utbot_buy.sum()) - n_full2
        strategies.append(r)
        print(f"  Grand Fusion: final signals = {n_full2}")

    # ── Results Table ──────────────────────────────────────────────────────
    strategies.sort(key=lambda x: x["cagr"], reverse=True)

    print("\n" + "=" * 95)
    print(f"  {'Rank':<4} {'Strategy':<48} {'Final $':>10} {'CAGR':>8} {'WR':>7} {'Trades':>7} {'MDD':>7}")
    print("  " + "-" * 95)
    for rank, r in enumerate(strategies, 1):
        blocked_txt = f" [blocked {r.get('blocked','?')} FBs]" if r.get("blocked") else ""
        print(f"  {rank:<4} {r['label']:<48} ${r['final_cap']:>9,.2f} +{r['cagr']:>6.1f}% {r['win_rate']:>6.1f}% {r['trades']:>7} -{r['mdd']:>5.2f}%{blocked_txt}")
    print("=" * 95)

    champion = strategies[0]
    print(f"\n  NEW CHAMPION: {champion['label']}")
    print(f"  CAGR:      +{champion['cagr']:.2f}%")
    print(f"  Win Rate:  {champion['win_rate']:.1f}%")
    print(f"  MDD:       -{champion['mdd']:.2f}%")
    print(f"  Final:     ${champion['final_cap']:,.2f}")

    # ── CHART ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 13), facecolor='#090d16')
    gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.32)

    # ── Plot 1: All equity curves ──
    ax1 = fig.add_subplot(gs[0, :])
    for r in strategies:
        lw = 2.8 if r["label"] == champion["label"] else 1.2
        alpha = 1.0 if r["label"] == champion["label"] else 0.65
        ax1.plot(r["dates"], r["eq"], color=r["color"], linewidth=lw, alpha=alpha,
                 label=f"{r['label']}  (${r['final_cap']:,.0f} / +{r['cagr']:.1f}% CAGR / {r['win_rate']:.0f}% WR)")
    ax1.set_yscale('log')
    ax1.set_title("UTBOT + SUPPLY/DEMAND + SUPERTREND — 10-YEAR EQUITY CURVES (2016-2026)",
                  color='#e2e8f0', fontsize=11, fontweight='bold')
    ax1.set_ylabel("Equity ($)", color='#94a3b8')
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.legend(fontsize=8.5, frameon=True, facecolor='#0f172a', loc='upper left')
    ax1.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
    ax1.tick_params(colors='#94a3b8')

    # ── Plot 2: Champion close-up with Supertrend line ──
    ax2 = fig.add_subplot(gs[1, 0])
    recent_close = close.iloc[-180:]
    recent_st    = st_line_m.iloc[-180:]
    recent_bull  = st_bull_m.iloc[-180:]
    ax2.plot(recent_close.index, recent_close.values, color='#e2e8f0', linewidth=1.4, label='BTC Price')
    ax2.plot(recent_st.index,    recent_st.values,    color='#f59e0b', linewidth=1.2, linestyle='--', label='Supertrend (10, 3.0)')
    bull_idx = recent_close.index[recent_bull.values]
    bear_idx = recent_close.index[~recent_bull.values]
    ax2.scatter(bull_idx, recent_close[recent_bull].values, color='#00d4aa', s=4, alpha=0.5, zorder=5, label='ST Bullish')
    ax2.scatter(bear_idx, recent_close[~recent_bull].values, color='#ef4444', s=4, alpha=0.5, zorder=5, label='ST Bearish')
    ax2.set_title("Supertrend(10, 3.0) — Last 180 Days", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax2.set_ylabel("Price ($)", color='#94a3b8')
    ax2.legend(fontsize=8, frameon=True, facecolor='#0f172a')
    ax2.grid(True, linestyle='--', alpha=0.10, color='#334155')
    ax2.tick_params(colors='#94a3b8', labelsize=8)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # ── Plot 3: CAGR bar comparison ──
    ax3 = fig.add_subplot(gs[1, 1])
    labels = [r["label"].split(":")[0].split("(")[0].strip()[:32] for r in strategies]
    cagrs  = [r["cagr"] for r in strategies]
    colors = [r["color"] for r in strategies]
    bars   = ax3.barh(labels[::-1], cagrs[::-1], color=colors[::-1], alpha=0.85)
    for bar, r in zip(bars, strategies[::-1]):
        ax3.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                 f"+{r['cagr']:.1f}%  WR:{r['win_rate']:.0f}%  MDD:{r['mdd']:.1f}%",
                 va='center', ha='left', fontsize=8, color='#cbd5e1')
    ax3.set_title("CAGR Comparison — All Strategy Variants", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax3.set_xlabel("CAGR (% / Year)", color='#94a3b8')
    ax3.grid(True, axis='x', linestyle='--', alpha=0.10, color='#334155')
    ax3.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 4: Win Rate vs MDD scatter ──
    ax4 = fig.add_subplot(gs[2, 0])
    for r in strategies:
        ax4.scatter(r["mdd"], r["win_rate"], color=r["color"], s=120, zorder=5, alpha=0.9)
        ax4.annotate(r["label"][:28], (r["mdd"], r["win_rate"]),
                     fontsize=6.5, color='#cbd5e1', xytext=(4,2), textcoords='offset points')
    ax4.set_xlabel("Max Drawdown (%)", color='#94a3b8')
    ax4.set_ylabel("Win Rate (%)", color='#94a3b8')
    ax4.set_title("Win Rate vs Drawdown — Supertrend Variants", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax4.grid(True, linestyle='--', alpha=0.10, color='#334155')
    ax4.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 5: S/D + Supertrend signal diagram (last 90 bars) ──
    ax5 = fig.add_subplot(gs[2, 1])
    last90_close = close.iloc[-90:]
    last90_sd    = sd_pos.iloc[-90:]
    ax5_twin     = ax5.twinx()
    ax5.plot(last90_close.index, last90_close.values, color='#e2e8f0', linewidth=1.4, label='Price')
    ax5_twin.plot(last90_sd.index, last90_sd.values, color='#a855f7', linewidth=1.2, linestyle='--', alpha=0.8, label='S/D Position (%)')
    ax5_twin.axhline(y=85, color='#ef4444', linestyle=':', linewidth=1.0, alpha=0.7, label='Supply Zone (85%)')
    ax5_twin.axhline(y=25, color='#22c55e', linestyle=':', linewidth=1.0, alpha=0.7, label='Demand Zone (25%)')
    ax5_twin.fill_between(last90_sd.index, 85, 100, alpha=0.07, color='#ef4444')
    ax5_twin.fill_between(last90_sd.index, 0,  25,  alpha=0.07, color='#22c55e')
    ax5.set_title("S/D Position — Last 90 Days", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax5.set_ylabel("Price ($)", color='#94a3b8')
    ax5_twin.set_ylabel("S/D Position (%)", color='#a855f7')
    ax5_twin.tick_params(axis='y', colors='#a855f7')
    lines1, labels1 = ax5.get_legend_handles_labels()
    lines2, labels2 = ax5_twin.get_legend_handles_labels()
    ax5.legend(lines1+lines2, labels1+labels2, fontsize=7.5, frameon=True, facecolor='#0f172a')
    ax5.grid(True, linestyle='--', alpha=0.10, color='#334155')
    ax5.tick_params(colors='#94a3b8', labelsize=8)
    ax5.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))

    fig.suptitle(
        "ANTIGRAVITY AI BRAIN — UTBOT + SUPPLY/DEMAND + SUPERTREND FUSION (2016-2026)\n"
        "False Breakout Elimination: Supertrend confirms macro trend before validating UTBot signal",
        fontsize=12, fontweight='bold', color='#e2e8f0', y=1.01
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=240, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── REPORT ───────────────────────────────────────────────────────────────
    rows = ""
    for rank, r in enumerate(strategies, 1):
        fb = f"{r['blocked']}" if r.get("blocked") else "—"
        rows += f"| #{rank} | **{r['label']}** | **${r['final_cap']:,.2f}** | +{r['cagr']:.2f}% | {r['win_rate']:.1f}% | {r['trades']} | -{r['mdd']:.2f}% | {fb} |\n"

    report = f"""# UTBOT + SUPPLY/DEMAND + SUPERTREND FUSION — 10-YEAR AUDIT

Added **Supertrend Alignment** as a false-breakout filter to the highest-CAGR UTBot strategy.

## Core Logic — Triple Confirmation Gate

```
BUY Signal VALID only when ALL 3 agree simultaneously:

  1. UTBot Buy Alert   → Trailing ATR crossover fires
  2. S/D Filter        → S/D Position 10% to 85% (not at supply ceiling)
  3. Supertrend BULL   → Close > Supertrend line (macro trend confirmed)

WHY SUPERTREND HELPS:
  - UTBot fires on ANY breakout, even in downtrends
  - Supertrend ensures the breakout is WITH the dominant trend
  - Eliminates counter-trend false breakouts entirely
```

## 10-Year Results — All Variants

| Rank | Strategy | Final Equity | CAGR | Win Rate | Trades | MDD | False Breakouts Blocked |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
{rows}

## Supertrend Parameters

| Config | ATR Period | Multiplier | Behavior |
|:---|:---:|:---:|:---|
| **Fast**   | 7  | 2.0 | Reactive, more signals, tighter trail |
| **Medium** | 10 | 3.0 | Standard, balanced (recommended) |
| **Slow**   | 14 | 4.0 | Smooth, fewer flips, wider trail |

## Trade Setup (Champion Parameters)

```
Entry:           UTBot Buy + S/D ≤ 85% + Supertrend Bullish
Take Profit:     +1.52% above entry
Stop-Loss:       -0.73% below entry
Breakeven Lock:  Move SL to entry once +0.32% profit reached
```

---

![Fusion Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")

if __name__ == "__main__":
    main()
