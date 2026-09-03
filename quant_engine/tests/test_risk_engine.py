"""
==============================================================================
  QUANT ENGINE TESTS — DETERMINISTIC RISK ENGINE & KILL SWITCH VERIFICATION
==============================================================================
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

from quant_engine.risk.risk_manager import RiskEngine
from quant_engine.risk.kill_switch import EmergencyKillSwitch

def test_risk_engine_bounds():
    risk = RiskEngine()
    portfolio_normal = {"total_equity": 100000.0, "daily_pnl_pct": -0.01}
    trade_proposed   = {"allocation_pct": 0.50, "entry_price": 100.0}

    res = risk.validate_trade(portfolio_normal, trade_proposed)
    assert res["approved"] == True
    assert res["allocation_pct"] <= 0.35 # Position capped at 35%
    print("  [PASSED] Position Cap Limit Test Passed!")

    portfolio_breached = {"total_equity": 100000.0, "daily_pnl_pct": -0.06}
    res_breached = risk.validate_trade(portfolio_breached, trade_proposed)
    assert res_breached["approved"] == False # Rejected due to daily loss breach
    print("  [PASSED] Daily Loss Limit Rejection Test Passed!")

def test_kill_switch():
    ks = EmergencyKillSwitch()
    assert ks.is_triggered == False
    ks.trigger("Simulated API Disconnect")
    assert ks.is_triggered == True
    print("  [PASSED] Emergency Kill Switch Test Passed!")

if __name__ == "__main__":
    test_risk_engine_bounds()
    test_kill_switch()
