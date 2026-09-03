"""
==============================================================================
  UNIT TESTS — J.A.R.V.I.S. QUANTITATIVE COMMANDER & GUARDIAN PROTOCOL
==============================================================================
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

from quant_engine.jarvis.jarvis_commander import GuardianProtocol, JarvisCommander


def test_guardian_steamroller_veto():
    """Verify that risking $500 for a $17 profit is strictly vetoed!"""
    steamroller_setup = {
        "max_loss": 500.0,
        "max_gain": 17.0,      # Asymmetric disaster: R:R = 1:0.034
        "conviction": 0.80,
        "is_unhedged_naked": False
    }
    res = GuardianProtocol.audit_trade(steamroller_setup, equity=10000.0)
    assert res["approved"] is False
    assert res["code"] == "STEAMROLLER_RISK"
    print("  [PASSED] Guardian successfully vetoed steamroller risk ($500 risk for $17 profit)!")


def test_guardian_naked_risk_veto():
    """Verify that unhedged/naked risk is strictly vetoed!"""
    naked_setup = {
        "max_loss": 100.0,
        "max_gain": 300.0,
        "conviction": 0.85,
        "is_unhedged_naked": True  # Naked short leg!
    }
    res = GuardianProtocol.audit_trade(naked_setup, equity=10000.0)
    assert res["approved"] is False
    assert res["code"] == "UNBOUNDED_RISK"
    print("  [PASSED] Guardian successfully vetoed unhedged naked risk!")


def test_guardian_approved_asymmetric_trade():
    """Verify that a defined-risk trade with 1:3 R:R is approved!"""
    good_setup = {
        "max_loss": 120.0,     # 1.2% equity risk
        "max_gain": 360.0,     # 1:3.0 R:R
        "conviction": 0.75,
        "is_unhedged_naked": False
    }
    res = GuardianProtocol.audit_trade(good_setup, equity=10000.0)
    assert res["approved"] is True
    assert res["code"] == "PERFECT_GEOMETRY"
    print("  [PASSED] Guardian successfully approved 1:3 asymmetric trade!")


def test_jarvis_radar_sweep():
    """Verify Jarvis 5-D radar scan and executive briefing generation."""
    jarvis = JarvisCommander()
    prices = {"BTC": 64250.0, "ETH": 3490.0, "SOL": 149.2}
    sweep = jarvis.run_full_radar_sweep(prices, equity=10000.0)
    
    assert "briefing" in sweep
    assert len(sweep["radar"]) == 3
    assert sweep["guardian_status"] == "ACTIVE_ARMED"
    print("  [PASSED] J.A.R.V.I.S. Radar Sweep & Executive Briefing verified!")
    print(f"  [BRIEFING PREVIEW]: {sweep['briefing'][:120]}...")


if __name__ == "__main__":
    test_guardian_steamroller_veto()
    test_guardian_naked_risk_veto()
    test_guardian_approved_asymmetric_trade()
    test_jarvis_radar_sweep()
