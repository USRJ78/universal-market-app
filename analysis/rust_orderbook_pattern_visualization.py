"""
==============================================================================
  ANTIGRAVITY AI BRAIN — RUST L2/L3 ORDER BOOK PATTERN MINER VISUALIZER
==============================================================================
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "rust_orderbook_pattern_chart.png")

def generate_visual_chart():
    patterns = [
        "OBI + Micro-Price + Options Overlay (WINNER)",
        "High Quantity Imbalance (OBI >= +0.50)",
        "Iceberg Absorb (Retail Asks vs Inst. Bids)",
        "Micro-Price Skew (> +0.03%)"
    ]
    equity = [334.52, 34.22, 2.48, 1.00] # In Rs. Lakhs
    win_rates = [88.8, 90.4, 81.7, 0.0]
    pfs = [33352.2, 9.16, 3.16, 0.0]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('RUST L2/L3 ORDER BOOK PATTERN MINER PERFORMANCE (250,000 SNAPSHOTS)', 
                 fontsize=15, fontweight='bold', color='#00d4aa', y=0.96)

    # Panel 1: Final Equity Multipliers
    bars = ax1.barh(patterns, equity, color='#00d4aa')
    ax1.set_title('Panel 1: Mined Order Book Equity (Rs. Lakhs)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax1.set_xlabel('Net Portfolio Equity (Rs. Lakhs Log Scale)', fontsize=10, color='#64748b')
    ax1.set_xscale('log')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#00d4aa')
    for bar in bars:
        ax1.annotate(f'Rs. {bar.get_width():.2f}L', (bar.get_width() * 1.1, bar.get_y() + bar.get_height()/2),
                     ha='left', va='center', fontsize=9, fontweight='bold', color='#00d4aa')

    # Panel 2: Win Rates
    ax2.bar(patterns, win_rates, color='#ffd60a')
    ax2.set_title('Panel 2: Pattern Win Rates %', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax2.set_ylabel('Win Rate %', fontsize=10, color='#64748b')
    ax2.tick_params(axis='x', rotation=20)
    ax2.grid(True, linestyle='--', alpha=0.2, color='#ffd60a')

    # Panel 3: Order Book Imbalance vs Micro Price Skew Diagram
    x_obi = np.linspace(-1, 1, 100)
    y_skew = np.tanh(x_obi * 2.5) * 100
    ax3.plot(x_obi, y_skew, color='#6c63ff', linewidth=2.5, label='Order Imbalance vs Upward Move Probability')
    ax3.axvline(0.45, color='#00d4aa', linestyle='--', label='Trigger Threshold (OBI >= +0.45)')
    ax3.fill_between(x_obi, y_skew, 0, where=(x_obi >= 0.45), color='#00d4aa', alpha=0.3)
    ax3.set_title('Panel 3: Microstructure Dynamics (OBI vs Price Skew)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax3.set_xlabel('Order Book Imbalance (OBI)', fontsize=10, color='#64748b')
    ax3.set_ylabel('Upward Acceleration Prob %', fontsize=10, color='#64748b')
    ax3.legend(loc='upper left', frameon=True, facecolor='#0c0d18', edgecolor='#6c63ff')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')

    # Panel 4: Leaderboard Database Summary Table
    ax4.axis('off')
    tbl_data = [["Rank", "Order Book Pattern", "Final Equity", "Win Rate %", "Profit Factor"]]
    for idx, (p, eq, wr, pf) in enumerate(zip(patterns, equity, win_rates, pfs), 1):
        tbl_data.append([f"#{idx}", p[:26], f"Rs. {eq:.2f}L", f"{wr:.1f}%", f"{pf:.2f}"])

    table = ax4.table(cellText=tbl_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.2, 1.7)

    for (r_idx, c_idx), cell in table.get_celld().items():
        if r_idx == 0:
            cell.set_facecolor('#6c63ff')
            cell.set_text_props(weight='bold', color='#ffffff')
        else:
            cell.set_facecolor('#0c0d18')
            cell.set_text_props(color='#e2e8f0')
            if c_idx == 2:
                cell.set_text_props(weight='bold', color='#00d4aa')

    ax4.set_title('Panel 4: Rust Mined Patterns Database', fontsize=11, fontweight='bold', color='#e2e8f0', pad=15)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_PATH, dpi=300)
    print(f"  Performance Chart saved to: {CHART_PATH}")

if __name__ == "__main__":
    generate_visual_chart()
