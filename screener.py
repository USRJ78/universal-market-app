import pandas as pd
import numpy as np
from backtest_graham_lynch_cached import load_cached_data, calculate_graham_value, get_historical_eps

data, fundamentals = load_cached_data()

latest_date = data.index[-1]
current_prices = data.iloc[-1]

print(f"Scanning market for {latest_date.strftime('%Y-%m-%d')}...")

scores = []
for t in fundamentals.keys():
    if t not in current_prices or pd.isna(current_prices[t]): continue
    price = current_prices[t]
    if price <= 0: continue
    
    f = fundamentals[t]
    hist_eps = f['current_eps'] # For current screening, we use current EPS directly!
    g = f['growth_rate']
    
    intrinsic_val = calculate_graham_value(hist_eps, g)
    pe = price / hist_eps if hist_eps > 0 else 999
    peg = pe / g if g > 0 else 999
    margin_of_safety = intrinsic_val / price
    
    if margin_of_safety > 1.0 and peg < 1.5:
        scores.append({
            'Ticker': t,
            'Price': price,
            'Intrinsic Value': intrinsic_val,
            'Margin of Safety': margin_of_safety,
            'PEG Ratio': peg,
            'EPS': hist_eps,
            'Growth %': g
        })

scores.sort(key=lambda x: x['Margin of Safety'], reverse=True)
top_15 = scores[:15]

df = pd.DataFrame(top_15)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print("\nTop 15 Graham & Lynch Value Picks for Today:")
print(df.to_string(index=False))
