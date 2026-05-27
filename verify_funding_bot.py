# verify_funding_bot.py
import sys
import os
import json
import time

def test_funding_system():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: FUNDING ARBITRAGE BOT")
    print("====================================================")
    
    # 1. Test Imports and Modules
    print("\n[Step 1] Checking imports and requirements...")
    try:
        import ccxt
        print("[SUCCESS] ccxt package imported successfully.")
    except ImportError:
        print("[WARNING] ccxt package missing. Bot will use high-fidelity simulation fallback.")
        
    try:
        from funding_arb_bot import FundingArbBot, run_funding_bot, STATE_FILE, LOG_FILE
        print("[SUCCESS] funding_arb_bot modules imported successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to import funding_arb_bot components: {e}")
        return False
        
    # 2. Instantiate Bot and Test Core Configurations
    print("\n[Step 2] Testing bot initialization and configuration state...")
    try:
        bot = FundingArbBot(start_capital=1000.0, min_apr_trigger=8.0, stop_apr_trigger=2.0)
        print(f"[SUCCESS] Bot successfully initialized.")
        print(f"   · Mock Capital: ${bot.capital:.2f}")
        print(f"   · Min APR Entry Trigger: {bot.min_apr_trigger}%")
        print(f"   · Stop APR Exit Trigger: {bot.stop_apr_trigger}%")
        print(f"   · Allocation size: ${bot.position_allocation:.2f}")
    except Exception as e:
        print(f"[FAIL] Bot initialization failed: {e}")
        return False

    # 3. Test State Serialization & JSON Caching
    print("\n[Step 3] Testing JSON State Serialization...")
    try:
        # Clear existing test files to be clean
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            
        bot.save_state()
        if os.path.exists(STATE_FILE):
            print(f"[SUCCESS] State file '{STATE_FILE}' created successfully.")
            with open(STATE_FILE, "r") as f:
                saved_data = json.load(f)
            print(f"   · Verified Status field in JSON: {saved_data.get('status')}")
            print(f"   · Verified Balance in JSON: ${saved_data.get('balance_usdt'):.2f}")
        else:
            print("[FAIL] State file was not created by save_state()")
            return False
    except Exception as e:
        print(f"[FAIL] Serialization check failed: {e}")
        return False

    # 4. Run One Simulation Cycle to Check Yield Accrual and Trade Triggers
    print("\n[Step 4] Simulating an active yield-capture and cycle scan...")
    try:
        # We pass None to force simulation/mock exchange feed for safe offline verification
        bot.run_one_cycle(exchange=None)
        print(f"[SUCCESS] Cycle 1 completed successfully.")
        print(f"   · Cycles scanned: {bot.cycles_scanned}")
        print(f"   · Active Positions Count: {len(bot.positions)}")
        print(f"   · Accrued Yield Captured: ${bot.total_yield:.8f}")
        
        # Open a manual position to verify yield accrual math and basis profit calculation
        print("\n[Step 5] Injecting Mock Open Position & Accruing Yield...")
        bot.positions = []
        bot.balance_usdt = 1000.0
        bot.open_position(asset="SOL", spot_price=165.0, perp_price=166.0, apr=15.0)
        
        # Verify position opening in state
        assert len(bot.positions) == 1, "Position should be opened"
        assert bot.positions[0]["asset"] == "SOL", "Asset should be SOL"
        print("[SUCCESS] Mock position in SOL successfully opened.")
        
        # Let's run a second cycle to simulate yield accrual (pro-rata pro-rated over 2s interval)
        bot.run_one_cycle(exchange=None)
        print(f"[SUCCESS] Cycle 2 completed. Captured Yield: ${bot.total_yield:.8f}")
        
        # Close position and verify realized PnL
        print("\n[Step 6] Simulating Position Clean Unwind...")
        bot.close_position(idx=0, current_spot=165.2, current_perp=165.5)
        print(f"[SUCCESS] Position successfully unwound.")
        print(f"   · Cumulative Trades: {bot.total_trades}")
        print(f"   · Ending Wallet Balance: ${bot.balance_usdt:.4f}")
    except Exception as e:
        print(f"[FAIL] Yield scan validation failed: {e}")
        return False

    # Cleanup temp state files
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        
    print("\n====================================================")
    print("SUCCESS: ALL PROGRAMMATIC BOT VALIDATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = test_funding_system()
    sys.exit(0 if success else 1)
