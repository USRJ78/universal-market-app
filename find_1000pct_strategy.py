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

def run_high_yield_simulation():
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
    
    # We want to check 7-day DTE options
    T_days = 7
    T_yrs = T_days / 365.0
    
    # Slice into weekly non-overlapping windows
    indices = np.arange(0, len(closes) - T_days, T_days)
    S_start = closes[indices]
    S_end = closes[indices + T_days]
    V_start = vols[indices]
    
    # We want to find a 1-year window (approx 52 weeks) that yields > 1000%
    # We will search over a grid of strikes and leverage
    c_strikes = np.arange(0.80, 1.30, 0.02) # 25 steps
    p_strikes = np.arange(0.70, 1.20, 0.02) # 25 steps
    c_qtys = np.arange(1.0, 15.0, 1.0)      # 14 steps
    p_qtys = np.arange(1.0, 15.0, 1.0)      # 14 steps
    
    # We will slide a 1-year window (52 weeks) across the backtest period
    weeks_in_year = 52
    total_weeks = len(S_start)
    
    print(f"Total weeks in backtest: {total_weeks}")
    print(f"Grid size: {len(c_strikes)} x {len(p_strikes)} x {len(c_qtys)} x {len(p_qtys)} = {len(c_strikes)*len(p_strikes)*len(c_qtys)*len(p_qtys):,} per window")
    
    # Precompute put options
    put_premiums = np.zeros((len(p_strikes), total_weeks))
    put_payoffs = np.zeros((len(p_strikes), total_weeks))
    for i, p_strk in enumerate(p_strikes):
        K = S_start * p_strk
        put_premiums[i] = bs_put_vec(S_start, K, T_yrs, r, V_start)
        put_payoffs[i] = np.maximum(0, K - S_end)
        
    best_ret = 0.0
    best_params = None
    best_period = None
    best_dd = 0.0
    
    for c_idx, c_strk in enumerate(c_strikes):
        K_c = S_start * c_strk
        c_prem = bs_call_vec(S_start, K_c, T_yrs, r, V_start)
        c_payoff = np.maximum(0, S_end - K_c)
        
        for p_idx, p_strk in enumerate(p_strikes):
            p_prem = put_premiums[p_idx]
            p_pay = put_payoffs[p_idx]
            
            # Broadcast over c_qty and p_qty
            for c_qty in c_qtys:
                for p_qty in p_qtys:
                    # Calculate weekly returns
                    net_prem = (c_prem * c_qty) + (p_prem * p_qty)
                    net_pay = (c_payoff * c_qty) + (p_pay * p_qty)
                    
                    margin_c = (S_start * 0.15) * c_qty
                    margin_p = (S_start * 0.15) * p_qty
                    total_margin = np.maximum(margin_c + margin_p, 100.0)
                    
                    weekly_ret = (net_pay - net_prem) / total_margin
                    weekly_ret = np.maximum(weekly_ret, -0.95) # Cap loss at 95% per week to avoid total ruin
                    
                    # Slide 1-year window (52 weeks)
                    for start_wk in range(0, total_weeks - weeks_in_year, 4): # Step by 4 weeks to speed up
                        window_rets = weekly_ret[start_wk : start_wk + weeks_in_year]
                        cum_eq = np.cumprod(1.0 + window_rets)
                        final_ret = cum_eq[-1] - 1.0
                        
                        if final_ret > best_ret:
                            best_ret = final_ret
                            # Calculate drawdown for this window
                            peaks = np.maximum.accumulate(cum_eq)
                            dd = np.min((cum_eq - peaks) / peaks)
                            
                            best_dd = dd
                            best_ret = final_ret
                            best_params = (c_strk, p_strk, c_qty, p_qty)
                            best_period = (start_wk, start_wk + weeks_in_year)
                            
        if (c_idx + 1) % 5 == 0:
            print(f"Processed {c_idx+1}/{len(c_strikes)} call strike steps. Best 1-Year Return: {best_ret*100:.2f}%")
            
    print("\n========== SEARCH COMPLETE ==========")
    if best_params:
        print(f"Best 1-Year Period Return: {best_ret*100:.2f}%")
        print(f"Max Drawdown during that year: {best_dd*100:.2f}%")
        print(f"Call Strike: {best_params[0]*100:.0f}% of Spot")
        print(f"Put Strike: {best_params[1]*100:.0f}% of Spot")
        print(f"Call Leverage/Qty: {best_params[2]}x")
        print(f"Put Leverage/Qty: {best_params[3]}x")
        print(f"Starts week: {best_period[0]} to {best_period[1]}")
    else:
        print("No strategy found.")

if __name__ == '__main__':
    run_high_yield_simulation()
