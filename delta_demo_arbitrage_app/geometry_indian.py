"""
MARKET GEOMETRY ENGINE — Indian Smallcap Multibaggers (2016-2026)
==================================================================
Apply Fibonacci + Gann geometry to a universe of known Indian 
multibagger stocks that had 10x-100x runs.

Geometry layers:
  1. Fibonacci Retracement (buy at 61.8% pullback of major swing)
  2. Fibonacci Extension (exit at 161.8%, 261.8% targets)
  3. Gann Fan Angles (45-degree 1x1 trend line from swing lows)
  4. Swing Pivot Detection (ZigZag-style high/low identification)
  5. Breakout from Geometric Consolidation (price > swing high)
  6. Circle of 360 (seasonal turning points at 90/180/270/360 days)

Universe: Top Indian multibaggers 2016-2026
  Tata Elxsi     (TATAELXSI.NS) - 25x
  Tanla Platforms (TANLA.NS)    - 67x
  Solar Industries (SOLARINDS.NS) - 40x
  Deepak Nitrite  (DEEPAKNTR.NS)  - 25x
  Dixon Tech      (DIXON.NS)      - 12x
  CDSL            (CDSL.NS)       - 9x
  Persistent Sys  (PERSISTENT.NS) - 10x
  Polycab         (POLYCAB.NS)    - 9x
  Angel One       (ANGELONE.NS)   - 20x
  Laurus Labs     (LAURUSLABS.NS) - 5x
  Navin Fluorine  (NAVINFLUOR.NS) - 8x
  Alkyl Amines    (ALKYLAMINE.NS) - 15x
  Fine Organic    (FINEORG.NS)    - 8x
  Aarti Industries (AARTIIND.NS)  - 6x
  Astral Poly     (ASTRAL.NS)     - 8x
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.signal import argrelextrema

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPITAL  = 100_000.0
FRICTION = 0.002
START    = "2016-07-01"
END      = "2026-07-16"

# Golden ratio constants
PHI   = 1.6180339887   # 161.8% extension
RPHI  = 0.6180339887   # 61.8% retracement
RPHI2 = 0.3820339887   # 38.2% retracement

UNIVERSE = {
    "TATAELXSI":   "TATAELXSI.NS",
    "TANLA":       "TANLA.NS",
    "SOLARINDS":   "SOLARINDS.NS",
    "DEEPAKNTR":   "DEEPAKNTR.NS",
    "DIXON":       "DIXON.NS",
    "CDSL":        "CDSL.NS",
    "PERSISTENT":  "PERSISTENT.NS",
    "POLYCAB":     "POLYCAB.NS",
    "ANGELONE":    "ANGELONE.NS",
    "LAURUSLABS":  "LAURUSLABS.NS",
    "NAVINFLUOR":  "NAVINFLUOR.NS",
    "ALKYLAMINE":  "ALKYLAMINE.NS",
    "FINEORG":     "FINEORG.NS",
    "AARTIIND":    "AARTIIND.NS",
    "ASTRAL":      "ASTRAL.NS",
}

print("="*70)
print("  MARKET GEOMETRY ENGINE — Indian Multibagger Universe")
print(f"  Capital: INR {CAPITAL:,.0f}  |  Period: 2016-2026")
print("="*70)

# ─── 1. DOWNLOAD ALL STOCKS ──────────────────────────────────────────────────
print("\n[1/4] Downloading Indian multibagger universe...")
raw = {}
for name, sym in UNIVERSE.items():
    try:
        df = yf.download(sym, start=START, end=END, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        s = df['Close'].dropna()
        if len(s) > 100:
            raw[name] = s
            gain = s.iloc[-1]/s.iloc[0]
            print(f"   {name:12s}: {len(s):4d} rows  Rs{s.iloc[0]:>8,.0f} -> Rs{s.iloc[-1]:>8,.0f}  ({gain:.1f}x)")
        else:
            print(f"   {name:12s}: insufficient data")
    except Exception as e:
        print(f"   {name:12s}: ERROR")

print(f"\n   {len(raw)} stocks loaded successfully")

# ─── 2. GEOMETRY ENGINE ──────────────────────────────────────────────────────
print("\n[2/4] Computing market geometry signals...")

def find_swings(s, order=10):
    """Find major swing highs and lows using local extrema."""
    vals = s.values
    idx  = s.index
    highs = argrelextrema(vals, np.greater, order=order)[0]
    lows  = argrelextrema(vals, np.less,    order=order)[0]
    return idx[highs], vals[highs], idx[lows], vals[lows]

def gann_angle(price_low, date_low, current_date, current_price):
    """
    Gann 1x1 angle: price should equal time from the swing low.
    Uses sqrt of price as natural unit (Gann Square of Nine concept).
    Returns: 1 if price above Gann 1x1, -1 if below.
    """
    days = (current_date - date_low).days
    gann_price = price_low * (1 + days/365.0)  # 1x1 = 100%/year from low
    return 1 if current_price > gann_price else -1

def fib_geometry_signals(s, name):
    """
    Main geometry engine per stock.
    Returns a DataFrame of signals: BUY/SELL with geometry rationale.
    """
    if len(s) < 50:
        return pd.DataFrame()

    weekly = s.resample("W").last().ffill()
    signals = pd.DataFrame(index=weekly.index)
    signals['price']   = weekly
    signals['sma20']   = weekly.rolling(20).mean()
    signals['sma50']   = weekly.rolling(50).mean()

    # ── Swing detection ─────────────────────────────────────────────────
    hi_idx, hi_vals, lo_idx, lo_vals = find_swings(weekly, order=8)

    # ── Fibonacci Retracement Signal ─────────────────────────────────────
    # For each week, check if price is near the 61.8% retracement of
    # the most recent major swing (low → high)
    fib_buy_signal  = pd.Series(0, index=weekly.index)
    fib_sell_signal = pd.Series(0, index=weekly.index)
    gann_signal     = pd.Series(0, index=weekly.index)
    momentum_signal = pd.Series(0, index=weekly.index)

    for t in range(len(weekly)):
        dt = weekly.index[t]
        p  = weekly.iloc[t]
        if np.isnan(p): continue

        # Find most recent swing low before this date
        past_lows  = [(lo_idx[i], lo_vals[i]) for i in range(len(lo_idx)) if lo_idx[i] < dt]
        past_highs = [(hi_idx[i], hi_vals[i]) for i in range(len(hi_idx)) if hi_idx[i] < dt]

        if len(past_lows) >= 1 and len(past_highs) >= 1:
            last_low_dt,  last_low_p  = past_lows[-1]
            last_high_dt, last_high_p = past_highs[-1]

            # Case 1: Recent low BEFORE recent high — we had a rally, now checking retracement
            if last_low_dt < last_high_dt:
                swing_range = last_high_p - last_low_p
                if swing_range > 0:
                    fib618 = last_high_p - RPHI  * swing_range  # 61.8% retrace
                    fib382 = last_high_p - RPHI2 * swing_range  # 38.2% retrace
                    # Buy zone: price pulls back to 50%-70% Fibonacci retracement
                    if fib618 * 0.93 <= p <= fib382 * 1.07:
                        fib_buy_signal.iloc[t] = 1

                    # Fibonacci Extension Sell: price reaches 161.8% of the prior swing
                    ext_1618 = last_low_p + PHI  * swing_range  # 161.8% extension
                    ext_2618 = last_low_p + (PHI**2) * swing_range  # 261.8%
                    if p >= ext_1618 * 0.97:
                        fib_sell_signal.iloc[t] = 1

            # Case 2: Recent high BEFORE recent low — downtrend, buy the bounce
            elif last_high_dt < last_low_dt:
                swing_range = last_high_p - last_low_p
                if swing_range > 0 and len(past_highs) >= 2:
                    # Gann 1x1 from the most recent swing low
                    gann_signal.iloc[t] = gann_angle(last_low_p, last_low_dt, dt, p)

        # Momentum confirmation (weekly)
        if t >= 12:
            mom3m  = weekly.iloc[t] / weekly.iloc[t-13] - 1  # 3-month momentum
            mom1m  = weekly.iloc[t] / weekly.iloc[t-4]  - 1  # 1-month momentum
            if mom3m > 0.1 and mom1m > 0:               # 10%+ in 3 months and rising
                momentum_signal.iloc[t] = 1
            elif mom3m < -0.1:
                momentum_signal.iloc[t] = -1

    # ── Circle of 360 (seasonal timing filter) ───────────────────────────
    # Key turning days: 90, 180, 270, 360 days from each swing low
    c360_filter = pd.Series(0, index=weekly.index)
    for i in range(len(lo_idx)):
        base = lo_idx[i]
        for days in [90, 180, 270, 360]:
            target = base + pd.Timedelta(days=days)
            nearby = weekly.index[abs((weekly.index - target).days) <= 14]
            c360_filter[nearby] = 1

    # ── Composite Score ───────────────────────────────────────────────────
    # Score: weighted sum of all geometry signals
    signals['fib_buy']  = fib_buy_signal
    signals['fib_sell'] = fib_sell_signal
    signals['gann']     = gann_signal
    signals['momentum'] = momentum_signal
    signals['c360']     = c360_filter
    signals['above_sma20'] = (weekly > signals['sma20']).astype(int)
    signals['above_sma50'] = (weekly > signals['sma50']).astype(int)

    # Composite geometry score for ranking (higher = stronger buy signal)
    signals['geo_score'] = (
        signals['fib_buy']    * 2.0 +   # Fib 61.8% retracement = strong buy
        signals['momentum']   * 1.5 +   # Momentum confirmation
        signals['gann']       * 1.0 +   # Gann angle support
        signals['above_sma20']* 0.8 +   # Above SMA20 trend filter
        signals['above_sma50']* 0.8 +   # Above SMA50 trend filter
        signals['c360']       * 0.5 -   # Circle of 360 timing bonus
        signals['fib_sell']   * 3.0     # Fibonacci extension = sell signal
    )

    # Hard exit: any of these → sell
    signals['hard_exit'] = (
        (weekly < signals['sma50']) &    # Price below 50-week SMA
        (signals['momentum'] < 0)        # AND momentum turning negative
    ).astype(int)

    return signals

# Build geometry signals for all stocks
all_signals = {}
for name, s in raw.items():
    sig = fib_geometry_signals(s, name)
    if len(sig) > 0:
        all_signals[name] = sig

weekly_idx = list(all_signals.values())[0].index if all_signals else pd.DatetimeIndex([])
print(f"   Geometry computed for {len(all_signals)} stocks")

# ─── 3. ROTATION BACKTEST ─────────────────────────────────────────────────────
print("[3/4] Running geometry rotation backtest...")

capital    = CAPITAL
position   = 0.0
held       = None
held_weeks = 0
entry_cap  = 0.0

port_vals  = []
asset_log  = []
trades     = []
doubles    = []
dbl_ct     = 0
dbl_tgts   = [CAPITAL*(2**i) for i in range(1,11)]
MIN_HOLD   = 4  # minimum 4 weeks before rotating

for dt in weekly_idx:
    # Get current scores for all stocks
    scores = {}
    prices = {}
    exits  = {}
    for name, sig in all_signals.items():
        if dt in sig.index:
            row = sig.loc[dt]
            p   = row['price']
            if not np.isnan(p) and p > 0:
                scores[name] = row['geo_score']
                prices[name] = p
                exits[name]  = (row['hard_exit'] == 1) or (row['fib_sell'] == 1 and row['above_sma20'] == 0)

    # ── EXIT ──────────────────────────────────────────────────────────────
    if held and held in prices:
        curr_p  = prices[held]
        do_exit = exits.get(held, False) and held_weeks >= MIN_HOLD

        # Also exit if a MUCH better opportunity exists (score > current + 3)
        if held in scores and not do_exit and held_weeks >= MIN_HOLD:
            curr_score = scores[held]
            best_other = max((s for n,s in scores.items() if n != held), default=-99)
            if best_other > curr_score + 3.0 and curr_score < 2.0:
                do_exit = True

        if do_exit:
            gross   = position * curr_p
            fee     = gross * FRICTION
            capital = max(gross - fee, 0)
            trades.append({"date":dt,"type":"SELL","asset":held,
                           "price":curr_p,"capital":capital,"wks":held_weeks})
            position, held, held_weeks = 0.0, None, 0

    # ── ENTRY ─────────────────────────────────────────────────────────────
    if held is None and capital > 0 and scores:
        # Only buy stocks with positive geometry score
        valid = {n:sc for n,sc in scores.items() if sc > 1.0 and n in prices}
        if valid:
            best = max(valid, key=lambda n: valid[n])
            ep   = prices[best]
            if ep > 0:
                fee      = capital * FRICTION
                position = (capital - fee) / ep
                entry_cap = capital
                capital  = 0.0
                held     = best
                held_weeks = 0
                trades.append({"date":dt,"type":"BUY","asset":best,
                               "price":ep,"score":valid[best]})

    if held: held_weeks += 1

    # ── PORTFOLIO VALUE ───────────────────────────────────────────────────
    if held and held in prices:
        pv = position * prices[held]
    else:
        pv = capital

    port_vals.append(pv)
    asset_log.append(held or "CASH")

    while dbl_ct < 10 and pv >= dbl_tgts[dbl_ct]:
        doubles.append((dt, dbl_ct+1, pv))
        dbl_ct += 1

port_s = pd.Series(port_vals, index=weekly_idx)

# Buy & Hold benchmarks using individual best stocks
best_stocks_bh = {}
for name, s in raw.items():
    w = s.resample("W").last().reindex(weekly_idx, method="ffill")
    if len(w.dropna()) > 30:
        best_stocks_bh[name] = CAPITAL * (w / w.dropna().iloc[0])

# Nifty 50 as market benchmark
nifty = yf.download("^NSEI", start=START, end=END, progress=False)
if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.get_level_values(0)
nifty_w = nifty['Close'].dropna().resample("W").last().reindex(weekly_idx, method="ffill")
bh_nifty = CAPITAL * (nifty_w / nifty_w.dropna().iloc[0])

# ─── 4. RESULTS ──────────────────────────────────────────────────────────────
def stats(s):
    s = s.dropna()
    if len(s) < 5: return 0,0,0,0
    r = s.pct_change().dropna()
    cagr = (s.iloc[-1]/s.iloc[0])**(52/len(s))-1
    sh   = (cagr-0.06)/(r.std()*np.sqrt(52)) if r.std()>0 else 0
    dd   = ((s-s.cummax())/s.cummax()).min()
    return cagr, r.std()*np.sqrt(52), sh, dd

c_g,v_g,s_g,d_g = stats(port_s)
final   = port_s.dropna().iloc[-1]
total_x = final / CAPITAL

from collections import Counter
alloc = Counter(asset_log)
total_w = len(asset_log)

print("\n" + "="*70)
print("  MARKET GEOMETRY ENGINE — RESULTS")
print("="*70)
print(f"\n  Strategy        | Final (INR)   | CAGR   | Sharpe | MaxDD | Dbl")
print(f"  ----------------+---------------+--------+--------+-------+----")
print(f"  Geometry Engine | {final:>13,.0f} | {c_g*100:5.1f}% | {s_g:6.2f} | {d_g*100:5.1f}% | {dbl_ct}/10")
c_n,_,s_n,d_n = stats(bh_nifty)
print(f"  Nifty 50 B&H    | {bh_nifty.dropna().iloc[-1]:>13,.0f} | {c_n*100:5.1f}% | {s_n:6.2f} | {d_n*100:5.1f}% |  -")

# Top individual stock returns
print(f"\n  Top stock buy-holds in universe:")
stock_results = []
for name, bh in best_stocks_bh.items():
    c,_,sh,dd = stats(bh)
    fv = bh.dropna().iloc[-1]
    stock_results.append((name, fv, c, sh, dd))
stock_results.sort(key=lambda x:-x[1])
for name,fv,c,sh,dd in stock_results[:8]:
    print(f"    {name:12s}: Rs{fv:>10,.0f}  ({fv/CAPITAL:.0f}x)  CAGR {c*100:.0f}%  MaxDD {dd*100:.0f}%")

print(f"\n  Geometry Engine Final: Rs{final:,.0f} ({total_x:.0f}x)  [{dbl_ct}/10 doubles]")
if doubles:
    print(f"\n  Doubling Timeline:")
    for d in doubles:
        print(f"    #{d[1]:>2}  {d[0].strftime('%b %Y')}  Rs{d[2]:>13,.0f}  ({d[2]/CAPITAL:.0f}x)")

print(f"\n  Asset allocation:")
for a,cnt in sorted(alloc.items(), key=lambda x:-x[1])[:10]:
    bar = "█"*int(cnt/total_w*35)
    print(f"    {a:14s} {cnt:4d}w ({cnt/total_w*100:4.1f}%)  {bar}")

sells = [t for t in trades if t['type']=='SELL']
buys_ = [t for t in trades if t['type']=='BUY'][1:]
print(f"\n  Key rotations ({len(sells)} total):")
for s,b in zip(sells[:15], buys_[:15]):
    print(f"    {s['date'].strftime('%b %Y')}: {s['asset']:12s} -> {b['asset']:12s}  Rs{s.get('capital',0):>10,.0f}")

# ─── 5. CHART ─────────────────────────────────────────────────────────────────
print("\n[4/4] Generating chart...")
import matplotlib.patches as mpatches
import matplotlib.cm as cm

# Color per stock
stock_names = list(all_signals.keys())
color_map   = {n: cm.tab20(i/len(stock_names)) for i,n in enumerate(stock_names)}
color_map["CASH"] = (0.2, 0.2, 0.3, 1.0)

plt.style.use("dark_background")
fig = plt.figure(figsize=(18, 12), facecolor="#06060e")
gs  = fig.add_gridspec(3, 2, height_ratios=[3.5,1,1], hspace=0.06, wspace=0.22)
ax1 = fig.add_subplot(gs[0, :])
ax2 = fig.add_subplot(gs[1, :], sharex=ax1)
ax3 = fig.add_subplot(gs[2, 0], sharex=ax1)
ax4 = fig.add_subplot(gs[2, 1])
for ax in [ax1,ax2,ax3]: ax.set_facecolor("#06060e")
ax4.set_facecolor("#06060e")

# Main equity curve
ax1.plot(port_s.index, port_s, color="#00ffcc", lw=3.0, zorder=5,
         label=f"Geometry Engine  ({c_g*100:.1f}% CAGR | {total_x:.0f}x | {dbl_ct}/10 doubles)")
ax1.plot(bh_nifty.index, bh_nifty, color="#aaaaaa", lw=1.0, ls="--", alpha=0.4,
         label=f"Nifty 50 B&H  ({c_n*100:.1f}% CAGR)")

# Top 5 individual stock curves
for i,(name,fv,c,sh,dd) in enumerate(stock_results[:5]):
    bh = best_stocks_bh[name]
    ax1.plot(bh.index, bh, lw=1.0, ls=":", alpha=0.5, color=color_map[name],
             label=f"{name}  ({fv/CAPITAL:.0f}x  {c*100:.0f}% CAGR)")

# Doubling markers
cmap = plt.cm.plasma(np.linspace(0.15,1.0,10))
dbl_tgts_list = [CAPITAL*(2**i) for i in range(1,11)]
for i,(dt,dn,pv) in enumerate(doubles):
    ax1.axhline(dbl_tgts_list[i], color=cmap[i], lw=0.7, ls=":", alpha=0.55)
    ax1.scatter([dt],[pv], color=cmap[i], s=130, zorder=6, edgecolors='white', linewidths=0.5)
    ax1.annotate(f"#{dn} ({pv/CAPITAL:.0f}x)", (dt,pv),
                 xytext=(7,5), textcoords="offset points",
                 fontsize=8, color=cmap[i], fontweight="bold")

ax1.axhline(10_000_000, color="#ff3333", lw=2.2, ls="--", alpha=0.9,
            label="Rs 10 Crore Target")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x,_: f"Rs{x/1e7:.0f}Cr" if x>=5e6 else(f"Rs{x/1e5:.0f}L" if x>=1e5 else f"Rs{x/1e3:.0f}k")))
ax1.set_ylabel("Portfolio (INR)", color="#ccc", fontsize=11)
ax1.set_title(
    "Market Geometry Engine — Indian Smallcap Multibaggers (2016-2026)\n"
    "Fibonacci 61.8% Retracement + Gann 1x1 + Momentum + Circle of 360 | Zero Leverage",
    color="white", fontsize=13, fontweight="bold", pad=12)
ax1.legend(loc="upper left", fontsize=7.5, facecolor="#1a1a2e", edgecolor="#444",
           ncol=2)
ax1.grid(True, color="#1a1a2e", ls=":", alpha=0.6)

# Asset allocation bar (color per stock)
prev = np.zeros(len(weekly_idx))
all_assets = sorted(set(asset_log), key=lambda a: alloc[a], reverse=True)
for a in all_assets:
    vals = np.array([1.0 if x==a else 0.0 for x in asset_log])
    color = color_map.get(a, (0.5,0.5,0.5,1.0))
    ax2.bar(weekly_idx, vals, bottom=prev, color=color, width=8, alpha=0.9)
    prev += vals
ax2.set_yticks([])
ax2.set_ylabel("Stock Held", color="#ccc", fontsize=9)
patches = [mpatches.Patch(color=color_map.get(a,(0.5,0.5,0.5,1.0)), label=a)
           for a in all_assets[:12]]
ax2.legend(handles=patches, loc="upper left", fontsize=6.5, ncol=7,
           facecolor="#1a1a2e", edgecolor="#444")

# Drawdown
dd_s = (port_s - port_s.cummax())/port_s.cummax()*100
ax3.fill_between(weekly_idx, dd_s, 0, color="#ff4444", alpha=0.35)
ax3.plot(weekly_idx, dd_s, color="#ff6666", lw=0.8)
ax3.axhline(0, color="#555", lw=0.5)
ax3.set_ylabel("Drawdown %", color="#ccc", fontsize=9)
ax3.grid(True, color="#1a1a2e", ls=":", alpha=0.4)

# Pie chart
pie_labels = [f"{a}\n{cnt/total_w*100:.0f}%" for a,cnt in sorted(alloc.items(),key=lambda x:-x[1])[:10]]
pie_sizes  = [cnt for a,cnt in sorted(alloc.items(),key=lambda x:-x[1])[:10]]
pie_colors = [color_map.get(a,(0.5,0.5,0.5,1.0)) for a,cnt in sorted(alloc.items(),key=lambda x:-x[1])[:10]]
ax4.pie(pie_sizes, labels=pie_labels, colors=pie_colors, startangle=90,
        textprops={"color":"white","fontsize":7},
        wedgeprops={"edgecolor":"#222","linewidth":0.8})
ax4.set_title("Allocation\nby Stock", color="white", fontsize=9, fontweight="bold")

plt.setp(ax1.get_xticklabels(), visible=False)
plt.setp(ax2.get_xticklabels(), visible=False)
for ax in [ax1,ax2,ax3]: ax.tick_params(colors="#aaa")

fig.text(0.08, 0.005,
    "Geometry: Fibonacci 61.8% retracement + 161.8% extension exits + Gann 1x1 angle + Circle of 360 seasonal timing. "
    "Universe: 15 Indian multibagger stocks. Min hold 4 weeks. Friction 0.2%/trade.",
    fontsize=7.5, color="#666", style="italic")
plt.tight_layout(rect=[0, 0.02, 1, 1])
chart = os.path.join(OUT_DIR, "geometry_indian_chart.png")
plt.savefig(chart, dpi=300, facecolor=fig.get_facecolor())

# ─── REPORT ──────────────────────────────────────────────────────────────────
rpt = os.path.join(OUT_DIR, "geometry_indian_report.md")
dbl_lines  = "\n".join(f"| {d[1]} | {d[0].strftime('%B %Y')} | INR {d[2]:,.0f} | {d[2]/CAPITAL:.0f}x |" for d in doubles)
stock_lines = "\n".join(f"| {n} | INR {fv:,.0f} | {fv/CAPITAL:.0f}x | {c*100:.0f}% | {dd*100:.0f}% |"
                        for n,fv,c,sh,dd in stock_results)
alloc_lines = "\n".join(f"| {a} | {cnt} | {cnt/total_w*100:.1f}% |" for a,cnt in sorted(alloc.items(),key=lambda x:-x[1])[:12])

with open(rpt,"w",encoding="utf-8") as f:
    f.write(f"""# Market Geometry Engine — Indian Multibagger Universe (2016-2026)

