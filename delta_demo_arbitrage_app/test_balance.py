import ccxt
import sys

try:
    from delta_demo_geometry_bot import DEMO_API, DEMO_SECRET
except ImportError:
    print("Failed to import API keys.")
    sys.exit(1)

exchange = ccxt.delta({
    'apiKey': DEMO_API,
    'secret': DEMO_SECRET,
    'enableRateLimit': True
})
# Use testnet URLs
exchange.urls['api'] = {
    'public': 'https://cdn-ind.testnet.deltaex.org',
    'private': 'https://api-ind.testnet.deltaex.org',
}

try:
    balance = exchange.fetch_balance()
    usd = balance.get('USD', {})
    print(f"FETCH_SUCCESS|Total: {usd.get('total', 0.0)}|Free: {usd.get('free', 0.0)}")
except Exception as e:
    print(f"FETCH_ERROR|{str(e)}")
