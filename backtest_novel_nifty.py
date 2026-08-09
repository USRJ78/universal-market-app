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

def simulate_geometry_a(df, initial_capital):
    # Volatility Trap: Long 90 DTE Straddle (ATM), Short 3x 7 DTE Strangles (105% / 95%)
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    long_active = False
    long_strike = 0
    long_days = 0
    long_qty = 0
    
    short_active = False
    short_call_strike = 0
    short_put_strike = 0
    short_days = 0
    short_qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        # Check Long Expiry / Roll (Every 85 days)
        if long_active:
            long_days += 1
            if long_days >= 85 or i == len(df) - 1:
                T_rem = max(0, 90 - long_days) / 365.0
                c_val = black_scholes(S, long_strike, T_rem, r, sigma, 'call')
                p_val = black_scholes(S, long_strike, T_rem, r, sigma, 'put')
                cash += (c_val + p_val) * long_qty
                long_active = False
                
        # Check Short Expiry (Every 7 days)
        if short_active:
            short_days += 1
            if short_days >= 7 or i == len(df) - 1:
                T_rem = max(0, 7 - short_days) / 365.0
                c_val = black_scholes(S, short_call_strike, T_rem, r, sigma, 'call')
                p_val = black_scholes(S, short_put_strike, T_rem, r, sigma, 'put')
                cash -= (c_val + p_val) * short_qty
                short_active = False
                
        # Open Long
        if not long_active and i < len(df) - 5:
            long_strike = S
            T_years = 90 / 365.0
            c_cost = black_scholes(S, long_strike, T_years, r, sigma, 'call')
            p_cost = black_scholes(S, long_strike, T_years, r, sigma, 'put')
            cost = c_cost + p_cost
            long_qty = (cash * 0.50) / cost # Use 50% cash to leave room for short margins
            cash -= long_qty * cost
            long_active = True
            long_days = 0
            
        # Open Short
        if not short_active and long_active and i < len(df) - 5:
            short_call_strike = S * 1.05
            short_put_strike = S * 0.95
            T_years = 7 / 365.0
            c_cost = black_scholes(S, short_call_strike, T_years, r, sigma, 'call')
            p_cost = black_scholes(S, short_put_strike, T_years, r, sigma, 'put')
            short_qty = long_qty * 3.0 # 3x ratio
            cash += (c_cost + p_cost) * short_qty
            short_active = True
            short_days = 0
            
        # MTM
        eq = cash
        if long_active:
            T_rem = max(0, 90 - long_days) / 365.0
            eq += (black_scholes(S, long_strike, T_rem, r, sigma, 'call') + black_scholes(S, long_strike, T_rem, r, sigma, 'put')) * long_qty
        if short_active:
            T_rem = max(0, 7 - short_days) / 365.0
            eq -= (black_scholes(S, short_call_strike, T_rem, r, sigma, 'call') + black_scholes(S, short_put_strike, T_rem, r, sigma, 'put')) * short_qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    dd = ((eq_df['Equity'] - peak) / peak).min() * 100
    
    return eq_df, ret, dd

def simulate_geometry_b(df, initial_capital):
    # Asymmetric Jade Lizard: Short OTM Put (90%), Short OTM Call (110%), Long Deep ITM Call (70%) 30 DTE
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    active = False
    s_p_strike, s_c_strike, l_c_strike = 0, 0, 0
    days = 0
    qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        if active:
            days += 1
            if days >= 25 or i == len(df) - 1:
                T = max(0, 30 - days) / 365.0
                s_p_val = black_scholes(S, s_p_strike, T, r, sigma, 'put')
                s_c_val = black_scholes(S, s_c_strike, T, r, sigma, 'call')
                l_c_val = black_scholes(S, l_c_strike, T, r, sigma, 'call')
                cash += (l_c_val - s_p_val - s_c_val) * qty
                active = False
                
        if not active and i < len(df) - 5:
            s_p_strike = S * 0.90
            s_c_strike = S * 1.10
            l_c_strike = S * 0.70
            T = 30 / 365.0
            
            s_p_prem = black_scholes(S, s_p_strike, T, r, sigma, 'put')
            s_c_prem = black_scholes(S, s_c_strike, T, r, sigma, 'call')
            l_c_cost = black_scholes(S, l_c_strike, T, r, sigma, 'call')
            
            net_cost = l_c_cost - s_p_prem - s_c_prem
            qty = (cash * 0.80) / net_cost if net_cost > 0 else (cash * 0.80) / l_c_cost
            cash -= net_cost * qty
            active = True
            days = 0
            
        eq = cash
        if active:
            T = max(0, 30 - days) / 365.0
            eq += (black_scholes(S, l_c_strike, T, r, sigma, 'call') - black_scholes(S, s_p_strike, T, r, sigma, 'put') - black_scholes(S, s_c_strike, T, r, sigma, 'call')) * qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    dd = ((eq_df['Equity'] - peak) / peak).min() * 100
    
    return eq_df, ret, dd