## Geometry Layers
1. **Fibonacci Retracement** — Buy at 50-70% retracement of major swing (61.8% = golden ratio)
2. **Fibonacci Extension** — Exit at 161.8% and 261.8% of prior swing (profit target)
3. **Gann 1x1 Angle** — Price above 1x1 trend line from swing low = bullish
4. **Momentum Filter** — 3-month return >10% AND 1-month positive
5. **Circle of 360** — Seasonal timing bonus at 90/180/270/360 days from swing lows
6. **Hard Exit** — Price below 50-week SMA + negative momentum

## Universe Performance (Buy & Hold)
| Stock | Buy & Hold Value | Return | CAGR | Max DD |
|:---|:---|:---|:---|:---|
{stock_lines}

## Geometry Rotation Engine Results

| Metric | Value |
|:---|:---|
| **Final Portfolio** | **INR {final:,.0f}** |
| **CAGR** | **{c_g*100:.1f}%** |
| **Sharpe Ratio** | **{s_g:.2f}** |
| **Max Drawdown** | **{d_g*100:.1f}%** |
| **Total Return** | **{total_x:.0f}x** |
| **Doublings** | **{dbl_ct}/10** |
| **Total Trades** | **{len(trades)}** |

## Doubling Timeline
| # | Month | Portfolio | Return |
|:---|:---|:---|:---|
{dbl_lines}

## Asset Allocation
| Stock | Weeks | % Time |
|:---|:---|:---|
{alloc_lines}
""")

print(f"\nChart:  {chart}")
print(f"Report: {rpt}")
print("=== DONE ===")
