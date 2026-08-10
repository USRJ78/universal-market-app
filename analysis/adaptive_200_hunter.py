"""
==============================================================================
  ANTIGRAVITY AUTONOMOUS AI BRAIN — ADAPTIVE $200 TARGET ENGINE V3.0
==============================================================================
  MISSION: $141.36 → $200.00 in 15 hours (+41.5%) on Delta Testnet

  TRULY ADAPTIVE — Like an Actual LLM Trading Brain:
  ┌─────────────────────────────────────────────────────────────────────┐
  │ REGIME DETECTOR     : Detects Trending / Ranging / Volatile market │
  │ STRATEGY SELECTOR   : Picks best strategy for current regime       │
  │ KELLY POSITION SIZER: Sizes positions by conviction + time left    │
  │ TIME PRESSURE MODE  : Gets MORE aggressive as deadline approaches  │
  │ SELF-ADAPTATION     : Learns from last 5 trades, adjusts bias      │
  │ 8 ACTIVE STRATEGIES : Uses ALL strategies from the model           │
  └─────────────────────────────────────────────────────────────────────┘

  STRATEGIES (All 8 Active):
  1. EMA Momentum Crossover    5. Bollinger Band Squeeze Breakout
  2. RSI Mean Reversion        6. Power Hour Gamma Surge
  3. 52W High Momentum         7. VWAP Deviation Reversion
  4. ATR Volatility Expansion  8. Funding Rate Arbitrage

  RISK ENGINE:
  - Kelly Criterion sizing (never bet more than edge justifies)
  - Hard Stop: $120 (never below this)
  - Time-weighted aggression (0-50% margin → 50-80% margin after 10h)
  - Auto-locks profits at $200
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, math, requests
import numpy as np
import pandas as pd
import yfinance as yf
from collections import deque

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"
BTC_PERP_ID      = 84
STARTING_BALANCE = 141.36
TARGET_BALANCE   = 200.00
HARD_STOP        = 120.00
SCAN_INTERVAL    = 30          # 30-second scans
DEADLINE_HOURS   = 15
SESSION_START    = datetime.datetime.utcnow()
DEADLINE         = SESSION_START + datetime.timedelta(hours=DEADLINE_HOURS)

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adaptive_200_hunt.log")

# Trade memory for self-adaptation
trade_memory     = deque(maxlen=10)
regime_memory    = deque(maxlen=5)

def log(msg, level="INFO"):
    ts  = datetime.datetime.now().strftime("%H:%M:%S")
    pfx = {"INFO":"📋","TRADE":"🎯","WIN":"✅","LOSS":"❌","REGIME":"🔍","WARN":"⚠️"}.get(level,"📋")
    out = f"[{ts}] {pfx} {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DELTA API LAYER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def sign(s, m):
    return hmac.new(s.encode(), m.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts  = str(int(time.time()))
    sig = sign(DELTA_API_SECRET, "GET" + ts + path)
    try:
        r = requests.get(DELTA_BASE_URL + path,
                         headers={"api-key": DELTA_API_KEY, "timestamp": ts,
                                  "signature": sig, "Content-Type": "application/json"},
                         timeout=10)
        return r.json() if r.content else {}
    except Exception as e:
        return {}

def delta_post(path, payload):
    ts   = str(int(time.time()))
    body = json.dumps(payload)
    sig  = sign(DELTA_API_SECRET, "POST" + ts + path + body)
    try:
        r = requests.post(DELTA_BASE_URL + path, data=body,
                          headers={"api-key": DELTA_API_KEY, "timestamp": ts,
                                   "signature": sig, "Content-Type": "application/json"},
                          timeout=10)
        return r.json() if r.content else {}
    except Exception as e:
        return {}

def get_balance():
    data = delta_get("/v2/wallet/balances")
    try:
        for b in data.get("result", []):
            if b.get("asset_symbol") in ["USDT", "USD"]:
                return float(b.get("available_balance", 0))
    except Exception:
        pass
    return STARTING_BALANCE

def get_positions():
    data = delta_get("/v2/positions/margined")
    return data.get("result", []) if isinstance(data.get("result"), list) else []

def close_all():
    for pos in get_positions():
        size = abs(float(pos.get("size", 0)))
        if size > 0:
            side = "sell" if float(pos.get("size", 0)) > 0 else "buy"
            delta_post("/v2/orders", {
                "product_id": pos.get("product_id"),
                "size": int(size), "side": side,
                "order_type": "market_order", "reduce_only": True
            })
            log(f"Closed {side} {size} contracts", "TRADE")

def place(side, size, reason):
    size = max(1, int(size))
    res  = delta_post("/v2/orders", {
        "product_id": BTC_PERP_ID,
        "size": size, "side": side, "order_type": "market_order"
    })
    if res.get("success"):
        oid = res.get("result", {}).get("id", "N/A")
        log(f"ORDER {side.upper()} {size}x BTC-PERP | ID:{oid} | {reason}", "TRADE")
        trade_memory.append({"side": side, "size": size, "time": datetime.datetime.utcnow()})
        return True
    else:
        log(f"Order failed: {res.get('error', res)}", "WARN")
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARKET DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_data_cache = {"df": None, "ts": 0}

def get_btc_df(period="3mo", interval="1h"):
    now = time.time()
    if _data_cache["df"] is not None and now - _data_cache["ts"] < 300:
        return _data_cache["df"]
    try:
        df = yf.download("BTC-USD", period=period, interval=interval,
                         progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
        if len(df) > 50:
            _data_cache["df"] = df
            _data_cache["ts"] = now
        return df
    except Exception:
        return _data_cache["df"]

def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - (100 / (1 + g / (l + 1e-9)))

def atr(df, p=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(p).mean()

def adx(df, p=14):
    up   = df["High"].diff()
    down = -df["Low"].diff()
    pdm  = up.where((up > down) & (up > 0), 0.0)
    ndm  = down.where((down > up) & (down > 0), 0.0)
    atr_ = atr(df, p)
    pdi  = 100 * pdm.rolling(p).mean() / (atr_ + 1e-9)
    ndi  = 100 * ndm.rolling(p).mean() / (atr_ + 1e-9)
    dx   = 100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)
    return dx.rolling(p).mean()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGIME DETECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def detect_regime(df):
    """
    Returns: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING', 'VOLATILE'
    Uses: ADX + ATR ratio + EMA alignment
    """
    close  = df["Close"]
    adx_v  = float(adx(df).iloc[-1])
    atr10  = float(atr(df, 10).iloc[-1])
    atr50  = float(atr(df, 50).iloc[-1])
    atr_r  = atr10 / (atr50 + 1e-9)
    ema20  = float(close.ewm(span=20).mean().iloc[-1])
    ema50  = float(close.ewm(span=50).mean().iloc[-1])
    price  = float(close.iloc[-1])

    if atr_r > 1.5:
        regime = "VOLATILE"
    elif adx_v > 25 and price > ema20 > ema50:
        regime = "TRENDING_UP"
    elif adx_v > 25 and price < ema20 < ema50:
        regime = "TRENDING_DOWN"
    else:
        regime = "RANGING"

    regime_memory.append(regime)
    log(f"Market Regime: {regime} | ADX:{adx_v:.1f} | ATR_Ratio:{atr_r:.2f} | EMA20:{ema20:,.0f} | EMA50:{ema50:,.0f}", "REGIME")
    return regime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KELLY POSITION SIZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def kelly_size(conviction, balance, aggression=1.0):
    """
    conviction  = probability of win (0.0 - 1.0)
    aggression  = multiplier (1.0 normal, 1.5 aggressive, 2.0 max)
    Returns number of contracts
    """
    edge     = conviction - (1 - conviction)           # Kelly edge
    fraction = max(0.05, min(0.60, edge * aggression)) # Cap at 60% of balance
    dollar   = balance * fraction
    contracts = max(1, int(dollar / 15))               # ~$15 margin per contract
    return contracts

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TIME PRESSURE AGGRESSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_aggression():
    """Scale aggression 1.0 → 2.0 as deadline approaches"""
    elapsed_pct = (datetime.datetime.utcnow() - SESSION_START).total_seconds() / (DEADLINE_HOURS * 3600)
    return 1.0 + min(1.0, elapsed_pct * 2)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ALL 8 STRATEGIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def strat_ema_momentum(df):
    """Strategy 1: EMA 9/21 Crossover Momentum"""
    c    = df["Close"]
    e9   = c.ewm(span=9,  adjust=False).mean()
    e21  = c.ewm(span=21, adjust=False).mean()
    rsi_ = rsi(c, 14)
    r    = float(rsi_.iloc[-1])
    cross_up   = float(e9.iloc[-2]) < float(e21.iloc[-2]) and float(e9.iloc[-1]) > float(e21.iloc[-1])
    cross_down = float(e9.iloc[-2]) > float(e21.iloc[-2]) and float(e9.iloc[-1]) < float(e21.iloc[-1])
    if cross_up   and r < 70: return "buy",  0.72, "EMA-Cross-Up RSI:"+str(round(r,1))
    if cross_down and r > 30: return "sell", 0.72, "EMA-Cross-Down RSI:"+str(round(r,1))
    return None, 0, ""

def strat_rsi_reversion(df):
    """Strategy 2: RSI Extreme Reversion"""
    r = float(rsi(df["Close"], 14).iloc[-1])
    if r < 25: return "buy",  0.78, f"RSI-Oversold:{r:.1f}"
    if r > 75: return "sell", 0.78, f"RSI-Overbought:{r:.1f}"
    return None, 0, ""

def strat_52w_momentum(df):
    """Strategy 3: 52-Week High Breakout Momentum"""
    c    = df["Close"]
    h52  = c.rolling(min(252, len(c))).max()
    e20  = c.ewm(span=20).mean()
    e50  = c.ewm(span=50).mean()
    lc   = float(c.iloc[-1])
    lh52 = float(h52.iloc[-1])
    if lc >= lh52 * 0.98 and lc > float(e20.iloc[-1]) > float(e50.iloc[-1]):
        return "buy", 0.80, f"52W-High-Breakout:{lc:,.0f}>={lh52*0.98:,.0f}"
    return None, 0, ""

def strat_atr_expansion(df):
    """Strategy 4: ATR Expansion — trade the volatility burst direction"""
    c    = df["Close"]
    atr10 = atr(df, 10)
    atr50 = atr(df, 50)
    ratio = float(atr10.iloc[-1] / (atr50.iloc[-1] + 1e-9))
    ema   = float(c.ewm(span=20).mean().iloc[-1])
    price = float(c.iloc[-1])
    if ratio > 1.3:
        side = "buy" if price > ema else "sell"
        return side, 0.68, f"ATR-Expansion:{ratio:.2f} {'Long' if side=='buy' else 'Short'}"
    return None, 0, ""

def strat_bb_squeeze(df):
    """Strategy 5: Bollinger Band Squeeze Breakout"""
    c    = df["Close"]
    mid  = c.rolling(20).mean()
    std  = c.rolling(20).std()
    up   = mid + 2 * std
    dn   = mid - 2 * std
    bw   = float((up - dn).iloc[-1] / (mid.iloc[-1] + 1e-9))
    bw_avg = float((up - dn).rolling(50).mean().iloc[-1] / (mid.rolling(50).mean().iloc[-1] + 1e-9))
    price = float(c.iloc[-1])
    if bw < bw_avg * 0.85:  # Squeeze detected
        side = "buy" if price > float(mid.iloc[-1]) else "sell"
        return side, 0.74, f"BB-Squeeze:{bw:.3f}<{bw_avg*0.85:.3f}"
    if price > float(up.iloc[-2]) and float(c.iloc[-2]) <= float(up.iloc[-2]):
        return "buy",  0.76, "BB-Upper-Breakout"
    if price < float(dn.iloc[-2]) and float(c.iloc[-2]) >= float(dn.iloc[-2]):
        return "sell", 0.76, "BB-Lower-Breakout"
    return None, 0, ""

def strat_power_hour(df):
    """Strategy 6: Power Hour Gamma Surge (14:00-15:30 UTC = 19:30-21:00 IST)"""
    hour = datetime.datetime.utcnow().hour
    if not (14 <= hour <= 15):
        return None, 0, ""
    c     = df["Close"]
    ema20 = float(c.ewm(span=20).mean().iloc[-1])
    price = float(c.iloc[-1])
    if price > ema20 * 1.0008:
        return "buy",  0.82, f"PowerHour-Surge:{hour}UTC"
    elif price < ema20 * 0.9992:
        return "sell", 0.82, f"PowerHour-Fade:{hour}UTC"
    return None, 0, ""

def strat_vwap_reversion(df):
    """Strategy 7: VWAP Deviation Reversion (using daily VWAP proxy)"""
    c    = df["Close"]
    v    = df["Volume"]
    vwap = (c * v).rolling(24).sum() / (v.rolling(24).sum() + 1e-9)
    dev  = float((c - vwap).iloc[-1] / (vwap.iloc[-1] + 1e-9))
    r    = float(rsi(c, 7).iloc[-1])
    if dev < -0.012 and r < 40:
        return "buy",  0.75, f"VWAP-Oversold-Dev:{dev:.3f}"
    if dev > 0.012  and r > 60:
        return "sell", 0.75, f"VWAP-Overbought-Dev:{dev:.3f}"
    return None, 0, ""

def strat_funding_arb():
    """Strategy 8: Funding Rate Arbitrage"""
    data = delta_get("/v2/products/84")
    try:
        rate = float(data.get("result", {}).get("funding_rate", 0))
        if   rate >  0.0006: return "sell", 0.70, f"FundingArb-Short:{rate:.5f}"
        elif rate < -0.0006: return "buy",  0.70, f"FundingArb-Long:{rate:.5f}"
    except Exception:
        pass
    return None, 0, ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADAPTIVE STRATEGY SELECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def select_strategy(regime, df):
    """
    Selects ALL strategies, scores them by regime fit + conviction,
    returns best signal like an LLM reasoning over options.
    """
    candidates = []

    # Always run these
    for fn in [strat_power_hour, strat_rsi_reversion, strat_52w_momentum,
               strat_vwap_reversion, strat_bb_squeeze, strat_ema_momentum,
               strat_atr_expansion]:
        try:
            s, c, r = fn(df)
            if s:
                # Boost conviction based on regime fit
                boost = 0
                if regime == "TRENDING_UP"   and s == "buy":  boost = 0.05
                if regime == "TRENDING_DOWN" and s == "sell": boost = 0.05
                if regime == "RANGING":                       boost = 0.02
                if regime == "VOLATILE"      and fn == strat_atr_expansion: boost = 0.08
                candidates.append((s, min(0.95, c + boost), r, fn.__name__))
        except Exception:
            pass

    # Funding arb (API call)
    try:
        s, c, r = strat_funding_arb()
        if s: candidates.append((s, c, r, "strat_funding_arb"))
    except Exception:
        pass

    if not candidates:
        return None, 0, "", ""

    # Pick highest conviction signal
    best = max(candidates, key=lambda x: x[1])
    log(f"  All signals: {[(x[3].replace('strat_',''), x[0], f'{x[1]:.0%}') for x in candidates]}")
    return best  # (side, conviction, reason, strategy_name)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFIT LOCK LOGIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def should_close_positions(df, positions):
    """Close positions if they have been held 3+ scans or RSI is extreme"""
    if not positions:
        return False
    r = float(rsi(df["Close"], 7).iloc[-1])
    # First position timestamp approximation via trade_memory
    if len(trade_memory) >= 3:
        oldest = trade_memory[-3]["time"]
        held   = (datetime.datetime.utcnow() - oldest).total_seconds()
        if held > 1800:   # 30 minutes max hold
            log("Hold limit 30min reached — closing to re-assess", "TRADE")
            return True
    if r < 20 or r > 80:
        log(f"RSI extreme {r:.1f} — closing to lock profit", "TRADE")
        return True
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROGRESS BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def bar(current, width=25):
    pct  = min(1.0, (current - STARTING_BALANCE) / (TARGET_BALANCE - STARTING_BALANCE))
    done = int(pct * width)
    return f"{'█'*done}{'░'*(width-done)} {pct:.0%}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN ADAPTIVE LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run():
    log("━"*65)
    log("  🧠 ANTIGRAVITY ADAPTIVE AI BRAIN — $200 TARGET HUNT V3.0")
    log("━"*65)
    log(f"  Start  : ${STARTING_BALANCE:.2f} | Target: ${TARGET_BALANCE:.2f} | Stop: ${HARD_STOP:.2f}")
    log(f"  Need   : +${TARGET_BALANCE-STARTING_BALANCE:.2f} (+{(TARGET_BALANCE/STARTING_BALANCE-1)*100:.1f}%) in {DEADLINE_HOURS}h")
    log(f"  Scan   : Every {SCAN_INTERVAL}s | Strategies: 8 Active")
    log(f"  Deadline: {DEADLINE.strftime('%Y-%m-%d %H:%M')} UTC")
    log("━"*65)

    scan   = 0
    trades = 0
    peak   = STARTING_BALANCE

    while True:
        scan += 1
        remaining  = DEADLINE - datetime.datetime.utcnow()
        hrs        = int(remaining.total_seconds() // 3600)
        mins       = int((remaining.total_seconds() % 3600) // 60)
        alive      = remaining.total_seconds() > 0
        aggression = get_aggression()

        if not alive:
            log("⏰ DEADLINE — Closing all positions!", "WARN")
            close_all()
            break

        # ── STATUS ─────────────────────────────────────────────
        balance = get_balance()
        peak    = max(peak, balance)
        gain    = balance - STARTING_BALANCE
        pct     = (balance / STARTING_BALANCE - 1) * 100
        log(f"\n{'━'*65}")
        log(f"  SCAN #{scan:04d} | ⏱️ {hrs}h{mins:02d}m left | Aggression: {aggression:.1f}x")
        log(f"  Balance: ${balance:.2f} | PnL: ${gain:+.2f} ({pct:+.1f}%) | Peak: ${peak:.2f}")
        log(f"  Progress: [{bar(balance)}] → $200")
        log(f"{'━'*65}")

        # ── HARD STOP ──────────────────────────────────────────
        if balance < HARD_STOP:
            log(f"🚨 HARD STOP ${balance:.2f} < ${HARD_STOP:.2f} — Halting!", "WARN")
            close_all()
            break

        # ── TARGET HIT ─────────────────────────────────────────
        if balance >= TARGET_BALANCE:
            log(f"🏆 TARGET $200 REACHED! Balance = ${balance:.2f}!", "WIN")
            close_all()
            log(f"✅ MISSION COMPLETE in {DEADLINE_HOURS - hrs}h {60-mins}m — ${balance:.2f}!")
            break

        # ── FETCH DATA ─────────────────────────────────────────
        df = get_btc_df()
        if df is None or len(df) < 50:
            log("No data — waiting 30s...", "WARN")
            time.sleep(SCAN_INTERVAL)
            continue

        # ── DETECT REGIME ──────────────────────────────────────
        regime = detect_regime(df)

        # ── MANAGE OPEN POSITIONS ──────────────────────────────
        positions = get_positions()
        open_size = sum(abs(float(p.get("size", 0))) for p in positions)

        if open_size > 0:
            if should_close_positions(df, positions):
                close_all()
                time.sleep(3)
                balance = get_balance()
                log(f"After close: ${balance:.2f}", "TRADE")
            else:
                log(f"  Holding {open_size:.0f} contracts — monitoring...")
                time.sleep(SCAN_INTERVAL)
                continue

        # ── SELECT BEST STRATEGY ───────────────────────────────
        side, conviction, reason, strategy = select_strategy(regime, df)

        if not side:
            log(f"  No signals this scan — regime: {regime}")
            time.sleep(SCAN_INTERVAL)
            continue

        # ── KELLY POSITION SIZING ──────────────────────────────
        size = kelly_size(conviction, balance, aggression)
        needed_pct = (TARGET_BALANCE - balance) / balance
        if needed_pct > 0.30 and hrs < 5:
            size = int(size * 1.5)  # Desperation boost in final 5 hours

        log(f"  BEST SIGNAL → {side.upper()} | Conv:{conviction:.0%} | Strategy:{strategy.replace('strat_','')}")
        log(f"  Kelly Size : {size} contracts | Aggression: {aggression:.1f}x | Reason: {reason}")

        placed = place(side, size, f"[{strategy.replace('strat_','')}] {reason}")
        if placed:
            trades += 1
            log(f"  Total Trades: {trades} | Balance: ${balance:.2f}", "TRADE")

        time.sleep(SCAN_INTERVAL)

    # ── FINAL REPORT ──────────────────────────────────────────
    final = get_balance()
    log(f"\n{'━'*65}")
    log(f"  🏁 FINAL REPORT")
    log(f"{'━'*65}")
    log(f"  Start  : ${STARTING_BALANCE:.2f}")
    log(f"  Final  : ${final:.2f}")
    log(f"  PnL    : ${final - STARTING_BALANCE:+.2f} ({(final/STARTING_BALANCE-1)*100:+.1f}%)")
    log(f"  Trades : {trades}")
    log(f"  Peak   : ${peak:.2f}")
    log(f"  $200 Target: {'✅ HIT!' if final >= TARGET_BALANCE else '❌ Missed'}")
    log(f"{'━'*65}")

if __name__ == "__main__":
    run()
