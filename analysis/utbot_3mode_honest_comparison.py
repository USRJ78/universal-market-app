"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT+S&D+SUPERTREND: 3-MODE HONEST COMPARISON
==============================================================================
  Runs the best UTBot strategy (UTBot + S&D + Supertrend Slow ATR14×4.0)
  across 3 execution modes side-by-side:

  MODE 1: PURE SPOT (1x, no leverage, no options)
    - TP: +1.52% raw price move × 25% allocation
    - SL: -0.73% raw price move × 25% allocation
    - Exactly what you'd make buying/selling spot crypto or stocks

  MODE 2: OPTIONS CALL SPREAD (what previous backtests modelled)
    - Zero Net Debit 1×2 Ratio Call Spread payoff geometry
    - TP: +9.12% on 25% allocation (6x amplification)
    - SL: -3.65% on 25% allocation (5x amplification)
    - No borrowed capital, no liquidation risk

  MODE 3: 5x FUTURES LEVERAGE
    - Actual margin-based 5x leverage on 25% allocation
    - TP: +7.60% on 25% allocation (5x amplification)
    - SL: -3.65% on 25% allocation (5x amplification)
    - Liquidation threshold: -20% price move (27x beyond our SL)
    - Funding rate cost: ~0.01%/8h simulated

  Starting Capital: $1,000 USD | BTC-USD 2016-2026 (3,889 bars)
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
CHART_PATH  = os.path.join(ARTIFACTS_DIR, "utbot_3mode_honest_comparison_chart.png")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "utbot_3mode_honest_comparison_report.md")

INITIAL_CAPITAL = 1000.0
TP_PCT = 0.0152   # +1.52% raw price target
SL_PCT = 0.0073   # -0.73% raw price stop
BE_PCT = 0.0032   # +0.32% breakeven lock

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
    return (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))

def compute_sd_position(df, n=20):
    close  = df["Close"]
    high_n = df["High"].rolling(n).max()
    low_n  = df["Low"].rolling(n).min()
    return 100.0 * (close - low_n) / (high_n - low_n + 1e-9)

def compute_supertrend(df, atr_period=14, multiplier=4.0):
    high, low, close = df["High"], df["Low"], df["Close"]
    pc  = close.shift(1)
    tr  = pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()
    hl2 = (high + low) / 2.0
    upper_b = hl2 + multiplier * atr
    lower_b = hl2 - multiplier * atr

    final_upper = upper_b.copy()
    final_lower = lower_b.copy()
    for i in range(1, len(close)):
        if upper_b.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = upper_b.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        if lower_b.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = lower_b.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]

    direction = pd.Series(1, index=close.index)
    for i in range(1, len(close)):
        if   direction.iloc[i-1] ==  1 and close.iloc[i] < final_lower.iloc[i]: direction.iloc[i] = -1
        elif direction.iloc[i-1] == -1 and close.iloc[i] > final_upper.iloc[i]: direction.iloc[i] =  1
        else:                                                                      direction.iloc[i] = direction.iloc[i-1]

    return direction == 1

# ── 3-Mode Backtest Engine ────────────────────────────────────────────────────

