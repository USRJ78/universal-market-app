# swarm_bot_engine.py
import os
import sys
import time
import json
import random
import traceback
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Resolve paths relative to this script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "swarm_state.json")
LOG_FILE = os.path.join(BASE_DIR, "swarm_bot.log")

ASSETS = {
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"],
    "Stocks": ["AAPL", "MSFT", "TSLA", "NVDA"],
    "Bonds": ["TLT", "IEF", "SHY"],
    "Indices": ["^GSPC", "^IXIC"]
}

ALL_TICKERS = [t for cat in ASSETS.values() for t in cat]

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "is_running": False,
        "starting": False,
        "pid": None,
        "num_bots": 5000,
        "anomalies": [],
        "stats": {
            "total_scans": 0,
            "anomalies_detected": 0,
            "active_bugs": 0
        },
        "last_update": datetime.now().isoformat()
    }

def save_state(state):
    state["last_update"] = datetime.now().isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        log_message(f"Error saving state file: {e}")

def compute_indicators(df, rsi_period=14, ema_fast=5, ema_slow=15, bb_period=20, channel_period=20):
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    
    # EMAs
    df["EMA_fast"] = close.ewm(span=ema_fast, adjust=False).mean()
    df["EMA_slow"] = close.ewm(span=ema_slow, adjust=False).mean()
    df["EMA_fast_prev"] = df["EMA_fast"].shift(1)
    df["EMA_slow_prev"] = df["EMA_slow"].shift(1)
    
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    rolling_mean = close.rolling(bb_period).mean()
    rolling_std = close.rolling(bb_period).std()
    df["BB_upper"] = rolling_mean + 2 * rolling_std
    df["BB_lower"] = rolling_mean - 2 * rolling_std
    
    # Channel boundary
    df["High_chan"] = high.rolling(channel_period).max().shift(1)
    df["Low_chan"] = low.rolling(channel_period).min().shift(1)
    
    # Z-Score
    df["Zscore"] = (close - rolling_mean) / (rolling_std + 1e-9)
    
    return df

def fetch_asset_data(ticker):
    try:
        # Download last 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return ticker, df
    except Exception as e:
        log_message(f"Error fetching data for {ticker}: {e}")
    return ticker, None

def evaluate_bug_rules(ticker, df, num_bugs_for_asset):
    if df is None or len(df) < 22:
        return []
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close = float(last_row["Close"])
    open_p = float(last_row["Open"])
    high = float(last_row["High"])
    low = float(last_row["Low"])
    
    close_prev = float(prev_row["Close"])
    open_prev = float(prev_row["Open"])
    
    anomalies = []
    
    # We will simulate evaluation of 'num_bugs_for_asset' bugs
    # Each bug has slightly different indicators and parameters
    for bug_idx in range(num_bugs_for_asset):
        bug_id = f"Bug #{random.randint(100000, 999999)}"
        
        # Vary technical indicator parameters slightly based on bug index to simulate "different variables"
        rsi_var = 12 + (bug_idx % 5) # RSI period 12 to 16
        ema_f_var = 4 + (bug_idx % 3) # EMA fast 4 to 6
        ema_s_var = 14 + (bug_idx % 4) # EMA slow 14 to 17
        
        df_var = compute_indicators(df, rsi_period=rsi_var, ema_fast=ema_f_var, ema_slow=ema_s_var)
        v_row = df_var.iloc[-1]
        v_row_prev = df_var.iloc[-2]
        
        rsi = float(v_row["RSI"])
        ema_f = float(v_row["EMA_fast"])
        ema_s = float(v_row["EMA_slow"])
        ema_f_prev = float(v_row_prev["EMA_fast"])
        ema_s_prev = float(v_row_prev["EMA_slow"])
        bb_up = float(v_row["BB_upper"])
        bb_low = float(v_row["BB_lower"])
        chan_up = float(v_row["High_chan"])
        chan_low = float(v_row["Low_chan"])
        zscore = float(v_row["Zscore"])
        
        # Check rule variants
        triggered = False
        desc = ""
        direction = "ALERT"
        strength = 0.0
        
        rule_type = bug_idx % 8
        if rule_type == 0: # RSI Oversold check
            if rsi < 30:
                triggered = True
                desc = f"RSI-{rsi_var} Oversold Level ({rsi:.1f})"
                direction = "BUY"
                strength = 30.0 - rsi
        elif rule_type == 1: # RSI Overbought check
            if rsi > 70:
                triggered = True
                desc = f"RSI-{rsi_var} Overbought Level ({rsi:.1f})"
                direction = "SELL"
                strength = rsi - 70.0
        elif rule_type == 2: # Golden Cross
            if ema_f > ema_s and ema_f_prev <= ema_s_prev:
                triggered = True
                desc = f"Golden Crossover EMA-{ema_f_var}/{ema_s_var}"
                direction = "BUY"
                strength = abs(ema_f - ema_s) / close * 100.0
        elif rule_type == 3: # Death Cross
            if ema_f < ema_s and ema_f_prev >= ema_s_prev:
                triggered = True
                desc = f"Death Crossover EMA-{ema_f_var}/{ema_s_var}"
                direction = "SELL"
                strength = abs(ema_s - ema_f) / close * 100.0
        elif rule_type == 4: # Bollinger Upper Band Breakout
            if close >= bb_up:
                triggered = True
                desc = f"Bollinger Upper Band Breakout Z={zscore:.2f}"
                direction = "SELL"
                strength = zscore
        elif rule_type == 5: # Bollinger Lower Band Breakout
            if close <= bb_low:
                triggered = True
                desc = f"Bollinger Lower Band Breakout Z={zscore:.2f}"
                direction = "BUY"
                strength = abs(zscore)
        elif rule_type == 6: # Channel High breakout
            if close >= chan_up:
                triggered = True
                desc = "20-Period Channel Ceiling Breakout"
                direction = "BUY"
                strength = (close - chan_up) / chan_up * 100.0
        elif rule_type == 7: # Bullish/Bearish Engulfing
            is_bull_eng = (close > open_p) and (close_prev < open_prev) and (close >= open_prev) and (open_p <= close_prev)
            is_bear_eng = (close < open_p) and (close_prev > open_prev) and (close <= open_prev) and (open_p >= close_prev)
            if is_bull_eng:
                triggered = True
                desc = "Bullish Engulfing Candle Reversal"
                direction = "BUY"
                strength = (close - open_p) / open_p * 100.0
            elif is_bear_eng:
                triggered = True
                desc = "Bearish Engulfing Candle Reversal"
                direction = "SELL"
                strength = (open_p - close) / open_p * 100.0
                
        if triggered:
            # We found a pattern!
            anomalies.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bug_id": bug_id,
                "asset": ticker,
                "pattern": desc,
                "direction": direction,
                "strength": round(float(strength), 4),
                "price": round(close, 4)
            })
            
    return anomalies

