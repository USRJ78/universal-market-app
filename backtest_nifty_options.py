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

def run_nifty_backtest():
    print("==================================================")
    print("📈 NIFTY vs BANKNIFTY OPTIONS CORRELATION BACKTEST 📈")
    print("==================================================")
    
    # 1. Fetch historical data (2 years, hourly)
    print("Fetching hourly Nifty, Bank Nifty, and India VIX data...")
    nifty = yf.download("^NSEI", period="2y", interval="1h", progress=False)
    banknifty = yf.download("^NSEBANK", period="2y", interval="1h", progress=False)
    indiavix = yf.download("^INDIAVIX", period="2y", interval="1h", progress=False)
    
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
        banknifty.columns = banknifty.columns.get_level_values(0)
        indiavix.columns = indiavix.columns.get_level_values(0)
        
    print("Aligning and cleaning dataset...")
    df = pd.DataFrame(index=nifty.index)
    df['NIFTY_Close'] = nifty['Close']
    df['BANKNIFTY_Close'] = banknifty['Close']
    
    # Multi-timeframe features
    df['NIFTY_Ret'] = df['NIFTY_Close'].pct_change()
    df['BANKNIFTY_Ret'] = df['BANKNIFTY_Close'].pct_change()
    
    df['Ratio'] = df['NIFTY_Close'] / df['BANKNIFTY_Close']
    
    # Z-scores and rolling correlations
    for w in [10, 50, 120]:
        df[f'Ratio_MA_{w}'] = df['Ratio'].rolling(window=w).mean()
        df[f'Ratio_STD_{w}'] = df['Ratio'].rolling(window=w).std()
        df[f'Ratio_Z_{w}'] = (df['Ratio'] - df[f'Ratio_MA_{w}']) / (df[f'Ratio_STD_{w}'] + 1e-9)
        df[f'Corr_{w}'] = df['NIFTY_Ret'].rolling(window=w).corr(df['BANKNIFTY_Ret'])
        
    # Volatility
    df['NIFTY_Vol'] = df['NIFTY_Ret'].rolling(window=50).std() * math.sqrt(252 * 7)
    df['BANKNIFTY_Vol'] = df['BANKNIFTY_Ret'].rolling(window=50).std() * math.sqrt(252 * 7)
    
    # India VIX
    df['VIX'] = indiavix['Close'].reindex(df.index, method='ffill').fillna(15.0)
    df['TNX'] = 7.0
    
    df.dropna(inplace=True)
    
    # Target labeling (14 hours = 2 trading days lookahead)
    print("Building training labels (14h lookahead)...")
    lookahead = 14
    labels = []
    for i in range(len(df)):
        if i + lookahead < len(df):
            future_ratio = df['Ratio'].iloc[i + lookahead]
            current_ratio = df['Ratio'].iloc[i]
            ratio_change = (future_ratio - current_ratio) / current_ratio
            
            # Lower threshold to 0.6% to capture more divergence opportunities
            if ratio_change > 0.006:
                labels.append(1) # Nifty outperforming
            elif ratio_change < -0.006:
                labels.append(2) # BankNifty outperforming
            else:
                labels.append(0) # Stable
        else:
            labels.append(0)
            
    df['Label'] = labels
    
    # Print label distribution
    label_counts = df['Label'].value_counts()
    print("Label distribution in dataset:")
    print(label_counts)
    
    # Calculate class weights to handle imbalance
    total_samples = len(df)
    class_weights = []
    for c in [0, 1, 2]:
        count = label_counts.get(c, 1)
        # Inverse frequency weighting
        class_weights.append(total_samples / (3.0 * count))
    weights_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"Class Weights passed to Loss Function: {class_weights}")
    
    geom_cols = [
        'NIFTY_Ret', 'BANKNIFTY_Ret', 
        'Ratio_Z_10', 'Ratio_Z_50', 'Ratio_Z_120',
        'Corr_10', 'Corr_50', 'Corr_120',
        'NIFTY_Vol', 'BANKNIFTY_Vol', 'Ratio'
    ]
    macro_cols = ['VIX', 'TNX']
    
    geom_arr = df[geom_cols].values
    macro_arr = df[macro_cols].values
    labels_arr = df['Label'].values
    
    X_geom, X_macro, Y = [], [], []
    seq_len = 10
    
    for i in range(seq_len, len(df) - lookahead):
        geom_seq = geom_arr[i-seq_len:i]
        macro_seq = macro_arr[i-seq_len:i]
        
        g_mean, g_std = np.mean(geom_seq, axis=0), np.std(geom_seq, axis=0) + 1e-8
        m_mean, m_std = np.mean(macro_seq, axis=0), np.std(macro_seq, axis=0) + 1e-8
        
        X_geom.append((geom_seq - g_mean) / g_std)
        X_macro.append((macro_seq - m_mean) / m_std)
        Y.append(labels_arr[i])
        
    X_geom_t = torch.tensor(np.array(X_geom), dtype=torch.float32)
    X_macro_t = torch.tensor(np.array(X_macro), dtype=torch.float32)
    Y_t = torch.tensor(np.array(Y), dtype=torch.long)
    
    split = int(len(X_geom_t) * 0.75)
    X_geom_train, X_geom_test = X_geom_t[:split], X_geom_t[split:]
    X_macro_train, X_macro_test = X_macro_t[:split], X_macro_t[split:]
    Y_train, Y_test = Y_t[:split], Y_t[split:]
    
    test_df = df.iloc[seq_len + split : len(df) - lookahead].copy()
    
    # 4. Train model (Use Weighted CrossEntropyLoss)
    print("Training PyTorch Correlation NN for NIFTY (Weighted Loss)...")
    model = CorrelationOptionsNN(seq_len=seq_len, geom_input_dim=11, macro_input_dim=2)
    criterion = nn.CrossEntropyLoss(weight=weights_tensor)
    optimizer = optim.AdamW(model.parameters(), lr=0.0005, weight_decay=1e-2)
    
    epochs = 40
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
            
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs} | Loss: {epoch_loss/len(X_geom_train):.6f}")
            
    # 5. Options Simulation Backtest
    print("Running Options spreads backtest on test dataset...")
    model.eval()
    with torch.no_grad():
        outputs = model(X_geom_test, X_macro_test)
        probs = torch.softmax(outputs, dim=1).numpy()
        preds = torch.argmax(outputs, dim=1).numpy()
        
    test_df['Signal'] = preds
    test_df['Prob'] = np.max(probs, axis=1)
    
    print(f"Predictions Value Counts on Test Set:")
    print(pd.Series(preds).value_counts())
    
    initial_capital = 100000.0 # 1 Lakh Rupees
    capital = initial_capital
    equity_curve = []
    active_trades = []
    
    # Option Parameters
    dte_hrs = 35 # 5 trading days
    dte_yrs = 5.0 / 365.0
    rf_rate = 0.07
    allocation_pct = 0.05
    confidence_threshold = 0.40 # Slightly lower confidence threshold because we use weighted loss
    
    wins = 0
    losses = 0
    
    for i in range(len(test_df)):
        nifty_price = test_df['NIFTY_Close'].iloc[i]
        bn_price = test_df['BANKNIFTY_Close'].iloc[i]
        nifty_vol = test_df['NIFTY_Vol'].iloc[i]
        bn_vol = test_df['BANKNIFTY_Vol'].iloc[i]
        signal = test_df['Signal'].iloc[i]
        prob = test_df['Prob'].iloc[i]
        
        # Update active trades
        retaining_trades = []
        for trade in active_trades:
            if i >= trade['expiry_index']:
                nifty_expiry_price = test_df['NIFTY_Close'].iloc[trade['expiry_index']]
                bn_expiry_price = test_df['BANKNIFTY_Close'].iloc[trade['expiry_index']]
                
                payoff = 0.0
                
                if trade['type'] == 1:
                    # Nifty Call Spread (Buy ATM, Sell 5% OTM)
                    nifty_payoff = max(0.0, min(nifty_expiry_price - trade['nifty_entry'], trade['nifty_entry'] * 0.05))
                    # BankNifty Put Spread (Buy ATM, Sell 5% OTM)
                    bn_payoff = max(0.0, min(trade['bn_entry'] - bn_expiry_price, trade['bn_entry'] * 0.05))
                    
                    n_return = nifty_payoff / (trade['nifty_premium'] + 1e-9)
                    bn_return = bn_payoff / (trade['bn_premium'] + 1e-9)
                    payoff = (trade['allocation'] / 2.0) * n_return + (trade['allocation'] / 2.0) * bn_return
                    
                elif trade['type'] == 2:
                    # Nifty Put Spread (Buy ATM, Sell 5% OTM)
                    nifty_payoff = max(0.0, min(trade['nifty_entry'] - nifty_expiry_price, trade['nifty_entry'] * 0.05))
                    # BankNifty Call Spread (Buy ATM, Sell 5% OTM)
                    bn_payoff = max(0.0, min(bn_expiry_price - trade['bn_entry'], trade['bn_entry'] * 0.05))
                    
                    n_return = nifty_payoff / (trade['nifty_premium'] + 1e-9)
                    bn_return = bn_payoff / (trade['bn_premium'] + 1e-9)
                    payoff = (trade['allocation'] / 2.0) * n_return + (trade['allocation'] / 2.0) * bn_return
                
                capital += payoff
                if payoff > trade['allocation']:
                    wins += 1
                else:
                    losses += 1
            else:
                retaining_trades.append(trade)
                
        active_trades = retaining_trades
        
        # Place new trades
        if signal in [1, 2] and prob >= confidence_threshold and len(active_trades) < 10 and capital > 1000:
            trade_allocation = capital * allocation_pct
            capital -= trade_allocation
            
            n_call_atm = bs_call(nifty_price, nifty_price, dte_yrs, rf_rate, nifty_vol)
            n_call_otm = bs_call(nifty_price, nifty_price * 1.05, dte_yrs, rf_rate, nifty_vol)
            n_call_spread = max(1.0, n_call_atm - n_call_otm)
            
            n_put_atm = bs_put(nifty_price, nifty_price, dte_yrs, rf_rate, nifty_vol)
            n_put_otm = bs_put(nifty_price, nifty_price * 0.95, dte_yrs, rf_rate, nifty_vol)
            n_put_spread = max(1.0, n_put_atm - n_put_otm)
            
            bn_call_atm = bs_call(bn_price, bn_price, dte_yrs, rf_rate, bn_vol)
            bn_call_otm = bs_call(bn_price, bn_price * 1.05, dte_yrs, rf_rate, bn_vol)
            bn_call_spread = max(1.0, bn_call_atm - bn_call_otm)
            
            bn_put_atm = bs_put(bn_price, bn_price, dte_yrs, rf_rate, bn_vol)
            bn_put_otm = bs_put(bn_price, bn_price * 0.95, dte_yrs, rf_rate, bn_vol)
            bn_put_spread = max(1.0, bn_put_atm - bn_put_otm)
            
            nifty_premium = n_call_spread if signal == 1 else n_put_spread
            bn_premium = bn_put_spread if signal == 1 else bn_call_spread
            
            active_trades.append({
                'type': signal,
                'entry_index': i,
                'expiry_index': min(i + dte_hrs, len(test_df) - 1),
                'allocation': trade_allocation,
                'nifty_entry': nifty_price,
                'bn_entry': bn_price,
                'nifty_premium': nifty_premium,
                'bn_premium': bn_premium
            })
            
        current_equity = capital + sum([t['allocation'] for t in active_trades])
        equity_curve.append(current_equity)
        
    test_df['Strategy_Equity'] = equity_curve
    test_df['NIFTY_Hold_Return'] = (test_df['NIFTY_Close'] / test_df['NIFTY_Close'].iloc[0]) * initial_capital
    
    # Calculate performance metrics
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - peaks) / peaks
    max_dd = np.min(drawdowns)
    
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    
    print("\n========== NIFTY BACKTEST REPORT ==========")
    print(f"Final Equity: ₹{final_equity:.2f}")
    print(f"Total Return: {total_return * 100.0:.2f}%")
    print(f"Max Drawdown: {max_dd * 100.0:.2f}%")
    print(f"Win Rate: {win_rate:.2f}% ({wins} wins, {losses} losses)")
    
    # Save chart
    plt.figure(figsize=(12, 6))
    plt.plot(test_df.index, test_df['Strategy_Equity'], label='AI Nifty Options Strategy', color='blue', linewidth=2)
    plt.plot(test_df.index, test_df['NIFTY_Hold_Return'], label='Nifty 50 Buy & Hold', color='orange', linestyle='--', alpha=0.7)
    plt.title('AI Correlation Options Strategy vs Nifty 50 Buy & Hold (Balanced)')
    plt.xlabel('Date')
    plt.ylabel('Equity (₹)')
    plt.legend()
    plt.grid(True)
    
    chart_path = r'C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\nifty_correlation_nn_chart.png'
    plt.savefig(chart_path)
    print(f"Performance chart saved to {chart_path}")
    
    # Save Report
    report = f"""# Nifty Options Correlation Strategy Backtest Report (Weighted Loss + Balanced Labels)

We evaluated the performance of the **AI Correlation Options Strategy** on the **Nifty 50 vs Bank Nifty** hourly index options dataset over a 2-year period.

## 🏆 Performance Overview
* **Initial Capital:** ₹100,000.00
* **Final Equity:** ₹{final_equity:,.2f}
* **Total Return:** {total_return * 100.0:.2f}%
* **Max Drawdown:** {max_dd * 100.0:.2f}%
* **Win Rate:** {win_rate:.2f}% ({wins} wins, {losses} losses)

## 📈 Equity Curve Comparison
The performance chart is saved at [nifty_correlation_nn_chart.png](file:///{chart_path.replace('\\', '/')}).
"""
    report_path = r'C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\nifty_correlation_nn_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to {report_path}")

if __name__ == '__main__':
    run_nifty_backtest()
