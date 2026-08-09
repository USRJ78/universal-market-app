import ccxt
import json

api_key = 'KoDWNWYEBc392P2tYKZzcS43kyRShL'
secret = 'XuHNnS3eTI4J7kIIrLjMol7kIskaHQTKkYgHg3ZBJBXuKt3u9Y5h3I7yelEa'

exchange_india = ccxt.delta({
    'apiKey': api_key,
    'secret': secret,
})
# Overwrite urls for India testnet
exchange_india.urls['api']['public'] = 'https://cdn-ind.testnet.deltaex.org'
exchange_india.urls['api']['private'] = 'https://cdn-ind.testnet.deltaex.org'

try:
    positions = exchange_india.fetch_positions()
    print("LIVE OPEN POSITIONS ON DELTA INDIA TESTNET:")
    for pos in positions:
        info = pos['info']
        size = float(info.get('size', 0))
        if size != 0:
            print(f"Symbol: {info.get('product_symbol')}")
            print(f"  Size: {size}")
            print(f"  Entry Price: {info.get('entry_price')}")
            print(f"  Mark Price: {info.get('mark_price')}")
            print(f"  Unrealized PnL: {info.get('unrealized_pnl')}")
            print(f"  Margin Mode: {info.get('margin_mode')}")
            print("-" * 30)
except Exception as e:
    print(f"Error: {e}")
