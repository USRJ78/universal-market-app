"""
==============================================================================
  DELTA DEMO TESTNET PERPETUAL FUTURES & OPTIONS EXPLORER
==============================================================================
"""

import ccxt
import pandas as pd

API_KEY = "KoDWNWYEBc392P2tYKZzcS43kyRShL"
SECRET  = "XuHNnS3eTI4J7kIIrLjMol7kIskaHQTKkYgHg3ZBJBXuKt3u9Y5h3I7yelEa"

exchange = ccxt.delta({
    'apiKey': API_KEY,
    'secret': SECRET,
})
exchange.urls['api']['public']  = 'https://cdn-ind.testnet.deltaex.org'
exchange.urls['api']['private'] = 'https://cdn-ind.testnet.deltaex.org'

markets = exchange.load_markets()

perps = [symbol for symbol, m in markets.items() if m.get('swap', False) or m.get('future', False)]
options = [symbol for symbol, m in markets.items() if m.get('option', False)]

print(f"Total Markets : {len(markets)}")
print(f"Perpetual/Futures Markets ({len(perps)}):")
for p in perps[:15]:
    print(f"  - {p}")

print(f"\nOptions Markets ({len(options)}):")
for o in options[:15]:
    print(f"  - {o}")
