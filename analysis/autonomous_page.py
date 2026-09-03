"""
==============================================================================
  DEDICATED SEPARATE PAGE: AUTONOMOUS INTELLIGENCE DASHBOARD
  WITH LEVERAGE SIMULATOR & PAPER TRADE ENGINE
==============================================================================
"""

AUTONOMOUS_INTELLIGENCE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Autonomous Intelligence - 24/7 Quantitative Neural Network</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:      #060611;
    --card:    rgba(255,255,255,0.04);
    --border:  rgba(255,255,255,0.08);
    --accent:  #00f2fe;
    --green:   #10b981;
    --red:     #ef4444;
    --yellow:  #f59e0b;
    --purple:  #8b5cf6;
    --text:    #e2e8f0;
    --muted:   #64748b;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); padding:20px; min-height:100vh; }
  .header { display:flex; justify-content:space-between; align-items:center; padding-bottom:18px; border-bottom:1px solid var(--border); margin-bottom:20px; }
  .logo { display:flex; align-items:center; gap:10px; font-size:20px; font-weight:800; color:#fff; }
  .live-badge { padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700; background:rgba(16,185,129,0.15); color:var(--green); border:1px solid rgba(16,185,129,0.3); display:flex; align-items:center; gap:6px; }
  .dot { width:7px; height:7px; border-radius:50%; background:var(--green); box-shadow:0 0 8px var(--green); animation:pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .tabs { display:flex; gap:4px; margin-bottom:20px; border-bottom:1px solid var(--border); padding-bottom:0; }
  .tab { padding:10px 20px; cursor:pointer; font-size:13px; font-weight:600; border-bottom:2px solid transparent; color:var(--muted); transition:all 0.2s; }
  .tab.active { color:var(--accent); border-bottom-color:var(--accent); }
  .tab-content { display:none; }
  .tab-content.active { display:block; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
  .grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:16px; }
  .grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; }
  .card-title { font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:14px; }
  .metric-val { font-size:26px; font-weight:800; color:#fff; font-family:'JetBrains Mono',monospace; }
  .label { font-size:11px; color:var(--muted); margin-bottom:4px; }
  input, select { width:100%; background:rgba(255,255,255,0.06); border:1px solid var(--border); border-radius:8px; padding:10px 12px; color:#fff; font-size:14px; font-family:'JetBrains Mono',monospace; outline:none; }
  input:focus, select:focus { border-color:var(--accent); }
  .btn { padding:11px 20px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; border:none; transition:all 0.2s; width:100%; }
  .btn-long { background:rgba(16,185,129,0.2); color:var(--green); border:1px solid var(--green); }
  .btn-short { background:rgba(239,68,68,0.2); color:var(--red); border:1px solid var(--red); }
  .btn-primary { background:var(--accent); color:#000; }
  .btn-outline { background:transparent; color:#fff; border:1px solid var(--border); }
  .btn:hover { opacity:0.85; transform:translateY(-1px); }
  .result-box { background:rgba(0,242,254,0.05); border:1px solid rgba(0,242,254,0.2); border-radius:10px; padding:16px; margin-top:14px; }
  .result-row { display:flex; justify-content:space-between; align-items:center; padding:7px 0; border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; }
  .result-row:last-child { border-bottom:none; }
  .result-label { color:var(--muted); }
  .result-val { font-family:'JetBrains Mono',monospace; font-weight:700; }
  .green { color:var(--green); }
  .red { color:var(--red); }
  .yellow { color:var(--yellow); }
  .accent { color:var(--accent); }
  .lev-btn { padding:8px 0; border-radius:6px; text-align:center; cursor:pointer; font-weight:700; font-size:13px; border:1px solid var(--border); color:var(--muted); background:var(--card); transition:all 0.2s; }
  .lev-btn.active { background:rgba(0,242,254,0.15); color:var(--accent); border-color:var(--accent); }
  .lev-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:6px; margin-bottom:14px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; }
  .tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }
  .tag-long { background:rgba(16,185,129,0.15); color:var(--green); }
  .tag-short { background:rgba(239,68,68,0.15); color:var(--red); }
  .tag-open { background:rgba(0,242,254,0.15); color:var(--accent); }
  .tag-closed { background:rgba(100,116,139,0.2); color:var(--muted); }
  .liquidation-bar { height:8px; border-radius:4px; background:rgba(255,255,255,0.05); margin-top:8px; overflow:hidden; }
  .liquidation-fill { height:100%; border-radius:4px; background:linear-gradient(90deg, var(--green), var(--yellow), var(--red)); transition:width 0.4s; }
  .pnl-positive { color:var(--green); }
  .pnl-negative { color:var(--red); }
  .warning-box { background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:8px; padding:12px; font-size:12px; color:var(--red); margin-top:10px; }
  .info-box { background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:12px; font-size:12px; color:var(--yellow); margin-top:10px; }
  .mono { font-family:'JetBrains Mono',monospace; }
  .section-head { font-size:16px; font-weight:800; color:#fff; margin-bottom:16px; display:flex; align-items:center; gap:8px; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">&#x1F916; AUTONOMOUS INTELLIGENCE QUANT ENGINE</div>
  <div style="display:flex;gap:10px;align-items:center;">
    <div class="live-badge"><div class="dot"></div>24/7 NEURAL LOOP ACTIVE</div>
    <a href="/" style="color:var(--muted);text-decoration:none;font-size:12px;font-weight:600;">&#8592; Main Dashboard</a>
  </div>
</div>

<!-- TABS -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('neural')">&#x1F9E0; Neural Engine</div>
  <div class="tab" onclick="switchTab('leverage')">&#x26A1; Leverage Simulator</div>
  <div class="tab" onclick="switchTab('paper')">&#x1F4CB; Paper Trades</div>
  <div class="tab" onclick="switchTab('risk')">&#x1F6E1; Risk Analysis</div>
</div>

<!-- ─── TAB 1: NEURAL ENGINE ─── -->
<div id="tab-neural" class="tab-content active">
  <div class="grid3">
    <div class="card">
      <div class="card-title">&#x1F9E0; Neural Network Ensemble</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
        <div><div class="label">P(Up)</div><div class="metric-val green" id="nn-prob-up">74.0%</div></div>
        <div><div class="label">Expected Return</div><div class="metric-val accent" id="nn-exp-ret">+2.4%</div></div>
      </div>
      <div style="font-size:12px;color:var(--muted);">Rust Engine: <b style="color:#fff;">29.3M Predictions/Sec</b> | Latency: <b style="color:var(--green);">0.034 us</b></div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F4CA; Market Regime</div>
      <div class="metric-val accent" id="regime-badge" style="font-size:18px;margin-bottom:8px;">BULL_LOW_VOL</div>
      <div style="font-size:12px;color:var(--muted);">Shannon Entropy: <b style="color:var(--green);">H(X) = 2.14 bits</b></div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F6E1;&#xFE0F; Risk Engine Status</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <div><div class="label">Max Position</div><div class="metric-val" style="font-size:18px;">35%</div></div>
        <div><div class="label">Daily Loss Limit</div><div class="metric-val red" style="font-size:18px;">-5%</div></div>
      </div>
      <div style="font-size:12px;color:var(--muted);">Kill Switch: <b id="kill-status" class="green">NORMAL</b></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">&#x2753; Trade Attribution — Why did the system pick this trade?</div>
    <div style="background:rgba(0,242,254,0.05);border:1px solid rgba(0,242,254,0.2);border-radius:8px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--accent);" id="trade-explanation">
      LONG BTC-USD | P(Up): 74% | Expected Return: +2.4% | Regime: BULL_LOW_VOL | Pattern: Volatility Compression | Risk Engine: APPROVED
    </div>
  </div>
</div>

<!-- ─── TAB 2: LEVERAGE SIMULATOR ─── -->
<div id="tab-leverage" class="tab-content">
  <div class="section-head">&#x26A1; Leverage Simulator — Calculate Risk Before You Trade</div>
  <div class="grid2">

    <!-- LEFT: INPUTS -->
    <div class="card">
      <div class="card-title">&#x1F4B0; Trade Parameters</div>

      <div class="label" style="margin-bottom:6px;">Asset Symbol</div>
      <select id="lev-symbol" style="margin-bottom:12px;" onchange="fetchLivePrice()">
        <option value="BTC">BTC/USDT</option>
        <option value="ETH">ETH/USDT</option>
        <option value="SOL">SOL/USDT</option>
        <option value="CUSTOM">Custom Price</option>
      </select>

      <div class="label" style="margin-bottom:6px;">Entry Price ($)</div>
      <input type="number" id="lev-entry" value="60000" step="0.01" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div class="label" style="margin-bottom:6px;">Capital / Margin ($)</div>
      <input type="number" id="lev-capital" value="1000" step="1" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div class="label" style="margin-bottom:8px;">Leverage</div>
      <div class="lev-grid">
        <div class="lev-btn active" onclick="setLev(1)">1x</div>
        <div class="lev-btn" onclick="setLev(2)">2x</div>
        <div class="lev-btn" onclick="setLev(5)">5x</div>
        <div class="lev-btn" onclick="setLev(10)">10x</div>
        <div class="lev-btn" onclick="setLev(25)">25x</div>
        <div class="lev-btn" onclick="setLev(50)">50x</div>
        <div class="lev-btn" onclick="setLev(75)">75x</div>
        <div class="lev-btn" onclick="setLev(100)">100x</div>
        <div class="lev-btn" onclick="setLev(125)">125x</div>
        <div class="lev-btn" onclick="setLev(150)">150x</div>
        <div class="lev-btn" onclick="setLev(200)">200x</div>
        <div class="lev-btn" onclick="setLev(0)">Custom</div>
      </div>
      <input type="number" id="lev-custom" value="10" min="1" max="500" oninput="calcLeverage()" placeholder="Custom leverage" style="margin-bottom:12px;" />

      <div class="label" style="margin-bottom:6px;">Stop Loss (%)</div>
      <input type="number" id="lev-sl" value="2" step="0.1" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div class="label" style="margin-bottom:6px;">Take Profit (%)</div>
      <input type="number" id="lev-tp" value="4" step="0.1" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px;">
        <button class="btn btn-long" onclick="openPaperTrade('LONG')">&#x1F4C8; PAPER LONG</button>
        <button class="btn btn-short" onclick="openPaperTrade('SHORT')">&#x1F4C9; PAPER SHORT</button>
      </div>
    </div>

    <!-- RIGHT: RESULTS -->
    <div>
      <div class="card" style="margin-bottom:14px;">
        <div class="card-title">&#x1F4CA; Position Breakdown</div>
        <div class="result-box" style="margin-top:0;">
          <div class="result-row"><span class="result-label">Position Size</span><span class="result-val accent" id="r-position">$10,000</span></div>
          <div class="result-row"><span class="result-label">Margin Required</span><span class="result-val yellow" id="r-margin">$1,000</span></div>
          <div class="result-row"><span class="result-label">Leverage</span><span class="result-val" id="r-lev">10x</span></div>
          <div class="result-row"><span class="result-label">Contracts / Units</span><span class="result-val" id="r-units">0.1667 BTC</span></div>
        </div>
      </div>

      <div class="card" style="margin-bottom:14px;">
        <div class="card-title">&#x26A0;&#xFE0F; Risk & Liquidation</div>
        <div class="result-box" style="margin-top:0;">
          <div class="result-row"><span class="result-label">Liquidation Price (Long)</span><span class="result-val red" id="r-liq-long">$54,600</span></div>
          <div class="result-row"><span class="result-label">Liquidation Price (Short)</span><span class="result-val red" id="r-liq-short">$65,400</span></div>
          <div class="result-row"><span class="result-label">Stop Loss Price</span><span class="result-val yellow" id="r-sl-price">$58,800</span></div>
          <div class="result-row"><span class="result-label">Take Profit Price</span><span class="result-val green" id="r-tp-price">$62,400</span></div>
          <div class="result-row"><span class="result-label">Max Loss (SL Hit)</span><span class="result-val red" id="r-max-loss">-$200</span></div>
          <div class="result-row"><span class="result-label">Max Gain (TP Hit)</span><span class="result-val green" id="r-max-gain">+$400</span></div>
          <div class="result-row"><span class="result-label">Risk/Reward Ratio</span><span class="result-val accent" id="r-rr">1:2.0</span></div>
        </div>
        <div style="margin-top:10px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">
            <span style="color:var(--green);">Liquidation Safe Zone</span>
            <span id="r-dist-pct" class="yellow">9.0% away</span>
          </div>
          <div class="liquidation-bar"><div class="liquidation-fill" id="liq-fill" style="width:90%"></div></div>
        </div>
        <div id="r-warning" class="warning-box" style="display:none;"></div>
      </div>

      <div class="card">
        <div class="card-title">&#x1F4B9; P&L Scenarios</div>
        <table>
          <thead><tr><th>Price Move</th><th>P&L ($)</th><th>ROE %</th><th>Status</th></tr></thead>
          <tbody id="scenario-rows"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ─── TAB 3: PAPER TRADES ─── -->
<div id="tab-paper" class="tab-content">
  <div class="section-head">&#x1F4CB; Paper Trade Journal</div>
  <div class="card" style="margin-bottom:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div class="card-title" style="margin-bottom:0;">Active Trades</div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-outline" style="width:auto;padding:6px 14px;font-size:12px;" onclick="closeAllTrades()">Close All</button>
        <button class="btn btn-primary" style="width:auto;padding:6px 14px;font-size:12px;" onclick="switchTab('leverage')">+ New Trade</button>
      </div>
    </div>
    <table>
      <thead><tr><th>Symbol</th><th>Side</th><th>Leverage</th><th>Entry</th><th>Cur Price</th><th>Margin</th><th>P&L ($)</th><th>ROE %</th><th>Liq Price</th><th>Action</th></tr></thead>
      <tbody id="paper-trades-body">
        <tr><td colspan="10" style="text-align:center;color:var(--muted);padding:20px;">No open trades. Go to Leverage Simulator to open a paper trade.</td></tr>
      </tbody>
    </table>
  </div>

  <div class="grid3">
    <div class="card">
      <div class="card-title">Total P&L</div>
      <div class="metric-val green" id="total-pnl">$0.00</div>
    </div>
    <div class="card">
      <div class="card-title">Win Rate</div>
      <div class="metric-val accent" id="win-rate">0%</div>
    </div>
    <div class="card">
      <div class="card-title">Total Trades</div>
      <div class="metric-val" id="total-trades">0</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Closed Trade History</div>
    <table>
      <thead><tr><th>Symbol</th><th>Side</th><th>Lev</th><th>Entry</th><th>Exit</th><th>Margin</th><th>P&L ($)</th><th>ROE %</th><th>Result</th></tr></thead>
      <tbody id="closed-trades-body">
        <tr><td colspan="9" style="text-align:center;color:var(--muted);padding:16px;">No closed trades yet.</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ─── TAB 4: RISK ANALYSIS ─── -->
<div id="tab-risk" class="tab-content">
  <div class="section-head">&#x1F6E1; Portfolio Risk Dashboard</div>
  <div class="grid4">
    <div class="card"><div class="card-title">Total Exposure</div><div class="metric-val yellow" id="risk-exposure">$0</div></div>
    <div class="card"><div class="card-title">Max Drawdown Risk</div><div class="metric-val red" id="risk-mdd">$0</div></div>
    <div class="card"><div class="card-title">Portfolio Margin</div><div class="metric-val accent" id="risk-margin">$0</div></div>
    <div class="card"><div class="card-title">Avg Leverage</div><div class="metric-val" id="risk-avg-lev">0x</div></div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">&#x1F4C9; Worst-Case Loss Scenarios</div>
      <table>
        <thead><tr><th>Market Drop</th><th>Portfolio Loss</th><th>Margin Wiped</th></tr></thead>
        <tbody id="risk-scenarios"></tbody>
      </table>
      <div class="info-box" style="margin-top:12px;">
        Based on your paper portfolio. Real losses depend on exchange liquidation rules.
      </div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F4D6; Kelly Criterion — Optimal Position Sizing</div>
      <div class="label" style="margin-top:8px;">Win Rate (%)</div>
      <input type="number" id="kelly-wr" value="55" min="1" max="99" oninput="calcKelly()" style="margin-bottom:10px;" />
      <div class="label">Win/Loss Ratio (avg win / avg loss)</div>
      <input type="number" id="kelly-ratio" value="2" step="0.1" min="0.1" oninput="calcKelly()" style="margin-bottom:14px;" />
      <div class="result-box" style="margin-top:0;">
        <div class="result-row"><span class="result-label">Full Kelly %</span><span class="result-val green" id="kelly-full">32.5%</span></div>
        <div class="result-row"><span class="result-label">Half Kelly % (Recommended)</span><span class="result-val accent" id="kelly-half">16.25%</span></div>
        <div class="result-row"><span class="result-label">Quarter Kelly % (Conservative)</span><span class="result-val yellow" id="kelly-quarter">8.125%</span></div>
        <div class="result-row"><span class="result-label">On $10,000 Capital — Bet</span><span class="result-val" id="kelly-dollar">$1,625</span></div>
      </div>
    </div>
  </div>
</div>

<script>
// ─── STATE ──────────────────────────────────────────────────────────────────
let currentLev = 10;
let paperTrades = JSON.parse(localStorage.getItem('paperTrades') || '[]');
let closedTrades = JSON.parse(localStorage.getItem('closedTrades') || '[]');

const LIVE_PRICES = { BTC: 60000, ETH: 3500, SOL: 150, CUSTOM: 0 };

async function fetchLivePrice() {
  const symEl = document.getElementById('lev-symbol');
  if(!symEl) return;
  const sym = symEl.value;
  if(sym === 'CUSTOM') return;
  const pairMap = { BTC: 'BTCUSDT', ETH: 'ETHUSDT', SOL: 'SOLUSDT' };
  try {
    const pair = pairMap[sym];
    if(pair) {
      const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${pair}`);
      const data = await res.json();
      if(data.price) {
        document.getElementById('lev-entry').value = parseFloat(data.price).toFixed(2);
        calcLeverage();
        return;
      }
    }
  } catch(e) {}
  if(LIVE_PRICES[sym]) {
    document.getElementById('lev-entry').value = LIVE_PRICES[sym];
    calcLeverage();
  }
}

// ─── TABS ────────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab')[['neural','leverage','paper','risk'].indexOf(name)].classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  if(name === 'paper') renderPaperTrades();
  if(name === 'risk') renderRiskDashboard();
}

// ─── LEVERAGE CALCULATOR ─────────────────────────────────────────────────────
function setLev(val) {
  document.querySelectorAll('.lev-btn').forEach(b => b.classList.remove('active'));
  if(val === 0) { document.querySelector('.lev-btn:last-child').classList.add('active'); }
  else {
    const btns = document.querySelectorAll('.lev-btn');
    btns.forEach(b => { if(b.textContent === val+'x') b.classList.add('active'); });
    document.getElementById('lev-custom').value = val;
  }
  currentLev = val || parseFloat(document.getElementById('lev-custom').value) || 1;
  calcLeverage();
}

function calcLeverage() {
  const entry    = parseFloat(document.getElementById('lev-entry').value) || 0;
  const capital  = parseFloat(document.getElementById('lev-capital').value) || 0;
  const lev      = parseFloat(document.getElementById('lev-custom').value) || 1;
  const slPct    = parseFloat(document.getElementById('lev-sl').value) || 0;
  const tpPct    = parseFloat(document.getElementById('lev-tp').value) || 0;

  currentLev = lev;
  const position = capital * lev;
  const units    = position / entry;
  const mmRate   = 0.004; // 0.4% maintenance margin

  const liqLong  = entry * (1 - 1/lev + mmRate);
  const liqShort = entry * (1 + 1/lev - mmRate);
  const slPrice  = entry * (1 - slPct/100);
  const tpPrice  = entry * (1 + tpPct/100);
  const maxLoss  = capital * (slPct/100) * lev;
  const maxGain  = capital * (tpPct/100) * lev;
  const rr       = maxGain / (maxLoss || 1);
  const distPct  = ((entry - liqLong) / entry * 100).toFixed(2);

  document.getElementById('r-position').textContent   = '$' + fmt(position);
  document.getElementById('r-margin').textContent     = '$' + fmt(capital);
  document.getElementById('r-lev').textContent        = lev + 'x';
  document.getElementById('r-units').textContent      = units.toFixed(4) + ' units';
  document.getElementById('r-liq-long').textContent   = '$' + fmt(liqLong);
  document.getElementById('r-liq-short').textContent  = '$' + fmt(liqShort);
  document.getElementById('r-sl-price').textContent   = '$' + fmt(slPrice);
  document.getElementById('r-tp-price').textContent   = '$' + fmt(tpPrice);
  document.getElementById('r-max-loss').textContent   = '-$' + fmt(maxLoss);
  document.getElementById('r-max-gain').textContent   = '+$' + fmt(maxGain);
  document.getElementById('r-rr').textContent         = '1:' + rr.toFixed(1);
  document.getElementById('r-dist-pct').textContent   = distPct + '% away from liquidation';
  document.getElementById('liq-fill').style.width     = Math.min(100, parseFloat(distPct)*5) + '%';

  // Warning for high leverage
  const warn = document.getElementById('r-warning');
  if(lev >= 50) {
    warn.style.display = 'block';
    warn.textContent = 'WARNING: ' + lev + 'x leverage liquidates if price moves just ' + (100/lev).toFixed(2) + '% against you. Extremely high risk — paper trade only!';
  } else { warn.style.display = 'none'; }

  // P&L scenarios
  const scenarios = [-10,-5,-3,-2,-1,1,2,3,5,10];
  let rows = '';
  scenarios.forEach(pct => {
    const pnl = capital * (pct/100) * lev;
    const roe = pct * lev;
    const isWin = pnl > 0;
    const liqHit = (pct < 0 && Math.abs(pct) >= 100/lev);
    rows += `<tr>
      <td class="mono">${pct > 0 ? '+' : ''}${pct}%</td>
      <td class="mono ${isWin ? 'green' : 'red'}">${isWin ? '+' : ''}$${fmt(Math.abs(pnl))}</td>
      <td class="mono ${isWin ? 'green' : 'red'}">${isWin ? '+' : ''}${roe.toFixed(1)}%</td>
      <td><span class="tag ${liqHit ? 'tag-short' : isWin ? 'tag-long' : 'tag-short'}">${liqHit ? 'LIQUIDATED' : isWin ? 'PROFIT' : 'LOSS'}</span></td>
    </tr>`;
  });
  document.getElementById('scenario-rows').innerHTML = rows;
}

// ─── PAPER TRADES ────────────────────────────────────────────────────────────
function openPaperTrade(side) {
  const entry   = parseFloat(document.getElementById('lev-entry').value) || 0;
  const capital = parseFloat(document.getElementById('lev-capital').value) || 0;
  const lev     = parseFloat(document.getElementById('lev-custom').value) || 1;
  const slPct   = parseFloat(document.getElementById('lev-sl').value) || 2;
  const tpPct   = parseFloat(document.getElementById('lev-tp').value) || 4;
  const symbol  = document.getElementById('lev-symbol').options[document.getElementById('lev-symbol').selectedIndex].text;

  const mmRate  = 0.004;
  const liqPrice = side === 'LONG'
    ? entry * (1 - 1/lev + mmRate)
    : entry * (1 + 1/lev - mmRate);
  const slPrice  = side === 'LONG' ? entry * (1 - slPct/100) : entry * (1 + slPct/100);
  const tpPrice  = side === 'LONG' ? entry * (1 + tpPct/100) : entry * (1 - tpPct/100);

  const trade = {
    id: Date.now(),
    symbol, side, leverage: lev, entry, capital,
    position: capital * lev, liqPrice, slPrice, tpPrice,
    openTime: new Date().toLocaleString(),
    curPrice: entry
  };

  paperTrades.push(trade);
  localStorage.setItem('paperTrades', JSON.stringify(paperTrades));
  switchTab('paper');
}

function renderPaperTrades() {
  const tbody = document.getElementById('paper-trades-body');
  if(!paperTrades.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--muted);padding:20px;">No open trades. Go to Leverage Simulator to open a paper trade.</td></tr>';
  } else {
    tbody.innerHTML = paperTrades.map(t => {
      const pnl = t.side === 'LONG'
        ? (t.curPrice - t.entry) / t.entry * t.capital * t.leverage
        : (t.entry - t.curPrice) / t.entry * t.capital * t.leverage;
      const roe = (pnl / t.capital * 100).toFixed(2);
      const isLiq = t.side === 'LONG' ? t.curPrice <= t.liqPrice : t.curPrice >= t.liqPrice;
      return `<tr>
        <td class="mono">${t.symbol}</td>
        <td><span class="tag tag-${t.side.toLowerCase()}">${t.side}</span></td>
        <td class="mono accent">${t.leverage}x</td>
        <td class="mono">$${fmt(t.entry)}</td>
        <td class="mono"><input type="number" value="${t.curPrice}" style="width:90px;padding:4px 6px;font-size:12px;" onchange="updatePrice(${t.id}, this.value)" /></td>
        <td class="mono yellow">$${fmt(t.capital)}</td>
        <td class="mono ${pnl >= 0 ? 'green' : 'red'}">${pnl >= 0 ? '+' : ''}$${fmt(Math.abs(pnl))}</td>
        <td class="mono ${parseFloat(roe) >= 0 ? 'green' : 'red'}">${parseFloat(roe) >= 0 ? '+' : ''}${roe}%</td>
        <td class="mono red">$${fmt(t.liqPrice)}</td>
        <td><button class="btn btn-short" style="padding:4px 10px;font-size:11px;width:auto;" onclick="closeTrade(${t.id})">Close</button></td>
      </tr>` + (isLiq ? `<tr><td colspan="10" class="red" style="text-align:center;font-size:12px;font-weight:700;padding:6px;">LIQUIDATED — Enter a current price above liquidation level</td></tr>` : '');
    }).join('');
  }

  // Closed trades
  const cbody = document.getElementById('closed-trades-body');
  if(!closedTrades.length) {
    cbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:16px;">No closed trades yet.</td></tr>';
  } else {
    cbody.innerHTML = closedTrades.map(t => {
      const won = t.pnl >= 0;
      return `<tr>
        <td class="mono">${t.symbol}</td>
        <td><span class="tag tag-${t.side.toLowerCase()}">${t.side}</span></td>
        <td class="mono accent">${t.leverage}x</td>
        <td class="mono">$${fmt(t.entry)}</td>
        <td class="mono">$${fmt(t.exitPrice)}</td>
        <td class="mono yellow">$${fmt(t.capital)}</td>
        <td class="mono ${won ? 'green' : 'red'}">${won ? '+' : ''}$${fmt(Math.abs(t.pnl))}</td>
        <td class="mono ${won ? 'green' : 'red'}">${(t.pnl/t.capital*100).toFixed(2)}%</td>
        <td><span class="tag ${won ? 'tag-long' : 'tag-short'}">${won ? 'WIN' : 'LOSS'}</span></td>
      </tr>`;
    }).join('');
  }

  // Stats
  const totalPnl = [...closedTrades].reduce((a,t) => a + t.pnl, 0);
  const wins = closedTrades.filter(t => t.pnl >= 0).length;
  document.getElementById('total-pnl').textContent = (totalPnl >= 0 ? '+' : '') + '$' + fmt(Math.abs(totalPnl));
  document.getElementById('total-pnl').className = 'metric-val ' + (totalPnl >= 0 ? 'green' : 'red');
  document.getElementById('win-rate').textContent = closedTrades.length ? (wins/closedTrades.length*100).toFixed(0) + '%' : '0%';
  document.getElementById('total-trades').textContent = closedTrades.length;
}

function updatePrice(id, newPrice) {
  const t = paperTrades.find(t => t.id === id);
  if(t) { t.curPrice = parseFloat(newPrice) || t.entry; localStorage.setItem('paperTrades', JSON.stringify(paperTrades)); renderPaperTrades(); }
}

function closeTrade(id) {
  const idx = paperTrades.findIndex(t => t.id === id);
  if(idx === -1) return;
  const t = paperTrades[idx];
  const exitPrice = t.curPrice;
  const pnl = t.side === 'LONG'
    ? (exitPrice - t.entry) / t.entry * t.capital * t.leverage
    : (t.entry - exitPrice) / t.entry * t.capital * t.leverage;
  closedTrades.push({...t, exitPrice, pnl, closeTime: new Date().toLocaleString()});
  paperTrades.splice(idx, 1);
  localStorage.setItem('paperTrades', JSON.stringify(paperTrades));
  localStorage.setItem('closedTrades', JSON.stringify(closedTrades));
  renderPaperTrades();
}

function closeAllTrades() {
  paperTrades.forEach(t => {
    const pnl = t.side === 'LONG'
      ? (t.curPrice - t.entry) / t.entry * t.capital * t.leverage
      : (t.entry - t.curPrice) / t.entry * t.capital * t.leverage;
    closedTrades.push({...t, exitPrice: t.curPrice, pnl, closeTime: new Date().toLocaleString()});
  });
  paperTrades = [];
  localStorage.setItem('paperTrades', JSON.stringify(paperTrades));
  localStorage.setItem('closedTrades', JSON.stringify(closedTrades));
  renderPaperTrades();
}

// ─── RISK DASHBOARD ──────────────────────────────────────────────────────────
function renderRiskDashboard() {
  const totalExposure = paperTrades.reduce((a,t) => a + t.position, 0);
  const totalMargin   = paperTrades.reduce((a,t) => a + t.capital, 0);
  const avgLev = paperTrades.length ? (paperTrades.reduce((a,t) => a + t.leverage, 0) / paperTrades.length).toFixed(1) : 0;
  document.getElementById('risk-exposure').textContent = '$' + fmt(totalExposure);
  document.getElementById('risk-margin').textContent   = '$' + fmt(totalMargin);
  document.getElementById('risk-avg-lev').textContent  = avgLev + 'x';

  const drops = [1, 2, 5, 10, 20, 50];
  let riskRows = '';
  drops.forEach(d => {
    const loss = totalMargin * (d/100) * (parseFloat(avgLev)||1);
    const wiped = Math.min(100, d * (parseFloat(avgLev)||1)).toFixed(0);
    riskRows += `<tr>
      <td class="red mono">-${d}%</td>
      <td class="red mono">-$${fmt(Math.min(loss, totalMargin))}</td>
      <td class="${wiped >= 100 ? 'red' : wiped >= 50 ? 'yellow' : 'green'} mono">${wiped}%</td>
    </tr>`;
  });
  document.getElementById('risk-scenarios').innerHTML = riskRows || '<tr><td colspan="3" style="text-align:center;color:var(--muted);">Open paper trades first</td></tr>';
  document.getElementById('risk-mdd').textContent = '-$' + fmt(totalMargin);
  calcKelly();
}

function calcKelly() {
  const wr = parseFloat(document.getElementById('kelly-wr').value) / 100 || 0.55;
  const ratio = parseFloat(document.getElementById('kelly-ratio').value) || 2;
  const full = (wr - (1 - wr) / ratio) * 100;
  document.getElementById('kelly-full').textContent    = full.toFixed(2) + '%';
  document.getElementById('kelly-half').textContent   = (full/2).toFixed(2) + '%';
  document.getElementById('kelly-quarter').textContent = (full/4).toFixed(2) + '%';
  document.getElementById('kelly-dollar').textContent  = '$' + fmt(10000 * full/2 / 100);
}

// ─── NEURAL STATUS REFRESH ────────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const res = await fetch('/api/autonomous/status');
    const data = await res.json();
    if(data.predictions) {
      document.getElementById('nn-prob-up').textContent  = (data.predictions.prob_up * 100).toFixed(1) + '%';
      document.getElementById('nn-exp-ret').textContent  = '+' + (data.predictions.expected_return || 0).toFixed(1) + '%';
    }
    if(data.regime) document.getElementById('regime-badge').textContent = data.regime;
    if(data.explanation) document.getElementById('trade-explanation').textContent = data.explanation;
  } catch(e) {}
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function fmt(n) {
  return Number(n).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
}

// ─── INIT ────────────────────────────────────────────────────────────────────
calcLeverage();
calcKelly();
fetchLivePrice();
fetchStatus();
setInterval(fetchStatus, 5000);
</script>
</body>
</html>
"""
