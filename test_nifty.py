import yfinance as yf
print("Downloading 2 years of Nifty...")
nifty = yf.download("^NSEI", period="2y", interval="1h", progress=False)
print("Nifty shape:", nifty.shape)
