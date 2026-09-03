"""
==============================================================================
  QUANT ENGINE — PATTERN DISCOVERY ENGINE & OOS STATISTICAL VALIDATOR
==============================================================================
"""

import numpy as np
import pandas as pd

class PatternDiscoveryEngine:
    def __init__(self):
        pass

    def mine_patterns(self, df: pd.DataFrame, horizons=[5, 10, 20, 60]) -> list:
        """Discovers statistical market state relationships and validates OOS performance"""
        discovered = []

        if df.empty or "volatility_compression" not in df.columns:
            return discovered

        for h in horizons:
            future_ret = df["Close"].pct_change(h).shift(-h)
            
            # Candidate Pattern #1: Volatility Compression + Breakout Distance
            cond1 = (df["volatility_compression"] < 0.85) & (df["breakout_distance"] > 0.0)
            sample1 = future_ret[cond1].dropna()

            if len(sample1) >= 20:
                win_rate = float((sample1 > 0).mean() * 100.0)
                exp_ret  = float(sample1.mean() * 100.0)
                sharpe   = float((sample1.mean() / (sample1.std() + 1e-9)) * np.sqrt(252 / h))

                # Split Out-of-Sample Test (Last 30% of data)
                split_idx = int(len(sample1) * 0.7)
                insample  = sample1.iloc[:split_idx]
                outsample = sample1.iloc[split_idx:]

                oos_win_rate = float((outsample > 0).mean() * 100.0) if len(outsample) > 5 else win_rate
                oos_sharpe   = float((outsample.mean() / (outsample.std() + 1e-9)) * np.sqrt(252 / h)) if len(outsample) > 5 else sharpe

                # OOS Filter: Reject patterns that disappear out-of-sample
                if oos_win_rate >= 50.0 and oos_sharpe > 0.5:
                    discovered.append({
                        "pattern_id": f"PATTERN-VOLCOMP-{h}D",
                        "horizon": f"{h}D",
                        "condition": "volatility_compression < 0.85 & breakout > 0",
                        "sample_size": len(sample1),
                        "win_rate": round(win_rate, 1),
                        "expected_return": round(exp_ret, 2),
                        "sharpe": round(sharpe, 2),
                        "oos_win_rate": round(oos_win_rate, 1),
                        "oos_sharpe": round(oos_sharpe, 2),
                        "is_valid": True
                    })

        return discovered
