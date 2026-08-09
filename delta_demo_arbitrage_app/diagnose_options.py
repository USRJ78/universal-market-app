import ccxt
from datetime import datetime

DEMO_API = 'J0qo3wjxK875fZzEfl02wAzZVF3AHa'
DEMO_SECRET = 'UGtWmUs4wQITBHLsnVLffeKrnKLp8r15wcKZcH1GLwaIQsojJjvgWwK6BeR3'
ENDPOINT = 'https://cdn-ind.testnet.deltaex.org'
exchange = ccxt.delta({'apiKey': DEMO_API, 'secret': DEMO_SECRET, 'enableRateLimit': True})
exchange.urls['api'] = {'public': ENDPOINT, 'private': ENDPOINT}

print("Loading markets...")
markets = exchange.load_markets()
btc_ticker = exchange.fetch_ticker('BTC/USD:USD')
btc_price = btc_ticker.get('last', 60000)
print(f"BTC Price: ${btc_price:,.2f}")

# Scan options
strikes_by_expiry = {}
for symbol, m in markets.items():
    if m.get('option') and m.get('base') == 'BTC':
        expiry = m.get('expiryDatetime')
        strike = m.get('strike')
        opt_type = m.get('optionType')
        if expiry and strike and opt_type:
            exp_dt = datetime.strptime(expiry.split('T')[0], "%Y-%m-%d")
            days_to_expiry = (exp_dt - datetime.today()).days
            if 3 < days_to_expiry < 45:
                if expiry not in strikes_by_expiry:
                    strikes_by_expiry[expiry] = {'calls': [], 'puts': []}
                if opt_type.lower() == 'call':
                    strikes_by_expiry[expiry]['calls'].append((strike, symbol))
                elif opt_type.lower() == 'put':
                    strikes_by_expiry[expiry]['puts'].append((strike, symbol))

print(f"\nTotal valid expiries found (3-45 days): {len(strikes_by_expiry)}")
for exp in sorted(strikes_by_expiry.keys()):
    data = strikes_by_expiry[exp]
    exp_dt = datetime.strptime(exp.split('T')[0], "%Y-%m-%d")
    days = (exp_dt - datetime.today()).days
    exp_date = exp.split('T')[0]
    print(f"  Expiry: {exp_date} ({days}d) | Calls: {len(data['calls'])} | Puts: {len(data['puts'])}")

if not strikes_by_expiry:
    print("\nNO VALID EXPIRIES FOUND - This is why no trade executes!")
else:
    best_expiry = max(strikes_by_expiry.keys(), key=lambda k: len(strikes_by_expiry[k]['calls']))
    calls = sorted(strikes_by_expiry[best_expiry]['calls'], key=lambda x: x[0])
    puts = sorted(strikes_by_expiry[best_expiry]['puts'], key=lambda x: x[0], reverse=True)
    best_date = best_expiry.split('T')[0]
    print(f"\nBest expiry: {best_date}")
    print(f"Deepest ITM Call: strike=${calls[0][0]:,.0f} | {calls[0][1]}")
    print(f"Deepest ITM Put:  strike=${puts[0][0]:,.0f} | {puts[0][1]}")

    print("\n--- Checking CALL quotes (deepest 5 ITM) ---")
    for strike, sym in calls[:5]:
        try:
            t = exchange.fetch_ticker(sym)
            ask = t.get('ask')
            bid = t.get('bid')
            last = t.get('last')
            print(f"  {sym}: ask={ask} bid={bid} last={last}  {'<<< HAS QUOTE' if ask else '<<< NO QUOTE (problem!)'}")
        except Exception as e:
            print(f"  {sym}: ERROR - {e}")

    print("\n--- Checking PUT quotes (deepest 5 ITM) ---")
    for strike, sym in puts[:5]:
        try:
            t = exchange.fetch_ticker(sym)
            ask = t.get('ask')
            bid = t.get('bid')
            last = t.get('last')
            print(f"  {sym}: ask={ask} bid={bid} last={last}  {'<<< HAS QUOTE' if ask else '<<< NO QUOTE (problem!)'}")
        except Exception as e:
            print(f"  {sym}: ERROR - {e}")
