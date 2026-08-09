import yfinance as yf
print("Downloading VIX...")
vix = yf.download("^VIX", period="2y", interval="1h", progress=False)
print("VIX download finished. Shape:", vix.shape)

print("Downloading TNX...")
tnx = yf.download("^TNX", period="2y", interval="1h", progress=False)
print("TNX download finished. Shape:", tnx.shape)
