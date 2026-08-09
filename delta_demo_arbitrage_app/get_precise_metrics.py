import numpy as np
import pandas as pd
import os
from scipy.stats import norm

scratch_dir = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\scratch"
nifty_path = os.path.join(scratch_dir, "nifty_cache.csv")
btc_path = os.path.join(scratch_dir, "cache_btc.csv")
gold_path = os.path.join(scratch_dir, "cache_gold.csv")

def rolling_vol(prices, w=21):
    lr = np.log(np.maximum(prices[1:], 1e-9) / np.maximum(prices[:-1], 1e-9))
    rv = np.full(len(prices), 0.20)
    for i in range(w, len(lr)):
        rv[i+1] = np.std(lr[i-w:i]) * np.sqrt(252)
    return np.clip(rv, 0.05, 2.0)

R = 0.07
SLP = 0.004

def bs_batch(S, K_pct, T, vol, opt_type):
    K   = S * K_pct
    T   = np.maximum(T, 1e-5)
    vol = np.maximum(vol, 0.08)
    d1  = (np.log(S / K) + (R + 0.5 * vol**2) * T) / (vol * np.sqrt(T))
    d2  = d1 - vol * np.sqrt(T)
    if opt_type == 'c':
        return np.maximum(S * norm.cdf(d1) - K * np.exp(-R * T) * norm.cdf(d2), 0)
    else:
        return np.maximum(K * np.exp(-R * T) * norm.cdf(-d2) - S * norm.cdf(-d1), 0)

def simulate_strategy(strategy, prices, vols, hold):
    idx = np.arange(0, len(prices) - hold - 1, hold)
    N = len(idx)
    if N == 0: return 0.0, 1.0, 0.0
    
    S0  = prices[idx]
    S1  = prices[idx + hold]
    vol = np.maximum(vols[idx], 0.10)
    
    net_pnl = np.zeros(N)
    net_cost = np.zeros(N)
    
    for (ot, k_pct, ratio, dte) in strategy:
        T0 = dte / 365.0
        T1 = max((dte - hold) / 365.0, 0.0)
        
        ep = bs_batch(S0, k_pct, np.full(N, T0), vol, ot)
        if T1 > 0:
            xp = bs_batch(S1, k_pct, np.full(N, T1), vol, ot)
        else:
            K = S0 * k_pct
            xp = np.maximum(S1 - K, 0) if ot == 'c' else np.maximum(K - S1, 0)
            
        ep_adj = ep * (1 + SLP) if ratio > 0 else ep * (1 - SLP)
        xp_adj = xp * (1 - SLP) if ratio > 0 else xp * (1 + SLP)
        
        leg_pnl = (xp_adj - ep_adj) * ratio
        if ratio < 0:
            max_loss = np.abs(ep_adj) * abs(ratio) * 5.0
            leg_pnl = np.maximum(leg_pnl, -max_loss)
            
        net_pnl += leg_pnl
        net_cost += np.abs(ep_adj) * abs(ratio)
        
    cost_basis = np.maximum(net_cost, 0.01)
    pnl_frac = (net_pnl / cost_basis) * 0.10
    pnl_frac = np.clip(pnl_frac, -0.15, 0.50)
    
    linear_equity = 100000.0 + np.cumsum(pnl_frac * 100000.0)
    total_r = (linear_equity[-1] - 100000.0) / 100000.0
    
    peak = np.maximum.accumulate(linear_equity)
    dd = (peak - linear_equity) / peak
    max_dd = dd.max()
    
    ann_factor = np.sqrt(252.0 / hold)
    sharpe = (np.mean(pnl_frac) / (np.std(pnl_frac) + 1e-9)) * ann_factor
    
    return total_r * 100, max_dd * 100, sharpe

strategies = {
    "Golden Straddle PHI x 1.5": ([('c',1.00,2,14),('p',1.00,2,14),('c',1.24,-1,30),('p',0.76,-1,30)], 14),
    "Julia Set 6.18% Escape": ([('c',1.03,2,14),('p',0.98,2,14),('c',1.06,-1,30),('p',0.94,-1,30)], 14),
    "Time Warp 7d/21d ATM": ([('c',1.00,1,7),('p',1.00,1,7),('c',1.01,-1,21),('p',0.99,-1,21)], 7)
}

paths = {"NIFTY": nifty_path, "BTC": btc_path, "GOLD": gold_path}

for asset, path in paths.items():
    print(f"\n--- {asset} ---")
    df = pd.read_csv(path, header=None, skiprows=3, names=['Date', 'Close'], parse_dates=['Date'], index_col='Date')
    px = df['Close'].dropna().values.astype(np.float64)
    vols = rolling_vol(px)
    for name, (strat, hold) in strategies.items():
        ret, dd, sh = simulate_strategy(strat, px, vols, hold)
        print(f"  {name}: Return={ret:.1f}%, MaxDD={dd:.1f}%, Sharpe={sh:.2f}")
