import requests

queries = [
    "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
    "SBI Magnum Gilt Fund - Direct Plan - Growth",
    "SBI Magnum Gilt Fund",
    "HDFC Mid-Cap Opportunities Fund"
]

print("Searching details...")
for q in queries:
    url = f"https://api.mfapi.in/mf/search?q={q}"
    res = requests.get(url).json()
    print(f"\nQuery: {q}")
    for item in res[:5]:
        print(f"  Code: {item['schemeCode']} | Name: {item['schemeName']}")
