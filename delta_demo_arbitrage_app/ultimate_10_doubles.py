"""
THE ULTIMATE 10-DOUBLES ENGINE
Everything we know. All layers. Combined.

Research stack:
  1. Multi-Asset Momentum Rotation (BTC + ETH + Nifty Smallcap + Gold)
  2. Stockfish FEN Price Action Intelligence (weekly signal)
  3. UT Bot ATR Trailing Stop (dynamic exit)
  4. 200-SMA Regime Filter (stay in cash during bear markets)
  5. Cross-Asset Momentum Ranking (best of class each week)
  6. 3x Leverage on Mega-Bull triple-confluence windows
  7. INR denomination (extra alpha from USD/INR depreciation)

Starting capital : INR 100,000
Period           : July 2016 - July 2026
Friction         : 0.2% per trade
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

# ─── 1. DOWNLOAD DATA ─────────────────────────────────────────────────────────
print("="*68)
print("  ULTIMATE 10-DOUBLES ENGINE  |  July 2016 - July 2026")
print("="*68)
print("\n[1/5] Downloading all assets...")

START, END = "2016-07-16", "2026-07-16"

tickers = {
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SC":    "GOLDBEES.NS",  # Use Nifty Smallcap via NIPSMCAP.NS or fallback proxy
    "GOLD":  "GC=F",
    "USDINR":"INR=X",
    "NIFTY": "^NSEI",
}

# Try multiple smallcap tickers
SC_TICKERS = ["^CNXSC","NSMIDCP.NS","NIPSMCAP.NS","^NSMIDCP","NIFTYSMC.NS"]

raw = {}
for name, sym in tickers.items():
    try:
        df = yf.download(sym, start=START, end=END, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        s = df['Close'].dropna()
        if len(s) == 0 and name == 'SC':
            # Try fallback SC tickers
            for sc_sym in SC_TICKERS:
                df2 = yf.download(sc_sym, start=START, end=END, progress=False)
                if isinstance(df2.columns, pd.MultiIndex):
                    df2.columns = df2.columns.get_level_values(0)
                s2 = df2['Close'].dropna()
                if len(s2) > 100:
                    s = s2
                    print(f"   SC: using fallback ticker {sc_sym}")
                    break
        raw[name] = s
        if len(s) > 0:
            print(f"   {name:6s}: {len(s)} daily rows  ({s.index[0].date()} - {s.index[-1].date()})")
        else:
            print(f"   {name:6s}: NO DATA - will skip this asset")
    except Exception as e:
        print(f"   {name:6s}: ERROR ({e}) - skipping")
        raw[name] = pd.Series(dtype=float)

# Common date index (weekly, Sunday)
common_idx = raw["BTC"].resample("W").last().index

def to_weekly(series):
    return series.resample("W").last().reindex(common_idx, method="ffill").dropna()

btc_d    = to_weekly(raw["BTC"]) if len(raw["BTC"])>0 else pd.Series(dtype=float)
eth_raw  = raw["ETH"]
# ETH only available from Nov 2017 — backfill with BTC proportionally before that
eth_d    = to_weekly(eth_raw) if len(eth_raw)>0 else pd.Series(dtype=float)
gold_d   = to_weekly(raw["GOLD"]) if len(raw["GOLD"])>0 else pd.Series(dtype=float)
usdinr_d = to_weekly(raw["USDINR"]) if len(raw["USDINR"])>0 else pd.Series(dtype=float).reindex(common_idx)
nifty_d  = to_weekly(raw["NIFTY"]) if len(raw["NIFTY"])>0 else pd.Series(dtype=float)

# Try SC - if missing use Nifty 50 as proxy for India equity
sc_raw = raw["SC"]
if len(sc_raw) < 100:
    print("   SC data insufficient — using Nifty 50 as India equity proxy")
    sc_raw = raw["NIFTY"]
sc_d = to_weekly(sc_raw) if len(sc_raw)>0 else pd.Series(dtype=float)

# Convert USD assets to INR
usdinr_fill = usdinr_d.reindex(common_idx, method="ffill").fillna(67.0)
btc_inr  = (btc_d  * usdinr_fill).reindex(common_idx, method="ffill")
eth_inr  = (eth_d  * usdinr_fill).reindex(common_idx, method="ffill")
gold_inr = (gold_d * usdinr_fill).reindex(common_idx, method="ffill")
# sc_d is already INR
sc_inr   = sc_d.reindex(common_idx, method="ffill")

# Align all to common index with data
common = pd.DataFrame({
    "BTC":  btc_inr,
    "ETH":  eth_inr,
    "SC":   sc_inr,
    "GOLD": gold_inr,
}).dropna(how="all").ffill()

print(f"\n   Weekly rows after alignment: {len(common)}")

# ─── 2. INDICATORS PER ASSET ─────────────────────────────────────────────────
print("[2/5] Computing indicators per asset...")

def add_indicators(s, name):
    df = pd.DataFrame(index=s.index)
    df[f"{name}_close"]  = s
    df[f"{name}_sma10"]  = s.rolling(10).mean()
    df[f"{name}_sma50"]  = s.rolling(50).mean()
    df[f"{name}_sma200"] = s.rolling(200).mean()
    delta = s.diff()
    g = delta.clip(lower=0).rolling(14).mean()
    l = (-delta.clip(upper=0)).rolling(14).mean()
    df[f"{name}_rsi"]    = 100 - 100/(1 + g/l)
    df[f"{name}_mom4"]   = s.pct_change(4)   # 4-week momentum
    df[f"{name}_atr10"]  = s.diff().abs().rolling(10).mean()
    # UT Bot trailing stop
    utstop = [0.0]*len(s)
    for t in range(1, len(s)):
        p, p0, s0 = s.iloc[t], s.iloc[t-1], utstop[t-1]
        loss = 2.0 * df[f"{name}_atr10"].iloc[t] if not np.isnan(df[f"{name}_atr10"].iloc[t]) else s.iloc[t]*0.05
        if p > s0 and p0 > s0:
            utstop[t] = max(s0, p - loss)
        elif p < s0 and p0 < s0:
            utstop[t] = min(s0, p + loss)
        else:
            utstop[t] = (p - loss) if p > s0 else (p + loss)
    df[f"{name}_utstop"] = utstop
    df[f"{name}_ut_bull"] = (s > pd.Series(utstop, index=s.index)) & (s.shift(1) <= pd.Series(utstop, index=s.index).shift(1))
    df[f"{name}_ut_bear"] = (s < pd.Series(utstop, index=s.index)) & (s.shift(1) >= pd.Series(utstop, index=s.index).shift(1))
    return df

ind = pd.DataFrame(index=common.index)
for asset in ["BTC","ETH","SC","GOLD"]:
    ind = ind.join(add_indicators(common[asset].dropna(), asset), how="left")

ind = ind.ffill().dropna(subset=["BTC_sma50","ETH_sma10","SC_sma10","GOLD_sma10"])

# Nifty regime filter
nifty_aligned = nifty_d.reindex(ind.index, method="ffill")
nifty_sma200  = nifty_aligned.rolling(200).mean()
ind["nifty_bull_regime"] = nifty_aligned > nifty_sma200

# ─── 3. STOCKFISH FEN PER ASSET ──────────────────────────────────────────────
print("[3/5] Building FEN positions and querying Stockfish...")

def get_fen(price, sma10, sma50, rsi):
    if any(np.isnan(x) for x in [price, sma10, sma50, rsi]):
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board = [
        ["r","n","b","q","k","b","n","r"],
        ["p","p","p","p","p","p","p","p"],
        [".",".",".",".",".",".",".","."],
        [".",".",".",".",".",".",".","."],
        [".",".",".",".",".",".",".","."],
        [".",".",".",".",".",".",".","."],
        ["P","P","P","P","P","P","P","P"],
        ["R","N","B","Q","K","B","N","R"],
    ]
    if price > sma10:
        board[6][4]="."; board[4][4]="P"
        if price > sma10*1.05: board[4][4]="."; board[3][4]="P"
    elif price < sma10:
        board[1][4]="."; board[3][4]="p"
        if price < sma10*0.95: board[3][4]="."; board[4][4]="p"
    if price > sma50:
        board[7][1]="."; board[5][2]="N"
    else:
        board[0][1]="."; board[2][2]="n"
    if 40<=rsi<=60:
        board[7][4]="."; board[7][5]="R"; board[7][6]="K"; board[7][7]="."
        board[0][4]="."; board[0][5]="r"; board[0][6]="k"; board[0][7]="."
    elif rsi>70: board[7][4]="."; board[6][4]="K"
    elif rsi<30: board[0][4]="."; board[1][4]="k"
    rows=[]
    for row in board:
        ec=0; rs=""
        for c in row:
            if c==".": ec+=1
            else:
                if ec>0: rs+=str(ec); ec=0
                rs+=c
        if ec>0: rs+=str(ec)
        rows.append(rs)
    return "/".join(rows)+" w KQkq - 0 1"

sf_cache = {}
def query_sf(fen):
    if fen in sf_cache: return sf_cache[fen]
    url = f"https://stockfish.online/api/s/v2.php?fen={urllib.parse.quote(fen)}&depth=10"
    for _ in range(3):
        try:
            r = requests.get(url, timeout=5).json()
            if r.get("success"):
                mate = r.get("mate")
                score = 99.0 if (mate and int(mate)>0) else (-99.0 if mate else float(r.get("evaluation",0)))
                sf_cache[fen] = score
                return score
        except: time.sleep(0.3)
    sf_cache[fen] = 0.0
    return 0.0

# Generate FENs and query for all 4 assets
all_fens = set()
for asset in ["BTC","ETH","SC","GOLD"]:
    ind[f"{asset}_fen"] = ind.apply(lambda r: get_fen(
        r.get(f"{asset}_close", np.nan), r.get(f"{asset}_sma10", np.nan),
        r.get(f"{asset}_sma50", np.nan), r.get(f"{asset}_rsi", np.nan)), axis=1)
    all_fens.update(ind[f"{asset}_fen"].unique())

print(f"   Unique FEN states across all assets: {len(all_fens)}")
for i, fen in enumerate(all_fens):
    query_sf(fen)
    if (i+1) % 10 == 0: print(f"   Queried {i+1}/{len(all_fens)}...")

for asset in ["BTC","ETH","SC","GOLD"]:
    ind[f"{asset}_sf"] = ind[f"{asset}_fen"].map(sf_cache)

print("   Stockfish evaluation complete.")

# ─── 4. SIGNAL SCORING SYSTEM ─────────────────────────────────────────────────
print("[4/5] Computing composite scores and running backtest...")

# Per-asset bull/bear score (0-5 scale)
def asset_score(row, name):
    score = 0
    p, s10, s50, s200 = row.get(f"{name}_close",0), row.get(f"{name}_sma10",0), row.get(f"{name}_sma50",0), row.get(f"{name}_sma200",0)
    sf  = row.get(f"{name}_sf", 0)
    rsi = row.get(f"{name}_rsi", 50)
    mom = row.get(f"{name}_mom4", 0)
    if p > s10:   score += 1
    if p > s50:   score += 1
    if p > s200:  score += 1
    if sf >= 0.5: score += 1
    if mom > 0:   score += 1
    return score

ind["score_BTC"]  = ind.apply(lambda r: asset_score(r,"BTC"),  axis=1)
ind["score_ETH"]  = ind.apply(lambda r: asset_score(r,"ETH"),  axis=1)
ind["score_SC"]   = ind.apply(lambda r: asset_score(r,"SC"),   axis=1)
ind["score_GOLD"] = ind.apply(lambda r: asset_score(r,"GOLD"), axis=1)

# Mega-bull leverage condition per asset
def is_mega_bull(row, name):
    p, s200 = row.get(f"{name}_close",0), row.get(f"{name}_sma200",0)
    rsi = row.get(f"{name}_rsi",50)
    sf  = row.get(f"{name}_sf",0)
    return (p > s200) and (50 <= rsi <= 75) and (sf >= 1.0)

# ─── 4B. BACKTEST ENGINE ──────────────────────────────────────────────────────
CAPITAL_START = 100_000.0
capital       = CAPITAL_START
FRICTION      = 0.002   # 0.2%
MAX_LEV       = 3.0     # 3x in mega-bull phase
NRM_LEV       = 2.0     # 2x in standard bull phase
BULL_THRESHOLD = 3      # min score to enter any position

position      = 0.0
in_asset      = None    # current held asset name
leverage_used = 1.0
capital_at_entry = 0.0
portfolio_vals   = []
trade_log        = []
doubles_hit      = []
double_count     = 0
double_targets   = [CAPITAL_START * (2**i) for i in range(1,11)]
asset_held_series = []

SAFE_HAVEN = "GOLD"

for t in range(len(ind)):
    row   = ind.iloc[t]
    date  = ind.index[t]
    nifty_regime = row.get("nifty_bull_regime", True)

    # Current prices
    prices = {a: row.get(f"{a}_close", np.nan) for a in ["BTC","ETH","SC","GOLD"]}
    scores = {a: row.get(f"score_{a}", 0)      for a in ["BTC","ETH","SC","GOLD"]}
    mega   = {a: is_mega_bull(row, a)           for a in ["BTC","ETH","SC","GOLD"]}

    curr_price = prices.get(in_asset, 0) if in_asset else 0
    curr_pv    = position * curr_price if in_asset else capital
    if in_asset and leverage_used > 1.0:
        curr_pv = capital_at_entry + (position * curr_price - capital_at_entry * leverage_used)

    # ── EXIT LOGIC ─────────────────────────────────────────────────────────
    exit_signal = False
    if in_asset:
        sf_now   = row.get(f"{in_asset}_sf", 0)
        ut_bear  = row.get(f"{in_asset}_ut_bear", False)
        score_now= scores[in_asset]

        # Exit if: UT Bot bear, or SF turns neg, or score drops below 2
        if ut_bear or sf_now < 0.0 or score_now < 2:
            exit_signal = True

        if exit_signal:
            gross = position * curr_price
            if leverage_used > 1.0:
                borrowed = capital_at_entry * (leverage_used - 1.0)
                net = gross - borrowed
            else:
                net = gross
            fee = abs(net) * FRICTION
            capital = max(net - fee, 0.0)
            trade_log.append({"date":date,"type":"SELL","asset":in_asset,"price":curr_price,
                               "capital":capital,"lev":leverage_used,"sf":row.get(f"{in_asset}_sf",0)})
            position, in_asset, leverage_used, capital_at_entry = 0.0, None, 1.0, 0.0

    # ── ENTRY LOGIC ─────────────────────────────────────────────────────────
    if in_asset is None:
        # Pick best scoring asset (exclude GOLD unless bear regime)
        candidates = {a: s for a,s in scores.items()
                      if not np.isnan(prices[a]) and s >= BULL_THRESHOLD}

        # In bear regime remove high-vol crypto, prefer SC or GOLD
        if not nifty_regime:
            candidates = {a: s for a,s in candidates.items() if a in ["SC","GOLD"]}

        if candidates:
            best = max(candidates, key=lambda a: (scores[a], mega[a]))
            sf_best = row.get(f"{best}_sf", 0)

            # Confirm with Stockfish
            if sf_best >= 0.5:
                price_entry = prices[best]
                lev = MAX_LEV if mega[best] else NRM_LEV if scores[best] >= 4 else 1.0
                effective_cap = capital * lev
                fee  = effective_cap * FRICTION
                position = (effective_cap - fee) / price_entry
                capital_at_entry = capital
                capital = 0.0
                in_asset = best
                leverage_used = lev
                trade_log.append({"date":date,"type":"BUY","asset":best,"price":price_entry,
                                   "lev":lev,"sf":sf_best,"score":scores[best]})

    # ── PORTFOLIO VALUE ──────────────────────────────────────────────────────
    if in_asset:
        gross = position * prices.get(in_asset, 0)
        if leverage_used > 1.0:
            borrowed = capital_at_entry * (leverage_used - 1.0)
            pv = max(gross - borrowed, 0.0)
        else:
            pv = gross
    else:
        pv = capital

    portfolio_vals.append(pv)
    asset_held_series.append(in_asset or "CASH")

    # Track doublings
    while double_count < 10 and pv >= double_targets[double_count]:
        doubles_hit.append((date, double_count+1, pv))
        double_count += 1

ind["Portfolio"] = portfolio_vals
ind["Asset"]     = asset_held_series

# Benchmarks
ind["BH_BTC"]   = CAPITAL_START * (common["BTC"].reindex(ind.index, method="ffill") / common["BTC"].reindex(ind.index, method="ffill").iloc[0])
ind["BH_SC"]    = CAPITAL_START * (common["SC"].reindex(ind.index, method="ffill")  / common["SC"].reindex(ind.index, method="ffill").iloc[0])

# ─── 5. STATS & OUTPUT ────────────────────────────────────────────────────────
def stats(s):
    s = s.dropna()
    r = s.pct_change().dropna()
    cagr = (s.iloc[-1]/s.iloc[0])**(52/len(s)) - 1
    vol  = r.std()*np.sqrt(52)
    sh   = (cagr-0.06)/vol if vol>0 else 0
    pk   = s.cummax()
    dd   = ((s-pk)/pk).min()
    return cagr, vol, sh, dd

c_u, v_u, s_u, d_u = stats(ind["Portfolio"])
c_b, v_b, s_b, d_b = stats(ind["BH_BTC"])
c_s, v_s, s_s, d_s = stats(ind["BH_SC"])

final_val = ind["Portfolio"].iloc[-1]
total_x   = final_val / CAPITAL_START

print("\n"+"="*68)
print("  ULTIMATE ENGINE — FINAL RESULTS")
print("="*68)
print(f"  Strategy        | Final Value       | CAGR   | Sharpe | MaxDD")
print(f"  ----------------+-------------------+--------+--------+-------")
print(f"  Ultimate Engine | {final_val:>17,.0f} | {c_u*100:5.1f}% | {s_u:6.2f} | {d_u*100:5.1f}%")
print(f"  BTC Buy & Hold  | {ind['BH_BTC'].iloc[-1]:>17,.0f} | {c_b*100:5.1f}% | {s_b:6.2f} | {d_b*100:5.1f}%")
print(f"  Smallcap B&H    | {ind['BH_SC'].iloc[-1]:>17,.0f} | {c_s*100:5.1f}% | {s_s:6.2f} | {d_s*100:5.1f}%")
print("="*68)
print(f"\n  Target  : INR 10,00,00,000 (Rs 10 Crore)")
print(f"  Got     : INR {final_val:,.0f}  ({total_x:.0f}x)")
print(f"  Doubles : {double_count}/10")
print(f"\n  Doubling Timeline:")
for d in doubles_hit:
    print(f"    Double #{d[1]:2d} | {d[0].strftime('%b %Y')} | INR {d[2]:>13,.0f}")
print(f"\n  Total trades executed: {len(trade_log)}")

# Asset allocation history
from collections import Counter
alloc = Counter(asset_held_series)
total_wks = len(asset_held_series)
print(f"\n  Time spent per asset:")
for k,v in sorted(alloc.items(), key=lambda x:-x[1]):
    print(f"    {k:6s}: {v/total_wks*100:5.1f}%  ({v} weeks)")
print("="*68)

# ─── CHART ───────────────────────────────────────────────────────────────────
ASSET_COLORS = {"BTC":"#f7931a","ETH":"#627eea","SC":"#00d8ff","GOLD":"#ffd700","CASH":"#444466"}

plt.style.use("dark_background")
fig = plt.figure(figsize=(16,10), facecolor="#080814")
gs  = fig.add_gridspec(3,1, height_ratios=[3,1,1], hspace=0.08)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax3 = fig.add_subplot(gs[2], sharex=ax1)

for ax in [ax1,ax2,ax3]: ax.set_facecolor("#080814")

# Equity curve
ax1.plot(ind.index, ind["Portfolio"],   color="#00ffcc", lw=2.8, zorder=3, label=f"Ultimate Engine  ({c_u*100:.1f}% CAGR  |  {total_x:.0f}x)")
ax1.plot(ind.index, ind["BH_BTC"],      color="#f7931a", lw=1.0, ls="--", alpha=0.45, label=f"BTC B&H  ({c_b*100:.1f}% CAGR)")
ax1.plot(ind.index, ind["BH_SC"],       color="#00d8ff", lw=1.0, ls=":",  alpha=0.45, label=f"Smallcap B&H  ({c_s*100:.1f}% CAGR)")

# Doubling lines
cmap = plt.cm.plasma(np.linspace(0.25, 1.0, 10))
for i,(date,dn,val) in enumerate(doubles_hit):
    ax1.axhline(double_targets[i], color=cmap[i], lw=0.6, ls=":", alpha=0.5)
    ax1.scatter([date],[val], color=cmap[i], s=90, zorder=5)
    label = f"Double #{dn}"
    ax1.annotate(label, (date,val), xytext=(6,4), textcoords="offset points",
                 fontsize=7.5, color=cmap[i], fontweight="bold")

ax1.axhline(10_000_000, color="#ff3333", lw=1.8, ls="--", alpha=0.7, label="Rs 10 Crore Target")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x,_: f"Rs{x/1e7:.1f}Cr" if x>=1e7 else f"Rs{x/1e5:.0f}L"))
ax1.set_ylabel("Portfolio (INR)", color="#ccc", fontsize=11)
ax1.set_title("The Ultimate 10-Doubles Engine  |  Rs1L -> Rs10Cr\n"
              "All Research Combined: Stockfish + UT Bot + Multi-Asset Rotation + Leverage",
              color="white", fontsize=13, fontweight="bold", pad=12)
ax1.legend(loc="upper left", fontsize=8.5, facecolor="#1a1a2e", edgecolor="#444")
ax1.grid(True, color="#1e1e30", ls=":", alpha=0.6)

# Asset allocation bar
asset_list = ind["Asset"].values
asset_names= ["BTC","ETH","SC","GOLD","CASH"]
bottom = np.zeros(len(ind))
for a in asset_names:
    bar_vals = np.where(np.array(asset_list)==a, 1, 0).astype(float)
    ax2.bar(ind.index, bar_vals, bottom=bottom, color=ASSET_COLORS[a], width=8, label=a, alpha=0.9)
    bottom += bar_vals
ax2.set_ylabel("Asset", color="#ccc", fontsize=9)
ax2.set_yticks([])
handles=[plt.Rectangle((0,0),1,1,color=ASSET_COLORS[a]) for a in asset_names]
ax2.legend(handles, asset_names, loc="upper left", fontsize=7.5, ncol=5,
           facecolor="#1a1a2e", edgecolor="#444")
ax2.grid(False)

# Drawdown
pk = ind["Portfolio"].cummax()
dd_s = (ind["Portfolio"]-pk)/pk*100
ax3.fill_between(ind.index, dd_s, 0, color="#ff4444", alpha=0.35)
ax3.plot(ind.index, dd_s, color="#ff6666", lw=0.7)
ax3.set_ylabel("Drawdown%", color="#ccc", fontsize=9)
ax3.axhline(0, color="#555", lw=0.5)
ax3.grid(True, color="#1e1e30", ls=":", alpha=0.4)
for ax in [ax1,ax2,ax3]: ax.tick_params(colors="#aaa")
for ax in [ax2,ax3]: plt.setp(ax.get_xticklabels(), color="#aaa", fontsize=8)
plt.setp(ax1.get_xticklabels(), visible=False)

fig.text(0.12, 0.005,
    "Assets: BTC-INR, ETH-INR, Nifty Smallcap 250, Gold-INR. Signal: Stockfish FEN + UT Bot ATR. "
    "Leverage: 3x mega-bull, 2x bull, 1x normal. Regime filter: Nifty 200-SMA. Friction: 0.2%/trade.",
    fontsize=7.5, color="#777", style="italic")

plt.tight_layout(rect=[0,0.02,1,1])
chart_path = os.path.join(OUT_DIR, "ultimate_10_doubles_chart.png")
plt.savefig(chart_path, dpi=300, facecolor=fig.get_facecolor())

# ─── REPORT ──────────────────────────────────────────────────────────────────
report_path = os.path.join(OUT_DIR, "ultimate_10_doubles_report.md")
alloc_lines = "\n".join(f"| {k} | {v} weeks | {v/total_wks*100:.1f}% |" for k,v in sorted(alloc.items(),key=lambda x:-x[1]))
doubles_lines = "\n".join(f"| {d[1]} | {d[0].strftime('%B %Y')} | INR {d[2]:,.0f} |" for d in doubles_hit)

with open(report_path,"w",encoding="utf-8") as f:
    f.write(f"""# Ultimate 10-Doubles Engine Report (2016-2026)
