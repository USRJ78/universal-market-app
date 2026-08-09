import ccxt

DEMO_API = 'J0qo3wjxK875fZzEfl02wAzZVF3AHa'
DEMO_SECRET = 'UGtWmUs4wQITBHLsnVLffeKrnKLp8r15wcKZcH1GLwaIQsojJjvgWwK6BeR3'
ENDPOINT = 'https://cdn-ind.testnet.deltaex.org'
exchange = ccxt.delta({'apiKey': DEMO_API, 'secret': DEMO_SECRET, 'enableRateLimit': True})
exchange.urls['api'] = {'public': ENDPOINT, 'private': ENDPOINT}

markets = exchange.load_markets()
btc_ticker = exchange.fetch_ticker('BTC/USD:USD')
btc_price = btc_ticker.get('last', 65000)
print(f"BTC Price: ${btc_price:,.2f}")

# Test ALL puts for July 31 expiry
print("\n=== ALL BTC PUTS - 2026-07-31 ===")
puts_jul31 = [(m.get('strike'), sym) for sym, m in markets.items()
              if m.get('option') and m.get('base') == 'BTC'
              and m.get('optionType','').lower() == 'put'
              and '260731' in sym]
puts_jul31.sort(key=lambda x: x[0], reverse=True)

for strike, sym in puts_jul31:
    try:
        t = exchange.fetch_ticker(sym)
        ask = t.get('ask')
        bid = t.get('bid')
        last = t.get('last')
        mark = t.get('info', {}).get('mark_price')
        liquidity = "HAS ASK" if ask else ("HAS LAST" if last else ("HAS MARK" if mark else "NO PRICE"))
        print(f"  Strike ${strike:,.0f} | ask={ask} bid={bid} last={last} mark={mark} | {liquidity}")
    except Exception as e:
        print(f"  Strike ${strike:,.0f} | ERROR: {e}")
