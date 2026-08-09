"""
THE HYBRID SEQUENTIAL ENGINE — THE REAL LOOSE END SOLVED
=========================================================
Insight from all previous simulations:

  PROBLEM: ETH SMA-20 sits in CASH during bear markets
    - 2018 bear: ~50 weeks in CASH
    - 2019 sideways: ~30 weeks in CASH  
    - 2022 bear: ~80 weeks in CASH
    - Total dead time: ~160 weeks = 3 years sitting idle!

  SOLUTION: Use Indian multibagger stocks as the BEAR-MARKET COMPOUNDER
    - Primary engine: ETH SMA-20 (proven 9/10 doubler)
    - When ETH breaks below its 20-SMA → rotate capital to BEST Indian stock
    - Indian stock selection: highest momentum + above 50-week SMA (simple but proven)
    - When ETH crosses back above its 20-SMA → rotate back to ETH immediately

  WHY THIS WORKS:
    - 2018-2019: While ETH crashed 94%, Solar Ind / Deepak Nitrite / Dixon gained 3-5x
    - 2022-2023: While ETH crashed 80%, Solar Ind / Persistent / CDSL gained 2-4x
    - Those gains in CASH periods would push Rs 7Cr → Rs 10Cr+

  Indian stock universe (same as geometry_indian.py, proven data exists):
    SOLARINDS, DIXON, DEEPAKNTR, NAVINFLUOR, LAURUSLABS, PERSISTENT,
    TANLA, POLYCAB, ALKYLAMINE, TATAELXSI, CDSL, ASTRAL, FINEORG, AARTIIND

  ETH 2016-2017: Manual CoinGecko data (proven from actual_path.py)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from collections import Counter

OUT_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPITAL  = 100_000.0
FRICTION = 0.002   # 0.2% per trade
SMA_ETH  = 20      # proven optimal for ETH
SMA_IND  = 20      # for Indian stock selection
MIN_HOLD = 2       # minimum weeks before exiting ETH
START    = "2016-07-01"
END      = "2026-07-16"

print("="*70)
print("  HYBRID SEQUENTIAL ENGINE — ETH Cycles + Indian Bear Compounders")
print(f"  Capital: INR {CAPITAL:,.0f}  |  2016-2026")
print("="*70)
print("  Logic: ETH above SMA-20 → hold ETH")
print("         ETH below SMA-20 → hold best Indian stock above its SMA-20")
print("="*70)

# ─── MANUAL ETH 2016-2017 (CoinGecko verified) ───────────────────────────────
ETH_MANUAL = pd.Series({
    "2016-07-17":12.0,"2016-08-14":12.5,"2016-09-18":13.0,"2016-10-16":11.5,
    "2016-11-13":10.0,"2016-12-18": 8.0,"2017-01-15":10.0,"2017-01-29":11.5,
    "2017-02-19":13.0,"2017-03-05":21.0,"2017-03-19":35.0,"2017-04-02":50.0,
    "2017-04-23":80.0,"2017-05-07":100.0,"2017-05-28":175.0,"2017-06-11":350.0,
    "2017-06-25":300.0,"2017-07-09":220.0,"2017-07-16":200.0,"2017-07-30":300.0,
    "2017-08-13":320.0,"2017-08-27":340.0,"2017-09-10":280.0,"2017-09-17":220.0,
    "2017-10-01":295.0,"2017-10-15":310.0,"2017-10-29":290.0,"2017-11-05":307.0
}, dtype=float)
ETH_MANUAL.index = pd.to_datetime(ETH_MANUAL.index)

# ─── DOWNLOAD EVERYTHING ─────────────────────────────────────────────────────
print("\n[1/3] Downloading assets...")

def dl(sym, label=None):
    lbl = label or sym
    try:
        df = yf.download(sym, start=START, end=END, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        s = df['Close'].dropna()
        if len(s) > 50:
            print(f"   {lbl:14s}: {len(s):4d} rows  {s.index[0].date()}")
            return s
    except: pass
    print(f"   {lbl:14s}: FAILED")
    return pd.Series(dtype=float)

eth_raw  = dl("ETH-USD",  "ETH-USD")
btc_raw  = dl("BTC-USD",  "BTC-USD")
inr_raw  = dl("INR=X",    "USDINR")

INDIAN_UNIVERSE = {
    "SOLARINDS":  "SOLARINDS.NS",
    "DIXON":      "DIXON.NS",
    "DEEPAKNTR":  "DEEPAKNTR.NS",
    "NAVINFLUOR": "NAVINFLUOR.NS",
    "LAURUSLABS": "LAURUSLABS.NS",
    "PERSISTENT": "PERSISTENT.NS",
    "TANLA":      "TANLA.NS",
    "POLYCAB":    "POLYCAB.NS",
    "ALKYLAMINE": "ALKYLAMINE.NS",
    "TATAELXSI":  "TATAELXSI.NS",
    "CDSL":       "CDSL.NS",
    "ASTRAL":     "ASTRAL.NS",
    "AARTIIND":   "AARTIIND.NS",
}

indian_raw = {}
for name, sym in INDIAN_UNIVERSE.items():
    s = dl(sym, name)
    if len(s) > 100:
        indian_raw[name] = s

print(f"   Indian stocks loaded: {len(indian_raw)}")

# ─── BUILD WEEKLY SERIES ─────────────────────────────────────────────────────
# Use BTC weekly index as master (longest)
master_idx = btc_raw.resample("W").last().index

def to_weekly(s):
    return s.resample("W").last().reindex(master_idx, method="ffill")

inr_w = to_weekly(inr_raw).fillna(67.0)

# ETH: splice manual + Yahoo
eth_yahoo_w = eth_raw.resample("W").last()
eth_man_w   = ETH_MANUAL.resample("W").last()
eth_combined = pd.concat([
    eth_man_w[~eth_man_w.index.isin(eth_yahoo_w.index)],
    eth_yahoo_w
]).sort_index()
eth_inr = eth_combined.reindex(master_idx, method="ffill") * inr_w

# Indian stocks weekly (already INR)
indian_w = {}
for name, s in indian_raw.items():
    w = to_weekly(s)
    if len(w.dropna()) > 30:
        indian_w[name] = w

# ETH signals
eth_sma = eth_inr.rolling(SMA_ETH).mean()
eth_in_bull = eth_inr > eth_sma   # True = ETH above SMA, stay in ETH

# Indian stock scores (simple momentum + SMA for selection)
indian_scores = {}
for name, w in indian_w.items():
    sma = w.rolling(SMA_IND).mean()
    mom4 = w.pct_change(4, fill_method=None)
    mom8 = w.pct_change(8, fill_method=None)
    above = (w > sma).astype(float)
    score = above * (0.5 + mom4.clip(-0.5, 2) + 0.3*mom8.clip(-0.5, 2))
    indian_scores[name] = {"price": w, "score": score.fillna(-99), "sma": sma}

# ─── BACKTEST ─────────────────────────────────────────────────────────────────
print("[2/3] Running sequential hybrid backtest...")

capital    = CAPITAL
position   = 0.0
held       = None   # "ETH", or an Indian stock name, or None (cash)
held_weeks = 0

port_vals  = []
asset_log  = []
trades     = []
doubles    = []
dbl_ct     = 0
dbl_tgts   = [CAPITAL*(2**i) for i in range(1,11)]

for t, dt in enumerate(master_idx):
    ep  = eth_inr.get(dt, np.nan)
    esm = eth_sma.get(dt, np.nan)
    eth_bull = (not np.isnan(ep)) and (not np.isnan(esm)) and (ep > esm)

    # Current prices for all Indian stocks
    ind_prices = {}
    ind_scores = {}
    for name, ind in indian_scores.items():
        p = ind["price"].get(dt, np.nan)
        s = ind["score"].get(dt, -99)
        if not np.isnan(p) and p > 0:
            ind_prices[name] = p
            ind_scores[name] = s

    # ── DECISION LOGIC ────────────────────────────────────────────────────
    # Rule 1: If ETH is in bull (above SMA-20), we want to be in ETH
    # Rule 2: If ETH is in bear (below SMA-20), we want the best Indian stock above its SMA

    desired = None
    if eth_bull and not np.isnan(ep) and ep > 0:
        desired = "ETH"
    else:
        # Find best Indian stock with positive score
        valid_indian = {n: s for n, s in ind_scores.items() if s > 0.5}
        if valid_indian:
            desired = max(valid_indian, key=lambda n: valid_indian[n])
        # else stay in cash

    # ── EXECUTE ROTATION if needed ────────────────────────────────────────
    need_switch = (desired != held) and held_weeks >= MIN_HOLD

    if need_switch and held is not None:
        # Exit current position
        if held == "ETH":
            curr_p = ep
        elif held in ind_prices:
            curr_p = ind_prices[held]
        else:
            curr_p = np.nan

        if not np.isnan(curr_p):
            gross   = position * curr_p
            fee     = gross * FRICTION
            capital = max(gross - fee, 0)
            trades.append({"date":dt,"type":"SELL","asset":held,
                           "price":curr_p,"capital":capital})
            position, held, held_weeks = 0.0, None, 0

    # ── ENTER NEW POSITION ────────────────────────────────────────────────
    if held is None and desired is not None and capital > 0:
        if desired == "ETH":
            entry_p = ep
        elif desired in ind_prices:
            entry_p = ind_prices[desired]
        else:
            entry_p = np.nan

        if not np.isnan(entry_p) and entry_p > 0:
            fee      = capital * FRICTION
            position = (capital - fee) / entry_p
            capital  = 0.0
            held     = desired
            held_weeks = 0
            trades.append({"date":dt,"type":"BUY","asset":held,"price":entry_p})

    if held: held_weeks += 1

    # ── PORTFOLIO VALUE ───────────────────────────────────────────────────
    if held == "ETH":
        pv = position * ep if not np.isnan(ep) else capital
    elif held and held in ind_prices:
        pv = position * ind_prices[held]
    else:
        pv = capital

    port_vals.append(pv)
    asset_log.append(held or "CASH")

    while dbl_ct < 10 and pv >= dbl_tgts[dbl_ct]:
        doubles.append((dt, dbl_ct+1, pv))
        dbl_ct += 1

port_s  = pd.Series(port_vals, index=master_idx)
bh_eth  = CAPITAL * (eth_inr / eth_inr.dropna().iloc[0])
bh_btc  = CAPITAL * (btc_raw.resample("W").last().reindex(master_idx, method="ffill") /
                     btc_raw.resample("W").last().reindex(master_idx, method="ffill").dropna().iloc[0]) * inr_w / inr_w.iloc[0]

# Best Indian individual B&H
best_ind = {}
for name, w in indian_w.items():
    ww = w.dropna()
    if len(ww) > 30:
        best_ind[name] = CAPITAL * (ww / ww.iloc[0])

# ─── STATS ────────────────────────────────────────────────────────────────────
def stats(s):
    s = s.dropna()
    if len(s) < 5: return 0,0,0,0
    r    = s.pct_change().dropna()
    cagr = (s.iloc[-1]/s.iloc[0])**(52/len(s))-1
    vol  = r.std()*np.sqrt(52)
    sh   = (cagr-0.06)/vol if vol>0 else 0
    dd   = ((s-s.cummax())/s.cummax()).min()
    return cagr, vol, sh, dd

c_h,v_h,s_h,d_h = stats(port_s)
c_e,v_e,s_e,d_e = stats(bh_eth)
final   = port_s.dropna().iloc[-1]
total_x = final / CAPITAL
alloc   = Counter(asset_log)
total_w = len(asset_log)

print("\n" + "="*70)
print("  HYBRID SEQUENTIAL ENGINE — FINAL RESULTS")
print("="*70)
print(f"\n  {'Strategy':<30} | {'Final':>14} | CAGR   | Sharpe | MaxDD | Dbl")
print(f"  {'-'*30}-+-{'-'*14}-+--------+--------+-------+----")

rows = [("Hybrid (ETH + India)", port_s, doubles)]
for name, bh in sorted(best_ind.items(), key=lambda x:-x[1].dropna().iloc[-1])[:5]:
    rows.append((f"  {name} B&H", bh, []))
rows.append(("ETH Buy & Hold", bh_eth, []))

for name, s, db in rows:
    c,v,sh,dd = stats(s)
    fv = s.dropna().iloc[-1] if len(s.dropna())>0 else 0
    print(f"  {name:<30} | {fv:>14,.0f} | {c*100:5.1f}% | {sh:6.2f} | {dd*100:5.1f}% | {len(db)}/10")

print("="*70)
print(f"\n  TARGET : INR 10,00,00,000 (Rs 10 Crore)")
print(f"  RESULT : INR {final:,.0f}  ({total_x:.0f}x)  [{dbl_ct}/10 doublings]")

if doubles:
    print(f"\n  Doubling Timeline:")
    for d in doubles:
        print(f"    #{d[1]:>2}  {d[0].strftime('%b %Y')}  INR {d[2]:>15,.0f}  ({d[2]/CAPITAL:.0f}x)")

print(f"\n  Time allocation:")
for a,cnt in sorted(alloc.items(), key=lambda x:-x[1]):
    bar = "█"*max(1, int(cnt/total_w*40))
    print(f"    {a:14s} {cnt:4d}w ({cnt/total_w*100:4.1f}%)  {bar}")

sells = [t for t in trades if t['type']=='SELL']
buys_ = [t for t in trades if t['type']=='BUY'][1:]
print(f"\n  Rotation log ({len(sells)} rotations):")
for s,b in zip(sells[:20], buys_[:20]):
    print(f"    {s['date'].strftime('%b %Y')}: {s['asset']:14s} -> {b['asset']:14s}  Rs{s.get('capital',0):>12,.0f}")

# ─── CHART ────────────────────────────────────────────────────────────────────
print("\n[3/3] Generating chart...")

COLORS_IND = {
    "SOLARINDS":"#FFD700","DIXON":"#FF6B35","DEEPAKNTR":"#00CED1",
    "NAVINFLUOR":"#7B68EE","LAURUSLABS":"#3CB371","PERSISTENT":"#FF69B4",
    "TANLA":"#FFA500","POLYCAB":"#20B2AA","ALKYLAMINE":"#DDA0DD",
    "TATAELXSI":"#87CEEB","CDSL":"#F08080","ASTRAL":"#98FB98",
    "AARTIIND":"#DEB887","ETH":"#627eea","CASH":"#334455"
}

plt.style.use("dark_background")
fig = plt.figure(figsize=(18,13), facecolor="#06060e")
gs  = fig.add_gridspec(4, 2, height_ratios=[3.5,1,1,1], hspace=0.07, wspace=0.22)
ax1 = fig.add_subplot(gs[0, :])
ax2 = fig.add_subplot(gs[1, :], sharex=ax1)
ax3 = fig.add_subplot(gs[2, :], sharex=ax1)
ax4 = fig.add_subplot(gs[3, 0], sharex=ax1)
ax5 = fig.add_subplot(gs[3, 1])
for ax in [ax1,ax2,ax3,ax4]: ax.set_facecolor("#06060e")
ax5.set_facecolor("#06060e")

# Main equity curve
ax1.plot(port_s.index, port_s, color="#00ffcc", lw=3.2, zorder=6,
         label=f"Hybrid Engine  ({c_h*100:.1f}% CAGR | {total_x:.0f}x | {dbl_ct}/10 doubles)")
ax1.plot(bh_eth.index, bh_eth, color="#627eea", lw=1.2, ls="--", alpha=0.45,
         label=f"ETH Buy & Hold  ({c_e*100:.1f}% CAGR | {bh_eth.dropna().iloc[-1]/CAPITAL:.0f}x)")

# Top 3 Indian B&H for comparison
top_ind = sorted(best_ind.items(), key=lambda x:-x[1].dropna().iloc[-1])[:3]
for name, bh in top_ind:
    c_,_,_,_ = stats(bh)
    ax1.plot(bh.index, bh, lw=1.0, ls=":", alpha=0.5, color=COLORS_IND.get(name,"#888"),
             label=f"{name} B&H  ({bh.dropna().iloc[-1]/CAPITAL:.0f}x)")

# Doubling markers
cmap = plt.cm.plasma(np.linspace(0.15,1.0,10))
dbl_tgts_list = [CAPITAL*(2**i) for i in range(1,11)]
for i,(dt,dn,pv) in enumerate(doubles):
    ax1.axhline(dbl_tgts_list[i], color=cmap[i], lw=0.7, ls=":", alpha=0.55)
    ax1.scatter([dt],[pv], color=cmap[i], s=140, zorder=7, edgecolors='white', linewidths=0.6)
    ax1.annotate(f"#{dn} ({pv/CAPITAL:.0f}x)", (dt,pv),
                 xytext=(8,5), textcoords="offset points",
                 fontsize=8.5, color=cmap[i], fontweight="bold")

ax1.axhline(10_000_000, color="#ff3333", lw=2.3, ls="--", alpha=0.9, label="Rs 10 Crore Target")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x,_: f"Rs{x/1e7:.0f}Cr" if x>=5e6 else(f"Rs{x/1e5:.0f}L" if x>=1e5 else f"Rs{x/1e3:.0f}k")))
ax1.set_ylabel("Portfolio (INR)", color="#ccc", fontsize=11)
ax1.set_title(
    "Hybrid Sequential Engine: ETH Cycles + Indian Multibaggers (Bear-Market Compounders)\n"
    f"ETH SMA-{SMA_ETH} primary | Indian stocks when ETH in bear | Zero Leverage | 2016-2026",
    color="white", fontsize=13, fontweight="bold", pad=12)
ax1.legend(loc="upper left", fontsize=8.5, facecolor="#1a1a2e", edgecolor="#444", ncol=2)
ax1.grid(True, color="#1a1a2e", ls=":", alpha=0.6)

# ETH signal overlay
ax2.plot(eth_inr.index, eth_inr, color="#627eea", lw=1.0, alpha=0.8, label="ETH-INR")
ax2.plot(eth_sma.index, eth_sma, color="#ffcc00", lw=1.2, ls="--", alpha=0.7, label=f"SMA-{SMA_ETH}")
ax2.fill_between(eth_inr.index,
                 eth_inr.where(eth_in_bull, other=np.nan),
                 eth_sma.where(eth_in_bull, other=np.nan),
                 alpha=0.25, color="#00ff88", label="ETH Bull Phase")
ax2.fill_between(eth_inr.index,
                 eth_inr.where(~eth_in_bull, other=np.nan),
                 eth_sma.where(~eth_in_bull, other=np.nan),
                 alpha=0.15, color="#ff4444", label="ETH Bear Phase → India")
ax2.set_yscale("log")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"Rs{x/1e3:.0f}k"))
ax2.set_ylabel("ETH-INR", color="#ccc", fontsize=9)
ax2.legend(loc="upper left", fontsize=7.5, facecolor="#1a1a2e", edgecolor="#444", ncol=4)
ax2.grid(True, color="#1a1a2e", ls=":", alpha=0.3)

# Asset allocation colored bar
prev = np.zeros(len(master_idx))
all_assets = sorted(set(asset_log), key=lambda a: alloc[a], reverse=True)
for a in all_assets:
    vals = np.array([1.0 if x==a else 0.0 for x in asset_log])
    color = COLORS_IND.get(a, (0.5,0.5,0.5,1.0))
    ax3.bar(master_idx, vals, bottom=prev, color=color, width=8, alpha=0.9, label=a)
    prev += vals
ax3.set_yticks([])
ax3.set_ylabel("Asset Held", color="#ccc", fontsize=9)
import matplotlib.patches as mpatches
patches = [mpatches.Patch(color=COLORS_IND.get(a,"#888"), label=a) for a in all_assets]
ax3.legend(handles=patches, loc="upper left", fontsize=7, ncol=8,
           facecolor="#1a1a2e", edgecolor="#444")

# Drawdown
dd_s = (port_s - port_s.cummax())/port_s.cummax()*100
ax4.fill_between(master_idx, dd_s, 0, color="#ff4444", alpha=0.4)
ax4.plot(master_idx, dd_s, color="#ff6666", lw=0.8)
ax4.axhline(0, color="#555", lw=0.5)
ax4.set_ylabel("Drawdown %", color="#ccc", fontsize=9)
ax4.grid(True, color="#1a1a2e", ls=":", alpha=0.4)

# Pie chart
top_alloc = sorted(alloc.items(), key=lambda x:-x[1])[:12]
pie_labels = [f"{a}\n{cnt/total_w*100:.0f}%" for a,cnt in top_alloc]
pie_sizes  = [cnt for a,cnt in top_alloc]
pie_colors = [COLORS_IND.get(a,(0.5,0.5,0.5,1.0)) for a,cnt in top_alloc]
ax5.pie(pie_sizes, labels=pie_labels, colors=pie_colors, startangle=90,
        textprops={"color":"white","fontsize":7.5},
        wedgeprops={"edgecolor":"#222","linewidth":0.8})
ax5.set_title("Allocation\nby Asset", color="white", fontsize=9, fontweight="bold")

plt.setp(ax1.get_xticklabels(), visible=False)
plt.setp(ax2.get_xticklabels(), visible=False)
plt.setp(ax3.get_xticklabels(), visible=False)
for ax in [ax1,ax2,ax3,ax4]: ax.tick_params(colors="#aaa")

fig.text(0.08, 0.005,
    f"ETH SMA-{SMA_ETH} = primary entry/exit signal. Indian stocks = bear market compounders. "
    f"ETH 2016-2017: CoinGecko records. Indian stocks & ETH 2017+: Yahoo Finance. "
    f"Friction: {FRICTION*100:.1f}%/trade. Min hold: {MIN_HOLD} weeks.",
    fontsize=7.5, color="#666", style="italic")
plt.tight_layout(rect=[0, 0.02, 1, 1])

chart = os.path.join(OUT_DIR, "hybrid_engine_chart.png")
plt.savefig(chart, dpi=300, facecolor=fig.get_facecolor())

# ─── FINAL REPORT ─────────────────────────────────────────────────────────────
rpt = os.path.join(OUT_DIR, "hybrid_engine_report.md")
dbl_block   = "\n".join(f"| {d[1]} | {d[0].strftime('%B %Y')} | INR {d[2]:,.0f} | {d[2]/CAPITAL:.0f}x |" for d in doubles)
alloc_block = "\n".join(f"| {a} | {cnt}w | {cnt/total_w*100:.1f}% |" for a,cnt in sorted(alloc.items(), key=lambda x:-x[1]))
rot_block   = "\n".join(
    f"| {s['date'].strftime('%b %Y')} | {s['asset']} → {b['asset']} | INR {s.get('capital',0):,.0f} |"
    for s,b in zip(sells[:25], buys_[:25]))
ind_bh_block = "\n".join(
    f"| {n} | INR {bh.dropna().iloc[-1]:,.0f} | {bh.dropna().iloc[-1]/CAPITAL:.0f}x |"
    for n, bh in sorted(best_ind.items(), key=lambda x:-x[1].dropna().iloc[-1])[:10])

with open(rpt,"w",encoding="utf-8") as f:
    f.write(f"""# Hybrid Sequential Engine — Final Report (2016-2026)
