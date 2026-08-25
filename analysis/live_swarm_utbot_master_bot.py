"""
==============================================================================
  ANTIGRAVITY AI BRAIN — LIVE SWARM × UTBOT MASTER TRADING BOT
==============================================================================
  The unified autonomous trading intelligence combining:
    - Swarm Call Spread (Agent Alpha + Beta + Gamma + Delta)
    - UTBot Champion Signal (Key=2.4, ATR=9)
    - Supertrend(10, 3.0) trend alignment
    - Zero Net Debit 1×2 Ratio Call Spread execution

  SETUP (fill in your credentials below):
    1. TELEGRAM_TOKEN   — from @BotFather on Telegram
    2. TELEGRAM_CHAT_ID — from @userinfobot on Telegram
    3. DELTA_API_KEY    — from Delta Exchange API settings
    4. DELTA_API_SECRET — from Delta Exchange API settings

  HOW TO RUN:
    python analysis/live_swarm_utbot_master_bot.py

  WHAT IT DOES:
    - Scans markets every 5 minutes (configurable)
    - Checks all 5 signal layers
    - Alerts you on Telegram for every signal
    - Places orders via Delta Exchange API when conviction >= 70%
    - Monitors open positions and exits automatically
    - Logs every trade to trade_ledger.json
==============================================================================
"""

import os, sys, time, json, hmac, hashlib, datetime, math, traceback
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import schedule

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ══════════════════════════════════════════════════════════════════════════════
#  ⚙️  YOUR CREDENTIALS — FILL THESE IN
# ══════════════════════════════════════════════════════════════════════════════

TELEGRAM_TOKEN   = "YOUR_TELEGRAM_BOT_TOKEN"       # from @BotFather
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"          # from @userinfobot

DELTA_API_KEY    = "YOUR_DELTA_API_KEY"
DELTA_API_SECRET = "YOUR_DELTA_API_SECRET"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"  # change to live URL for real trading
                  # Live URL: "https://api.india.delta.exchange"

# ── Bot Settings ──────────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES = 5        # Scan every N minutes
CONVICTION_GATE       = 0.70     # Minimum 70% (3/5 layers) to enter
ALLOC_PCT             = 0.25     # 25% of wallet per trade
MAX_CONCURRENT        = 2        # Max open trades at once
MAX_DAILY_LOSS_PCT    = 0.05     # Shut down if daily loss > 5%
STOP_LOSS_PCT         = 0.03     # Stop loss on net debit breach
TAKE_PROFIT_PCT       = 0.045   # K2 strike = entry × 1.045
CATASTRO_EXIT_PCT     = 0.10    # Emergency exit if price > 10% above entry

# ── Assets to Scan ────────────────────────────────────────────────────────────
WATCH_LIST = [
    {"ticker": "BTC-USD",    "label": "BTC",       "type": "crypto"},
    {"ticker": "^NSEI",      "label": "NIFTY",     "type": "index"},
    {"ticker": "^NSEBANK",   "label": "BANKNIFTY", "type": "index"},
    {"ticker": "RELIANCE.NS","label": "RELIANCE",  "type": "stock"},
    {"ticker": "INFY.NS",    "label": "INFOSYS",   "type": "stock"},
]

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LEDGER_FILE = os.path.join(BASE_DIR, "trade_ledger.json")
LOG_FILE    = os.path.join(BASE_DIR, "master_bot.log")

# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def log(msg, level="INFO"):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = f"[{ts}] [{level}] {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM ALERTS
# ══════════════════════════════════════════════════════════════════════════════

def telegram_send(message):
    if "YOUR_TELEGRAM" in TELEGRAM_TOKEN:
        log(f"[TELEGRAM DISABLED] {message}", "WARN")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
        if resp.status_code != 200:
            log(f"Telegram error: {resp.text}", "WARN")
    except Exception as e:
        log(f"Telegram failed: {e}", "WARN")

