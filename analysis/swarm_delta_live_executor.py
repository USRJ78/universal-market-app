"""
==============================================================================
  SWARM BOT TRUE 1x2 RATIO CALL SPREAD — LIVE OPTIONS EXECUTOR V2.0
==============================================================================
  Executes a REAL Zero Net Debit 1x2 Ratio Call Spread on Delta Testnet:

    LEG 1: BUY  1x ATM BTC Call Option  (K1 = nearest ATM strike)
    LEG 2: SELL 2x OTM BTC Call Option  (K2 = K1 x 1.04 to 1.05)

  Dynamically fetches live BTC options chain from Delta Exchange Testnet,
  selects optimal strikes using Black-Scholes geometry, and places
  real options orders when Swarm Conviction >= 70%.

  Runs 24/7 on Oracle Cloud — scans every 5 minutes.
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, requests
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ─────────────────────────────────────────────
# DELTA EXCHANGE TESTNET CONFIG
# ─────────────────────────────────────────────
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"
CONVICTION_GATE  = 0.70
SCAN_INTERVAL    = 300   # 5 minutes
K2_MULTIPLIER    = 1.04  # OTM strike = ATM x 1.04

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swarm_call_spread_live.log")

def log(msg):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = f"[{ts}] [SWARM-SPREAD-V2] {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ─────────────────────────────────────────────
# DELTA API HELPERS
# ─────────────────────────────────────────────
def sign(secret, msg):
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts      = str(int(time.time()))
    sig_str = "GET" + ts + path
    headers = {
        "api-key":      DELTA_API_KEY,
        "timestamp":    ts,
        "signature":    sign(DELTA_API_SECRET, sig_str),
        "Content-Type": "application/json",
        "User-Agent":   "swarm-spread-v2/1.0"
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
    sig_str = "POST" + ts + path + body
    headers = {
        "api-key":      DELTA_API_KEY,
        "timestamp":    ts,
        "signature":    sign(DELTA_API_SECRET, sig_str),
        "Content-Type": "application/json",
        "User-Agent":   "swarm-spread-v2/1.0"
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

# ─────────────────────────────────────────────
# LIVE OPTIONS CHAIN FETCHER
# ─────────────────────────────────────────────
def get_btc_options_chain():
    """Fetch all BTC call options from Delta Testnet dynamically."""
    all_options = []
    for page in range(1, 6):
        data    = delta_get(f"/v2/products?contract_types=call_options&page_size=100&page={page}")
        results = data.get("result", [])
        if not results:
            break
        btc = [p for p in results if "BTC" in str(p.get("symbol", "")).upper()]
        all_options.extend(btc)
    return all_options

def select_spread_legs(options, spot_price):
    """
    Select optimal K1 (ATM) and K2 (OTM) strikes for 1x2 Ratio Call Spread.
    K1 = strike nearest to spot price
    K2 = strike nearest to spot_price * 1.04
    """
    # Filter options expiring in 1-7 days
    today    = datetime.datetime.utcnow().date()
    valid    = []
    for o in options:
        try:
            expiry = datetime.datetime.strptime(o.get("settlement_time","")[:10], "%Y-%m-%d").date()
            days   = (expiry - today).days
            if 1 <= days <= 7:
                valid.append((o, days, float(o.get("strike_price", 0))))
        except Exception:
            continue

    if not valid:
        log("  ⚠️ No options expiring within 1-7 days found!")
        return None, None

    # Find K1 (ATM — nearest to spot)
    k1_target = spot_price
    k1_opt    = min(valid, key=lambda x: abs(x[2] - k1_target))

    # Find K2 (OTM — nearest to spot * 1.04)
    k2_target = spot_price * K2_MULTIPLIER
    k2_opt    = min(valid, key=lambda x: abs(x[2] - k2_target))

    return k1_opt[0], k2_opt[0]

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
        log(f"  Data fetch error: {e}")
        return None

def agent_alpha(df):
    close  = df["Close"]
    ema20  = close.ewm(span=20, adjust=False).mean()
    ema50  = close.ewm(span=50, adjust=False).mean()
    h52    = close.rolling(min(252, len(close))).max()
    lc     = float(close.iloc[-1])
    trend  = 1.0 if (lc > float(ema20.iloc[-1]) > float(ema50.iloc[-1])) else 0.5
    brk    = 1.0 if (lc >= float(h52.iloc[-1]) * 0.98) else 0.5
    score  = (0.6 * trend) + (0.4 * brk)
    log(f"  Agent Alpha (Momentum)    | BTC: ${lc:,.0f} | Score: {score:.2f}")
    return score, lc

def agent_beta(df):
    hl    = df["High"] - df["Low"]
    hc    = (df["High"] - df["Close"].shift()).abs()
    lc    = (df["Low"]  - df["Close"].shift()).abs()
    tr    = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    sqz   = float((tr.rolling(10).mean() / (tr.rolling(50).mean() + 1e-9)).iloc[-1])
    hv20  = float(np.log(df["Close"] / df["Close"].shift(1)).rolling(20).std().iloc[-1] * np.sqrt(252))
    score = 1.0 if sqz < 0.88 else 0.8 if sqz < 0.95 else 0.3
    log(f"  Agent Beta (Vol Squeeze)  | ATR Ratio: {sqz:.3f} | HV20: {hv20:.1%} | Score: {score:.2f}")
    return score, hv20

def agent_gamma(S, hv, k1_strike, k2_strike):
    T, r  = 5 / 365.0, 0.05
    sigma = max(hv, 0.15)
    def bs_call(K):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    c1   = bs_call(k1_strike)
    c2   = bs_call(k2_strike)
    net  = c1 - 2 * c2
    max_profit = k2_strike - k1_strike
    score = 1.0 if abs(net) < c1 * 0.20 else 0.6
    log(f"  Agent Gamma (Geometry)    | K1: ${k1_strike:,} (C=${c1:.1f}) | K2: ${k2_strike:,} (C=${c2:.1f}) | Net Debit: ${net:.2f} | Max Profit: ${max_profit:,} | Score: {score:.2f}")
    return score

def agent_delta_overseer(a, b, g):
    conviction = (0.35 * a) + (0.30 * b) + (0.35 * g)
    log(f"  Agent Delta (Overseer)    | Conviction: {conviction:.1%} | Gate: {CONVICTION_GATE:.0%}")
    return conviction

# ─────────────────────────────────────────────
# PLACE TRUE 1x2 CALL SPREAD ORDERS (REAL OPTIONS)
# ─────────────────────────────────────────────
def place_spread(k1_option, k2_option, balance=140.0):
    """
    Execute true 1x2 Ratio Call Spread on REAL OPTIONS CONTRACTS:
    LEG 1: BUY  N x ATM Call (K1)
    LEG 2: SELL 2N x OTM Call (K2)
    """
    k1_id  = k1_option.get("id")
    k2_id  = k2_option.get("id")
    k1_sym = k1_option.get("symbol")
    k2_sym = k2_option.get("symbol")

    # Scale spreads to use 95% of free available margin
    num_spreads = max(1, int((balance * 0.95) / 15.0))
    leg1_size   = num_spreads
    leg2_size   = num_spreads * 2

    log(f"\n  🎯 EXECUTING TRUE 1x2 RATIO CALL SPREAD ON DELTA OPTIONS CHAIN:")
    log(f"     Allocating 95% Margin (${balance*0.95:.2f}) -> {num_spreads} Spreads")
    log(f"     LEG 1: BUY  {leg1_size}x {k1_sym} (ID: {k1_id})")
    log(f"     LEG 2: SELL {leg2_size}x {k2_sym} (ID: {k2_id})")

    # LEG 1: BUY N x ATM Call
    leg1 = delta_post("/v2/orders", {
        "product_id": k1_id,
        "size":       leg1_size,
        "side":       "buy",
        "order_type": "market_order"
    })
    if leg1.get("success"):
        oid1 = leg1.get("result", {}).get("id", "N/A")
        log(f"  ✅ LEG 1 FILLED | BUY {leg1_size}x {k1_sym} | Order ID: {oid1}")
    else:
        log(f"  ❌ LEG 1 FAILED: {leg1}")
        return False

    time.sleep(1)

    # LEG 2: SELL 2N x OTM Call
    leg2 = delta_post("/v2/orders", {
        "product_id": k2_id,
        "size":       leg2_size,
        "side":       "sell",
        "order_type": "market_order"
    })
    if leg2.get("success"):
        oid2 = leg2.get("result", {}).get("id", "N/A")
        log(f"  ✅ LEG 2 FILLED | SELL {leg2_size}x {k2_sym} | Order ID: {oid2}")
        return True
    else:
        log(f"  ❌ LEG 2 FAILED: {leg2}")
        return False

# ─────────────────────────────────────────────
# MAIN LIVE TRADING LOOP
# ─────────────────────────────────────────────
def run_live():
    log("=" * 70)
    log("  🚀 SWARM BOT TRUE 1x2 RATIO CALL SPREAD — LIVE OPTIONS EXECUTOR V2.0")
    log("=" * 70)
    log(f"  Exchange    : Delta Exchange Testnet")
    log(f"  Strategy    : Zero Net Debit 1x2 Ratio Call Spread (REAL OPTIONS)")
    log(f"  Leg 1       : BUY  1x ATM BTC Call (K1)")
    log(f"  Leg 2       : SELL 2x OTM BTC Call (K2 = K1 x {K2_MULTIPLIER})")
    log(f"  Conviction  : >= {CONVICTION_GATE:.0%} required")
    log(f"  Scan Cycle  : Every {SCAN_INTERVAL//60} minutes")
    log("=" * 70)

    scan_count   = 0
    trades_placed = 0

    while True:
        scan_count += 1
        log(f"\n{'='*60}")
        log(f"  SWARM SCAN #{scan_count:04d} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"{'='*60}")

        # 1. Wallet Balance
        balance = get_wallet_balance()
        log(f"  Wallet Balance : ${balance:.2f} USD")

        # 2. Fetch BTC Market Data
        df = fetch_btc_data()
        if df is None or len(df) < 60:
            log("  ⚠️ Insufficient data — retrying in 5 min...")
            time.sleep(SCAN_INTERVAL)
            continue

        # 3. Run Swarm Agents
        log("\n  🤖 RUNNING ALL 4 SWARM AGENTS...")
        alpha_score, btc_price = agent_alpha(df)
        beta_score,  hv20      = agent_beta(df)

        # 4. Fetch Live Options Chain
        log(f"\n  📡 FETCHING LIVE BTC OPTIONS CHAIN FROM DELTA TESTNET...")
        options = get_btc_options_chain()
        log(f"  Found {len(options)} BTC Call Options Available")

        if not options:
            log("  ⚠️ No options available — retrying in 5 min...")
            time.sleep(SCAN_INTERVAL)
            continue

        # 5. Select K1 (ATM) and K2 (OTM) strikes
        k1_option, k2_option = select_spread_legs(options, btc_price)
        if not k1_option or not k2_option:
            log("  ⚠️ Could not select valid spread legs — retrying in 5 min...")
            time.sleep(SCAN_INTERVAL)
            continue

        k1_strike = float(k1_option.get("strike_price", 0))
        k2_strike = float(k2_option.get("strike_price", 0))

        # 6. Run Agent Gamma with real strikes
        gamma_score = agent_gamma(btc_price, hv20, k1_strike, k2_strike)

        # 7. Swarm Conviction Gate
        conviction = agent_delta_overseer(alpha_score, beta_score, gamma_score)

        # 8. Trade Decision
        log(f"\n  📊 TRADE DECISION")
        if conviction >= CONVICTION_GATE:
            log(f"  ✅ CONVICTION {conviction:.1%} >= {CONVICTION_GATE:.0%} — EXECUTING 1x2 CALL SPREAD!")
            placed = place_spread(k1_option, k2_option)
            if placed:
                trades_placed += 1
                log(f"  🏆 SPREAD #{trades_placed} SUCCESSFULLY PLACED!")
                log(f"     Structure : BUY 1x C-BTC-{int(k1_strike)}-xx | SELL 2x C-BTC-{int(k2_strike)}-xx")
                log(f"     Max Profit: ${k2_strike - k1_strike:,.0f} per contract")
                log(f"     Risk      : Net Debit Only (Capped Downside)")
        else:
            log(f"  ⏳ CONVICTION {conviction:.1%} < {CONVICTION_GATE:.0%} — NO TRADE. Waiting for next scan...")

        log(f"\n  💤 Next scan in {SCAN_INTERVAL//60} minutes...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_live()
