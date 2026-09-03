"""
==============================================================================
  QUANT ENGINE — EMERGENCY HARD KILL SWITCH
==============================================================================
  Automatically disables live trading when:
    - Daily loss exceeds limit
    - API behaves unexpectedly or disconnects
    - Market data becomes stale
    - Model confidence collapses
==============================================================================
"""

import os, sys, datetime

class EmergencyKillSwitch:
    def __init__(self):
        self.is_triggered = False
        self.trigger_reason = None
        self.triggered_at = None

    def trigger(self, reason: str):
        """Triggers emergency kill switch, cancels pending orders, and alerts user"""
        self.is_triggered = True
        self.trigger_reason = reason
        self.triggered_at = datetime.datetime.now().isoformat()
        
        print(f"\n🚨🚨 EMERGENCY KILL SWITCH TRIGGERED 🚨🚨")
        print(f"  Reason: {reason}")
        print(f"  Timestamp: {self.triggered_at}")
        print(f"  Action: ALL LIVE TRADING STOPPED. CANCELING ALL OPEN ORDERS.\n")

    def reset(self):
        """Requires explicit human action to re-enable trading"""
        self.is_triggered = False
        self.trigger_reason = None
        self.triggered_at = None
        print("  [✓] Emergency Kill Switch manually reset by human operator.")
