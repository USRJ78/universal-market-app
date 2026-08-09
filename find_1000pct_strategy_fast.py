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

def run_fast_simulation():
    print("Fetching BTC-USD Data (2020-2026) for high-volatility search...")
    df = yf.download("BTC-USD", start="2020-01-01", end="2026-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df['Vol30'] = df['Vol30'].bfill()
    df['Vol30'] = df['Vol30'].apply(lambda x: 0.30 if math.isnan(x) or x <= 0 else x)
    
    closes = df['Close'].values
    vols = df['Vol30'].values
    r = 0.05
    
    T_days = 7
    T_yrs = T_days / 365.0
    
    # Non-overlapping 7-day windows
    indices = np.arange(0, len(closes) - T_days, T_days)
    S_start = closes[indices]
    S_end = closes[indices + T_days]
    V_start = vols[indices]
    W = len(S_start)
    
    c_strikes = np.arange(0.80, 1.30, 0.02) # 25 steps
    p_strikes = np.arange(0.70, 1.20, 0.02) # 25 steps
    c_qtys = np.arange(1.0, 15.0, 1.0)      # 14 steps
    p_qtys = np.arange(1.0, 15.0, 1.0)      # 14 steps
    
    print(f"Total Weeks: {W}")
    print(f"Grid Permutations: {len(c_strikes) * len(p_strikes) * len(c_qtys) * len(p_qtys):,}")
    
    # Precompute options
    call_prems = np.zeros((len(c_strikes), W))
    call_payoffs = np.zeros((len(c_strikes), W))
    for i, c_strk in enumerate(c_strikes):
        K = S_start * c_strk
        call_prems[i] = bs_call_vec(S_start, K, T_yrs, r, V_start)
        call_payoffs[i] = np.maximum(0, S_end - K)
        
    put_prems = np.zeros((len(p_strikes), W))
    put_payoffs = np.zeros((len(p_strikes), W))
    for i, p_strk in enumerate(p_strikes):
        K = S_start * p_strk
        put_prems[i] = bs_put_vec(S_start, K, T_yrs, r, V_start)
        put_payoffs[i] = np.maximum(0, K - S_end)
        
    best_ret = 0.0
    best_params = None
    best_period_dates = None
    best_dd = 0.0
    
    # We will iterate over c_strk and p_strk to keep memory size reasonable, 
    # but vectorize the quantity sweeps (c_qty and p_qty) completely!
    C_Q = c_qtys[:, np.newaxis, np.newaxis] # (14, 1, 1)
    P_Q = p_qtys[np.newaxis, :, np.newaxis] # (1, 14, 1)
    
    start_time = time.time()
    
    for c_idx, c_strk in enumerate(c_strikes):
        c_prem = call_prems[c_idx] # (W,)
        c_pay = call_payoffs[c_idx] # (W,)
        
        for p_idx, p_strk in enumerate(p_strikes):
            p_prem = put_prems[p_idx] # (W,)
            p_pay = put_payoffs[p_idx] # (W,)
            
            # Broadcast premiums and payoffs
            # total_prem shape: (14, 14, W)
            total_prem = (c_prem * C_Q) + (p_prem * P_Q)
            total_pay = (c_pay * C_Q) + (p_pay * P_Q)
            
            margin_c = (S_start * 0.15) * C_Q
            margin_p = (S_start * 0.15) * P_Q
            total_margin = np.maximum(margin_c + margin_p, 100.0)
            
            # window_ret shape: (14, 14, W)
            window_ret = (total_pay - total_prem) / total_margin
            window_ret = np.maximum(window_ret, -0.95) # Cap loss at 95% to prevent total ruin
            
            # Vectorized rolling product using logs
            log_r = np.log(1.0 + window_ret) # (14, 14, W)
            cum_log_r = np.cumsum(log_r, axis=2) # (14, 14, W)
            
            # Slide window size 52
            weeks_in_year = 52
            for start_wk in range(0, W - weeks_in_year, 1): # Step by 1 week for precision!
                end_wk = start_wk + weeks_in_year
                
                # Get log return for the 52-week period
                if start_wk == 0:
                    period_log_r = cum_log_r[:, :, end_wk - 1]
                else:
                    period_log_r = cum_log_r[:, :, end_wk - 1] - cum_log_r[:, :, start_wk - 1]
                    
                period_ret = np.exp(period_log_r) - 1.0 # (14, 14)
                
                max_local_idx = np.unravel_index(np.argmax(period_ret), period_ret.shape)
                max_local_ret = period_ret[max_local_idx]
                
                if max_local_ret > best_ret:
                    best_ret = max_local_ret
                    # Reconstruct equity curve for this window to calculate drawdown
                    best_c_qty = c_qtys[max_local_idx[0]]
                    best_p_qty = p_qtys[max_local_idx[1]]
                    
                    window_rets = window_ret[max_local_idx[0], max_local_idx[1], start_wk:end_wk]
                    cum_eq = np.cumprod(1.0 + window_rets)
                    peaks = np.maximum.accumulate(cum_eq)
                    best_dd = np.min((cum_eq - peaks) / peaks)
                    
                    best_params = (c_strk, p_strk, best_c_qty, best_p_qty)
                    # Convert week indices to dates
                    start_date = df.index[indices[start_wk]].strftime("%Y-%m-%d")
                    end_date = df.index[indices[end_wk]].strftime("%Y-%m-%d")
                    best_period_dates = (start_date, end_date)
                    
    elapsed = time.time() - start_time
    print(f"\n========== SEARCH COMPLETE (Took {elapsed:.2f}s) ==========")
    if best_params:
        print(f"Best 1-Year Period Return: {best_ret*100:,.2f}%")
        print(f"Max Drawdown during that year: {best_dd*100:.2f}%")
        print(f"Call Strike: {best_params[0]*100:.0f}% of Spot")
        print(f"Put Strike: {best_params[1]*100:.0f}% of Spot")
        print(f"Call Leverage/Qty: {best_params[2]}x")
        print(f"Put Leverage/Qty: {best_params[3]}x")
        print(f"Period: {best_period_dates[0]} to {best_period_dates[1]}")
    else:
        print("No strategy found.")

if __name__ == '__main__':
    run_fast_simulation()