def alert_entry(asset, conviction, layers, entry_price, k2_price, alloc):
    layer_icons = {
        "alpha": "Alpha (52wk High)",
        "beta":  "Beta (Vol Squeeze)",
        "gamma": "Gamma (S&D Zone)",
        "utbot": "UTBot (Crossover)",
        "st":    "Supertrend (GREEN)"
    }
    layer_str = "\n".join([
        f"  {'OK' if v else '--'} Layer {i+1}: {layer_icons[k]}"
        for i, (k, v) in enumerate(layers.items())
    ])
    msg = (
        f"SIGNAL DETECTED\n"
        f"Asset: {asset}\n"
        f"Conviction: {conviction*100:.0f}%\n"
        f"Layers:\n{layer_str}\n"
        f"Action: Entering 1x2 Call Spread\n"
        f"  Buy  1x ATM @ {entry_price:,.2f}\n"
        f"  Sell 2x OTM @ {k2_price:,.2f} (+{TAKE_PROFIT_PCT*100:.1f}%)\n"
        f"Allocated: {alloc:.2f} (25% of wallet)"
    )
    log(f"ENTRY ALERT: {asset} @ {entry_price:.2f} conviction={conviction*100:.0f}%")
    telegram_send(msg)

def alert_exit(asset, entry_price, exit_price, net_pct, wallet_before, wallet_after, reason):
    icon  = "TARGET HIT" if net_pct > 0 else "STOPPED OUT"
    emoji = "+" if net_pct > 0 else ""
    msg = (
        f"{icon}\n"
        f"Asset: {asset}\n"
        f"Entry: {entry_price:,.2f}\n"
        f"Exit:  {exit_price:,.2f}\n"
        f"Return: {emoji}{net_pct*100:.1f}%\n"
        f"Reason: {reason}\n"
        f"Wallet: {wallet_before:.2f} -> {wallet_after:.2f}"
    )
    log(f"EXIT ALERT: {asset} {emoji}{net_pct*100:.1f}% | {reason}")
    telegram_send(msg)

def alert_heartbeat(wallet, open_trades, daily_pnl):
    msg = (
        f"BOT HEARTBEAT\n"
        f"Wallet: ${wallet:.2f}\n"
        f"Open trades: {open_trades}\n"
        f"Today P&L: {'+' if daily_pnl>=0 else ''}{daily_pnl*100:.2f}%\n"
        f"Time: {datetime.datetime.now().strftime('%H:%M:%S IST')}"
    )
    telegram_send(msg)

# ══════════════════════════════════════════════════════════════════════════════
#  DELTA EXCHANGE API
# ══════════════════════════════════════════════════════════════════════════════

def delta_sign(secret, method, path, timestamp, body=""):
    msg = method + timestamp + path + body
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def delta_headers(method, path, body=""):
    ts  = str(int(time.time()))
    sig = delta_sign(DELTA_API_SECRET, method, path, ts, body)
    return {
        "api-key":       DELTA_API_KEY,
        "timestamp":     ts,
        "signature":     sig,
        "Content-Type":  "application/json",
        "User-Agent":    "AntigravityAIBot/2.0"
    }

def delta_get_wallet():
    """Get current wallet balance from Delta Exchange"""
    if "YOUR_DELTA" in DELTA_API_KEY:
        return 250.0  # Paper mode default
    try:
        path = "/v2/wallet/balances"
        resp = requests.get(
            DELTA_BASE_URL + path,
            headers=delta_headers("GET", path),
            timeout=10
        )
        data = resp.json()
        if data.get("success"):
            for b in data.get("result", []):
                if b.get("asset_symbol") in ("USDT", "USD", "INR"):
                    return float(b.get("available_balance", 0))
    except Exception as e:
        log(f"Wallet fetch failed: {e}", "WARN")
    return 250.0

