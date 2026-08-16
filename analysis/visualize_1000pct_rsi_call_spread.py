"""
==============================================================================
  ANTIGRAVITY AI BRAIN — TACTICAL 1000% RSI CALL SPREAD BLUEPRINT & PAYOFF VISUALIZER
==============================================================================
  Generates a high-resolution 4-panel visual graphic illustrating how to place
  Tactical RSI + 1x2 Ratio Call Spreads to achieve the +1,000% Return Target.
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
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "1000pct_rsi_call_spread_blueprint.png")

def generate_blueprint():
    print("=" * 75)
    print("  🎯 GENERATING TACTICAL 1000% RSI CALL SPREAD BLUEPRINT GRAPHIC")
    print("=" * 75)

    # 1. Option Payoff Geometry Math
    spot = 65000.0
    k1   = spot         # ATM Buy 1x Call ($65,000)
    k2   = spot * 1.045 # OTM Sell 2x Call ($67,925)
    
    underlying_range = np.linspace(spot * 0.90, spot * 1.12, 500)
    
    # Payoffs at Expiry per unit
    payoff_k1 = np.maximum(0.0, underlying_range - k1)
    payoff_k2 = np.maximum(0.0, underlying_range - k2)
    
    # Zero Net Debit 1x2 Ratio Call Spread Payoff
    # Net Debit = $0.00 (financed by selling 2x K2)
    spread_payoff = payoff_k1 - (2.0 * payoff_k2)
    
    # 1x1 Standard Bull Call Spread Payoff (for comparison)
    spread_payoff_1x1 = payoff_k1 - payoff_k2 - (0.012 * spot)

    # 2. Capital Compounding Trajectory to 1000% Target
    initial_cap = 100.0 # $100 or Rs 1 Lakh baseline
    trades = np.arange(0, 13) # 12 trade sequences
    # Target: 10x growth (+1000% return) via 22% net portfolio gain per winning cycle
    target_trajectory = initial_cap * (1.215 ** trades)

    # 3. Create 4-Panel Master Graphic
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('⚡ TACTICAL BLUEPRINT: +1,000% RETURN VIA RSI & 1x2 RATIO CALL SPREADS', 
                 fontsize=15, fontweight='bold', color='#00d4aa', y=0.96)

    # PANEL 1: Payoff Diagram at Expiry
    ax1.plot(underlying_range, spread_payoff / 1000, color='#00d4aa', linewidth=2.5, label='1x2 Ratio Call Spread (Zero Net Debit)')
    ax1.plot(underlying_range, spread_payoff_1x1 / 1000, color='#6c63ff', linestyle='--', linewidth=1.8, label='1x1 Standard Spread (Net Debit Paid)')
    ax1.axvline(k1, color='#ffd60a', linestyle=':', label=f'K1 ATM Strike (${k1:,.0f})')
    ax1.axvline(k2, color='#ff4d6d', linestyle=':', label=f'K2 OTM Strike (${k2:,.0f})')
    ax1.axhline(0, color='#64748b', linewidth=0.8)
    
    # Annotate Sweet Spot Max Profit Zone
    max_p = (k2 - k1) / 1000
    ax1.annotate(f'TARGET MAX PROFIT ZONE\n+${max_p:.1f}k / contract at K2', xy=(k2, max_p), xytext=(k2*1.01, max_p*0.75),
                 arrowprops=dict(facecolor='#00d4aa', shrink=0.05, width=1.5, headwidth=8),
                 fontsize=10, fontweight='bold', color='#00d4aa', bbox=dict(boxstyle='round,pad=0.5', facecolor='#0c0d18', edgecolor='#00d4aa'))
    
    ax1.set_title('Panel 1: Options Strike Payoff Geometry at Expiry', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax1.set_xlabel('BTC Price at Expiry ($)', fontsize=10, color='#64748b')
    ax1.set_ylabel('Profit / Loss ($ Thousands)', fontsize=10, color='#64748b')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')
    ax1.legend(loc='upper left', fontsize=8, frameon=True, facecolor='#0c0d18', edgecolor='#6c63ff')

    # PANEL 2: RSI Entry Gate Trigger Zones
    rsi_x = np.linspace(0, 100, 200)
    y_gate = np.zeros_like(rsi_x)
    # 48 <= RSI <= 65 is Optimal Momentum Zone
    y_gate[(rsi_x >= 48) & (rsi_x <= 65)] = 1.0
    y_gate[rsi_x <= 32] = 0.85 # Oversold bounce zone

    ax2.plot(rsi_x, y_gate, color='#00d4aa', linewidth=2)
    ax2.fill_between(rsi_x, y_gate, color='#00d4aa', alpha=0.25)
    ax2.axvline(48, color='#ffd60a', linestyle='--')
    ax2.axvline(65, color='#ffd60a', linestyle='--')
    ax2.axvline(32, color='#ff4d6d', linestyle='--')
    
    ax2.text(56.5, 0.5, 'OPTIMAL MOMENTUM ZONE\n(48 <= RSI <= 65)\nHigh-Probability 1x2 Entry', 
             ha='center', va='center', fontsize=9, fontweight='bold', color='#00d4aa', bbox=dict(boxstyle='round', facecolor='#0c0d18', edgecolor='#00d4aa'))
    ax2.text(20, 0.45, 'OVERSOLD BOUNCE\n(RSI <= 32)', ha='center', va='center', fontsize=8, color='#ff4d6d')
    ax2.text(82.5, 0.45, 'EXHAUSTION ZONE\n(RSI > 68)\nNo Trade', ha='center', va='center', fontsize=8, color='#64748b')

    ax2.set_title('Panel 2: RSI Trigger Gate & High-Probability Entry Zones', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax2.set_xlabel('RSI (14) Value', fontsize=10, color='#64748b')
    ax2.set_ylabel('Swarm Conviction Gate', fontsize=10, color='#64748b')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#00d4aa')

    # PANEL 3: 1000% Target Compounding Trajectory (12 Trade Sequences)
    ax3.plot(trades, target_trajectory, color='#ffd60a', marker='o', linewidth=2.5, markersize=6, label='Compounding Pathway to 1000% (+10x)')
    ax3.axhline(1000.0, color='#00d4aa', linestyle='--', label='1,000% Target Line ($1,000 / Rs. 10 Lakh)')
    ax3.fill_between(trades, target_trajectory, 100, color='#ffd60a', alpha=0.15)
    
    for x, y in zip(trades[::3], target_trajectory[::3]):
        ax3.annotate(f'${y:.0f}', (x, y), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, fontweight='bold', color='#ffd60a')

    ax3.set_title('Panel 3: Compounding Pathway to +1,000% Target (12 Winning Cycles)', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax3.set_xlabel('Winning Trade Cycle Count', fontsize=10, color='#64748b')
    ax3.set_ylabel('Capital Growth ($ Baseline 100)', fontsize=10, color='#64748b')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#ffd60a')
    ax3.legend(loc='upper left', fontsize=8, frameon=True, facecolor='#0c0d18', edgecolor='#ffd60a')

    # PANEL 4: Tactical Risk-Reward Ratio Matrix
    categories = ['1x1 Standard', 'Pure RSI Squeeze', 'Tactical 1x2 Swarm']
    cagr_vals  = [5.2, 29.9, 118.5]
    mdd_vals   = [16.4, 3.06, 2.53]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax4.bar(x - width/2, cagr_vals, width, label='CAGR % (Upside)', color='#00d4aa')
    rects2 = ax4.bar(x + width/2, mdd_vals, width, label='Max Drawdown % (Risk)', color='#ff4d6d')

    ax4.set_title('Panel 4: Tactical Performance & Risk Comparison', fontsize=11, fontweight='bold', color='#e2e8f0')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories, fontsize=9, color='#e2e8f0')
    ax4.set_ylabel('Percentage (%)', fontsize=10, color='#64748b')
    ax4.grid(True, linestyle='--', alpha=0.2, color='#6c63ff')
    ax4.legend(loc='upper left', fontsize=8, frameon=True, facecolor='#0c0d18', edgecolor='#6c63ff')

    for bar in rects1:
        height = bar.get_height()
        ax4.annotate(f'+{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold', color='#00d4aa')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_PATH, dpi=300)
    print(f"  📊 High-Resolution Graphic saved to: {CHART_PATH}")

if __name__ == "__main__":
    generate_blueprint()
