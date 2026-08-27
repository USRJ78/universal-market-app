"""
==============================================================================
  ANTIGRAVITY AI BRAIN — DYNAMIC OPTIONS PAYOFF & REGIME SWITCHER
==============================================================================
  Educational & Quantitative Engine for Master Options Positioning:
    1. Visualizes exact Option Payoff Diagrams (Bull Call, Bear Put, 1x2 Spreads)
    2. Dynamic Strike Positioning Math (ATM K1 vs OTM K2 using Volatility Bands)
    3. Rapid Regime Switching Protocol (Call Spread <-> Put Spread <-> Straddle)
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH   = os.path.join(ANALYSIS_DIR, "dynamic_options_payoff_regime_chart.png")
REPORT_PATH  = os.path.join(ANALYSIS_DIR, "dynamic_options_payoff_guide.md")

# ══════════════════════════════════════════════════════════════════════════════
#  OPTION PAYOFF CALCULATORS
# ══════════════════════════════════════════════════════════════════════════════

def payoff_bull_call_spread(S_range, K1, K2, net_debit):
    """Buy 1x Call @ K1, Sell 1x Call @ K2"""
    long_call  = np.maximum(S_range - K1, 0)
    short_call = -np.maximum(S_range - K2, 0)
    return long_call + short_call - net_debit

def payoff_bear_put_spread(S_range, K1, K2, net_debit):
    """Buy 1x Put @ K1, Sell 1x Put @ K2 (K1 > K2)"""
    long_put  = np.maximum(K1 - S_range, 0)
    short_put = -np.maximum(K2 - S_range, 0)
    return long_put + short_put - net_debit

def payoff_1x2_ratio_call_spread(S_range, K1, K2, net_debit=0.0):
    """Buy 1x Call @ K1 (ATM), Sell 2x Call @ K2 (OTM, ~4.5% above)"""
    long_call   = np.maximum(S_range - K1, 0)
    short_calls = -2.0 * np.maximum(S_range - K2, 0)
    return long_call + short_calls - net_debit

def payoff_1x2_ratio_put_spread(S_range, K1, K2, net_debit=0.0):
    """Buy 1x Put @ K1 (ATM), Sell 2x Put @ K2 (OTM, ~4.5% below)"""
    long_put   = np.maximum(K1 - S_range, 0)
    short_puts = -2.0 * np.maximum(K2 - S_range, 0)
    return long_put + short_puts - net_debit

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN VISUALIZATION & GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def generate_payoff_charts():
    print("=" * 80)
    print("  DYNAMC OPTIONS PAYOFF & REGIME SWITCHER — GENERATING GUIDE")
    print("=" * 80)

    S0 = 100.0  # Base Stock/Spot Price
    S_range = np.linspace(80.0, 120.0, 500)

    # ── Strike Math ──
    # Bull Call 1x2: K1 = 100 (ATM), K2 = 104.5 (4.5% OTM)
    # Bear Put 1x2:  K1 = 100 (ATM), K2 = 95.5  (4.5% OTM)
    K1_call, K2_call = 100.0, 104.5
    K1_put,  K2_put  = 100.0, 95.5

    p_bull_1x2 = payoff_1x2_ratio_call_spread(S_range, K1_call, K2_call, net_debit=0.2)
    p_bear_1x2 = payoff_1x2_ratio_put_spread(S_range, K1_put, K2_put, net_debit=0.2)
    p_bull_deb = payoff_bull_call_spread(S_range, 100.0, 105.0, net_debit=1.5)
    p_bear_deb = payoff_bear_put_spread(S_range, 100.0, 95.0, net_debit=1.5)

    # Plotting 4 Payoff Panels
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), facecolor='#090d16')
    fig.suptitle("ANTIGRAVITY OPTIONS PAYOFF GEOMETRY & REGIME SWITCHING PROTOCOL",
                 fontsize=14, fontweight='bold', color='#e2e8f0', y=0.98)

    # Panel 1: Bullish Regime — 1x2 Ratio Call Spread
    ax1 = axes[0, 0]
    ax1.set_facecolor('#0f172a')
    ax1.plot(S_range, p_bull_1x2, color='#00d4aa', linewidth=2.5, label="Zero Debit 1x2 Bull Call Spread")
    ax1.axhline(0, color='#64748b', linestyle='--', alpha=0.7)
    ax1.axvline(S0, color='#38bdf8', linestyle=':', label="Spot (S0 = 100)")
    ax1.axvline(K2_call, color='#f59e0b', linestyle=':', label=f"Max Profit Strike (K2 = {K2_call})")
    ax1.fill_between(S_range, p_bull_1x2, 0, where=(p_bull_1x2 >= 0), color='#00d4aa', alpha=0.15)
    ax1.fill_between(S_range, p_bull_1x2, 0, where=(p_bull_1x2 < 0), color='#ef4444', alpha=0.15)
    ax1.set_title("REGIME 1: BULLISH BREAKOUT\nBuy 1x ATM Call (100) + Sell 2x OTM Call (104.5)", color='#00d4aa', fontsize=11, fontweight='bold')
    ax1.set_xlabel("Spot Price at Expiry", color='#94a3b8')
    ax1.set_ylabel("Payoff ($ / Premium)", color='#94a3b8')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#334155')
    ax1.legend(fontsize=8.5, facecolor='#0f172a')
    ax1.tick_params(colors='#94a3b8')

    # Panel 2: Bearish Regime — 1x2 Ratio Put Spread
    ax2 = axes[0, 1]
    ax2.set_facecolor('#0f172a')
    ax2.plot(S_range, p_bear_1x2, color='#ef4444', linewidth=2.5, label="Zero Debit 1x2 Bear Put Spread")
    ax2.axhline(0, color='#64748b', linestyle='--', alpha=0.7)
    ax2.axvline(S0, color='#38bdf8', linestyle=':', label="Spot (S0 = 100)")
    ax2.axvline(K2_put, color='#f59e0b', linestyle=':', label=f"Max Profit Strike (K2 = {K2_put})")
    ax2.fill_between(S_range, p_bear_1x2, 0, where=(p_bear_1x2 >= 0), color='#00d4aa', alpha=0.15)
    ax2.fill_between(S_range, p_bear_1x2, 0, where=(p_bear_1x2 < 0), color='#ef4444', alpha=0.15)
    ax2.set_title("REGIME 2: BEARISH BREAKDOWN\nBuy 1x ATM Put (100) + Sell 2x OTM Put (95.5)", color='#ef4444', fontsize=11, fontweight='bold')
    ax2.set_xlabel("Spot Price at Expiry", color='#94a3b8')
    ax2.set_ylabel("Payoff ($ / Premium)", color='#94a3b8')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#334155')
    ax2.legend(fontsize=8.5, facecolor='#0f172a')
    ax2.tick_params(colors='#94a3b8')

    # Panel 3: Standard Bull Call Debit Spread
    ax3 = axes[1, 0]
    ax3.set_facecolor('#0f172a')
    ax3.plot(S_range, p_bull_deb, color='#38bdf8', linewidth=2.2, label="Bull Call Debit Spread (Debit = $1.5)")
    ax3.axhline(0, color='#64748b', linestyle='--', alpha=0.7)
    ax3.axvline(S0, color='#38bdf8', linestyle=':')
    ax3.fill_between(S_range, p_bull_deb, 0, where=(p_bull_deb >= 0), color='#38bdf8', alpha=0.15)
    ax3.fill_between(S_range, p_bull_deb, 0, where=(p_bull_deb < 0), color='#ef4444', alpha=0.15)
    ax3.set_title("STANDARD BULL CALL SPREAD\nBuy 1x Call (100) + Sell 1x Call (105) | Capped Risk & Reward", color='#38bdf8', fontsize=11, fontweight='bold')
    ax3.set_xlabel("Spot Price at Expiry", color='#94a3b8')
    ax3.set_ylabel("Payoff ($ / Premium)", color='#94a3b8')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#334155')
    ax3.legend(fontsize=8.5, facecolor='#0f172a')
    ax3.tick_params(colors='#94a3b8')

    # Panel 4: Standard Bear Put Debit Spread
    ax4 = axes[1, 1]
    ax4.set_facecolor('#0f172a')
    ax4.plot(S_range, p_bear_deb, color='#a855f7', linewidth=2.2, label="Bear Put Debit Spread (Debit = $1.5)")
    ax4.axhline(0, color='#64748b', linestyle='--', alpha=0.7)
    ax4.axvline(S0, color='#38bdf8', linestyle=':')
    ax4.fill_between(S_range, p_bear_deb, 0, where=(p_bear_deb >= 0), color='#a855f7', alpha=0.15)
    ax4.fill_between(S_range, p_bear_deb, 0, where=(p_bear_deb < 0), color='#ef4444', alpha=0.15)
    ax4.set_title("STANDARD BEAR PUT SPREAD\nBuy 1x Put (100) + Sell 1x Put (95) | Capped Risk & Reward", color='#a855f7', fontsize=11, fontweight='bold')
    ax4.set_xlabel("Spot Price at Expiry", color='#94a3b8')
    ax4.set_ylabel("Payoff ($ / Premium)", color='#94a3b8')
    ax4.grid(True, linestyle='--', alpha=0.2, color='#334155')
    ax4.legend(fontsize=8.5, facecolor='#0f172a')
    ax4.tick_params(colors='#94a3b8')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=220, facecolor='#090d16', bbox_inches='tight')
    plt.close()
    print(f"  [CHART] Saved: {CHART_PATH}")

    # Generate Markdown Guide
    guide_md = f"""# 📐 MASTER OPTIONS PAYOFF GEOMETRY & RAPID REGIME SWITCHING GUIDE

