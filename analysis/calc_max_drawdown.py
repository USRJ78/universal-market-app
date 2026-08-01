"""
==============================================================================
  MAX DRAWDOWN CALCULATOR FOR 10-YEAR SWARM CALL SPREAD BACKTEST
==============================================================================
"""

import os, pandas as pd, numpy as np

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(OUTPUT_DIR, "swarm_10yr_trades.csv")

df_trades = pd.read_csv(csv_file)

INITIAL_CAPITAL = 100_000
capital_curve = [INITIAL_CAPITAL]

for _, tr in df_trades.iterrows():
    ret_pct = tr["Return_%"] / 100.0
    allocated = capital_curve[-1] * 0.08
    pnl = allocated * ret_pct
    new_cap = max(1000, capital_curve[-1] + pnl)
    capital_curve.append(new_cap)

arr = np.array(capital_curve)
peaks = np.maximum.accumulate(arr)
drawdowns = (arr - peaks) / peaks
max_dd_pct = abs(np.min(drawdowns)) * 100

# Consecutive Losses
df_trades["Loss"] = ~df_trades["Win"]
df_trades["Loss_Streak"] = df_trades["Loss"].groupby((~df_trades["Loss"]).cumsum()).cumsum()
max_consecutive_losses = int(df_trades["Loss_Streak"].max())

print("=" * 65)
print("  10-YEAR SWARM BOT BACKTEST DRAWDOWN & RISK AUDIT")
print("=" * 65)
print(f"  Initial Capital        : Rs. {INITIAL_CAPITAL:,.0f}")
print(f"  Peak Capital Reached   : Rs. {np.max(arr):,.0f}")
print(f"  MAXIMUM DRAWDOWN (MDD) : {max_dd_pct:.2f}% 🔥")
print(f"  Max Consecutive Losses : {max_consecutive_losses} Trades")
print("=" * 65)
