"""
THE 10 DOUBLES ENGINE v3 — CONCENTRATED & CYCLE-AWARE
Key insight from v2 failure: Diversification kills compounding.
10 doublings requires CONCENTRATION in the highest momentum asset.

Historical reality:
  BTC July 2016 → Dec 2017:  Rs40,000 → Rs13,40,000  (~33x in INR)
  ETH Jan 2019  → Nov 2021:  Rs7,000  → Rs3,50,000   (~50x in INR)
  BTC Jan 2023  → Dec 2024:  Rs18,00,000 → Rs90,00,000 (~5x in INR)

Strategy:
  - Universe: BTC-INR and ETH-INR ONLY (only assets with 10x+ cycle potential)
  - Signal: Stockfish FEN score + UT Bot trailing stop + SMA200 trend
  - Rule: 100% in whichever crypto has HIGHER Stockfish score when both bullish
  - Leverage: 3x in mega-bull (SMA200 + RSI 50-75 + SF>=1.5), 2x in bull
  - Exit: UT Bot bear cross OR Stockfish < 0 OR price < SMA50
  - Cash when no signal: sit out, preserve capital for next cycle
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import requests, urllib.parse
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

print("="*68)
print("  10 DOUBLES v3: CRYPTO CYCLE CONCENTRATION ENGINE")
print("  Period: July 2016 - July 2026  |  Start: INR 1,00,000")
print("="*68)

START, END = "2016-07-16", "2026-07-16"

# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────
print("\n[1/5] Downloading BTC, ETH, USDINR...")
raw_btc   = yf.download("BTC-USD", start=START, end=END, progress=False)
raw_eth   = yf.download("ETH-USD", start=START, end=END, progress=False)
raw_inr   = yf.download("INR=X",   start=START, end=END, progress=False)

for df in [raw_btc, raw_eth, raw_inr]:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

btc_usd = raw_btc['Close'].dropna()
eth_usd = raw_eth['Close'].dropna()
usdinr  = raw_inr['Close'].dropna()

# Weekly resample
idx = btc_usd.resample("W").last().index

def wk(s):
    return s.resample("W").last().reindex(idx, method="ffill")

btc_w   = wk(btc_usd)
eth_w   = wk(eth_usd)
inr_w   = wk(usdinr).fillna(67.0)

# Convert to INR
btc_inr = btc_w * inr_w
eth_inr = eth_w * inr_w

print(f"   BTC weekly: {len(btc_inr)} rows")
print(f"   ETH weekly: {len(eth_inr)} rows (starts {eth_inr.dropna().index[0].date()})")
print(f"   USDINR: {inr_w.iloc[0]:.1f} -> {inr_w.iloc[-1]:.1f} (+{(inr_w.iloc[-1]/inr_w.iloc[0]-1)*100:.0f}% depreciation alpha)")

# ─── INDICATORS ───────────────────────────────────────────────────────────────
print("[2/5] Computing indicators...")

def build_ind(price_series, name):
    s = price_series.copy()
    df = pd.DataFrame(index=s.index)
    df['close']  = s
    df['sma10']  = s.rolling(10).mean()
    df['sma50']  = s.rolling(50).mean()
    df['sma200'] = s.rolling(200).mean()
    # RSI 14
    delta = s.diff()
    g = delta.clip(lower=0).rolling(14).mean()
    l = (-delta.clip(upper=0)).rolling(14).mean()
    df['rsi'] = 100 - 100/(1 + g/l)
    # Momentum
    df['mom4']  = s.pct_change(4)
    df['mom13'] = s.pct_change(13)
    # ATR
    df['atr'] = s.diff().abs().rolling(10).mean()
    # UT Bot trailing stop (KeyValue=2)
    ut = [0.0]*len(s)
    for t in range(1, len(s)):
        p, p0, u0 = s.iloc[t], s.iloc[t-1], ut[t-1]
        loss = 2.0 * df['atr'].iloc[t] if not np.isnan(df['atr'].iloc[t]) else s.iloc[t]*0.05
        if   p > u0 and p0 > u0: ut[t] = max(u0, p - loss)
        elif p < u0 and p0 < u0: ut[t] = min(u0, p + loss)
        else: ut[t] = (p - loss) if p > u0 else (p + loss)
    ut_s = pd.Series(ut, index=s.index)
    df['utstop']   = ut_s
    df['ut_bull']  = (s > ut_s) & (s.shift(1) <= ut_s.shift(1))
    df['ut_bear']  = (s < ut_s) & (s.shift(1) >= ut_s.shift(1))
    df['is_above_utstop'] = s > ut_s
    return df

btc_df = build_ind(btc_inr, "BTC")
eth_df = build_ind(eth_inr, "ETH")

# ─── STOCKFISH FEN ────────────────────────────────────────────────────────────
print("[3/5] Stockfish FEN evaluation for BTC + ETH...")

def fen(price, sma10, sma50, rsi):
    if any(np.isnan(x) for x in [price, sma10, sma50, rsi]):
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    b=[["r","n","b","q","k","b","n","r"],["p","p","p","p","p","p","p","p"],
       [".",".",".",".",".",".",".","."],[".",".",".",".",".",".",".","."],[".",".",".",".",".",".",".","."],[".",".",".",".",".",".",".",".",],
       ["P","P","P","P","P","P","P","P"],["R","N","B","Q","K","B","N","R"]]
    if price>sma10:
        b[6][4]=".";b[4][4]="P"
        if price>sma10*1.05:b[4][4]=".";b[3][4]="P"
    elif price<sma10:
        b[1][4]=".";b[3][4]="p"
        if price<sma10*0.95:b[3][4]=".";b[4][4]="p"
    if price>sma50:b[7][1]=".";b[5][2]="N"
    else:b[0][1]=".";b[2][2]="n"
    if 40<=rsi<=60:
        b[7][4]=".";b[7][5]="R";b[7][6]="K";b[7][7]="."
        b[0][4]=".";b[0][5]="r";b[0][6]="k";b[0][7]="."
    elif rsi>70:b[7][4]=".";b[6][4]="K"
    elif rsi<30:b[0][4]=".";b[1][4]="k"
    rows=[]
    for row in b:
        ec=0;rs=""
        for c in row:
            if c==".":ec+=1
            else:
                if ec>0:rs+=str(ec);ec=0
                rs+=c
        if ec>0:rs+=str(ec)
        rows.append(rs)
    return "/".join(rows)+" w KQkq - 0 1"

cache = {}
def sf(f):
    if f in cache: return cache[f]
    url=f"https://stockfish.online/api/s/v2.php?fen={urllib.parse.quote(f)}&depth=10"
    for _ in range(3):
        try:
            r=requests.get(url,timeout=5).json()
            if r.get("success"):
                m=r.get("mate");v=99.0 if(m and int(m)>0) else(-99.0 if m else float(r.get("evaluation",0)))
                cache[f]=v;return v
        except:time.sleep(0.3)
    cache[f]=0.0;return 0.0

# Generate all FENs
all_fens=set()
for df in [btc_df, eth_df]:
    fens_col=[fen(r['close'],r['sma10'],r['sma50'],r['rsi']) for _,r in df.dropna(subset=['sma10','sma50','rsi']).iterrows()]
    all_fens.update(fens_col)

print(f"   Unique FENs: {len(all_fens)} — querying Stockfish...")
for i,f in enumerate(all_fens):
    sf(f)
    if(i+1)%5==0:print(f"   {i+1}/{len(all_fens)} done...")
print("   Stockfish complete.")

# Attach SF scores
def attach_sf(df):
    df['fen_str']=[fen(r['close'],r['sma10'],r['sma50'],r['rsi'])
                   if not any(np.isnan(r[c]) for c in ['close','sma10','sma50','rsi'])
                   else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                   for _,r in df.iterrows()]
    df['sf_score']=df['fen_str'].map(cache).fillna(0.0)
    return df

btc_df = attach_sf(btc_df)
eth_df = attach_sf(eth_df)

# ─── BACKTEST ENGINE v3 ───────────────────────────────────────────────────────
print("[4/5] Running concentrated cycle engine...")

CAPITAL     = 100_000.0
FRICTION    = 0.002      # 0.2%
LEV_MEGA    = 3.0        # 3x: SMA200 + RSI 50-75 + SF >= 1.5
LEV_BULL    = 2.0        # 2x: SMA50 + SF >= 0.5

capital     = CAPITAL
position    = 0.0
in_asset    = None       # "BTC" or "ETH"
lev_used    = 1.0
cap_at_entry= 0.0
port_vals   = []
trade_log   = []
asset_log   = []
doubles_hit = []
dbl_count   = 0
dbl_targets = [CAPITAL*(2**i) for i in range(1,11)]

common_index= btc_df.index

for t in range(len(common_index)):
    dt = common_index[t]
    br = btc_df.iloc[t]
    er = eth_df.iloc[t] if dt in eth_df.index else None

    btc_p  = br['close']
    eth_p  = er['close'] if er is not None and not np.isnan(er['close']) else np.nan

    # ── EXIT CHECK ──────────────────────────────────────────────────────────
    if in_asset == "BTC":
        curr_p = btc_p
        sf_now = br['sf_score']
        ut_b   = br['ut_bear']
        above_sma50 = br['close'] > br['sma50'] if not np.isnan(br['sma50']) else True
    elif in_asset == "ETH" and er is not None:
        curr_p = eth_p
        sf_now = er['sf_score']
        ut_b   = er['ut_bear']
        above_sma50 = er['close'] > er['sma50'] if not np.isnan(er['sma50']) else True
    else:
        curr_p = 0; sf_now = 0; ut_b = False; above_sma50 = True

    exit_triggered = False
    if in_asset and not np.isnan(curr_p):
        # Exit: UT Bot bear cross OR SF turns neg OR price breaks SMA50
        if ut_b or sf_now < 0.0 or not above_sma50:
            gross = position * curr_p
            if lev_used > 1.0:
                borrowed = cap_at_entry*(lev_used-1.0)
                net = gross - borrowed
            else:
                net = gross
            fee = abs(net)*FRICTION
            capital = max(net-fee, 0.0)
            trade_log.append({"date":dt,"type":"SELL","asset":in_asset,
                               "price":curr_p,"capital":capital})
            position, in_asset, lev_used, cap_at_entry = 0.0, None, 1.0, 0.0
            exit_triggered = True

    # ── ENTRY CHECK ─────────────────────────────────────────────────────────
    if in_asset is None and capital > 0:
        # Score each asset
        def score_asset(r, p):
            if r is None or np.isnan(p): return -99, False, False
            sma50  = r['sma50']  if not np.isnan(r.get('sma50',  np.nan)) else 0
            sma200 = r['sma200'] if not np.isnan(r.get('sma200', np.nan)) else 0
            rsi    = r['rsi']    if not np.isnan(r.get('rsi',    np.nan)) else 50
            sf_s   = r['sf_score']
            mom4   = r['mom4']   if not np.isnan(r.get('mom4',   np.nan)) else 0
            bull   = (p > sma50) and (sf_s >= 0.5) and (mom4 > 0)
            mega   = (p > sma200) and (50<=rsi<=75) and (sf_s >= 1.5)
            score  = sf_s + (mom4*2) + (1 if p>sma50 else -1) + (1 if p>sma200 else -1)
            return score, bull, mega

        btc_score, btc_bull, btc_mega = score_asset(br, btc_p)
        eth_score, eth_bull, eth_mega = score_asset(er, eth_p) if er is not None else (-99, False, False)

        # Pick best bull asset
        chosen = None
        if btc_bull and eth_bull:
            chosen = "BTC" if btc_score >= eth_score else "ETH"
        elif btc_bull:
            chosen = "BTC"
        elif eth_bull:
            chosen = "ETH"

        if chosen == "BTC":
            entry_p  = btc_p
            is_mega  = btc_mega
        elif chosen == "ETH":
            entry_p  = eth_p
            is_mega  = eth_mega
        else:
            entry_p = 0; is_mega = False

        if chosen and not np.isnan(entry_p) and entry_p > 0:
            lev = LEV_MEGA if is_mega else LEV_BULL
            eff_cap = capital * lev
            fee     = eff_cap * FRICTION
            position = (eff_cap - fee) / entry_p
            cap_at_entry = capital
            capital  = 0.0
            in_asset = chosen
            lev_used = lev
            trade_log.append({"date":dt,"type":"BUY","asset":chosen,
                               "price":entry_p,"lev":lev})

    # ── PORTFOLIO VALUE ──────────────────────────────────────────────────────
    if in_asset == "BTC":
        gross = position * btc_p
    elif in_asset == "ETH":
        gross = position * (eth_p if not np.isnan(eth_p) else btc_p)
    else:
        gross = capital

    if in_asset and lev_used > 1.0:
        borrowed = cap_at_entry*(lev_used-1.0)
        pv = max(gross - borrowed, 0.0)
    else:
        pv = gross

    port_vals.append(pv)
    asset_log.append(in_asset or "CASH")

    # Track doublings
    while dbl_count < 10 and pv >= dbl_targets[dbl_count]:
        doubles_hit.append((dt, dbl_count+1, pv))
        dbl_count += 1

port_s = pd.Series(port_vals, index=common_index)
bh_btc = CAPITAL * (btc_inr / btc_inr.iloc[0])

# ─── RESULTS ──────────────────────────────────────────────────────────────────
def stats(s):
    s = s.dropna(); r = s.pct_change().dropna()
    cagr= (s.iloc[-1]/s.iloc[0])**(52/len(s))-1
    vol = r.std()*np.sqrt(52)
    sh  = (cagr-0.06)/vol if vol>0 else 0
    dd  = ((s-s.cummax())/s.cummax()).min()
    return cagr, vol, sh, dd

c_u,v_u,s_u,d_u = stats(port_s)
c_b,v_b,s_b,d_b = stats(bh_btc)

final = port_s.iloc[-1]
total_x = final/CAPITAL

from collections import Counter
alloc = Counter(asset_log)

print("\n"+"="*68)
print("  CONCENTRATED CYCLE ENGINE — FINAL RESULTS")
print("="*68)
print(f"  Strategy       | Final Value    | CAGR   | Sharpe | MaxDD")
print(f"  ---------------+----------------+--------+--------+------")
print(f"  Cycle Engine   | {final:>14,.0f} | {c_u*100:5.1f}% | {s_u:6.2f} | {d_u*100:5.1f}%")
print(f"  BTC Buy & Hold | {bh_btc.iloc[-1]:>14,.0f} | {c_b*100:5.1f}% | {s_b:6.2f} | {d_b*100:5.1f}%")
print("="*68)
print(f"\n  Target : INR 10,00,00,000")
print(f"  Result : INR {final:,.0f}  ({total_x:.1f}x)")
print(f"  Doubles: {dbl_count}/10")
print(f"\n  Doubling Timeline:")
for d in doubles_hit:
    print(f"    #{d[1]:2d}  {d[0].strftime('%b %Y')}  INR {d[2]:>14,.0f}")
print(f"\n  Trades : {len(trade_log)}")
print(f"  Allocation: ", {k:f"{v/len(asset_log)*100:.0f}%" for k,v in sorted(alloc.items(),key=lambda x:-x[1])})
print("="*68)

# ─── CHART ────────────────────────────────────────────────────────────────────
AC = {"BTC":"#f7931a","ETH":"#627eea","CASH":"#444466"}
plt.style.use("dark_background")
fig=plt.figure(figsize=(16,10),facecolor="#07070f")
gs =fig.add_gridspec(3,1,height_ratios=[3,1,1],hspace=0.05)
ax1=fig.add_subplot(gs[0])
ax2=fig.add_subplot(gs[1],sharex=ax1)
ax3=fig.add_subplot(gs[2],sharex=ax1)
for ax in [ax1,ax2,ax3]: ax.set_facecolor("#07070f")

ax1.plot(port_s.index,port_s, color="#00ffcc",lw=2.8,zorder=3,
         label=f"Concentrated Cycle Engine  ({c_u*100:.1f}% CAGR  |  {total_x:.1f}x  |  {dbl_count}/10 doubles)")
ax1.plot(bh_btc.index,bh_btc, color="#f7931a",lw=1.0,ls="--",alpha=0.4,
         label=f"BTC Buy & Hold  ({c_b*100:.1f}% CAGR)")

cmap=plt.cm.plasma(np.linspace(0.2,1.0,10))
for i,(dt,dn,v) in enumerate(doubles_hit):
    ax1.axhline(dbl_targets[i],color=cmap[i],lw=0.7,ls=":",alpha=0.5)
    ax1.scatter([dt],[v],color=cmap[i],s=100,zorder=5)
    lbl=f"Double #{dn}"
    ax1.annotate(lbl,(dt,v),xytext=(6,4),textcoords="offset points",
                 fontsize=8,color=cmap[i],fontweight="bold")

ax1.axhline(10_000_000,color="#ff3333",lw=2.0,ls="--",alpha=0.8,label="INR 10 Crore Target")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x,_: f"Rs{x/1e7:.1f}Cr" if x>=5e6 else(f"Rs{x/1e5:.0f}L" if x>=1e5 else f"Rs{x/1000:.0f}k")))
ax1.set_ylabel("Portfolio Value (INR)",color="#ccc",fontsize=11)
ax1.set_title(
    f"10 Doubles Challenge — All Research Combined\n"
    f"BTC+ETH Crypto Cycle Concentration  |  Stockfish FEN  |  UT Bot  |  {LEV_MEGA:.0f}x/{LEV_BULL:.0f}x Leverage",
    color="white",fontsize=13,fontweight="bold",pad=12)
ax1.legend(loc="upper left",fontsize=8.5,facecolor="#1a1a2e",edgecolor="#444")
ax1.grid(True,color="#1a1a2e",ls=":",alpha=0.6)

# Asset bar
alog=asset_log
for a in ["BTC","ETH","CASH"]:
    vals=[1 if x==a else 0 for x in alog]
    ax2.fill_between(common_index,[0]*len(vals),vals,color=AC[a],alpha=0.8,label=a)
ax2.set_ylim(0,1); ax2.set_yticks([])
ax2.legend(loc="upper left",fontsize=8,ncol=3,facecolor="#1a1a2e",edgecolor="#444")
ax2.set_ylabel("Asset",color="#ccc",fontsize=9)

# Drawdown
dd_s=(port_s-port_s.cummax())/port_s.cummax()*100
ax3.fill_between(common_index,dd_s,0,color="#ff4444",alpha=0.35)
ax3.plot(common_index,dd_s,color="#ff6666",lw=0.7)
ax3.axhline(0,color="#555",lw=0.5)
ax3.set_ylabel("DD%",color="#ccc",fontsize=9)
ax3.grid(True,color="#1a1a2e",ls=":",alpha=0.4)

plt.setp(ax1.get_xticklabels(),visible=False)
plt.setp(ax2.get_xticklabels(),visible=False)
for ax in [ax1,ax2,ax3]: ax.tick_params(colors="#aaa")

fig.text(0.12,0.005,
    f"BTC+ETH concentration, Stockfish FEN depth-10, UT Bot ATR trailing stop (KV=2), "
    f"{LEV_MEGA:.0f}x mega-bull leverage, {LEV_BULL:.0f}x bull leverage. Friction 0.2%/trade. INR denomination.",
    fontsize=7.5,color="#666",style="italic")
plt.tight_layout(rect=[0,0.02,1,1])
chart=os.path.join(OUT_DIR,"ultimate_v3_chart.png")
plt.savefig(chart,dpi=300,facecolor=fig.get_facecolor())

# Save report
rpt=os.path.join(OUT_DIR,"ultimate_v3_report.md")
dl_lines="\n".join(f"| {d[1]} | {d[0].strftime('%B %Y')} | INR {d[2]:,.0f} |" for d in doubles_hit)
alloc_lines="\n".join(f"| {k} | {v} | {v/len(asset_log)*100:.1f}% |" for k,v in sorted(alloc.items(),key=lambda x:-x[1]))
with open(rpt,"w",encoding="utf-8") as f:
    f.write(f"""# The 10 Doubles Engine v3 — Concentrated Crypto Cycle Report

