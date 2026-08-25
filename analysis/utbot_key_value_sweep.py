"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT KEY VALUE SWEEP + SUPERTREND(10,3) FILTER
==============================================================================
  Sweeps UTBot Key Value from 1 to 10 (with ATR Period = 1, matching TV)
  WITH Supertrend(10,3) alignment filter applied throughout.

  Finds the optimal Key Value that maximises:
    ✅ Win Rate
    ✅ CAGR
    ✅ Pareto Score = Win Rate + CAGR - 2×MDD

  Assets:
    - TATMOTORS.NS  (Tata Motors — NSE Daily, proxy for TATMPV 4H)
    - BTC-USD       (Bitcoin — reference asset)
    - ^NSEI         (NIFTY 50 — Indian market reference)

  ATR Period : fixed at 1  (as shown on TradingView)
  Supertrend : Period=10, Multiplier=3.0  (as shown on TradingView)
  Key Values : 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 10
==============================================================================
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter, MultipleLocator
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".gemini", "antigravity", "brain",
    "a0eeb781-d7e4-484e-898c-51f143744494"
)
CHART_PATH  = os.path.join(ARTIFACTS_DIR, "utbot_key_sweep_chart.png")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "utbot_key_sweep_report.md")

INITIAL_CAPITAL = 1000.0
KEY_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 10.0]

ASSETS = [
    {"ticker": "TATMOTORS.NS", "label": "Tata Motors",  "start": "2016-01-01", "cur": "Rs."},
    {"ticker": "BTC-USD",       "label": "Bitcoin",      "start": "2016-01-01", "cur": "$"},
    {"ticker": "^NSEI",         "label": "NIFTY 50",     "start": "2016-01-01", "cur": "Rs."},
]

# ── Indicators ────────────────────────────────────────────────────────────────

def compute_utbot(close, key, atr_period=1):
    tr    = close.diff().abs()
    atr   = tr.rolling(max(1, atr_period)).mean()
    nloss = key * atr

    xatr = [0.0] * len(close)
    for t in range(1, len(close)):
        sc = float(close.iloc[t])
        sp = float(close.iloc[t - 1])
        xa = xatr[t - 1]
        lc = float(nloss.iloc[t]) if not np.isnan(nloss.iloc[t]) else 0.0
        if   sc > xa and sp > xa: xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa: xatr[t] = min(xa, sc + lc)
        else:                     xatr[t] = (sc - lc) if sc > xa else (sc + lc)

    xatr_s = pd.Series(xatr, index=close.index)
    buy  = (close > xatr_s) & (close.shift(1) <= xatr_s.shift(1))
    sell = (close < xatr_s) & (close.shift(1) >= xatr_s.shift(1))
    return buy, sell, xatr_s


