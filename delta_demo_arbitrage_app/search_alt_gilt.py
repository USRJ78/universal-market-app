import requests

queries = [
    "SBI Magnum Gilt Fund - Growth",
    "SBI Magnum Gilt Fund - Regular Plan - Growth",
    "ICICI Prudential Gilt Fund - Growth",
    "SBI Magnum Gilt Fund"
]

print("Searching gilt codes...")
for q in queries:
    url = f"https://api.mfapi.in/mf/search?q={q}"
    res = requests.get(url).json()
    print(f"\nQuery: {q}")
    for x in res[:5]:
        print(f"  Code: {x['schemeCode']} | Name: {x['schemeName']}")
