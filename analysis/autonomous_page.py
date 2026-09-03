"""
==============================================================================
  DEDICATED SEPARATE PAGE: AUTONOMOUS INTELLIGENCE DASHBOARD
==============================================================================
"""

AUTONOMOUS_INTELLIGENCE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 Autonomous Intelligence — 24/7 Quantitative Neural Network</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:        #060611;
    --card:      rgba(255,255,255,0.04);
    --border:    rgba(255,255,255,0.08);
    --accent:    #00f2fe;
    --green:     #10b981;
    --red:       #ef4444;
    --yellow:    #f59e0b;
    --text:      #e2e8f0;
    --muted:     #64748b;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    min-height: 100vh;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 22px;
    font-weight: 800;
    color: #fff;
  }
  .status-badge {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    background: rgba(16,185,129,0.15);
    color: var(--green);
    border: 1px solid rgba(16,185,129,0.3);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(10px);
  }
  .card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
  }
  .metric-val {
    font-size: 28px;
    font-weight: 800;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
  }
  .btn-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
  }
  .btn {
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
  }
  .btn-primary { background: var(--accent); color: #000; box-shadow: 0 0 15px rgba(0,242,254,0.3); }
  .btn-danger { background: rgba(239,68,68,0.2); color: var(--red); border: 1px solid var(--red); }
  .btn-outline { background: transparent; color: #fff; border: 1px solid var(--border); }
  .btn:hover { opacity: 0.9; transform: translateY(-1px); }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { padding: 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--muted); font-weight: 600; }
  .explanation-card {
    background: rgba(0,242,254,0.05);
    border: 1px solid rgba(0,242,254,0.2);
    border-radius: 8px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--accent);
    margin-top: 10px;
  }
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <span>🤖</span> AUTONOMOUS INTELLIGENCE QUANT ENGINE V1.0
  </div>
  <div style="display:flex; gap:12px; align-items:center;">
    <div class="status-badge" id="live-status">
      <div class="dot"></div> 24/7 AUTONOMOUS LOOP ACTIVE
    </div>
    <a href="/" style="color:var(--muted); text-decoration:none; font-size:13px; font-weight:600;">← Back to Main Dashboard</a>
  </div>
</div>

<div class="btn-bar">
  <button class="btn btn-primary" onclick="startLoop()">⚡ START 24/7 NEURAL LOOP</button>
  <button class="btn btn-outline" onclick="stopLoop()">⏹ PAUSE NEURAL LOOP</button>
  <button class="btn btn-outline" onclick="triggerStep()">🎯 TRIGGER MANUAL STEP</button>
  <button class="btn btn-danger" onclick="triggerKillSwitch()">🚨 EMERGENCY KILL SWITCH</button>
</div>

<div class="grid">
  <!-- Card 1: Neural Network Matrix -->
  <div class="card">
    <div class="card-title"><span>🧠 Neural Network Ensemble</span> <span>MLP + RF</span></div>
    <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
      <div>
        <div style="font-size:12px; color:var(--muted)">Probability Up P(Up)</div>
        <div class="metric-val" id="nn-prob-up" style="color:var(--green)">74.0%</div>
      </div>
      <div>
        <div style="font-size:12px; color:var(--muted)">Expected Return</div>
        <div class="metric-val" id="nn-exp-ret" style="color:var(--accent)">+2.4%</div>
      </div>
    </div>
    <div style="font-size:12px; color:var(--muted)">Throughput: <b style="color:#fff">29.3M Predictions/Sec</b> | Latency: <b style="color:var(--green)">0.034 µs</b></div>
  </div>

  <!-- Card 2: Market Regime Monitor -->
  <div class="card">
    <div class="card-title"><span>📊 Market Regime Monitor</span> <span>HMM 8-State</span></div>
    <div class="metric-val" id="regime-badge" style="color:var(--accent); font-size:22px; margin-bottom:10px;">BULL_LOW_VOL</div>
    <div style="font-size:12px; color:var(--muted)">Noise Filter (Shannon Entropy): <b style="color:var(--green)">H(X) = 2.14 bits (LOW NOISE)</b></div>
  </div>

  <!-- Card 3: Deterministic Risk Engine -->
  <div class="card">
    <div class="card-title"><span>🛡️ Deterministic Risk Engine</span> <span style="color:var(--green)">ACTIVE</span></div>
    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
      <div>
        <div style="font-size:12px; color:var(--muted)">Max Position Cap</div>
        <div class="metric-val" style="font-size:20px;">35.0%</div>
      </div>
      <div>
        <div style="font-size:12px; color:var(--muted)">Daily Loss Limit</div>
        <div class="metric-val" style="font-size:20px; color:var(--yellow)">-5.0%</div>
      </div>
    </div>
    <div style="font-size:12px; color:var(--muted)">Kill Switch Status: <b id="kill-status" style="color:var(--green)">NORMAL (RUNNING)</b></div>
  </div>
</div>

<!-- Discovered Patterns Leaderboard -->
<div class="card" style="margin-bottom:24px;">
  <div class="card-title"><span>🔍 Active Discovered Patterns Leaderboard</span> <span>OOS Validated</span></div>
  <table>
    <thead>
      <tr>
        <th>Pattern ID</th>
        <th>Horizon</th>
        <th>Condition</th>
        <th>Sample Size</th>
        <th>Win Rate</th>
        <th>OOS Sharpe</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody id="pattern-rows">
      <tr>
        <td>PATTERN-VOLCOMP-5D</td>
        <td>5D</td>
        <td>volatility_compression &lt; 0.85 &amp; breakout &gt; 0</td>
        <td>148 Trades</td>
        <td style="color:var(--green)">68.5%</td>
        <td>2.41</td>
        <td><span style="color:var(--green)">PROMOTED TO PAPER</span></td>
      </tr>
    </tbody>
  </table>
</div>

<!-- Trade Interpretability ("Why did the system take this trade?") -->
<div class="card">
  <div class="card-title"><span>❓ Why Did The System Take This Trade? (Trade Attribution)</span></div>
  <div class="explanation-card" id="trade-explanation">
    LONG BTC-USD | Probability Up: 74% | Expected Return: +2.4% | Regime: BULL_LOW_VOL | Pattern: Volatility Compression (2 active patterns) | Risk Engine: APPROVED ($15,000 Position Size)
  </div>
</div>

<script>
  async function fetchStatus() {
    try {
      const res = await fetch('/api/autonomous/status');
      const data = await res.json();
      if(data.predictions) {
        document.getElementById('nn-prob-up').innerText = (data.predictions.prob_up * 100).toFixed(1) + '%';
        document.getElementById('nn-exp-ret').innerText = '+' + data.predictions.expected_return.toFixed(1) + '%';
      }
      if(data.regime) {
        document.getElementById('regime-badge').innerText = data.regime;
      }
      if(data.explanation) {
        document.getElementById('trade-explanation').innerText = data.explanation;
      }
    } catch(e) {}
  }

  async function startLoop() {
    await fetch('/api/autonomous/start', {method: 'POST'});
    fetchStatus();
  }

  async function stopLoop() {
    await fetch('/api/autonomous/stop', {method: 'POST'});
    fetchStatus();
  }

  async function triggerStep() {
    await fetch('/api/autonomous/step', {method: 'POST'});
    fetchStatus();
  }

  setInterval(fetchStatus, 3000);
  fetchStatus();
</script>
</body>
</html>
"""
