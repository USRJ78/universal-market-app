"""
==============================================================================
  ANTIGRAVITY AI BRAIN — 5-YEAR PATTERN-BASED RS. 1 LAKH CAPITAL SIMULATION
==============================================================================
  Calculates exact 5-year returns starting from Rs. 1 Lakh (Rs. 1,00,000)
  for each mined chart pattern combined with Zero Net Debit Options Spreads.
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

def run_simulation():
    print("=" * 75)
    print("  💰 RS. 1 LAKH 5-YEAR PATTERN PROFIT SIMULATION (2021 - 2026)")
    print("=" * 75)

    try:
        df = yf.download("BTC-USD", start="2021-01-01", end="2026-08-15", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
    except Exception as e:
        print(f"  ❌ Data fetch error: {e}")
        return

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    df["EMA20"] = close.ewm(span=20).mean()
    df["EMA50"] = close.ewm(span=50).mean()

    tr = np.maximum(high - low, np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))))
    df["ATR10"] = pd.Series(tr, index=df.index).rolling(10).mean()
    df["ATR50"] = pd.Series(tr, index=df.index).rolling(50).mean()
    df["SqueezeRatio"] = df["ATR10"] / (df["ATR50"] + 1e-9)

    delta = close.diff()
    gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    initial_capital = 100000.0  # Rs. 1 Lakh
    capacity_limit  = 2500000.0 # Rs. 25 Lakh
    brokerage_pct   = 0.0005
    slippage_pct    = 0.0015
    tax_rate        = 0.15

    patterns = [
        {"name": "ATR Volatility Squeeze (Most Frequent)", "type": "atr"},
        {"name": "Bull Flag / Consolidation Breakout", "type": "flag"},
        {"name": "RSI Oversold Bounce (RSI <= 30)", "type": "rsi"},
        {"name": "Ascending Triangle Breakout", "type": "triangle"},
        {"name": "Double Bottom (W-Reversal)", "type": "double_bottom"},
        {"name": "EMA 20/50 Golden Cross", "type": "ema"}
    ]

    results = []

    for pat in patterns:
        capital = initial_capital
        ptype   = pat["type"]
        in_pos  = False
        entry_p = 0.0
        entry_d = None
        margin  = 0.0
        trades  = 0
        wins    = 0

        for i in range(50, len(df) - 5):
            p_now = close.iloc[i]
            date  = df.index[i]
            rsi   = df["RSI"].iloc[i]

            trigger = False
            if ptype == "atr" and df["SqueezeRatio"].iloc[i] < 0.85 and p_now > df["EMA20"].iloc[i]:
                trigger = True
            elif ptype == "flag" and (close.iloc[i-3] - close.iloc[i-7]) / close.iloc[i-7] > 0.08:
                trigger = True
            elif ptype == "rsi" and df["RSI"].iloc[i-1] <= 30 and rsi > df["RSI"].iloc[i-1]:
                trigger = True
            elif ptype == "triangle" and abs(high.iloc[i-10:i].max() - p_now) / p_now < 0.01:
                trigger = True
            elif ptype == "double_bottom" and abs(low.iloc[i] - low.iloc[i-15:i-5].min()) / p_now < 0.015:
                trigger = True
            elif ptype == "ema" and df["EMA20"].iloc[i] > df["EMA50"].iloc[i] and df["EMA20"].iloc[i-1] <= df["EMA50"].iloc[i-1]:
                trigger = True

            if not in_pos:
                if trigger:
                    in_pos  = True
                    entry_p = p_now * (1.0 + slippage_pct)
                    entry_d = date
                    margin  = min(capital * 0.25, capacity_limit)
                    k1      = entry_p
                    k2      = entry_p * 1.045
            else:
                hold_days = (date - entry_d).days
                if hold_days >= 5 or p_now >= k2:
                    exit_p = p_now * (1.0 - slippage_pct)
                    payoff_k1 = max(0.0, exit_p - k1)
                    payoff_k2 = max(0.0, exit_p - k2)
                    spread_p  = payoff_k1 - (2.0 * payoff_k2)

                    max_risk  = -0.05 * margin
                    raw_pnl   = max(max_risk, (spread_p / (entry_p + 1e-9)) * margin * 3.5)
                    net_pnl   = raw_pnl - (margin * brokerage_pct)
                    
                    if net_pnl > 0:
                        net_pnl *= (1.0 - tax_rate)
                        wins += 1

                    capital += net_pnl
                    trades  += 1
                    in_pos   = False

        mult = capital / initial_capital
        cagr = ((capital / initial_capital) ** (1/5.6) - 1) * 100.0
        results.append({
            "name": pat["name"],
            "capital": capital,
            "net_profit": capital - initial_capital,
            "mult": mult,
            "cagr": cagr,
            "trades": trades,
            "win_rate": (wins / trades * 100.0) if trades > 0 else 0.0
        })

    res_df = pd.DataFrame(results).sort_values(by="capital", ascending=False)

    print("=" * 75)
    for idx, r in enumerate(res_df.itertuples(), 1):
        print(f"  #{idx} | {r.name:<42}")
        print(f"       Starting: Rs. 1,00,000 -> Final Equity: Rs. {r.capital:,.2f}")
        print(f"       Net Profit: +Rs. {r.net_profit:,.2f} ({r.mult:.2f}x Multiplier | CAGR: +{r.cagr:.1f}%)")
        print(f"       Total Signals: {r.trades} Trades | Options Win Rate: {r.win_rate:.1f}%\n")
    print("=" * 75)

if __name__ == "__main__":
    run_simulation()