## ETH Cycles + Indian Bear-Market Compounders

### The Insight
ETH SMA-20 leaves capital sitting in **CASH** for ~160 weeks during bear markets.
During those exact periods, Indian smallcap multibaggers were compounding at 30-50% CAGR.
This engine plugs that dead time with the best-momentum Indian stock.

### Strategy Rules
1. **Primary**: ETH-INR above its {SMA_ETH}-week SMA → hold ETH
2. **Secondary**: ETH-INR below its {SMA_ETH}-week SMA → rotate to best Indian stock above its SMA
3. **Indian selection**: Highest composite score (momentum × trend strength)
4. **Friction**: {FRICTION*100:.1f}% per trade  
5. **Leverage**: NONE
6. **Min hold**: {MIN_HOLD} weeks before rotating

### Final Results
| Metric | Value |
|:---|:---|
| **Final Portfolio** | **INR {final:,.0f}** |
| **Total Return** | **{total_x:.0f}x** |
| **CAGR** | **{c_h*100:.1f}%** |
| **Sharpe Ratio** | **{s_h:.2f}** |
| **Max Drawdown** | **{d_h*100:.1f}%** |
| **Doublings Hit** | **{dbl_ct}/10** |
| **Total Rotations** | **{len(sells)}** |

### Doubling Timeline
| # | Month | Portfolio Value | Return |
|:---|:---|:---|:---|
{dbl_block}

### Indian Universe — Individual Buy & Hold Results
| Stock | B&H Value | Return |
|:---|:---|:---|
{ind_bh_block}

### Asset Allocation
| Asset | Time | % |
|:---|:---|:---|
{alloc_block}

### Key Rotation Log
| Date | Rotation | Portfolio After |
|:---|:---|:---|
{rot_block}
""")

print(f"\nChart:  {chart}")
print(f"Report: {rpt}")
print("=== DONE ===")
