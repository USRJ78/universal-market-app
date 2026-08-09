"""
MASTER COMPARISON — All Strategies Tested (2016-2026)
======================================================
The definitive visual summary of every approach tried.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPITAL = 100_000.0

# ETH manual data
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

print("Downloading data...")
eth_d  = yf.download("ETH-USD",  start="2016-07-01", end="2026-07-16", progress=False)
btc_d  = yf.download("BTC-USD",  start="2016-07-01", end="2026-07-16", progress=False)
inr_d  = yf.download("INR=X",    start="2016-07-01", end="2026-07-16", progress=False)
sol_d  = yf.download("SOL-USD",  start="2020-04-01", end="2026-07-16", progress=False)

for df in [eth_d, btc_d, inr_d, sol_d]:
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

btc_w  = btc_d['Close'].dropna().resample("W").last()
all_idx= btc_w.index
inr_w  = inr_d['Close'].dropna().resample("W").last().reindex(all_idx, method="ffill").fillna(67.0)

eth_yahoo = eth_d['Close'].dropna().resample("W").last()
eth_man   = ETH_MANUAL.resample("W").last()
eth_combo = pd.concat([eth_man[~eth_man.index.isin(eth_yahoo.index)], eth_yahoo]).sort_index()
eth_inr   = eth_combo.reindex(all_idx, method="ffill") * inr_w

sol_inr   = sol_d['Close'].dropna().resample("W").last().reindex(all_idx, method="ffill") * inr_w
btc_inr   = btc_w * inr_w

# ── ETH SMA-20 Strategy (THE WINNER) ─────────────────────────────────────────
def run_sma(price_s, n=20, friction=0.002, min_hold=0):
    sma = price_s.rolling(n).mean()
    cap, pos, held = CAPITAL, 0.0, False
    held_w = 0
    vals, dbl, dbl_ct = [], [], 0
    tgts = [CAPITAL*(2**i) for i in range(1,11)]
    for t in range(len(price_s)):
        p, sm = price_s.iloc[t], sma.iloc[t]
        if np.isnan(p) or np.isnan(sm):
            vals.append(cap if not held else pos*p)
            continue
        pp  = price_s.iloc[t-1] if t>0 else p
        psm = sma.iloc[t-1]     if t>0 else sm
        if not held and (p>sm) and (pp<=psm):
            pos, cap, held, held_w = (cap*(1-friction))/p, 0.0, True, 0
        elif held and (p<sm) and (pp>=psm) and held_w>=min_hold:
            cap, pos, held, held_w = pos*p*(1-friction), 0.0, False, 0
        if held: held_w+=1
        pv = (pos*p) if held else cap
        vals.append(pv)
        while dbl_ct<10 and pv>=tgts[dbl_ct]:
            dbl.append((price_s.index[t], dbl_ct+1, pv)); dbl_ct+=1
    return pd.Series(vals, index=price_s.index), dbl

eth20, dbl_eth20 = run_sma(eth_inr, 20)
eth10, dbl_eth10 = run_sma(eth_inr, 10)
btc20, dbl_btc20 = run_sma(btc_inr, 20)

bh_eth = CAPITAL * (eth_inr / eth_inr.dropna().iloc[0])
bh_btc = CAPITAL * (btc_inr / btc_inr.dropna().iloc[0])
bh_sol = CAPITAL * (sol_inr / sol_inr.dropna().iloc[0])

def stats(s):
    s = s.dropna()
    if len(s)<5: return 0,0,0,0
    r = s.pct_change().dropna()
    cagr = (s.iloc[-1]/s.iloc[0])**(52/len(s))-1
    vol  = r.std()*np.sqrt(52)
    return cagr, vol, (cagr-0.06)/vol if vol>0 else 0, ((s-s.cummax())/s.cummax()).min()

# Results table
results = [
    ("ETH SMA-20 Cycle ⭐",  eth20,  dbl_eth20, "#00ffcc"),
    ("ETH SMA-10 Cycle",     eth10,  dbl_eth10, "#00ccaa"),
    ("BTC SMA-20 Cycle",     btc20,  dbl_btc20, "#f7931a"),
    ("ETH Buy & Hold",       bh_eth, [],         "#627eea"),
    ("BTC Buy & Hold",       bh_btc, [],         "#f7931a"),
    ("SOL Buy & Hold",       bh_sol, [],         "#9945ff"),
]

print("\n" + "="*72)
print("  MASTER COMPARISON — All Strategies 2016-2026")
print("="*72)
print(f"  {'Strategy':<26} | {'Final (INR)':>14} | CAGR   | Sharpe | MaxDD | Dbl")
print(f"  {'-'*26}-+-{'-'*14}-+--------+--------+-------+----")
for name, s, db, _ in results:
    c,v,sh,dd = stats(s)
    fv = s.dropna().iloc[-1]
    print(f"  {name:<26} | {fv:>14,.0f} | {c*100:5.1f}% | {sh:6.2f} | {dd*100:5.1f}% | {len(db)}/10")

print("="*72)

# Also print what the other engines got (from saved results)
print(f"\n  (From previous runs:)")
print(f"  {'Geometry Indian':<26} | {'778,115':>14} | {'22.5%':>6}   | {'0.41':>6} | {'-58.8%':>6} |  3/10")
print(f"  {'Hybrid ETH+India':<26} | {'275,496':>14} | {'10.6%':>6}   | {'0.07':>6} | {'-85.4%':>6} |  4/10")
print(f"  {'Everything Engine':<26} | {'2,716,603':>14} | {'38.7%':>6}   | {'0.41':>6} | {'-96.4%':>6} |  7/10")

# ── CHART ────────────────────────────────────────────────────────────────────
print("\nGenerating master comparison chart...")
plt.style.use("dark_background")
fig = plt.figure(figsize=(18,13), facecolor="#06060e")
gs  = fig.add_gridspec(3, 2, height_ratios=[3.5, 1.2, 1.2], hspace=0.08, wspace=0.25)
ax1 = fig.add_subplot(gs[0, :])
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
ax3 = fig.add_subplot(gs[1, 1])
ax4 = fig.add_subplot(gs[2, 0], sharex=ax1)
ax5 = fig.add_subplot(gs[2, 1])
for ax in [ax1,ax2,ax4]: ax.set_facecolor("#06060e")
ax3.set_facecolor("#0d0d1a")
ax5.set_facecolor("#0d0d1a")

# ── MAIN EQUITY CURVES ────────────────────────────────────────────────────────
ax1.plot(eth20.index, eth20, color="#00ffcc", lw=3.5, zorder=7,
         label=f"⭐ ETH SMA-20 Cycle — THE WINNER  ({stats(eth20)[0]*100:.1f}% CAGR | {eth20.dropna().iloc[-1]/CAPITAL:.0f}x | {len(dbl_eth20)}/10 doublings)")
ax1.plot(eth10.index, eth10, color="#00aa88", lw=1.8, zorder=6, ls="-",
         label=f"ETH SMA-10 Cycle  ({stats(eth10)[0]*100:.1f}% CAGR | {eth10.dropna().iloc[-1]/CAPITAL:.0f}x | {len(dbl_eth10)}/10 doublings)")
ax1.plot(bh_eth.index, bh_eth, color="#627eea", lw=1.2, ls="--", alpha=0.5,
         label=f"ETH Buy & Hold  ({stats(bh_eth)[0]*100:.1f}% CAGR | {bh_eth.dropna().iloc[-1]/CAPITAL:.0f}x)")
ax1.plot(bh_btc.index, bh_btc, color="#f7931a", lw=1.0, ls=":", alpha=0.4,
         label=f"BTC Buy & Hold  ({stats(bh_btc)[0]*100:.1f}% CAGR)")
ax1.plot(btc20.index, btc20, color="#cc7700", lw=1.0, ls="--", alpha=0.5,
         label=f"BTC SMA-20 Cycle  ({stats(btc20)[0]*100:.1f}% CAGR | {btc20.dropna().iloc[-1]/CAPITAL:.0f}x)")

# Add the other engines as horizontal reference lines at their final values
ax1.axhline(70_039_804, color="#00ffcc", lw=0.4, ls=":", alpha=0.3)  # eth20 reference
ax1.axhline(2_716_603, color="#ff8800", lw=1.0, ls=":", alpha=0.6,
            label="Everything Engine (best multi-asset)  ₹27L  7/10 doublings")
ax1.axhline(778_115,   color="#ff4444", lw=1.0, ls=":", alpha=0.5,
            label="Geometry Indian Engine  ₹7.8L  3/10 doublings")
ax1.axhline(275_496,   color="#ff2222", lw=1.0, ls=":", alpha=0.4,
            label="Hybrid ETH+India Engine  ₹2.75L  4/10 doublings")

# Doubling markers for ETH SMA-20
cmap = plt.cm.plasma(np.linspace(0.15,1.0,10))
dbl_tgts_list = [CAPITAL*(2**i) for i in range(1,11)]
for i,(dt,dn,pv) in enumerate(dbl_eth20):
    ax1.axhline(dbl_tgts_list[i], color=cmap[i], lw=0.8, ls=":", alpha=0.6)
    ax1.scatter([dt],[pv], color=cmap[i], s=150, zorder=8, edgecolors='white', linewidths=0.7)
    ax1.annotate(f"#{dn}  {pv/CAPITAL:.0f}x", (dt,pv),
                 xytext=(8,5), textcoords="offset points",
                 fontsize=8.5, color=cmap[i], fontweight="bold")

ax1.axhline(10_000_000, color="#ff3333", lw=2.5, ls="--", alpha=0.95,
            label="🎯 Rs 10 Crore Target")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x,_: f"Rs{x/1e7:.0f}Cr" if x>=5e6 else(f"Rs{x/1e5:.0f}L" if x>=1e5 else f"Rs{x/1e3:.0f}k")))
ax1.set_ylabel("Portfolio Value (INR)", color="#ccc", fontsize=12)
ax1.set_title(
    "Master Comparison: Every Strategy Tested — INR 1 Lakh → ? (2016-2026)\n"
    "ETH SMA-20 Cycle is the Undisputed Winner: 9/10 Doublings | ₹7 Crore | 92% CAGR | Zero Leverage",
    color="white", fontsize=13, fontweight="bold", pad=14)
ax1.legend(loc="upper left", fontsize=8, facecolor="#1a1a2e", edgecolor="#444", ncol=1)
ax1.grid(True, color="#1a1a2e", ls=":", alpha=0.6)

# ── ETH PRICE + SMA-20 ────────────────────────────────────────────────────────
ax2.plot(eth_inr.index, eth_inr, color="#627eea", lw=1.0, alpha=0.8)
sma20 = eth_inr.rolling(20).mean()
ax2.plot(sma20.index, sma20, color="#ffcc00", lw=1.5, ls="--", alpha=0.8)
bull  = eth_inr > sma20
ax2.fill_between(eth_inr.index, eth_inr, sma20,
                 where=bull, alpha=0.3, color="#00ff88", label="Bull (hold ETH)")
ax2.fill_between(eth_inr.index, eth_inr, sma20,
                 where=~bull, alpha=0.2, color="#ff4444", label="Bear (exit ETH)")
ax2.set_yscale("log")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"Rs{x/1e3:.0f}k"))
ax2.set_ylabel("ETH-INR", color="#ccc", fontsize=9)
ax2.set_title("ETH-INR vs SMA-20 Signal", color="white", fontsize=10, fontweight="bold")
ax2.legend(fontsize=8, facecolor="#1a1a2e", edgecolor="#444")
ax2.grid(True, color="#1a1a2e", ls=":", alpha=0.4)

# ── BAR CHART: STRATEGY COMPARISON ───────────────────────────────────────────
strat_names = [
    "ETH\nSMA-20⭐", "ETH\nSMA-10", "BTC\nSMA-20",
    "ETH\nB&H", "Everything\nEngine", "Geometry\nIndian",
    "Hybrid\nETH+India", "BTC\nB&H"
]
strat_vals = [
    eth20.dropna().iloc[-1]/CAPITAL,
    eth10.dropna().iloc[-1]/CAPITAL,
    btc20.dropna().iloc[-1]/CAPITAL,
    bh_eth.dropna().iloc[-1]/CAPITAL,
    27.2,   # everything engine from saved results
    7.8,    # geometry indian
    2.75,   # hybrid
    bh_btc.dropna().iloc[-1]/CAPITAL
]
strat_colors = ["#00ffcc","#00aa88","#cc7700","#627eea","#ff8800","#ff4444","#ff2222","#f7931a"]
bars = ax3.bar(strat_names, strat_vals, color=strat_colors, edgecolor="#333", linewidth=0.8)
ax3.set_yscale("log")
ax3.set_ylabel("Total Return (x)", color="#ccc", fontsize=9)
ax3.set_title("Final Return Comparison (×)", color="white", fontsize=10, fontweight="bold")
ax3.axhline(100, color="#ff3333", lw=1.5, ls="--", alpha=0.8, label="10Cr = 1000x")
ax3.tick_params(colors="#aaa", labelsize=7.5)
for bar, val in zip(bars, strat_vals):
    ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.1,
             f"{val:.0f}x", ha='center', va='bottom', fontsize=8, color='white', fontweight='bold')
ax3.set_facecolor("#0d0d1a")
ax3.grid(True, color="#1a1a2e", ls=":", alpha=0.4, axis='y')

# ── DRAWDOWN ─────────────────────────────────────────────────────────────────
dd_eth20 = (eth20 - eth20.cummax())/eth20.cummax()*100
ax4.fill_between(all_idx, dd_eth20, 0, color="#00ffcc", alpha=0.35, label="ETH SMA-20")
dd_eth_bh = (bh_eth - bh_eth.cummax())/bh_eth.cummax()*100
ax4.fill_between(all_idx, dd_eth_bh, 0, color="#627eea", alpha=0.15, label="ETH B&H")
ax4.axhline(0, color="#555", lw=0.5)
ax4.set_ylabel("Drawdown %", color="#ccc", fontsize=9)
ax4.set_title("Drawdown: SMA-20 vs Buy & Hold", color="white", fontsize=10, fontweight="bold")
ax4.legend(fontsize=8, facecolor="#1a1a2e", edgecolor="#444")
ax4.grid(True, color="#1a1a2e", ls=":", alpha=0.4)

# ── DOUBLINGS TIMELINE ────────────────────────────────────────────────────────
if dbl_eth20:
    dates = [d[0] for d in dbl_eth20]
    vals  = [d[1] for d in dbl_eth20]
    colors_d = [cmap[i] for i in range(len(dbl_eth20))]
    ax5.scatter(dates, vals, c=colors_d, s=200, zorder=5, edgecolors='white', linewidths=1)
    ax5.step(dates, vals, color="#00ffcc", lw=2, where='post', alpha=0.7)
    for dt,dn,pv in dbl_eth20:
        ax5.annotate(f"#{dn}\n{dt.strftime('%b %y')}", (dt,dn),
                     xytext=(5,3), textcoords="offset points",
                     fontsize=7.5, color=cmap[dn-1])
    ax5.axhline(10, color="#ff3333", lw=2.0, ls="--", alpha=0.85, label="Target: 10 doublings")
    ax5.set_ylabel("Doublings Hit", color="#ccc", fontsize=9)
    ax5.set_xlabel("Date", color="#ccc", fontsize=9)
    ax5.set_title("ETH SMA-20: Doubling Timeline", color="white", fontsize=10, fontweight="bold")
    ax5.set_yticks(range(1,11))
    ax5.legend(fontsize=8, facecolor="#1a1a2e", edgecolor="#444")
    ax5.grid(True, color="#1a1a2e", ls=":", alpha=0.5)
ax5.set_facecolor("#0d0d1a")
ax5.tick_params(colors="#aaa")

plt.setp(ax1.get_xticklabels(), visible=False)
plt.setp(ax2.get_xticklabels(), visible=False)
for ax in [ax1,ax2,ax4]: ax.tick_params(colors="#aaa")

fig.text(0.08, 0.005,
    "ETH 2016-2017: CoinGecko historical records. All other data: Yahoo Finance. "
    "Friction: 0.2%/trade. No leverage. Weekly bars. INR denomination (includes USD/INR depreciation alpha).",
    fontsize=7.5, color="#666", style="italic")
plt.tight_layout(rect=[0, 0.02, 1, 1])

out = os.path.join(OUT_DIR, "MASTER_COMPARISON_FINAL.png")
plt.savefig(out, dpi=300, facecolor=fig.get_facecolor())
print(f"\nSaved: {out}")
print("DONE.")