def simulate_geometry_c(df, initial_capital):
    # Fibonacci Iron Butterfly: Short ATM Call/Put, Long Call (127.2%), Long Put (78.6%) 30 DTE
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    active = False
    s_strike, l_c_strike, l_p_strike = 0, 0, 0
    days = 0
    qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        if active:
            days += 1
            if days >= 25 or i == len(df) - 1:
                T = max(0, 30 - days) / 365.0
                s_c_val = black_scholes(S, s_strike, T, r, sigma, 'call')
                s_p_val = black_scholes(S, s_strike, T, r, sigma, 'put')
                l_c_val = black_scholes(S, l_c_strike, T, r, sigma, 'call')
                l_p_val = black_scholes(S, l_p_strike, T, r, sigma, 'put')
                cash += (l_c_val + l_p_val - s_c_val - s_p_val) * qty
                active = False
                
        if not active and i < len(df) - 5:
            s_strike = S
            l_c_strike = S * 1.272
            l_p_strike = S * 0.786
            T = 30 / 365.0
            
            s_c_prem = black_scholes(S, s_strike, T, r, sigma, 'call')
            s_p_prem = black_scholes(S, s_strike, T, r, sigma, 'put')
            l_c_cost = black_scholes(S, l_c_strike, T, r, sigma, 'call')
            l_p_cost = black_scholes(S, l_p_strike, T, r, sigma, 'put')
            
            # This is a credit spread (Butterfly usually collects credit if wings are wide)
            net_credit = s_c_prem + s_p_prem - l_c_cost - l_p_cost
            
            # Margin required is approx width of the spread
            margin_req = (s_strike - l_p_strike)
            qty = (cash * 0.90) / margin_req if margin_req > 0 else 1.0
            
            cash += net_credit * qty
            active = True
            days = 0
            
        eq = cash
        if active:
            T = max(0, 30 - days) / 365.0
            eq += (black_scholes(S, l_c_strike, T, r, sigma, 'call') + black_scholes(S, l_p_strike, T, r, sigma, 'put') - black_scholes(S, s_strike, T, r, sigma, 'call') - black_scholes(S, s_strike, T, r, sigma, 'put')) * qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    ret = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    dd = ((eq_df['Equity'] - peak) / peak).min() * 100
    
    return eq_df, ret, dd

