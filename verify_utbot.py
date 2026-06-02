# verify_utbot.py
import pandas as pd
import numpy as np
import os
import sys
import importlib.util

def test_utbot_calculations():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: CRYPTO UTBOT STRATEGY")
    print("====================================================")
    
    # 1. Generate realistic synthetic daily price data
    print("\n[Step 1] Creating synthetic price dataset...")
    dates = pd.date_range(start="2026-01-01", periods=100, freq="D")
    
    np.random.seed(42)
    base_price = 100.0
    price_series = []
    for i in range(100):
        base_price += np.sin(i / 5.0) * 3.0 + np.random.normal(0, 1.5) + 0.5
        price_series.append(base_price)
        
    df = pd.DataFrame({
        "Close": price_series,
        "High": [p * 1.02 for p in price_series],
        "Low": [p * 0.98 for p in price_series]
    }, index=dates)
    
    print(f"[SUCCESS] Synthetic dataset created: {len(df)} records. Starting close: {df['Close'].iloc[0]:.2f}, Ending close: {df['Close'].iloc[-1]:.2f}")

    # 2. Dynamic loading ofpages/8_Crypto_UT_Bot_Backtester.py using importlib
    print("\n[Step 2] Dynamically loading pages/8_Crypto_UT_Bot_Backtester.py...")
    try:
        module_path = os.path.join("pages", "8_Crypto_UT_Bot_Backtester.py")
        spec = importlib.util.spec_from_file_location("Crypto_UT_Bot_Backtester", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        compute_utbot = module.compute_utbot
        run_utbot_backtest = module.run_utbot_backtest
        print("[SUCCESS] Dashboard module dynamically loaded without syntax constraints.")
    except Exception as e:
        print(f"[FAIL] Module dynamic loading failed: {e}")
        return False

    # 3. Test compute_utbot implementation
    print("\n[Step 3] Testing compute_utbot signal generation math...")
    try:
        df = compute_utbot(df, atr_p=10, mult=1.0)
        
        required_cols = ["tr", "atr", "upper", "lower", "trend", "buy", "sell"]
        for col in required_cols:
            assert col in df.columns, f"Required column '{col}' is missing from output DataFrame"
            
        print("[SUCCESS] All required math columns are present in compute_utbot output.")
        
        unique_trends = df["trend"].dropna().unique()
        assert set(unique_trends).issubset({1, -1}), f"Trend column contains unexpected values: {unique_trends}"
        print("[SUCCESS] UTBot trends are binary (1 for Bullish, -1 for Bearish) as expected.")
        
        buy_signals = df[df["buy"] == True]
        sell_signals = df[df["sell"] == True]
        print(f"[SUCCESS] Computed {len(buy_signals)} BUY alerts and {len(sell_signals)} SELL alerts cleanly.")
    except Exception as e:
        print(f"[FAIL] compute_utbot execution failed: {e}")
        return False

    # 4. Test run_utbot_backtest simulator
    print("\n[Step 4] Executing portfolio transaction simulator...")
    try:
        cap = 10000.0
        fee_pct = 0.001
        slip_pct = 0.001
        
        # Inject standard coin name as mock reference in global namespace if needed by the function
        # Since 'coin' is referenced globally inside run_utbot_backtest for logging, let's inject it into module namespace!
        module.coin = "BTC"
        
        equity_series, trades = run_utbot_backtest(df, "2026-01-15", cap, fee_pct, slip_pct)
        
        assert not equity_series.empty, "Equity curve output series is empty"
        print(f"[SUCCESS] Transaction backtester executed cleanly.")
        print(f"   · Starting capital: ${cap:,.2f}")
        print(f"   · Final Equity Value: ${equity_series.iloc[-1]:,.2f}")
        print(f"   · Total return: {((equity_series.iloc[-1]/cap - 1)*100):+.2f}%")
        print(f"   · Total completed trades logged: {len(trades)}")
        
        if trades:
            print("   · Sample Trade record:")
            print(f"     - Type: {trades[0]['Type']}")
            print(f"     - Entry Date: {trades[0]['Entry Date']} | Price: ${trades[0]['Entry Price']:.2f}")
            print(f"     - Exit Date: {trades[0]['Exit Date']} | Price: ${trades[0]['Exit Price']:.2f}")
            print(f"     - PnL: {trades[0]['Profit (%)']:+.2f}% (${trades[0]['Profit ($)']:+.2f})")
    except Exception as e:
        print(f"[FAIL] Backtester transaction execution failed: {e}")
        return False

    print("\n====================================================")
    print("SUCCESS: ALL PROGRAMMATIC UTBOT VALIDATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = test_utbot_calculations()
    sys.exit(0 if success else 1)
