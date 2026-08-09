import requests
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

# AMFI Scheme Codes
funds = {
    "Smallcap": "113177",     # Nippon India Small Cap Fund - Growth
    "Midcap": "105758",       # HDFC Mid Cap Fund - Growth
    "Largecap": "108466",     # ICICI Prudential Large Cap Fund - Growth (Index Proxy)
    "Gold": "114616",         # Nippon India Gold Savings Fund - Growth
    "Gilt": "100369",         # ICICI Prudential Gilt Fund - Growth (Interest Rate Proxy)
    "Infra": "103149",        # ICICI Prudential Infrastructure Fund - Growth (Commodity/Valuation Proxy)
    "Value": "100496",        # Templeton India Value Fund - Growth Plan (Value Proxy)
    "Tech": "100363"          # ICICI Prudential Technology Fund - Growth (Sector/Valuation Proxy)
}

print("Downloading mutual fund NAV histories...")
df_dict = {}

for name, code in funds.items():
    try:
        url = f"https://api.mfapi.in/mf/{code}"
        res = requests.get(url).json()
        data = res.get('data', [])
        
        records = []
        for r in data:
            records.append({
                "Date": pd.to_datetime(r['date'], format='%d-%m-%Y'),
                name: float(r['nav'])
            })
        
        df = pd.DataFrame(records).set_index("Date").sort_index()
        df_dict[name] = df
    except Exception as e:
        print(f"  Error downloading {name}: {e}")

all_df = pd.concat(df_dict.values(), axis=1).sort_index().ffill()

start_date = '2011-01-01'
end_date = '2026-07-15'
all_df = all_df.loc[start_date:end_date]
monthly_df = all_df.resample('ME').last()
dates = monthly_df.index

# Let's perform a grid search for pure mutual fund rotation with ANNUAL rebalancing (rp = 12 months)
# Since rp = 12 months, exit load is 0%, and transaction friction is virtually 0%. We will set friction to 0.1% to be conservative.
friction_rate = 0.001 

lookbacks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
top_n_choices = [1, 2]

best_cagr = 0.0
best_params = {}

for lb in lookbacks:
    for top_n in top_n_choices:
        portfolio_values = []
        current_allocations = {}
        moms = monthly_df.pct_change(lb)
        
        for i in range(len(dates)):
            current_date = dates[i]
            
            if i == 0:
                # Initialize
                init_alloc = ["Smallcap"]
                for f in init_alloc:
                    current_allocations[f] = 100000.0
                portfolio_values.append(100000.0)
                continue
                
            prev_date = dates[i-1]
            total_val = 0.0
            for f, val in current_allocations.items():
                ret = (monthly_df.loc[current_date, f] / monthly_df.loc[prev_date, f])
                current_allocations[f] = val * ret
                total_val += current_allocations[f]
                
            # Rebalance annually (every 12 months)
            if i % 12 == 0:
                signals = {}
                for f in funds.keys():
                    signals[f] = moms.loc[current_date, f]
                
                # Sort
                sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
                selected_funds = [x[0] for x in sorted_signals[:top_n]]
                
                # Target weight
                target_wt = 1.0 / top_n
                
                # Calculate friction
                fee_incurred = 0.0
                for f in list(current_allocations.keys()):
                    if f not in selected_funds:
                        fee_incurred += current_allocations[f] * friction_rate
                    else:
                        target_val = total_val * target_wt
                        change = abs(current_allocations[f] - target_val)
                        fee_incurred += (change / 2.0) * friction_rate
                        
                total_reallocated_val = total_val - fee_incurred
                
                current_allocations = {}
                for f in selected_funds:
                    current_allocations[f] = total_reallocated_val * target_wt
                
                portfolio_values.append(total_reallocated_val)
            else:
                portfolio_values.append(total_val)
                
        series = pd.Series(portfolio_values)
        cagr = (series.iloc[-1] / series.iloc[0]) ** (12 / len(series)) - 1
        
        if cagr > best_cagr:
            best_cagr = cagr
            best_params = {
                "lb": lb, "top_n": top_n, "cagr": cagr, "values": portfolio_values
            }

print("\n" + "="*75)
print(" BEST ANNUAL REBALANCE MF STRATEGY ")
print("="*75)
print(f"Momentum Lookback (lb): {best_params['lb']} months")
print(f"Top N Allocated:       {best_params['top_n']}")
print(f"CAGR:                  {best_params['cagr']*100:.2f}%")
print(f"Final Value:           INR {best_params['values'][-1]:,.2f}")
print("="*75)
