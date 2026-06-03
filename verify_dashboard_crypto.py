# verify_dashboard_crypto.py
import pandas as pd
import numpy as np
import sys
import os
from strategy_helper import StrategyHelper

def verify_integration():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: STRATEGY DASHBOARD CRYPTO INTEGRATION")
    print("====================================================")
    
    # 1. Initialize Helper
    print("\n[Step 1] Instantiating StrategyHelper...")
    try:
        helper = StrategyHelper()
        print(f"[SUCCESS] StrategyHelper initialized. Strategies loaded: {list(helper.strategies.keys())}")
        assert "Crypto UTBot Strategy" in helper.strategies, "Crypto UTBot Strategy must be defined in self.strategies"
        print("[SUCCESS] Crypto UTBot Strategy detected in config.")
    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        return False
        
    # 2. Check Daily Equity Curve loading
    print("\n[Step 2] Testing load_daily_equity_curve for Crypto UTBot Strategy...")
    try:
        curve = helper.load_daily_equity_curve("Crypto UTBot Strategy")
        assert not curve.empty, "Equity curve DataFrame is empty"
        assert "Date" in curve.columns and "Equity" in curve.columns, "Columns must contain 'Date' and 'Equity'"
        print(f"[SUCCESS] Loaded {len(curve)} daily equity records.")
        print(f"   · Start Date: {curve['Date'].min().strftime('%Y-%m-%d')} | Equity: ${curve['Equity'].iloc[0]:,.2f}")
        print(f"   · End Date: {curve['Date'].max().strftime('%Y-%m-%d')} | Equity: ${curve['Equity'].iloc[-1]:,.2f}")
    except Exception as e:
        print(f"[FAIL] Equity curve loading failed: {e}")
        return False
        
    # 3. Check Trade Ledger loading
    print("\n[Step 3] Testing load_strategy_trades for Crypto UTBot Strategy...")
    try:
        trades = helper.load_strategy_trades("Crypto UTBot Strategy")
        assert not trades.empty, "Trades ledger is empty"
        assert "Exit Date" in trades.columns and "Profit" in trades.columns, "Columns must contain 'Exit Date' and 'Profit'"
        print(f"[SUCCESS] Loaded {len(trades)} historical trade logs.")
        print(f"   · Total Gross Profit: ${trades['Profit'].sum():+,.2f}")
        print(f"   · Number of winning trades: {len(trades[trades['Profit'] > 0])}")
        print(f"   · Number of losing trades: {len(trades[trades['Profit'] <= 0])}")
    except Exception as e:
        print(f"[FAIL] Trades ledger loading failed: {e}")
        return False

    # 4. Check Aligned Returns matrix
    print("\n[Step 4] Testing get_aligned_strategy_returns for all strategies...")
    try:
        active_strats = list(helper.strategies.keys())
        aligned = helper.get_aligned_strategy_returns(active_strats)
        assert not aligned.empty, "Aligned returns matrix is empty"
        
        # Verify no NaN values in aligned columns
        for name in active_strats:
            eq_col = f"{name}_Equity"
            ret_col = f"{name}_Return"
            if eq_col in aligned.columns:
                nans_eq = aligned[eq_col].isna().sum()
                nans_ret = aligned[ret_col].isna().sum()
                assert nans_eq == 0, f"Aligned equity column {eq_col} has {nans_eq} NaN values!"
                assert nans_ret == 0, f"Aligned return column {ret_col} has {nans_ret} NaN values!"
                
        print(f"[SUCCESS] Returns aligned perfectly for all {len(active_strats)} strategies.")
        print(f"   · Aligned matrix dimension: {aligned.shape}")
        print(f"   · Start date of alignment: {aligned['Date'].min().strftime('%Y-%m-%d')}")
        print(f"   · End date of alignment: {aligned['Date'].max().strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"[FAIL] Aligned returns mapping failed: {e}")
        return False

    print("\n====================================================")
    print("SUCCESS: ALL CRYPTO STRATEGY DASHBOARD INTEGRATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = verify_integration()
    sys.exit(0 if success else 1)
