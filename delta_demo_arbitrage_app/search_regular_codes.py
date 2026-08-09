import requests

queries = [
    "Nippon India Small Cap Fund Growth Option",
    "HDFC Mid Cap Opportunities Fund Growth",
    "ICICI Prudential Bluechip Fund Growth",
    "Nippon India Gold Savings Fund Growth",
    "SBI Magnum Gilt Fund Growth",
    "ICICI Prudential Infrastructure Fund Growth",
    "Templeton India Value Fund Growth",
    "ICICI Prudential Technology Fund Growth"
]

print("Searching regular growth options...")
for q in queries:
    url = f"https://api.mfapi.in/mf/search?q={q}"
    res = requests.get(url).json()
    print(f"\nQuery: {q}")
    # filter for growth and exclude "direct" to get regular plans
    regular_growth = [x for x in res if "growth" in x['schemeName'].lower() and "direct" not in x['schemeName'].lower()]
    for item in regular_growth[:3]:
        print(f"  Code: {item['schemeCode']} | Name: {item['schemeName']}")
