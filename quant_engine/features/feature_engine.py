"""
==============================================================================
  QUANT ENGINE — ADVANCED FEATURE ENGINEERING ENGINE
==============================================================================
"""

import numpy as np
import pandas as pd

class FeatureEngineeringEngine:
    def __init__(self):
        pass

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generates Price, Volatility, Volume, Geometry, and Interaction features"""
        if df.empty or len(df) < 50:
            return df

        data = df.copy()
        close = data["Close"]
        high  = data["High"]
        low   = data["Low"]
        vol   = data["Volume"]

        # 1. Price Features
        data["returns_1d"] = close.pct_change().fillna(0)
        data["returns_5d"] = close.pct_change(5).fillna(0)
        data["momentum_20"] = close / close.shift(20) - 1.0
        data["acceleration"] = data["returns_1d"] - data["returns_1d"].shift(1)
        
        h52 = close.rolling(252, min_periods=20).max()
        l52 = close.rolling(252, min_periods=20).min()
        data["dist_from_high_52"] = (close - h52) / (h52 + 1e-9)
        data["dist_from_low_52"]  = (close - l52) / (l52 + 1e-9)
        data["breakout_distance"] = (close - close.rolling(20).max()) / (close.rolling(20).max() + 1e-9)

        # 2. Volatility Features
        ret_std_10 = data["returns_1d"].rolling(10).std()
        ret_std_50 = data["returns_1d"].rolling(50).std()
        data["volatility_compression"] = ret_std_10 / (ret_std_50 + 1e-9)
        data["volatility_expansion"]   = ret_std_10 * np.sqrt(252)

        # ATR Calculation
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        data["atr_14"] = tr.rolling(14).mean()

        # 3. Volume Features
        vol_mean_20 = vol.rolling(20).mean()
        data["relative_volume"] = vol / (vol_mean_20 + 1e-9)
        data["volume_zscore"]   = (vol - vol_mean_20) / (vol.rolling(20).std() + 1e-9)

        # 4. Geometry & Fibonacci Features
        swing_high = high.rolling(50, min_periods=10).max()
        swing_low  = low.rolling(50, min_periods=10).min()
        swing_range = swing_high - swing_low + 1e-9
        
        data["fib_retracement_618"] = (close - swing_low) / (swing_range * 0.618)
        data["fib_distance"]        = (close - (swing_low + swing_range * 0.618)).abs() / (close + 1e-9)
        data["geometry_score"]      = np.tanh((close - swing_low) / swing_range * 2.0 - 1.0)

        # 5. Interaction Features
        data["momentum_x_volatility"]     = data["momentum_20"] * data["volatility_expansion"]
        data["vol_comp_x_breakout"]      = data["volatility_compression"] * data["breakout_distance"]
        data["volume_z_x_momentum"]      = data["volume_zscore"] * data["momentum_20"]
        data["fib_distance_x_momentum"]  = data["fib_distance"] * data["momentum_20"]

        data.fillna(0, inplace=True)
        return data
