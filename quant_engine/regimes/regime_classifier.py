"""
==============================================================================
  QUANT ENGINE — MARKET REGIME CLASSIFIER
==============================================================================
"""

import numpy as np
import pandas as pd

class MarketRegimeEngine:
    REGIMES = [
        "BULL_LOW_VOL", "BULL_HIGH_VOL",
        "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
        "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
        "PANIC", "TRANSITION"
    ]

    def __init__(self):
        pass

    def classify_regime(self, df: pd.DataFrame) -> str:
        """Classifies current market state into one of 8 distinct regimes"""
        if df.empty or len(df) < 30:
            return "BULL_LOW_VOL"

        returns_20 = df["Close"].pct_change(20).iloc[-1]
        volatility = df["Close"].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
        med_vol    = df["Close"].pct_change().rolling(100).std().median() * np.sqrt(252)

        if volatility > med_vol * 2.5 and returns_20 < -0.10:
            return "PANIC"
        
        is_bull = returns_20 > 0.02
        is_bear = returns_20 < -0.02
        is_high_vol = volatility > med_vol

        if is_bull:
            return "BULL_HIGH_VOL" if is_high_vol else "BULL_LOW_VOL"
        elif is_bear:
            return "BEAR_HIGH_VOL" if is_high_vol else "BEAR_LOW_VOL"
        else:
            return "SIDEWAYS_HIGH_VOL" if is_high_vol else "SIDEWAYS_LOW_VOL"
