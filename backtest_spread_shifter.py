import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

def bs_price(S, K, T, r, sigma, option_type='call'):
    if T <= 0:
        if option_type == 'call': return max(0.0, S - K)
        else: return max(0.0, K - S)
    if sigma <= 0: sigma = 1e-5
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def bs_delta(S, K, T, r, sigma, option_type='call'):
    if T <= 0:
        if option_type == 'call': return 1.0 if S > K else 0.0
        else: return -1.0 if S < K else 0.0
    if sigma <= 0: sigma = 1e-5
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1.0

def fetch_data(ticker, start, end):
    print(f"Fetching {ticker}...")
    df = yf.download(ticker, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * np.sqrt(365)
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df.dropna(inplace=True)
    return df

class SpreadShifter:
    def __init__(self, df, initial_capital=100000):
        self.df = df
        self.initial_capital = initial_capital
        self.r = 0.05
        
    def _open_spread(self, S, sigma, direction, cash):
        # Direction: 1 for Call Spread, -1 for Put Spread
        # 30 DTE, 5% OTM short leg
        T = 30 / 365.0
        if direction == 1:
            long_k = S
            short_k = S * 1.05
            cost_long = bs_price(S, long_k, T, self.r, sigma, 'call')
            prem_short = bs_price(S, short_k, T, self.r, sigma, 'call')
            net_cost = cost_long - prem_short
        else:
            long_k = S
            short_k = S * 0.95
            cost_long = bs_price(S, long_k, T, self.r, sigma, 'put')
            prem_short = bs_price(S, short_k, T, self.r, sigma, 'put')
            net_cost = cost_long - prem_short
            
        # Allocate 50% of capital to the spread to avoid total ruin
        allocation = cash * 0.50
        qty = allocation / net_cost if net_cost > 0 else 0
        
        return {
            'dir': direction,
            'long_k': long_k,
            'short_k': short_k,
            'qty': qty,
            'entry_cost': net_cost,
            'days_held': 0
        }
        
    def _price_spread(self, pos, S, sigma):
        T = max(0, 30 - pos['days_held']) / 365.0
        if pos['dir'] == 1:
            long_val = bs_price(S, pos['long_k'], T, self.r, sigma, 'call')
            short_val = bs_price(S, pos['short_k'], T, self.r, sigma, 'call')
        else:
            long_val = bs_price(S, pos['long_k'], T, self.r, sigma, 'put')
            short_val = bs_price(S, pos['short_k'], T, self.r, sigma, 'put')
        return long_val - short_val

    def _delta_spread(self, pos, S, sigma):
        T = max(0, 30 - pos['days_held']) / 365.0
        if pos['dir'] == 1:
            long_d = bs_delta(S, pos['long_k'], T, self.r, sigma, 'call')
            short_d = bs_delta(S, pos['short_k'], T, self.r, sigma, 'call')
        else:
            long_d = bs_delta(S, pos['long_k'], T, self.r, sigma, 'put')
            short_d = bs_delta(S, pos['short_k'], T, self.r, sigma, 'put')
        return long_d - short_d

    def simulate(self, strategy_type):
        cash = self.initial_capital
        pos = None
        equity_curve = []
        
        # Start with Call Spread
        start_S = self.df['Close'].iloc[0]
        start_sig = self.df['Vol30'].iloc[0]
        pos = self._open_spread(start_S, start_sig, 1, cash)
        cash -= pos['entry_cost'] * pos['qty']
        
        for i in range(len(self.df)):
            date = self.df.index[i]
            S = float(self.df['Close'].iloc[i])
            sigma = float(self.df['Vol30'].iloc[i])
            sma5 = float(self.df['SMA5'].iloc[i])
            sma20 = float(self.df['SMA20'].iloc[i])
            
            pos['days_held'] += 1
            current_val = self._price_spread(pos, S, sigma)
            
            flip_signal = False
            
            # Condition Evaluation
            if pos['days_held'] >= 29:
                # Expiry reached, must roll
                flip_signal = True # Actually just close and reopen based on trend
            else:
                if strategy_type == 'premium':
                    # Stop loss: if spread drops 25% in value
                    if current_val < pos['entry_cost'] * 0.75:
                        flip_signal = True
                elif strategy_type == 'indicator':
                    # Flip if MA crosses against position
                    if pos['dir'] == 1 and sma5 < sma20:
                        flip_signal = True
                    elif pos['dir'] == -1 and sma5 > sma20:
                        flip_signal = True
                elif strategy_type == 'delta':
                    # Flip if Delta degrades significantly
                    net_d = self._delta_spread(pos, S, sigma)
                    if pos['dir'] == 1 and net_d < 0.15:
                        flip_signal = True
                    elif pos['dir'] == -1 and net_d > -0.15:
                        flip_signal = True
                        
            # Execute Flip
            if flip_signal:
                # Liquidate
                cash += current_val * pos['qty']
                
                # Determine new direction
                new_dir = -pos['dir']
                if pos['days_held'] >= 29 and strategy_type == 'indicator':
                    # If it just expired, follow the MA trend
                    new_dir = 1 if sma5 > sma20 else -1
                    
                # Re-deploy
                pos = self._open_spread(S, sigma, new_dir, cash)
                cash -= pos['entry_cost'] * pos['qty']
                current_val = self._price_spread(pos, S, sigma) # update for MTM
                
            # MTM tracking
            mtm_equity = cash + (current_val * pos['qty'])
            equity_curve.append({'Date': date, 'Equity': mtm_equity})
            
        eq_df = pd.DataFrame(equity_curve).set_index('Date')
        return eq_df

if __name__ == "__main__":
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    
    btc_df = fetch_data("BTC-USD", start_date, end_date)
    
    engine = SpreadShifter(btc_df, initial_capital=100000)
    
    print("Running Option A (Premium Stop-Loss)...")
    eq_premium = engine.simulate('premium')
    print("Running Option B (MA Crossover)...")
    eq_indicator = engine.simulate('indicator')
    print("Running Option C (Delta Threshold)...")
    eq_delta = engine.simulate('delta')
    
    # Calc stats
    def calc_stats(df):
        ret = (df['Equity'].iloc[-1] / 100000 - 1) * 100
        peak = df['Equity'].cummax()
        dd = (df['Equity'] - peak) / peak * 100
        return ret, dd.min()
        
    p_ret, p_dd = calc_stats(eq_premium)
    i_ret, i_dd = calc_stats(eq_indicator)
    d_ret, d_dd = calc_stats(eq_delta)
    
    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(eq_premium.index, eq_premium['Equity'], label=f'Premium Stop-Loss (Ret: {p_ret:.1f}%)', color='red')
    plt.plot(eq_indicator.index, eq_indicator['Equity'], label=f'MA Crossover (Ret: {i_ret:.1f}%)', color='blue')
    plt.plot(eq_delta.index, eq_delta['Equity'], label=f'Delta Decay (Ret: {d_ret:.1f}%)', color='green')
    
    # Baseline Buy & Hold
    buy_hold = btc_df['Close'] / btc_df['Close'].iloc[0] * 100000
    plt.plot(buy_hold.index, buy_hold, label='BTC Buy & Hold', color='black', linestyle='--')
    
    plt.title("BTC Dynamic Spread Shifter (SAR) - 1 Year Backtest")
    plt.ylabel("Portfolio Equity ($)")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\spread_shifter_chart.png"
    plt.savefig(chart_path)
    print(f"Saved chart to {chart_path}")
    
    report = f"""# Dynamic Spread Shifter (SAR) Results

We backtested the continuous "Stop-and-Reverse" (SAR) spread strategy on Bitcoin (BTC-USD) over a highly volatile 1-year window (2023).

**Initial Capital:** $100,000
**Structure:** 30 DTE ATM Vertical Spreads (5% Wide). 50% Capital allocation per spread.

## Strategy Variants Performance

### Option A: Premium Stop-Loss (Risk-based)
*Flips when the spread loses 25% of its entry premium.*
* **Total Return:** {p_ret:.2f}%
* **Max Drawdown:** {p_dd:.2f}%

### Option B: Moving Average Crossover (Trend-based)
*Flips when the 5-day SMA crosses the 20-day SMA.*
* **Total Return:** {i_ret:.2f}%
* **Max Drawdown:** {i_dd:.2f}%

### Option C: Delta Decay (Options-based)
*Flips when the net Delta of the spread decays below 0.15 (losing directional Greek sensitivity).*
* **Total Return:** {d_ret:.2f}%
* **Max Drawdown:** {d_dd:.2f}%

![SAR Backtest Chart](/absolute/path/to/spread_shifter_chart.png)
"""
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\spread_shifter_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print("Done.")
