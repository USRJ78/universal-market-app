import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import math

class SyntheticOptionsEnv:
    def __init__(self, ticker='TSLA', start_date='2023-01-01', end_date='2024-01-01', initial_capital=100000.0):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        self.cash = initial_capital
        self.positions = [] # List of dicts: {'type': 'CALL'/'PUT', 'strike': 150, 'expiry_date': '...', 'premium_paid': 5.0, 'qty': 100}
        self.current_step = 0
        
        self._load_data()
        
    def _load_data(self):
        print(f"Loading {self.ticker} data from {self.start_date} to {self.end_date}...")
        self.df = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)
        if isinstance(self.df.columns, pd.MultiIndex):
            self.df.columns = self.df.columns.get_level_values(0)
        self.vix = yf.download('^VIX', start=self.start_date, end=self.end_date, progress=False)
        if isinstance(self.vix.columns, pd.MultiIndex):
            self.vix.columns = self.vix.columns.get_level_values(0)
            
        self.df['VIX'] = self.vix['Close']
        self.df.dropna(inplace=True)
        self.dates = self.df.index.tolist()
        print(f"Loaded {len(self.dates)} trading days.")

    def reset(self):
        self.cash = self.initial_capital
        self.positions = []
        self.current_step = 0
        return self._get_observation()
        
    def _bs_call(self, S, K, T, r, sigma):
        if T <= 0: return max(0, S - K)
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
        
    def _bs_put(self, S, K, T, r, sigma):
        if T <= 0: return max(0, K - S)
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        return K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    def _generate_option_chain(self, S, vix, current_date):
        # Generate strikes +/- 15% from current price
        base_strike = round(S / 5) * 5
        strikes = [base_strike + i*5 for i in range(-3, 4)]
        
        # 1 month to expiry (~21 trading days)
        T = 21 / 252.0 
        r = 0.05 # 5% risk free rate
        sigma = vix / 100.0 # VIX is in percentage
        
        chain = []
        for K in strikes:
            call_px = self._bs_call(S, K, T, r, sigma)
            put_px = self._bs_put(S, K, T, r, sigma)
            chain.append({
                'strike': K,
                'call_ask': round(call_px * 1.02, 2), # Add spread
                'put_ask': round(put_px * 1.02, 2)
            })
        return chain

    def _get_observation(self):
        if self.current_step >= len(self.dates):
            return None
            
        current_date = self.dates[self.current_step]
        row = self.df.iloc[self.current_step]
        S = row['Close']
        vix = row['VIX']
        
        chain = self._generate_option_chain(S, vix, current_date)
        
        # Also compute current portfolio value
        portfolio_val = self.cash
        for pos in self.positions:
            # Re-price the option based on remaining time
            days_held = (current_date - pos['entry_date']).days
            days_left = max(0, 30 - days_held) # assuming 30 days total expiry approx
            T = days_left / 365.0
            
            if pos['type'] == 'CALL':
                px = self._bs_call(S, pos['strike'], T, 0.05, vix/100.0)
            else:
                px = self._bs_put(S, pos['strike'], T, 0.05, vix/100.0)
                
            portfolio_val += px * pos['qty'] * 100 # options multiplier is 100
            
        obs = {
            'date': current_date.strftime('%Y-%m-%d'),
            'price': round(S, 2),
            'vix': round(vix, 2),
            'option_chain': chain,
            'cash': round(self.cash, 2),
            'portfolio_value': round(portfolio_val, 2),
            'open_positions': [
                {
                    'type': p['type'], 
                    'strike': p['strike'], 
                    'days_held': (current_date - p['entry_date']).days
                } for p in self.positions
            ]
        }
        return obs

    def step(self, action):
        """
        action is a dict: 
        {'type': 'BUY_CALL'/'BUY_PUT'/'CLOSE_ALL'/'HOLD', 'strike': 150}
        """
        obs = self._get_observation()
        if obs is None:
            return None, 0, True
            
        S = obs['price']
        vix = obs['vix']
        current_date = self.dates[self.current_step]
        
        # Settle any expired options (approximated as held for 30 days)
        active_pos = []
        for pos in self.positions:
            days_held = (current_date - pos['entry_date']).days
            if days_held >= 30:
                # Expired - calculate intrinsic
                if pos['type'] == 'CALL':
                    intrinsic = max(0, S - pos['strike'])
                else:
                    intrinsic = max(0, pos['strike'] - S)
                self.cash += intrinsic * pos['qty'] * 100
            else:
                active_pos.append(pos)
        self.positions = active_pos
        
        # Execute Action
        action_type = action.get('action_type', 'HOLD')
        if action_type == 'CLOSE_ALL':
            for pos in self.positions:
                days_held = (current_date - pos['entry_date']).days
                T = max(0, 30 - days_held) / 365.0
                if pos['type'] == 'CALL':
                    px = self._bs_call(S, pos['strike'], T, 0.05, vix/100.0)
                else:
                    px = self._bs_put(S, pos['strike'], T, 0.05, vix/100.0)
                self.cash += px * 0.98 * pos['qty'] * 100 # 2% slippage on close
            self.positions = []
            
        elif action_type in ['BUY_CALL', 'BUY_PUT']:
            # Find the strike in chain
            strike = action.get('strike')
            chain = obs['option_chain']
            target_opt = next((x for x in chain if x['strike'] == strike), None)
            
            if target_opt:
                if action_type == 'BUY_CALL':
                    premium = target_opt['call_ask']
                    opt_type = 'CALL'
                else:
                    premium = target_opt['put_ask']
                    opt_type = 'PUT'
                    
                cost = premium * 100 * 1 # Buy 1 contract
                if self.cash >= cost:
                    self.cash -= cost
                    self.positions.append({
                        'type': opt_type,
                        'strike': strike,
                        'entry_date': current_date,
                        'premium_paid': premium,
                        'qty': 1
                    })
        
        self.current_step += 1
        done = self.current_step >= len(self.dates)
        next_obs = self._get_observation() if not done else None
        
        reward = next_obs['portfolio_value'] - obs['portfolio_value'] if next_obs else 0
        
        return next_obs, reward, done
