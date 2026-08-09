import requests

queries = [
    "HDFC Mid Cap",
    "HDFC Mid-Cap",
    "SBI Magnum Gilt",
    "Gilt Direct",
    "Mid Cap Direct",
    "Gold Direct",
    "Value Direct"
]

print("Searching details...")
for q in queries:
    url = f"https://api.mfapi.in/mf/search?q={q}"
    res = requests.get(url).json()
    print(f"\nQuery: {q}")
    for item in res[:5]:
        print(f"  Code: {item['schemeCode']} | Name: {item['schemeName']}")
