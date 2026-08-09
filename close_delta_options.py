import ccxt
import json

api_key = 'KoDWNWYEBc392P2tYKZzcS43kyRShL'
secret = 'XuHNnS3eTI4J7kIIrLjMol7kIskaHQTKkYgHg3ZBJBXuKt3u9Y5h3I7yelEa'

import sys
sys.stdout.reconfigure(encoding='utf-8')

exchange_india = ccxt.delta({
    'apiKey': api_key,
    'secret': secret,
})
# Overwrite urls for India testnet
exchange_india.urls['api']['public'] = 'https://cdn-ind.testnet.deltaex.org'
exchange_india.urls['api']['private'] = 'https://cdn-ind.testnet.deltaex.org'

try:
    print("Fetching active positions on Delta India Testnet...")
    positions = exchange_india.fetch_positions()
    
    closed_any = False
    for pos in positions:
        info = pos['info']
        size = float(info.get('size', 0))
        if size == 0:
            continue
            
        symbol = pos.get('symbol')
        if not symbol:
            symbol = info.get('product_symbol') # Fallback to local symbol
            
        side = pos.get('side', '') # 'buy' or 'sell'
        contracts = abs(size)
        
        closing_side = 'sell' if side == 'buy' else 'buy'
        
        print(f"Closing position: {symbol} | Size: {size} | Side: {side} -> Placing {closing_side.upper()} order for {contracts} contracts...")
        
        try:
            order = exchange_india.create_order(symbol, 'market', closing_side, contracts)
            print(f"  [SUCCESS] Order ID: {order.get('id')}")
            closed_any = True
        except Exception as order_err:
            print(f"  [FAILED] to close {symbol}: {order_err}")
            
    if not closed_any:
        print("No open positions found to close.")
except Exception as e:
    print(f"Error fetching positions: {e}")
