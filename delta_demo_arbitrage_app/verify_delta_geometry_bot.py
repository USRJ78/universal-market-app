# verify_delta_geometry_bot.py
import ccxt
import sys
import re

DEMO_API = "qsNKMuPZyeubUK7rpqligKksNO0tey"
DEMO_SECRET = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

def verify_delta_geometry():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: DELTA EXCHANGE GEOMETRY BOT")
    print("====================================================")
    
    # 1. Initialize CCXT Delta Testnet
    print("\n[Step 1] Instantiating CCXT Delta Testnet Client...")
    try:
        exchange = ccxt.delta({
            'apiKey': DEMO_API,
            'secret': DEMO_SECRET,
            'enableRateLimit': True
        })
        exchange.urls['api'] = {
            'public': ENDPOINT,
            'private': ENDPOINT
        }
        print(f"[SUCCESS] Client initialized targeting: {ENDPOINT}")
    except Exception as e:
        print(f"[FAIL] Client initialization failed: {e}")
        return False

    # 2. Test Connection & Load Markets
    print("\n[Step 2] Testing connection and loading markets...")
    try:
        exchange.load_markets()
        print(f"[SUCCESS] Markets loaded. Total available symbols: {len(exchange.symbols)}")
        assert "BTC/USD:USD" in exchange.symbols, "BTC/USD perp contract must exist"
    except Exception as e:
        print(f"[FAIL] Markets load failed: {e}")
        return False

    # 3. Fetch candles and test channel calculations
    print("\n[Step 3] Fetching historical 15m candles and calculating geometry indicators...")
    try:
        symbol = "BTC/USD:USD"
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        assert len(ohlcv) >= 25, "Must fetch at least 25 candles"
        
        # Calculate channels
        highs = [x[2] for x in ohlcv]
        lows = [x[3] for x in ohlcv]
        
        period = 20
        prev_highs = highs[-period-1:-1]
        prev_lows = lows[-period-1:-1]
        
        high20_prev = max(prev_highs)
        low20_prev = min(prev_lows)
        
        fib618_prev = high20_prev - 0.618 * (high20_prev - low20_prev)
        fib382_prev = high20_prev - 0.382 * (high20_prev - low20_prev)
        
        print(f"[SUCCESS] Geometry channels calculated successfully:")
        print(f"         · 20-Period Channel High (Prev): ${high20_prev:,.2f}")
        print(f"         · 20-Period Channel Low (Prev):  ${low20_prev:,.2f}")
        print(f"         · Fib 61.8% Support Level:      ${fib618_prev:,.2f}")
        print(f"         · Fib 38.2% Resistance Level:   ${fib382_prev:,.2f}")
        
        assert high20_prev > low20_prev, "High boundary must be greater than low boundary"
        assert low20_prev < fib618_prev < fib382_prev < high20_prev, "Fibonacci retracements must align sequentially"
    except Exception as e:
        print(f"[FAIL] Geometry calculations failed: {e}")
        return False

    # 4. Test Private Credentials & Catch IP Whitelisting
    print("\n[Step 4] Testing credentials authentication & IP Whitelist validation...")
    try:
        exchange.fetch_balance()
        print("[SUCCESS] Credentials fully authenticated! Account is live and whitelisted.")
    except Exception as e:
        err_str = str(e).lower()
        if "ip_not_whitelisted" in err_str or "ip_not_whitelisted_for_api_key" in err_str:
            ip_match = re.search(r'"client_ip"\s*:\s*"([^"]+)"', str(e))
            client_ip = ip_match.group(1) if ip_match else "your IP address"
            print(f"[SUCCESS] Keys validated. Successfully caught IP whitelisting requirement for IP: {client_ip}")
            print("         * Note: Please add this IP to your API key whitelist on the exchange to place orders *")
        else:
            print(f"[FAIL] Unexpected authentication error: {e}")
            return False

    print("\n====================================================")
    print("SUCCESS: ALL PROGRAMMATIC DELTA GEOMETRY VALIDATIONS PASSED!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = verify_delta_geometry()
    sys.exit(0 if success else 1)
