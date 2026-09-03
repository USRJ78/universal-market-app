"""
==============================================================================
  QUANT ENGINE — MULTI-ASSET MARKET DATA PIPELINE
==============================================================================
"""

import os, time, pandas as pd, numpy as np, yfinance as yf
from quant_engine.data.anti_leakage import AntiLeakageVerifier

class MarketDataPipeline:
    def __init__(self):
        self.verifier = AntiLeakageVerifier()

    def fetch_market_data(self, symbol="BTC-USD", period="1y", interval="1d"):
        """Fetches OHLCV and computes basic returns without look-ahead bias"""
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df.dropna(inplace=True)

            if not self.verifier.verify_no_lookahead(df):
                raise ValueError("Look-ahead bias detected in fetched dataset!")

            df["returns"] = df["Close"].pct_change().fillna(0)
            df["log_returns"] = np.log(df["Close"] / df["Close"].shift(1)).fillna(0)
            df["volume_usd"] = df["Close"] * df["Volume"]
            df["realized_vol_20"] = df["returns"].rolling(20).std() * np.sqrt(252)
            
            return df
        except Exception as e:
            print(f"Data Fetch Error ({symbol}): {e}")
            return pd.DataFrame()
