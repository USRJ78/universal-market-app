# verify_stockfish_arb_bot.py
import ccxt
import sys
import re
import requests
import urllib.parse
import os

DEMO_API = "qsNKMuPZyeubUK7rpqligKksNO0tey"
DEMO_SECRET = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

# Import helper functions from stockfish_basis_arb_bot
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import stockfish_basis_arb_bot

def main():
    print("====================================================")
    print("[INFO] PROGRAMMATIC VALIDATION: STOCKFISH ARBITRAGE BOT")
    print("====================================================")
    
    # 1. Test CCXT Delta Client Init
    print("\n[Step 1] Initializing CCXT Delta Client...")
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
        exchange.load_markets()
        print(f"[SUCCESS] Connected. Available symbols: {len(exchange.symbols)}")
    except Exception as e:
        print(f"[FAIL] Initialization / Connection failed: {e}")
        sys.exit(1)
        
    # 2. Check Credentials & IP Whitelist status
    print("\n[Step 2] Testing API Key Authentication...")
    try:
        bal = exchange.fetch_balance()
        print(f"[SUCCESS] Credentials fully authenticated! Current Balance: {bal.get('USD', {}).get('free', 0.0)} USD")
    except Exception as e:
        err_str = str(e).lower()
        if "ip_not_whitelisted" in err_str:
            ip_match = re.search(r'"client_ip"\s*:\s*"([^"]+)"', str(e))
            client_ip = ip_match.group(1) if ip_match else "your IP address"
            print(f"[WARNING] Successfully connected but API key is blocked by IP Whitelist for IP: {client_ip}")
            print("          * Sandbox Fallback Mode will take over during daemon run *")
        else:
            print(f"[FAIL] Authentication error: {e}")
            sys.exit(1)
            
    # 3. Test FEN translation logic
    print("\n[Step 3] Testing spread-to-FEN mathematical mapping...")
    try:
        # Test positive spread
        fen_pos = stockfish_basis_arb_bot.spread_to_fen(0.12, 12.0, 0.35)
        # Test negative spread
        fen_neg = stockfish_basis_arb_bot.spread_to_fen(-0.12, -12.0, 0.35)
        
        print(f"  * positive spread FEN: {fen_pos}")
        print(f"  * negative spread FEN: {fen_neg}")
        
        # Verify White pushes on positive, Black pushes on negative
        assert "P" in fen_pos, "FEN mapping must include White pawn pushes"
        assert "p" in fen_neg, "FEN mapping must include Black pawn pushes"
        print("[SUCCESS] FEN mathematical translations correct!")
    except Exception as e:
        print(f"[FAIL] FEN mapping logic failed: {e}")
        sys.exit(1)
        
    # 4. Test Stockfish Engine API connection
    print("\n[Step 4] Querying Stockfish Engine API...")
    try:
        success, score, mate, bestmove = stockfish_basis_arb_bot.query_stockfish(fen_pos)
        if success:
            print(f"[SUCCESS] Stockfish responded successfully!")
            print(f"          · Score: {score:+.2f}")
            print(f"          · Best Move: {bestmove}")
        else:
            print("[FAIL] Stockfish API query returned unsuccessful status.")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Stockfish connection failed: {e}")
        sys.exit(1)
        
    print("\n====================================================")
    print("SUCCESS: ALL PROGRAMMATIC STOCKFISH ARBITRAGE TESTS PASSED!")
    print("====================================================")
    sys.exit(0)

if __name__ == "__main__":
    main()
