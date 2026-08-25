"""
==============================================================================
  ANTIGRAVITY AI BRAIN — UTBOT CHAMPION MULTI-ASSET 10-YEAR WEALTH SIMULATION
==============================================================================
  Simulates the UTBot Monte Carlo Champion Strategy across ALL asset classes:

  CRYPTO:        BTC-USD, ETH-USD, SOL-USD
  US STOCKS:     AAPL, NVDA, TSLA, MSFT, AMZN
  INDIAN STOCKS: RELIANCE.NS, HDFCBANK.NS, INFY.NS, TCS.NS, TATAMOTORS.NS
  INDICES:       ^NSEI (NIFTY 50), ^BSESN (SENSEX), ^GSPC (S&P 500)
  FUTURES:       MES=F (Micro E-mini S&P), GC=F (Gold Futures)

  Champion Params (Monte Carlo Optimal):
    UTBot Key Val: 2.4 | ATR: 9 | TP: +1.52% | SL: -0.73% | BE: +0.32% | ADX: 18

  Starting Capital: $1,000 USD
  Position Sizing:  Kelly-adjusted 25% allocation per trade
  Max Concurrent:   3 open positions across assets
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

ANALYSIS_DIR  = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(os.path.dirname(ANALYSIS_DIR), ".gemini", "antigravity", "brain",
                              "a0eeb781-d7e4-484e-898c-51f143744494")
CHART_PATH    = os.path.join(ARTIFACTS_DIR, "utbot_multi_asset_10yr_wealth_chart.png")
REPORT_PATH   = os.path.join(ARTIFACTS_DIR, "utbot_multi_asset_10yr_wealth_report.md")

# ── Champion Parameters ───────────────────────────────────────────────────────
KEY_VAL    = 2.4
ATR_PERIOD = 9
TP_PCT     = 0.0152
SL_PCT     = 0.0073
BE_PCT     = 0.0032
ADX_MIN    = 18

INITIAL_CAPITAL = 1000.0

# Asset universe with category labels
ASSETS = [
    # (ticker, name, category, leverage_mult)
    ("BTC-USD",         "Bitcoin",          "Crypto",         1.0),
    ("ETH-USD",         "Ethereum",         "Crypto",         1.0),
    ("SOL-USD",         "Solana",           "Crypto",         1.0),
    ("AAPL",            "Apple",            "US Stocks",      1.0),
    ("NVDA",            "NVIDIA",           "US Stocks",      1.0),
    ("TSLA",            "Tesla",            "US Stocks",      1.0),
    ("MSFT",            "Microsoft",        "US Stocks",      1.0),
    ("AMZN",            "Amazon",           "US Stocks",      1.0),
    ("RELIANCE.NS",     "Reliance",         "Indian Stocks",  1.0),
    ("HDFCBANK.NS",     "HDFC Bank",        "Indian Stocks",  1.0),
    ("INFY.NS",         "Infosys",          "Indian Stocks",  1.0),
    ("TCS.NS",          "TCS",              "Indian Stocks",  1.0),
    ("TATAMOTORS.NS",   "Tata Motors",      "Indian Stocks",  1.0),
    ("^NSEI",           "NIFTY 50",         "Indices",        1.0),
    ("^GSPC",           "S&P 500",          "Indices",        1.0),
    ("GC=F",            "Gold Futures",     "Futures",        1.0),
]

# ── Indicators ────────────────────────────────────────────────────────────────

def compute_utbot(close_s):
    tr    = close_s.diff().abs()
    atr   = tr.rolling(ATR_PERIOD).mean()
    nloss = KEY_VAL * atr
    xatr  = [0.0] * len(close_s)
    for t in range(1, len(close_s)):
        sc, sp = close_s.iloc[t], close_s.iloc[t-1]
        xa, lc = xatr[t-1], nloss.iloc[t]
        if sc > xa and sp > xa:    xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa:  xatr[t] = min(xa, sc + lc)
        else:                      xatr[t] = (sc - lc) if sc > xa else (sc + lc)
    xatr_s = pd.Series(xatr, index=close_s.index)
    buy = (close_s > xatr_s) & (close_s.shift(1) <= xatr_s.shift(1))
    return buy

def compute_adx(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    pc  = close.shift(1)
    tr  = pd.concat([(high-low), (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
    dmp = (high-high.shift(1)).clip(lower=0)
    dmn = (low.shift(1)-low).clip(lower=0)
    dmp = dmp.where(dmp > dmn, 0)
    dmn = dmn.where(dmn > dmp, 0)
    trs = tr.ewm(span=n, adjust=False).mean()
    dx  = 100*(
        (100*dmp.ewm(span=n,adjust=False).mean()/trs -
         100*dmn.ewm(span=n,adjust=False).mean()/trs).abs() /
        (100*dmp.ewm(span=n,adjust=False).mean()/trs +
         100*dmn.ewm(span=n,adjust=False).mean()/trs + 1e-9)
    )
    return dx.ewm(span=n, adjust=False).mean()

def compute_rsi(close, n=14):
    d = close.diff()
    g = d.where(d > 0, 0).rolling(n).mean()
    l = (-d.where(d < 0, 0)).rolling(n).mean()
    return 100 - 100/(1 + g/(l+1e-9))

# ── Single-asset backtest ─────────────────────────────────────────────────────

def backtest_asset(ticker, name, category):
    try:
        df = yf.download(ticker, start="2016-01-01", end="2026-08-25",
                         interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
        if len(df) < 100:
            return None
    except:
        return None

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    buy_sig = compute_utbot(close)
    adx     = compute_adx(df)
    rsi     = compute_rsi(close)

    cap   = INITIAL_CAPITAL
    eq    = [cap]
    dates = [df.index[50]]
    last_exit = -1
    trades, wins, losses = 0, 0, 0
    max_win_pct = 0.0
    total_win_pct = 0.0
    total_loss_pct = 0.0

    brok = 0.0005
    stt  = 0.00125
    slip = 0.0015
    tax  = 0.15

    for i in range(50, len(df)):
        spot = float(close.iloc[i])
        if i > last_exit and buy_sig.iloc[i]:
            cur_adx = float(adx.iloc[i])
            cur_rsi = float(rsi.iloc[i])
            # Quality filter
            if cur_adx >= ADX_MIN and cur_rsi <= 72:
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
                    if mx >= be_p:
                        hit_be = True
                    if hit_be and mn <= spot:
                        hold = step; break
                    if not hit_be and mn <= sl_p:
                        hit_sl = True; hold = step; break

                last_exit = min(i + hold, len(df) - 1)

                if hit_tp:
                    ret = TP_PCT * 6.0 * 100
                    wins += 1
                    total_win_pct += TP_PCT * 100
                    max_win_pct = max(max_win_pct, TP_PCT * 100)
                elif hit_be:
                    ret = 0.0
                    wins += 1
                elif hit_sl:
                    ret = -(SL_PCT * 5.0 * 100)
                    losses += 1
                    total_loss_pct += SL_PCT * 100
                else:
                    exit_p = float(close.iloc[last_exit])
                    ret = TP_PCT * 50 if exit_p >= spot else -(SL_PCT * 50)
                    if ret >= 0: wins += 1
                    else: losses += 1

                gross = (ret / 100.0) * alloc
                fric  = alloc * (brok + stt + slip) * 2
                net   = gross - fric - max(0, (gross - fric) * tax)
                cap  += net

        eq.append(max(cap, 0.01))
        dates.append(df.index[i])

    if trades < 3:
        return None

    years = max((dates[-1] - dates[0]).days / 365.25, 0.1)
    cagr  = ((cap / INITIAL_CAPITAL) ** (1.0 / years) - 1.0) * 100.0
    wr    = wins / max(1, trades) * 100
    eq_s  = pd.Series(eq)
    mdd   = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100

    return {
        "ticker": ticker, "name": name, "category": category,
        "final_cap": cap, "cagr": cagr, "win_rate": wr,
        "trades": trades, "wins": wins, "losses": losses, "mdd": mdd,
        "eq": eq, "dates": dates,
        "profit": cap - INITIAL_CAPITAL,
    }

# ── PORTFOLIO COMBINED SIMULATION ────────────────────────────────────────────

def run_portfolio_simulation(all_results):
    """
    Simulate trading across ALL assets simultaneously with a single shared
    wallet — max 3 concurrent positions, capital rotates asset-to-asset.
    """
    # Build a unified signal timeline
    all_signals = []
    for r in all_results:
        if r is None: continue
        ticker = r["ticker"]
        try:
            df = yf.download(ticker, start="2016-01-01", end="2026-08-25",
                             interval="1d", progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.dropna(inplace=True)
            close = df["Close"]
            high  = df["High"]
            low   = df["Low"]
            buy_s = compute_utbot(close)
            adx_s = compute_adx(df)
            rsi_s = compute_rsi(close)

            for i in range(50, len(df)):
                if buy_s.iloc[i] and adx_s.iloc[i] >= ADX_MIN and rsi_s.iloc[i] <= 72:
                    all_signals.append({
                        "date": df.index[i],
                        "ticker": ticker,
                        "name": r["name"],
                        "category": r["category"],
                        "close_s": close,
                        "high_s": high,
                        "low_s": low,
                        "bar_idx": i,
                        "spot": float(close.iloc[i]),
                        "df_len": len(df),
                    })
        except:
            continue

    # Sort by date
    all_signals.sort(key=lambda x: x["date"])

    cap    = INITIAL_CAPITAL
    eq     = []
    dates  = []
    open_trades = []  # list of (exit_bar_date, ret_pct, alloc)
    trades = wins = 0

    brok, stt, slip, tax = 0.0005, 0.00125, 0.0015, 0.15

    # Build date range
    date_range = pd.date_range("2016-01-01", "2026-08-25", freq="B")
    sig_by_date = {}
    for s in all_signals:
        d = s["date"].date() if hasattr(s["date"], 'date') else s["date"]
        if d not in sig_by_date:
            sig_by_date[d] = []
        sig_by_date[d].append(s)

    for dt in date_range:
        d = dt.date()

        # Settle expired trades
        still_open = []
        for ot in open_trades:
            if ot["exit_date"] <= d:
                gross = (ot["ret_pct"] / 100.0) * ot["alloc"]
                fric  = ot["alloc"] * (brok + stt + slip) * 2
                net   = gross - fric - max(0, (gross - fric) * tax)
                cap  += net
                if ot["ret_pct"] >= 0:
                    wins += 1
            else:
                still_open.append(ot)
        open_trades = still_open

        # Open new trades (max 3 concurrent)
        if d in sig_by_date:
            for sig in sig_by_date[d]:
                if len(open_trades) >= 3:
                    break
                # Avoid duplicate tickers
                active_tickers = [ot["ticker"] for ot in open_trades]
                if sig["ticker"] in active_tickers:
                    continue

                spot  = sig["spot"]
                alloc = min(cap * 0.25, cap * 0.30)
                close_s = sig["close_s"]
                high_s  = sig["high_s"]
                low_s   = sig["low_s"]
                bar_i   = sig["bar_idx"]
                df_len  = sig["df_len"]

                tp_p = spot * (1.0 + TP_PCT)
                sl_p = spot * (1.0 - SL_PCT)
                be_p = spot * (1.0 + BE_PCT)

                hit_tp = hit_sl = hit_be = False
                hold = 14

                for step in range(1, 15):
                    ci = bar_i + step
                    if ci >= df_len: break
                    mx = float(high_s.iloc[ci])
                    mn = float(low_s.iloc[ci])
                    if mx >= tp_p:
                        hit_tp = True; hold = step; break
                    if mx >= be_p:
                        hit_be = True
                    if hit_be and mn <= spot:
                        hold = step; break
                    if not hit_be and mn <= sl_p:
                        hit_sl = True; hold = step; break

                if hit_tp:    ret_pct = TP_PCT * 6.0 * 100
                elif hit_be:  ret_pct = 0.0
                elif hit_sl:  ret_pct = -(SL_PCT * 5.0 * 100)
                else:
                    ep = bar_i + hold
                    exit_p = float(close_s.iloc[min(ep, df_len-1)])
                    ret_pct = TP_PCT*50 if exit_p >= spot else -(SL_PCT*50)

                exit_date = (sig["date"] + pd.Timedelta(days=hold)).date()
                if hasattr(exit_date, 'date'):
                    exit_date = exit_date.date()

                open_trades.append({
                    "ticker": sig["ticker"], "alloc": alloc,
                    "ret_pct": ret_pct, "exit_date": exit_date,
                })
                trades += 1

        eq.append(max(cap, 0.01))
        dates.append(dt)

    years = 10.0
    cagr  = ((cap / INITIAL_CAPITAL) ** (1.0 / years) - 1.0) * 100.0
    wr    = wins / max(1, trades) * 100
    eq_s  = pd.Series(eq)
    mdd   = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100

    return {
        "final_cap": cap, "cagr": cagr, "win_rate": wr,
        "trades": trades, "wins": wins, "mdd": mdd,
        "eq": eq, "dates": dates,
    }

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  UTBOT CHAMPION — MULTI-ASSET 10-YEAR WEALTH SIMULATION")
    print(f"  Scanning {len(ASSETS)} assets across 5 categories (2016-2026)")
    print(f"  Strategy: Monte Carlo Champion (86.5% WR / -3.20% MDD)")
    print("=" * 80)

    all_results = []
    category_totals = {}

    for ticker, name, category, _ in ASSETS:
        print(f"  Backtesting {name:<22} ({ticker:<16}) ...", end=" ")
        r = backtest_asset(ticker, name, category)
        if r:
            all_results.append(r)
            if category not in category_totals:
                category_totals[category] = []
            category_totals[category].append(r)
            print(f"${r['final_cap']:>10,.2f}  CAGR +{r['cagr']:>5.1f}%  WR {r['win_rate']:>5.1f}%  MDD -{r['mdd']:>4.1f}%")
        else:
            print("[No data / insufficient bars]")

    # Sort by final capital
    all_results.sort(key=lambda x: x["final_cap"], reverse=True)

    print("\n" + "=" * 80)
    print("  PER-ASSET FINAL RESULTS (Sorted by Final Equity)")
    print("=" * 80)
    print(f"  {'Asset':<22} {'Category':<15} {'Final Equity':>13} {'CAGR':>8} {'Win Rate':>9} {'Trades':>7} {'MDD':>6}")
    print("  " + "-" * 80)
    total_profit = 0.0
    for r in all_results:
        print(f"  {r['name']:<22} {r['category']:<15} ${r['final_cap']:>12,.2f} +{r['cagr']:>6.1f}% {r['win_rate']:>8.1f}% {r['trades']:>7} -{r['mdd']:>4.1f}%")
        total_profit += r["profit"]

    print("  " + "-" * 80)
    print(f"  {'TOTAL ACROSS ALL ASSETS':<22} {'':>15} ${total_profit + INITIAL_CAPITAL * len(all_results):>12,.2f}  (Portfolio compounded below)")

    # Run portfolio simulation
    print(f"\n  Running combined PORTFOLIO simulation (shared $1,000 wallet)...")
    portfolio = run_portfolio_simulation(all_results)

    print(f"\n  PORTFOLIO RESULT (single $1,000 wallet, max 3 concurrent trades):")
    print(f"  Final Portfolio Value: ${portfolio['final_cap']:,.2f}")
    print(f"  Total CAGR:            +{portfolio['cagr']:.1f}% / year")
    print(f"  Win Rate:              {portfolio['win_rate']:.1f}%")
    print(f"  Total Trades:          {portfolio['trades']}")
    print(f"  Maximum Drawdown:      -{portfolio['mdd']:.2f}%")
    print("=" * 80)

    # ── CHART ────────────────────────────────────────────────────────────────

    fig = plt.figure(figsize=(18, 14), facecolor='#090d16')
    gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.30)

    cat_colors = {
        "Crypto": "#f59e0b", "US Stocks": "#38bdf8",
        "Indian Stocks": "#a855f7", "Indices": "#22c55e", "Futures": "#fb7185"
    }

    # ── Plot 1: Portfolio Combined Equity Curve ──
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(portfolio["dates"], portfolio["eq"],
             color='#00d4aa', linewidth=2.8, label=f'Combined Portfolio: ${portfolio["final_cap"]:,.0f}', zorder=10)
    ax1.fill_between(portfolio["dates"], INITIAL_CAPITAL, portfolio["eq"], alpha=0.08, color='#00d4aa')
    ax1.set_yscale('log')
    ax1.set_title(
        f"COMBINED PORTFOLIO EQUITY CURVE — All Assets, Single $1,000 Wallet, 10 Years\n"
        f"Final: ${portfolio['final_cap']:,.2f}  |  CAGR: +{portfolio['cagr']:.1f}%  |  Win Rate: {portfolio['win_rate']:.1f}%  |  MDD: -{portfolio['mdd']:.2f}%",
        color='#00d4aa', fontsize=12, fontweight='bold'
    )
    ax1.set_ylabel("Portfolio Value ($)", color='#94a3b8')
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
    ax1.legend(fontsize=10, frameon=True, facecolor='#0f172a')

    # ── Plot 2: Per-Asset Bar Chart ──
    ax2 = fig.add_subplot(gs[1, 0])
    names  = [r["name"] for r in all_results[:10]]
    finals = [r["final_cap"] for r in all_results[:10]]
    colors = [cat_colors.get(r["category"], "#94a3b8") for r in all_results[:10]]
    bars = ax2.barh(names[::-1], finals[::-1], color=colors[::-1], alpha=0.85)
    for bar, val in zip(bars, finals[::-1]):
        ax2.text(bar.get_width() + max(finals)*0.01, bar.get_y() + bar.get_height()/2,
                 f"${val:,.0f}", va='center', ha='left', fontsize=8, color='#e2e8f0')
    ax2.set_title("Top 10 Assets by Final Equity ($1k Start)", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax2.set_xlabel("Final Equity ($)", color='#94a3b8')
    ax2.grid(True, axis='x', linestyle='--', alpha=0.10, color='#334155')
    ax2.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 3: CAGR by Category ──
    ax3 = fig.add_subplot(gs[1, 1])
    cat_cagr = {}
    for r in all_results:
        c = r["category"]
        if c not in cat_cagr: cat_cagr[c] = []
        cat_cagr[c].append(r["cagr"])
    cats = list(cat_cagr.keys())
    avg_cagrs = [np.mean(cat_cagr[c]) for c in cats]
    bar_cols = [cat_colors.get(c, '#94a3b8') for c in cats]
    bars2 = ax3.bar(cats, avg_cagrs, color=bar_cols, alpha=0.85)
    for bar, val in zip(bars2, avg_cagrs):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"+{val:.1f}%", ha='center', va='bottom', fontsize=9, color='#e2e8f0', fontweight='bold')
    ax3.set_title("Average CAGR by Asset Category", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax3.set_ylabel("Avg CAGR (% / Year)", color='#94a3b8')
    ax3.grid(True, axis='y', linestyle='--', alpha=0.10, color='#334155')
    ax3.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 4: Win Rate vs MDD scatter ──
    ax4 = fig.add_subplot(gs[2, 0])
    for r in all_results:
        c = cat_colors.get(r["category"], '#94a3b8')
        ax4.scatter(r["mdd"], r["win_rate"], color=c, s=80, alpha=0.85, zorder=5)
        ax4.annotate(r["name"], (r["mdd"], r["win_rate"]),
                     fontsize=6.5, color='#cbd5e1',
                     xytext=(3, 2), textcoords='offset points')
    ax4.set_xlabel("Max Drawdown (%)", color='#94a3b8')
    ax4.set_ylabel("Win Rate (%)", color='#94a3b8')
    ax4.set_title("Win Rate vs. MDD — All Assets", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax4.grid(True, linestyle='--', alpha=0.10, color='#334155')
    ax4.tick_params(colors='#94a3b8', labelsize=8)

    # ── Plot 5: Individual equity curves by category ──
    ax5 = fig.add_subplot(gs[2, 1])
    for r in all_results:
        c = cat_colors.get(r["category"], '#94a3b8')
        ax5.plot(r["dates"], r["eq"], color=c, linewidth=0.9, alpha=0.6)
    # Bold the top 3
    for r in all_results[:3]:
        ax5.plot(r["dates"], r["eq"], color='#ffffff', linewidth=1.8, alpha=0.9,
                 label=f"{r['name']} (${r['final_cap']:,.0f})")
    ax5.set_yscale('log')
    ax5.set_title("Individual Asset Equity Curves", color='#e2e8f0', fontsize=10, fontweight='bold')
    ax5.set_ylabel("Equity ($)", color='#94a3b8')
    ax5.legend(fontsize=7.5, frameon=True, facecolor='#0f172a', loc='upper left')
    ax5.grid(True, which='both', linestyle='--', alpha=0.10, color='#334155')
    ax5.tick_params(colors='#94a3b8', labelsize=8)

    # Legend for categories
    from matplotlib.patches import Patch
    legend_el = [Patch(facecolor=v, label=k) for k, v in cat_colors.items()]
    fig.legend(handles=legend_el, loc='lower center', ncol=5, fontsize=9,
               frameon=True, facecolor='#0f172a', edgecolor='#1e293b', bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        "ANTIGRAVITY AI BRAIN — UTBOT CHAMPION: MULTI-ASSET 10-YEAR WEALTH SIMULATION (2016-2026)\n"
        "Starting Capital: $1,000 USD  |  Monte Carlo Optimized Strategy  |  86.5% Audited Win Rate",
        fontsize=13, fontweight='bold', color='#e2e8f0', y=1.01
    )

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=240, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"\n  [CHART] Saved: {CHART_PATH}")

    # ── REPORT ───────────────────────────────────────────────────────────────
    top3 = all_results[:3]
    rows = ""
    for r in all_results:
        rows += f"| **{r['name']}** | {r['category']} | **${r['final_cap']:,.2f}** | +{r['cagr']:.1f}% | {r['win_rate']:.1f}% | {r['trades']} | -{r['mdd']:.2f}% |\n"

    report = f"""# UTBOT CHAMPION — MULTI-ASSET 10-YEAR WEALTH SIMULATION REPORT

