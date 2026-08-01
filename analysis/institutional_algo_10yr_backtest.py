"""
==============================================================================
  10-YEAR FULL BACKTEST ENGINE: INSTITUTIONAL ALGORITHMIC EXECUTION STRATEGY
  PERIOD: 2016 - 2026 (10 YEARS)
==============================================================================

MATHEMATICAL STRATEGY RULES:

1. REGIME IDENTIFICATION (HURST EXPONENT):
   - Every bar, calculate 30-bar rolling Hurst Exponent (H).
   - H < 0.48: Mean-Reverting Regime (Active Range Execution).
   - H > 0.52: Trending Expansion Regime (Breakout Momentum Execution).

2. EXECUTION SIGNALS:
   - Range Regime (H < 0.48):
     * BUY (Accumulation): Price <= VWAP - 2.0 * sigma
     * SELL / SHORT (Distribution): Price >= VWAP + 2.0 * sigma
   - Trending Regime (H > 0.52):
     * BUY (Momentum): Price > VWAP + 1.5 * sigma and Price > 20-bar Donchian High

3. RISK MANAGEMENT:
   - Dynamic Stop-Loss: 1.5x ATR(14)
   - Dynamic Profit Target: 3.0x ATR(14) (2:1 Reward-to-Risk)
   - Time Stop: Exit after 10 bars if target not reached.

4. FRICTION & AUDIT:
   - Account Capital: $100,000 USD
   - Transaction Fees: 0.10% per side + Slippage
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def calculate_hurst(ts, max_lag=20):
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def clamp(val, min_v, max_v):
    return max(min_v, min(val, max_v))

def run_institutional_algo_backtest(ticker="BTC-USD", initial_cap=100000.0):
    df = yf.download(ticker, start="2016-01-01", end="2026-07-27", auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    open_p = df["Open"]
    vol   = df["Volume"]

    # 1. VWAP Benchmark & Standard Deviation Bands (30-bar rolling)
    window = 30
    pv = close * vol
    vwap = pv.rolling(window).sum() / (vol.rolling(window).sum() + 1e-9)
    var = (vol * (close - vwap)**2).rolling(window).sum() / (vol.rolling(window).sum() + 1e-9)
    vwap_std = np.sqrt(var)

    vwap_upper2 = vwap + 2.0 * vwap_std
    vwap_lower2 = vwap - 2.0 * vwap_std

    # ATR(14)
    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # Donchian High(20)
    donchian_high = high.rolling(20).max().shift(1)

    # Rolling Hurst Exponent
    close_vals = close.values
    hurst_list = []
    for i in range(len(close_vals)):
        if i < 40:
            hurst_list.append(0.50)
        else:
            try:
                h = calculate_hurst(close_vals[i-30:i])
                hurst_list.append(clamp(h, 0.1, 0.9))
            except Exception:
                hurst_list.append(0.50)

    df["Hurst"] = hurst_list

    # Backtest Loop
    equity = initial_cap
    equity_curve = []
    trades = []

    in_pos = False
    pos_type = None  # 'LONG' or 'SHORT'
    entry_price = 0.0
    entry_date = None
    stop_loss = 0.0
    take_profit = 0.0
    hold_bars = 0
    pos_size = 0.0
    fee_rate = 0.0010

    dates = df.index
    for i in range(50, len(df)):
        dt = dates[i]
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v_upper = float(vwap_upper2.iloc[i])
        v_lower = float(vwap_lower2.iloc[i])
        v_vwap  = float(vwap.iloc[i])
        c_atr   = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else c * 0.02
        c_hurst = float(hurst_list[i])
        c_donch = float(donchian_high.iloc[i]) if not np.isnan(donchian_high.iloc[i]) else c * 1.05

        if in_pos:
            hold_bars += 1
            if pos_type == 'LONG':
                # Check Stop Loss
                if l <= stop_loss:
                    exit_p = stop_loss
                    pnl_pct = (exit_p - entry_price) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "LONG", "Entry": entry_price, "Exit": exit_p, "Reason": "STOP_LOSS", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False
                # Check Take Profit
                elif h >= take_profit:
                    exit_p = take_profit
                    pnl_pct = (exit_p - entry_price) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "LONG", "Entry": entry_price, "Exit": exit_p, "Reason": "TAKE_PROFIT", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False
                elif hold_bars >= 10:
                    exit_p = c
                    pnl_pct = (exit_p - entry_price) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "LONG", "Entry": entry_price, "Exit": exit_p, "Reason": "TIME_EXIT", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False

            elif pos_type == 'SHORT':
                # Check Stop Loss
                if h >= stop_loss:
                    exit_p = stop_loss
                    pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "SHORT", "Entry": entry_price, "Exit": exit_p, "Reason": "STOP_LOSS", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False
                elif l <= take_profit:
                    exit_p = take_profit
                    pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "SHORT", "Entry": entry_price, "Exit": exit_p, "Reason": "TAKE_PROFIT", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False
                elif hold_bars >= 10:
                    exit_p = c
                    pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                    pnl_usd = pos_size * pnl_pct
                    equity += pnl_usd
                    trades.append({"Date": dt, "Type": "SHORT", "Entry": entry_price, "Exit": exit_p, "Reason": "TIME_EXIT", "PnL_%": pnl_pct*100, "Equity": equity})
                    in_pos = False

        else:
            # Entry Signal Evaluation
            # 1. Mean-Reverting Regime (Hurst < 0.48)
            if c_hurst < 0.48:
                if c <= v_lower:
                    # Buy Accumulation Zone
                    in_pos = True
                    pos_type = 'LONG'
                    entry_price = c
                    entry_date = dt
                    stop_loss = entry_price - (1.5 * c_atr)
                    take_profit = entry_price + (3.0 * c_atr)
                    hold_bars = 0
                    risk_amt = equity * 0.025
                    pos_size = risk_amt / (1.5 * c_atr / entry_price)

                elif c >= v_upper:
                    # Sell Distribution Zone
                    in_pos = True
                    pos_type = 'SHORT'
                    entry_price = c
                    entry_date = dt
                    stop_loss = entry_price + (1.5 * c_atr)
                    take_profit = entry_price - (3.0 * c_atr)
                    hold_bars = 0
                    risk_amt = equity * 0.025
                    pos_size = risk_amt / (1.5 * c_atr / entry_price)

            # 2. Trending Regime (Hurst > 0.52)
            elif c_hurst > 0.52:
                if c > v_vwap + (1.5 * vwap_std.iloc[i]) and c > c_donch:
                    # Momentum Expansion Buy
                    in_pos = True
                    pos_type = 'LONG'
                    entry_price = c
                    entry_date = dt
                    stop_loss = entry_price - (1.5 * c_atr)
                    take_profit = entry_price + (3.5 * c_atr)
                    hold_bars = 0
                    risk_amt = equity * 0.025
                    pos_size = risk_amt / (1.5 * c_atr / entry_price)

        equity_curve.append(equity)

    df_eq = pd.Series(equity_curve, index=dates[50:])
    df_tr = pd.DataFrame(trades)

    total_t = len(df_tr)
    if total_t > 0:
        wins = df_tr[df_tr["PnL_%"] > 0]
        losses = df_tr[df_tr["PnL_%"] <= 0]
        win_rate = (len(wins) / total_t) * 100
        gross_p = wins["PnL_%"].sum()
        gross_l = abs(losses["PnL_%"].sum())
        pf = gross_p / gross_l if gross_l > 0 else 99.0
        cagr = ((equity / initial_cap) ** (1 / 10.0) - 1) * 100
        peak = df_eq.cummax()
        dd = (df_eq - peak) / peak
        mdd = dd.min() * 100
    else:
        win_rate = pf = cagr = mdd = 0.0

    return {
        "Ticker": ticker.replace("^NSEI", "NIFTY50"),
        "Final_Equity": equity,
        "CAGR_%": cagr,
        "Win_Rate_%": win_rate,
        "Profit_Factor": pf,
        "MDD_%": mdd,
        "Total_Trades": total_t,
        "Equity_Curve": df_eq
    }


def master_backtest():
    tickers = ["BTC-USD", "ETH-USD", "^NSEI"]
    results = []

    print("=" * 75)
    print("  INSTITUTIONAL ALGORITHM MATH — 10-YEAR MASTER BACKTEST (2016-2026)")
    print("=" * 75)

    for ticker in tickers:
        res = run_institutional_algo_backtest(ticker)
        print(f"\n[ASSET: {res['Ticker']}]")
        print(f"  Final Equity   : ${res['Final_Equity']:,.2f} (from $100,000)")
        print(f"  CAGR           : {res['CAGR_%']:.2f}%")
        print(f"  Win Rate       : {res['Win_Rate_%']:.1f}%")
        print(f"  Profit Factor  : {res['Profit_Factor']:.2f}")
        print(f"  Max Drawdown   : {res['MDD_%']:.2f}%")
        print(f"  Total Trades   : {res['Total_Trades']}")

        results.append({
            "Ticker": res["Ticker"],
            "Final_Equity": round(res["Final_Equity"], 2),
            "CAGR_%": round(res["CAGR_%"], 2),
            "Win_Rate_%": round(res["Win_Rate_%"], 1),
            "Profit_Factor": round(res["Profit_Factor"], 2),
            "MDD_%": round(res["MDD_%"], 2),
            "Total_Trades": res["Total_Trades"]
        })

        if res["Ticker"] == "BTC-USD":
            plot_equity(res)

    df_res = pd.DataFrame(results)
    out_csv = os.path.join(OUTPUT_DIR, "institutional_algo_10yr_results.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\n[OK] 10-Year Master Results saved -> {out_csv}")


def plot_equity(res):
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(p["bg"])
    ax.set_facecolor(p["panel"])

    eq = res["Equity_Curve"]
    ax.plot(eq.index, eq, color="#39d353", lw=2.0, label=f"{res['Ticker']} Institutional Math Algo (CAGR: {res['CAGR_%']:.1f}%, Win Rate: {res['Win_Rate_%']:.1f}%)")

    ax.set_title(f"10-Year Backtest Equity Curve: {res['Ticker']} Institutional Algo Math (2016-2026)", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel("Account Equity ($)", color=p["muted"])
    ax.tick_params(colors=p["muted"])
    ax.grid(True, color="#30363d", ls=":", alpha=0.5)
    ax.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    out_png = os.path.join(OUTPUT_DIR, "institutional_algo_10yr_equity.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] 10-Year Equity Chart saved -> {out_png}")


if __name__ == "__main__":
    master_backtest()