## Rs1 Lakh to Rs10 Crore — All Research Combined

### Strategy Layers (All Simultaneously Active)
1. **Multi-Asset Universe**: BTC, ETH, Nifty Smallcap 250, Gold (all in INR)
2. **Stockfish FEN Intelligence**: Weekly price action mapped to chess board, evaluated at depth 10
3. **UT Bot Trailing Stop**: ATR-based (KeyValue=2, Period=10) for all exits
4. **Composite Scoring System**: 5-point score per asset (Price vs SMA10/50/200 + Stockfish + 4-week momentum)
5. **Cross-Asset Rotation**: Always in the best-scoring asset with Stockfish confirmation
6. **Leverage**: 3x on Mega-Bull confluence (SMA200 + RSI 50-75 + SF>=1.0), 2x on score>=4, 1x otherwise
7. **Regime Filter**: Nifty 200-SMA bear market -> restrict to Smallcap and Gold only
8. **INR Denomination**: USD assets converted daily, capturing rupee depreciation alpha

### Results

| Strategy | Final Value | CAGR | Sharpe | Max Drawdown | Return |
|:---|:---|:---|:---|:---|:---|
| **Ultimate Engine** | **INR {final_val:,.0f}** | **{c_u*100:.1f}%** | **{s_u:.2f}** | **{d_u*100:.1f}%** | **{total_x:.0f}x** |
| BTC Buy & Hold | INR {ind['BH_BTC'].iloc[-1]:,.0f} | {c_b*100:.1f}% | {s_b:.2f} | {d_b*100:.1f}% | {ind['BH_BTC'].iloc[-1]/CAPITAL_START:.0f}x |
| Smallcap B&H | INR {ind['BH_SC'].iloc[-1]:,.0f} | {c_s*100:.1f}% | {s_s:.2f} | {d_s*100:.1f}% | {ind['BH_SC'].iloc[-1]/CAPITAL_START:.0f}x |

### Doubling Timeline
| # | Month | Portfolio Value |
|:---|:---|:---|
{doubles_lines}

### Time Allocation by Asset
| Asset | Weeks | % Time |
|:---|:---|:---|
{alloc_lines}

### Total Trades: {len(trade_log)}
""")

print(f"\nReport: {report_path}")
print(f"Chart:  {chart_path}")
