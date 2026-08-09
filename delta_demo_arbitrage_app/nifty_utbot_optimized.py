import yfinance as yf
import pandas as pd
import numpy as np

print("Running Nifty UT Bot optimization...")
nifty = yf.download("^NSEI", start="2016-07-16", end="2026-07-16", progress=False)
if isinstance(nifty.columns, pd.MultiIndex):
    nifty.columns = nifty.columns.get_level_values(0)

high = nifty['High']
low = nifty['Low']
close = nifty['Close']

high_low = high - low
high_cp = np.abs(high - close.shift(1))
low_cp = np.abs(low - close.shift(1))
tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)

def run_utbot_backtest(df_tr, close_series, key_value, atr_period, friction=0.001):
    atr = df_tr.rolling(atr_period).mean()
    nloss = key_value * atr
    
    xatr = [0.0] * len(close_series)
    for t in range(1, len(close_series)):
        src_curr = close_series.iloc[t]
        src_prev = close_series.iloc[t-1]
        xatr_prev = xatr[t-1]
        loss_curr = nloss.iloc[t]
        
        if src_curr > xatr_prev and src_prev > xatr_prev:
            xatr[t] = max(xatr_prev, src_curr - loss_curr)
        elif src_curr < xatr_prev and src_prev < xatr_prev:
            xatr[t] = min(xatr_prev, src_curr + loss_curr)
        else:
            xatr[t] = (src_curr - loss_curr) if src_curr > xatr_prev else (src_curr + loss_curr)
            
    xatr = pd.Series(xatr, index=close_series.index)
    buy_signals = (close_series > xatr) & (close_series.shift(1) <= xatr.shift(1))
    sell_signals = (close_series < xatr) & (close_series.shift(1) >= xatr.shift(1))
    
    capital = 100000.0
    position = 0.0
    in_position = False
    portfolio_values = []
    trades_count = 0
    
    for t in range(len(close_series)):
        curr_close = close_series.iloc[t]
        
        if not in_position:
            if buy_signals.iloc[t] and t > atr_period:
                fee = capital * friction
                capital -= fee
                position = capital / curr_close
                in_position = True
                capital = 0.0
                trades_count += 1
            portfolio_values.append(capital if not in_position else position * curr_close)
        else:
            if sell_signals.iloc[t]:
                val = position * curr_close
                fee = val * friction
                capital = val - fee
                position = 0.0
                in_position = False
                portfolio_values.append(capital)
            else:
                portfolio_values.append(position * curr_close)
                
    portfolio_values = pd.Series(portfolio_values, index=close_series.index)
    cagr = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) ** (252 / len(portfolio_values)) - 1
    return cagr, portfolio_values, trades_count

best_cagr = 0.0
best_params = {}

for kv in [1, 2, 3, 4, 5]:
    for ap in [5, 10, 20, 50, 100]:
        cagr, _, tc = run_utbot_backtest(tr, close, kv, ap)
        if cagr > best_cagr:
            best_cagr = cagr
            best_params = {"kv": kv, "ap": ap, "cagr": cagr, "trades": tc}

print(f"Best parameters found for Nifty 50:")
print(f"  Key Value:     {best_params['kv']}")
print(f"  ATR Period:    {best_params['ap']}")
print(f"  CAGR:          {best_params['cagr']*100:.2f}%")
print(f"  Trades count:  {best_params['trades']}")
