import requests

funds_to_search = [
    "Nippon India Small Cap Fund",
    "HDFC Mid-Cap Opportunities Fund",
    "ICICI Prudential Bluechip Fund",
    "Nippon India Gold Savings Fund",
    "SBI Magnum Gilt Fund",
    "ICICI Prudential Infrastructure Fund",
    "Templeton India Value Fund",
    "ICICI Prudential Technology Fund"
]

print("Searching scheme codes on api.mfapi.in...")
for query in funds_to_search:
    try:
        url = f"https://api.mfapi.in/mf/search?q={query}"
        res = requests.get(url).json()
        print(f"\nQuery: {query}")
        # Print top 3 growth options
        growth_options = [x for x in res if "growth" in x['schemeName'].lower() and "direct" in x['schemeName'].lower()]
        if not growth_options:
            growth_options = [x for x in res if "growth" in x['schemeName'].lower()]
        for item in growth_options[:3]:
            print(f"  Code: {item['schemeCode']} | Name: {item['schemeName']}")
    except Exception as e:
        print(f"Error searching {query}: {e}")