def simulate_geometry_d(df, initial_capital):
    # Capped Volatility Trap: Long 90 DTE Straddle (ATM), Short 3x 7 DTE Strangles (105% / 95%), Long 3x 7 DTE Far Wings (110% / 90%)
    cash = initial_capital
    r = 0.05
    equity_curve = []
    
    long_active = False
    long_strike = 0
    long_days = 0
    long_qty = 0
    
    short_active = False
    s_c_strike = 0
    s_p_strike = 0
    l_c_wing = 0
    l_p_wing = 0
    short_days = 0
    short_qty = 0
    
    for i in range(len(df)):
        date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        # Check Long Expiry / Roll
        if long_active:
            long_days += 1
            if long_days >= 85 or i == len(df) - 1:
                T_rem = max(0, 90 - long_days) / 365.0
                c_val = black_scholes(S, long_strike, T_rem, r, sigma, 'call')
                p_val = black_scholes(S, long_strike, T_rem, r, sigma, 'put')
                cash += (c_val + p_val) * long_qty
                long_active = False
                
        # Check Short Expiry
        if short_active:
            short_days += 1
            if short_days >= 7 or i == len(df) - 1:
                T_rem = max(0, 7 - short_days) / 365.0
                s_c_val = black_scholes(S, s_c_strike, T_rem, r, sigma, 'call')
                s_p_val = black_scholes(S, s_p_strike, T_rem, r, sigma, 'put')
                l_c_val = black_scholes(S, l_c_wing, T_rem, r, sigma, 'call')
                l_p_val = black_scholes(S, l_p_wing, T_rem, r, sigma, 'put')
                # Settle shorts (buy back) and long wings (sell)
                cash += (l_c_val + l_p_val - s_c_val - s_p_val) * short_qty
                short_active = False
                
        # Open Long
        if not long_active and i < len(df) - 5:
            long_strike = S
            T_years = 90 / 365.0
            c_cost = black_scholes(S, long_strike, T_years, r, sigma, 'call')
            p_cost = black_scholes(S, long_strike, T_years, r, sigma, 'put')
            cost = c_cost + p_cost
            long_qty = (cash * 0.90) / cost # With capped risk, we can deploy 90% of capital safely
            cash -= long_qty * cost
            long_active = True
            long_days = 0
            
        # Open Short & Wings (The Capped Condor)
        if not short_active and long_active and i < len(df) - 5:
            s_c_strike = S * 1.05
            s_p_strike = S * 0.95
            l_c_wing = S * 1.10
            l_p_wing = S * 0.90
            T_years = 7 / 365.0
            
            s_c_cost = black_scholes(S, s_c_strike, T_years, r, sigma, 'call')
            s_p_cost = black_scholes(S, s_p_strike, T_years, r, sigma, 'put')
            l_c_cost = black_scholes(S, l_c_wing, T_years, r, sigma, 'call')
            l_p_cost = black_scholes(S, l_p_wing, T_years, r, sigma, 'put')
            
            short_qty = long_qty * 3.0 # 3x ratio
            
            # Net credit from opening the condor
            net_credit = (s_c_cost + s_p_cost) - (l_c_cost + l_p_cost)
            cash += net_credit * short_qty
            
            short_active = True
            short_days = 0
            
        # MTM
        eq = cash
        if long_active:
            T_rem = max(0, 90 - long_days) / 365.0
            eq += (black_scholes(S, long_strike, T_rem, r, sigma, 'call') + black_scholes(S, long_strike, T_rem, r, sigma, 'put')) * long_qty
        if short_active:
            T_rem = max(0, 7 - short_days) / 365.0
            s_c_val = black_scholes(S, s_c_strike, T_rem, r, sigma, 'call')
            s_p_val = black_scholes(S, s_p_strike, T_rem, r, sigma, 'put')
            l_c_val = black_scholes(S, l_c_wing, T_rem, r, sigma, 'call')
            l_p_val = black_scholes(S, l_p_wing, T_rem, r, sigma, 'put')
            eq += (l_c_val + l_p_val - s_c_val - s_p_val) * short_qty
            
        equity_curve.append({'Date': date, 'Equity': eq})
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    
    # Check if we ever hit negative equity (blowout)
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

if __name__ == "__main__":
    start_date = "2015-01-01"
    end_date = "2025-01-01"
    
    df = fetch_data("^NSEI", start_date, end_date)
    
    eq_a, ret_a, dd_a = simulate_geometry_a(df, 1000000)
    eq_d, ret_d, dd_d = simulate_geometry_d(df, 1000000)
    
    report = f"""# Autonomous Research: Fixing the Volatility Trap
    
**Asset:** NIFTY 50 (^NSEI)
**Timeframe:** 10 Years ({start_date} to {end_date})

## Geometry A: The Original Volatility Trap (Uncapped)
* **Structure:** Long 90-DTE ATM Straddle, Short 3x 7-DTE OTM Strangles (105%/95%)
* **Total Return:** {ret_a:.2f}%
* **Max Drawdown:** {dd_a:.2f}%

## Geometry D: The Capped Volatility Trap
* **Structure:** Long 90-DTE ATM Straddle, Short 3x 7-DTE OTM Strangles (105%/95%), Long 3x 7-DTE Far Wings (110%/90%)
* **Total Return:** {ret_d:.2f}%
* **Max Drawdown:** {dd_d:.2f}%
"""
    print(report)
    
    plt.figure(figsize=(12, 6))
    # We clip equity a so it doesn't distort the graph if it goes negative massively
    clipped_eq_a = eq_a['Equity'].clip(lower=0)
    plt.plot(eq_a.index, clipped_eq_a / eq_a['Equity'].iloc[0], label='Original Volatility Trap (Uncapped)', alpha=0.5)
    plt.plot(eq_d.index, eq_d['Equity'] / eq_d['Equity'].iloc[0], label='Capped Volatility Trap', linewidth=2)
    plt.title("Fixing the Volatility Trap (NIFTY - 10 Yrs)")
    plt.ylabel("Growth Multiple")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\capped_volatility_trap.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\capped_volatility_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")
