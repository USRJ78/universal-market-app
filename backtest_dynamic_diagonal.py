import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt
import os
from datetime import timedelta

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """Calculate Black-Scholes option price."""
    # Handle edge cases
    if T <= 0:
        if option_type == 'call':
            return max(0.0, S - K)
        else:
            return max(0.0, K - S)
    if sigma <= 0:
        sigma = 1e-5
        
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return price

def fetch_data(ticker, start, end):
    print(f"Fetching {ticker}...")
    df = yf.download(ticker, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    
    # Calculate 30-day historical volatility
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * np.sqrt(365)  # Annualized
    df.dropna(inplace=True)
    return df

def run_simulation(df, initial_capital, asset_name):
    print(f"Running simulation for {asset_name}...")
    
    cash = initial_capital
    r = 0.05  # 5% risk-free rate
    
    # Trackers
    equity_curve = []
    
    # Core Position State
    core_active = False
    core_call_strike = 0
    core_put_strike = 0
    core_entry_spot = 0
    core_days_held = 0
    core_qty = 0
    
    # Short Theta Position State
    short_active = False
    short_call_strike = 0
    short_put_strike = 0
    short_days_held = 0
    short_qty = 0
    
    for i in range(len(df)):
        current_date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        # 1. Evaluate rolling conditions
        roll_core = False
        if core_active:
            core_days_held += 1
            short_days_held += 1
            
            # Check 15% spot movement threshold
            if abs(S - core_entry_spot) / core_entry_spot >= 0.15:
                roll_core = True
            
            # Roll if core is getting too close to expiry (e.g. 14 days left from 90)
            if core_days_held >= 76:
                roll_core = True
                
        # 2. Close positions if rolling or short legs expired
        if core_active and (roll_core or i == len(df)-1):
            # Close Core
            T_core = (90 - core_days_held) / 365.0
            call_val = black_scholes(S, core_call_strike, T_core, r, sigma, 'call')
            put_val = black_scholes(S, core_put_strike, T_core, r, sigma, 'put')
            
            cash += (call_val + put_val) * core_qty
            core_active = False
            
            # Close Shorts if any
            if short_active:
                T_short = max(0, 7 - short_days_held) / 365.0
                short_call_val = black_scholes(S, short_call_strike, T_short, r, sigma, 'call')
                short_put_val = black_scholes(S, short_put_strike, T_short, r, sigma, 'put')
                cash -= (short_call_val + short_put_val) * short_qty
                short_active = False
                
        elif short_active and short_days_held >= 7:
            # Short legs expired, buy them back (or they expire worthless)
            T_short = 0
            short_call_val = max(0, S - short_call_strike)
            short_put_val = max(0, short_put_strike - S)
            cash -= (short_call_val + short_put_val) * short_qty
            short_active = False
            
        # 3. Open new positions if not active
        if not core_active and i < len(df)-5:
            # Define new core strikes
            core_call_strike = S * 0.60
            core_put_strike = S * 1.40
            core_entry_spot = S
            
            # Price them at 90 DTE
            T_core = 90 / 365.0
            call_cost = black_scholes(S, core_call_strike, T_core, r, sigma, 'call')
            put_cost = black_scholes(S, core_put_strike, T_core, r, sigma, 'put')
            
            # Use 95% of available cash to buy the core strangle
            allocation = cash * 0.95
            cost_per_unit = call_cost + put_cost
            
            core_qty = allocation / cost_per_unit
            cash -= core_qty * cost_per_unit
            core_active = True
            core_days_held = 0
            
        if core_active and not short_active and i < len(df)-5:
            # Sell new 7 DTE short legs against the core
            short_call_strike = S * 1.10
            short_put_strike = S * 0.90
            
            T_short = 7 / 365.0
            call_premium = black_scholes(S, short_call_strike, T_short, r, sigma, 'call')
            put_premium = black_scholes(S, short_put_strike, T_short, r, sigma, 'put')
            
            # Match quantity to the core (diagonalize)
            short_qty = core_qty
            cash += (call_premium + put_premium) * short_qty
            short_active = True
            short_days_held = 0
            
        # 4. Record Daily Mark-to-Market Equity
        mtm_equity = cash
        if core_active:
            T_core = max(0, 90 - core_days_held) / 365.0
            mtm_equity += black_scholes(S, core_call_strike, T_core, r, sigma, 'call') * core_qty
            mtm_equity += black_scholes(S, core_put_strike, T_core, r, sigma, 'put') * core_qty
        if short_active:
            T_short = max(0, 7 - short_days_held) / 365.0
            mtm_equity -= black_scholes(S, short_call_strike, T_short, r, sigma, 'call') * short_qty
            mtm_equity -= black_scholes(S, short_put_strike, T_short, r, sigma, 'put') * short_qty
            
        equity_curve.append({
            'Date': current_date,
            'Equity': mtm_equity
        })
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    
    # Calculate metrics
    total_return = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    drawdown = (eq_df['Equity'] - peak) / peak * 100
    max_dd = drawdown.min()
    
    return eq_df, total_return, max_dd

if __name__ == "__main__":
    start_date = "2020-01-01"
    end_date = "2025-01-01"
    
    # BTC
    btc_df = fetch_data("BTC-USD", start_date, end_date)
    btc_eq, btc_ret, btc_dd = run_simulation(btc_df, 100000, "BTC")
    
    # NIFTY
    nifty_df = fetch_data("^NSEI", start_date, end_date)
    nifty_eq, nifty_ret, nifty_dd = run_simulation(nifty_df, 1000000, "NIFTY")
    
    # Print Report
    report = f"""# Dynamic Diagonal Strangle Backtest Results
    
**Period:** {start_date} to {end_date}

## BTC-USD
* **Initial Capital:** $100,000
* **Total Return:** {btc_ret:.2f}%
* **Max Drawdown:** {btc_dd:.2f}%

## NIFTY 50 (^NSEI)
* **Initial Capital:** INR 1,000,000
* **Total Return:** {nifty_ret:.2f}%
* **Max Drawdown:** {nifty_dd:.2f}%
"""
    print(report)
    
    # Save chart
    plt.figure(figsize=(12, 6))
    plt.plot(btc_eq.index, btc_eq['Equity'] / btc_eq['Equity'].iloc[0], label='BTC Equity (Normalized)')
    plt.plot(nifty_eq.index, nifty_eq['Equity'] / nifty_eq['Equity'].iloc[0], label='NIFTY Equity (Normalized)')
    plt.title("Dynamic Diagonal Strangle Performance")
    plt.ylabel("Growth Multiple")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\dynamic_diagonal_chart.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\dynamic_diagonal_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")
