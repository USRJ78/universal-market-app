import requests

codes = {
    "Nippon Small Cap": "113177",
    "HDFC Mid Cap": "105758",
    "ICICI Large Cap": "108466",
    "Nippon Gold": "114616",
    "SBI Gilt": "101918",
    "ICICI Infra": "103149",
    "Templeton Value": "100496",
    "ICICI Tech": "100363"
}

for name, code in codes.items():
    try:
        url = f"https://api.mfapi.in/mf/{code}"
        res = requests.get(url).json()
        meta = res.get('meta', {})
        data = res.get('data', [])
        if data:
            start_date = data[-1]['date']
            end_date = data[0]['date']
            print(f"Name: {name} | Code: {code} | Meta Name: {meta.get('scheme_name')} | Start: {start_date} | End: {end_date} | Points: {len(data)}")
        else:
            print(f"Name: {name} | Code: {code} | No data found!")
    except Exception as e:
        print(f"Name: {name} | Code: {code} | Error: {e}")
