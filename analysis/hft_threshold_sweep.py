#!/usr/bin/env python
"""HFT_SCORE Threshold Sweep and Mode Comparison

This script imports the core functions from `HFTJIMSIMMONS.ipynb` and runs
back‑tests for a range of entry thresholds. It evaluates the three modes:
- HFT (vector bundle only)
- UTBOT (trend‑following only)
- HYBRID (both signals)

Results are saved to `hft_threshold_sweep_results.xlsx` (Excel) and
`hft_threshold_sweep_results.csv` (CSV). A win‑rate vs threshold plot is
saved as `hft_threshold_winrate.png`.
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import nbformat
from scipy.stats import binomtest

# ---------------------------------------------------------------------
# Load functions from the notebook using nbformat
NOTEBOOK_PATH = os.path.abspath(
    "c:/Users/USER/OneDrive/Documents/universal-market-app/HFTJIMSIMMONS.ipynb"
)
with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb_json = nbformat.read(f, as_version=4)
code = ""
for cell in nb_json.cells:
    if cell.get("cell_type") == "code":
        code += cell.get("source", "") + "\n"
ns = {}
exec(code, ns)
# Extract required functions
load_nse_tickers = ns["load_nse_tickers"]
compute_hft_score = ns["compute_hft_score"]
backtest_strategy = ns["backtest_strategy"]
evaluate_strategy = ns["evaluate_strategy"]
load_data = ns["load_data"]

# ---------------------------------------------------------------------
# Parameters
THRESHOLDS = np.arange(0.5, 0.96, 0.05)  # 0.5 to 0.95 inclusive
MODES = ["HFT", "UTBOT", "HYBRID"]

# Load tickers (first 300 as in original notebook)
all_tickers = load_nse_tickers()[:300]
all_data = load_data(all_tickers)

results = []

for mode in MODES:
    for thr in THRESHOLDS:
        # Set the global threshold used by backtest_strategy
        backtest_strategy.__globals__['HFT_THRESHOLD'] = thr
        trades, equity_curve, dates = backtest_strategy(all_data, mode=mode)
        metrics = evaluate_strategy(f"{mode}_thr{thr:.2f}", trades, equity_curve)
        win_rate = metrics.get("Win Rate %", 0)
        total_trades = metrics.get("Trades", 0)
        # Binomial test against 0.5 null hypothesis (two‑sided, greater)
        wins = int(round(win_rate * total_trades / 100))
        pval = binomtest(wins, total_trades, p=0.5, alternative="greater").pvalue if total_trades > 0 else np.nan
        results.append({
            "Mode": mode,
            "Threshold": thr,
            "Win Rate %": win_rate,
            "Total Trades": total_trades,
            "Final Capital": metrics.get("Final Capital"),
            "Sharpe": metrics.get("Sharpe"),
            "Max Drawdown %": metrics.get("Max Drawdown %"),
            "Binomial p‑value": pval,
        })

# ---------------------------------------------------------------------
# Save results
df = pd.DataFrame(results)
output_excel = "hft_threshold_sweep_results.xlsx"
output_csv = "hft_threshold_sweep_results.csv"
with pd.ExcelWriter(output_excel) as writer:
    df.to_excel(writer, sheet_name="Summary", index=False)
df.to_csv(output_csv, index=False)

# Plot win‑rate vs threshold for each mode
plt.figure(figsize=(10, 6))
for mode in MODES:
    sub = df[df["Mode"] == mode]
    plt.plot(sub["Threshold"], sub["Win Rate %"], marker="o", label=mode)
plt.title("Win Rate vs HFT_SCORE Threshold (All Modes)")
plt.xlabel("HFT_SCORE Threshold")
plt.ylabel("Win Rate %")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("hft_threshold_winrate.png")
print("Done. Results saved to", output_excel, output_csv, "and plot to hft_threshold_winrate.png")
