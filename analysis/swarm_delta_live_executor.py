"""
==============================================================================
  SWARM BOT 1x2 RATIO CALL SPREAD — LIVE DELTA TESTNET EXECUTOR
==============================================================================
  Connects the Swarm Bot signal engine to Delta Exchange Testnet
  and executes BTC perpetual futures trades based on:
    - Agent Alpha (Momentum Conviction >= 70%)
    - Agent Beta  (Volatility Squeeze Confirmed)
    - Agent Gamma (Zero Net Debit Spread Geometry)
    - Agent Delta (Swarm Overseer — Final Risk Gate)

  Runs continuously 24/7 on Oracle Cloud.
  Checks for signals every 5 minutes.
  Places live orders on Delta Exchange Testnet when conviction >= 70%.
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, requests
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

# ─────────────────────────────────────────────
# DELTA EXCHANGE TESTNET CONFIG
# ─────────────────────────────────────────────
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"
PRODUCT_ID       = 84   # BTC Perpetual Futures on Delta Testnet
ORDER_SIZE       = 1    # 1 contract per signal (risk-controlled)
CONVICTION_GATE  = 0.70 # Minimum 70% swarm conviction to trade

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swarm_delta_live.log")

def log(msg):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = f"[{ts}] [SWARM-DELTA-LIVE] {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ─────────────────────────────────────────────
# DELTA EXCHANGE AUTHENTICATION
# ─────────────────────────────────────────────
def sign(secret, msg):
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts      = str(int(time.time()))
    sig_str = f"GET{ts}{path}"
    headers = {
        "api-key":   DELTA_API_KEY,
        "timestamp": ts,
        "signature": sign(DELTA_API_SECRET, sig_str),
        "Content-Type": "application/json",
        "User-Agent": "swarm-delta-live/1.0"
    }
    try:
        r = requests.get(DELTA_BASE_URL + path, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        log(f"GET ERROR: {e}")
        return {}

def delta_post(path, payload):
    ts      = str(int(time.time()))
    body    = json.dumps(payload)
    sig_str = f"POST{ts}{path}{body}"
    headers = {
        "api-key":   DELTA_API_KEY,
        "timestamp": ts,
        "signature": sign(DELTA_API_SECRET, sig_str),
        "Content-Type": "application/json",
        "User-Agent": "swarm-delta-live/1.0"
    }
    try:
        r = requests.post(DELTA_BASE_URL + path, data=body, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        log(f"POST ERROR: {e}")
        return {}

def get_wallet_balance():
    data = delta_get("/v2/wallet/balances")
    try:
        for b in data.get("result", []):
            if b.get("asset_symbol") in ["USDT", "USD"]:
                return float(b.get("available_balance", 0))
    except Exception:
        pass
    return 0.0

def place_order(side, size, reason):
    payload = {
        "product_id": PRODUCT_ID,
        "size":       size,
        "side":       side,
        "order_type": "market_order"
    }
    res = delta_post("/v2/orders", payload)
    if res.get("success"):
        oid = res.get("result", {}).get("id", "N/A")
        log(f"✅ ORDER PLACED | Side: {side.upper()} | Size: {size} | Order ID: {oid} | Reason: {reason}")
        return True
    else:
        log(f"❌ ORDER FAILED | Response: {res}")
        return False

# ─────────────────────────────────────────────
# SWARM AGENT SIGNALS
# ─────────────────────────────────────────────
def fetch_btc_data():
    try:
        df = yf.download("BTC-USD", period="6mo", interval="1d", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
        return df
    except Exception as e:
        log(f"Data fetch error: {e}")
        return None

def agent_alpha_momentum(df):
    """Agent Alpha: 52-Week Momentum & EMA Trend"""
    close  = df["Close"]
    ema20  = close.ewm(span=20, adjust=False).mean()
    ema50  = close.ewm(span=50, adjust=False).mean()
    h52    = close.rolling(min(252, len(close))).max()
    last_c = float(close.iloc[-1])
    last_20= float(ema20.iloc[-1])
    last_50= float(ema50.iloc[-1])
    last_h = float(h52.iloc[-1])
    trend  = 1.0 if (last_c > last_20 > last_50) else 0.5 if (last_c > last_50) else 0.0
    brk    = 1.0 if (last_c >= last_h * 0.98) else 0.5
    score  = (0.6 * trend) + (0.4 * brk)
    log(f"  Agent Alpha | Price: ${last_c:,.0f} | EMA20: ${last_20:,.0f} | 52W-High: ${last_h:,.0f} | Score: {score:.2f}")
    return score, last_c

def agent_beta_volatility(df):
    """Agent Beta: ATR Volatility Squeeze"""
    hl  = df["High"] - df["Low"]
    hc  = (df["High"] - df["Close"].shift()).abs()
    lc  = (df["Low"]  - df["Close"].shift()).abs()
    tr  = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr10 = tr.rolling(10).mean()
    atr50 = tr.rolling(50).mean()
    sqz   = float((atr10 / (atr50 + 1e-9)).iloc[-1])
    hv20  = float(np.log(df["Close"] / df["Close"].shift(1)).rolling(20).std().iloc[-1] * np.sqrt(252))
    score = 1.0 if sqz < 0.88 else 0.8 if sqz < 0.95 else 0.3
    log(f"  Agent Beta  | ATR Ratio: {sqz:.3f} | HV20: {hv20:.1%} | Score: {score:.2f}")
    return score, hv20

def agent_gamma_geometry(S, hv):
    """Agent Gamma: Zero Net Debit 1x2 Spread Geometry"""
    T  = 30 / 365.0
    r  = 0.05
    sigma = max(hv, 0.15)

    def bs_call(K):
        if T <= 0 or sigma <= 0: return max(S - K, 0)
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))

    k1  = round(S / 100) * 100
    c1  = bs_call(k1)
    k2  = k1
    best_diff = 999999
    for step in range(1, 30):
        candidate = k1 + step * 100
        c2 = bs_call(candidate)
        net_debit = c1 - 2 * c2
        if abs(net_debit) < abs(best_diff):
            best_diff = net_debit
            k2 = candidate
    max_profit = k2 - k1
    score = 1.0 if abs(best_diff) < c1 * 0.15 else 0.6
    log(f"  Agent Gamma | K1 (ATM): ${k1:,} | K2 (OTM): ${k2:,} | Net Debit: ${best_diff:.2f} | Max Profit: ${max_profit:,} | Score: {score:.2f}")
    return score

def agent_delta_overseer(a, b, g):
    """Agent Delta: Swarm Conviction Aggregator"""
    conviction = (0.35 * a) + (0.30 * b) + (0.35 * g)
    log(f"  Agent Delta | Conviction Score: {conviction:.1%} | Gate: {CONVICTION_GATE:.0%}")
    return conviction

# ─────────────────────────────────────────────
# MAIN LIVE TRADING LOOP
# ─────────────────────────────────────────────
def run_live():
    log("=" * 70)
    log("  🚀 SWARM BOT 1x2 RATIO CALL SPREAD — LIVE DELTA TESTNET EXECUTOR")
    log("=" * 70)
    log(f"  Exchange     : Delta Exchange Testnet")
    log(f"  Strategy     : Zero Net Debit 1x2 Ratio Call Spread")
    log(f"  Conviction   : >= {CONVICTION_GATE:.0%} required to trade")
    log(f"  Scan Interval: Every 5 minutes")
    log("=" * 70)

    scan_count = 0
    trades_placed = 0

    while True:
        scan_count += 1
        log(f"\n{'='*60}")
        log(f"  SWARM SCAN #{scan_count:04d} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
        log(f"{'='*60}")

        # 1. Get wallet balance
        balance = get_wallet_balance()
        log(f"  Wallet Balance : ${balance:.2f} USD")

        # 2. Fetch BTC data
        df = fetch_btc_data()
        if df is None or len(df) < 60:
            log("  ⚠️ Insufficient data — retrying in 5 minutes...")
            time.sleep(300)
            continue

        # 3. Run all 4 Swarm Agents
        log("\n  🤖 RUNNING SWARM AGENTS...")
        alpha_score, btc_price = agent_alpha_momentum(df)
        beta_score,  hv20      = agent_beta_volatility(df)
        gamma_score            = agent_gamma_geometry(btc_price, hv20)
        conviction             = agent_delta_overseer(alpha_score, beta_score, gamma_score)

        # 4. Trade Decision
        log(f"\n  📊 TRADE DECISION")
        if conviction >= CONVICTION_GATE:
            log(f"  ✅ CONVICTION {conviction:.1%} >= {CONVICTION_GATE:.0%} — PLACING BUY ORDER!")
            side = "buy"
            placed = place_order(side, ORDER_SIZE, f"Swarm Conviction {conviction:.1%}")
            if placed:
                trades_placed += 1
                log(f"  📈 Total Trades Placed This Session: {trades_placed}")
        else:
            log(f"  ⏳ CONVICTION {conviction:.1%} < {CONVICTION_GATE:.0%} — NO TRADE. Waiting for next scan...")

        log(f"\n  💤 Next scan in 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    run_live()