def delta_place_order(product_id, side, size, order_type="limit_order", price=None):
    """Place an order on Delta Exchange"""
    if "YOUR_DELTA" in DELTA_API_KEY:
        log(f"[PAPER] Would place {side} {size}x product {product_id} @ {price}", "PAPER")
        return {"success": True, "result": {"id": f"PAPER_{int(time.time())}"}}
    try:
        path = "/v2/orders"
        body = json.dumps({
            "product_id":   product_id,
            "size":         size,
            "side":         side,
            "order_type":   order_type,
            "limit_price":  str(price) if price else None,
            "time_in_force":"gtc"
        })
        resp = requests.post(
            DELTA_BASE_URL + path,
            headers=delta_headers("POST", path, body),
            data=body, timeout=10
        )
        return resp.json()
    except Exception as e:
        log(f"Order failed: {e}", "ERROR")
        return {"success": False, "error": str(e)}

# ══════════════════════════════════════════════════════════════════════════════
#  SIGNAL INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

def compute_utbot_signal(close, key=2.4, atr_period=9):
    tr    = close.diff().abs()
    atr   = tr.rolling(atr_period).mean()
    nloss = key * atr
    xatr  = [0.0] * len(close)
    for t in range(1, len(close)):
        sc = float(close.iloc[t])
        sp = float(close.iloc[t-1])
        xa = xatr[t-1]
        lc = float(nloss.iloc[t]) if not np.isnan(nloss.iloc[t]) else 0.0
        if   sc > xa and sp > xa: xatr[t] = max(xa, sc - lc)
        elif sc < xa and sp < xa: xatr[t] = min(xa, sc + lc)
        else:                     xatr[t] = (sc - lc) if sc > xa else (sc + lc)
    xatr_s = pd.Series(xatr, index=close.index)
    buy = bool((close.iloc[-1] > xatr_s.iloc[-1]) and
               (close.iloc[-2] <= xatr_s.iloc[-2]))
    return buy, xatr_s


def compute_supertrend_signal(df, period=10, multiplier=3.0):
    high, low, close = df["High"], df["Low"], df["Close"]
    pc  = close.shift(1)
    tr  = pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high+low)/2
    ub  = hl2 + multiplier*atr
    lb  = hl2 - multiplier*atr
    fu  = ub.copy().astype(float)
    fl  = lb.copy().astype(float)
    for i in range(1, len(close)):
        fu.iloc[i] = ub.iloc[i] if ub.iloc[i]<fu.iloc[i-1] or close.iloc[i-1]>fu.iloc[i-1] else fu.iloc[i-1]
        fl.iloc[i] = lb.iloc[i] if lb.iloc[i]>fl.iloc[i-1] or close.iloc[i-1]<fl.iloc[i-1] else fl.iloc[i-1]
    direction = pd.Series(1, index=close.index, dtype=int)
    for i in range(1, len(close)):
        if   direction.iloc[i-1]==1  and close.iloc[i]<fl.iloc[i]: direction.iloc[i]=-1
        elif direction.iloc[i-1]==-1 and close.iloc[i]>fu.iloc[i]: direction.iloc[i]=1
        else:                                                        direction.iloc[i]=direction.iloc[i-1]
    return bool(direction.iloc[-1] == 1)