def compute_supertrend(df, period=10, multiplier=3.0):
    high, low, close = df["High"], df["Low"], df["Close"]
    pc  = close.shift(1)
    tr  = pd.concat([(high-low), (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2.0

    upper_b = hl2 + multiplier * atr
    lower_b = hl2 - multiplier * atr
    final_upper = upper_b.copy().astype(float)
    final_lower = lower_b.copy().astype(float)

    for i in range(1, len(close)):
        fu_p = final_upper.iloc[i-1]
        fl_p = final_lower.iloc[i-1]
        c_p  = float(close.iloc[i-1])
        final_upper.iloc[i] = upper_b.iloc[i] if upper_b.iloc[i] < fu_p or c_p > fu_p else fu_p
        final_lower.iloc[i] = lower_b.iloc[i] if lower_b.iloc[i] > fl_p or c_p < fl_p else fl_p

    direction = pd.Series(1, index=close.index, dtype=int)
    for i in range(1, len(close)):
        d = direction.iloc[i-1]
        c = float(close.iloc[i])
        if   d ==  1 and c < final_lower.iloc[i]: direction.iloc[i] = -1
        elif d == -1 and c > final_upper.iloc[i]: direction.iloc[i] =  1
        else:                                      direction.iloc[i] = d

    st_line = pd.Series(
        np.where(direction == 1, final_lower, final_upper),
        index=close.index
    )
    return direction == 1, st_line


# ── Backtest ──────────────────────────────────────────────────────────────────

def backtest(df, buy_sig, sell_sig):
    close = df["Close"]
    high  = df["High"]

    cap   = INITIAL_CAPITAL
    eq    = [cap]
    dates = [df.index[20]]
    trades = wins = 0
    last_exit = -1

    brok = 0.0003; stt = 0.001; slip = 0.001; tax = 0.15

    for i in range(20, len(df)):
        if i > last_exit and bool(buy_sig.iloc[i]):
            entry = float(close.iloc[i])
            alloc = cap * 0.25
            trades += 1

            exit_p = entry
            for step in range(1, 21):
                ci = i + step
                if ci >= len(df):
                    exit_p = float(close.iloc[-1]); last_exit = len(df)-1; break
                if bool(sell_sig.iloc[ci]):
                    exit_p = float(close.iloc[ci]); last_exit = ci; break
            else:
                last_exit = min(i+20, len(df)-1)
                exit_p = float(close.iloc[last_exit])

            raw = (exit_p - entry) / entry
            gross = raw * alloc
            fric  = alloc * (brok + stt + slip) * 2
            net   = gross - fric - max(0, (gross-fric)*tax)
            cap   = max(cap + net, 0.01)
            if raw >= 0: wins += 1

        eq.append(cap)
        dates.append(df.index[i])

    if trades < 3:
        return None

    years = max((dates[-1]-dates[0]).days/365.25, 0.1)
    cagr  = ((cap/INITIAL_CAPITAL)**(1/years)-1)*100
    wr    = wins/max(1,trades)*100
    eq_s  = pd.Series(eq)
    mdd   = abs(((eq_s-eq_s.cummax())/eq_s.cummax()).min())*100
    pareto = wr + cagr*0.5 - mdd*2.0

    return {
        "final": cap, "cagr": cagr, "wr": wr,
        "trades": trades, "mdd": mdd, "pareto": pareto,
        "eq": eq, "dates": dates,
    }


# ── MAIN ──────────────────────────────────────────════════════════════════════

def main():
    print("=" * 80)
    print("  UTBOT KEY VALUE SWEEP  (ATR=1, Supertrend 10x3 filter)")
    print(f"  Testing Key values: {KEY_VALUES}")
    print("=" * 80)

    # ── Fetch data ────────────────────────────────────────────────────────────
    all_dfs = {}
    for a in ASSETS:
        print(f"\n  Downloading {a['label']} ({a['ticker']})...")
        try:
            df = yf.download(a["ticker"], start=a["start"], end="2026-08-25",
                             interval="1d", progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.dropna(inplace=True)
            if len(df) >= 100:
                all_dfs[a["ticker"]] = (df, a["label"], a["cur"])
                print(f"    {len(df)} bars")
            else:
                print(f"    Skipped (only {len(df)} bars)")
        except Exception as e:
            print(f"    Error: {e}")

    # ── Sweep ─────────────────────────────────────────────────────────────────
    sweep_results = {}   # ticker -> list of results per key
    for ticker, (df, label, cur) in all_dfs.items():
        print(f"\n  {'='*70}")
        print(f"  SWEEPING: {label}")
        print(f"  {'Key':>6} | {'Signals':>8} | {'Valid':>6} | {'Blocked':>8} | "
              f"{'Final':>10} | {'CAGR':>7} | {'WR':>6} | {'MDD':>6} | {'Pareto':>7}")
        print(f"  {'-'*80}")

        st_bull, st_line = compute_supertrend(df)
        asset_rows = []

        for key in KEY_VALUES:
            buy_raw, sell_raw, xatr_s = compute_utbot(df["Close"], key=key, atr_period=1)

            # Apply Supertrend alignment
            buy_aln  = buy_raw  & st_bull
            sell_aln = sell_raw & (~st_bull)

            n_raw   = int(buy_raw.sum())
            n_valid = int(buy_aln.sum())
            n_blk   = n_raw - n_valid

            r = backtest(df, buy_aln, sell_aln)
            if r:
                r["key"]   = key
                r["n_sig"] = n_raw
                r["n_val"] = n_valid
                r["n_blk"] = n_blk
                asset_rows.append(r)

                star = " <-- BEST" if r["pareto"] == max(
                    [x["pareto"] for x in asset_rows]) else ""
                print(f"  {key:>6.1f} | {n_raw:>8} | {n_valid:>6} | {n_blk:>8} | "
                      f"${r['final']:>9,.2f} | +{r['cagr']:>5.1f}% | "
                      f"{r['wr']:>5.1f}% | -{r['mdd']:>4.2f}% | "
                      f"{r['pareto']:>7.1f}{star}")

        sweep_results[ticker] = (asset_rows, label, cur,
                                 st_bull, st_line, df)

    # ── Find overall champion key per asset ───────────────────────────────────
    print("\n" + "=" * 80)
    print("  OPTIMAL KEY VALUE PER ASSET (by Pareto Score)")
    print("=" * 80)
    champions = {}
    for ticker, (rows, label, cur, _, _, _) in sweep_results.items():
        if not rows: continue
        best = max(rows, key=lambda r: r["pareto"])
        champions[ticker] = best
        print(f"  {label:<18} Key={best['key']:>4.1f}  "
              f"Final=${best['final']:>9,.2f}  CAGR=+{best['cagr']:.1f}%  "
              f"WR={best['wr']:.1f}%  MDD=-{best['mdd']:.2f}%  "
              f"Pareto={best['pareto']:.1f}  "
              f"Valid signals={best['n_val']}")

    # ── CHART ─────────────────────────────────────────────────────────────────
    n_assets = len(sweep_results)
    fig = plt.figure(figsize=(18, 5 + 5*n_assets), facecolor='#090d16')
    total_rows = 2 + n_assets
    gs = gridspec.GridSpec(total_rows, 3, figure=fig,
                           hspace=0.55, wspace=0.35)

    PARETO_COLOR = "#f59e0b"
    CAGR_COLOR   = "#38bdf8"
    WR_COLOR     = "#00d4aa"
    MDD_COLOR    = "#ef4444"
    SIGNAL_COLOR = "#a855f7"

    # ── Row 0: Key sweep metric lines (averaged across assets) ──
    # Collect per-key averages
    key_avg = {k: {"cagr": [], "wr": [], "mdd": [], "pareto": [], "signals": []}
               for k in KEY_VALUES}
    for ticker, (rows, *_) in sweep_results.items():
        for r in rows:
            k = r["key"]
            key_avg[k]["cagr"].append(r["cagr"])
            key_avg[k]["wr"].append(r["wr"])
            key_avg[k]["mdd"].append(r["mdd"])
            key_avg[k]["pareto"].append(r["pareto"])
            key_avg[k]["signals"].append(r["n_val"])

    keys_used  = [k for k in KEY_VALUES if key_avg[k]["pareto"]]
    avg_pareto = [np.mean(key_avg[k]["pareto"])  for k in keys_used]
    avg_cagr   = [np.mean(key_avg[k]["cagr"])    for k in keys_used]
    avg_wr     = [np.mean(key_avg[k]["wr"])      for k in keys_used]
    avg_mdd    = [np.mean(key_avg[k]["mdd"])     for k in keys_used]
    avg_sigs   = [np.mean(key_avg[k]["signals"]) for k in keys_used]

    best_key_idx = int(np.argmax(avg_pareto))
    best_key_val = keys_used[best_key_idx]

    # Pareto score across keys
    ax_p = fig.add_subplot(gs[0, :2])
    ax_p.plot(keys_used, avg_pareto, color=PARETO_COLOR, linewidth=2.5,
              marker='o', markersize=7, label='Pareto Score (WR + 0.5×CAGR - 2×MDD)')
    ax_p.plot(keys_used, avg_wr,     color=WR_COLOR,     linewidth=1.5,
              marker='s', markersize=5, linestyle='--', label='Win Rate (%)')
    ax_p.plot(keys_used, avg_cagr,   color=CAGR_COLOR,   linewidth=1.5,
              marker='^', markersize=5, linestyle='--', label='CAGR (%/yr)')
    ax_p.axvline(x=best_key_val, color='#ffffff', linewidth=1.5,
                 linestyle=':', alpha=0.6, label=f'Optimal Key={best_key_val}')
    ax_p.fill_between(keys_used, avg_pareto,
                      alpha=0.08, color=PARETO_COLOR)
    ax_p.annotate(f'Optimal\nKey={best_key_val}',
                  xy=(best_key_val, avg_pareto[best_key_idx]),
                  xytext=(best_key_val+0.3, avg_pareto[best_key_idx]+1),
                  fontsize=9, color='#ffffff', fontweight='bold',
                  arrowprops=dict(arrowstyle='->', color='#ffffff', lw=1.2))
    ax_p.set_title("Pareto Score, Win Rate & CAGR vs UTBot Key Value (Averaged Across All Assets)",
                   color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_p.set_xlabel("UTBot Key Value", color='#94a3b8')
    ax_p.set_ylabel("Score / %", color='#94a3b8')
    ax_p.legend(fontsize=9, frameon=True, facecolor='#0f172a')
    ax_p.grid(True, linestyle='--', alpha=0.12, color='#334155')
    ax_p.tick_params(colors='#94a3b8')
    ax_p.xaxis.set_major_locator(MultipleLocator(0.5))

    # Signal count vs Key
    ax_s = fig.add_subplot(gs[0, 2])
    ax_s_mdd = ax_s.twinx()
    ax_s.bar(keys_used, avg_sigs, width=0.35, color=SIGNAL_COLOR,
             alpha=0.75, label='Avg Valid Signals')
    ax_s_mdd.plot(keys_used, avg_mdd, color=MDD_COLOR, linewidth=2.0,
                  marker='o', markersize=5, label='Avg MDD (%)')
    ax_s.set_title("Signal Count vs MDD\n(More signals = noisier)", color='#e2e8f0',
                   fontsize=10, fontweight='bold')
    ax_s.set_xlabel("Key Value", color='#94a3b8')
    ax_s.set_ylabel("Avg Valid Signals", color=SIGNAL_COLOR)
    ax_s_mdd.set_ylabel("Avg MDD (%)", color=MDD_COLOR)
    ax_s.tick_params(axis='y', colors=SIGNAL_COLOR, labelsize=8)
    ax_s_mdd.tick_params(axis='y', colors=MDD_COLOR, labelsize=8)
    ax_s.tick_params(axis='x', colors='#94a3b8', labelsize=8)
    ax_s.grid(True, linestyle='--', alpha=0.12, color='#334155')
    lines1, labels1 = ax_s.get_legend_handles_labels()
    lines2, labels2 = ax_s_mdd.get_legend_handles_labels()
    ax_s.legend(lines1+lines2, labels1+labels2, fontsize=8,
                frameon=True, facecolor='#0f172a')

    # ── Per-asset rows ────────────────────────────────────────────────────────
    palette = ["#f59e0b", "#38bdf8", "#00d4aa", "#a855f7",
               "#fb7185", "#22c55e", "#e879f9"]

    for ai, (ticker, (rows, label, cur, st_bull, st_line, df)) \
            in enumerate(sweep_results.items()):

        if not rows: continue
        row = ai + 1
        best = max(rows, key=lambda r: r["pareto"])

        # ── Sub-plot A: CAGR/WR/Pareto vs Key for this asset ──
        ax_a = fig.add_subplot(gs[row, 0])
        ks  = [r["key"]    for r in rows]
        par = [r["pareto"] for r in rows]
        wr  = [r["wr"]     for r in rows]
        ca  = [r["cagr"]   for r in rows]

        ax_a.plot(ks, par, color=PARETO_COLOR, linewidth=2.2,
                  marker='o', markersize=6, label='Pareto')
        ax_a.plot(ks, wr,  color=WR_COLOR,     linewidth=1.4,
                  marker='s', markersize=4, linestyle='--', label='Win Rate')
        ax_a.plot(ks, ca,  color=CAGR_COLOR,   linewidth=1.4,
                  marker='^', markersize=4, linestyle='--', label='CAGR')
        ax_a.axvline(x=best["key"], color='#ffffff', linewidth=1.2,
                     linestyle=':', alpha=0.6)
        ax_a.set_title(f"{label} — Metrics vs Key Value",
                       color='#e2e8f0', fontsize=10, fontweight='bold')
        ax_a.set_xlabel("Key Value", color='#94a3b8')
        ax_a.set_ylabel("Score / %", color='#94a3b8')
        ax_a.legend(fontsize=8, frameon=True, facecolor='#0f172a')
        ax_a.grid(True, linestyle='--', alpha=0.10, color='#334155')
        ax_a.tick_params(colors='#94a3b8', labelsize=8)

        # ── Sub-plot B: Equity curves for 3 representative keys ──
        ax_b = fig.add_subplot(gs[row, 1])
        show_keys = sorted(set([rows[0]["key"], best["key"],
                                rows[-1]["key"]]))
        for ri, r in enumerate(rows):
            if r["key"] not in show_keys: continue
            is_best = r["key"] == best["key"]
            lw  = 2.2 if is_best else 1.0
            clr = palette[ri % len(palette)]
            ax_b.plot(r["dates"], r["eq"], color=clr, linewidth=lw,
                      label=f"Key={r['key']} ${r['final']:,.0f} "
                            f"+{r['cagr']:.0f}% WR{r['wr']:.0f}%"
                            + (" BEST" if is_best else ""))
        ax_b.set_yscale('log')
        ax_b.set_title(f"{label} — Equity Curves (selected keys)",
                       color='#e2e8f0', fontsize=10, fontweight='bold')
        ax_b.set_ylabel(f"Equity ({cur})", color='#94a3b8')
        ax_b.yaxis.set_major_formatter(
            FuncFormatter(lambda x, _: f"{cur}{x:,.0f}"))
        ax_b.legend(fontsize=7.5, frameon=True, facecolor='#0f172a')
        ax_b.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
        ax_b.tick_params(colors='#94a3b8', labelsize=8)

        # ── Sub-plot C: Recent price with optimal UTBot + Supertrend ──
        ax_c = fig.add_subplot(gs[row, 2])
        n_plot = min(300, len(df))
        df_p   = df.iloc[-n_plot:]
        cl_p   = df_p["Close"]
        idx_p  = df_p.index
        st_b_p = st_bull.iloc[-n_plot:]
        st_l_p = st_line.iloc[-n_plot:]

        buy_opt, sell_opt, _ = compute_utbot(df["Close"], key=best["key"])
        buy_opt  = buy_opt  & st_bull
        sell_opt = sell_opt & (~st_bull)
        b_p = buy_opt.iloc[-n_plot:]
        s_p = sell_opt.iloc[-n_plot:]

        # Supertrend shading
        for i in range(1, len(idx_p)):
            c = '#1a4a2e' if st_b_p.iloc[i] else '#4a1a1a'
            ax_c.axvspan(idx_p[i-1], idx_p[i], alpha=0.30, color=c, linewidth=0)

        # Supertrend line
        ax_c.plot(idx_p, st_l_p.where(st_b_p, np.nan),  color='#00c080', lw=1.2)
        ax_c.plot(idx_p, st_l_p.where(~st_b_p, np.nan), color='#ff4060', lw=1.2)
        ax_c.plot(idx_p, cl_p, color='#60aaff', lw=1.4, label='Price')
        ax_c.scatter(idx_p[b_p], cl_p[b_p], marker='^', color='#00ff80',
                     s=60, zorder=10, label=f'BUY (Key={best["key"]})')
        ax_c.scatter(idx_p[s_p], cl_p[s_p], marker='v', color='#ff4060',
                     s=60, zorder=10, label='SELL')
        ax_c.set_title(f"{label} — Optimal Key={best['key']} + Supertrend(10,3)",
                       color='#f59e0b', fontsize=10, fontweight='bold')
        ax_c.set_ylabel(f"Price ({cur})", color='#94a3b8')
        ax_c.yaxis.set_major_formatter(
            FuncFormatter(lambda x, _: f"{cur}{x:,.0f}"))
        ax_c.legend(fontsize=7.5, frameon=True, facecolor='#0f172a')
        ax_c.grid(True, linestyle='--', alpha=0.10, color='#334155')
        ax_c.tick_params(colors='#94a3b8', labelsize=8)

    fig.suptitle(
        "ANTIGRAVITY AI BRAIN — UTBOT KEY VALUE SWEEP\n"
        f"ATR Period=1  |  Supertrend(10, 3.0) Alignment Filter  |  "
        f"Optimal Key = {best_key_val}",
        fontsize=12, fontweight='bold', color='#e2e8f0', y=1.005
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=220, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── Report ────────────────────────────────────────────────────────────────
    champ_rows = ""
    for ticker, (rows, label, cur, _, _, _) in sweep_results.items():
        if not rows: continue
        best = max(rows, key=lambda r: r["pareto"])
        champ_rows += (f"| **{label}** | **{best['key']}** | "
                       f"**{cur}{best['final']:,.2f}** | "
                       f"+{best['cagr']:.1f}% | "
                       f"**{best['wr']:.1f}%** | "
                       f"{best['trades']} | "
                       f"-{best['mdd']:.2f}% | "
                       f"{best['pareto']:.1f} |\n")

    sweep_table = ""
    for ticker, (rows, label, *_) in sweep_results.items():
        if not rows: continue
        sweep_table += f"\n### {label}\n\n"
        sweep_table += "| Key | Valid Sigs | Final | CAGR | Win Rate | MDD | Pareto |\n"
        sweep_table += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        for r in rows:
            mk = "**" if r["key"] == max(rows, key=lambda x: x["pareto"])["key"] else ""
            sweep_table += (f"| {mk}{r['key']}{mk} | {r['n_val']} | "
                            f"${r['final']:,.0f} | +{r['cagr']:.1f}% | "
                            f"{r['wr']:.1f}% | -{r['mdd']:.2f}% | "
                            f"{r['pareto']:.1f} |\n")

    report = f"""# UTBOT KEY VALUE SWEEP — REPORT

## Setup
- **ATR Period**: 1 (matching TradingView)
- **Supertrend**: Period=10, Multiplier=3.0 (matching TradingView)
- **Key Values Tested**: {KEY_VALUES}
- **Alignment Rule**: BUY only when ST Green | SELL only when ST Red

## Overall Optimal Key Value: **{best_key_val}**

## Champion Results Per Asset

| Asset | Optimal Key | Final ($1k) | CAGR | Win Rate | Trades | MDD | Pareto |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
{champ_rows}

## Full Sweep Tables
{sweep_table}

---

## How to Read the Pareto Score
```
Pareto Score = Win Rate + (CAGR × 0.5) - (MDD × 2.0)

Higher Key  → fewer signals, higher quality, lower MDD
Lower Key   → more signals, noisier, higher MDD
Sweet spot  → Key={best_key_val} balances all three
```

![Sweep Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