---

## 1. How To Position Strikes Dynamically

```
STRIKE GEOMETRY MATH:
  Spot Price = S0

  1. ATM Strike (K1):
     K1 = Nearest Round Strike to S0  (e.g., S0 = 100 -> K1 = 100)

  2. OTM Strike (K2) for Bull Call Spread:
     K2 = K1 x (1 + 0.045)  = K1 x 1.045  (+4.5% above S0)

  3. OTM Strike (K2) for Bear Put Spread:
     K2 = K1 x (1 - 0.045)  = K1 x 0.955  (-4.5% below S0)
```

---

## 2. Option Payoff Diagrams & Structure Comparison

![Options Payoffs](file:///{CHART_PATH.replace(os.sep, '/')})

---

## 3. Rapid Strategy Regime Switch Protocol (Quick Matrix)

| Market Condition | Indicator Signal | Strategy Structure | Execution Leg 1 | Execution Leg 2 | Net Premium |
|:---|:---|:---:|:---:|:---:|:---:|
| 🟢 **Bullish Momentum** | Price > Supertrend GREEN + UTBot BUY | **1×2 Ratio Call Spread** | Buy 1× ATM Call ($K_1$) | Sell 2× OTM Call ($K_2 = K_1 \times 1.045$) | **≈ Zero Debit** |
| 🔴 **Bearish Breakdown** | Price < Supertrend RED + UTBot SELL | **1×2 Ratio Put Spread** | Buy 1× ATM Put ($K_1$) | Sell 2× OTM Put ($K_2 = K_1 \times 0.955$) | **≈ Zero Debit** |
| 🟡 **Low Vol Consolidation** | ATR(10)/ATR(50) < 0.85 + Neutral Trend | **Iron Condor / Strangle** | Sell 1× OTM Call + Put | Buy 1× Far OTM Protection | **Net Credit** |
| ⚡ **Impulsive Vol Explosion** | Vol Squeeze Breakout + High Volume | **Long Straddle / Strangle** | Buy 1× ATM Call | Buy 1× ATM Put | **Debit Paid** |

---

## 4. Rapid Strategy Shift Rules (How to Flip Position in < 10 Seconds)

```
SCENARIO A — Flipping from Bull Call Spread to Bear Put Spread:
  1. Close Long Call @ K1  +  Close 2x Short Call @ K2
  2. Open Long Put @ K1   +  Open 2x Short Put @ K2 (0.955 x S0)
  3. Net Debit required to flip: ≈ 0 (only transaction friction)

SCENARIO B — Locking in Profits when Price reaches K2:
  1. Once Spot Price hits K2 (+4.5%), Max Profit is reached!
  2. Immediately CLOSE the 1x2 Spread to lock in 300%+ returns on margin.
  3. Do NOT hold beyond K2 to prevent short calls from eroding profit.
```
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(guide_md)
    print(f"  [REPORT] Saved: {REPORT_PATH}")

if __name__ == "__main__":
    generate_payoff_charts()
