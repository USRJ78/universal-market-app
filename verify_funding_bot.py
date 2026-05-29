# verify_funding_bot.py
import sys
import os
import json
import time

def test_funding_system():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: FUNDING ARBITRAGE BOT")
    print("====================================================")
    
    from funding_arb_bot import FundingArbBot, run_funding_bot, STATE_FILE, LOG_FILE
    
    # Clean up state file before starting to ensure a pristine test environment
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[INFO] Pre-existing state file cleared for testing.")
        except Exception as e:
            print(f"[WARNING] Could not clear state file: {e}")

    # 1. Test Imports and Modules
    print("\n[Step 1] Checking imports and requirements...")
    try:
        import ccxt
        print("[SUCCESS] ccxt package imported successfully.")
    except ImportError:
        print("[WARNING] ccxt package missing. Bot will use high-fidelity simulation fallback.")
        
    try:
        print("[SUCCESS] funding_arb_bot modules imported successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to import funding_arb_bot components: {e}")
        return False
        
    # 2. Instantiate Bot and Test Core Configurations
    print("\n[Step 2] Testing bot initialization and configuration state...")
    try:
        bot = FundingArbBot(start_capital=1000.0, min_apr_trigger=8.0, stop_apr_trigger=2.0)
        # Force clean reset of state in memory in case anything was loaded
        bot.positions = []
        bot.balance_usdt = 1000.0
        bot.capital = 1000.0
        
        print(f"[SUCCESS] Bot successfully initialized.")
        print(f"   · Mock Capital: ${bot.capital:.2f}")
        print(f"   · Min APR Entry Trigger: {bot.min_apr_trigger}%")
        print(f"   · Stop APR Exit Trigger: {bot.stop_apr_trigger}%")
        print(f"   · Allocation size: ${bot.position_allocation:.2f}")
        print(f"   · Default Leverage: {bot.futures_leverage}x")
    except Exception as e:
        print(f"[FAIL] Bot initialization failed: {e}")
        return False

    # 3. Test State Serialization & JSON Caching with Leverage
    print("\n[Step 3] Testing JSON State Serialization with Leverage...")
    try:
        bot.futures_leverage = 5.0
        bot.save_state()
        if os.path.exists(STATE_FILE):
            print(f"[SUCCESS] State file '{STATE_FILE}' created successfully.")
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            print(f"   · Verified Status field in JSON: {saved_data.get('status')}")
            print(f"   · Verified Balance in JSON: ${saved_data.get('balance_usdt'):.2f}")
            print(f"   · Verified Futures Leverage in JSON: {saved_data.get('futures_leverage')}x")
            assert saved_data.get("futures_leverage") == 5.0, "Saved leverage should match what was set"
            
            # Reload state
            new_bot = FundingArbBot(start_capital=1000.0)
            print(f"   · Verified Loaded Futures Leverage: {new_bot.futures_leverage}x")
            assert new_bot.futures_leverage == 5.0, "Loaded leverage should be 5x"
        else:
            print("[FAIL] State file was not created by save_state()")
            return False
    except Exception as e:
        print(f"[FAIL] Serialization check failed: {e}")
        return False

    # 4. Test 1x Leverage Cash-and-Carry Position Math
    print("\n[Step 4] Testing 1x Leverage Position Math...")
    try:
        # Clear state file so reload starts from clean parameters
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            
        bot = FundingArbBot(start_capital=1000.0)
        bot.positions = []
        bot.balance_usdt = 1000.0
        bot.capital = 1000.0
        bot.futures_leverage = 1.0
        bot.position_allocation = 250.0
        
        # Open manual position
        bot.open_position(asset="SOL", spot_price=165.0, perp_price=166.0, apr=15.0)
        
        assert len(bot.positions) == 1, f"Position should be opened, got {len(bot.positions)}"
        pos = bot.positions[0]
        
        # Math checks
        # S = 250 / (1 + 1/1) = 125
        assert abs(pos["spot_size"] - 125.0) < 1e-4, "Spot size should be 125.0 at 1x leverage"
        assert abs(pos["perp_size"] - 125.0) < 1e-4, "Perp size should be 125.0 at 1x leverage"
        assert abs(pos["perp_margin"] - 125.0) < 1e-4, "Perp margin should be 125.0 at 1x leverage"
        assert abs(pos["liq_price"] - 332.0) < 1e-4, "Liq price should be entry_perp * 2 at 1x leverage"
        
        open_fee = 125.0 * 0.0015 # 0.1875
        expected_balance = 1000.0 - 250.0 - open_fee # 749.8125
        assert abs(bot.balance_usdt - expected_balance) < 1e-4, f"Balance should be {expected_balance}, got {bot.balance_usdt}"
        
        print("[SUCCESS] 1x leverage position opened with correct sizes and balance updates.")
        print(f"   · Spot size: ${pos['spot_size']:.2f}")
        print(f"   · Futures Margin: ${pos['perp_margin']:.2f}")
        print(f"   · Liquidation Price: ${pos['liq_price']:.2f}")
        print(f"   · Remaining Balance: ${bot.balance_usdt:.4f}")
        
        # Close position
        # Entry spot=165.0, Entry perp=166.0, Exit spot=165.2, Exit perp=165.5
        # Entry spread = (166 - 165)/165 = 1/165
        # Exit spread = (165.5 - 165.2)/165.2 = 0.3/165.2
        # basis_profit = S * (1/165 - 0.3/165.2) = 125 * (0.0060606 - 0.00181598) = 125 * 0.004244625 = 0.53058
        # close_fee = S * 0.0015 = 0.1875
        # cash returned = M + basis_profit - close_fee = 250 + 0.53058 - 0.1875 = 250.34308
        # expected end balance = 749.8125 + 250.34308 = 1000.15558
        bot.close_position(idx=0, current_spot=165.2, current_perp=165.5)
        expected_end_balance = expected_balance + 250.0 + 0.530578 - 0.1875
        assert abs(bot.balance_usdt - expected_end_balance) < 1e-2, f"Ending balance should be {expected_end_balance}, got {bot.balance_usdt}"
        print(f"[SUCCESS] 1x leverage position closed cleanly. Ending Balance: ${bot.balance_usdt:.4f}")
    except Exception as e:
        print(f"[FAIL] 1x leverage position check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Test 10x Leverage Cash-and-Carry Position Math
    print("\n[Step 5] Testing 10x Leverage Position Math...")
    try:
        # Clear state file so reload starts from clean parameters
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            
        bot = FundingArbBot(start_capital=1000.0)
        bot.positions = []
        bot.balance_usdt = 1000.0
        bot.capital = 1000.0
        bot.futures_leverage = 10.0
        bot.position_allocation = 250.0
        
        # Configure extremely high open trigger to prevent scan cycle from auto-opening other assets
        bot.min_apr_trigger = 100.0
        
        # Open manual position
        bot.open_position(asset="SOL", spot_price=165.0, perp_price=166.0, apr=15.0)
        
        assert len(bot.positions) == 1, f"Position should be opened, got {len(bot.positions)}"
        pos = bot.positions[0]
        
        # Math checks
        # S = 250 / (1 + 1/10) = 250 / 1.1 = 227.272727
        expected_spot_size = 250.0 / 1.1
        expected_perp_margin = expected_spot_size / 10.0
        expected_liq_price = 166.0 * 1.1 # 182.6
        
        assert abs(pos["spot_size"] - expected_spot_size) < 1e-4, f"Spot size should be {expected_spot_size}, got {pos['spot_size']}"
        assert abs(pos["perp_size"] - expected_spot_size) < 1e-4, f"Perp size should be {expected_spot_size}, got {pos['perp_size']}"
        assert abs(pos["perp_margin"] - expected_perp_margin) < 1e-4, f"Perp margin should be {expected_perp_margin}, got {pos['perp_margin']}"
        assert abs(pos["liq_price"] - expected_liq_price) < 1e-4, f"Liq price should be {expected_liq_price}, got {pos['liq_price']}"
        
        open_fee = expected_spot_size * 0.0015
        expected_balance = 1000.0 - 250.0 - open_fee
        assert abs(bot.balance_usdt - expected_balance) < 1e-4, f"Balance should be {expected_balance}, got {bot.balance_usdt}"
        
        print("[SUCCESS] 10x leverage position opened with correct sizes and balance updates.")
        print(f"   · Spot size: ${pos['spot_size']:.2f}")
        print(f"   · Futures Margin: ${pos['perp_margin']:.2f}")
        print(f"   · Liquidation Price: ${pos['liq_price']:.2f}")
        print(f"   · Remaining Balance: ${bot.balance_usdt:.4f}")
        
        # Let's run a second cycle to simulate yield accrual (pro-rata pro-rated over 2s interval)
        bot.run_one_cycle(exchange=None)
        print(f"[SUCCESS] Cycle completed. Captured Yield: ${bot.total_yield:.8f}")
        
        # Verify that total_yield accrued based on the larger leveraged spot size (expected_spot_size)
        expected_yield = expected_spot_size * (15.0 / 100.0) * (2.0 / (365 * 24 * 3600))
        assert abs(bot.total_yield - expected_yield) < 1e-8, f"Yield should be {expected_yield}, got {bot.total_yield}"
        print(f"[SUCCESS] Yield verified based on leveraged spot size: ${bot.total_yield:.8f}")
        
        # Close position
        # S = 227.272727
        # Entry spot=165.0, Entry perp=166.0, Exit spot=165.2, Exit perp=165.5
        # Entry spread = (166 - 165)/165 = 1/165
        # Exit spread = (165.5 - 165.2)/165.2 = 0.3/165.2
        # basis_profit = S * (1/165 - 0.3/165.2) = 227.272727 * 0.004244625 = 0.964687
        # close_fee = S * 0.0015 = 0.340909
        # expected end balance = balance_before_close + M + yield + basis_profit - close_fee
        bot.close_position(idx=0, current_spot=165.2, current_perp=165.5)
        
        expected_basis = expected_spot_size * ((166.0 - 165.0)/165.0 - (165.5 - 165.2)/165.2)
        close_fee = expected_spot_size * 0.0015
        expected_end_balance = expected_balance + 250.0 + expected_yield + expected_basis - close_fee
        
        assert abs(bot.balance_usdt - expected_end_balance) < 1e-2, f"Ending balance should be {expected_end_balance}, got {bot.balance_usdt}"
        print(f"[SUCCESS] 10x leverage position closed cleanly. Ending Balance: ${bot.balance_usdt:.4f}")
    except Exception as e:
        print(f"[FAIL] 10x leverage position check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Cleanup temp state files
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
        
    print("\n====================================================")
    print("SUCCESS: ALL LEVERAGED QUANTITATIVE BOT VALIDATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = test_funding_system()
    sys.exit(0 if success else 1)
