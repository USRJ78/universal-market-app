"""
==============================================================================
  ANTIGRAVITY AI BRAIN — FULL WEB DASHBOARD (Replica of Desktop App)
==============================================================================
  Complete web replica of brain_dashboard.py (PyQt6) for browser + mobile.
  Features:
  - All 19 Strategies with Execute/Stop buttons
  - Live BTC Price Chart (Chart.js)
  - Real-time P&L, Balance, Positions
  - AI Brain Log Feed
  - Strategy Performance Table
  - Exchange Connection Status
  - One-click strategy launcher
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, subprocess, threading, requests
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ─── CONFIG ────────────────────────────────────────────────
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"
ANALYSIS_DIR     = os.path.dirname(os.path.abspath(__file__))
BASE_DIR         = os.path.dirname(ANALYSIS_DIR)
BRAIN_DIR        = os.path.join(BASE_DIR, "antigravity_ai_brain")

app = Flask(__name__)

# Track running strategy processes
running_processes = {}

# ─── ALL 19 STRATEGIES ─────────────────────────────────────
STRATEGIES = [
    {"id": "swarm_call_spread",      "name": "Swarm Bot 1x2 Call Spread",           "icon": "🤖", "cagr": "34.55x PF",  "win": "55.1%", "mdd": "-4.7%",   "script": "swarm_delta_live_executor.py",    "color": "#6c63ff"},
    {"id": "adaptive_200_hunter",    "name": "Adaptive $200 Target Hunter",          "icon": "🎯", "cagr": "+41%/day",   "win": "78.0%", "mdd": "-13.4%",  "script": "adaptive_200_hunter.py",          "color": "#00d4aa"},
    {"id": "autonomous_llm_agent",   "name": "Autonomous AI LLM Agent",             "icon": "🧠", "cagr": "+74.7%",     "win": "74.7%", "mdd": "-5.0%",   "script": "autonomous_quant_llm_agent.py",   "color": "#f59e0b"},
    {"id": "kinetic_hyper_surge",    "name": "Kinetic Hyper-Surge Rust Engine V7",  "icon": "⚡", "cagr": "1535.79%",  "win": "49.0%", "mdd": "-2.0%",   "script": "master_1000pct_cagr_blueprint.py","color": "#ef4444"},
    {"id": "post_tax_1000pct",       "name": "Post-Tax +1000% Net Compounder",      "icon": "💰", "cagr": "32M%",       "win": "25.7%", "mdd": "-7.3%",   "script": "post_tax_1000pct_cagr_engine.py", "color": "#10b981"},
    {"id": "kakushadze_residual",    "name": "Kakushadze Residual Momentum",        "icon": "📊", "cagr": "20.60%",     "win": "53.3%", "mdd": "-20.4%",  "script": "kakushadze_151_quant_strategy.py","color": "#3b82f6"},
    {"id": "power_hour_gamma",       "name": "14:00 Power Hour Gamma Surge",        "icon": "🚀", "cagr": "19.86%",     "win": "99.9%", "mdd": "-1.85%",  "script": "mine_intraday_patterns.py",       "color": "#8b5cf6"},
    {"id": "vwap_reversion",         "name": "11:30 VWAP Reversion Engine",         "icon": "📈", "cagr": "+81.2%",     "win": "81.2%", "mdd": "-3.2%",   "script": "mine_intraday_patterns.py",       "color": "#06b6d4"},
    {"id": "volume_delta_reversal",  "name": "Volume-Delta Reversal Signal",        "icon": "🔄", "cagr": "+72.5%",     "win": "72.5%", "mdd": "-4.1%",   "script": "mine_intraday_patterns.py",       "color": "#f97316"},
    {"id": "orb_15min",              "name": "15-Min Opening Range Breakout",       "icon": "📉", "cagr": "+68.4%",     "win": "68.4%", "mdd": "-5.8%",   "script": "mine_intraday_patterns.py",       "color": "#ec4899"},
    {"id": "geopolitical_vix",       "name": "Geopolitical VIX Normalization",      "icon": "🌍", "cagr": "+84.5%",     "win": "84.5%", "mdd": "-2.9%",   "script": "mine_market_timing_patterns.py",  "color": "#14b8a6"},
    {"id": "european_vwap",          "name": "European Open VWAP Momentum",         "icon": "🇪🇺", "cagr": "+81.2%",    "win": "81.2%", "mdd": "-3.5%",   "script": "mine_market_timing_patterns.py",  "color": "#6366f1"},
    {"id": "us_crypto_volume",       "name": "US Open Crypto Volume Surge",         "icon": "🇺🇸", "cagr": "+78.4%",    "win": "78.4%", "mdd": "-4.2%",   "script": "mine_market_timing_patterns.py",  "color": "#84cc16"},
    {"id": "bar_squeeze",            "name": "14-21 Bar ATR Squeeze Breakout",      "icon": "💥", "cagr": "+76.2%",     "win": "76.2%", "mdd": "-3.8%",   "script": "mine_market_timing_patterns.py",  "color": "#f43f5e"},
    {"id": "totm_inflows",           "name": "Turn of Month Institutional Inflows", "icon": "📅", "cagr": "+71.8%",     "win": "71.8%", "mdd": "-5.1%",   "script": "mine_market_timing_patterns.py",  "color": "#a855f7"},
    {"id": "real_world_friction",    "name": "Real-World Friction Audit Engine",    "icon": "🔬", "cagr": "+98.28%",    "win": "52.5%", "mdd": "-4.7%",   "script": "real_world_friction_backtest.py", "color": "#0ea5e9"},
    {"id": "all_in_100pct",          "name": "All-In 100% Portfolio Compounder",    "icon": "🎰", "cagr": "+60M%",      "win": "55.1%", "mdd": "-20.3%",  "script": "all_in_100pct_cagr_backtest.py",  "color": "#dc2626"},
    {"id": "swarm_10yr_backtest",    "name": "Swarm Call Spread 10-Year Backtest",  "icon": "📋", "cagr": "34.55x PF",  "win": "55.1%", "mdd": "-4.7%",   "script": "swarm_call_spread_10yr_backtest.py","color": "#7c3aed"},
    {"id": "continuous_learning",    "name": "Continuous Learning RL Agent",        "icon": "🔮", "cagr": "Gen#2",      "win": "74.7%", "mdd": "-5.0%",   "script": "continuous_learning_quant_agent.py","color": "#059669"},
]

# ─── DELTA API ─────────────────────────────────────────────
def sign(s, m):
    return hmac.new(s.encode(), m.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts  = str(int(time.time()))
    sig = sign(DELTA_API_SECRET, "GET" + ts + path)
    try:
        r = requests.get(DELTA_BASE_URL + path,
            headers={"api-key": DELTA_API_KEY, "timestamp": ts,
                     "signature": sig, "Content-Type": "application/json"}, timeout=8)
        return r.json() if r.content else {}
    except: return {}

def get_balance():
    data = delta_get("/v2/wallet/balances")
    try:
        for b in data.get("result", []):
            if b.get("asset_symbol") in ["USDT","USD"]:
                return float(b.get("available_balance", 0))
    except: pass
    return 0.0

def get_positions():
    data = delta_get("/v2/positions/margined")
    out  = []
    try:
        for p in (data.get("result") or []):
            size = float(p.get("size", 0))
            if abs(size) > 0:
                out.append({
                    "symbol": p.get("product", {}).get("symbol", "BTC-PERP"),
                    "size":   size,
                    "entry":  float(p.get("entry_price", 0)),
                    "side":   "LONG" if size > 0 else "SHORT",
                    "pnl":    float(p.get("realized_pnl", 0))
                })
    except: pass
    return out

def get_btc_price():
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="2d", interval="1h", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        if len(df) > 0:
            return float(df["Close"].iloc[-1])
    except: pass
    return 65000.0

def get_btc_chart_data():
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="7d", interval="1h", progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)
        labels = [str(i.strftime("%m/%d %H:%M")) for i in df.index[-48:]]
        prices = [round(float(v), 2) for v in df["Close"].iloc[-48:]]
        return {"labels": labels, "prices": prices}
    except: return {"labels": [], "prices": []}

def read_logs(n=30):
    logs = []
    for fname in ["adaptive_200_hunt.log", "swarm_call_spread_live.log",
                  "ai_brain.log", "swarm_delta_live.log", "target_200_hunt.log"]:
        for d in [ANALYSIS_DIR, BRAIN_DIR]:
            fpath = os.path.join(d, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for line in lines[-20:]:
                        line = line.strip()
                        if line: logs.append({"source": fname.replace(".log",""), "msg": line})
                except: pass
    return sorted(logs, key=lambda x: x["msg"])[-n:]

# ─── API ROUTES ─────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    balance   = get_balance()
    positions = get_positions()
    btc       = get_btc_price()
    logs      = read_logs(25)
    running   = list(running_processes.keys())
    return jsonify({
        "balance":    round(balance, 2),
        "btc_price":  round(btc, 2),
        "positions":  positions,
        "logs":       logs,
        "running":    running,
        "gain":       round(balance - 138.57, 2),
        "gain_pct":   round((balance / 138.57 - 1) * 100, 2),
        "progress":   round(min(100, max(0, (balance-138.57)/(200-138.57)*100)), 1),
        "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "exchange":   "Delta Exchange Testnet",
        "connected":  balance > 0
    })

@app.route("/api/chart")
def api_chart():
    return jsonify(get_btc_chart_data())

@app.route("/api/strategies")
def api_strategies():
    result = []
    for s in STRATEGIES:
        s2 = dict(s)
        s2["running"] = s["id"] in running_processes
        result.append(s2)
    return jsonify(result)

@app.route("/api/execute/<strategy_id>", methods=["POST"])
def api_execute(strategy_id):
    strat = next((s for s in STRATEGIES if s["id"] == strategy_id), None)
    if not strat:
        return jsonify({"success": False, "error": "Strategy not found"})
    if strategy_id in running_processes:
        return jsonify({"success": False, "error": "Already running"})
    script = os.path.join(ANALYSIS_DIR, strat["script"])
    if not os.path.exists(script):
        return jsonify({"success": False, "error": f"Script not found: {strat['script']}"})
    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            cwd=ANALYSIS_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        running_processes[strategy_id] = proc
        return jsonify({"success": True, "message": f"Started {strat['name']}", "pid": proc.pid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/stop/<strategy_id>", methods=["POST"])
def api_stop(strategy_id):
    if strategy_id == "all":
        for sid, proc in list(running_processes.items()):
            try: proc.terminate()
            except: pass
        running_processes.clear()
        return jsonify({"success": True, "message": "All strategies stopped"})
    if strategy_id not in running_processes:
        return jsonify({"success": False, "error": "Not running"})
    try:
        running_processes[strategy_id].terminate()
        del running_processes[strategy_id]
        return jsonify({"success": True, "message": "Stopped"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/place_order", methods=["POST"])
def api_place_order():
    data = request.json
    side = data.get("side", "buy")
    size = int(data.get("size", 1))
    ts   = str(int(time.time()))
    body = json.dumps({"product_id": 84, "size": size, "side": side, "order_type": "market_order"})
    sig  = sign(DELTA_API_SECRET, "POST" + ts + "/v2/orders" + body)
    try:
        r = requests.post(DELTA_BASE_URL + "/v2/orders", data=body,
            headers={"api-key": DELTA_API_KEY, "timestamp": ts, "signature": sig,
                     "Content-Type": "application/json"}, timeout=10)
        res = r.json()
        return jsonify({"success": res.get("success", False),
                        "order_id": res.get("result", {}).get("id", "N/A")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/close_all", methods=["POST"])
def api_close_all():
    positions = get_positions()
    closed = 0
    for pos in positions:
        size = abs(float(pos.get("size", 0)))
        if size > 0:
            side = "sell" if float(pos["size"]) > 0 else "buy"
            ts   = str(int(time.time()))
            body = json.dumps({"product_id": 84, "size": int(size), "side": side,
                               "order_type": "market_order", "reduce_only": True})
            sig  = sign(DELTA_API_SECRET, "POST" + ts + "/v2/orders" + body)
            requests.post(DELTA_BASE_URL + "/v2/orders", data=body,
                headers={"api-key": DELTA_API_KEY, "timestamp": ts, "signature": sig,
                         "Content-Type": "application/json"}, timeout=10)
            closed += 1
    return jsonify({"success": True, "closed": closed})

# ─── MAIN WEB UI ────────────────────────────────────────────
@app.route("/")
def index():
    return MAIN_HTML

MAIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ Antigravity AI Brain</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg:#07080f; --sidebar:#0d0f1a; --card:rgba(255,255,255,0.04);
  --border:rgba(255,255,255,0.08); --accent:#6c63ff; --green:#00d4aa;
  --red:#ff4d6d; --yellow:#ffd60a; --text:#e2e8f0; --muted:#64748b;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;height:100vh;overflow:hidden}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 10%,rgba(108,99,255,0.07) 0,transparent 50%),radial-gradient(ellipse at 80% 90%,rgba(0,212,170,0.05) 0,transparent 50%);pointer-events:none;z-index:0}

/* SIDEBAR */
.sidebar{width:280px;min-width:280px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;overflow:hidden;position:relative;z-index:10}
.sidebar-header{padding:20px 16px 16px;border-bottom:1px solid var(--border)}
.logo{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.logo-icon{width:38px;height:38px;background:linear-gradient(135deg,var(--accent),var(--green));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 0 20px rgba(108,99,255,0.3)}
.logo-text h2{font-size:14px;font-weight:700}
.logo-text p{font-size:11px;color:var(--muted)}
.exchange-badge{display:flex;align-items:center;gap:6px;background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.15);border-radius:8px;padding:8px 10px;font-size:11px}
.pulse{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

.sidebar-balance{padding:12px 16px;border-bottom:1px solid var(--border)}
.bal-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.bal-value{font-size:22px;font-weight:800;color:var(--accent)}
.bal-sub{font-size:11px;color:var(--muted);margin-top:2px}

.sidebar-nav{padding:8px 0;overflow-y:auto;flex:1}
.nav-section{padding:6px 16px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:8px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;border-radius:0;transition:background 0.15s;font-size:12px;border-left:2px solid transparent}
.nav-item:hover{background:rgba(255,255,255,0.04)}
.nav-item.active{background:rgba(108,99,255,0.1);border-left-color:var(--accent);color:var(--accent)}
.nav-item-icon{font-size:14px;width:20px;text-align:center}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;position:relative;z-index:1}
.topbar{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:rgba(7,8,15,0.8);backdrop-filter:blur(20px)}
.page-title{font-size:16px;font-weight:700}
.topbar-right{display:flex;gap:8px;align-items:center}
.btn{padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif}
.btn:hover{border-color:var(--accent);background:rgba(108,99,255,0.1)}
.btn-green{background:rgba(0,212,170,0.15);border-color:rgba(0,212,170,0.3);color:var(--green)}
.btn-red{background:rgba(255,77,109,0.15);border-color:rgba(255,77,109,0.3);color:var(--red)}
.btn-accent{background:linear-gradient(135deg,var(--accent),#8b5cf6);border:none;color:white;box-shadow:0 0 20px rgba(108,99,255,0.3)}
#btc-price{font-family:'JetBrains Mono';font-size:13px;color:var(--yellow)}

.content{flex:1;overflow-y:auto;padding:20px}
.content::-webkit-scrollbar{width:4px}
.content::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}

/* PAGES */
.page{display:none}
.page.active{display:block}

/* CARDS */
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;backdrop-filter:blur(20px);transition:border-color 0.2s,box-shadow 0.2s}
.card:hover{border-color:rgba(108,99,255,0.2);box-shadow:0 0 30px rgba(108,99,255,0.08)}
.card-label{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.card-value{font-size:24px;font-weight:800;letter-spacing:-0.5px}
.card-sub{font-size:11px;color:var(--muted);margin-top:4px}
.g{color:var(--green)}.r{color:var(--red)}.y{color:var(--yellow)}.a{color:var(--accent)}

/* PROGRESS */
.progress-track{width:100%;height:10px;background:rgba(255,255,255,0.06);border-radius:999px;overflow:hidden;margin:10px 0}
.progress-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--accent),var(--green));transition:width 1s ease;box-shadow:0 0 12px rgba(108,99,255,0.4)}

/* CHART */
.chart-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;margin-bottom:16px}
.chart-wrap canvas{max-height:220px}

/* STRATEGIES */
.strat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.strat-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;transition:all 0.2s;position:relative;overflow:hidden}
.strat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;opacity:0.6}
.strat-card:hover{border-color:rgba(255,255,255,0.15);transform:translateY(-1px)}
.strat-header{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.strat-icon{font-size:22px;width:36px;height:36px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.05);border-radius:10px}
.strat-name{font-size:13px;font-weight:700;line-height:1.3}
.strat-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.strat-tag{padding:2px 8px;border-radius:999px;font-size:10px;font-weight:600}
.tag-cagr{background:rgba(108,99,255,0.15);color:var(--accent)}
.tag-win{background:rgba(0,212,170,0.15);color:var(--green)}
.tag-mdd{background:rgba(255,77,109,0.15);color:var(--red)}
.strat-actions{display:flex;gap:8px}
.btn-execute{flex:1;padding:8px;border-radius:8px;border:none;background:linear-gradient(135deg,var(--accent),#8b5cf6);color:white;font-size:12px;font-weight:700;cursor:pointer;transition:opacity 0.2s;font-family:'Inter',sans-serif}
.btn-execute:hover{opacity:0.85}
.btn-stop-strat{padding:8px 12px;border-radius:8px;border:1px solid rgba(255,77,109,0.3);background:rgba(255,77,109,0.1);color:var(--red);font-size:12px;font-weight:700;cursor:pointer;font-family:'Inter',sans-serif}
.running-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;background:rgba(0,212,170,0.15);color:var(--green);margin-left:auto}

/* LOG */
.log-feed{background:rgba(0,0,0,0.4);border:1px solid var(--border);border-radius:12px;padding:12px;height:300px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.8}
.log-feed::-webkit-scrollbar{width:4px}
.log-feed::-webkit-scrollbar-thumb{background:var(--border)}
.log-line{color:#64748b;word-break:break-all}
.log-buy{color:#00d4aa}.log-sell{color:#ff4d6d}.log-win{color:#ffd60a}.log-regime{color:#a78bfa}

/* POSITIONS */
.pos-empty{text-align:center;padding:24px;color:var(--muted);font-size:12px}
.pos-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)}
.pos-row:last-child{border-bottom:none}
.pos-badge{padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700}
.long{background:rgba(0,212,170,0.15);color:var(--green)}.short{background:rgba(255,77,109,0.15);color:var(--red)}

/* MANUAL TRADE */
.trade-box{display:grid;grid-template-columns:1fr 1fr auto auto;gap:8px;align-items:end}
.form-group{display:flex;flex-direction:column;gap:4px}
.form-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:1px}
.form-input{padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--text);font-size:13px;font-family:'Inter',sans-serif}
.form-select{padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--text);font-size:13px;font-family:'Inter',sans-serif}

/* MOBILE */
@media(max-width:768px){
  .sidebar{position:fixed;left:-280px;z-index:100;transition:left 0.3s;height:100vh}
  .sidebar.open{left:0}
  .grid-4{grid-template-columns:repeat(2,1fr)}
  .trade-box{grid-template-columns:1fr 1fr;grid-template-rows:auto auto}
  .main{width:100vw}
  .topbar{padding:12px 14px}
  .content{padding:12px}
}
.menu-btn{display:none;background:none;border:none;color:var(--text);font-size:20px;cursor:pointer;padding:4px}
@media(max-width:768px){.menu-btn{display:block}}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99}
.overlay.open{display:block}

.section-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;margin-top:4px}
.toast{position:fixed;bottom:24px;right:24px;background:#1e293b;border:1px solid var(--border);border-radius:12px;padding:12px 16px;font-size:13px;font-weight:600;z-index:200;opacity:0;transform:translateY(10px);transition:all 0.3s;pointer-events:none}
.toast.show{opacity:1;transform:translateY(0)}
</style>
</head>
<body>

<div class="overlay" id="overlay" onclick="closeSidebar()"></div>

<!-- SIDEBAR -->
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="logo">
      <div class="logo-icon">⚡</div>
      <div class="logo-text">
        <h2>Antigravity AI Brain</h2>
        <p>Autonomous Trading System</p>
      </div>
    </div>
    <div class="exchange-badge">
      <div class="pulse"></div>
      <span id="conn-status">Delta Exchange Testnet</span>
    </div>
  </div>

  <div class="sidebar-balance">
    <div class="bal-label">Live Balance</div>
    <div class="bal-value" id="sb-balance">$---</div>
    <div class="bal-sub" id="sb-pnl">Loading...</div>
  </div>

  <div class="sidebar-nav">
    <div class="nav-section">Navigation</div>
    <div class="nav-item active" onclick="showPage('dashboard')">
      <div class="nav-item-icon">📊</div> Dashboard
    </div>
    <div class="nav-item" onclick="showPage('strategies')">
      <div class="nav-item-icon">🤖</div> Strategies
    </div>
    <div class="nav-item" onclick="showPage('trade')">
      <div class="nav-item-icon">⚡</div> Manual Trade
    </div>
    <div class="nav-item" onclick="showPage('logs')">
      <div class="nav-item-icon">📡</div> Live Logs
    </div>
    <div class="nav-section">Quick Actions</div>
    <div class="nav-item" onclick="stopAll()" style="color:var(--red)">
      <div class="nav-item-icon">🛑</div> Stop All Strategies
    </div>
    <div class="nav-item" onclick="closeAllPositions()" style="color:var(--yellow)">
      <div class="nav-item-icon">🔒</div> Close All Positions
    </div>
  </div>
</div>

<!-- MAIN -->
<div class="main">
  <!-- TOPBAR -->
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px">
      <button class="menu-btn" onclick="openSidebar()">☰</button>
      <div class="page-title" id="page-title">Dashboard</div>
    </div>
    <div class="topbar-right">
      <span id="btc-price">BTC $---</span>
      <span style="font-size:11px;color:var(--muted)" id="clock">--:--:-- IST</span>
    </div>
  </div>

  <!-- CONTENT -->
  <div class="content">

    <!-- DASHBOARD PAGE -->
    <div class="page active" id="page-dashboard">
      <div class="grid-4">
        <div class="card">
          <div class="card-label">💰 Balance</div>
          <div class="card-value a" id="d-balance">$---</div>
          <div class="card-sub">Available Margin</div>
        </div>
        <div class="card">
          <div class="card-label">📈 Net PnL</div>
          <div class="card-value" id="d-pnl">---</div>
          <div class="card-sub">vs $138.57 baseline</div>
        </div>
        <div class="card">
          <div class="card-label">🎯 Target Progress</div>
          <div class="card-value y" id="d-progress">0%</div>
          <div class="card-sub">$138.57 → $200.00</div>
        </div>
        <div class="card">
          <div class="card-label">🤖 Active Strategies</div>
          <div class="card-value g" id="d-running">0</div>
          <div class="card-sub">Running now</div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="card" style="margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-size:13px;font-weight:600">24-Hour $200 Target</div>
          <div style="font-size:18px;font-weight:800;color:var(--accent)" id="d-pct">0%</div>
        </div>
        <div class="progress-track"><div class="progress-fill" id="d-bar" style="width:0%"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted)">
          <span>$138.57</span><span id="d-current">$---</span><span>$200</span>
        </div>
      </div>

      <!-- BTC Chart -->
      <div class="chart-wrap">
        <div class="section-title">BTC/USD — 48H Price Chart</div>
        <canvas id="btcChart"></canvas>
      </div>

      <!-- Positions -->
      <div class="card">
        <div class="section-title">📊 Active Positions</div>
        <div id="d-positions"><div class="pos-empty">⏳ Loading positions...</div></div>
      </div>
    </div>

    <!-- STRATEGIES PAGE -->
    <div class="page" id="page-strategies">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div style="font-size:14px;font-weight:700">All 19 Quantitative Strategies</div>
        <button class="btn btn-red" onclick="stopAll()">🛑 Stop All</button>
      </div>
      <div class="strat-grid" id="strat-grid">
        <!-- Populated by JS -->
      </div>
    </div>

    <!-- MANUAL TRADE PAGE -->
    <div class="page" id="page-trade">
      <div class="card" style="margin-bottom:16px">
        <div class="section-title">⚡ Manual BTC Perpetual Order</div>
        <div class="trade-box">
          <div class="form-group">
            <div class="form-label">Side</div>
            <select class="form-select" id="t-side">
              <option value="buy">BUY (Long)</option>
              <option value="sell">SELL (Short)</option>
            </select>
          </div>
          <div class="form-group">
            <div class="form-label">Size (Contracts)</div>
            <input class="form-input" type="number" id="t-size" value="1" min="1">
          </div>
          <button class="btn btn-green" onclick="placeOrder()" style="height:38px">✅ Place Order</button>
          <button class="btn btn-red" onclick="closeAllPositions()" style="height:38px">🔒 Close All</button>
        </div>
      </div>

      <div class="card">
        <div class="section-title">📊 Current Positions</div>
        <div id="t-positions"><div class="pos-empty">⏳ Loading...</div></div>
      </div>
    </div>

    <!-- LOGS PAGE -->
    <div class="page" id="page-logs">
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div class="section-title" style="margin:0">📡 Live AI Brain Log Feed</div>
          <button class="btn" onclick="fetchLogs()">🔄 Refresh</button>
        </div>
        <div class="log-feed" id="log-feed">Connecting...</div>
      </div>
    </div>

  </div><!-- /content -->
</div><!-- /main -->

<div class="toast" id="toast"></div>

<script>
let btcChart = null;

// ── NAVIGATION ────────────────────────────────────────
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  document.getElementById('page-title').textContent = {
    dashboard:'Dashboard', strategies:'Strategies',
    trade:'Manual Trade', logs:'Live Logs'
  }[id] || id;
  event?.currentTarget?.classList.add('active');
  closeSidebar();
  if (id === 'strategies') loadStrategies();
  if (id === 'logs') fetchLogs();
}

function openSidebar()  { document.getElementById('sidebar').classList.add('open'); document.getElementById('overlay').classList.add('open'); }
function closeSidebar() { document.getElementById('sidebar').classList.remove('open'); document.getElementById('overlay').classList.remove('open'); }

// ── TOAST ────────────────────────────────────────────
function toast(msg, type='info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.color = type==='error' ? '#ff4d6d' : type==='success' ? '#00d4aa' : '#e2e8f0';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

// ── STATUS ───────────────────────────────────────────
async function fetchStatus() {
  try {
    const d = await fetch('/api/status').then(r => r.json());

    // Sidebar
    document.getElementById('sb-balance').textContent = '$'+d.balance.toFixed(2);
    document.getElementById('sb-pnl').textContent = (d.gain >= 0 ? '+' : '') + '$'+d.gain.toFixed(2) + ' ('+d.gain_pct.toFixed(2)+'%)';
    document.getElementById('sb-pnl').style.color = d.gain >= 0 ? 'var(--green)' : 'var(--red)';

    // Dashboard metrics
    document.getElementById('d-balance').textContent = '$'+d.balance.toFixed(2);
    const pnlEl = document.getElementById('d-pnl');
    pnlEl.textContent = (d.gain >= 0 ? '+' : '') + '$'+d.gain.toFixed(2) + ' ('+d.gain_pct.toFixed(2)+'%)';
    pnlEl.className = 'card-value '+(d.gain >= 0 ? 'g' : 'r');
    document.getElementById('d-progress').textContent = d.progress.toFixed(1)+'%';
    document.getElementById('d-running').textContent = d.running.length;
    document.getElementById('d-pct').textContent = d.progress.toFixed(1)+'%';
    document.getElementById('d-bar').style.width = d.progress+'%';
    document.getElementById('d-current').textContent = '$'+d.balance.toFixed(2);

    // BTC Price
    document.getElementById('btc-price').textContent = 'BTC $'+d.btc_price.toLocaleString();

    // Positions
    const posHtml = d.positions.length === 0
      ? '<div class="pos-empty">💤 No open positions</div>'
      : d.positions.map(p => `
          <div class="pos-row">
            <div><div style="font-weight:600;font-size:13px">${p.symbol}</div>
            <div style="font-size:11px;color:var(--muted)">Entry: $${p.entry.toLocaleString()}</div></div>
            <div style="text-align:right">
              <span class="pos-badge ${p.side==='LONG'?'long':'short'}">${p.side}</span>
              <div style="font-size:11px;color:var(--muted);margin-top:3px">Size: ${Math.abs(p.size)}</div>
            </div>
          </div>`).join('');
    document.getElementById('d-positions').innerHTML = posHtml;
    if (document.getElementById('t-positions'))
      document.getElementById('t-positions').innerHTML = posHtml;

    // Logs
    if (d.logs.length > 0) {
      const logHtml = d.logs.slice().reverse().map(l => {
        let cls = 'log-line';
        if (l.msg.includes('ORDER') && l.msg.includes('buy'))  cls += ' log-buy';
        if (l.msg.includes('ORDER') && l.msg.includes('sell')) cls += ' log-sell';
        if (l.msg.includes('TARGET') || l.msg.includes('HIT') || l.msg.includes('✅')) cls += ' log-win';
        if (l.msg.includes('Regime') || l.msg.includes('Agent')) cls += ' log-regime';
        return `<div class="${cls}">${l.msg}</div>`;
      }).join('');
      document.getElementById('log-feed').innerHTML = logHtml;
    }
  } catch(e) { console.error(e); }
}

// ── CHART ────────────────────────────────────────────
async function loadChart() {
  const d = await fetch('/api/chart').then(r => r.json());
  const ctx = document.getElementById('btcChart').getContext('2d');
  if (btcChart) btcChart.destroy();
  btcChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.labels,
      datasets: [{
        label: 'BTC/USD',
        data: d.prices,
        borderColor: '#6c63ff',
        backgroundColor: 'rgba(108,99,255,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false },
        tooltip: { mode: 'index', intersect: false,
          callbacks: { label: ctx => ' $'+ctx.raw.toLocaleString() }
        }
      },
      scales: {
        x: { ticks: { color:'#64748b', maxTicksLimit:8, font:{size:10} }, grid:{color:'rgba(255,255,255,0.04)'} },
        y: { ticks: { color:'#64748b', font:{size:10}, callback: v => '$'+v.toLocaleString() }, grid:{color:'rgba(255,255,255,0.04)'} }
      }
    }
  });
}

// ── STRATEGIES ───────────────────────────────────────
async function loadStrategies() {
  const strategies = await fetch('/api/strategies').then(r => r.json());
  const grid = document.getElementById('strat-grid');
  grid.innerHTML = strategies.map(s => `
    <div class="strat-card" id="sc-${s.id}" style="--strat-color:${s.color}">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;background:${s.color};opacity:0.7;border-radius:14px 14px 0 0"></div>
      <div class="strat-header">
        <div class="strat-icon">${s.icon}</div>
        <div>
          <div class="strat-name">${s.name}</div>
          ${s.running ? '<div class="running-badge"><div class="pulse"></div> RUNNING</div>' : ''}
        </div>
      </div>
      <div class="strat-meta">
        <span class="strat-tag tag-cagr">📈 ${s.cagr}</span>
        <span class="strat-tag tag-win">✅ ${s.win}</span>
        <span class="strat-tag tag-mdd">⬇️ ${s.mdd}</span>
      </div>
      <div class="strat-actions">
        <button class="btn-execute" onclick="executeStrategy('${s.id}')">
          ${s.running ? '⚡ Running...' : '▶ Execute Strategy'}
        </button>
        ${s.running ? `<button class="btn-stop-strat" onclick="stopStrategy('${s.id}')">■ Stop</button>` : ''}
      </div>
    </div>
  `).join('');
}

async function executeStrategy(id) {
  const res = await fetch('/api/execute/'+id, {method:'POST'}).then(r => r.json());
  if (res.success) {
    toast('✅ '+res.message, 'success');
    await loadStrategies();
  } else {
    toast('❌ '+res.error, 'error');
  }
}

async function stopStrategy(id) {
  const res = await fetch('/api/stop/'+id, {method:'POST'}).then(r => r.json());
  if (res.success) { toast('🛑 Strategy stopped', 'success'); await loadStrategies(); }
  else toast('❌ '+res.error, 'error');
}

async function stopAll() {
  await fetch('/api/stop/all', {method:'POST'});
  toast('🛑 All strategies stopped', 'success');
  await loadStrategies();
}

// ── MANUAL TRADE ─────────────────────────────────────
async function placeOrder() {
  const side = document.getElementById('t-side').value;
  const size = parseInt(document.getElementById('t-size').value);
  const res  = await fetch('/api/place_order', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({side, size})
  }).then(r => r.json());
  if (res.success) toast(`✅ ${side.toUpperCase()} ${size}x placed! ID: ${res.order_id}`, 'success');
  else toast('❌ Order failed: '+res.error, 'error');
}

async function closeAllPositions() {
  const res = await fetch('/api/close_all', {method:'POST'}).then(r => r.json());
  toast(res.closed > 0 ? `🔒 Closed ${res.closed} position(s)` : '💤 No open positions', 'success');
}

// ── LOGS ─────────────────────────────────────────────
async function fetchLogs() {
  const d = await fetch('/api/status').then(r => r.json());
  const logFeed = document.getElementById('log-feed');
  if (d.logs.length > 0) {
    logFeed.innerHTML = d.logs.slice().reverse().map(l => {
      let cls = 'log-line';
      if (l.msg.includes('buy')) cls += ' log-buy';
      if (l.msg.includes('sell')) cls += ' log-sell';
      return `<div class="${cls}">${l.msg}</div>`;
    }).join('');
  }
}

// ── CLOCK ────────────────────────────────────────────
function updateClock() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-IN', {timeZone:'Asia/Kolkata', hour12:false}) + ' IST';
}

// ── INIT ─────────────────────────────────────────────
loadChart();
fetchStatus();
setInterval(fetchStatus, 10000);
setInterval(updateClock, 1000);
setInterval(loadChart, 300000); // Chart refreshes every 5 min
updateClock();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("="*65)
    print("  ⚡ ANTIGRAVITY AI BRAIN — FULL WEB DASHBOARD V2.0")
    print("="*65)
    print(f"  Dashboard : http://140.245.195.162:8080")
    print(f"  Local     : http://localhost:8080")
    print("="*65)
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
