# verify_crypto_dashboard.py
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
from crypto_strategy_helper import CryptoStrategyHelper

def verify_crypto_integration():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: CRYPTO STRATEGY DASHBOARD")
    print("====================================================")
    
    # 1. Initialize Helper
    print("\n[Step 1] Instantiating CryptoStrategyHelper...")
    try:
        helper = CryptoStrategyHelper()
        print(f"[SUCCESS] CryptoStrategyHelper initialized. Available strategies: {list(helper.strategies.keys())}")
        assert len(helper.strategies) == 6, "Must have exactly 6 crypto strategies defined."
    except Exception as e:
        print(f"[FAIL] Helper initialization failed: {e}")
        return False

    # 2. Fetch data for testing
    print("\n[Step 2] Fetching historical data (short window for speed)...")
    coins = ["BTC", "ETH"]
    # 60 days buffer warm-up + 10 days testing = 70 days window
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    try:
        raw_data = helper.fetch_historical_prices(coins, start_date, end_date)
        assert len(raw_data) == 2, "Failed to download test data for BTC and ETH."
        print(f"[SUCCESS] Historical prices loaded. BTC length: {len(raw_data['BTC'])}, ETH length: {len(raw_data['ETH'])}")
    except Exception as e:
        print(f"[FAIL] Data loading failed: {e}")
        return False

    # 3. Compute indicators
    print("\n[Step 3] Computing indicators (ATR, EMAs, RSI, UTBot)...")
    processed_data = {}
    try:
        for coin, df in raw_data.items():
            processed = helper.compute_indicators(df, atr_period=10, ut_mult=1.0)
            assert "Close" in processed.columns, "Missing close price"
            assert "ATR10" in processed.columns, "Missing ATR10"
            assert "RSI14" in processed.columns, "Missing RSI"
            assert "EMA50" in processed.columns, "Missing EMA50"
            assert "trend" in processed.columns, "Missing UTBot trend"
            
            # Make sure no lookahead bias in helper prev columns
            assert "EMA5_prev" in processed.columns, "Missing EMA5_prev"
            assert "High20_prev" in processed.columns, "Missing High20_prev"
            processed_data[coin] = processed
        print("[SUCCESS] Indicators computed successfully for all test coins.")
    except Exception as e:
        print(f"[FAIL] Indicator calculation failed: {e}")
        return False

    # 4. Simulate each of the 6 strategies
    print("\n[Step 4] Simulating all 6 strategies on test coins...")
    sim_results = {}
    capital = 100000.0
    fee_pct = 0.001
    slip_pct = 0.0005
    
    strategies_runners = {
        "Discount Coin Strategy (DCS)": helper.simulate_dcs,
        "Chess Trading Strategy": helper.simulate_chess,
        "HFT Vector Bundle": helper.simulate_hft,
        "Market Geometry Strategy": helper.simulate_geometry,
        "Basket Selection Strategy (BSS)": helper.simulate_bss,
        "Crypto Arbitrage": helper.simulate_arbitrage
    }
    
    for name, runner in strategies_runners.items():
        try:
            print(f"   · Running {name}...")
            eq_curve, trades = runner(processed_data, start_date, capital, fee_pct, slip_pct)
            
            assert isinstance(eq_curve, pd.DataFrame), f"{name} must return an equity curve DataFrame"
            assert isinstance(trades, pd.DataFrame), f"{name} must return a trades ledger DataFrame"
            assert not eq_curve.empty, f"{name} equity curve should not be empty"
            assert "Equity" in eq_curve.columns, f"{name} equity curve must contain 'Equity' column"
            
            sim_results[name] = (eq_curve, trades)
            print(f"     [SUCCESS] curve len: {len(eq_curve)}, trades count: {len(trades)}")
        except Exception as e:
            print(f"     [FAIL] {name} simulation failed: {e}")
            return False

    # 5. Check Aligned returns matrix
    print("\n[Step 5] Creating and checking aligned returns matrix...")
    try:
        aligned = helper.get_aligned_strategy_returns(sim_results)
        assert isinstance(aligned, pd.DataFrame), "Aligned returns must be a DataFrame"
        assert "Date" in aligned.columns, "Aligned returns must contain 'Date' column"
        assert not aligned.empty, "Aligned returns DataFrame is empty"
        
        # Verify no NaN values in aligned columns
        for name in helper.strategies.keys():
            eq_col = f"{name}_Equity"
            ret_col = f"{name}_Return"
            assert eq_col in aligned.columns, f"Missing {eq_col}"
            assert ret_col in aligned.columns, f"Missing {ret_col}"
            
            nans_eq = aligned[eq_col].isna().sum()
            nans_ret = aligned[ret_col].isna().sum()
            assert nans_eq == 0, f"Aligned equity column {eq_col} has {nans_eq} NaN values!"
            assert nans_ret == 0, f"Aligned return column {ret_col} has {nans_ret} NaN values!"
            
        print(f"[SUCCESS] Aligned returns matrix verified with dimensions: {aligned.shape}")
        print(f"   · Start date: {aligned['Date'].min().strftime('%Y-%m-%d')}")
        print(f"   · End date: {aligned['Date'].max().strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"[FAIL] Aligned returns checks failed: {e}")
        return False

    # 6. Test Risk Metrics calculation
    print("\n[Step 6] Testing Risk Metrics calculation...")
    try:
        test_curve = sim_results["Discount Coin Strategy (DCS)"][0]
        metrics = helper.calculate_metrics(test_curve, capital)
        assert "CAGR" in metrics, "Missing CAGR in metrics output"
        assert "Sharpe" in metrics, "Missing Sharpe in metrics output"
        assert "Max_DD" in metrics, "Missing Max_DD in metrics output"
        assert "Total_Return" in metrics, "Missing Total_Return in metrics"
        assert "Ending_Capital" in metrics, "Missing Ending_Capital in metrics"
        print(f"[SUCCESS] Metrics calculated successfully: Sharpe={metrics['Sharpe']:.2f}, MaxDD={metrics['Max_DD']:.2f}%")
    except Exception as e:
        print(f"[FAIL] Metrics calculation failed: {e}")
        return False

    print("\n====================================================")
    print("SUCCESS: ALL CRYPTO STRATEGIES AND INTEGRATION CHECKS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = verify_crypto_integration()
    sys.exit(0 if success else 1)
