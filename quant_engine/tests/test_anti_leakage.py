"""
==============================================================================
  QUANT ENGINE TESTS — ANTI-LEAKAGE AUTOMATED VERIFICATION
==============================================================================
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

import pandas as pd
from quant_engine.data.anti_leakage import AntiLeakageVerifier

def test_anti_leakage_verifier():
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df_valid = pd.DataFrame({"timestamp": dates, "price": range(10)})
    assert AntiLeakageVerifier.verify_no_lookahead(df_valid) == True
    print("  [PASSED] Anti-Leakage Verifier Test Passed!")

if __name__ == "__main__":
    test_anti_leakage_verifier()
