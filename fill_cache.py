import pandas as pd
import numpy as np
import yfinance as yf
from yahooquery import Ticker
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import os
import time

warnings.filterwarnings('ignore')

START_DATE = (datetime.now() - timedelta(days=10*365)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')
CAPITAL = 100000.0
MAX_POSITIONS = 15
AAA_YIELD = 7.5

CACHE_DIR = 'cache_gl'

def fetch_nse_universe():
    print("Fetching active NSE equities...")
    df = pd.read_csv('https://archives.nseindia.com/content/equities/EQUITY_L.csv')
    tickers = [str(sym) + '.NS' for sym in df['SYMBOL']]
    return tickers

def get_missing_data():
    tickers = fetch_nse_universe()
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    cached_files = os.listdir(CACHE_DIR)
    cached_tickers = [f.replace('_NS.pkl', '.NS') for f in cached_files if f.endswith('.pkl')]
    
    missing_tickers = list(set(tickers) - set(cached_tickers))
    print(f"Total Tickers: {len(tickers)}")
    print(f"Already Cached: {len(cached_tickers)}")
    print(f"Missing Tickers to Fetch: {len(missing_tickers)}")
    
    if len(missing_tickers) > 0:
        print("Fetching missing fundamentals using yahooquery (Bypassing yfinance block)...")
        # Split into chunks of 100 to avoid huge URI
        for i in range(0, len(missing_tickers), 100):
            chunk = missing_tickers[i:i+100]
            try:
                yq_ticker = Ticker(" ".join(chunk))
                stats = yq_ticker.key_stats
                
                prices = yf.download(chunk, start=START_DATE, end=END_DATE, threads=True)
                if isinstance(prices.columns, pd.MultiIndex):
                    prices = prices.get('Adj Close', prices.get('Close'))
                else:
                    prices = prices.to_frame() if isinstance(prices, pd.Series) else prices
                    
                prices.fillna(method='ffill', inplace=True)
                
                for t in chunk:
                    try:
                        if t not in prices.columns: continue
                        df = prices[[t]].copy()
                        df.columns = ['Close']
                        if df['Close'].isna().all(): continue
                        
                        eps = None
                        peg = None
                        
                        if isinstance(stats, dict) and t in stats and isinstance(stats[t], dict):
                            t_stats = stats[t]
                            eps = t_stats.get('trailingEps', None)
                            peg = t_stats.get('pegRatio', None)
                            
                        # Fallback calculation
                        if eps is None or eps <= 0:
                            p = df['Close'].iloc[-1]
                            if not pd.isna(p) and p > 0:
                                eps = p / 20.0
                        if peg is None or peg <= 0:
                            peg = 1.2
                            
                        p = df['Close'].iloc[-1]
                        if not pd.isna(p) and p > 0 and eps > 0:
                            pe = p / eps
                            g = pe / peg
                            g = max(5.0, min(25.0, g))
                        else:
                            g = 10.0
                            eps = 1.0
                            
                        df['EPS'] = eps
                        df['GrowthPct'] = g
                        df['GrahamValue'] = eps * (8.5 + 2 * g) * 4.4 / AAA_YIELD
                        df['MarketCapCr'] = 1000 # Dummy for now
                        
                        safe_name = t.replace('.', '_')
                        df.to_pickle(os.path.join(CACHE_DIR, f"{safe_name}.pkl"))
                        
                    except Exception as e:
                        pass
                        
            except Exception as e:
                print(f"Error fetching chunk: {e}")
            time.sleep(1)
            
get_missing_data()
