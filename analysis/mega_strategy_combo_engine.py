"""
==============================================================================
  ANTIGRAVITY AI BRAIN — MEGA STRATEGY COMBINATION ENGINE (10-YEAR AUDIT)
==============================================================================
  Tests every meaningful combination of the 8 core strategies built in this
  session, finding the single best multi-layer fusion engine.

  STRATEGIES COMBINED:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  A) UTBot MC Champion  — ADX-gated trailing stop breakout
  B) Market Geometry    — Fibonacci arc + harmonic price geometry
  C) Rust HFT Micro     — Sub-second momentum burst signal proxy
  D) DSS2 Oscillator    — Double-Smoothed Stochastic (DSS Bressert)
  E) CHESS Engine       — Chakravyuh Harmonic Entry Signal System
                          (RSI + Supertrend + VWAP confluence)
  F) Dependable Fortress— Kakushadze #151 Residual Momentum Rank
  G) Swarm Call Spread  — 52-week high momentum + ATR squeeze
  H) Jim Simons Factor  — Multi-factor cross-asset momentum model

  COMBINATION APPROACH:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Each combo requires AGREEMENT from its component strategies:
  - 2-strategy combos:  both must fire BUY
  - 3-strategy combos:  all 3 must agree
  - GRAND MASTER:       best 4 must all agree simultaneously

  10-Year Backtest: BTC-USD (2016-2026, 3,500+ bars)
  Starting Capital: $1,000 USD
==============================================================================
"""

import os, sys, datetime
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
CHART_PATH  = os.path.join(ARTIFACTS_DIR, "mega_strategy_combo_chart.png")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "mega_strategy_combo_report.md")

INITIAL_CAPITAL = 1000.0
TP_PCT  = 0.0152
SL_PCT  = 0.0073
BE_PCT  = 0.0032

# ══════════════════════════════════════════════════════════════════
#  INDIVIDUAL STRATEGY SIGNAL GENERATORS
# ══════════════════════════════════════════════════════════════════

def sig_utbot(df):
    """A) UTBot MC Champion — ADX-gated trailing stop"""
    close = df["Close"]
    tr    = close.diff().abs()
    atr   = tr.rolling(9).mean()
    nloss = 2.4 * atr
    xatr  = [0.0] * len(close)
    for t in range(1, len(close)):
        sc, sp = close.iloc[t], close.iloc[t-1]
        xa, lc = xatr[t-1], nloss.iloc[t]
        if sc > xa and sp > xa:    xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa:  xatr[t] = min(xa, sc + lc)
        else:                      xatr[t] = (sc - lc) if sc > xa else (sc + lc)
    xatr_s = pd.Series(xatr, index=close.index)
    raw_buy = (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))

    # ADX gate
    high, low, pc = df["High"], df["Low"], close.shift(1)
    tr2  = pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()], axis=1).max(axis=1)
    dmp  = (high-high.shift(1)).clip(lower=0)
    dmn  = (low.shift(1)-low).clip(lower=0)
    dmp  = dmp.where(dmp > dmn, 0)
    dmn  = dmn.where(dmn > dmp, 0)
    trs  = tr2.ewm(span=14, adjust=False).mean()
    dip  = 100*dmp.ewm(span=14, adjust=False).mean()/(trs+1e-9)
    din  = 100*dmn.ewm(span=14, adjust=False).mean()/(trs+1e-9)
    dx   = 100*(dip-din).abs()/(dip+din+1e-9)
    adx  = dx.ewm(span=14, adjust=False).mean()

    return raw_buy & (adx >= 18)

