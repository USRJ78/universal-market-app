import yfinance as yf
print("Downloading...")
try:
    df = yf.download("BTC-USD", period="2y", interval="1h", progress=False)
    print("Success!")
    print(df.shape)
except Exception as e:
    print(f"Error: {e}")
