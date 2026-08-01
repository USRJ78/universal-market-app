"""
==============================================================================
  AUTONOMOUS INDEPENDENT DAEMON: OUROBOROS QUANTUM CONVEXITY ENGINE V6.0
==============================================================================
  Runs continuously in the background, scanning multi-asset markets every 60s,
  evaluating Hurst Exponent regimes, updating Swarm Conviction Scores,
  and syncing live state with the Antigravity AI Brain.
==============================================================================
"""

import os, sys, time, datetime, json
import numpy as np
import pandas as pd
import yfinance as yf

# Unbuffered line output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUTPUT_DIR, "ouroboros_daemon.log")
BRAIN_STATE_FILE = os.path.join(os.path.dirname(OUTPUT_DIR), "antigravity_ai_brain", "ai_brain_state.json")

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_daemon():
    log("===========================================================================")
    log("  LAUNCHING AUTONOMOUS INDEPENDENT DAEMON — OUROBOROS QUANTUM V6.0")
    log("===========================================================================")
    log(f"  PID            : {os.getpid()}")
    log(f"  Log File       : {LOG_FILE}")
    log(f"  Brain State    : {BRAIN_STATE_FILE}")

    tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "^NSEI", "^NSEBANK", "RELIANCE.NS"]
    
    cycle = 0
    while True:
        cycle += 1
        log(f"\n--- [CYCLE #{cycle:04d}] SCANNING MARKETS ({len(tickers)} ASSETS) ---")

        radar_results = []
        for t in tickers:
            try:
                df = yf.download(t, period="60d", interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                if df is not None and len(df) > 30:
                    close = df["Close"]
                    high = df["High"]
                    low = df["Low"]
                    vol = df["Volume"]

                    c = float(close.iloc[-1])
                    e20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
                    e50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
                    h52 = float(close.rolling(52).max().iloc[-1]) if len(close) >= 52 else c

                    hl = high - low
                    hc = (high - close.shift()).abs()
                    lc = (low - close.shift()).abs()
                    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                    atr10 = float(tr.rolling(10).mean().iloc[-1])
                    atr50 = float(tr.rolling(50).mean().iloc[-1])
                    sqz = atr10 / (atr50 + 1e-9)

                    # Hurst Proxy
                    ret1 = close.pct_change(1)
                    ret5 = close.pct_change(5)
                    std1 = float(ret1.rolling(20).std().iloc[-1])
                    std5 = float(ret5.rolling(20).std().iloc[-1])
                    h_val = float(np.clip(0.50 + 0.25 * np.log2((std5 / (std1 * np.sqrt(5) + 1e-9)) + 1e-9), 0.1, 0.9))

                    # Swarm Conviction Matrix
                    c1 = 30 if (c >= h52 * 0.96) else 15 if (c >= e20 > e50) else 0
                    c2 = 30 if (sqz <= 0.92) else 15 if (sqz <= 1.00) else 0
                    c3 = 25 if (c > e20) else 0
                    c4 = 15 if (h_val > 0.52 or h_val < 0.45) else 0

                    conviction = int(c1 + c2 + c3 + c4)

                    regime = "MEAN REVERTING" if h_val < 0.45 else "PARABOLIC MOMENTUM" if h_val > 0.52 else "NEUTRAL"
                    action = "EXECUTE ZERO DEBIT SPREAD" if conviction >= 75 else "MONITORING"

                    log(f"  {t:12s} | Price: ${c:10,.2f} | Conviction: {conviction}% | Regime: {regime:18s} | Action: {action}")

                    radar_results.append({
                        "asset": t, "price": c, "conviction": conviction,
                        "regime": regime, "action": action, "squeeze": round(sqz, 3), "hurst": round(h_val, 3)
                    })

            except Exception as e:
                log(f"  [ERROR] Scanning {t}: {e}")

        # Update AI Brain State JSON
        try:
            brain_state = {
                "daemon": "Ouroboros Quantum V6.0 Autonomous Engine",
                "pid": os.getpid(),
                "status": "RUNNING_INDEPENDENTLY",
                "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cycle": cycle,
                "radar_matrix": radar_results
            }
            with open(BRAIN_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(brain_state, f, indent=2)
            log("  [OK] Brain State JSON successfully updated.")
        except Exception as e:
            log(f"  [WARN] Failed to write brain state JSON: {e}")

        log("  [SLEEP] Waiting 60 seconds for next cycle scan ...")
        time.sleep(60)


if __name__ == "__main__":
    run_daemon()
