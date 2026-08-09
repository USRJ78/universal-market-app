import ccxt

DEMO_API = 'J0qo3wjxK875fZzEfl02wAzZVF3AHa'
DEMO_SECRET = 'UGtWmUs4wQITBHLsnVLffeKrnKLp8r15wcKZcH1GLwaIQsojJjvgWwK6BeR3'
ENDPOINT = 'https://cdn-ind.testnet.deltaex.org'
exchange = ccxt.delta({'apiKey': DEMO_API, 'secret': DEMO_SECRET, 'enableRateLimit': True})
exchange.urls['api'] = {'public': ENDPOINT, 'private': ENDPOINT}

print("=== OPEN POSITIONS ===")
try:
    positions = exchange.fetch_positions()
    if not positions:
        print("NO open positions found!")
    for p in positions:
        sym = p.get('symbol')
        size = p.get('contracts')
        side = p.get('side')
        entry = p.get('entryPrice')
        notional = p.get('notional')
        print(f"  {sym} | Side: {side} | Size: {size} | Entry: {entry} | Notional: {notional}")
except Exception as e:
    print(f"fetch_positions error: {e}")

print("\n=== RECENT ORDERS (last 10) ===")
try:
    orders = exchange.fetch_orders(limit=10)
    for o in orders:
        sym = o.get('symbol')
        side = o.get('side')
        qty = o.get('amount')
        price = o.get('price') or o.get('average')
        status = o.get('status')
        otype = o.get('type')
        ts = o.get('datetime')
        print(f"  {ts} | {sym} | {side} {qty} @ {price} | {otype} | status={status}")
except Exception as e:
    print(f"fetch_orders error: {e}")

print("\n=== OPEN ORDERS ===")
try:
    open_orders = exchange.fetch_open_orders()
    if not open_orders:
        print("NO open orders found!")
    for o in open_orders:
        sym = o.get('symbol')
        side = o.get('side')
        qty = o.get('amount')
        price = o.get('price')
        otype = o.get('type')
        print(f"  {sym} | {side} {qty} @ {price} | {otype}")
except Exception as e:
    print(f"fetch_open_orders error: {e}")
