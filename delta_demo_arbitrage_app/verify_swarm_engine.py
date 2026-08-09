# verify_swarm_engine.py
import sys
import os
import pandas as pd

# Ensure local directory is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import swarm_bot_engine

def test_swarm_components():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: SWARM BOT PATTERN ANALYZER")
    print("====================================================")
    
    # 1. Test asset basket definitions
    print("\n[Step 1] Verifying asset baskets configuration...")
    try:
        assert len(swarm_bot_engine.ASSETS) == 4, "Must define 4 categories (Crypto, Stocks, Bonds, Indices)"
        assert len(swarm_bot_engine.ALL_TICKERS) == 13, "Must define all 13 asset tickers"
        print(f"[SUCCESS] Asset configurations loaded. Total tickers: {len(swarm_bot_engine.ALL_TICKERS)}")
    except Exception as e:
        print(f"[FAIL] Asset configuration verify failed: {e}")
        return False

    # 2. Test yfinance data download & warm-up formatting
    print("\n[Step 2] Testing yfinance historical downloading for subset assets...")
    test_tickers = ["BTC-USD", "AAPL", "TLT"]
    try:
        for ticker in test_tickers:
            t, df = swarm_bot_engine.fetch_asset_data(ticker)
            assert df is not None, f"Dataframe for {ticker} must load successfully"
            assert len(df) >= 30, f"Dataframe for {ticker} must contain historical warm-up buffer"
            print(f"[SUCCESS] Sourced {len(df)} candles for {ticker}.")
    except Exception as e:
        print(f"[FAIL] Data downloading test failed: {e}")
        return False

    # 3. Test variable calculations (EMA, RSI, Bollinger Bands, Channel, Z-score)
    print("\n[Step 3] Verifying mathematical calculations on indicators...")
    try:
        _, sample_df = swarm_bot_engine.fetch_asset_data("BTC-USD")
        calc_df = swarm_bot_engine.compute_indicators(sample_df)
        
        required_cols = ["EMA_fast", "EMA_slow", "RSI", "BB_upper", "BB_lower", "High_chan", "Low_chan", "Zscore"]
        for col in required_cols:
            assert col in calc_df.columns, f"Indicator column {col} must exist"
            assert not calc_df[col].dropna().empty, f"Indicator column {col} must contain calculated values"
            
        print(f"[SUCCESS] All technical variables computed successfully on sample DataFrame.")
    except Exception as e:
        print(f"[FAIL] Calculations check failed: {e}")
        return False

    # 4. Test virtual bug rule triggers evaluation
    print("\n[Step 4] Testing bug signal rules triggers evaluation...")
    try:
        anomalies = swarm_bot_engine.evaluate_bug_rules("BTC-USD", calc_df, 100)
        print(f"[SUCCESS] Bug rules evaluated successfully. Signal anomalies detected: {len(anomalies)}")
        if len(anomalies) > 0:
            sample = anomalies[0]
            print(f"         · Sample Alert: {sample['asset']} | {sample['pattern']} | {sample['direction']} | Strength: {sample['strength']}")
    except Exception as e:
        print(f"[FAIL] Signal rules test failed: {e}")
        return False

    print("\n====================================================")
    print("SUCCESS: ALL PROGRAMMATIC SWARM VALIDATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = test_swarm_components()
    sys.exit(0 if success else 1)
