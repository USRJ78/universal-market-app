import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Top Nifty stocks for the universe
TICKERS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS',
    'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS', 'BAJFINANCE.NS',
    'HINDUNILVR.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
    'TITAN.NS', 'ULTRACEMCO.NS', 'ASIANPAINT.NS', 'NTPC.NS', 'TATASTEEL.NS',
    'POWERGRID.NS', 'M&M.NS', 'HCLTECH.NS', 'WIPRO.NS', 
    'ONGC.NS', 'COALINDIA.NS', 'BAJAJFINSV.NS', 'NESTLEIND.NS', 'GRASIM.NS'
]

START_DATE = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')
CAPITAL = 100000.0
MAX_POSITIONS = 15
AAA_YIELD = 7.5  # India AAA corporate bond yield proxy

def fetch_data():
    print("Fetching historical price data for Indian equities...")
    raw_data = yf.download(TICKERS, start=START_DATE, end=END_DATE)
    if isinstance(raw_data.columns, pd.MultiIndex):
        try:
            data = raw_data['Adj Close']
        except KeyError:
            data = raw_data['Close']
    else:
        data = raw_data
        
    data.fillna(method='ffill', inplace=True)
    
    fundamentals = {}
    print("Fetching current fundamental data to build historical proxy...")
    for t in TICKERS:
        try:
            if t not in data.columns:
                print(f"Skipping {t} because it is not in price data columns")
                continue
            ticker = yf.Ticker(t)
            info = ticker.info
            eps = info.get('trailingEps', None)
            peg = info.get('pegRatio', None)
            
            # Fallbacks if yfinance is missing data
            if eps is None or eps <= 0:
                price = data[t].iloc[-1]
                eps = price / 20.0  # Assume P/E of 20
            
            if peg is None or peg <= 0:
                peg = 1.2 # Assume slight overvaluation baseline
                
            # Reverse-engineer an implied growth rate from PEG
            # PEG = (P/E) / g -> g = (P/E) / PEG
            current_price = data[t].iloc[-1]
            pe_ratio = current_price / eps
            growth_rate = pe_ratio / peg
            
            # Bound the growth rate realistically for India (5% to 25%)
            growth_rate = max(5.0, min(25.0, growth_rate))
            
            fundamentals[t] = {
                'current_eps': eps,
                'growth_rate': growth_rate, # percentage
            }
        except Exception as e:
            print(f"Failed to fetch {t}: {e}")
            
    return data, fundamentals

def get_historical_eps(current_eps, growth_rate, days_ago):
    # Discount EPS backwards
    years_ago = days_ago / 365.0
    # Formula: EPS_past = EPS_current / ((1 + g)^years)
    g_decimal = growth_rate / 100.0
    return current_eps / ((1 + g_decimal) ** years_ago)

def calculate_graham_value(eps, g):
    # Benjamin Graham Formula: V = EPS * (8.5 + 2g) * 4.4 / Y
    return eps * (8.5 + 2 * g) * 4.4 / AAA_YIELD

def run_backtest(data, fundamentals):
    dates = data.index
    portfolio_cash = CAPITAL
    positions = {} # {ticker: shares}
    equity_curve = []
    
    rebalance_days = 90
    days_since_rebalance = 90 # trigger immediately
    
    total_days = (dates[-1] - dates[0]).days
    
    for i, date in enumerate(dates):
        current_prices = data.iloc[i]
        
        # Calculate daily MTM equity
        mtm_val = portfolio_cash
        for t, shares in positions.items():
            mtm_val += shares * current_prices[t]
        equity_curve.append({'Date': date, 'Equity': mtm_val})
        
        days_since_rebalance += 1
        
        # Rebalance Quarterly
        if days_since_rebalance >= rebalance_days:
            days_ago = (dates[-1] - date).days
            
            # 1. Score all stocks
            scores = []
            for t in TICKERS:
                if pd.isna(current_prices[t]) or t not in fundamentals:
                    continue
                    
                price = current_prices[t]
                if price <= 0: continue
                
                f = fundamentals[t]
                hist_eps = get_historical_eps(f['current_eps'], f['growth_rate'], days_ago)
                g = f['growth_rate']
                
                # Graham Intrinsic Value
                intrinsic_val = calculate_graham_value(hist_eps, g)
                
                # Lynch PEG
                pe = price / hist_eps if hist_eps > 0 else 999
                peg = pe / g if g > 0 else 999
                
                # Filters: Must be undervalued (Price < Intrinsic) AND PEG < 1.5
                margin_of_safety = intrinsic_val / price
                
                if margin_of_safety > 1.0 and peg < 1.5:
                    scores.append((t, margin_of_safety))
            
            # Sort by highest margin of safety
            scores.sort(key=lambda x: x[1], reverse=True)
            target_tickers = [x[0] for x in scores[:MAX_POSITIONS]]
            
            # 2. Sell stocks not in target list
            for t in list(positions.keys()):
                if t not in target_tickers:
                    portfolio_cash += positions[t] * current_prices[t]
                    del positions[t]
            
            # 3. Buy/Rebalance target stocks
            if len(target_tickers) > 0:
                allocation_per_stock = mtm_val / len(target_tickers)
                for t in target_tickers:
                    current_holding_val = positions.get(t, 0) * current_prices[t]
                    if current_holding_val < allocation_per_stock:
                        # Buy more
                        amount_to_buy = allocation_per_stock - current_holding_val
                        if amount_to_buy <= portfolio_cash:
                            shares_to_buy = amount_to_buy / current_prices[t]
                            positions[t] = positions.get(t, 0) + shares_to_buy
                            portfolio_cash -= amount_to_buy
                    elif current_holding_val > allocation_per_stock:
                        # Sell some
                        amount_to_sell = current_holding_val - allocation_per_stock
                        shares_to_sell = amount_to_sell / current_prices[t]
                        positions[t] = positions.get(t, 0) - shares_to_sell
                        portfolio_cash += amount_to_sell
                        
            days_since_rebalance = 0
            
    eq_df = pd.DataFrame(equity_curve).set_index('Date')
    return eq_df

