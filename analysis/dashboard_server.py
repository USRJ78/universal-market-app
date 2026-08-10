"""
==============================================================================
  ANTIGRAVITY AI BRAIN — LIVE TRADING DASHBOARD SERVER
==============================================================================
  Flask API + Beautiful Web UI served on Oracle Cloud VM
  Access from ANY device: http://140.245.195.162
  Auto-refreshes every 10 seconds
==============================================================================
"""

import os, sys, time, hmac, hashlib, json, datetime, requests
from flask import Flask, jsonify, send_from_directory

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

# ─── CONFIG ────────────────────────────────────────────────
DELTA_API_KEY    = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
DELTA_BASE_URL   = "https://cdn-ind.testnet.deltaex.org"
STARTING_BALANCE = 138.57
TARGET_BALANCE   = 200.00
HARD_STOP        = 120.00
LOG_DIR          = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(LOG_DIR, "dashboard_static"))

# ─── DELTA API ─────────────────────────────────────────────
def sign(s, m):
    return hmac.new(s.encode(), m.encode(), hashlib.sha256).hexdigest()

def delta_get(path):
    ts  = str(int(time.time()))
    sig = sign(DELTA_API_SECRET, "GET" + ts + path)
    try:
        r = requests.get(DELTA_BASE_URL + path,
            headers={"api-key": DELTA_API_KEY, "timestamp": ts,
                     "signature": sig, "Content-Type": "application/json"},
            timeout=8)
        return r.json() if r.content else {}
    except:
        return {}

def get_balance():
    data = delta_get("/v2/wallet/balances")
    try:
        for b in data.get("result", []):
            if b.get("asset_symbol") in ["USDT", "USD"]:
                return float(b.get("available_balance", 0))
    except:
        pass
    return STARTING_BALANCE

def get_positions():
    data = delta_get("/v2/positions/margined")
    positions = []
    try:
        for p in (data.get("result") or []):
            size = float(p.get("size", 0))
            if abs(size) > 0:
                positions.append({
                    "symbol":     p.get("product", {}).get("symbol", "BTC-PERP"),
                    "size":       size,
                    "entry":      float(p.get("entry_price", 0)),
                    "side":       "LONG" if size > 0 else "SHORT",
                    "pnl":        float(p.get("realized_pnl", 0))
                })
    except:
        pass
    return positions