def sig_market_geometry(df):
    """B) Market Geometry — Fibonacci retracement + harmonic confluence"""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # 20-bar swing high/low Fibonacci levels
    roll_high = high.rolling(20).max()
    roll_low  = low.rolling(20).min()
    fib_range = roll_high - roll_low
    fib_618   = roll_low  + 0.618 * fib_range
    fib_382   = roll_low  + 0.382 * fib_range

    # Buy signal: price bounces off 0.382-0.618 Fibonacci zone
    in_fib_zone = (close >= fib_382) & (close <= fib_618)
    # with upward momentum (close > 5-EMA)
    ema5 = close.ewm(span=5).mean()
    momentum_up = close > ema5

    # Harmonic: price makes a higher low vs prev 3-bar low
    higher_low  = low > low.shift(3)

    return in_fib_zone & momentum_up & higher_low

def sig_rust_hft(df):
    """C) Rust HFT Micro — Momentum burst proxy (fast EMA crossover + vol surge)"""
    close = df["Close"]
    vol   = df["Volume"]

    ema3  = close.ewm(span=3).mean()
    ema8  = close.ewm(span=8).mean()
    volma = vol.rolling(10).mean()

    # Fast EMA crosses above slow + volume confirmation
    cross_up  = (ema3 > ema8) & (ema3.shift(1) <= ema8.shift(1))
    vol_burst = vol >= volma * 1.15

    # Price above 20-EMA (trend aligned)
    above_trend = close > close.ewm(span=20).mean()

    return cross_up & vol_burst & above_trend

def sig_dss2(df):
    """D) DSS2 — Double-Smoothed Stochastic Bressert Oscillator"""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    n = 13  # DSS period

    # Stochastic %K
    lowest_low   = low.rolling(n).min()
    highest_high = high.rolling(n).max()
    stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-9)

    # First smoothing (5-period EMA of stoch)
    smooth1 = stoch_k.ewm(span=5).mean()

    # Re-normalize
    s1_lo = smooth1.rolling(n).min()
    s1_hi = smooth1.rolling(n).max()
    dss1  = 100 * (smooth1 - s1_lo) / (s1_hi - s1_lo + 1e-9)

    # Second smoothing (5-period EMA) = DSS2 line
    dss2 = dss1.ewm(span=5).mean()

    # Signal line
    dss2_signal = dss2.ewm(span=3).mean()

    # Buy: DSS2 crosses above signal line from oversold (<30)
    cross_up = (dss2 > dss2_signal) & (dss2.shift(1) <= dss2_signal.shift(1))
    oversold = dss2 < 40

    return cross_up & oversold

def sig_chess(df):
    """E) CHESS Engine — RSI + Supertrend + VWAP Confluence"""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # RSI
    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi   = 100 - 100/(1 + gain/(loss+1e-9))

    # Supertrend (ATR multiplier 3.0, period 10)
    tr    = pd.concat([(high-low),(high-close.shift(1)).abs(),(low-close.shift(1)).abs()], axis=1).max(axis=1)
    atr10 = tr.rolling(10).mean()
    basic_upper = (high + low)/2 + 3.0 * atr10
    basic_lower = (high + low)/2 - 3.0 * atr10

    supertrend = pd.Series(np.nan, index=close.index)
    direction  = pd.Series(1, index=close.index)
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()

    for i in range(1, len(close)):
        fu_prev = final_upper.iloc[i-1]
        fl_prev = final_lower.iloc[i-1]
        bu_curr = basic_upper.iloc[i]
        bl_curr = basic_lower.iloc[i]
        c_prev  = close.iloc[i-1]
        c_curr  = close.iloc[i]

        final_upper.iloc[i] = bu_curr if bu_curr < fu_prev or c_prev > fu_prev else fu_prev
        final_lower.iloc[i] = bl_curr if bl_curr > fl_prev or c_prev < fl_prev else fl_prev

        if direction.iloc[i-1] == -1 and c_curr > final_upper.iloc[i]:
            direction.iloc[i] = 1
        elif direction.iloc[i-1] == 1 and c_curr < final_lower.iloc[i]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]

    supertrend_buy = direction == 1

    # VWAP
    typical = (high + low + close) / 3
    vwap = (typical * vol).rolling(20).sum() / (vol.rolling(20).sum() + 1e-9)
    above_vwap = close > vwap

    # CHESS signal: RSI 40-65 + Supertrend bullish + above VWAP
    rsi_ok = (rsi >= 40) & (rsi <= 65)
    return rsi_ok & supertrend_buy & above_vwap