def run_swarm_engine():
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)
    
    log_message("==================================================")
    log_message(f"🐜 BOOTING SWARM PATTERN CRAWLER DAEMON (PID: {os.getpid()})")
    log_message("==================================================")
    
    while True:
        try:
            state = load_state()
            if not state.get("is_running", False):
                log_message("Stop signal received. Shutting down swarm daemon.")
                break
                
            num_bots = state.get("num_bots", 5000)
            log_message(f"Deploying swarm of {num_bots} bots across Stocks, Bonds, Crypto, and Index markets...")
            
            # Fetch data in parallel using thread executor
            fetched_data = {}
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = executor.map(fetch_asset_data, ALL_TICKERS)
                for ticker, df in results:
                    if df is not None:
                        fetched_data[ticker] = df
                        
            log_message(f"Sourced data for {len(fetched_data)}/{len(ALL_TICKERS)} assets. Beginning analysis...")
            
            # Evaluate bugs per asset
            num_assets = len(fetched_data)
            if num_assets == 0:
                log_message("⚠️ No assets loaded. Retrying in 10 seconds...")
                time.sleep(10)
                continue
                
            bugs_per_asset = num_bots // num_assets
            
            all_anomalies = []
            for ticker, df in fetched_data.items():
                anomalies = evaluate_bug_rules(ticker, df, bugs_per_asset)
                if anomalies:
                    all_anomalies.extend(anomalies)
                    log_message(f"  · {ticker}: Scanned by {bugs_per_asset} bots. Flagged {len(anomalies)} pattern signals.")
                    
            # Sort anomalies by strength
            all_anomalies.sort(key=lambda x: x["strength"], reverse=True)
            
            # Keep top 100 anomalies in state to prevent bloating
            top_anomalies = all_anomalies[:100]
            
            # Update state stats
            state = load_state()
            state["anomalies"] = top_anomalies
            state["stats"]["total_scans"] += 1
            state["stats"]["anomalies_detected"] += len(all_anomalies)
            state["stats"]["active_bugs"] = num_bots
            save_state(state)
            
            log_message(f"Swarm cycle completed. Total Anomalies Detected: {len(all_anomalies)} (Top 100 serialized).")
            log_message("Sleeping 30 seconds for next swarm scan...")
            
            if not sleep_checking_stop(30):
                break
                
        except Exception as e:
            log_message(f"⚠️ Error in swarm daemon loop: {e}")
            traceback.print_exc()
            time.sleep(10)
            
    state = load_state()
    state["is_running"] = False
    state["pid"] = None
    state["starting"] = False
    save_state(state)
    log_message("Swarm daemon stopped.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--start", "--daemon"]:
        state = load_state()
        state["is_running"] = True
        save_state(state)
        
    state = load_state()
    if state.get("is_running", False):
        try:
            run_swarm_engine()
        except KeyboardInterrupt:
            log_message("Swarm engine stopped manually.")
        finally:
            state = load_state()
            state["is_running"] = False
            state["pid"] = None
            state["starting"] = False
            save_state(state)
