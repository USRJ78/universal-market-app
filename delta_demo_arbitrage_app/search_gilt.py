import requests

url = "https://api.mfapi.in/mf/search?q=Magnum Gilt"
res = requests.get(url).json()
for x in res:
    print(f"Code: {x['schemeCode']} | Name: {x['schemeName']}")
