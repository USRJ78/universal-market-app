import ccxt
import sys

demo_api = "qsNKMuPZyeubUK7rpqligKksNO0tey"
demo_secret = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"

endpoints = [
    {"name": "CCXT Testnet URL", "url": "https://testnet-api.delta.exchange"},
    {"name": "Delta India Testnet Org URL", "url": "https://cdn-ind.testnet.deltaex.org"},
    {"name": "Delta India Testnet URL", "url": "https://testnet-api.india.delta.exchange"},
    {"name": "Delta Demo API URL", "url": "https://demo-api.delta.exchange"},
    {"name": "Delta India Demo API URL", "url": "https://demo-api.india.delta.exchange"}
]

print("=== Delta Exchange Demo API Test ===")
for ep in endpoints:
    print(f"\nTrying endpoint: {ep['name']} ({ep['url']})...")
    try:
        exchange = ccxt.delta({
            'apiKey': demo_api,
            'secret': demo_secret,
            'enableRateLimit': True
        })
        exchange.urls['api'] = {
            'public': ep["url"],
            'private': ep["url"]
        }
        exchange.load_markets()
        print("[SUCCESS] Markets loaded.")
        balance = exchange.fetch_balance()
        print(f"[SUCCESS] Balance fetched: {list(balance.keys())[:5]}")
        print("Demo API successfully authenticated on this endpoint!")
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Error: {e}")

print("\nAll default test endpoints failed to authenticate. Let's try standard set_sandbox_mode(True)")
try:
    exchange = ccxt.delta({
        'apiKey': demo_api,
        'secret': demo_secret,
        'enableRateLimit': True
    })
    exchange.set_sandbox_mode(True)
    exchange.load_markets()
    print("[SUCCESS] Markets loaded via set_sandbox_mode(True)")
    balance = exchange.fetch_balance()
    print(f"[SUCCESS] Balance fetched via set_sandbox_mode(True): {list(balance.keys())[:5]}")
    sys.exit(0)
except Exception as e:
    print(f"[FAIL] set_sandbox_mode(True) failed: {e}")
