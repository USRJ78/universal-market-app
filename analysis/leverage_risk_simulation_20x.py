"""
==============================================================================
  ANTIGRAVITY AI BRAIN — 20X LEVERAGE RISK & LIQUIDATION AUDIT
==============================================================================
"""

import os, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

def simulate_20x_leverage_risk():
    print("=" * 80)
    print("  ⚠️ 20X LEVERAGE RISK & LIQUIDATION MATHEMATICAL AUDIT")
    print("=" * 80)

    capital = 1000.0 # $1,000 Starting Capital
    leverage = 20.0
    position_size = capital * leverage # $20,000 Position Size

    print(f"  Starting Wallet Capital : ${capital:,.2f} USD")
    print(f"  Selected Leverage       : 20x")
    print(f"  Total Position Size     : ${position_size:,.2f} USD\n")

    print("  --------------------------------------------------------------------------")
    print("  MARKET ADVERSE MOVE (%) | CAPITAL LOSS ($ USD) | REMAINING WALLET | STATUS")
    print("  --------------------------------------------------------------------------")

    adverse_moves = [-0.1, -0.5, -1.0, -2.0, -3.0, -4.5, -5.0, -10.0]

    for move_pct in adverse_moves:
        move_frac = move_pct / 100.0
        loss_usd  = position_size * abs(move_frac)
        rem_cap   = max(0.0, capital - loss_usd)
        
        if rem_cap == 0.0 or abs(move_pct) >= 5.0:
            status = "🔴 100% TOTAL LIQUIDATION (WIPEOUT)"
        elif abs(move_pct) >= 3.0:
            status = "⚠️ CRITICAL MARGIN CALL (-60% LOSS)"
        else:
            status = "🟡 ACTIVE HOLD"

        print(f"   {move_pct:>5.1f}% Adverse Move    | -${loss_usd:>8.2f} USD      | ${rem_cap:>8.2f} USD    | {status}")

    print("  --------------------------------------------------------------------------")
    print("  💡 KEY TAKEAWAY: At 20x Leverage, a market drop of just -5.0% wipes out 100% of your account!")
    print("=" * 80)

if __name__ == "__main__":
    simulate_20x_leverage_risk()