def sig_dependable_fortress(df):
    """F) Dependable Fortress — Kakushadze #151 Residual Momentum Rank"""
    close = df["Close"]
    high  = df["High"]

    # Residual momentum: 20-day return minus 5-day return (medium - short)
    ret20 = close.pct_change(20)
    ret5  = close.pct_change(5)
    residual_mom = ret20 - ret5

    # Rank: is residual momentum in top 50% (positive)?
    rank_ok = residual_mom > 0

    # Additional: price making higher highs (52-week strength)
    high52 = high.rolling(252).max()
    near_high = close >= high52 * 0.92

    # Volume confirmation
    vol    = df["Volume"]
    volma  = vol.rolling(20).mean()
    vol_ok = vol >= volma * 0.9

    return rank_ok & near_high & vol_ok

def sig_swarm_call_spread(df):
    """G) Swarm Call Spread — 52-week momentum + ATR volatility squeeze"""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # 52-week high proximity (within 2%)
    high52 = high.rolling(252).max()
    near52 = close >= high52 * 0.98

    # EMA trend
    ema20  = close.ewm(span=20).mean()
    ema50  = close.ewm(span=50).mean()
    trend_up = ema20 > ema50

    # ATR volatility squeeze: 10-day ATR < 92% of 50-day ATR
    tr   = pd.concat([(high-low),(high-close.shift(1)).abs(),(low-close.shift(1)).abs()], axis=1).max(axis=1)
    atr10 = tr.rolling(10).mean()
    atr50 = tr.rolling(50).mean()
    vol_squeeze = (atr10 / (atr50 + 1e-9)) < 0.92

    return near52 & trend_up & vol_squeeze

def sig_jim_simons(df):
    """H) Jim Simons Multi-Factor — Mean-reversion + momentum + regime"""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # Factor 1: Short-term mean reversion (1-day return z-score over 20 days)
    ret1d   = close.pct_change(1)
    ret_mu  = ret1d.rolling(20).mean()
    ret_std = ret1d.rolling(20).std()
    zscore  = (ret1d - ret_mu) / (ret_std + 1e-9)
    mean_rev_buy = (zscore > -1.5) & (zscore < 0.5)  # slightly oversold

    # Factor 2: 5-day momentum positive
    mom5    = close.pct_change(5)
    mom_ok  = mom5 > 0

    # Factor 3: Volume-weighted momentum (OBV trending up)
    ret     = close.diff()
    obv     = np.where(ret > 0, vol, np.where(ret < 0, -vol, 0.0))
    obv_s   = pd.Series(obv, index=close.index).cumsum()
    obv_ma  = obv_s.rolling(20).mean()
    obv_up  = obv_s > obv_ma

    # Factor 4: Volatility regime — low vol (calm market = Simons edge)
    vol20   = close.pct_change().rolling(20).std() * np.sqrt(252)
    low_vol = vol20 < vol20.rolling(60).mean()

    return mean_rev_buy & mom_ok & obv_up & low_vol

# ══════════════════════════════════════════════════════════════════
#  BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════

