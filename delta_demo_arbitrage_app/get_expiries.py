import ccxt
from datetime import datetime

try:
    from delta_demo_geometry_bot import DEMO_API, DEMO_SECRET
except ImportError:
    import sys
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

markets = exchange.load_markets()
tickers = exchange.fetch_tickers()
btc_price = tickers.get('BTC/USD:USD', {}).get('last', 60000)
print(f"BTC Price: {btc_price}")

expiries = set()
for symbol, m in markets.items():
    if m.get('option') and m.get('base') == 'BTC':
        expiry = m.get('expiryDatetime')
        if expiry:
            exp_dt = datetime.strptime(expiry.split('T')[0], "%Y-%m-%d")
            days = (exp_dt - datetime.today()).days
            expiries.add((expiry.split('T')[0], days))

print("Available Expiries (Date, Days to Expiry):")
for e in sorted(expiries, key=lambda x: x[1]):
    print(f"  {e[0]} ({e[1]} days)")
