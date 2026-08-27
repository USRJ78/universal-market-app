import requests

url = "https://cdn-ind.testnet.deltaex.org/v2/products"
res = requests.get(url).json()

products = res.get("result", [])
call_options = [p for p in products if p.get("contract_type") == "call_options"]

print(f"Total Call Option Products Found on Delta Testnet: {len(call_options)}")
for p in call_options[:10]:
    print(f"  - Symbol: {p['symbol']} | Strike: {p.get('strike_price')} | Expiry: {p.get('settlement_time')}")
