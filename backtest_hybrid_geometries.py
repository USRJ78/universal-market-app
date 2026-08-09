import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt

def black_scholes(S, K, T, r, sigma, option_type='call'):
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
    
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * np.sqrt(365)
    df.dropna(inplace=True)
    return df

def simulate_hybrid_a_collar(df, initial_capital):
    # Long Future + Long 95% Put + Short 105% Call (90 DTE)
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    active = False
    entry_spot = 0
    put_strike = 0
    call_strike = 0
    days = 0
    qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        if active:
            days += 1
            if days >= 85 or i == len(df) - 1:
                T_rem = max(0, 90 - days) / 365.0
                
                # Close Future
                future_pnl = (S - entry_spot) * qty
                cash += future_pnl
                
                # Close Options
                p_val = black_scholes(S, put_strike, T_rem, r, sigma, 'put')
                c_val = black_scholes(S, call_strike, T_rem, r, sigma, 'call')
                cash += (p_val - c_val) * qty
                active = False
                
        if not active and i < len(df) - 5:
            entry_spot = S
            put_strike = S * 0.95
            call_strike = S * 1.05
            T_years = 90 / 365.0
            
            p_cost = black_scholes(S, put_strike, T_years, r, sigma, 'put')
            c_cost = black_scholes(S, call_strike, T_years, r, sigma, 'call')
            
            # Future margin = 10% of Spot. Options cost = net premium.
            net_premium = p_cost - c_cost
            margin_req = (S * 0.10) + max(0, net_premium)
            
            qty = (cash * 0.90) / margin_req if margin_req > 0 else 1.0
            cash -= net_premium * qty
            active = True
            days = 0
            
        eq = cash
        if active:
            T_rem = max(0, 90 - days) / 365.0
            future_pnl = (S - entry_spot) * qty
            p_val = black_scholes(S, put_strike, T_rem, r, sigma, 'put')
            c_val = black_scholes(S, call_strike, T_rem, r, sigma, 'call')
            eq += future_pnl + (p_val - c_val) * qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    
    # Handle blowout
    if (eq_df['Equity'] <= 0).any():
        first_blowout = eq_df[eq_df['Equity'] <= 0].index[0]
        eq_df.loc[first_blowout:, 'Equity'] = 0.0
        ret = -100.0
        dd = -100.0
    else:
        ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
        peak = eq_df['Equity'].cummax()
        dd = ((eq_df['Equity'] - peak) / peak).min() * 100
        
    return eq_df, ret, dd

def simulate_hybrid_b_synthetic_straddle(df, initial_capital):
    # Long Future + Long 2x ATM Puts (90 DTE)
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    active = False
    entry_spot = 0
    put_strike = 0
    days = 0
    qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        if active:
            days += 1
            if days >= 85 or i == len(df) - 1:
                T_rem = max(0, 90 - days) / 365.0
                
                # Close Future
                future_pnl = (S - entry_spot) * qty
                cash += future_pnl
                
                # Close Puts
                p_val = black_scholes(S, put_strike, T_rem, r, sigma, 'put')
                cash += (p_val * 2.0) * qty
                active = False
                
        if not active and i < len(df) - 5:
            entry_spot = S
            put_strike = S
            T_years = 90 / 365.0
            
            p_cost = black_scholes(S, put_strike, T_years, r, sigma, 'put')
            
            # Future margin = 10% of Spot. Puts cost = 2x p_cost.
            margin_req = (S * 0.10) + (p_cost * 2.0)
            
            qty = (cash * 0.90) / margin_req if margin_req > 0 else 1.0
            cash -= (p_cost * 2.0) * qty
            active = True
            days = 0
            
        eq = cash
        if active:
            T_rem = max(0, 90 - days) / 365.0
            future_pnl = (S - entry_spot) * qty
            p_val = black_scholes(S, put_strike, T_rem, r, sigma, 'put')
            eq += future_pnl + (p_val * 2.0) * qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    
    if (eq_df['Equity'] <= 0).any():
        first_blowout = eq_df[eq_df['Equity'] <= 0].index[0]
        eq_df.loc[first_blowout:, 'Equity'] = 0.0
        ret = -100.0
        dd = -100.0
    else:
        ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
        peak = eq_df['Equity'].cummax()
        dd = ((eq_df['Equity'] - peak) / peak).min() * 100
        
    return eq_df, ret, dd

def simulate_hybrid_c_cash_carry(df, initial_capital):
    # Cash and Carry Arbitrage: Long Spot + Short Future (Simulated 8% Annualized Contango)
    # Roll every 90 days
    cash = initial_capital
    annual_yield = 0.08
    equity_curve = []
    
    for i in range(len(df)):
        date = df.index[i]
        
        # We accrue a completely risk-free yield daily on our deployed capital
        # We assume we can deploy 90% of our capital into this arb safely.
        daily_yield = (annual_yield / 365.0)
        
        if i > 0:
            yield_earned = (cash * 0.90) * daily_yield
            cash += yield_earned
            
        equity_curve.append({'Date': date, 'Equity': cash})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    
    ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    dd = ((eq_df['Equity'] - peak) / peak).min() * 100
    
    return eq_df, ret, dd

if __name__ == "__main__":
    start_date = "2015-01-01"
    end_date = "2025-01-01"
    
    df_btc = fetch_data("BTC-USD", start_date, end_date)
    df_nifty = fetch_data("^NSEI", start_date, end_date)
    
    # Run for BTC
    eq_a_btc, ret_a_btc, dd_a_btc = simulate_hybrid_a_collar(df_btc, 100000)
    eq_b_btc, ret_b_btc, dd_b_btc = simulate_hybrid_b_synthetic_straddle(df_btc, 100000)
    eq_c_btc, ret_c_btc, dd_c_btc = simulate_hybrid_c_cash_carry(df_btc, 100000)
    
    report = f"""# Autonomous Research: Futures & Options Hybrids
    
**Timeframe:** 10 Years ({start_date} to {end_date})

## BTC-USD Results
**Hybrid A: Zero-Cost Collar (Long Future + Long 95% Put + Short 105% Call)**
* **Total Return:** {ret_a_btc:.2f}%
* **Max Drawdown:** {dd_a_btc:.2f}%

**Hybrid B: Synthetic Straddle (Long Future + Long 2x ATM Puts)**
* **Total Return:** {ret_b_btc:.2f}%
* **Max Drawdown:** {dd_b_btc:.2f}%

**Hybrid C: Cash-and-Carry Arbitrage (Long Spot + Short Future @ 8% Contango)**
* **Total Return:** {ret_c_btc:.2f}%
* **Max Drawdown:** {dd_c_btc:.2f}%
"""
    print(report)
    
    plt.figure(figsize=(12, 6))
    
    # Clip to prevent massive negative distortion
    clipped_eq_a = eq_a_btc['Equity'].clip(lower=0)
    clipped_eq_b = eq_b_btc['Equity'].clip(lower=0)
    
    plt.plot(eq_a_btc.index, clipped_eq_a / eq_a_btc['Equity'].iloc[0], label='Hybrid A: Collar')
    plt.plot(eq_b_btc.index, clipped_eq_b / eq_b_btc['Equity'].iloc[0], label='Hybrid B: Synthetic Straddle')
    plt.plot(eq_c_btc.index, eq_c_btc['Equity'] / eq_c_btc['Equity'].iloc[0], label='Hybrid C: Cash & Carry')
    plt.title("Hybrid Futures & Options Geometries (BTC - 10 Yrs)")
    plt.ylabel("Growth Multiple")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\hybrid_backtest_chart.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\hybrid_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")
