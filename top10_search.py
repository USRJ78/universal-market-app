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

def run_top10_search():
    print("Fetching Bitcoin Data (2014-2024)...")
    df = yf.download("BTC-USD", start="2014-01-01", end="2024-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df['Vol30'] = df['Vol30'].bfill()
    df['Vol30'] = df['Vol30'].apply(lambda x: 0.15 if math.isnan(x) or x <= 0 else x)
    
    closes = df['Close'].values
    vols = df['Vol30'].values
    r = 0.05
    # Realistic strike boundaries (Liquid NSE options are usually within 10% of spot)
    c_strikes = np.arange(0.90, 1.11, 0.01) # 21 steps
    p_strikes = np.arange(0.90, 1.11, 0.01) # 21 steps
    
    # Realistic contract sizes (multiples of 0.5 to represent ratio spreading lots)
    c_qtys = np.arange(1.0, 10.5, 0.5) # 20 steps
    p_qtys = np.arange(1.0, 10.5, 0.5) # 20 steps
    
    total_perms = len(c_strikes) * len(p_strikes) * len(c_qtys) * len(p_qtys)
    print(f"Total Combinations in fast grid: {total_perms:,}")
    
    T_days = 7
    T_yrs = T_days / 365.0
    
    indices = np.arange(0, len(closes) - T_days, T_days)
    S_start = closes[indices]
    S_end = closes[indices + T_days]
    V_start = vols[indices]
    windows_count = len(S_start)
    
    put_premiums = np.zeros((len(p_strikes), windows_count))
    put_payoffs = np.zeros((len(p_strikes), windows_count))
    for i, p_strk in enumerate(p_strikes):
        K = S_start * p_strk
        put_premiums[i] = bs_put_vec(S_start, K, T_yrs, r, V_start)
        put_payoffs[i] = np.maximum(0, K - S_end)
        
    valid_results = []
    
    start_time = time.time()
    for c_idx, c_strk in enumerate(c_strikes):
        K_c = S_start * c_strk
        c_prem = bs_call_vec(S_start, K_c, T_yrs, r, V_start)
        c_payoff = np.maximum(0, S_end - K_c)
        
        for p_idx in range(len(p_strikes)):
            p_prem = put_premiums[p_idx]
            p_pay = put_payoffs[p_idx]
            
            C_Q = c_qtys[:, np.newaxis]
            P_Q = p_qtys[np.newaxis, :]
            
            total_prem = ((c_prem[np.newaxis, np.newaxis, :] * C_Q[:, :, np.newaxis]) + (p_prem[np.newaxis, np.newaxis, :] * P_Q[:, :, np.newaxis])) * 1.01
            total_pay = (c_payoff[np.newaxis, np.newaxis, :] * C_Q[:, :, np.newaxis]) + (p_pay[np.newaxis, np.newaxis, :] * P_Q[:, :, np.newaxis])
            
            margin_c = (S_start * 0.20)[np.newaxis, np.newaxis, :] * C_Q[:, :, np.newaxis]
            margin_p = (S_start * 0.20)[np.newaxis, np.newaxis, :] * P_Q[:, :, np.newaxis]
            total_margin = np.maximum(margin_c + margin_p, 1000.0)
            
            window_ret = (total_pay - total_prem) / (total_margin)
            window_ret = np.maximum(window_ret, -1.0)
            cum_equity = np.cumprod(1.0 + window_ret, axis=2)
            final_returns = cum_equity[:, :, -1] - 1.0
            
            peaks = np.maximum.accumulate(cum_equity, axis=2)
            drawdowns = (cum_equity - peaks) / peaks
            max_dd = np.min(drawdowns, axis=2)
            
            calmars = np.where(max_dd < 0, final_returns / np.abs(max_dd), final_returns / 1e-5)
            
            valid_ret = final_returns.flatten()
            valid_dd = max_dd.flatten()
            valid_calmars = calmars.flatten()
            
            for r_idx in range(len(valid_ret)):
                c_idx_qty = r_idx // len(p_qtys)
                p_idx_qty = r_idx % len(p_qtys)
                valid_results.append((valid_ret[r_idx], valid_dd[r_idx], valid_calmars[r_idx], (c_strk, p_strikes[p_idx], c_qtys[c_idx_qty], p_qtys[p_idx_qty])))


    print(f"\nExecution took {time.time() - start_time:.2f} seconds.")
    
    # Sort by Calmar Ratio (Index 2)
    valid_results.sort(key=lambda x: x[2], reverse=True)
    
    report = "# Top 10 Configurations (Realistic 10-Year Return - Bitcoin)\n\n"
    report += "Constrained to Liquid Strikes (90%-110%), 1% Slippage, over 2014-2024. Sorted by Calmar Ratio.\n\n"
    for i, (ret, dd, calmar, params) in enumerate(valid_results[:10]):
        report += f"## Rank #{i+1}\n"
        report += f"* **Call Strike:** {params[0]*100:.0f}%\n"
        report += f"* **Put Strike:** {params[1]*100:.0f}%\n"
        report += f"* **Call Qty:** {params[2]:.1f}x\n"
        report += f"* **Put Qty:** {params[3]:.1f}x\n"
        report += f"### Performance\n"
        report += f"* **Total Return:** {ret*100:,.2f}%\n"
        report += f"* **Max Drawdown:** {dd*100:,.2f}%\n"
        report += f"* **Calmar Ratio:** {calmar:,.2f}\n\n"
        
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\top10_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("Done")

if __name__ == '__main__':
    run_top10_search()
