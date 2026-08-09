import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
import torch.optim as optim
import math
import matplotlib.pyplot as plt
from scipy.special import erf
from correlation_nn_options_strategy import CorrelationOptionsNN

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Black-Scholes pricing functions
def norm_cdf(x):
    return (1.0 + erf(x / 1.4142135623730951)) / 2.0

def bs_call(S, K, T, r, sigma):
    sigma = max(sigma, 1e-4)
    if T <= 0: return max(0.0, S - K)
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r*T) * norm_cdf(d2)

def bs_put(S, K, T, r, sigma):
    sigma = max(sigma, 1e-4)
    if T <= 0: return max(0.0, K - S)
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    return K * math.exp(-r*T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def run_backtest():
    print("==================================================")
    print("📈 AI CORRELATION OPTIONS STRATEGY BACKTEST 📈")
    print("==================================================")
    
    # 1. Fetch historical data (2 years, hourly)
    print("Fetching hourly BTC, ETH, VIX, and TNX data...")
    btc = yf.download("BTC-USD", period="2y", interval="1h", progress=False)
    eth = yf.download("ETH-USD", period="2y", interval="1h", progress=False)
    vix = yf.download("^VIX", period="2y", interval="1h", progress=False)
    tnx = yf.download("^TNX", period="2y", interval="1h", progress=False)
    
    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
        eth.columns = eth.columns.get_level_values(0)
        vix.columns = vix.columns.get_level_values(0)
        tnx.columns = tnx.columns.get_level_values(0)
        
    print("Aligning and cleaning dataset...")
    df = pd.DataFrame(index=btc.index)
    df['BTC_Close'] = btc['Close']
    df['ETH_Close'] = eth['Close']
    
    # Calculate ratio and Z-score
    df['Ratio'] = df['BTC_Close'] / df['ETH_Close']
    df['Ratio_MA'] = df['Ratio'].rolling(window=30).mean()
    df['Ratio_STD'] = df['Ratio'].rolling(window=30).std()
    df['Ratio_Z'] = (df['Ratio'] - df['Ratio_MA']) / (df['Ratio_STD'] + 1e-9)
    
    # Calculate rolling correlation
    df['BTC_Ret'] = df['BTC_Close'].pct_change()
    df['ETH_Ret'] = df['ETH_Close'].pct_change()
    df['Correlation'] = df['BTC_Ret'].rolling(window=30).corr(df['ETH_Ret'])
    
    # Volatility
    df['BTC_Vol'] = df['BTC_Ret'].rolling(window=30).std() * math.sqrt(365 * 24)
    df['ETH_Vol'] = df['ETH_Ret'].rolling(window=30).std() * math.sqrt(365 * 24)
    df['Vol_Ratio'] = df['BTC_Vol'] / (df['ETH_Vol'] + 1e-9)
    
    # Macro context
    df['VIX'] = vix['Close'].reindex(df.index, method='ffill').fillna(15.0)
    df['TNX'] = tnx['Close'].reindex(df.index, method='ffill').fillna(4.0)
    
    # Drop NaNs
    df.dropna(inplace=True)
    
    # 2. Build target labels based on 24-hour future ratio move
    print("Building synthetic training labels...")
    lookahead = 24 # 24 hours
    labels = []
    for i in range(len(df)):
        if i + lookahead < len(df):
            future_ratio = df['Ratio'].iloc[i + lookahead]
            current_ratio = df['Ratio'].iloc[i]
            ratio_change = (future_ratio - current_ratio) / current_ratio
            
            if ratio_change > 0.015:
                labels.append(1) # BTC outperforming
            elif ratio_change < -0.015:
                labels.append(2) # ETH outperforming
            else:
                labels.append(0) # Hold / Stable
        else:
            labels.append(0)
            
    df['Label'] = labels
    
    # 3. Create tensors
    geom_cols = ['BTC_Ret', 'ETH_Ret', 'Ratio_Z', 'Correlation', 'BTC_Vol', 'ETH_Vol']
    macro_cols = ['VIX', 'TNX']
    
    X_geom, X_macro, Y = [], [], []
    seq_len = 10
    
    for i in range(seq_len, len(df) - lookahead):
        geom_seq = df[geom_cols].iloc[i-seq_len:i].values
        macro_seq = df[macro_cols].iloc[i-seq_len:i].values
        
        # Normalize local sequences
        g_mean, g_std = np.mean(geom_seq, axis=0), np.std(geom_seq, axis=0) + 1e-8
        m_mean, m_std = np.mean(macro_seq, axis=0), np.std(macro_seq, axis=0) + 1e-8
        
        X_geom.append((geom_seq - g_mean) / g_std)
        X_macro.append((macro_seq - m_mean) / m_std)
        Y.append(df['Label'].iloc[i])
        
    X_geom_t = torch.tensor(np.array(X_geom), dtype=torch.float32)
    X_macro_t = torch.tensor(np.array(X_macro), dtype=torch.float32)
    Y_t = torch.tensor(np.array(Y), dtype=torch.long)
    
    # Split train/test (75/25)
    split = int(len(X_geom_t) * 0.75)
    X_geom_train, X_geom_test = X_geom_t[:split], X_geom_t[split:]
    X_macro_train, X_macro_test = X_macro_t[:split], X_macro_t[split:]
    Y_train, Y_test = Y_t[:split], Y_t[split:]
    
    test_df = df.iloc[seq_len + split : len(df) - lookahead].copy()
    
    print(f"Dataset Split: {len(X_geom_train)} train samples, {len(X_geom_test)} test samples.")
    
    # 4. Train model
    print("\nTraining PyTorch Correlation NN...")
    model = CorrelationOptionsNN(seq_len=seq_len, geom_input_dim=6, macro_input_dim=2)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-3)
    
    epochs = 20
    batch_size = 128
    
    model.train()
    for epoch in range(epochs):
        permutation = torch.randperm(X_geom_train.size()[0])
        epoch_loss = 0
        for i in range(0, X_geom_train.size()[0], batch_size):
            indices = permutation[i:i+batch_size]
            batch_g, batch_m, batch_y = X_geom_train[indices], X_macro_train[indices], Y_train[indices]
            
            optimizer.zero_grad()
            outputs = model(batch_g, batch_m)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{epochs} | Loss: {epoch_loss/len(X_geom_train):.6f}")
            
    # 5. Options Simulation Backtest
    print("\nRunning Options Execution Backtest on test set...")
    model.eval()
    with torch.no_grad():
        preds = torch.argmax(model(X_geom_test, X_macro_test), dim=1).numpy()
        
    test_df['Signal'] = preds
    
    # Backtest variables
    initial_capital = 10000.0
    capital = initial_capital
    equity_curve = []
    active_trades = []
    
    # Option Parameters
    dte_hrs = 168 # 7 Days DTE
    dte_yrs = dte_hrs / (365.0 * 24.0)
    rf_rate = 0.05
    allocation_pct = 0.05 # Allocate 5% of capital to each trade (maximum 10 overlapping trades)
    
    wins = 0
    losses = 0
    
    for i in range(len(test_df)):
        current_time = test_df.index[i]
        btc_price = test_df['BTC_Close'].iloc[i]
        eth_price = test_df['ETH_Close'].iloc[i]
        btc_vol = test_df['BTC_Vol'].iloc[i]
        eth_vol = test_df['ETH_Vol'].iloc[i]
        signal = test_df['Signal'].iloc[i]
        
        # 1. Update active trades
        retaining_trades = []
        for trade in active_trades:
            # Check if option expired (168 hours passed)
            if i >= trade['expiry_index']:
                # Calculate payoff at expiration
                btc_expiry_price = test_df['BTC_Close'].iloc[trade['expiry_index']]
                eth_expiry_price = test_df['ETH_Close'].iloc[trade['expiry_index']]
                
                payoff = 0.0
                
                # Trade Type 1: Long BTC / Short ETH (BTC Call Spread & ETH Put Spread)
                if trade['type'] == 1:
                    # BTC Call Spread: Buy ATM Call (K = btc_entry), Sell 5% OTM Call (K = btc_entry * 1.05)
                    btc_payoff = max(0.0, min(btc_expiry_price - trade['btc_entry'], trade['btc_entry'] * 0.05))
                    # ETH Put Spread: Buy ATM Put (K = eth_entry), Sell 5% OTM Put (K = eth_entry * 0.95)
                    eth_payoff = max(0.0, min(trade['eth_entry'] - eth_expiry_price, trade['eth_entry'] * 0.05))
                    
                    # Convert payoffs to return percentage on option premium
                    btc_return = (btc_payoff / (trade['btc_premium'] + 1e-9)) - 1.0
                    eth_return = (eth_payoff / (trade['eth_premium'] + 1e-9)) - 1.0
                    
                    payoff = (trade['allocation'] / 2.0) * (1.0 + btc_return) + (trade['allocation'] / 2.0) * (1.0 + eth_return)
                    
                # Trade Type 2: Short BTC / Long ETH (BTC Put Spread & ETH Call Spread)
                elif trade['type'] == 2:
                    # BTC Put Spread
                    btc_payoff = max(0.0, min(trade['btc_entry'] - btc_expiry_price, trade['btc_entry'] * 0.05))
                    # ETH Call Spread
                    eth_payoff = max(0.0, min(eth_expiry_price - trade['eth_entry'], trade['eth_entry'] * 0.05))
                    
                    btc_return = (btc_payoff / (trade['btc_premium'] + 1e-9)) - 1.0
                    eth_return = (eth_payoff / (trade['eth_premium'] + 1e-9)) - 1.0
                    
                    payoff = (trade['allocation'] / 2.0) * (1.0 + btc_return) + (trade['allocation'] / 2.0) * (1.0 + eth_return)
                
                capital += payoff
                if payoff > trade['allocation']:
                    wins += 1
                else:
                    losses += 1
            else:
                retaining_trades.append(trade)
                
        active_trades = retaining_trades
        
        # 2. Place new trades based on signal (if we have slot and capital)
        if signal in [1, 2] and len(active_trades) < 10 and capital > 100:
            trade_allocation = capital * allocation_pct
            capital -= trade_allocation
            
            # Calculate option premium costs using Black-Scholes
            btc_call_atm = bs_call(btc_price, btc_price, dte_yrs, rf_rate, btc_vol)
            btc_call_otm = bs_call(btc_price, btc_price * 1.05, dte_yrs, rf_rate, btc_vol)
            btc_call_spread_cost = max(0.1, btc_call_atm - btc_call_otm)
            
            btc_put_atm = bs_put(btc_price, btc_price, dte_yrs, rf_rate, btc_vol)
            btc_put_otm = bs_put(btc_price, btc_price * 0.95, dte_yrs, rf_rate, btc_vol)
            btc_put_spread_cost = max(0.1, btc_put_atm - btc_put_otm)
            
            eth_call_atm = bs_call(eth_price, eth_price, dte_yrs, rf_rate, eth_vol)
            eth_call_otm = bs_call(eth_price, eth_price * 1.05, dte_yrs, rf_rate, eth_vol)
            eth_call_spread_cost = max(0.1, eth_call_atm - eth_call_otm)
            
            eth_put_atm = bs_put(eth_price, eth_price, dte_yrs, rf_rate, eth_vol)
            eth_put_otm = bs_put(eth_price, eth_price * 0.95, dte_yrs, rf_rate, eth_vol)
            eth_put_spread_cost = max(0.1, eth_put_atm - eth_put_otm)
            
            btc_premium = btc_call_spread_cost if signal == 1 else btc_put_spread_cost
            eth_premium = eth_put_spread_cost if signal == 1 else eth_call_spread_cost
            
            active_trades.append({
                'type': signal,
                'entry_index': i,
                'expiry_index': min(i + dte_hrs, len(test_df) - 1),
                'allocation': trade_allocation,
                'btc_entry': btc_price,
                'eth_entry': eth_price,
                'btc_premium': btc_premium,
                'eth_premium': eth_premium
            })
            
        # Calculate current net asset value (NAV)
        current_equity = capital + sum([t['allocation'] for t in active_trades])
        equity_curve.append(current_equity)
        
    test_df['Strategy_Equity'] = equity_curve
    test_df['BTC_Hold_Return'] = (test_df['BTC_Close'] / test_df['BTC_Close'].iloc[0]) * initial_capital
    
    # Calculate performance metrics
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    
    # Drawdown
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - peaks) / peaks
    max_dd = np.min(drawdowns)
    
    # Win rate
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    
    print("\n========== BACKTEST REPORT ==========")
    print(f"Final Equity: ${final_equity:.2f}")
    print(f"Total Return: {total_return * 100.0:.2f}%")
    print(f"Max Drawdown: {max_dd * 100.0:.2f}%")
    print(f"Win Rate: {win_rate:.2f}% ({wins} wins, {losses} losses)")
    
    # Save chart
    plt.figure(figsize=(12, 6))
    plt.plot(test_df.index, test_df['Strategy_Equity'], label='AI Correlation Options Strategy', color='blue', linewidth=2)
    plt.plot(test_df.index, test_df['BTC_Hold_Return'], label='BTC Buy & Hold', color='orange', linestyle='--', alpha=0.7)
    plt.title('AI Correlation Options Strategy vs BTC Buy & Hold (Out-of-Sample)')
    plt.xlabel('Date')
    plt.ylabel('Equity ($)')
    plt.legend()
    plt.grid(True)
    
    chart_path = r'C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\correlation_nn_backtest_chart.png'
    plt.savefig(chart_path)
    print(f"Performance chart saved to {chart_path}")
    
    # Save Report
    report = f"""# AI Correlation Options Strategy Backtest Report

We evaluated the performance of the **AI Correlation Neural Network Options Strategy** on the out-of-sample test set (last 6 months, hourly BTC/ETH options trading).

## 🏆 Performance Overview
* **Initial Capital:** $10,000.00
* **Final Equity:** ${final_equity:,.2f}
* **Total Return:** {total_return * 100.0:.2f}%
* **Max Drawdown:** {max_dd * 100.0:.2f}%
* **Win Rate:** {win_rate:.2f}% ({wins} wins, {losses} losses)

## 📈 Equity Curve Comparison
The performance chart comparing the Neural Network option strategy against holding BTC Spot is saved at [correlation_nn_backtest_chart.png](file:///{chart_path.replace('\\', '/')}).

## 🧠 Brain Architecture Details
The strategy uses a PyTorch LSTM model trained to spot relative strength divergence and automatically hedge across BTC/ETH options spreads.
"""
    report_path = r'C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\correlation_nn_backtest_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to {report_path}")

if __name__ == '__main__':
    run_backtest()
