import numpy as np
import pandas as pd
import yfinance as yf
import math
import time
from scipy.special import erf
import random
import matplotlib.pyplot as plt

def norm_cdf(x):
    return (1.0 + erf(x / 1.4142135623730951)) / 2.0

def norm_pdf(x):
    return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)

def bs_greeks_vec(S, K, T, r, sigma, is_call=True):
    sigma = np.maximum(sigma, 1e-5)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    gamma = norm_pdf(d1) / (S * sigma * np.sqrt(T))
    
    if is_call:
        prem = S * norm_cdf(d1) - K * np.exp(-r*T) * norm_cdf(d2)
        delta = norm_cdf(d1)
    else:
        prem = K * np.exp(-r*T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0
        
    return prem, delta, gamma

def run_brain_simulation():
    print("Fetching NIFTY 50 Data (2014-2024)...")
    df = yf.download("^NSEI", start="2014-01-01", end="2024-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df['Vol30'] = df['Vol30'].bfill()
    df['Vol30'] = df['Vol30'].apply(lambda x: 0.15 if math.isnan(x) or x <= 0 else x)
    
    closes = df['Close'].values
    vols = df['Vol30'].values
    r = 0.05
    T_days = 7
    T_yrs = T_days / 365.0
    
    indices = np.arange(0, len(closes) - T_days, T_days)
    S_start = closes[indices]
    S_end = closes[indices + T_days]
    V_start = vols[indices]
    
    num_strats = 20000
    print(f"Generating {num_strats} random architectural permutations...")
    
    # Generate random universes
    # Call strikes: 0.5 to 2.0
    c_strikes = np.random.uniform(0.5, 2.0, num_strats)
    # Put strikes: 0.5 to 2.0
    p_strikes = np.random.uniform(0.5, 2.0, num_strats)
    # Call Qty: -20 to 20
    c_qtys = np.random.uniform(-20.0, 20.0, num_strats)
    # Put Qty: -20 to 20
    p_qtys = np.random.uniform(-20.0, 20.0, num_strats)
    
    results = []
    
    start_time = time.time()
    
    # We will process in chunks to save memory
    chunk_size = 5000
    for chunk_start in range(0, num_strats, chunk_size):
        chunk_end = min(chunk_start + chunk_size, num_strats)
        
        c_strk_c = c_strikes[chunk_start:chunk_end]
        p_strk_c = p_strikes[chunk_start:chunk_end]
        c_qty_c = c_qtys[chunk_start:chunk_end]
        p_qty_c = p_qtys[chunk_start:chunk_end]
        
        K_c = S_start[:, np.newaxis] * c_strk_c
        K_p = S_start[:, np.newaxis] * p_strk_c
        
        # Calculate Call Greeks and Premiums
        S_expand = S_start[:, np.newaxis]
        V_expand = V_start[:, np.newaxis]
        
        c_prem, c_delta, c_gamma = bs_greeks_vec(S_expand, K_c, T_yrs, r, V_expand, is_call=True)
        p_prem, p_delta, p_gamma = bs_greeks_vec(S_expand, K_p, T_yrs, r, V_expand, is_call=False)
        
        c_payoff = np.maximum(0, S_end[:, np.newaxis] - K_c)
        p_payoff = np.maximum(0, K_p - S_end[:, np.newaxis])
        
        total_prem = (c_prem * c_qty_c) + (p_prem * p_qty_c)
        total_pay = (c_payoff * c_qty_c) + (p_payoff * p_qty_c)
        
        # Margin: 20% of spot per short option
        c_margin = np.where(c_qty_c < 0, S_expand * 0.20 * np.abs(c_qty_c), 0.0)
        p_margin = np.where(p_qty_c < 0, S_expand * 0.20 * np.abs(p_qty_c), 0.0)
        total_margin = np.maximum(c_margin + p_margin, 1000.0)
        
        window_ret = (total_pay - total_prem) / total_margin
        window_ret = np.maximum(window_ret, -1.0)
        
        cum_equity = np.cumprod(1.0 + window_ret, axis=0)
        final_returns = cum_equity[-1, :] - 1.0
        
        peaks = np.maximum.accumulate(cum_equity, axis=0)
        drawdowns = (cum_equity - peaks) / peaks
        max_dd = np.min(drawdowns, axis=0)
        
        calmars = np.where(max_dd < 0, final_returns / np.abs(max_dd), final_returns / 1e-5)
        
        avg_net_delta = np.mean((c_delta * c_qty_c) + (p_delta * p_qty_c), axis=0)
        avg_net_gamma = np.mean((c_gamma * c_qty_c) + (p_gamma * p_qty_c), axis=0)
        
        for i in range(chunk_end - chunk_start):
            results.append({
                'C_Strike': c_strk_c[i],
                'P_Strike': p_strk_c[i],
                'C_Qty': c_qty_c[i],
                'P_Qty': p_qty_c[i],
                'Return': final_returns[i],
                'MaxDD': max_dd[i],
                'Calmar': calmars[i],
                'Delta': avg_net_delta[i],
                'Gamma': avg_net_gamma[i]
            })

    print(f"Simulation of 20k geometries took {time.time() - start_time:.2f}s")
    
    df_res = pd.DataFrame(results)
    
    # Normalize metrics for the Brains (Min-Max Scaling 0 to 1)
    df_res['Norm_DD'] = (df_res['MaxDD'] - df_res['MaxDD'].min()) / (df_res['MaxDD'].max() - df_res['MaxDD'].min() + 1e-9)
    df_res['Norm_Gamma'] = (df_res['Gamma'] - df_res['Gamma'].min()) / (df_res['Gamma'].max() - df_res['Gamma'].min() + 1e-9)
    df_res['Norm_Delta'] = (df_res['Delta'] - df_res['Delta'].min()) / (df_res['Delta'].max() - df_res['Delta'].min() + 1e-9)
    df_res['Norm_Calmar'] = (df_res['Calmar'] - df_res['Calmar'].min()) / (df_res['Calmar'].max() - df_res['Calmar'].min() + 1e-9)
    
    # The 4 Brains
    # Buffett: Hates drawdown. Score is exactly the normalized MaxDD (where 1.0 is 0% DD).
    buffett_score = df_res['Norm_DD']
    
    # Livermore: Loves Gamma/Convexity
    livermore_score = df_res['Norm_Gamma']
    
    # Lynch: Loves Secular Trend (Positive Delta)
    lynch_score = df_res['Norm_Delta']
    
    # Simons: Loves pure efficiency (Calmar)
    simons_score = df_res['Norm_Calmar']
    
    # Mastermind Consensus Score (Equal Weighting)
    df_res['Mastermind_Score'] = (buffett_score + livermore_score + lynch_score + simons_score) / 4.0
    
    # Find the top strategies by individual brains
    best_buffett = df_res.iloc[df_res['Norm_DD'].idxmax()]
    best_livermore = df_res.iloc[df_res['Norm_Gamma'].idxmax()]
    best_lynch = df_res.iloc[df_res['Norm_Delta'].idxmax()]
    best_simons = df_res.iloc[df_res['Norm_Calmar'].idxmax()]
    best_mastermind = df_res.sort_values(by='Mastermind_Score', ascending=False).iloc[0]
    
    report = "# 🧠 The Ensemble Brain Consensus Report\n\n"
    report += "We generated 20,000 completely random option geometries (both long, both short, ratios, everything) and fed them into the Neural Ensemble.\n\n"
    
    def print_node(name, row, score_col):
        res = f"## Node: {name}\n"
        res += f"* **Call Strike:** {row['C_Strike']*100:.1f}%\n"
        res += f"* **Put Strike:** {row['P_Strike']*100:.1f}%\n"
        res += f"* **Call Qty:** {row['C_Qty']:.2f}x\n"
        res += f"* **Put Qty:** {row['P_Qty']:.2f}x\n"
        res += f"### Performance\n"
        res += f"* **Return:** {row['Return']*100:,.2f}%\n"
        res += f"* **Max Drawdown:** {row['MaxDD']*100:,.2f}%\n"
        res += f"* **Net Delta:** {row['Delta']:.4f}\n"
        res += f"* **Net Gamma:** {row['Gamma']:.4f}\n\n"
        return res
        
    report += print_node("Warren Buffett (Capital Preservation & Max Safety)", best_buffett, 'Norm_DD')
    report += print_node("Jesse Livermore (Maximum Convexity & Gamma)", best_livermore, 'Norm_Gamma')
    report += print_node("Peter Lynch (Secular Drift & Max Delta)", best_lynch, 'Norm_Delta')
    report += print_node("Jim Simons (Maximum Quant Efficiency)", best_simons, 'Norm_Calmar')
    
    report += "---\n"
    report += "## 👑 The Mastermind Consensus (The Ensemble Strategy)\n"
    report += "This is the single options architecture that satisfied all 4 legendary nodes simultaneously:\n\n"
    report += f"* **Call Strike:** {best_mastermind['C_Strike']*100:.1f}%\n"
    report += f"* **Put Strike:** {best_mastermind['P_Strike']*100:.1f}%\n"
    report += f"* **Call Qty:** {best_mastermind['C_Qty']:.2f}x\n"
    report += f"* **Put Qty:** {best_mastermind['P_Qty']:.2f}x\n"
    report += "### Consensus Performance\n"
    report += f"* **Return:** {best_mastermind['Return']*100:,.2f}%\n"
    report += f"* **Max Drawdown:** {best_mastermind['MaxDD']*100:,.2f}%\n"
    report += f"* **Calmar Ratio:** {best_mastermind['Calmar']:,.2f}\n"
    report += f"* **Net Delta:** {best_mastermind['Delta']:.4f}\n"
    report += f"* **Net Gamma:** {best_mastermind['Gamma']:.4f}\n\n"
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\brain_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    # Plotting the Mastermind Score distribution
    plt.figure(figsize=(10, 6))
    plt.hist(df_res['Mastermind_Score'], bins=50, color='purple', alpha=0.7)
    plt.title("Distribution of Mastermind Consensus Scores across 20,000 Architectures")
    plt.xlabel("Mastermind Score (0 to 1)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.savefig(r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\autonomous_brain_simulation.png")

    print("Done")

if __name__ == '__main__':
    run_brain_simulation()
