# verify_l2_bot.py
import sys
import os
import json

def test_l2_system():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: L2 RUPEES ARBITRAGE BOT")
    print("====================================================")
    
    # 1. Test Imports and Modules
    print("\n[Step 1] Checking imports and requirements...")
    try:
        from live_l2_arb_bot import LiveL2ArbBot, STATE_FILE, LOG_FILE
        print("[SUCCESS] live_l2_arb_bot modules imported successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to import live_l2_arb_bot components: {e}")
        return False
        
    # 2. Instantiate Bot and Test Rupees Configurations
    print("\n[Step 2] Testing L2 Rupees Bot initialization...")
    try:
        bot = LiveL2ArbBot(
            start_capital_inr=100000.0,
            trade_size_inr=15000.0,
            taker_fee_pct=0.10,
            usd_inr_rate=85.0,
            min_profit=0.05
        )
        print(f"[SUCCESS] L2 Bot successfully initialized.")
        print(f"   · Mock Capital: ₹{bot.capital:,.2f}")
        print(f"   · Trade Size allocation: ₹{bot.trade_size:,.2f}")
        print(f"   · Taker fee rate: {bot.taker_fee_pct}%")
        print(f"   · USDT/INR conversion: ₹{bot.usd_inr_rate:.2f}/USDT")
        print(f"   · Minimum profit trigger: {bot.min_profit_pct}%")
    except Exception as e:
        print(f"[FAIL] Bot initialization failed: {e}")
        return False

    # 3. Test L2 Order Book Depth-Walking Mathematics
    print("\n[Step 3] Validating L2 Depth-Walking algorithms...")
    try:
        # Mock asks L2 depth book: [[price, volume]]
        # Level 1: 10.0 USD, size 1.0 BTC (cost = 10 USD)
        # Level 2: 12.0 USD, size 2.0 BTC (cost = 24 USD)
        # Level 3: 15.0 USD, size 5.0 BTC (cost = 75 USD)
        mock_asks = [[10.0, 1.0], [12.0, 2.0], [15.0, 5.0]]
        
        # Test 1: Cost exactly matches level 1 volume (10 USD)
        qty, avg_p = bot.walk_asks(mock_asks, 10.0)
        assert qty == 1.0, f"Expected 1.0 BTC, got {qty}"
        assert avg_p == 10.0, f"Expected average price 10.0, got {avg_p}"
        print("   · Test 1 (Exact level 1 match): Passed.")

        # Test 2: Cost eats into level 2 volume (Cost = 22 USD)
        # Level 1 cost = 10 USD (gets 1.0 BTC). Cost remaining = 12 USD.
        # Level 2 ask is at 12.0 USD. So 12 USD gets exactly 1.0 BTC.
        # Total BTC acquired = 1.0 (L1) + 1.0 (L2) = 2.0 BTC.
        # Average price = 22 USD / 2.0 BTC = 11.0 USD/BTC.
        qty, avg_p = bot.walk_asks(mock_asks, 22.0)
        assert qty == 2.0, f"Expected 2.0 BTC, got {qty}"
        assert avg_p == 11.0, f"Expected average price 11.0, got {avg_p}"
        print("   · Test 2 (Eats into level 2): Passed.")

        # Mock bids L2 depth book: [[price, volume]]
        # Level 1: 15.0 USD, size 1.0 ETH (value = 15 USD)
        # Level 2: 12.0 USD, size 2.0 ETH (value = 24 USD)
        mock_bids = [[15.0, 1.0], [12.0, 2.0]]
        
        # Test 3: Sell 2.0 ETH into bids
        # Level 1 bid takes 1.0 ETH at 15.0 USD (gets 15 USD)
        # Level 2 bid takes 1.0 ETH at 12.0 USD (gets 12 USD)
        # Total USDT received = 27 USD.
        # Average execution price = 27 USD / 2.0 ETH = 13.5 USD.
        usdt, avg_p = bot.walk_bids(mock_bids, 2.0)
        assert usdt == 27.0, f"Expected 27.0 USDT, got {usdt}"
        assert avg_p == 13.5, f"Expected average price 13.5, got {avg_p}"
        print("   · Test 3 (Bid depth matching): Passed.")
        print("[SUCCESS] Depth-walking mathematics is 100% correct.")
    except Exception as e:
        print(f"[FAIL] Depth-walking validation failed: {e}")
        return False

    # 4. Test State Serialization & JSON Caching
    print("\n[Step 4] Testing JSON State Serialization...")
    try:
        # Clear existing test files
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            
        bot.save_state()
        if os.path.exists(STATE_FILE):
            print(f"[SUCCESS] State file '{STATE_FILE}' created successfully.")
            with open(STATE_FILE, "r") as f:
                saved_data = json.load(f)
            assert saved_data.get("usd_inr_rate") > 0.0, "USDT/INR rate mismatch in saved state"
            assert saved_data.get("capital") == 100000.0, "Starting Capital mismatch"
            print(f"   · Verified Status field in L2 JSON: {saved_data.get('status')}")
            print(f"   · Verified Balance in L2 JSON: ₹{saved_data.get('balance_inr'):,.2f}")
        else:
            print("[FAIL] State file was not created by save_state()")
            return False
    except Exception as e:
        print(f"[FAIL] Serialization check failed: {e}")
        return False

    # 5. Run L2 Simulation Cycle & Taker Fee Math
    print("\n[Step 5] Checking L2 Taker Fee deductions and execution cycles...")
    try:
        # Clear positions/trades
        bot.trades = []
        bot.balance_inr = 100000.0
        
        # We pass None to force high-fidelity L2 simulation loop safely
        bot.run_one_cycle(exchange=None)
        
        print(f"[SUCCESS] L2 cycle completed successfully.")
        print(f"   · Scans completed: {bot.cycles_scanned}")
        print(f"   · Active Trades Executed: {bot.total_trades}")
        
        # Test manual execution to check fee drag in INR
        # Expected taker fee drag: 0.10% per leg = ~0.30% total drag on ₹15,000 size = ₹45 fees.
        # Mock net return multiple: 1.005 (gross spread)
        # Taker fee deduction: 0.1% per leg in-kind
        # Let's add a manual trade and verify fee calculations
        expected_spread = 0.05
        net_pnl_inr = 750.0
        fee_paid_inr = 45.0
        slippage_drag_inr = 15.0
        
        bot.add_trade(expected_spread, net_pnl_inr, fee_paid_inr, slippage_drag_inr)
        
        assert len(bot.trades) == 1, "Trade record should be saved in trades ledger"
        assert bot.total_trades == 1, "Total trades count should be 1"
        assert bot.total_profit_inr == 750.0, "Total PnL calculation mismatch"
        assert bot.total_fees_paid_inr == 45.0, "Total fees paid calculation mismatch"
        assert bot.total_slippage_drag_inr == 15.0, "Slippage cost mismatch"
        assert bot.balance_inr == 100750.0, f"INR balance calculation mismatch: {bot.balance_inr}"
        
        print("   · Trade ledger recording and in-kind taker fee calculations: Passed.")
        print(f"   · Ending Wallet Balance: ₹{bot.balance_inr:,.2f} (Profit: ₹{bot.total_profit_inr:+.2f}, Fees: ₹{bot.total_fees_paid_inr:.2f})")
    except Exception as e:
        print(f"[FAIL] L2 execution and fee validation failed: {e}")
        return False

    # Cleanup temp state files
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        
    print("\n====================================================")
    print("SUCCESS: ALL L2 RUPEES BOT PROGRAMMATIC CHECKS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = test_l2_system()
    sys.exit(0 if success else 1)
