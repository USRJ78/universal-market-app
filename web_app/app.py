import math
import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

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

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/payoff', methods=['POST'])
def calculate_payoff():
    data = request.json
    legs = data.get('legs', [])
    S_entry = 100.0
    r = 0.05
    sigma = 0.40
    
    for leg in legs:
        strike = (leg['strike'] / 100.0) * S_entry
        dte = leg['dte'] / 365.0
        price = black_scholes_price(S_entry, strike, dte, r, sigma, leg['type'])
        leg['premium'] = price
        
    x_values = list(range(50, 151)) 
    y_values = []
    
    for S_expiry in x_values:
        total_pnl = 0
        for leg in legs:
            strike = (leg['strike'] / 100.0) * S_entry
            qty = leg['qty']
            action = 1 if leg['action'] == 'buy' else -1
            premium = leg['premium']
            
            if leg['type'] == 'call': payoff = max(0, S_expiry - strike)
            elif leg['type'] == 'put': payoff = max(0, strike - S_expiry)
            else: payoff = (S_expiry - S_entry) 
                
            if leg['type'] == 'future': pnl = payoff * action * qty
            else: pnl = (payoff - premium) * action * qty
                
            total_pnl += pnl
        y_values.append(total_pnl)
        
    return jsonify({'x': x_values, 'y': y_values})

@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.json
    legs = data.get('legs', [])
    asset = data.get('asset', 'BTC-USD')
    start_date = data.get('startDate', '2020-01-01')
    end_date = data.get('endDate', '2024-01-01')
    capital = float(data.get('capital', 100000))
    
    if not legs:
        return jsonify({'error': 'No legs provided'}), 400
        
    print(f"Fetching {asset} from {start_date} to {end_date}...")
    df = yf.download(asset, start=start_date, end=end_date)
    if df.empty:
        return jsonify({'error': 'No data found for this date range'}), 400
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df.fillna(method='bfill', inplace=True)
    
    cash = capital
    r = 0.05
    equity_curve = []
    dates = []
    
    active_legs = []
    days_held = 0
    earliest_dte = min([leg['dte'] for leg in legs if leg['type'] != 'future'] + [365])
    roll_days = max(7, earliest_dte - 2)
    
    for i in range(len(df)):
        date = df.index[i].strftime('%Y-%m-%d')
        S = float(df['Close'].iloc[i])
        sigma = float(df['Vol30'].iloc[i])
        if math.isnan(sigma) or sigma <= 0: sigma = 0.40
        
        # Open Position if none active
        if not active_legs and i < len(df) - 5:
            total_margin = 0
            net_premium = 0
            temp_legs = []
            
            for leg in legs:
                K = S * (leg['strike'] / 100.0)
                T = leg['dte'] / 365.0
                qty = leg['qty']
                action = 1 if leg['action'] == 'buy' else -1
                
                if leg['type'] == 'future':
                    margin = S * 0.10 * qty
                    total_margin += margin
                    temp_legs.append({'type': 'future', 'action': action, 'qty': qty, 'entry': S})
                else:
                    price = black_scholes_price(S, K, T, r, sigma, leg['type'])
                    if action == 1:
                        net_premium -= price * qty
                    else:
                        net_premium += price * qty
                        total_margin += S * 0.20 * qty
                    temp_legs.append({'type': leg['type'], 'action': action, 'strike': K, 'entry_price': price, 'qty': qty, 'dte': leg['dte']})
                    
            if total_margin <= 0: total_margin = 1000
            scale = (cash * 0.90) / total_margin if total_margin > 0 else 1.0
            if scale < 0 or cash <= 0: break
            
            cash += net_premium * scale
            active_legs = temp_legs
            days_held = 0
            current_scale = scale
            
        # MTM
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
        dates.append(date)
        
        # Roll / Settle
        if active_legs and (days_held >= roll_days or i == len(df) - 1):
            cash = mtm_cash
            active_legs = []
            days_held = 0
            if cash <= 0:
                cash = 0
                
    eq_s = pd.Series(equity_curve)
    ret = (eq_s.iloc[-1] / capital - 1) * 100
    peak = eq_s.cummax()
    dd = ((eq_s - peak) / peak).min() * 100
    
    daily_ret = eq_s.pct_change().dropna()
    sharpe = 0.0
    if daily_ret.std() > 0:
        sharpe = (daily_ret.mean() / daily_ret.std()) * math.sqrt(252)
        
    return jsonify({
        'dates': dates,
        'equity': equity_curve,
        'metrics': {
            'return': round(ret, 2),
            'drawdown': round(dd, 2),
            'sharpe': round(sharpe, 2)
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
