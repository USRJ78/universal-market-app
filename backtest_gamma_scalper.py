import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt

def black_scholes_price_and_delta(S, K, T, r, sigma, option_type='call'):
    if T <= 0:
        if option_type == 'call':
            return max(0.0, S - K), (1.0 if S > K else 0.0)
        else:
            return max(0.0, K - S), (-1.0 if S < K else 0.0)
    if sigma <= 0:
        sigma = 1e-5
        
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1.0
        
    return price, delta

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

def run_scalping_simulation(df, initial_capital, asset_name, strike_width, leverage):
    print(f"Running Gamma Scalping simulation for {asset_name}...")
    
    cash = initial_capital
    r = 0.05
    DTE = 90
    roll_threshold = 0.15
    hedge_threshold = 0.10
    
    equity_curve = []
    
    core_active = False
    core_call_strike = 0
    core_put_strike = 0
    core_entry_spot = 0
    core_days_held = 0
    core_qty = 0
    
    spot_hedge_qty = 0.0
    total_trades = 0
    
    for i in range(len(df)):
        current_date = df.index[i]
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        
        roll_core = False
        if core_active:
            core_days_held += 1
            if abs(S - core_entry_spot) / core_entry_spot >= roll_threshold or core_days_held >= DTE - 5:
                roll_core = True
                
        if core_active and (roll_core or i == len(df)-1):
            T_core = max(0, DTE - core_days_held) / 365.0
            call_val, _ = black_scholes_price_and_delta(S, core_call_strike, T_core, r, sigma, 'call')
            put_val, _ = black_scholes_price_and_delta(S, core_put_strike, T_core, r, sigma, 'put')
            
            # Liquidate options
            cash += (call_val + put_val) * core_qty
            # Liquidate spot hedges
            cash += spot_hedge_qty * S
            
            core_active = False
            spot_hedge_qty = 0.0
            
        if not core_active and i < len(df)-5:
            core_call_strike = S * (1.0 - strike_width)
            core_put_strike = S * (1.0 + strike_width)
            core_entry_spot = S
            
            T_core = DTE / 365.0
            call_cost, c_delta = black_scholes_price_and_delta(S, core_call_strike, T_core, r, sigma, 'call')
            put_cost, p_delta = black_scholes_price_and_delta(S, core_put_strike, T_core, r, sigma, 'put')
            
            cost_per_unit = call_cost + put_cost
            
            core_qty = (cash * leverage) / cost_per_unit
            cash -= core_qty * cost_per_unit
            
            core_active = True
            core_days_held = 0
            
            # Initial hedge
            net_delta = core_qty * (c_delta + p_delta)
            if abs(net_delta) > hedge_threshold:
                spot_hedge_qty = -net_delta
                cash -= spot_hedge_qty * S
                total_trades += 1
                
        # Daily Gamma Scalping
        mtm_equity = cash
        if core_active:
            T_core = max(0, DTE - core_days_held) / 365.0
            call_val, c_delta = black_scholes_price_and_delta(S, core_call_strike, T_core, r, sigma, 'call')
            put_val, p_delta = black_scholes_price_and_delta(S, core_put_strike, T_core, r, sigma, 'put')
            
            mtm_equity += (call_val + put_val) * core_qty
            mtm_equity += spot_hedge_qty * S
            
            # Check if we need to hedge
            portfolio_delta = (core_qty * (c_delta + p_delta)) + spot_hedge_qty
            
            if abs(portfolio_delta) >= hedge_threshold:
                # Scalp! Adjust spot hedge to bring portfolio delta back to exactly 0
                adjustment_qty = -portfolio_delta
                spot_hedge_qty += adjustment_qty
                cash -= adjustment_qty * S
                total_trades += 1
                
        equity_curve.append({
            'Date': current_date,
            'Equity': mtm_equity
        })
        
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    total_return = (eq_df['Equity'].iloc[-1] / initial_capital - 1) * 100
    peak = eq_df['Equity'].cummax()
    drawdown = (eq_df['Equity'] - peak) / peak * 100
    max_dd = drawdown.min()
    
    return eq_df, total_return, max_dd, total_trades

if __name__ == "__main__":
    start_date = "2015-01-01"
    end_date = "2025-01-01"
    
    # BTC (Wide Strikes, No Leverage)
    btc_df = fetch_data("BTC-USD", start_date, end_date)
    btc_eq, btc_ret, btc_dd, btc_trades = run_scalping_simulation(btc_df, 100000, "BTC", strike_width=0.40, leverage=1.0)
    
    # NIFTY (Tight Strikes, 3x Leverage)
    nifty_df = fetch_data("^NSEI", start_date, end_date)
    nifty_eq, nifty_ret, nifty_dd, nifty_trades = run_scalping_simulation(nifty_df, 1000000, "NIFTY", strike_width=0.20, leverage=3.0)
    
    report = f"""# Gamma Scalping Backtest Results (10-Year)
    
**Period:** {start_date} to {end_date}

## BTC-USD (Geometry: 40% Width, 1.0x Leverage)
* **Initial Capital:** $100,000
* **Total Trades Taken (Scalps):** {btc_trades}
* **Total Return:** {btc_ret:.2f}%
* **Max Drawdown:** {btc_dd:.2f}%

## NIFTY 50 (Geometry: 20% Width, 3.0x Leverage)
* **Initial Capital:** INR 1,000,000
* **Total Trades Taken (Scalps):** {nifty_trades}
* **Total Return:** {nifty_ret:.2f}%
* **Max Drawdown:** {nifty_dd:.2f}%
"""
    print(report)
    
    plt.figure(figsize=(12, 6))
    plt.plot(btc_eq.index, btc_eq['Equity'] / btc_eq['Equity'].iloc[0], label='BTC Equity (Gamma Scalped)')
    plt.plot(nifty_eq.index, nifty_eq['Equity'] / nifty_eq['Equity'].iloc[0], label='NIFTY Equity (Gamma Scalped)')
    plt.title("Gamma Scalped Deep ITM Strangle (10 Years)")
    plt.ylabel("Growth Multiple")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\gamma_scalper_chart.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\gamma_scalper_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")
