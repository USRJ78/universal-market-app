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

# We want to perform a Grid Search to find the absolute maximum return parameters
best_cagr = 0.0
best_params = {}
results = []

# Search parameters
lookbacks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] # momentum lookback months
rebalance_periods = [1, 2, 3, 4, 5, 6, 8, 12] # rebalance every N months
top_n_choices = [1, 2] # allocate to top 1 or top 2 funds
friction_rate = 0.01 # 1% transaction cost

# Pre-calculate returns for all lookbacks
moms_dict = {}
for lb in lookbacks:
    moms_dict[lb] = monthly_df.pct_change(lb)

print("\nRunning parameter grid search...")

for lb in lookbacks:
    for rp in rebalance_periods:
        for top_n in top_n_choices:
            # Simulate
            portfolio_values = []
            current_allocations = {}
            moms = moms_dict[lb]
            
            for i in range(len(dates)):
                current_date = dates[i]
                
                if i == 0:
                    # Initialize equal weight in equity assets
                    init_alloc = ["Smallcap", "Midcap", "Tech"]
                    wt = 1.0 / len(init_alloc)
                    for f in init_alloc:
                        current_allocations[f] = 100000.0 * wt
                    portfolio_values.append(100000.0)
                    continue
                
                prev_date = dates[i-1]
                total_val = 0.0
                for f, val in current_allocations.items():
                    ret = (monthly_df.loc[current_date, f] / monthly_df.loc[prev_date, f])
                    current_allocations[f] = val * ret
                    total_val += current_allocations[f]
                
                # Check if rebalance month
                if i % rp == 0:
                    # Calculate momentum signals
                    signals = {}
                    for f in funds.keys():
                        signals[f] = moms.loc[current_date, f]
                    
                    # Sort candidates
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
                    
                    # Reallocate
                    current_allocations = {}
                    for f in selected_funds:
                        current_allocations[f] = total_reallocated_val * target_wt
                    
                    portfolio_values.append(total_reallocated_val)
                else:
                    portfolio_values.append(total_val)
            
            # Compute stats
            series = pd.Series(portfolio_values)
            returns = series.pct_change().dropna()
            cagr = (series.iloc[-1] / series.iloc[0]) ** (12 / len(series)) - 1
            ann_vol = returns.std() * np.sqrt(12)
            sharpe = (cagr - 0.06) / ann_vol if ann_vol > 0 else 0
            peaks = series.cummax()
            drawdowns = (series - peaks) / peaks
            max_dd = drawdowns.min()
            
            results.append({
                "lb": lb, "rp": rp, "top_n": top_n,
                "cagr": cagr, "sharpe": sharpe, "max_dd": max_dd,
                "final_val": series.iloc[-1]
            })
            
            if cagr > best_cagr:
                best_cagr = cagr
                best_params = {
                    "lb": lb, "rp": rp, "top_n": top_n,
                    "cagr": cagr, "sharpe": sharpe, "max_dd": max_dd,
                    "values": portfolio_values
                }

print(f"\nGrid Search Complete!")
print(f"Best Parameters Found:")
print(f"  Momentum Lookback (lb): {best_params['lb']} months")
print(f"  Rebalance Period (rp):  every {best_params['rp']} months")
print(f"  Top N allocated funds:  {best_params['top_n']}")
print(f"  CAGR:                   {best_params['cagr']*100:.2f}%")
print(f"  Sharpe Ratio:           {best_params['sharpe']:.2f}")
print(f"  Max Drawdown:           {best_params['max_dd']*100:.2f}%")
print(f"  Final Portfolio Value:  INR {best_params['values'][-1]:,.2f}")

# Save the best strategy runs
results_df = pd.DataFrame(results)
results_df.to_csv("optimizer_results.csv", index=False)
print("Saved all optimizer runs to optimizer_results.csv")