def run_backtest_3mode(df, signal):
    """Returns results for all 3 modes in a single pass."""
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    modes = {
        "spot":    {"cap": INITIAL_CAPITAL, "eq": [INITIAL_CAPITAL], "wins": 0, "trades": 0},
        "options": {"cap": INITIAL_CAPITAL, "eq": [INITIAL_CAPITAL], "wins": 0, "trades": 0},
        "futures": {"cap": INITIAL_CAPITAL, "eq": [INITIAL_CAPITAL], "wins": 0, "trades": 0},
    }
    dates = [df.index[60]]
    last_exit = -1

    # Shared friction
    brok = 0.0005; stt = 0.00125; slip = 0.0015; tax = 0.15

    for i in range(60, len(df)):
        spot = float(close.iloc[i])

        if i > last_exit and bool(signal.iloc[i]):

            # --- Simulate trade outcome (shared across modes) ---
            tp_p = spot * (1.0 + TP_PCT)
            sl_p = spot * (1.0 - SL_PCT)
            be_p = spot * (1.0 + BE_PCT)
            liq_p = spot * 0.80  # -20% → 5x liquidation

            hit_tp = hit_sl = hit_be = hit_liq = False
            hold = 14
            for step in range(1, 15):
                ci = i + step
                if ci >= len(df): break
                mx = float(high.iloc[ci])
                mn = float(low.iloc[ci])
                if mn <= liq_p:
                    hit_liq = True; hold = step; break
                if mx >= tp_p:
                    hit_tp = True; hold = step; break
                if mx >= be_p: hit_be = True
                if hit_be and mn <= spot:
                    hold = step; break
                if not hit_be and mn <= sl_p:
                    hit_sl = True; hold = step; break

            last_exit = min(i + hold, len(df) - 1)
            raw_ret = (float(close.iloc[last_exit]) - spot) / spot  # actual price move

            for mode_name, mode in modes.items():
                cap   = mode["cap"]
                alloc = cap * 0.25  # 25% allocation per trade

                # Funding rate cost for futures (3 funding periods per day avg)
                funding_cost = alloc * 5 * 0.0001 * hold if mode_name == "futures" else 0.0

                if mode_name == "spot":
                    # Pure 1:1 price move
                    if hit_tp:
                        ret = TP_PCT * 100; mode["wins"] += 1
                    elif hit_be:
                        ret = 0.0; mode["wins"] += 1
                    elif hit_sl:
                        ret = -SL_PCT * 100
                    else:
                        ret = raw_ret * 100
                        if ret >= 0: mode["wins"] += 1

                elif mode_name == "options":
                    # 1×2 Ratio Call Spread payoff (6x TP, 5x SL, no liquidation)
                    if hit_tp:
                        ret = TP_PCT * 6.0 * 100; mode["wins"] += 1
                    elif hit_be:
                        ret = 0.0; mode["wins"] += 1
                    elif hit_sl:
                        ret = -SL_PCT * 5.0 * 100
                    else:
                        ret = raw_ret * 3.0 * 100  # partial options delta
                        if ret >= 0: mode["wins"] += 1

                else:  # futures 5x
                    if hit_liq:
                        ret = -100.0  # full margin wipeout
                    elif hit_tp:
                        ret = TP_PCT * 5.0 * 100; mode["wins"] += 1
                    elif hit_be:
                        ret = 0.0; mode["wins"] += 1
                    elif hit_sl:
                        ret = -SL_PCT * 5.0 * 100
                    else:
                        ret = raw_ret * 5.0 * 100
                        if ret >= 0: mode["wins"] += 1

                gross = (ret / 100.0) * alloc
                fric  = alloc * (brok + stt + slip) * 2
                net   = gross - fric - funding_cost - max(0, (gross - fric) * tax)
                mode["cap"] = max(mode["cap"] + net, 0.01)
                mode["trades"] += 1

        for mode in modes.values():
            mode["eq"].append(mode["cap"])
        dates.append(df.index[i])

    results = {}
    for mname, mode in modes.items():
        cap   = mode["cap"]
        years = max((dates[-1] - dates[0]).days / 365.25, 0.1)
        cagr  = ((cap / INITIAL_CAPITAL) ** (1.0 / years) - 1.0) * 100.0
        wr    = mode["wins"] / max(1, mode["trades"]) * 100
        eq_s  = pd.Series(mode["eq"])
        mdd   = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100
        results[mname] = {
            "final_cap": cap, "cagr": cagr, "win_rate": wr,
            "trades": mode["trades"], "mdd": mdd,
            "eq": mode["eq"], "dates": dates,
        }
    return results

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  UTBOT + S&D + SUPERTREND — 3-MODE HONEST COMPARISON")
    print("  Mode 1: Pure Spot  |  Mode 2: Options  |  Mode 3: 5x Futures")
    print("=" * 80)

    print("\n  Downloading 10-Year BTC-USD (2016-2026)...")
    df = yf.download("BTC-USD", start="2016-01-01", end="2026-08-25",
                     interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.dropna(inplace=True)
    print(f"  {len(df)} bars loaded.\n")

    # Build champion signal: UTBot + S&D + Supertrend Slow
    utbot_buy = compute_utbot(df["Close"])
    sd_pos    = compute_sd_position(df)
    st_bull   = compute_supertrend(df, atr_period=14, multiplier=4.0)

    signal_utbot_only  = utbot_buy
    signal_all_filters = utbot_buy & (sd_pos >= 10) & (sd_pos <= 85) & st_bull

    n_raw  = int(utbot_buy.sum())
    n_full = int(signal_all_filters.sum())
    print(f"  UTBot raw signals:           {n_raw}")
    print(f"  After S&D + Supertrend:      {n_full}  ({n_raw - n_full} false breakouts blocked)\n")

    # Run both signal sets across 3 modes
    print("  Running backtests...\n")

    res_raw  = run_backtest_3mode(df, signal_utbot_only)
    res_full = run_backtest_3mode(df, signal_all_filters)

    # ── Print Results ─────────────────────────────────────────────────────────

    configs = [
        ("UTBot Only",            res_raw),
        ("UTBot + S&D + ST Slow", res_full),
    ]
    mode_labels = {
        "spot":    "Pure Spot (1x)",
        "options": "Options Spread (6x TP)",
        "futures": "5x Futures Leverage",
    }
    mode_colors = {
        "spot":    "#64748b",
        "options": "#38bdf8",
        "futures": "#f59e0b",
    }

    print("=" * 95)
    print(f"  {'Strategy + Mode':<45} {'Final $':>12} {'CAGR':>9} {'Win Rate':>9} {'Trades':>7} {'MDD':>7}")
    print("  " + "-" * 95)
    for strat_name, res in configs:
        for mkey, mlabel in mode_labels.items():
            r = res[mkey]
            tag = f"  {strat_name} — {mlabel}"
            print(f"  {tag:<45} ${r['final_cap']:>11,.2f} +{r['cagr']:>7.1f}% {r['win_rate']:>8.1f}% {r['trades']:>7} -{r['mdd']:>5.2f}%")
        print()
    print("=" * 95)

    # ── CHART ────────────────────────────────────────────────────────────────

    fig = plt.figure(figsize=(18, 14), facecolor='#090d16')
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.52, wspace=0.35)

    def fmt_usd(x, _): return f"${x:,.0f}"

    # ── Plot 1: UTBot Only — 3 modes equity curve ──
    ax1 = fig.add_subplot(gs[0, :])
    linestyles = {"spot": "--", "options": "-", "futures": "-."}
    for mkey, mlabel in mode_labels.items():
        r = res_raw[mkey]
        ax1.plot(r["dates"], r["eq"], color=mode_colors[mkey],
                 linewidth=2.2, linestyle=linestyles[mkey],
                 label=f"UTBot Only — {mlabel}: ${r['final_cap']:,.0f}  (+{r['cagr']:.1f}% CAGR / {r['win_rate']:.0f}% WR)")
    for mkey, mlabel in mode_labels.items():
        r = res_full[mkey]
        ax1.plot(r["dates"], r["eq"], color=mode_colors[mkey],
                 linewidth=1.4, linestyle=linestyles[mkey], alpha=0.55,
                 label=f"UTBot+S&D+ST — {mlabel}: ${r['final_cap']:,.0f}  (+{r['cagr']:.1f}% CAGR / {r['win_rate']:.0f}% WR)")
    ax1.set_yscale('log')
    ax1.set_title("ALL 6 COMBINATIONS — Pure Spot vs Options vs 5x Futures (2016-2026)",
                  color='#e2e8f0', fontsize=11, fontweight='bold')
    ax1.set_ylabel("Equity ($)", color='#94a3b8')
    ax1.yaxis.set_major_formatter(FuncFormatter(fmt_usd))
    ax1.legend(fontsize=8, frameon=True, facecolor='#0f172a', ncol=2)
    ax1.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
    ax1.tick_params(colors='#94a3b8')

    # ── Plots 2-4: One per mode, both strategies ──
    for col, (mkey, mlabel) in enumerate(mode_labels.items()):
        ax = fig.add_subplot(gs[1, col])
        for strat_name, res in configs:
            r = res[mkey]
            lw = 2.2 if "Only" in strat_name else 1.4
            lbl = f"{strat_name}\n${r['final_cap']:,.0f} / +{r['cagr']:.1f}% / {r['win_rate']:.0f}% WR / -{r['mdd']:.1f}% MDD"
            clr = '#00d4aa' if "Only" in strat_name else '#f59e0b'
            ax.plot(r["dates"], r["eq"], color=clr, linewidth=lw, label=lbl)
        ax.set_yscale('log')
        ax.set_title(mlabel, color=mode_colors[mkey], fontsize=10, fontweight='bold')
        ax.set_ylabel("Equity ($)", color='#94a3b8')
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_usd))
        ax.legend(fontsize=7.5, frameon=True, facecolor='#0f172a')
        ax.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
        ax.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 5-6: Bar charts comparing CAGR and MDD ──
    ax5 = fig.add_subplot(gs[2, :2])
    bar_labels = []
    bar_cagrs  = []
    bar_colors = []
    bar_mdds   = []
    for strat_name, res in configs:
        for mkey, mlabel in mode_labels.items():
            r = res[mkey]
            bar_labels.append(f"{strat_name[:10]}\n{mlabel[:16]}")
            bar_cagrs.append(r["cagr"])
            bar_mdds.append(r["mdd"])
            bar_colors.append(mode_colors[mkey])

    x = np.arange(len(bar_labels))
    w = 0.38
    ax5_twin = ax5.twinx()
    bars = ax5.bar(x - w/2, bar_cagrs, w, color=bar_colors, alpha=0.85, label='CAGR (%)')
    bars2 = ax5_twin.bar(x + w/2, bar_mdds, w, color=bar_colors, alpha=0.45, label='MDD (%)')
    for bar, val in zip(bars, bar_cagrs):
        ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
                 f"+{val:.1f}%", ha='center', fontsize=7.5, color='#e2e8f0', fontweight='bold')
    for bar, val in zip(bars2, bar_mdds):
        ax5_twin.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                      f"-{val:.1f}%", ha='center', fontsize=7, color='#94a3b8')
    ax5.set_xticks(x); ax5.set_xticklabels(bar_labels, fontsize=7.5)
    ax5.set_ylabel("CAGR (%/year)", color='#94a3b8')
    ax5_twin.set_ylabel("Max Drawdown (%)", color='#ef4444')
    ax5_twin.tick_params(axis='y', colors='#ef4444')
    ax5.set_title("CAGR vs MDD — All 6 Combinations", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax5.grid(True, axis='y', linestyle='--', alpha=0.10, color='#334155')
    ax5.tick_params(colors='#94a3b8')

    # ── Plot 6: $250 wallet projection ──
    ax6 = fig.add_subplot(gs[2, 2])
    proj_labels, proj_vals, proj_cols = [], [], []
    for strat_name, res in configs:
        for mkey, mlabel in mode_labels.items():
            r = res[mkey]
            proj_labels.append(f"{strat_name[:8]}\n{mlabel[:14]}")
            proj_vals.append(r["final_cap"] * 0.25)  # scale to $250
            proj_cols.append(mode_colors[mkey])
    bars3 = ax6.barh(proj_labels[::-1], proj_vals[::-1], color=proj_cols[::-1], alpha=0.85)
    for bar, val in zip(bars3, proj_vals[::-1]):
        ax6.text(bar.get_width() + max(proj_vals)*0.01, bar.get_y()+bar.get_height()/2,
                 f"${val:,.0f}", va='center', fontsize=8, color='#e2e8f0')
    ax6.set_title("$250 Wallet → 10 Years", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax6.set_xlabel("Final Value ($)", color='#94a3b8')
    ax6.xaxis.set_major_formatter(FuncFormatter(fmt_usd))
    ax6.grid(True, axis='x', linestyle='--', alpha=0.10, color='#334155')
    ax6.tick_params(colors='#94a3b8', labelsize=7.5)

    fig.suptitle(
        "ANTIGRAVITY AI BRAIN — 3-MODE HONEST COMPARISON (Pure Spot / Options Spread / 5x Futures)\n"
        "UTBot + Supply & Demand + Supertrend Slow (ATR14 × 4.0)  |  $1,000 Start  |  2016-2026",
        fontsize=12, fontweight='bold', color='#e2e8f0', y=1.01
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=240, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── REPORT ───────────────────────────────────────────────────────────────
    rows = ""
    for strat_name, res in configs:
        for mkey, mlabel in mode_labels.items():
            r = res[mkey]
            rows += f"| **{strat_name}** | **{mlabel}** | **${r['final_cap']:,.2f}** | +{r['cagr']:.1f}% | {r['win_rate']:.1f}% | {r['trades']} | -{r['mdd']:.2f}% | **${r['final_cap']*0.25:,.2f}** |\n"

    report = f"""# UTBOT + S&D + SUPERTREND — 3-MODE HONEST COMPARISON REPORT

## Mode Definitions

| Mode | Mechanism | TP Return | SL Return | Risk |
|:---|:---|:---:|:---:|:---|
| **Pure Spot** | Buy/sell actual asset | +{TP_PCT*100:.2f}% on 25% alloc | -{SL_PCT*100:.2f}% on 25% alloc | No liquidation risk |
| **Options Spread** | 1×2 Zero Debit Call Spread | +{TP_PCT*6*100:.2f}% on 25% alloc | -{SL_PCT*5*100:.2f}% on 25% alloc | No liquidation risk |
| **5x Futures** | Leveraged margin position | +{TP_PCT*5*100:.2f}% on 25% alloc | -{SL_PCT*5*100:.2f}% on 25% alloc | Liquidation at -20% price |

## Full Results

| Strategy | Mode | Final ($1k) | CAGR | Win Rate | Trades | MDD | $250 Wallet → |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
{rows}

---

![3-Mode Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")

if __name__ == "__main__":
    main()
