import ccxt
import sys
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
    bal = exchange.fetch_balance()
    print("Balance info:")
    usd_info = bal.get('USD', {})
    print(f"Total: {usd_info.get('total')}")
    print(f"Free: {usd_info.get('free')}")
    print(f"Used (Margin Locked): {usd_info.get('used')}")
except Exception as e:
    print(e)