def read_recent_logs(n=25):
    logs = []
    for fname in ["adaptive_200_hunt.log", "swarm_call_spread_live.log",
                  "target_200_hunt.log", "swarm_delta_live.log"]:
        fpath = os.path.join(LOG_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    line = line.strip()
                    if line:
                        logs.append({"source": fname.replace(".log",""), "msg": line})
            except:
                pass
    return logs[-n:]

# ─── API ENDPOINTS ─────────────────────────────────────────
@app.route("/api/status")
def api_status():
    balance   = get_balance()
    positions = get_positions()
    logs      = read_recent_logs(20)
    gain      = balance - STARTING_BALANCE
    progress  = min(100, max(0, (balance - STARTING_BALANCE) /
                             (TARGET_BALANCE - STARTING_BALANCE) * 100))
    return jsonify({
        "balance":      round(balance, 2),
        "starting":     STARTING_BALANCE,
        "target":       TARGET_BALANCE,
        "hard_stop":    HARD_STOP,
        "gain":         round(gain, 2),
        "gain_pct":     round((balance / STARTING_BALANCE - 1) * 100, 2),
        "progress":     round(progress, 1),
        "positions":    positions,
        "logs":         logs,
        "timestamp":    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_hit":   balance >= TARGET_BALANCE,
        "stop_hit":     balance <= HARD_STOP
    })

@app.route("/")
def dashboard():
    return DASHBOARD_HTML

# ─── DASHBOARD HTML ────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>⚡ Antigravity AI Brain — Live Trading Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:        #060611;
    --card:      rgba(255,255,255,0.04);
    --border:    rgba(255,255,255,0.08);
    --accent:    #6c63ff;
    --accent2:   #00d4aa;
    --red:       #ff4d6d;
    --yellow:    #ffd60a;
    --green:     #00d4aa;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --glow:      0 0 40px rgba(108,99,255,0.15);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }
  body::before {
    content:'';
    position:fixed;
    top:-50%;left:-50%;
    width:200%;height:200%;
    background: radial-gradient(ellipse at 30% 20%, rgba(108,99,255,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 80%, rgba(0,212,170,0.06) 0%, transparent 50%);
    pointer-events:none;
    z-index:0;
  }
  .container { max-width:1200px; margin:0 auto; padding:16px; position:relative; z-index:1; }

  /* HEADER */
  .header {
    display:flex; align-items:center; justify-content:space-between;
    padding: 20px 0 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
  }
  .logo { display:flex; align-items:center; gap:12px; }
  .logo-icon {
    width:44px;height:44px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius:12px;
    display:flex; align-items:center; justify-content:center;
    font-size:22px;
    box-shadow: 0 0 20px rgba(108,99,255,0.4);
  }
  .logo-text h1 { font-size:18px; font-weight:700; letter-spacing:-0.5px; }
  .logo-text p  { font-size:12px; color:var(--muted); margin-top:2px; }
  .live-badge {
    display:flex; align-items:center; gap:6px;
    background: rgba(0,212,170,0.1);
    border: 1px solid rgba(0,212,170,0.2);
    border-radius:20px; padding:6px 12px;
    font-size:12px; font-weight:600; color:var(--green);
  }
  .pulse {
    width:8px;height:8px;border-radius:50%;
    background:var(--green);
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

  /* GRID */
  .grid-3 { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:16px; }
  .grid-2 { display:grid; grid-template-columns:repeat(2,1fr); gap:16px; margin-bottom:16px; }
  @media(max-width:768px) {
    .grid-3 { grid-template-columns:repeat(2,1fr); }
    .grid-2 { grid-template-columns:1fr; }
    .header { flex-direction:column; gap:12px; align-items:flex-start; }
  }
  @media(max-width:480px) {
    .grid-3 { grid-template-columns:1fr; }
  }

  /* CARDS */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius:16px;
    padding:20px;
    backdrop-filter: blur(20px);
    transition: border-color 0.3s, box-shadow 0.3s;
  }
  .card:hover { border-color:rgba(108,99,255,0.3); box-shadow:var(--glow); }
  .card-label { font-size:11px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; }
  .card-value { font-size:28px; font-weight:800; letter-spacing:-1px; }
  .card-sub   { font-size:12px; color:var(--muted); margin-top:6px; }
  .val-green { color:var(--green); }
  .val-red   { color:var(--red); }
  .val-yellow{ color:var(--yellow); }
  .val-accent{ color:var(--accent); }

  /* PROGRESS BAR */
  .progress-card { grid-column: 1 / -1; }
  .progress-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }
  .progress-title  { font-size:14px; font-weight:600; }
  .progress-pct    { font-size:24px; font-weight:800; color:var(--accent); }
  .progress-track  {
    width:100%; height:14px;
    background:rgba(255,255,255,0.06);
    border-radius:999px; overflow:hidden;
    position:relative;
  }
  .progress-fill {
    height:100%; border-radius:999px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    transition: width 1s cubic-bezier(0.4,0,0.2,1);
    position:relative;
    box-shadow: 0 0 16px rgba(108,99,255,0.5);
  }
  .progress-fill::after {
    content:'';
    position:absolute; right:0; top:0; bottom:0; width:4px;
    background:white; border-radius:999px; opacity:0.8;
    animation: shimmer 1.5s ease-in-out infinite;
  }
  @keyframes shimmer { 0%,100%{opacity:0.5} 50%{opacity:1} }
  .progress-labels { display:flex; justify-content:space-between; margin-top:8px; font-size:11px; color:var(--muted); }

  /* POSITIONS TABLE */
  .positions-empty {
    text-align:center; padding:30px; color:var(--muted); font-size:13px;
  }
  .pos-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:12px 0; border-bottom:1px solid var(--border);
    font-size:13px;
  }
  .pos-row:last-child { border-bottom:none; }
  .pos-badge {
    padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700;
  }
  .pos-long  { background:rgba(0,212,170,0.15); color:var(--green); }
  .pos-short { background:rgba(255,77,109,0.15); color:var(--red); }

  /* LOG FEED */
  .log-feed {
    background:rgba(0,0,0,0.3);
    border:1px solid var(--border);
    border-radius:12px;
    padding:16px;
    max-height:320px;
    overflow-y:auto;
    font-family:'JetBrains Mono', monospace;
    font-size:11px;
    line-height:1.7;
  }
  .log-feed::-webkit-scrollbar { width:4px; }
  .log-feed::-webkit-scrollbar-track { background:transparent; }
  .log-feed::-webkit-scrollbar-thumb { background:var(--border); border-radius:4px; }
  .log-line { color:#94a3b8; word-break:break-all; }
  .log-line.buy   { color:#00d4aa; }
  .log-line.sell  { color:#ff4d6d; }
  .log-line.win   { color:#ffd60a; }
  .log-line.regime{ color:#a78bfa; }

  /* STRATEGIES GRID */
  .strat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
  @media(max-width:768px) { .strat-grid { grid-template-columns:repeat(2,1fr); } }
  .strat-item {
    background:rgba(255,255,255,0.03);
    border:1px solid var(--border);
    border-radius:10px; padding:10px;
    text-align:center;
  }
  .strat-icon { font-size:20px; margin-bottom:4px; }
  .strat-name { font-size:10px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; }

  /* SECTION TITLE */
  .section-title { font-size:13px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; }

  /* ALERTS */
  .alert {
    padding:12px 16px; border-radius:12px; font-size:13px; font-weight:600;
    margin-bottom:16px; display:none;
  }
  .alert-win  { background:rgba(0,212,170,0.15); border:1px solid rgba(0,212,170,0.3); color:var(--green); }
  .alert-stop { background:rgba(255,77,109,0.15); border:1px solid rgba(255,77,109,0.3); color:var(--red); }

  /* TIMER */
  #timer { font-family:'JetBrains Mono'; font-size:13px; color:var(--muted); }

  /* MOBILE BOTTOM NAV */
  .bottom-refresh {
    position:fixed; bottom:20px; right:20px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border:none; border-radius:999px; padding:12px 20px;
    color:white; font-weight:700; font-size:13px; cursor:pointer;
    box-shadow:0 4px 20px rgba(108,99,255,0.4);
    z-index:100;
  }
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="logo">
      <div class="logo-icon">⚡</div>
      <div class="logo-text">
        <h1>Antigravity AI Brain</h1>
        <p>Live Trading Dashboard · Delta Testnet</p>
      </div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <div id="timer">--:--:--</div>
      <div class="live-badge"><div class="pulse"></div> LIVE</div>
    </div>
  </div>

  <!-- ALERTS -->
  <div id="alert-win"  class="alert alert-win">🏆 TARGET $200 REACHED! Mission Complete!</div>
  <div id="alert-stop" class="alert alert-stop">🚨 Hard Stop Hit — Trading Halted!</div>

  <!-- TOP METRICS -->
  <div class="grid-3" style="margin-bottom:16px;">
    <div class="card">
      <div class="card-label">💰 Current Balance</div>
      <div class="card-value val-accent" id="balance">$---.--</div>
      <div class="card-sub" id="balance-sub">Loading...</div>
    </div>
    <div class="card">
      <div class="card-label">📈 Net PnL</div>
      <div class="card-value" id="pnl">$--</div>
      <div class="card-sub" id="pnl-sub">vs $138.57 baseline</div>
    </div>
    <div class="card">
      <div class="card-label">🎯 Target</div>
      <div class="card-value val-yellow">$200.00</div>
      <div class="card-sub" id="target-sub">Loading...</div>
    </div>
  </div>

  <!-- PROGRESS -->
  <div class="card" style="margin-bottom:16px;">
    <div class="progress-header">
      <div>
        <div class="section-title" style="margin-bottom:4px;">24-Hour Target Progress</div>
        <div style="font-size:12px;color:var(--muted);" id="progress-label">$138.57 → $200.00</div>
      </div>
      <div class="progress-pct" id="progress-pct">0%</div>
    </div>
    <div class="progress-track">
      <div class="progress-fill" id="progress-bar" style="width:0%"></div>
    </div>
    <div class="progress-labels">
      <span>$138.57 Start</span>
      <span id="progress-current">$---</span>
      <span>$200 Target</span>
    </div>
  </div>

  <!-- GRID 2 -->
  <div class="grid-2">

    <!-- POSITIONS -->
    <div class="card">
      <div class="section-title">📊 Active Positions</div>
      <div id="positions-body">
        <div class="positions-empty">⏳ Fetching positions...</div>
      </div>
    </div>

    <!-- STRATEGIES -->
    <div class="card">
      <div class="section-title">🤖 Active Strategies</div>
      <div class="strat-grid">
        <div class="strat-item"><div class="strat-icon">📈</div><div class="strat-name">EMA Cross</div></div>
        <div class="strat-item"><div class="strat-icon">🔄</div><div class="strat-name">RSI Reversal</div></div>
        <div class="strat-item"><div class="strat-icon">🚀</div><div class="strat-name">52W Breakout</div></div>
        <div class="strat-item"><div class="strat-icon">💥</div><div class="strat-name">ATR Expansion</div></div>
        <div class="strat-item"><div class="strat-icon">🎯</div><div class="strat-name">BB Squeeze</div></div>
        <div class="strat-item"><div class="strat-icon">⚡</div><div class="strat-name">Power Hour</div></div>
        <div class="strat-item"><div class="strat-icon">📉</div><div class="strat-name">VWAP Reversion</div></div>
        <div class="strat-item"><div class="strat-icon">💰</div><div class="strat-name">Funding Arb</div></div>
      </div>
    </div>
  </div>

  <!-- LIVE LOG FEED -->
  <div class="card" style="margin-bottom:80px;">
    <div class="section-title">📡 Live AI Brain Log Feed</div>
    <div class="log-feed" id="log-feed">
      <div class="log-line">Connecting to Antigravity AI Brain...</div>
    </div>
  </div>

</div>

<!-- REFRESH BTN (Mobile) -->
<button class="bottom-refresh" onclick="fetchData()">⚡ Refresh</button>

<script>
const fmt = v => v >= 0 ? `+$${v.toFixed(2)}` : `-$${Math.abs(v).toFixed(2)}`;

async function fetchData() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();

    // Balance
    document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;
    document.getElementById('balance-sub').textContent =
      `Free margin available`;

    // PnL
    const pnlEl  = document.getElementById('pnl');
    const pnlVal = data.gain;
    pnlEl.textContent = fmt(pnlVal) + ` (${data.gain_pct > 0 ? '+' : ''}${data.gain_pct.toFixed(2)}%)`;
    pnlEl.className   = 'card-value ' + (pnlVal >= 0 ? 'val-green' : 'val-red');

    // Target sub
    const needed = (200 - data.balance).toFixed(2);
    document.getElementById('target-sub').textContent = `$${needed} more needed`;

    // Progress
    const pct = data.progress;
    document.getElementById('progress-pct').textContent     = `${pct.toFixed(1)}%`;
    document.getElementById('progress-bar').style.width     = `${pct}%`;
    document.getElementById('progress-current').textContent = `$${data.balance.toFixed(2)}`;

    // Alerts
    document.getElementById('alert-win').style.display  = data.target_hit ? 'block' : 'none';
    document.getElementById('alert-stop').style.display = data.stop_hit  ? 'block' : 'none';

    // Positions
    const posBody = document.getElementById('positions-body');
    if (data.positions.length === 0) {
      posBody.innerHTML = '<div class="positions-empty">💤 No open positions — scanning for entry...</div>';
    } else {
      posBody.innerHTML = data.positions.map(p => `
        <div class="pos-row">
          <div>
            <div style="font-weight:600;font-size:13px;">${p.symbol}</div>
            <div style="font-size:11px;color:var(--muted);">Entry: $${p.entry.toLocaleString()}</div>
          </div>
          <div style="text-align:right;">
            <span class="pos-badge ${p.side==='LONG'?'pos-long':'pos-short'}">${p.side}</span>
            <div style="font-size:11px;color:var(--muted);margin-top:4px;">Size: ${Math.abs(p.size)}</div>
          </div>
        </div>
      `).join('');
    }

    // Logs
    const logFeed = document.getElementById('log-feed');
    if (data.logs.length > 0) {
      logFeed.innerHTML = data.logs.slice().reverse().map(l => {
        const msg    = l.msg;
        let cls = 'log-line';
        if (msg.includes('ORDER') && msg.includes('buy'))  cls += ' buy';
        if (msg.includes('ORDER') && msg.includes('sell')) cls += ' sell';
        if (msg.includes('TARGET') || msg.includes('HIT')) cls += ' win';
        if (msg.includes('Regime') || msg.includes('REGIME')) cls += ' regime';
        return `<div class="${cls}">${msg}</div>`;
      }).join('');
      logFeed.scrollTop = 0;
    }

  } catch(e) {
    console.error('Fetch error:', e);
  }
}

// Live clock
function updateClock() {
  const now = new Date();
  document.getElementById('timer').textContent =
    now.toLocaleTimeString('en-IN', {timeZone:'Asia/Kolkata', hour12:false}) + ' IST';
}

// Auto-refresh every 10 seconds
fetchData();
setInterval(fetchData, 10000);
setInterval(updateClock, 1000);
updateClock();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("=" * 60)
    print("  ⚡ ANTIGRAVITY AI BRAIN — DASHBOARD SERVER")
    print("=" * 60)
    print(f"  Dashboard URL : http://140.245.195.162:8080")
    print(f"  Local URL     : http://localhost:8080")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