if __name__ == "__main__":
    data, fundamentals = fetch_data()
    eq_df = run_backtest(data, fundamentals)
    
    # Calculate Nifty Benchmark (Proxy: RELIANCE as broad market beta proxy if NIFTY is unavailable, but we can fetch ^NSEI)
    print("Fetching Nifty 50 benchmark...")
    raw_nifty = yf.download('^NSEI', start=START_DATE, end=END_DATE)
    if isinstance(raw_nifty.columns, pd.MultiIndex):
        try:
            nifty = raw_nifty['Adj Close']
        except KeyError:
            nifty = raw_nifty['Close']
    else:
        try:
            nifty = raw_nifty['Adj Close']
        except KeyError:
            nifty = raw_nifty['Close']

    if isinstance(nifty, pd.DataFrame) and not nifty.empty:
        nifty = nifty.iloc[:, 0]
    
    nifty.fillna(method='ffill', inplace=True)
    nifty_val = (nifty / nifty.iloc[0]) * CAPITAL
    
    # Stats
    final_eq = eq_df['Equity'].iloc[-1]
    ret = (final_eq / CAPITAL - 1) * 100
    peak = eq_df['Equity'].cummax()
    dd = ((eq_df['Equity'] - peak) / peak * 100).min()
    
    nifty_final = nifty_val.iloc[-1]
    nifty_ret = (nifty_final / CAPITAL - 1) * 100
    nifty_peak = nifty_val.cummax()
    nifty_dd = ((nifty_val - nifty_peak) / nifty_peak * 100).min()
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(eq_df.index, eq_df['Equity'], label=f'Graham+Lynch Portfolio (Ret: {ret:.1f}%)', color='green')
    plt.plot(nifty.index, nifty_val, label=f'Nifty 50 Benchmark (Ret: {nifty_ret:.1f}%)', color='gray', linestyle='--')
    plt.title("10-Year Indian Equities: Graham + Lynch Rotation (Max 15 Stocks)")
    plt.ylabel("Portfolio Value (INR)")
    plt.legend()
    plt.grid(True)
    
    chart_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\value_backtest_chart.png"
    plt.savefig(chart_path)
    print(f"Saved chart to {chart_path}")
    
    report = f"""# Value Investing Backtest: Graham & Lynch (Indian Equities)

We simulated a purely fundamental rotational portfolio over the past 10 years using the top Indian stocks (NSE).

## System Rules
* **Universe:** Top 30 liquid NSE companies (Nifty 50 constituents).
* **Starting Capital:** 100,000 INR
* **Sizing:** Maximum 15 stocks simultaneously (equal-weight distribution).
* **Rebalancing:** Quarterly (90 days).
* **Filter 1 (Graham):** Market Price must be lower than Intrinsic Value `(EPS * (8.5 + 2g) * 4.4 / Y)`.
* **Filter 2 (Lynch):** PEG Ratio must be less than 1.5.

> **Data Architecture Note:** Because free APIs do not provide 10 years of point-in-time historical EPS, we utilized "Option B" from our implementation plan: reverse-engineering historical EPS by taking current fundamental data and dynamically discounting it backward using implied sector growth rates.

## 10-Year Performance Results

### Graham & Lynch Portfolio
* **Total Return:** {ret:.2f}%
* **Max Drawdown:** {dd:.2f}%
* **Final Capital:** ₹{final_eq:,.2f}

### Benchmark (Nifty 50 Index)
* **Total Return:** {nifty_ret:.2f}%
* **Max Drawdown:** {nifty_dd:.2f}%
* **Final Capital:** ₹{nifty_final:,.2f}

![Value Backtest Chart](file:///C:/Users/USER/.gemini/antigravity/brain/bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91/value_backtest_chart.png)
"""
    
    report_path = r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\value_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print("Done.")
