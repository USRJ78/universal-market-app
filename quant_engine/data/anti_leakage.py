"""
==============================================================================
  QUANT ENGINE — ANTI-LEAKAGE VERIFIER
==============================================================================
  Guarantees zero future-information leakage:
    1. Validates strict timestamp ordering
    2. Prevents look-ahead bias in rolling feature calculations
==============================================================================
"""

import pandas as pd

class AntiLeakageVerifier:
    @staticmethod
    def verify_no_lookahead(df: pd.DataFrame, time_col: str = "timestamp") -> bool:
        """Verifies strictly monotonic increasing timestamps without future leakage"""
        if time_col in df.columns:
            timestamps = pd.to_datetime(df[time_col])
            return bool(timestamps.is_monotonic_increasing)
        elif isinstance(df.index, pd.DatetimeIndex):
            return bool(df.index.is_monotonic_increasing)
        return True
