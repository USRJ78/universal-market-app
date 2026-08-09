import math
import random
import numpy as np
import pandas as pd
import yfinance as yf
from multiprocessing import Pool, cpu_count
import itertools
import time

def norm_cdf(x):
    return (1.0 + math.erf(x / 1.4142135623730951)) / 2.0

def black_scholes_price(S, K, T, r, sigma, option_type):
    if T <= 0:
        if option_type == 'call': return max(0.0, S - K)
        else: return max(0.0, K - S)
    if sigma <= 0: sigma = 1e-5
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == 'call': return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else: return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def run_simulation(args):
    # Unpack args
    (strategy_type, call_strike_pct, put_strike_pct, dte, leverage, closes, vols, r) = args
    
    capital = 100000.0
    cash = capital
    active_legs = []
    days_held = 0
    roll_days = max(7, dte - 2)
    
    # Pre-build geometry based on type
    if strategy_type == 'strangle':
        base_legs = [
            {'type': 'call', 'action': 'buy', 'strike_ratio': call_strike_pct, 'qty': leverage},
            {'type': 'put', 'action': 'buy', 'strike_ratio': put_strike_pct, 'qty': leverage}
        ]
    elif strategy_type == 'collar':
        base_legs = [
            {'type': 'future', 'action': 'buy', 'qty': leverage},
            {'type': 'put', 'action': 'buy', 'strike_ratio': put_strike_pct, 'qty': leverage},
            {'type': 'call', 'action': 'sell', 'strike_ratio': call_strike_pct, 'qty': leverage}
        ]
    elif strategy_type == 'synthetic_straddle':
        base_legs = [
            {'type': 'future', 'action': 'buy', 'qty': leverage},
            {'type': 'put', 'action': 'buy', 'strike_ratio': put_strike_pct, 'qty': leverage * 2.0}
        ]
        
    equity_curve = []
    total_len = len(closes)
    
    for i in range(total_len):
        S = closes[i]
        sigma = vols[i]
        
        if not active_legs and i < total_len - 5:
            total_margin = 0
            net_premium = 0
            temp_legs = []
            
            for leg in base_legs:
                qty = leg['qty']
                action = 1 if leg['action'] == 'buy' else -1
                if leg['type'] == 'future':
                    margin = S * 0.10 * qty
                    total_margin += margin
                    temp_legs.append({'type': 'future', 'action': action, 'qty': qty, 'entry': S})
                else:
                    K = S * leg['strike_ratio']
                    T = dte / 365.0
                    price = black_scholes_price(S, K, T, r, sigma, leg['type'])
                    if action == 1:
                        net_premium -= price * qty
                    else:
                        net_premium += price * qty
                        total_margin += S * 0.20 * qty
                    temp_legs.append({'type': leg['type'], 'action': action, 'strike': K, 'entry_price': price, 'qty': qty, 'dte': dte})
            
            if total_margin <= 0: total_margin = 1000
            scale = (cash * 0.90) / total_margin if total_margin > 0 else 1.0
            if scale < 0 or cash <= 0: break
            
            cash += net_premium * scale
            active_legs = temp_legs
            days_held = 0
            current_scale = scale
            
        mtm_cash = cash
        if active_legs:
            days_held += 1
            for leg in active_legs:
                if leg['type'] == 'future':
                    mtm_cash += (S - leg['entry']) * leg['action'] * leg['qty'] * current_scale
                else:
                    T_rem = max(0, leg['dte'] - days_held) / 365.0
                    price = black_scholes_price(S, leg['strike'], T_rem, r, sigma, leg['type'])
                    if leg['action'] == 1: mtm_cash += price * leg['qty'] * current_scale
                    else: mtm_cash -= price * leg['qty'] * current_scale
                    
        equity_curve.append(mtm_cash)
        
        if active_legs and (days_held >= roll_days or i == total_len - 1):
            cash = mtm_cash
            active_legs = []
            days_held = 0
            if cash <= 0:
                cash = 0
                
    eq_s = pd.Series(equity_curve)
    if eq_s.empty or (eq_s <= 0).any():
        return args[:5], -100.0, -100.0, -999.0
        
    ret = (eq_s.iloc[-1] / capital - 1) * 100
    peak = eq_s.cummax()
    dd = ((eq_s - peak) / peak).min() * 100
    
    calmar = abs(ret / dd) if dd < 0 else ret
    
    return args[:5], ret, dd, calmar

if __name__ == '__main__':
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
    
    # Monte Carlo Search Space
    print("Generating 100,000 Monte Carlo Parameter Grids...")
    strategies = ['strangle', 'collar', 'synthetic_straddle']
    dtes = [7, 14, 30, 45, 60, 90, 180]
    leverages = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    
    combinations = []
    # Force 100,000 runs
    for _ in range(100000):
        st = random.choice(strategies)
        c_strike = round(random.uniform(0.70, 1.30), 2)
        p_strike = round(random.uniform(0.70, 1.30), 2)
        dte = random.choice(dtes)
        lev = random.choice(leverages)
        combinations.append((st, c_strike, p_strike, dte, lev, closes, vols, r))
        
    print(f"Executing {len(combinations)} Massive Parallel Backtests on {cpu_count()} CPU cores...")
    start_time = time.time()
    
    results = []
    chunksize = 1000
    with Pool(processes=cpu_count()) as pool:
        for i, res in enumerate(pool.imap_unordered(run_simulation, combinations, chunksize=chunksize)):
            results.append(res)
            if (i + 1) % 5000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                rem_time = (100000 - (i + 1)) / rate
                print(f"[{i+1}/100000] completed. Estimated time remaining: {rem_time/60:.1f} mins...")
        
    # Sort by Calmar Ratio (Return / Max Drawdown)
    valid_results = [res for res in results if res[2] < 0] # Must have some drawdown to be real
    sorted_results = sorted(valid_results, key=lambda x: x[3], reverse=True)
    
    top_5 = sorted_results[:5]
    
    report = "# NIFTY 100,000 Monte Carlo Simulation (Calmar Target)\n\n"
    report += "I executed exactly 100,000 randomized geometry backtests over a 10-year NIFTY 50 historical period (2014-2024).\n"
    report += f"The computation utilized all {cpu_count()} CPU cores to massively parallelize the search.\n\n"
    
    for idx, (params, ret, dd, calmar) in enumerate(top_5):
        st, c_strike, p_strike, dte, lev = params
        report += f"## Top #{idx+1}: {st.upper().replace('_', ' ')}\n"
        report += f"* **Call Strike:** {c_strike*100:.0f}% of Spot\n"
        report += f"* **Put Strike:** {p_strike*100:.0f}% of Spot\n"
        report += f"* **DTE:** {dte} Days\n"
        report += f"* **Leverage (Qty):** {lev}x\n"
        report += f"### Performance\n"
        report += f"* **Total Return:** {ret:.2f}%\n"
        report += f"* **Max Drawdown:** {dd:.2f}%\n"
        report += f"* **Calmar Ratio:** {calmar:.2f}\n\n"
        
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\monte_carlo_nifty_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Finished! Report saved to {report_path}")
