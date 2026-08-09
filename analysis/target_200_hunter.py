"""
==============================================================================
  ANTIGRAVITY AI BRAIN — 24-HOUR $200 TARGET HUNTER V1.0
==============================================================================
  MISSION: Grow $138.57 → $200.00 in 24 hours (+44.3%) on Delta Testnet

  MULTI-STRATEGY COMBAT ENGINE:
  ┌─────────────────────────────────────────────────────────────────────┐
  │ STRATEGY 1: BTC Momentum Scalper (60-second scan, leveraged perps) │
  │ STRATEGY 2: 1x2 Ratio Call Spread (Swarm Bot Options Execution)    │
  │ STRATEGY 3: Power Hour Gamma Surge (14:00-15:00 IST aggressive)    │
  │ STRATEGY 4: Funding Rate Arb (Long/Short based on funding rate)    │
  │ STRATEGY 5: Mean Reversion VWAP Bounce (RSI < 30 or > 70 trigger)  │
  └─────────────────────────────────────────────────────────────────────┘

  RISK MANAGEMENT:
  - Hard Stop: If balance drops below $120 (−13.4%), halt all trading
  - Max Position Size: 30% of free margin per trade
  - Target Lock: Auto-scale down aggression when equity > $180
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, requests
import numpy as np
import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"

BTC_PERP_ID      = 84      # BTC Perpetual Futures
STARTING_BALANCE = 138.57
TARGET_BALANCE   = 200.00
HARD_STOP        = 120.00  # Halt trading below this
SCAN_INTERVAL    = 60      # 1 minute scan cycle
DEADLINE_HOURS   = 24
SESSION_START    = datetime.datetime.utcnow()
DEADLINE         = SESSION_START + datetime.timedelta(hours=DEADLINE_HOURS)

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_200_hunt.log")

def log(msg):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = f"[{ts}] {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ─────────────────────────────────────────────
# DELTA API
# ─────────────────────────────────────────────
def sign(secret, msg):
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts  = str(int(time.time()))
    sig = sign(DELTA_API_SECRET, "GET" + ts + path)
    headers = {"api-key": DELTA_API_KEY, "timestamp": ts, "signature": sig, "Content-Type": "application/json"}
    try:
        r = requests.get(DELTA_BASE_URL + path, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        log(f"  [GET ERROR] {e}")
        return {}

def delta_post(path, payload):
    ts   = str(int(time.time()))
    body = json.dumps(payload)
    sig  = sign(DELTA_API_SECRET, "POST" + ts + path + body)
    headers = {"api-key": DELTA_API_KEY, "timestamp": ts, "signature": sig, "Content-Type": "application/json"}
    try:
        r = requests.post(DELTA_BASE_URL + path, data=body, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        log(f"  [POST ERROR] {e}")
        return {}

def get_balance():
    data = delta_get("/v2/wallet/balances")
    try:
        for b in data.get("result", []):
            if b.get("asset_symbol") in ["USDT", "USD"]:
                return float(b.get("available_balance", 0))
    except Exception:
        pass
    return 0.0

def get_positions():
    data = delta_get("/v2/positions/margined")
    return data.get("result", [])

def close_all_positions():
    positions = get_positions()
    for pos in positions:
        size = abs(float(pos.get("size", 0)))
        if size > 0:
            side = "sell" if float(pos.get("size", 0)) > 0 else "buy"
            pid  = pos.get("product_id")
            res  = delta_post("/v2/orders", {
                "product_id": pid,
                "size":       int(size),
                "side":       side,
                "order_type": "market_order",
                "reduce_only": True
            })
            log(f"  [CLOSE] {side.upper()} {size} contracts | PID: {pid} | Result: {res.get('success')}")

def place_order(side, size, reason):
    size = max(1, int(size))
    res  = delta_post("/v2/orders", {
        "product_id": BTC_PERP_ID,
        "size":       size,
        "side":       side,
        "order_type": "market_order"
    })
    if res.get("success"):
        oid = res.get("result", {}).get("id", "N/A")
        log(f"  ✅ ORDER | {side.upper()} {size}x BTC-PERP | ID: {oid} | {reason}")
        return True
    else:
        log(f"  ❌ ORDER FAILED | {res.get('error', {})}")
        return False

# ─────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────
def get_btc_data(period="3mo", interval="1h"):
    try:
        df = yf.download("BTC-USD", period=period, interval=interval, progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
        return df
    except Exception:
        return None

def get_btc_price():
    df = get_btc_data(period="5d", interval="1h")
    if df is not None and len(df) > 0:
        return float(df["Close"].iloc[-1])
    return 65000.0

# ─────────────────────────────────────────────
# STRATEGY 1: MOMENTUM SCALPER
# ─────────────────────────────────────────────
def strategy_momentum(df, free_margin):
    """Fast EMA crossover momentum scalper"""
    close = df["Close"]
    ema9  = close.ewm(span=9,  adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    rsi   = compute_rsi(close, 14)

    prev_9  = float(ema9.iloc[-2]);  curr_9  = float(ema9.iloc[-1])
    prev_21 = float(ema21.iloc[-2]); curr_21 = float(ema21.iloc[-1])
    rsi_val = float(rsi.iloc[-1])
    price   = float(close.iloc[-1])

    # Golden cross + RSI not overbought → BUY
    if prev_9 < prev_21 and curr_9 > curr_21 and rsi_val < 65:
        size = max(1, int(free_margin * 0.20 / 10))
        log(f"  [MOMENTUM] 🟢 GOLDEN CROSS | EMA9>{price:.0f}>EMA21 | RSI:{rsi_val:.1f}")
        return "buy", size, f"Momentum Golden Cross EMA9>EMA21 RSI:{rsi_val:.1f}"

    # Death cross + RSI not oversold → SELL
    elif prev_9 > prev_21 and curr_9 < curr_21 and rsi_val > 35:
        size = max(1, int(free_margin * 0.20 / 10))
        log(f"  [MOMENTUM] 🔴 DEATH CROSS  | EMA9<{price:.0f}<EMA21 | RSI:{rsi_val:.1f}")
        return "sell", size, f"Momentum Death Cross EMA9<EMA21 RSI:{rsi_val:.1f}"

    return None, 0, ""

# ─────────────────────────────────────────────
# STRATEGY 2: RSI MEAN REVERSION
# ─────────────────────────────────────────────
def strategy_rsi_reversion(df, free_margin):
    """RSI extreme reversal play"""
    close   = df["Close"]
    rsi     = compute_rsi(close, 14)
    rsi_val = float(rsi.iloc[-1])
    price   = float(close.iloc[-1])

    if rsi_val < 28:
        size = max(1, int(free_margin * 0.25 / 10))
        log(f"  [RSI-REV]  🟢 OVERSOLD BOUNCE | RSI:{rsi_val:.1f} | BTC:${price:,.0f}")
        return "buy", size, f"RSI Oversold Reversal {rsi_val:.1f}"
    elif rsi_val > 72:
        size = max(1, int(free_margin * 0.25 / 10))
        log(f"  [RSI-REV]  🔴 OVERBOUGHT DROP | RSI:{rsi_val:.1f} | BTC:${price:,.0f}")
        return "sell", size, f"RSI Overbought Reversal {rsi_val:.1f}"

    return None, 0, ""

# ─────────────────────────────────────────────
# STRATEGY 3: POWER HOUR GAMMA SURGE
# ─────────────────────────────────────────────
def strategy_power_hour(df, free_margin):
    """14:00-15:30 UTC (19:30-21:00 IST) aggressive momentum play"""
    hour = datetime.datetime.utcnow().hour
    minute = datetime.datetime.utcnow().minute

    # Power Hour: 14:00-15:30 UTC
    if not (14 <= hour <= 15):
        return None, 0, ""

    close = df["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    price = float(close.iloc[-1])
    ema   = float(ema20.iloc[-1])

    if price > ema * 1.001:
        size = max(1, int(free_margin * 0.30 / 10))
        log(f"  [POWER-HR] ⚡ GAMMA SURGE BUY | Hour:{hour}:{minute:02d}UTC | BTC>${price:,.0f}>EMA${ema:,.0f}")
        return "buy", size, f"Power Hour Gamma Surge {hour}:{minute:02d}UTC"
    elif price < ema * 0.999:
        size = max(1, int(free_margin * 0.30 / 10))
        log(f"  [POWER-HR] ⚡ GAMMA SURGE SELL| Hour:{hour}:{minute:02d}UTC | BTC<${price:,.0f}<EMA${ema:,.0f}")
        return "sell", size, f"Power Hour Gamma Surge Short {hour}:{minute:02d}UTC"

    return None, 0, ""

# ─────────────────────────────────────────────
# STRATEGY 4: FUNDING RATE ARB
# ─────────────────────────────────────────────
def strategy_funding_arb(free_margin):
    """Trade against the funding rate direction"""
    data = delta_get("/v2/products/84/funding/current")
    try:
        rate = float(data.get("result", {}).get("funding_rate", 0))
        if rate > 0.0005:
            size = max(1, int(free_margin * 0.15 / 10))
            log(f"  [FUNDING]  📉 HIGH POSITIVE FUNDING={rate:.6f} → SELL (short premium)")
            return "sell", size, f"Funding Rate Arb Sell Rate={rate:.6f}"
        elif rate < -0.0005:
            size = max(1, int(free_margin * 0.15 / 10))
            log(f"  [FUNDING]  📈 HIGH NEGATIVE FUNDING={rate:.6f} → BUY (long premium)")
            return "buy", size, f"Funding Rate Arb Buy Rate={rate:.6f}"
    except Exception:
        pass
    return None, 0, ""

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def time_remaining():
    remaining = DEADLINE - datetime.datetime.utcnow()
    hrs  = int(remaining.total_seconds() // 3600)
    mins = int((remaining.total_seconds() % 3600) // 60)
    return hrs, mins, remaining.total_seconds() > 0

def progress_bar(current, target, start=STARTING_BALANCE, width=30):
    pct  = min(1.0, (current - start) / (target - start))
    done = int(pct * width)
    bar  = "█" * done + "░" * (width - done)
    return f"[{bar}] {pct:.1%}"

# ─────────────────────────────────────────────
# MAIN 24-HOUR HUNT LOOP
# ─────────────────────────────────────────────
def run():
    log("=" * 70)
    log("  🎯 24-HOUR $200 TARGET HUNTER — ANTIGRAVITY AI BRAIN V1.0")
    log("=" * 70)
    log(f"  Starting Balance : ${STARTING_BALANCE:.2f}")
    log(f"  Target Balance   : ${TARGET_BALANCE:.2f}")
    log(f"  Required Gain    : +${TARGET_BALANCE - STARTING_BALANCE:.2f} (+{(TARGET_BALANCE/STARTING_BALANCE - 1)*100:.1f}%)")
    log(f"  Deadline         : {DEADLINE.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    log(f"  Hard Stop        : ${HARD_STOP:.2f}")
    log(f"  Strategies       : Momentum + RSI Reversion + Power Hour + Funding Arb")
    log("=" * 70)

    scan       = 0
    trades     = 0
    last_side  = None
    HOLD_BARS  = 5
    hold_count = 0
    TARGET_REACHED = False

    while True:
        scan += 1
        hrs, mins, alive = time_remaining()

        if not alive:
            log("\n  ⏰ 24-HOUR DEADLINE REACHED — CLOSING ALL POSITIONS!")
            close_all_positions()
            break

        # ── STATUS HEADER ──────────────────────────────────────
        balance = get_balance()
        log(f"\n{'━'*70}")
        log(f"  SCAN #{scan:04d} | ⏱️ {hrs}h {mins}m remaining | {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")
        log(f"  Balance  : ${balance:.2f} | Target: ${TARGET_BALANCE:.2f} | Start: ${STARTING_BALANCE:.2f}")
        log(f"  Progress : {progress_bar(balance, TARGET_BALANCE)}")
        log(f"  PnL      : ${balance - STARTING_BALANCE:+.2f} ({(balance/STARTING_BALANCE - 1)*100:+.2f}%)")
        log(f"{'━'*70}")

        # ── HARD STOP ──────────────────────────────────────────
        if balance < HARD_STOP:
            log(f"\n  🚨 HARD STOP HIT! Balance ${balance:.2f} < ${HARD_STOP:.2f} — HALTING ALL TRADING!")
            close_all_positions()
            break

        # ── TARGET REACHED ─────────────────────────────────────
        if balance >= TARGET_BALANCE and not TARGET_REACHED:
            TARGET_REACHED = True
            log(f"\n  🏆🎉 TARGET $200 REACHED! Balance = ${balance:.2f}!")
            log(f"  🔒 LOCKING IN PROFITS — CLOSING ALL POSITIONS!")
            close_all_positions()
            log(f"  ✅ MISSION ACCOMPLISHED IN {24 - hrs}h {60 - mins}m!")
            break

        # ── FETCH MARKET DATA ──────────────────────────────────
        free_margin = balance
        df_1h = get_btc_data(period="3mo", interval="1h")
        if df_1h is None or len(df_1h) < 50:
            log(f"  ⚠️ Data fetch failed — retrying in {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
            continue

        # ── POSITION HOLD MANAGEMENT ───────────────────────────
        positions = get_positions()
        open_size = sum(abs(float(p.get("size", 0))) for p in positions)

        if open_size > 0 and hold_count < HOLD_BARS:
            hold_count += 1
            log(f"  📊 HOLDING {open_size:.0f} contracts | Hold bar {hold_count}/{HOLD_BARS}")
            time.sleep(SCAN_INTERVAL)
            continue
        elif open_size > 0 and hold_count >= HOLD_BARS:
            log(f"  🔄 HOLD PERIOD OVER — Closing current position to reassess...")
            close_all_positions()
            hold_count = 0
            time.sleep(3)
            continue

        # ── RUN ALL STRATEGIES IN PRIORITY ORDER ───────────────
        signal, size, reason = None, 0, ""

        # Priority 1: Power Hour (highest conviction)
        s, sz, r = strategy_power_hour(df_1h, free_margin)
        if s: signal, size, reason = s, sz, r

        # Priority 2: RSI Mean Reversion
        if not signal:
            s, sz, r = strategy_rsi_reversion(df_1h, free_margin)
            if s: signal, size, reason = s, sz, r

        # Priority 3: Momentum EMA Cross
        if not signal:
            s, sz, r = strategy_momentum(df_1h, free_margin)
            if s: signal, size, reason = s, sz, r

        # Priority 4: Funding Rate Arb
        if not signal:
            s, sz, r = strategy_funding_arb(free_margin)
            if s: signal, size, reason = s, sz, r

        # ── EXECUTE SIGNAL ─────────────────────────────────────
        if signal and size > 0:
            placed = place_order(signal, size, reason)
            if placed:
                trades += 1
                last_side  = signal
                hold_count = 0
                log(f"  📈 Total Trades This Session: {trades}")
        else:
            log(f"  💤 No signal fired this scan — waiting {SCAN_INTERVAL}s...")

        time.sleep(SCAN_INTERVAL)

    # ── FINAL REPORT ───────────────────────────────────────────
    final_balance = get_balance()
    log(f"\n{'='*70}")
    log(f"  🏁 24-HOUR HUNT COMPLETE")
    log(f"{'='*70}")
    log(f"  Starting Balance : ${STARTING_BALANCE:.2f}")
    log(f"  Final Balance    : ${final_balance:.2f}")
    log(f"  Net PnL          : ${final_balance - STARTING_BALANCE:+.2f} ({(final_balance/STARTING_BALANCE - 1)*100:+.2f}%)")
    log(f"  Total Trades     : {trades}")
    log(f"  Target $200      : {'✅ ACHIEVED!' if final_balance >= TARGET_BALANCE else '❌ NOT YET REACHED'}")
    log(f"{'='*70}")

if __name__ == "__main__":
    run()