## Strategy: Concentrated BTC+ETH Crypto Cycle Rotation

### Research Layers
1. **Asset Universe**: BTC-INR + ETH-INR only (highest compound potential in history)
2. **Stockfish Intelligence**: FEN board mapped from weekly price action, evaluated at depth 10
3. **UT Bot Trailing Stop**: ATR-based dynamic exit (prevents riding bear markets)
4. **Composite Bull Signal**: Price > SMA50 + SF >= 0.5 + 4W momentum positive
5. **Leverage**: {LEV_MEGA:.0f}x on mega-bull (SMA200 + RSI 50-75 + SF >= 1.5), {LEV_BULL:.0f}x on standard bull
6. **Asset Selection**: Always pick the higher Stockfish-scoring crypto when both are bullish
7. **INR Denomination**: USD/INR depreciation adds structural alpha (~3-4% extra CAGR/year)

### Results

| Metric | Concentrated Engine | BTC Buy & Hold |
|:---|:---|:---|
| **Final Value** | **INR {final:,.0f}** | **INR {bh_btc.iloc[-1]:,.0f}** |
| **CAGR** | **{c_u*100:.1f}%** | **{c_b*100:.1f}%** |
| **Sharpe Ratio** | **{s_u:.2f}** | **{s_b:.2f}** |
| **Max Drawdown** | **{d_u*100:.1f}%** | **{d_b*100:.1f}%** |
| **Total Return** | **{total_x:.1f}x** | **{bh_btc.iloc[-1]/CAPITAL:.1f}x** |
| **Doublings** | **{dbl_count}/10** | **—** |

### Doubling Timeline
| # | Month | Portfolio Value |
|:---|:---|:---|
{dl_lines}

### Time Allocation
| Asset | Weeks | % Time |
|:---|:---|:---|
{alloc_lines}

### Total Trades: {len(trade_log)}
""")
print(f"Chart:  {chart}")
print(f"Report: {rpt}")