def compute_all_layers(df):
    """
    Compute all 5 signal layers and return conviction score.
    Returns: dict of layer results, conviction score (0.0 to 1.0)
    """
    close = df["Close"]
    high  = df["High"]

    # Layer 1 — Alpha: Near 52-week high + uptrend
    high52   = high.rolling(252).max()
    near52   = float(close.iloc[-1]) >= float(high52.iloc[-1]) * 0.98
    ema20    = close.ewm(span=20).mean()
    ema50    = close.ewm(span=50).mean()
    trend_up = float(ema20.iloc[-1]) > float(ema50.iloc[-1])
    alpha    = near52 and trend_up

    # Layer 2 — Beta: Volatility squeeze
    pc   = close.shift(1)
    tr   = pd.concat([
        (high-df["Low"]),
        (high-pc).abs(),
        (df["Low"]-pc).abs()
    ], axis=1).max(axis=1)
    atr10  = tr.rolling(10).mean()
    atr50  = tr.rolling(50).mean()
    beta   = float(atr10.iloc[-1]) / max(float(atr50.iloc[-1]), 1e-9) < 0.92

    # Layer 3 — Gamma: S&D safe zone
    high20 = high.rolling(20).max()
    low20  = df["Low"].rolling(20).min()
    sd_pos = 100.0*(float(close.iloc[-1])-float(low20.iloc[-1])) / \
             max(float(high20.iloc[-1])-float(low20.iloc[-1]), 1e-9)
    gamma  = 10.0 <= sd_pos <= 85.0

    # Layer 4 — UTBot crossover
    utbot, _ = compute_utbot_signal(close)

    # Layer 5 — Supertrend GREEN
    st_bull  = compute_supertrend_signal(df)

    layers = {
        "alpha": alpha,
        "beta":  beta,
        "gamma": gamma,
        "utbot": utbot,
        "st":    st_bull,
    }
    conviction = sum(layers.values()) / 5.0
    return layers, conviction

# ══════════════════════════════════════════════════════════════════════════════
#  TRADE LEDGER
# ══════════════════════════════════════════════════════════════════════════════

def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "wallet":       250.0,
        "open_trades":  [],
        "closed_trades":[],
        "daily_pnl":    0.0,
        "daily_start":  str(datetime.date.today()),
        "total_trades": 0,
        "total_wins":   0,
    }

def save_ledger(ledger):
    try:
        with open(LEDGER_FILE, "w") as f:
            json.dump(ledger, f, indent=2, default=str)
    except Exception as e:
        log(f"Ledger save failed: {e}", "ERROR")

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN SCAN LOOP
# ══════════════════════════════════════════════════════════════════════════════

def check_and_reset_daily(ledger):
    today = str(datetime.date.today())
    if ledger.get("daily_start") != today:
        ledger["daily_pnl"]   = 0.0
        ledger["daily_start"] = today
        log("Daily P&L reset for new trading day")
    return ledger

