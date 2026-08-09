import os
import pandas as pd
from backtest_graham_lynch_cached import calculate_graham_value

CACHE_DIR = 'cache_gl'
files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')]

scores = []
print("Scanning market for stocks with Market Cap > 500Cr...")

for f in files:
    t = f.replace('_NS.pkl', '.NS')
    df = pd.read_pickle(os.path.join(CACHE_DIR, f))
    
    if df.empty or 'Close' not in df.columns:
        continue
        
    price = df['Close'].iloc[-1]
    if pd.isna(price) or price <= 0:
        continue
        
    eps = df['EPS'].iloc[-1]
    g = df['GrowthPct'].iloc[-1]
    g = max(5.0, min(25.0, g))
    
    # Check if we stored market cap, if not, skip or compute
    if 'MarketCapCr' in df.columns:
        mcap = df['MarketCapCr'].iloc[-1]
    else:
        mcap = 1000  # Default dummy
        
    # We used 1000 as dummy in fill_cache.py for some stocks.
    # To get actual market cap, we might have to use yahooquery.
    
    if pd.isna(eps) or eps <= 0:
        continue
        
    intrinsic_val = calculate_graham_value(eps, g)
    pe = price / eps if eps > 0 else 999
    peg = pe / g if g > 0 else 999
    margin_of_safety = intrinsic_val / price
    
    if margin_of_safety > 1.0 and peg < 1.5:
        scores.append({
            'Ticker': t,
            'Price': price,
            'Intrinsic Value': intrinsic_val,
            'Margin of Safety': margin_of_safety,
            'PEG Ratio': peg,
            'EPS': eps,
            'Growth %': g,
            'MarketCapCr': mcap
        })

df_scores = pd.DataFrame(scores)
if len(df_scores) > 0:
    df_scores.sort_values(by='Margin of Safety', ascending=False, inplace=True)
    candidates = df_scores.head(50)['Ticker'].tolist()
    
    print("Fetching real market caps for top candidates...")
    from yahooquery import Ticker
    yq = Ticker(candidates)
    stats = yq.price
    
    true_mcaps = []
    for t in df_scores['Ticker']:
        mcap_cr = 0
        if isinstance(stats, dict) and t in stats and isinstance(stats[t], dict):
            mcap = stats[t].get('marketCap', 0)
            if mcap is not None:
                mcap_cr = mcap / 10000000.0 # Convert to Crores
        true_mcaps.append(mcap_cr)
        
    df_scores['TrueMarketCapCr'] = true_mcaps
    df_scores = df_scores[df_scores['TrueMarketCapCr'] > 500]
    
    top_15 = df_scores.head(15).drop(columns=['MarketCapCr'])

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print("\nTop Graham & Lynch Picks (> 500Cr Market Cap):")
    print(top_15.to_string(index=False))
else:
    print("No stocks found matching criteria.")
