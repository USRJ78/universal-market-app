import ccxt
import json
import datetime
import os

DEMO_API = 'J0qo3wjxK875fZzEfl02wAzZVF3AHa'
DEMO_SECRET = 'UGtWmUs4wQITBHLsnVLffeKrnKLp8r15wcKZcH1GLwaIQsojJjvgWwK6BeR3'
ENDPOINT = 'https://cdn-ind.testnet.deltaex.org'
exchange = ccxt.delta({'apiKey': DEMO_API, 'secret': DEMO_SECRET, 'enableRateLimit': True})
exchange.urls['api'] = {'public': ENDPOINT, 'private': ENDPOINT}

PUT_SYMBOL = 'BTC/USD:USD-260731-78000-P'
PUT_QTY = 4
PUT_STRIKE = 78000.0

print(f"Fetching current price for {PUT_SYMBOL}...")
markets = exchange.load_markets()
p_ticker = exchange.fetch_ticker(PUT_SYMBOL)
p_ask = p_ticker.get('ask') or p_ticker.get('last') or p_ticker.get('close')
p_info_mark = p_ticker.get('info', {}).get('mark_price')
if not p_ask and p_info_mark:
    p_ask = float(p_info_mark)

print(f"Put ticker - ask: {p_ticker.get('ask')} | last: {p_ticker.get('last')} | mark: {p_info_mark}")
print(f"Using ref price: {p_ask}")

if not p_ask:
    print("ERROR: No price available for put. Cannot place order.")
    exit(1)

fill = None

# Try market order, then limit
print(f"\nPlacing order: Buy {PUT_QTY}x {PUT_SYMBOL} @ market...")
try:
    o = exchange.create_market_buy_order(PUT_SYMBOL, PUT_QTY)
    fill = float(o.get('average') or o.get('price') or p_ask)
    print(f"[OK] Market order filled @ ${fill:.2f}")
except Exception as e:
    print(f"Market order failed: {e}")
    limit_p = round(p_ask * 1.05, 1)
    print(f"Trying limit order @ ${limit_p:.1f}...")
    try:
        o = exchange.create_limit_buy_order(PUT_SYMBOL, PUT_QTY, limit_p)
        fill = float(o.get('average') or o.get('price') or limit_p)
        print(f"[OK] Limit order placed @ ${limit_p:.1f} | status: {o.get('status')}")
    except Exception as e2:
        print(f"Limit order also failed: {e2}")
        exit(1)

if fill is None:
    print("ERROR: fill price not set, aborting state update")
    exit(1)

# Update state file
STATE = 'delta_demo_geometry_state.json'
with open(STATE, 'r') as f:
    state = json.load(f)

if state.get('active_position'):
    contract_size = state['active_position'].get('contract_size', 0.001)
    c_fill = state['active_position']['call']['entry_price']
    c_qty = state['active_position']['call']['qty']

    state['active_position']['put'] = {
        "symbol": PUT_SYMBOL,
        "qty": PUT_QTY,
        "entry_price": fill,
        "strike": PUT_STRIKE
    }
    state['active_position']['total_cost'] = (c_fill * c_qty * contract_size) + (fill * PUT_QTY * contract_size)
    state['last_update'] = datetime.datetime.now().isoformat()

    with open(STATE, 'w') as f:
        json.dump(state, f, indent=4)

    print(f"\n[DONE] State updated. New total cost: ${state['active_position']['total_cost']:.2f} USD")
    print(f"   Call leg: {c_qty}x @ ${c_fill:.2f}")
    print(f"   Put leg:  {PUT_QTY}x @ ${fill:.2f}")

# Verify on exchange
print("\n=== VERIFYING OPEN POSITIONS ===")
try:
    positions = exchange.fetch_positions()
    for p in positions:
        print(f"  {p.get('symbol')} | {p.get('side')} | size={p.get('contracts')} | entry={p.get('entryPrice')}")
except Exception as e:
    print(f"fetch_positions error: {e}")
