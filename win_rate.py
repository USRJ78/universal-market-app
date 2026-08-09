import pandas as pd
import numpy as np
from backtest_graham_lynch_cached import load_cached_data, calculate_graham_value, get_historical_eps

data, fundamentals = load_cached_data()

dates = data.index
portfolio_cash = 100000.0
positions = {} 
trades = []

rebalance_days = 90
days_since_rebalance = 90 

for i, date in enumerate(dates):
    current_prices = data.iloc[i]
    mtm_val = portfolio_cash
    for t, details in positions.items():
        if not pd.isna(current_prices.get(t, np.nan)):
            mtm_val += details['shares'] * current_prices[t]
            
    days_since_rebalance += 1
    
    if days_since_rebalance >= rebalance_days:
        days_ago = (dates[-1] - date).days
        scores = []
        for t in fundamentals.keys():
            if t not in current_prices or pd.isna(current_prices[t]): continue
            price = current_prices[t]
            if price <= 0: continue
            
            f = fundamentals[t]
            hist_eps = get_historical_eps(f['current_eps'], f['growth_rate'], days_ago)
            g = f['growth_rate']
            intrinsic_val = calculate_graham_value(hist_eps, g)
            pe = price / hist_eps if hist_eps > 0 else 999
            peg = pe / g if g > 0 else 999
            margin_of_safety = intrinsic_val / price
            
            if margin_of_safety > 1.0 and peg < 1.5:
                scores.append((t, margin_of_safety))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        target_tickers = [x[0] for x in scores[:15]]
        
        for t in list(positions.keys()):
            if t not in target_tickers:
                price_to_sell = current_prices.get(t, np.nan)
                if not pd.isna(price_to_sell) and price_to_sell > 0:
                    portfolio_cash += positions[t]['shares'] * price_to_sell
                    trades.append({'ticker': t, 'buy_price': positions[t]['avg_price'], 'sell_price': price_to_sell, 'return': price_to_sell / positions[t]['avg_price'] - 1})
                    del positions[t]
                    
        if len(target_tickers) > 0:
            allocation_per_stock = mtm_val / len(target_tickers)
            for t in target_tickers:
                current_holding_val = positions.get(t, {'shares': 0})['shares'] * current_prices[t]
                if current_holding_val < allocation_per_stock:
                    amount_to_buy = allocation_per_stock - current_holding_val
                    amount_to_buy = min(amount_to_buy, portfolio_cash)
                    if amount_to_buy > 0:
                        shares_to_buy = amount_to_buy / current_prices[t]
                        if t in positions:
                            old_shares = positions[t]['shares']
                            old_val = old_shares * positions[t]['avg_price']
                            new_shares = old_shares + shares_to_buy
                            new_avg = (old_val + amount_to_buy) / new_shares
                            positions[t] = {'shares': new_shares, 'avg_price': new_avg}
                        else:
                            positions[t] = {'shares': shares_to_buy, 'avg_price': current_prices[t]}
                        portfolio_cash -= amount_to_buy
                elif current_holding_val > allocation_per_stock:
                    if current_prices[t] > 0 and not pd.isna(current_prices[t]):
                        amount_to_sell = current_holding_val - allocation_per_stock
                        shares_to_sell = amount_to_sell / current_prices[t]
                        positions[t]['shares'] -= shares_to_sell
                        portfolio_cash += amount_to_sell
                        
        days_since_rebalance = 0

df = pd.DataFrame(trades)
wins = len(df[df['return'] > 0])
total = len(df)
print(f'Total Trades: {total}')
print(f'Winning Trades: {wins}')
print(f'Win Rate: {wins/total*100:.2f}%')
print(f'Average Win: {df[df["return"] > 0]["return"].mean()*100:.2f}%')
print(f'Average Loss: {df[df["return"] <= 0]["return"].mean()*100:.2f}%')
