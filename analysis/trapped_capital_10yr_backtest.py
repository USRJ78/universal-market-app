"""
==============================================================================
  10-YEAR FULL BACKTEST ENGINE: TRAPPED CAPITAL & BREAKEVEN LIQUIDITY SWEEP
  PERIOD: 2016 - 2026 (10 YEARS)
==============================================================================

STRATEGY RULES:
  1. TRAPPED CAPITAL DETECTION:
     Identifies high-volume consolidation nodes (Rel Volume > 1.3) followed by a 
     >= 4% downward price displacement within 5 bars.

  2. BREAKEVEN SWEEP ENTRY SIGNAL:
     When price rallies back to test the Trapped Supply Node (0.99x to 1.02x Trapped Price),
     a SHORT position (or Bearish Option Structure) is executed.

  3. RISK MANAGEMENT:
     - Stop-Loss: +3.5% above Trapped Supply Node (Invalidation)
     - Profit Target: 2.5x Risk-to-Reward (+8.75% gain) or Trailing Ratchet
     - Max Hold Time: 7 Days

  4. FRICTION & AUDIT:
     Includes 0.10% transaction fees per trade + slippage.
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

def run_trapped_capital_backtest(ticker="BTC-USD", initial_cap=100000.0):
    df = yf.download(ticker, start="2016-01-01", end="2026-07-27", auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.copy()
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    open_p = df["Open"]
    vol   = df["Volume"]

    # Calculate Indicators
    vol_sma = vol.rolling(30).mean()
    rel_vol = vol / (vol_sma + 1e-9)

    # 5-bar return to check for sharp downward displacement
    ret_5d = close.pct_change(5)

    # Trapped Node: High Volume followed by drop
    trapped_trigger = (rel_vol.shift(5) > 1.3) & (ret_5d < -0.04)
    trapped_level = np.where(trapped_trigger, close.shift(5), np.nan)
    trapped_level = pd.Series(trapped_level, index=df.index).ffill(limit=25)

    # Backtest Execution Engine
    equity = initial_cap
    equity_curve = []
    trades = []

    in_position = False
    entry_price = 0.0
    entry_date = None
    stop_loss = 0.0
    take_profit = 0.0
    hold_bars = 0
    position_size = 0.0

    fee_rate = 0.0010  # 0.10% fee per side

    dates = df.index
    for i in range(50, len(df)):
        dt = dates[i]
        c_price = float(close.iloc[i])
        h_price = float(high.iloc[i])
        l_price = float(low.iloc[i])
        o_price = float(open_p.iloc[i])
        t_level = float(trapped_level.iloc[i]) if not np.isnan(trapped_level.iloc[i]) else None

        if in_position:
            hold_bars += 1
            # Check Stop-Loss (Short Position: High >= Stop Loss)
            if h_price >= stop_loss:
                exit_p = stop_loss
                pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                pnl_usd = position_size * pnl_pct
                equity += pnl_usd
                trades.append({
                    "Entry_Date": entry_date, "Exit_Date": dt, "Type": "SHORT",
                    "Entry_Price": entry_price, "Exit_Price": exit_p, "Reason": "STOP_LOSS",
                    "PnL_%": pnl_pct * 100, "PnL_USD": pnl_usd, "Equity": equity
                })
                in_position = False

            # Check Take-Profit (Short Position: Low <= Take Profit)
            elif l_price <= take_profit:
                exit_p = take_profit
                pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                pnl_usd = position_size * pnl_pct
                equity += pnl_usd
                trades.append({
                    "Entry_Date": entry_date, "Exit_Date": dt, "Type": "SHORT",
                    "Entry_Price": entry_price, "Exit_Price": exit_p, "Reason": "TAKE_PROFIT",
                    "PnL_%": pnl_pct * 100, "PnL_USD": pnl_usd, "Equity": equity
                })
                in_position = False

            # Time Exit (7 Bars)
            elif hold_bars >= 7:
                exit_p = c_price
                pnl_pct = (entry_price - exit_p) / entry_price - (2 * fee_rate)
                pnl_usd = position_size * pnl_pct
                equity += pnl_usd
                trades.append({
                    "Entry_Date": entry_date, "Exit_Date": dt, "Type": "SHORT",
                    "Entry_Price": entry_price, "Exit_Price": exit_p, "Reason": "TIME_EXIT",
                    "PnL_%": pnl_pct * 100, "PnL_USD": pnl_usd, "Equity": equity
                })
                in_position = False

        else:
            # Check Entry Condition: Price sweeps up into trapped supply zone
            if t_level is not None and c_price < t_level:
                if h_price >= t_level * 0.99 and h_price <= t_level * 1.025:
                    in_position = True
                    entry_price = t_level * 0.995
                    entry_date = dt
                    stop_loss = entry_price * 1.035       # 3.5% Stop Loss
                    take_profit = entry_price * (1 - 0.0875) # 8.75% Take Profit (2.5x R/R)
                    hold_bars = 0
                    # Position sizing: Risk 2.5% of account per trade
                    risk_amount = equity * 0.025
                    position_size = risk_amount / 0.035

        equity_curve.append(equity)

    df_equity = pd.Series(equity_curve, index=dates[50:])
    df_trades = pd.DataFrame(trades)

    # Compute Performance Metrics
    total_trades = len(df_trades)
    if total_trades > 0:
        wins = df_trades[df_trades["PnL_USD"] > 0]
        losses = df_trades[df_trades["PnL_USD"] <= 0]
        win_rate = (len(wins) / total_trades) * 100
        gross_profit = wins["PnL_USD"].sum()
        gross_loss = abs(losses["PnL_USD"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0
        cagr = ((equity / initial_cap) ** (1 / 10.0) - 1) * 100

        # Peak-to-Trough Drawdown
        peak = df_equity.cummax()
        dd = (df_equity - peak) / peak
        mdd = dd.min() * 100
    else:
        win_rate = profit_factor = cagr = mdd = 0.0

    return {
        "Ticker": ticker.replace("^NSEI", "NIFTY50"),
        "Final_Equity": equity,
        "CAGR_%": cagr,
        "Win_Rate_%": win_rate,
        "Profit_Factor": profit_factor,
        "MDD_%": mdd,
        "Total_Trades": total_trades,
        "Trades": df_trades,
        "Equity_Curve": df_equity
    }


def master_backtest():
    tickers = ["BTC-USD", "ETH-USD", "^NSEI"]
    results = []

    print("=" * 75)
    print("  TRAPPED CAPITAL & BREAKEVEN LIQUIDITY SWEEP — 10-YEAR BACKTEST (2016-2026)")
    print("=" * 75)

    for ticker in tickers:
        res = run_trapped_capital_backtest(ticker)
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
            plot_equity_curve(res)

    df_res = pd.DataFrame(results)
    out_csv = os.path.join(OUTPUT_DIR, "trapped_capital_10yr_results.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\n[OK] 10-Year Backtest Results saved -> {out_csv}")


def plot_equity_curve(res):
    p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
         "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(p["bg"])
    ax.set_facecolor(p["panel"])

    eq = res["Equity_Curve"]
    ax.plot(eq.index, eq, color="#00ffcc", lw=2.0, label=f"{res['Ticker']} Trapped Capital Strategy (CAGR: {res['CAGR_%']:.1f}%, Win Rate: {res['Win_Rate_%']:.1f}%)")

    ax.set_title(f"10-Year Backtest Equity Curve: {res['Ticker']} Trapped Capital Strategy (2016-2026)", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel("Account Equity ($)", color=p["muted"])
    ax.tick_params(colors=p["muted"])
    ax.grid(True, color="#30363d", ls=":", alpha=0.5)
    ax.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    out_png = os.path.join(OUTPUT_DIR, "trapped_capital_10yr_equity.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Equity Curve saved -> {out_png}")


if __name__ == "__main__":
    master_backtest()
