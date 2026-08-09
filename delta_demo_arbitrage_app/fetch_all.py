import ccxt
import sys
import json
try:
    from delta_demo_geometry_bot import DEMO_API, DEMO_SECRET
except ImportError:
    sys.exit(1)

exchange = ccxt.delta({
    'apiKey': DEMO_API,
    'secret': DEMO_SECRET,
    'enableRateLimit': True
})
exchange.urls['api'] = {
    'public': 'https://cdn-ind.testnet.deltaex.org',
    'private': 'https://api-ind.testnet.deltaex.org',
}

try:
    # Try alternate endpoints
    response = exchange.privateGetPositions()
    
    active = [p for p in response if p.get('size', 0) != 0]
    print(f"FOUND {len(active)} ACTIVE POSITIONS VIA CCXT ENDPOINT")
    for pos in active:
        print(f"Symbol: {pos.get('symbol', pos.get('product_symbol'))}, Size: {pos.get('size')}")
except Exception as e:
    print(f"Error: {e}")