def run_backtest(df, combined_signal, tp=TP_PCT, sl=SL_PCT, be=BE_PCT):
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    cap   = INITIAL_CAPITAL
    eq    = [cap]
    dates = [df.index[60]]
    last_exit = -1
    trades = wins = 0

    brok = 0.0005; stt = 0.00125; slip = 0.0015; tax = 0.15

    for i in range(60, len(df)):
        spot = float(close.iloc[i])
        if i > last_exit and bool(combined_signal.iloc[i]):
            trades += 1
            alloc = min(cap * 0.25, cap * 0.25)

            tp_p  = spot * (1.0 + tp)
            sl_p  = spot * (1.0 - sl)
            be_p  = spot * (1.0 + be)

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
                ret = tp * 6.0 * 100; wins += 1
            elif hit_be:
                ret = 0.0; wins += 1
            elif hit_sl:
                ret = -(sl * 5.0 * 100)
            else:
                ep = float(close.iloc[last_exit])
                ret = tp*50 if ep >= spot else -(sl*50)
                if ret >= 0: wins += 1

            gross = (ret / 100.0) * alloc
            fric  = alloc * (brok + stt + slip) * 2
            net   = gross - fric - max(0, (gross - fric) * tax)
            cap   = max(cap + net, 0.01)

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
        "final_cap": cap, "cagr": cagr, "win_rate": wr,
        "trades": trades, "wins": wins, "mdd": mdd,
        "eq": eq, "dates": dates,
        "profit": cap - INITIAL_CAPITAL,
    }

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("  ANTIGRAVITY AI BRAIN — MEGA STRATEGY COMBINATION ENGINE")
    print("  Testing all meaningful combos of 8 strategies over 10 years")
    print("=" * 80)

    print("\n  Downloading 10-Year BTC-USD data (2016-2026)...")
    df = yf.download("BTC-USD", start="2016-01-01", end="2026-08-25",
                     interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.dropna(inplace=True)
    print(f"  {len(df)} bars loaded.\n")

    # Generate all individual signals
    print("  Computing individual strategy signals...")
    signals = {
        "UTBot-MC":   sig_utbot(df),
        "MktGeo":     sig_market_geometry(df),
        "RustHFT":    sig_rust_hft(df),
        "DSS2":       sig_dss2(df),
        "CHESS":      sig_chess(df),
        "Fortress":   sig_dependable_fortress(df),
        "SwarmCS":    sig_swarm_call_spread(df),
        "Simons":     sig_jim_simons(df),
    }

    for name, sig in signals.items():
        n_signals = sig.sum()
        print(f"    {name:<12}: {n_signals:>4} signals in 10 years")

    # Build combination list
    names = list(signals.keys())
    combos = []

    # Individual strategies
    for n in names:
        combos.append({"label": n, "components": [n]})

    # Best 2-strategy combos (all pairs)
    import itertools
    for a, b in itertools.combinations(names, 2):
        combos.append({"label": f"{a}+{b}", "components": [a, b]})

    # Best 3-strategy combos (curated most promising)
    for a, b, c in itertools.combinations(names, 3):
        combos.append({"label": f"{a}+{b}+{c}", "components": [a, b, c]})

    # 4-strategy combos (top candidates)
    curated_4 = [
        ["UTBot-MC", "DSS2", "CHESS", "Simons"],
        ["UTBot-MC", "MktGeo", "Fortress", "SwarmCS"],
        ["UTBot-MC", "RustHFT", "DSS2", "CHESS"],
        ["MktGeo", "DSS2", "Fortress", "Simons"],
        ["UTBot-MC", "DSS2", "Fortress", "Simons"],
        ["RustHFT", "DSS2", "CHESS", "SwarmCS"],
        ["UTBot-MC", "CHESS", "Fortress", "Simons"],
        ["UTBot-MC", "MktGeo", "DSS2", "Fortress"],
    ]
    for c4 in curated_4:
        combos.append({"label": "+".join(c4), "components": c4})

    # Grand Master — all 8 agree
    combos.append({"label": "GRAND MASTER (ALL 8)", "components": names})

    print(f"\n  Running {len(combos)} strategy combinations...\n")

    results = []
    for combo in combos:
        # Build combined signal (AND of all components)
        combined = pd.Series(True, index=df.index)
        for c in combo["components"]:
            combined = combined & signals[c]

        r = run_backtest(df, combined)
        if r:
            r["label"] = combo["label"]
            r["n_strats"] = len(combo["components"])
            results.append(r)

    # Sort by Pareto score: Win Rate + CAGR - 2*MDD
    def pareto(r):
        return r["win_rate"] + r["cagr"] * 0.5 - r["mdd"] * 2.0

    results.sort(key=pareto, reverse=True)

    print("=" * 100)
    print(f"  {'Rank':<5} {'Combination':<45} {'Strats':<7} {'Final $':<12} {'CAGR':<8} {'Win%':<8} {'Trades':<7} {'MDD':<7} {'Score':<7}")
    print("  " + "-" * 100)
    for rank, r in enumerate(results[:20], 1):
        score = pareto(r)
        marker = " <-- CHAMPION" if rank == 1 else ""
        print(f"  {rank:<5} {r['label']:<45} {r['n_strats']:<7} ${r['final_cap']:<10,.0f} +{r['cagr']:<6.1f}% {r['win_rate']:<7.1f}% {r['trades']:<7} -{r['mdd']:<5.2f}% {score:<7.1f}{marker}")
    print("=" * 100)

    champion = results[0]
    print(f"\n  CHAMPION: {champion['label']}")
    print(f"  Win Rate:      {champion['win_rate']:.1f}%")
    print(f"  Final Equity:  ${champion['final_cap']:,.2f}")
    print(f"  CAGR:          +{champion['cagr']:.1f}%")
    print(f"  Trades:        {champion['trades']}")
    print(f"  MDD:           -{champion['mdd']:.2f}%")

    # ── CHARTS ───────────────────────────────────────────────────────────────

    fig = plt.figure(figsize=(18, 14), facecolor='#090d16')
    gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.32)

    # Colors by number of strategies
    def color_for(r):
        return {1: '#64748b', 2: '#38bdf8', 3: '#a855f7', 4: '#f59e0b', 8: '#ef4444'}.get(r["n_strats"], '#22c55e')

    # ── Plot 1: Top 15 Pareto scores bar ──
    ax1 = fig.add_subplot(gs[0, :])
    top15 = results[:15]
    labels = [r["label"] for r in top15]
    scores = [pareto(r) for r in top15]
    bar_cols = [color_for(r) for r in top15]
    bars = ax1.barh(labels[::-1], scores[::-1], color=bar_cols[::-1], alpha=0.85)
    for bar, r in zip(bars, top15[::-1]):
        ax1.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                 f"WR:{r['win_rate']:.0f}%  CAGR:+{r['cagr']:.0f}%  MDD:-{r['mdd']:.1f}%  ({r['trades']}T)",
                 va='center', ha='left', fontsize=7.5, color='#cbd5e1')
    ax1.set_title("TOP 15 STRATEGY COMBINATIONS — Pareto Score (Win Rate + CAGR − 2×MDD)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax1.set_xlabel("Pareto Score", color='#94a3b8')
    ax1.grid(True, axis='x', linestyle='--', alpha=0.10, color='#334155')
    ax1.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 2: Champion equity curve ──
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(champion["dates"], champion["eq"], color='#00d4aa', linewidth=2.5)
    ax2.fill_between(champion["dates"], INITIAL_CAPITAL, champion["eq"], alpha=0.10, color='#00d4aa')
    ax2.set_yscale('log')
    ax2.set_title(f"CHAMPION: {champion['label']}\n"
                  f"WR: {champion['win_rate']:.1f}%  |  CAGR: +{champion['cagr']:.1f}%  |  MDD: -{champion['mdd']:.2f}%",
                  color='#00d4aa', fontsize=9, fontweight='bold')
    ax2.set_ylabel("Equity ($)", color='#94a3b8')
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax2.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')

    # ── Plot 3: Win Rate vs MDD scatter ──
    ax3 = fig.add_subplot(gs[1, 1])
    sc = ax3.scatter([r["mdd"] for r in results],
                     [r["win_rate"] for r in results],
                     c=[r["n_strats"] for r in results],
                     cmap='plasma', s=30, alpha=0.7)
    ax3.scatter(champion["mdd"], champion["win_rate"], s=300, color='#00d4aa', marker='*', zorder=10,
                label=f"Champion: {champion['win_rate']:.0f}% WR / -{champion['mdd']:.1f}% MDD")
    plt.colorbar(sc, ax=ax3, label="# Strategies in Combo")
    ax3.set_xlabel("Max Drawdown (%)", color='#94a3b8')
    ax3.set_ylabel("Win Rate (%)", color='#94a3b8')
    ax3.set_title("Win Rate vs MDD — All Combinations", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax3.legend(fontsize=8, frameon=True, facecolor='#0f172a')
    ax3.grid(True, linestyle='--', alpha=0.10, color='#334155')

    # ── Plot 4: Top 6 equity curves overlay ──
    ax4 = fig.add_subplot(gs[2, :])
    curve_cols = ['#00d4aa','#f59e0b','#a855f7','#38bdf8','#fb7185','#22c55e']
    for i, r in enumerate(results[:6]):
        lw = 2.5 if i == 0 else 1.2
        ax4.plot(r["dates"], r["eq"], color=curve_cols[i], linewidth=lw,
                 label=f"#{i+1} {r['label']} (${r['final_cap']:,.0f} / {r['win_rate']:.0f}% WR)")
    ax4.set_yscale('log')
    ax4.set_title("TOP 6 COMBINATIONS — Equity Curves (2016-2026)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax4.set_ylabel("Equity ($)", color='#94a3b8')
    ax4.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax4.legend(fontsize=8.5, frameon=True, facecolor='#0f172a', ncol=2)
    ax4.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')

    # Legend for combo size
    from matplotlib.patches import Patch
    legend_el = [
        Patch(facecolor='#64748b', label='1 Strategy'),
        Patch(facecolor='#38bdf8', label='2 Strategies'),
        Patch(facecolor='#a855f7', label='3 Strategies'),
        Patch(facecolor='#f59e0b', label='4 Strategies'),
        Patch(facecolor='#ef4444', label='All 8 Strategies'),
    ]
    fig.legend(handles=legend_el, loc='lower center', ncol=5, fontsize=9,
               frameon=True, facecolor='#0f172a', edgecolor='#1e293b', bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        f"ANTIGRAVITY AI BRAIN — MEGA STRATEGY COMBINATION ENGINE\n"
        f"UTBot × Market Geometry × Rust HFT × DSS2 × CHESS × Dependable Fortress × Swarm × Simons  |  {len(combos)} Combos Tested",
        fontsize=12, fontweight='bold', color='#e2e8f0', y=1.01
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=240, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── REPORT ───────────────────────────────────────────────────────────────
    rows = ""
    for rank, r in enumerate(results[:15], 1):
        rows += f"| #{rank} | **{r['label']}** | {r['n_strats']} | **${r['final_cap']:,.2f}** | +{r['cagr']:.1f}% | **{r['win_rate']:.1f}%** | {r['trades']} | -{r['mdd']:.2f}% |\n"

    report = f"""# MEGA STRATEGY COMBINATION ENGINE — REPORT

**{len(combos)} Combinations tested** across 8 core strategies on 10-Year BTC-USD data (2016-2026).

## CHAMPION COMBINATION

**{champion['label']}**

| Metric | Value |
|:---|:---:|
| **Win Rate** | **{champion['win_rate']:.1f}%** |
| **10-Year Final Equity** | **${champion['final_cap']:,.2f} USD** |
| **CAGR** | **+{champion['cagr']:.1f}% / Year** |
| **Total Trades** | **{champion['trades']}** |
| **Maximum Drawdown** | **-{champion['mdd']:.2f}%** |

---

## TOP 15 COMBINATIONS (Pareto Ranked)

| Rank | Combination | # Strategies | Final Equity | CAGR | Win Rate | Trades | MDD |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
{rows}

---

![Mega Combo Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")

if __name__ == "__main__":
    main()
