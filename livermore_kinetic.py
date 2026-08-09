import numpy as np
import pandas as pd
import yfinance as yf
import math
import time
from scipy.special import erf

def norm_cdf_vec(x):
    return (1.0 + erf(x / 1.4142135623730951)) / 2.0

def bs_call_vec(S, K, T, r, sigma):
    sigma = np.maximum(sigma, 1e-5)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    return S * norm_cdf_vec(d1) - K * np.exp(-r*T) * norm_cdf_vec(d2)

def bs_put_vec(S, K, T, r, sigma):
    sigma = np.maximum(sigma, 1e-5)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    return K * np.exp(-r*T) * norm_cdf_vec(-d2) - S * norm_cdf_vec(-d1)

def run_livermore_kinetic():
    print("Fetching NIFTY 50 Data (2014-2024)...")
    df = yf.download("^NSEI", start="2014-01-01", end="2024-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df['Vol30'] = df['Vol30'].bfill()
    df['Vol30'] = df['Vol30'].apply(lambda x: 0.15 if math.isnan(x) or x <= 0 else x)
    
    closes = df['Close'].values
    vols = df['Vol30'].values
    r = 0.05
    T_days = 7
    T_yrs = T_days / 365.0
    
    indices = np.arange(0, len(closes) - T_days, T_days)
    S_start = closes[indices]
    S_end = closes[indices + T_days]
    V_start = vols[indices]
    windows_count = len(S_start)
    
    # Sweep Parameters
    # Distance of OTM longs (1% to 50% OTM)
    distances = np.arange(0.01, 0.51, 0.01) # 50 steps
    # Ratio N of Longs to 1 Short
    ratios = np.arange(1.0, 20.1, 0.1) # 191 steps
    
    print(f"Total Geometries to test: {len(distances) * len(ratios)}")
    
    # Constant Short ATM Straddle
    short_c_prem = bs_call_vec(S_start, S_start, T_yrs, r, V_start)
    short_p_prem = bs_put_vec(S_start, S_start, T_yrs, r, V_start)
    short_c_payoff = np.maximum(0, S_end - S_start)
    short_p_payoff = np.maximum(0, S_start - S_end)
    
    results = []
    
    start_time = time.time()
    for d in distances:
        K_c = S_start * (1.0 + d)
        K_p = S_start * (1.0 - d)
        
        long_c_prem = bs_call_vec(S_start, K_c, T_yrs, r, V_start)
        long_p_prem = bs_put_vec(S_start, K_p, T_yrs, r, V_start)
        long_c_payoff = np.maximum(0, S_end - K_c)
        long_p_payoff = np.maximum(0, K_p - S_end)
        
        # Vectorize across all ratios
        R = ratios[:, np.newaxis]
        
        # Net Premium = Premium Collected (Shorts) - Premium Paid (Longs * Ratio)
        # We sell 1x ATM Call and 1x ATM Put, buy R*x OTM Call and R*x OTM Put
        net_prem = (short_c_prem + short_p_prem)[np.newaxis, :] - ((long_c_prem + long_p_prem)[np.newaxis, :] * R)
        
        # Net Payoff = (Longs Payoff * Ratio) - Shorts Payoff
        net_payoff = ((long_c_payoff + long_p_payoff)[np.newaxis, :] * R) - (short_c_payoff + short_p_payoff)[np.newaxis, :]
        
        # Margin = 20% of Spot (for the naked shorts) + Premium Paid if net_prem < 0
        margin_req = (S_start * 0.20)[np.newaxis, :] * 2.0 # For 2 naked shorts
        margin_req = np.maximum(margin_req, 1000.0)
        
        # Calculate Returns
        window_ret = (net_payoff + net_prem) / margin_req
        # Floor returns at -1.0
        window_ret = np.maximum(window_ret, -1.0)
        
        cum_equity = np.cumprod(1.0 + window_ret, axis=1)
        final_returns = cum_equity[:, -1] - 1.0
        
        peaks = np.maximum.accumulate(cum_equity, axis=1)
        drawdowns = (cum_equity - peaks) / peaks
        max_dd = np.min(drawdowns, axis=1)
        
        calmars = np.where(max_dd < 0, final_returns / np.abs(max_dd), final_returns / 1e-5)
        
        # Average Net Premium at inception (to check if it's zero-cost)
        avg_net_prem = np.mean(net_prem, axis=1)
        
        for r_idx in range(len(ratios)):
            results.append({
                'Distance': d,
                'Ratio': ratios[r_idx],
                'Total Return': final_returns[r_idx],
                'Max Drawdown': max_dd[r_idx],
                'Calmar': calmars[r_idx],
                'Avg Net Premium': avg_net_prem[r_idx]
            })

    print(f"Execution took {time.time() - start_time:.2f} seconds.")
    
    # Sort by Calmar
    results.sort(key=lambda x: x['Calmar'], reverse=True)
    
    report = "# 🎯 The Livermore Kinetic Strategy Results\n\n"
    report += "A Double Ratio Volatility Backspread engineered for pure convexity.\n\n"
    
    for i, res in enumerate(results[:10]):
        report += f"## Rank #{i+1}\n"
        report += f"* **Short Strike:** ATM (100%)\n"
        report += f"* **Long Call Strike:** { (1.0 + res['Distance']) * 100:.1f}%\n"
        report += f"* **Long Put Strike:** { (1.0 - res['Distance']) * 100:.1f}%\n"
        report += f"* **Structure Ratio:** Sell 1x ATM, Buy {res['Ratio']:.1f}x OTM\n"
        report += f"* **Avg Net Premium at Inception:** {'Credit' if res['Avg Net Premium'] > 0 else 'Debit'} ({(res['Avg Net Premium']):.2f})\n"
        report += f"### Performance\n"
        report += f"* **Total Return:** {res['Total Return']*100:,.2f}%\n"
        report += f"* **Max Drawdown:** {res['Max Drawdown']*100:,.2f}%\n"
        report += f"* **Calmar Ratio:** {res['Calmar']:,.2f}\n\n"
        
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\livermore_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("Done")

if __name__ == '__main__':
    run_livermore_kinetic()
