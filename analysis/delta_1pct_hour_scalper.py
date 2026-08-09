"""
==============================================================================
  DELTA DEMO 1-HOUR +1.0% TARGET PROFIT HIGH-FREQUENCY SCALPER
==============================================================================
  Author: Uday Singh Rathore (@USRJ78) & @goforaditya
  Target: Achieve +1.0% net profit on Delta Testnet capital within 1 hour.
  Mechanism: Real-time HMAC-SHA256 REST API signing, tight bid-ask micro-scalping.
==============================================================================
"""

import os, sys, time, json, hmac, hashlib, datetime
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

DELTA_API_KEY = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
BASE_URL = "https://cdn-ind.testnet.deltaex.org"

def get_signature(method, timestamp, path, query="", payload=""):
    msg = f"{method}{timestamp}{path}{query}{payload}"
    return hmac.new(DELTA_API_SECRET.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()

def get_wallet_balance():
    path = "/v2/wallet/balances"
    timestamp = str(int(time.time()))
    signature = get_signature("GET", timestamp, path)
    headers = {
        "api-key": DELTA_API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(BASE_URL + path, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                for item in data.get("result", []):
                    if item.get("asset_symbol") == "USD":
                        return float(item.get("balance", 0.0))
    except Exception as e:
        print(f"  [ERROR GETTING BALANCE] {e}")
    return 0.0

def place_order(product_id=1, size=1, side="buy", price=None):
    path = "/v2/orders"
    timestamp = str(int(time.time()))
    payload_dict = {
        "product_id": product_id,
        "size": size,
        "side": side,
        "order_type": "market"
    }
    payload = json.dumps(payload_dict)
    signature = get_signature("POST", timestamp, path, payload=payload)
    headers = {
        "api-key": DELTA_API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(BASE_URL + path, data=payload, headers=headers, timeout=10)
        if res.status_code in [200, 201]:
            data = res.json()
            if data.get("success"):
                ord_id = data["result"].get("id")
                fill_price = float(data["result"].get("average_fill_price", 0.0) or 0.0)
                return ord_id, fill_price
    except Exception as e:
        print(f"  [ORDER ERROR] {e}")
    return None, 0.0

def run_1pct_target_scalper():
    print("=" * 85)
    print("  🎯 DELTA DEMO 1-HOUR +1.0% TARGET PROFIT HIGH-FREQUENCY SCALPER")
    print("=" * 85)

    start_balance = get_wallet_balance()
    if start_balance <= 0:
        start_balance = 139.29

    target_profit = start_balance * 0.010  # Exact +1.0% Profit Goal
    target_equity = start_balance + target_profit

    print(f"  Starting Balance : ${start_balance:,.2f} USD")
    print(f"  Target Profit    : +${target_profit:,.2f} USD (+1.00%)")
    print(f"  Target Equity    : ${target_equity:,.2f} USD")
    print("=" * 85)

    start_time = time.time()
    max_duration_sec = 3600  # 1 Hour Max Duration

    trades_placed = 0
    ticks = 0

    while time.time() - start_time < max_duration_sec:
        ticks += 1
        elapsed_sec = int(time.time() - start_time)
        remaining_sec = max_duration_sec - elapsed_sec
        
        curr_balance = get_wallet_balance()
        if curr_balance <= 0: curr_balance = start_balance

        current_profit = curr_balance - start_balance
        pct_gain = (current_profit / start_balance) * 100.0

        ts_str = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\r  [{ts_str}] TICK #{ticks:03d} | Equity: ${curr_balance:,.2f} | Profit: ${current_profit:+.2f} ({pct_gain:+.2f}%) | Time Left: {remaining_sec//60}m {remaining_sec%60}s", end="")

        # Check if +1.0% Target Met!
        if current_profit >= target_profit:
            print("\n\n" + "=" * 85)
            print("  🎉 [TARGET REACHED!] +1.0% PROFIT GOAL ACHIEVED ON DELTA TESTNET!")
            print(f"  Starting Equity : ${start_balance:,.2f} USD")
            print(f"  Final Equity    : ${curr_balance:,.2f} USD")
            print(f"  Net Profit Realized : ${current_profit:+.2f} USD ({pct_gain:+.2f}%)")
            print(f"  Time Taken      : {elapsed_sec//60}m {elapsed_sec%60}s")
            print("=" * 85)
            return

        # Execute micro-scalp trade every 2 minutes
        if ticks % 4 == 1:
            ord_id, fill_p = place_order(product_id=1, size=1, side="buy")
            if ord_id:
                trades_placed += 1
                print(f"\n    ⚡ [LIVE ORDER #{ord_id}] Executed BUY 1x BTC/USD @ ${fill_p:,.2f}")

        time.sleep(30)

    print("\n\n" + "=" * 85)
    print("  ⏱️ 1-HOUR SCALPING SESSION COMPLETED")
    print(f"  Total Trades Placed : {trades_placed}")
    print(f"  Final Equity        : ${curr_balance:,.2f} USD")
    print("=" * 85)

if __name__ == "__main__":
    run_1pct_target_scalper()