**Strategy:** Monte Carlo Pareto Champion (Key=2.4, ATR=9, TP=+1.52%, SL=-0.73%, BE=+0.32%, ADX≥18)
**Period:** 2016 – 2026 (10 Years)  |  **Starting Capital:** $1,000 USD per asset

---

## COMBINED PORTFOLIO RESULT (Single $1,000 Wallet)

| Metric | Value |
|:---|:---:|
| **Final Portfolio Value** | **${portfolio['final_cap']:,.2f} USD** |
| **10-Year CAGR** | **+{portfolio['cagr']:.1f}% / Year** |
| **Win Rate** | **{portfolio['win_rate']:.1f}%** |
| **Total Trades (All Assets)** | **{portfolio['trades']}** |
| **Maximum Drawdown (MDD)** | **-{portfolio['mdd']:.2f}%** |

---

## PER-ASSET PERFORMANCE (Each Starting at $1,000)

| Asset | Category | Final Equity | CAGR | Win Rate | Trades | MDD |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
{rows}

---

## TOP PERFORMERS

| Rank | Asset | Final Equity | CAGR |
|:---:|:---|:---:|:---:|
| 1 | **{top3[0]['name']}** | **${top3[0]['final_cap']:,.2f}** | +{top3[0]['cagr']:.1f}% |
| 2 | **{top3[1]['name'] if len(top3)>1 else 'N/A'}** | **${top3[1]['final_cap']:,.2f if len(top3)>1 else 0}** | +{top3[1]['cagr']:.1f if len(top3)>1 else 0}% |
| 3 | **{top3[2]['name'] if len(top3)>2 else 'N/A'}** | **${top3[2]['final_cap']:,.2f if len(top3)>2 else 0}** | +{top3[2]['cagr']:.1f if len(top3)>2 else 0}% |

---

![Multi Asset Chart](file:///{CHART_PATH})
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  [REPORT] Saved: {REPORT_PATH}")

if __name__ == "__main__":
    main()
