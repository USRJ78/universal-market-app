import sys
sys.path.append('C:\\Users\\USER\\OneDrive\\Documents\\universal-market-app\\antigravity_ai_brain')
from market_sensor import MarketSensor
sensor = MarketSensor()
print("Initialized.")
try:
    data = sensor.fetch_live_indicators()
    print("Fetch successful!")
    print(data)
except Exception as e:
    print(f"Error: {e}")