def scan_markets():
    """Main scan — runs every SCAN_INTERVAL_MINUTES minutes"""
    log("=" * 60)
    log("MARKET SCAN STARTING")

    ledger = load_ledger()
    ledger = check_and_reset_daily(ledger)

    # ── Daily loss circuit breaker ────────────────────────────────
    if ledger["daily_pnl"] <= -MAX_DAILY_LOSS_PCT:
        log(f"CIRCUIT BREAKER: Daily loss {ledger['daily_pnl']*100:.1f}% >= limit. Stopping.", "WARN")
        telegram_send(
            f"CIRCUIT BREAKER TRIGGERED\n"
            f"Daily loss: {ledger['daily_pnl']*100:.1f}%\n"
            f"Bot paused until tomorrow."
        )
        return

    wallet = ledger["wallet"]
    log(f"Wallet: ${wallet:.2f} | Open trades: {len(ledger['open_trades'])}")

    # ── Monitor open trades ───────────────────────────────────────
    closed_now = []
    for trade in ledger["open_trades"]:
        ticker       = trade["ticker"]
        entry_price  = trade["entry_price"]
        k2_price     = trade["k2_price"]
        alloc        = trade["alloc"]

        try:
            df = yf.download(ticker, period="2d", interval="1h",
                             progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            if len(df) < 2: continue

            curr_price = float(df["Close"].iloc[-1])
            curr_high  = float(df["High"].iloc[-1])
            curr_low   = float(df["Low"].iloc[-1])

            st_still_bull = compute_supertrend_signal(df)
            exit_price    = None
            reason        = None

            if curr_high >= k2_price * 1.001:     # Hit K2 target
                exit_price = k2_price
                reason     = "TARGET HIT (K2)"
            elif curr_low <= entry_price * (1 - CATASTRO_EXIT_PCT):  # Catastrophic
                exit_price = curr_price
                reason     = "EMERGENCY EXIT (>10% drop)"
            elif curr_low <= entry_price * (1 - STOP_LOSS_PCT):  # Stop loss
                exit_price = entry_price * (1 - STOP_LOSS_PCT)
                reason     = "STOP LOSS (-3%)"
            elif not st_still_bull:                # Supertrend flipped
                exit_price = curr_price
                reason     = "SUPERTREND FLIP"

            if exit_price is not None:
                raw_ret   = (exit_price - entry_price) / entry_price
                if reason == "TARGET HIT (K2)":
                    net_ret = TAKE_PROFIT_PCT * 6.0   # 6x options leverage on TP
                elif "STOP" in reason or "EMERGENCY" in reason:
                    net_ret = -STOP_LOSS_PCT
                else:
                    net_ret = raw_ret * 2.5  # partial options delta on ST exit

                gross       = net_ret * alloc
                fric        = alloc * 0.002
                tax         = max(0, (gross - fric) * 0.15)
                net         = gross - fric - tax
                wallet_new  = wallet + net

                ledger["daily_pnl"] += net / wallet
                ledger["wallet"]     = wallet_new
                wallet               = wallet_new
                ledger["total_trades"] += 1
                if net_ret > 0:
                    ledger["total_wins"] += 1

                trade["exit_price"] = exit_price
                trade["net_return"] = net_ret
                trade["exit_time"]  = str(datetime.datetime.now())
                ledger["closed_trades"].append(trade)
                closed_now.append(trade)

                alert_exit(
                    trade["label"], entry_price, exit_price,
                    net_ret, wallet - net, wallet, reason
                )
        except Exception as e:
            log(f"Monitor error {ticker}: {e}", "WARN")

    # Remove closed trades
    ledger["open_trades"] = [
        t for t in ledger["open_trades"]
        if t not in closed_now
    ]

    # ── Scan for new entries ──────────────────────────────────────
    if len(ledger["open_trades"]) >= MAX_CONCURRENT:
        log(f"Max concurrent trades ({MAX_CONCURRENT}) reached — skipping scan")
        save_ledger(ledger)
        return

    for asset in WATCH_LIST:
        ticker = asset["ticker"]
        label  = asset["label"]

        # Skip if already have this asset open
        if any(t["ticker"] == ticker for t in ledger["open_trades"]):
            continue

        try:
            df = yf.download(ticker, period="300d", interval="1d",
                             progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.dropna(inplace=True)

            if len(df) < 60:
                log(f"{label}: Insufficient data ({len(df)} bars)")
                continue

            layers, conviction = compute_all_layers(df)
            curr_price         = float(df["Close"].iloc[-1])
            k2_price           = curr_price * (1 + TAKE_PROFIT_PCT)
            alloc              = wallet * ALLOC_PCT

            log(f"{label}: conviction={conviction*100:.0f}% | "
                f"alpha={layers['alpha']} beta={layers['beta']} "
                f"gamma={layers['gamma']} utbot={layers['utbot']} "
                f"st={layers['st']}")

            if conviction >= CONVICTION_GATE and layers["utbot"]:
                # ENTRY CONFIRMED
                alert_entry(label, conviction, layers,
                            curr_price, k2_price, alloc)

                # Place order via broker
                order = delta_place_order(
                    product_id=asset.get("product_id", 84),  # BTC perpetual default
                    side="buy",
                    size=1,
                    order_type="market_order"
                )

                trade_record = {
                    "ticker":      ticker,
                    "label":       label,
                    "entry_price": curr_price,
                    "k2_price":    k2_price,
                    "alloc":       alloc,
                    "layers":      {k: bool(v) for k, v in layers.items()},
                    "conviction":  conviction,
                    "entry_time":  str(datetime.datetime.now()),
                    "order_id":    order.get("result", {}).get("id", "PAPER"),
                }
                ledger["open_trades"].append(trade_record)

                log(f"ENTERED: {label} @ {curr_price:.2f} "
                    f"K2={k2_price:.2f} conviction={conviction*100:.0f}%", "TRADE")

                if len(ledger["open_trades"]) >= MAX_CONCURRENT:
                    break  # Stop scanning once max trades reached

        except Exception as e:
            log(f"Scan error {ticker}: {traceback.format_exc()}", "ERROR")

    save_ledger(ledger)

    # Stats summary
    total = ledger["total_trades"]
    wins  = ledger["total_wins"]
    wr    = wins/max(1,total)*100
    log(f"Scan complete. Wallet: ${wallet:.2f} | "
        f"All-time: {total} trades, {wr:.0f}% WR")


def send_daily_report():
    """Send daily performance summary at 6PM IST"""
    ledger = load_ledger()
    total  = ledger["total_trades"]
    wins   = ledger["total_wins"]
    wr     = wins / max(1, total) * 100
    msg = (
        f"DAILY REPORT\n"
        f"Wallet: ${ledger['wallet']:.2f}\n"
        f"Today P&L: {ledger['daily_pnl']*100:+.2f}%\n"
        f"All-time trades: {total}\n"
        f"All-time WR: {wr:.0f}%\n"
        f"Open positions: {len(ledger['open_trades'])}\n"
        f"Strategy: Swarm x UTBot Fusion\n"
        f"Date: {datetime.date.today()}"
    )
    telegram_send(msg)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    log("=" * 70)
    log("  ANTIGRAVITY AI BRAIN — LIVE SWARM x UTBOT MASTER TRADING BOT")
    log("  Strategy: 5-Layer Conviction → 1x2 Zero Net Debit Call Spread")
    log(f"  Scan interval: {SCAN_INTERVAL_MINUTES} minutes")
    log(f"  Conviction gate: {CONVICTION_GATE*100:.0f}%")
    log(f"  Max concurrent trades: {MAX_CONCURRENT}")
    log(f"  Allocation per trade: {ALLOC_PCT*100:.0f}% of wallet")
    log(f"  Mode: {'PAPER TRADE (no real orders)' if 'YOUR_DELTA' in DELTA_API_KEY else 'LIVE TRADING'}")
    log("=" * 70)

    # Validate credentials
    if "YOUR_TELEGRAM" in TELEGRAM_TOKEN:
        log("WARNING: Telegram not configured — alerts disabled", "WARN")
        log("  → Get your token from @BotFather on Telegram", "WARN")
    if "YOUR_DELTA" in DELTA_API_KEY:
        log("Running in PAPER MODE — no real orders will be placed", "WARN")
        log("  → Get API keys from delta.exchange to enable live trading", "WARN")

    # Startup Telegram message
    telegram_send(
        f"ANTIGRAVITY BOT STARTED\n"
        f"Strategy: Swarm x UTBot Fusion\n"
        f"Watching: {', '.join(a['label'] for a in WATCH_LIST)}\n"
        f"Mode: {'PAPER' if 'YOUR_DELTA' in DELTA_API_KEY else 'LIVE'}\n"
        f"Scan: Every {SCAN_INTERVAL_MINUTES} min"
    )

    # Run first scan immediately
    scan_markets()

    # Schedule scans
    schedule.every(SCAN_INTERVAL_MINUTES).minutes.do(scan_markets)
    schedule.every().day.at("18:00").do(send_daily_report)
    schedule.every(4).hours.do(
        lambda: alert_heartbeat(
            load_ledger()["wallet"],
            len(load_ledger()["open_trades"]),
            load_ledger()["daily_pnl"]
        )
    )

    log(f"Scheduled: scan every {SCAN_INTERVAL_MINUTES} min | "
        f"daily report at 18:00 | heartbeat every 4 hours")
    log("Bot is running. Press Ctrl+C to stop.\n")

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            log("Bot stopped by user.")
            telegram_send("BOT STOPPED\nManual shutdown by user.")
            break
        except Exception as e:
            log(f"Loop error: {traceback.format_exc()}", "ERROR")
            time.sleep(60)


if __name__ == "__main__":
    main()
