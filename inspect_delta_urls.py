import ccxt
import json

exchange = ccxt.delta()
print("Default URLs:")
print(json.dumps(exchange.urls, indent=2))

exchange.set_sandbox_mode(True)
print("\nSandbox URLs:")
print(json.dumps(exchange.urls, indent=2))
