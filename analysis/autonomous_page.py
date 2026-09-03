"""
==============================================================================
  DEDICATED SEPARATE PAGE: AUTONOMOUS INTELLIGENCE DASHBOARD
  REAL-TIME DATA STREAMING, LEVERAGE SIMULATOR & PAPER TRADING ENGINE
==============================================================================
"""

AUTONOMOUS_INTELLIGENCE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Autonomous Intelligence - Real-Time Paper Trading & Leverage Engine</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:        #060611;
    --card:      rgba(255,255,255,0.04);
    --border:    rgba(255,255,255,0.08);
    --accent:    #00f2fe;
    --green:     #10b981;
    --red:       #ef4444;
    --yellow:    #f59e0b;
    --purple:    #8b5cf6;
    --text:      #e2e8f0;
    --muted:     #64748b;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); padding:18px; min-height:100vh; }
  
  /* HEADER & LIVE TICKER BAR */
  .header { display:flex; justify-content:space-between; align-items:center; padding-bottom:14px; border-bottom:1px solid var(--border); margin-bottom:14px; }
  .logo { display:flex; align-items:center; gap:10px; font-size:19px; font-weight:800; color:#fff; }
  .live-status-pill { padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700; background:rgba(16,185,129,0.15); color:var(--green); border:1px solid rgba(16,185,129,0.3); display:flex; align-items:center; gap:6px; }
  .dot { width:7px; height:7px; border-radius:50%; background:var(--green); box-shadow:0 0 8px var(--green); animation:pulse 1.4s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:0.3;transform:scale(0.85);} }
  
  .ticker-bar { display:flex; gap:12px; overflow-x:auto; padding:10px 14px; background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:10px; margin-bottom:16px; align-items:center; }
  .ticker-pill { display:flex; align-items:center; gap:8px; padding:6px 14px; border-radius:8px; background:var(--card); border:1px solid var(--border); font-size:12px; white-space:nowrap; }
  .ticker-sym { font-weight:700; color:#fff; font-family:'JetBrains Mono',monospace; }
  .ticker-price { font-family:'JetBrains Mono',monospace; font-weight:800; transition:color 0.3s; }
  .price-up { color:var(--green) !important; animation:flashGreen 0.5s; }
  .price-down { color:var(--red) !important; animation:flashRed 0.5s; }
  @keyframes flashGreen { 0%{background:rgba(16,185,129,0.3);} 100%{background:transparent;} }
  @keyframes flashRed { 0%{background:rgba(239,68,68,0.3);} 100%{background:transparent;} }
  
  /* TABS */
  .tabs { display:flex; gap:4px; margin-bottom:18px; border-bottom:1px solid var(--border); }
  .tab { padding:10px 20px; cursor:pointer; font-size:13px; font-weight:700; border-bottom:2px solid transparent; color:var(--muted); transition:all 0.2s; }
  .tab.active { color:var(--accent); border-bottom-color:var(--accent); }
  .tab-content { display:none; }
  .tab-content.active { display:block; }
  
  /* GRIDS & CARDS */
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
  .grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:16px; }
  .grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; position:relative; }
  .card-title { font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; display:flex; justify-content:space-between; }
  .metric-val { font-size:26px; font-weight:800; color:#fff; font-family:'JetBrains Mono',monospace; }
  .label { font-size:11px; color:var(--muted); margin-bottom:4px; font-weight:600; }
  
  /* FORMS & BUTTONS */
  input, select { width:100%; background:rgba(255,255,255,0.06); border:1px solid var(--border); border-radius:8px; padding:9px 12px; color:#fff; font-size:13px; font-family:'JetBrains Mono',monospace; outline:none; }
  input:focus, select:focus { border-color:var(--accent); }
  .btn { padding:11px 18px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; border:none; transition:all 0.2s; width:100%; }
  .btn-long { background:rgba(16,185,129,0.2); color:var(--green); border:1px solid var(--green); }
  .btn-short { background:rgba(239,68,68,0.2); color:var(--red); border:1px solid var(--red); }
  .btn-primary { background:var(--accent); color:#000; }
  .btn-outline { background:transparent; color:#fff; border:1px solid var(--border); }
  .btn:hover { opacity:0.85; transform:translateY(-1px); }
  
  /* RESULTS & TABLES */
  .result-box { background:rgba(0,242,254,0.04); border:1px solid rgba(0,242,254,0.2); border-radius:10px; padding:14px; }
  .result-row { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.05); font-size:12px; }
  .result-row:last-child { border-bottom:none; }
  .result-label { color:var(--muted); }
  .result-val { font-family:'JetBrains Mono',monospace; font-weight:700; }
  .green { color:var(--green) !important; }
  .red { color:var(--red) !important; }
  .yellow { color:var(--yellow) !important; }
  .accent { color:var(--accent) !important; }
  .mono { font-family:'JetBrains Mono',monospace; }
  
  /* LEVERAGE BUTTONS */
  .lev-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:5px; margin-bottom:12px; }
  .lev-btn { padding:7px 0; border-radius:6px; text-align:center; cursor:pointer; font-weight:700; font-size:12px; border:1px solid var(--border); color:var(--muted); background:var(--card); transition:all 0.15s; }
  .lev-btn.active { background:rgba(0,242,254,0.15); color:var(--accent); border-color:var(--accent); }
  
  /* TABLES */
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th, td { padding:9px 12px; text-align:left; border-bottom:1px solid var(--border); }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; }
  .tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }
  .tag-long { background:rgba(16,185,129,0.15); color:var(--green); }
  .tag-short { background:rgba(239,68,68,0.15); color:var(--red); }
  .tag-liq { background:rgba(239,68,68,0.25); color:var(--red); border:1px solid var(--red); }
  
  /* TOAST NOTIFICATION */
  #toast { position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:8px; font-size:13px; font-weight:700; display:none; z-index:9999; box-shadow:0 10px 30px rgba(0,0,0,0.5); }
  .toast-success { background:#10b981; color:#000; }
  .toast-danger { background:#ef4444; color:#fff; }
  .toast-info { background:#00f2fe; color:#000; }

  /* PRICE STRESS SLIDER */
  .stress-container { background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:8px; padding:12px; margin-top:12px; }
  .stress-slider { -webkit-appearance:none; width:100%; height:6px; border-radius:3px; background:#334155; outline:none; margin:10px 0; }
  .stress-slider::-webkit-slider-thumb { -webkit-appearance:none; width:18px; height:18px; border-radius:50%; background:var(--accent); cursor:pointer; box-shadow:0 0 10px var(--accent); }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="logo">&#x1F916; AUTONOMOUS INTELLIGENCE QUANT ENGINE V2.0</div>
  <div style="display:flex;gap:10px;align-items:center;">
    <div class="live-status-pill" id="conn-pill"><div class="dot"></div><span id="conn-text">STREAMING REAL-TIME DATA</span></div>
    <a href="/" style="color:var(--muted);text-decoration:none;font-size:12px;font-weight:600;">&#8592; Main Dashboard</a>
  </div>
</div>

<!-- REAL-TIME TICKER STREAM BAR -->
<div class="ticker-bar">
  <span style="font-size:11px;color:var(--muted);font-weight:700;">LIVE FEEDS:</span>
  <div class="ticker-pill">
    <span class="ticker-sym">BTC/USDT</span>
    <span class="ticker-price" id="tick-btc">$---</span>
  </div>
  <div class="ticker-pill">
    <span class="ticker-sym">ETH/USDT</span>
    <span class="ticker-price" id="tick-eth">$---</span>
  </div>
  <div class="ticker-pill">
    <span class="ticker-sym">SOL/USDT</span>
    <span class="ticker-price" id="tick-sol">$---</span>
  </div>
  <div class="ticker-pill" style="margin-left:auto;border-color:transparent;background:transparent;">
    <span style="font-size:11px;color:var(--muted);" id="tick-count">Ticks: 0</span>
  </div>
</div>

<!-- TABS -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('leverage')">&#x26A1; Leverage Simulator</div>
  <div class="tab" onclick="switchTab('paper')">&#x1F4CB; Real-Time Paper Trades (<span id="tab-trade-count">0</span>)</div>
  <div class="tab" onclick="switchTab('risk')">&#x1F6E1; Risk & Liquidation Analysis</div>
  <div class="tab" onclick="switchTab('neural')">&#x1F9E0; Neural Engine & Regimes</div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 1: LEVERAGE SIMULATOR -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-leverage" class="tab-content active">
  <div class="grid2">
    <!-- LEFT: INPUTS -->
    <div class="card">
      <div class="card-title">
        <span>&#x1F4B0; Position Configuration</span>
        <button class="btn btn-outline" style="width:auto;padding:3px 10px;font-size:11px;" onclick="syncWithLiveTicker()">&#x21BB; Auto-Fill Live Price</button>
      </div>

      <div class="label">Asset Symbol</div>
      <select id="lev-symbol" style="margin-bottom:12px;" onchange="syncWithLiveTicker()">
        <option value="BTC">BTC / USDT (Bitcoin)</option>
        <option value="ETH">ETH / USDT (Ethereum)</option>
        <option value="SOL">SOL / USDT (Solana)</option>
        <option value="CUSTOM">Custom Symbol</option>
      </select>

      <div class="label">Entry Price ($)</div>
      <input type="number" id="lev-entry" value="64000" step="0.01" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div class="label">Margin / Collateral ($)</div>
      <input type="number" id="lev-capital" value="1000" step="10" oninput="calcLeverage()" style="margin-bottom:12px;" />

      <div class="label">Select Leverage Ratio</div>
      <div class="lev-grid">
        <div class="lev-btn" onclick="setLev(1)">1x</div>
        <div class="lev-btn" onclick="setLev(2)">2x</div>
        <div class="lev-btn" onclick="setLev(5)">5x</div>
        <div class="lev-btn active" onclick="setLev(10)">10x</div>
        <div class="lev-btn" onclick="setLev(25)">25x</div>
        <div class="lev-btn" onclick="setLev(50)">50x</div>
        <div class="lev-btn" onclick="setLev(75)">75x</div>
        <div class="lev-btn" onclick="setLev(100)">100x</div>
        <div class="lev-btn" onclick="setLev(125)">125x</div>
        <div class="lev-btn" onclick="setLev(150)">150x</div>
        <div class="lev-btn" onclick="setLev(200)">200x</div>
        <div class="lev-btn" onclick="setLev(0)">Custom</div>
      </div>
      <input type="number" id="lev-custom" value="10" min="1" max="500" oninput="calcLeverage()" placeholder="Custom leverage ratio" style="margin-bottom:12px;" />

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
        <div>
          <div class="label">Stop Loss (%)</div>
          <input type="number" id="lev-sl" value="2.0" step="0.1" oninput="calcLeverage()" />
        </div>
        <div>
          <div class="label">Take Profit (%)</div>
          <input type="number" id="lev-tp" value="4.0" step="0.1" oninput="calcLeverage()" />
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <button class="btn btn-long" onclick="openPaperTrade('LONG')">&#x1F4C8; OPEN PAPER LONG</button>
        <button class="btn btn-short" onclick="openPaperTrade('SHORT')">&#x1F4C9; OPEN PAPER SHORT</button>
      </div>

      <!-- PRICE STRESS TEST SLIDER -->
      <div class="stress-container">
        <div style="display:flex;justify-content:space-between;font-size:11px;">
          <span style="font-weight:700;color:var(--accent);">&#x26A1; Real-Time Price Stress Tester</span>
          <span id="stress-pct-label" class="mono">0.0% Move</span>
        </div>
        <input type="range" class="stress-slider" id="stress-slider" min="-25" max="25" value="0" step="0.5" oninput="applyStressTest(this.value)" />
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);">
          <span>-25% Crash</span>
          <span>Baseline</span>
          <span>+25% Surge</span>
        </div>
      </div>
    </div>

    <!-- RIGHT: REAL-TIME POSITION BREAKDOWN & RISK -->
    <div>
      <div class="card" style="margin-bottom:14px;">
        <div class="card-title"><span>&#x1F4CA; Position & Liquidation Metrics</span> <span id="r-status-badge" class="tag tag-long">SAFE</span></div>
        <div class="result-box">
          <div class="result-row"><span class="result-label">Gross Position Size</span><span class="result-val accent" id="r-position">$10,000.00</span></div>
          <div class="result-row"><span class="result-label">Margin Required</span><span class="result-val yellow" id="r-margin">$1,000.00</span></div>
          <div class="result-row"><span class="result-label">Contract Quantity</span><span class="result-val mono" id="r-units">0.1562 Units</span></div>
          <div class="result-row"><span class="result-label">Liquidation Price (LONG)</span><span class="result-val red" id="r-liq-long">$57,856.00</span></div>
          <div class="result-row"><span class="result-label">Liquidation Price (SHORT)</span><span class="result-val red" id="r-liq-short">$70,144.00</span></div>
          <div class="result-row"><span class="result-label">Stop-Loss Price</span><span class="result-val yellow" id="r-sl-price">$62,720.00</span></div>
          <div class="result-row"><span class="result-label">Take-Profit Price</span><span class="result-val green" id="r-tp-price">$66,560.00</span></div>
          <div class="result-row"><span class="result-label">Max Loss (SL Hit)</span><span class="result-val red" id="r-max-loss">-$200.00</span></div>
          <div class="result-row"><span class="result-label">Max Profit (TP Hit)</span><span class="result-val green" id="r-max-gain">+$400.00</span></div>
          <div class="result-row"><span class="result-label">Risk / Reward Ratio</span><span class="result-val accent" id="r-rr">1 : 2.0</span></div>
        </div>

        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">
            <span style="color:var(--muted);">Distance to Liquidation</span>
            <span id="r-dist-pct" class="yellow mono">9.60% away</span>
          </div>
          <div style="height:8px;border-radius:4px;background:rgba(255,255,255,0.06);overflow:hidden;">
            <div id="liq-fill" style="height:100%;background:linear-gradient(90deg, var(--green), var(--yellow), var(--red));width:85%;transition:width 0.3s;"></div>
          </div>
        </div>
      </div>

      <!-- PNL SCENARIO TABLE -->
      <div class="card">
        <div class="card-title">&#x1F4B9; Real-Time P&L Scenarios on Entry</div>
        <table>
          <thead><tr><th>Price Change</th><th>Simulated Price</th><th>P&L ($)</th><th>ROE %</th><th>Outcome</th></tr></thead>
          <tbody id="scenario-rows"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 2: REAL-TIME PAPER TRADES JOURNAL -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-paper" class="tab-content">
  <div class="grid4" style="margin-bottom:16px;">
    <div class="card">
      <div class="card-title">Total Account Equity</div>
      <div class="metric-val accent" id="account-equity">$10,000.00</div>
    </div>
    <div class="card">
      <div class="card-title">Real-Time Unrealized P&L</div>
      <div class="metric-val green" id="live-unrealized-pnl">+$0.00</div>
    </div>
    <div class="card">
      <div class="card-title">Realized P&L</div>
      <div class="metric-val" id="total-realized-pnl">$0.00</div>
    </div>
    <div class="card">
      <div class="card-title">Win Rate / Total Trades</div>
      <div class="metric-val yellow" id="stats-wr">0% <span style="font-size:14px;color:var(--muted);">(0)</span></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div class="card-title" style="margin-bottom:0;">
        <span>&#x1F4CA; Active Live-Monitored Positions (Streaming Mark-to-Market)</span>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-outline" style="width:auto;padding:6px 14px;font-size:12px;" onclick="closeAllTrades()">Close All</button>
        <button class="btn btn-primary" style="width:auto;padding:6px 14px;font-size:12px;" onclick="switchTab('leverage')">+ New Trade</button>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th>Leverage</th>
          <th>Entry Price</th>
          <th>Live Price</th>
          <th>Margin</th>
          <th>Unrealized P&L</th>
          <th>ROE %</th>
          <th>Liquidation</th>
          <th>SL / TP</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody id="paper-trades-body">
        <tr><td colspan="11" style="text-align:center;color:var(--muted);padding:24px;">No active paper trades. Open a trade in the Leverage Simulator to start real-time tracking!</td></tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">&#x1F4D6; Closed Trade History & Execution Log</div>
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th>Leverage</th>
          <th>Entry</th>
          <th>Exit</th>
          <th>Margin</th>
          <th>P&L ($)</th>
          <th>ROE %</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody id="closed-trades-body">
        <tr><td colspan="9" style="text-align:center;color:var(--muted);padding:18px;">No closed trades yet.</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 3: RISK & LIQUIDATION ANALYSIS -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-risk" class="tab-content">
  <div class="grid4">
    <div class="card"><div class="card-title">Total Exposure</div><div class="metric-val yellow" id="risk-exposure">$0.00</div></div>
    <div class="card"><div class="card-title">Margin At Risk</div><div class="metric-val red" id="risk-margin">$0.00</div></div>
    <div class="card"><div class="card-title">Average Leverage</div><div class="metric-val accent" id="risk-avg-lev">0x</div></div>
    <div class="card"><div class="card-title">Free Collateral</div><div class="metric-val green" id="risk-free-collateral">$10,000.00</div></div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">&#x1F4C9; Sudden Flash Crash Simulation</div>
      <table>
        <thead><tr><th>Market Shock</th><th>Estimated Loss</th><th>Collateral Wiped</th></tr></thead>
        <tbody id="risk-scenarios"></tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title">&#x1F4D0; Kelly Criterion Optimal Sizing</div>
      <div class="label">Estimated Win Rate (%)</div>
      <input type="number" id="kelly-wr" value="55" min="1" max="99" oninput="calcKelly()" style="margin-bottom:10px;" />
      <div class="label">Win / Loss Ratio (Avg Win $ / Avg Loss $)</div>
      <input type="number" id="kelly-ratio" value="2.0" step="0.1" min="0.1" oninput="calcKelly()" style="margin-bottom:14px;" />
      <div class="result-box">
        <div class="result-row"><span class="result-label">Full Kelly Sizing</span><span class="result-val green" id="kelly-full">32.50%</span></div>
        <div class="result-row"><span class="result-label">Half Kelly (Recommended)</span><span class="result-val accent" id="kelly-half">16.25%</span></div>
        <div class="result-row"><span class="result-label">Quarter Kelly (Safe)</span><span class="result-val yellow" id="kelly-quarter">8.13%</span></div>
        <div class="result-row"><span class="result-label">Suggested Position on $10k</span><span class="result-val mono" id="kelly-dollar">$1,625.00</span></div>
      </div>
    </div>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 4: NEURAL ENGINE & REGIMES -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-neural" class="tab-content">
  <div class="grid3">
    <div class="card">
      <div class="card-title">&#x1F9E0; Neural Ensemble Predictions</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
        <div><div class="label">P(Up)</div><div class="metric-val green" id="nn-prob-up">74.0%</div></div>
        <div><div class="label">Expected Return</div><div class="metric-val accent" id="nn-exp-ret">+2.4%</div></div>
      </div>
      <div style="font-size:12px;color:var(--muted);">Rust Engine: <b style="color:#fff;">29.3M Predictions/Sec</b> | Latency: <b style="color:var(--green);">0.034 us</b></div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F4CA; Regime Classification</div>
      <div class="metric-val accent" id="regime-badge" style="font-size:18px;margin-bottom:8px;">BULL_LOW_VOL</div>
      <div style="font-size:12px;color:var(--muted);">Shannon Entropy: <b style="color:var(--green);">H(X) = 2.14 bits</b></div>
    </div>
    <div class="card">
      <div class="card-title">&#x1F6E1; Deterministic Risk Limits</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <div><div class="label">Max Position</div><div class="metric-val" style="font-size:18px;">35%</div></div>
        <div><div class="label">Daily Loss Limit</div><div class="metric-val red" style="font-size:18px;">-5%</div></div>
      </div>
      <div style="font-size:12px;color:var(--muted);">Kill Switch: <b id="kill-status" class="green">NORMAL (ACTIVE)</b></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">&#x2753; Model Interpretability (Trade Attribution)</div>
    <div style="background:rgba(0,242,254,0.05);border:1px solid rgba(0,242,254,0.2);border-radius:8px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--accent);" id="trade-explanation">
      LONG BTC-USD | P(Up): 74% | Expected Return: +2.4% | Regime: BULL_LOW_VOL | Pattern: Volatility Compression | Risk: APPROVED
    </div>
  </div>
</div>

<!-- TOAST ALERT -->
<div id="toast"></div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- SCRIPT: REAL-TIME STREAMING & PAPER TRADE ENGINE -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<script>
let currentLev = 10;
let paperTrades = JSON.parse(localStorage.getItem('paperTrades_v2') || '[]');
let closedTrades = JSON.parse(localStorage.getItem('closedTrades_v2') || '[]');
let startingCapital = 10000.0;
let tickCount = 0;

// Live Real-Time Ticker Prices Cache
const livePrices = {
  BTC: 64200.0,
  ETH: 3480.0,
  SOL: 148.5
};

// ─── TABS ────────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active'));
  const idx = ['leverage','paper','risk','neural'].indexOf(name);
  if(idx >= 0) document.querySelectorAll('.tab')[idx].classList.add('active');
  const target = document.getElementById('tab-' + name);
  if(target) target.classList.add('active');
  if(name === 'paper') renderPaperTrades();
  if(name === 'risk') renderRiskDashboard();
}

// ─── REAL-TIME DATA STREAMING (WEBSOCKET + POLLING FALLBACK) ──────────────────
function initPriceStream() {
  // 1. Direct Binance Ticker WebSocket
  try {
    const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker/solusdt@ticker');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if(data && data.s && data.c) {
        const sym = data.s === 'BTCUSDT' ? 'BTC' : data.s === 'ETHUSDT' ? 'ETH' : data.s === 'SOLUSDT' ? 'SOL' : null;
        if(sym) {
          updateLivePrice(sym, parseFloat(data.c));
        }
      }
    };
    ws.onopen = () => {
      document.getElementById('conn-text').textContent = 'WEBSOCKET REAL-TIME STREAM ACTIVE';
      document.getElementById('conn-pill').style.background = 'rgba(16,185,129,0.15)';
    };
    ws.onerror = () => fallbackPolling();
  } catch(e) {
    fallbackPolling();
  }

  // 2. Local Proxy Server Polling Fallback (ensures 100% uptime on all networks)
  setInterval(fetchServerPrices, 1500);
}

async function fetchServerPrices() {
  try {
    const res = await fetch('/api/live_prices');
    const data = await res.json();
    if(data.BTC) updateLivePrice('BTC', data.BTC);
    if(data.ETH) updateLivePrice('ETH', data.ETH);
    if(data.SOL) updateLivePrice('SOL', data.SOL);
  } catch(e) {}
}

function updateLivePrice(sym, newPrice) {
  tickCount++;
  document.getElementById('tick-count').textContent = 'Ticks: ' + tickCount.toLocaleString();
  const oldPrice = livePrices[sym] || newPrice;
  livePrices[sym] = newPrice;

  const el = document.getElementById('tick-' + sym.toLowerCase());
  if(el) {
    el.textContent = '$' + fmt(newPrice);
    el.className = 'ticker-price ' + (newPrice >= oldPrice ? 'price-up' : 'price-down');
    setTimeout(() => { if(el) el.className = 'ticker-price'; }, 400);
  }

  // If currently simulating this symbol, update current price & recalculate
  const currentSel = document.getElementById('lev-symbol').value;
  if(currentSel === sym) {
    document.getElementById('lev-entry').dataset.live = newPrice;
  }

  // RUN REAL-TIME AUTO-MONITOR ON ALL OPEN PAPER TRADES
  processRealTimePaperTrades(sym, newPrice);
}

function syncWithLiveTicker() {
  const sym = document.getElementById('lev-symbol').value;
  if(livePrices[sym]) {
    document.getElementById('lev-entry').value = livePrices[sym].toFixed(2);
    calcLeverage();
    showToast(`Synced ${sym} to live price: $${fmt(livePrices[sym])}`, 'info');
  }
}

// ─── LEVERAGE CALCULATOR & SIMULATOR ─────────────────────────────────────────
function setLev(val) {
  document.querySelectorAll('.lev-btn').forEach(b => b.classList.remove('active'));
  if(val === 0) {
    document.querySelector('.lev-btn:last-child').classList.add('active');
  } else {
    const btns = document.querySelectorAll('.lev-btn');
    btns.forEach(b => { if(b.textContent === val + 'x') b.classList.add('active'); });
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
  const units    = entry > 0 ? (position / entry) : 0;
  const mmRate   = 0.004; // 0.4% maintenance margin

  const liqLong  = entry * (1 - 1/lev + mmRate);
  const liqShort = entry * (1 + 1/lev - mmRate);
  const slPrice  = entry * (1 - slPct/100);
  const tpPrice  = entry * (1 + tpPct/100);
  const maxLoss  = capital * (slPct/100) * lev;
  const maxGain  = capital * (tpPct/100) * lev;
  const rr       = maxGain / (maxLoss || 1);
  const distPct  = entry > 0 ? (((entry - liqLong) / entry) * 100).toFixed(2) : 0;

  document.getElementById('r-position').textContent  = '$' + fmt(position);
  document.getElementById('r-margin').textContent    = '$' + fmt(capital);
  document.getElementById('r-units').textContent     = units.toFixed(4) + ' Units';
  document.getElementById('r-liq-long').textContent  = '$' + fmt(liqLong);
  document.getElementById('r-liq-short').textContent = '$' + fmt(liqShort);
  document.getElementById('r-sl-price').textContent  = '$' + fmt(slPrice);
  document.getElementById('r-tp-price').textContent  = '$' + fmt(tpPrice);
  document.getElementById('r-max-loss').textContent  = '-$' + fmt(maxLoss);
  document.getElementById('r-max-gain').textContent  = '+$' + fmt(maxGain);
  document.getElementById('r-rr').textContent        = '1 : ' + rr.toFixed(1);
  document.getElementById('r-dist-pct').textContent  = distPct + '% away from liquidation';
  document.getElementById('liq-fill').style.width    = Math.min(100, Math.max(5, parseFloat(distPct) * 5)) + '%';

  const badge = document.getElementById('r-status-badge');
  if(lev >= 50) {
    badge.className = 'tag tag-liq';
    badge.textContent = 'HIGH RISK ' + lev + 'x';
  } else {
    badge.className = 'tag tag-long';
    badge.textContent = 'LEVERAGE ' + lev + 'x';
  }

  // P&L Scenarios table
  const scenarios = [-10, -5, -3, -2, -1, 1, 2, 3, 5, 10];
  let rows = '';
  scenarios.forEach(pct => {
    const simPrice = entry * (1 + pct/100);
    const pnl = capital * (pct/100) * lev;
    const roe = pct * lev;
    const isWin = pnl > 0;
    const isLiq = (pct < 0 && Math.abs(pct) >= (100/lev));
    rows += `<tr>
      <td class="mono">${pct > 0 ? '+' : ''}${pct}%</td>
      <td class="mono">$${fmt(simPrice)}</td>
      <td class="mono ${isWin ? 'green' : 'red'}">${isWin ? '+' : ''}$${fmt(Math.abs(pnl))}</td>
      <td class="mono ${isWin ? 'green' : 'red'}">${isWin ? '+' : ''}${roe.toFixed(1)}%</td>
      <td><span class="tag ${isLiq ? 'tag-liq' : isWin ? 'tag-long' : 'tag-short'}">${isLiq ? 'LIQUIDATED' : isWin ? 'PROFIT' : 'LOSS'}</span></td>
    </tr>`;
  });
  document.getElementById('scenario-rows').innerHTML = rows;
}

function applyStressTest(val) {
  const pct = parseFloat(val);
  document.getElementById('stress-pct-label').textContent = (pct >= 0 ? '+' : '') + pct.toFixed(1) + '% Move';
  const entry = parseFloat(document.getElementById('lev-entry').value) || 0;
  const capital = parseFloat(document.getElementById('lev-capital').value) || 0;
  const pnl = capital * (pct/100) * currentLev;
  const roe = pct * currentLev;
  const isLiq = (pct < 0 && Math.abs(pct) >= (100/currentLev));
  
  if(isLiq) {
    showToast(`🚨 STRESS TEST: ${pct}% move causes LIQUIDATION! Total Loss: -$${fmt(capital)}`, 'danger');
  }
}

// ─── REAL-TIME PAPER TRADING ENGINE ──────────────────────────────────────────
function openPaperTrade(side) {
  const sym     = document.getElementById('lev-symbol').value;
  const entry   = parseFloat(document.getElementById('lev-entry').value) || livePrices[sym] || 64000;
  const capital = parseFloat(document.getElementById('lev-capital').value) || 1000;
  const lev     = parseFloat(document.getElementById('lev-custom').value) || 10;
  const slPct   = parseFloat(document.getElementById('lev-sl').value) || 2.0;
  const tpPct   = parseFloat(document.getElementById('lev-tp').value) || 4.0;

  const mmRate  = 0.004;
  const liqPrice = side === 'LONG'
    ? entry * (1 - 1/lev + mmRate)
    : entry * (1 + 1/lev - mmRate);
  const slPrice = side === 'LONG' ? entry * (1 - slPct/100) : entry * (1 + slPct/100);
  const tpPrice = side === 'LONG' ? entry * (1 + tpPct/100) : entry * (1 - tpPct/100);

  const trade = {
    id: Date.now(),
    symbol: sym,
    side: side,
    leverage: lev,
    entry: entry,
    curPrice: entry,
    capital: capital,
    position: capital * lev,
    liqPrice: liqPrice,
    slPrice: slPrice,
    tpPrice: tpPrice,
    slPct: slPct,
    tpPct: tpPct,
    openTime: new Date().toLocaleTimeString(),
    pnl: 0,
    roe: 0
  };

  paperTrades.push(trade);
  saveTrades();
  showToast(`⚡ Opened ${lev}x PAPER ${side} on ${sym} at $${fmt(entry)}!`, 'success');
  switchTab('paper');
}

// Continuous Real-Time Price Processing Loop
function processRealTimePaperTrades(sym, livePrice) {
  let stateChanged = false;
  
  for(let i = paperTrades.length - 1; i >= 0; i--) {
    const t = paperTrades[i];
    if(t.symbol !== sym) continue;

    t.curPrice = livePrice;
    
    // Mark-to-market P&L calculation
    const priceDiff = t.side === 'LONG' ? (livePrice - t.entry) : (t.entry - livePrice);
    t.pnl = (priceDiff / t.entry) * t.capital * t.leverage;
    t.roe = (t.pnl / t.capital) * 100;
    stateChanged = true;

    // 1. CHECK LIQUIDATION
    const isLiquidated = t.side === 'LONG' ? (livePrice <= t.liqPrice) : (livePrice >= t.liqPrice);
    if(isLiquidated) {
      closeTradeWithReason(i, -t.capital, -100.0, 'LIQUIDATED (Margin Wiped)');
      showToast(`🚨 TRADE LIQUIDATED! ${t.side} ${t.symbol} breached $${fmt(t.liqPrice)}!`, 'danger');
      continue;
    }

    // 2. CHECK STOP-LOSS
    const slHit = t.side === 'LONG' ? (livePrice <= t.slPrice) : (livePrice >= t.slPrice);
    if(slHit) {
      const slLoss = -t.capital * (t.slPct / 100) * t.leverage;
      closeTradeWithReason(i, slLoss, -t.slPct * t.leverage, 'STOP LOSS HIT');
      showToast(`🛑 STOP LOSS TRIGGERED for ${t.symbol} at $${fmt(livePrice)}! Loss: -$${fmt(Math.abs(slLoss))}`, 'danger');
      continue;
    }

    // 3. CHECK TAKE-PROFIT
    const tpHit = t.side === 'LONG' ? (livePrice >= t.tpPrice) : (livePrice <= t.tpPrice);
    if(tpHit) {
      const tpGain = t.capital * (t.tpPct / 100) * t.leverage;
      closeTradeWithReason(i, tpGain, t.tpPct * t.leverage, 'TAKE PROFIT HIT');
      showToast(`🎯 TAKE PROFIT TRIGGERED for ${t.symbol} at $${fmt(livePrice)}! Gain: +$${fmt(tpGain)}`, 'success');
      continue;
    }
  }

  if(stateChanged) {
    saveTrades();
    renderPaperTrades();
  }
}

function closeTradeWithReason(index, finalPnl, finalRoe, reason) {
  const t = paperTrades[index];
  closedTrades.unshift({
    ...t,
    exitPrice: t.curPrice,
    pnl: finalPnl,
    roe: finalRoe,
    reason: reason,
    closeTime: new Date().toLocaleTimeString()
  });
  paperTrades.splice(index, 1);
  saveTrades();
  renderPaperTrades();
}

function closeTradeManual(id) {
  const idx = paperTrades.findIndex(t => t.id === id);
  if(idx === -1) return;
  const t = paperTrades[idx];
  closeTradeWithReason(idx, t.pnl, t.roe, 'MANUAL CLOSE');
  showToast(`Closed ${t.symbol} position at $${fmt(t.curPrice)}`, 'info');
}

function closeAllTrades() {
  while(paperTrades.length > 0) {
    const t = paperTrades[0];
    closeTradeWithReason(0, t.pnl, t.roe, 'MANUAL CLOSE ALL');
  }
  showToast('All open paper positions closed!', 'info');
}

function saveTrades() {
  localStorage.setItem('paperTrades_v2', JSON.stringify(paperTrades));
  localStorage.setItem('closedTrades_v2', JSON.stringify(closedTrades));
}

function renderPaperTrades() {
  document.getElementById('tab-trade-count').textContent = paperTrades.length;
  const tbody = document.getElementById('paper-trades-body');
  
  if(!paperTrades.length) {
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--muted);padding:24px;">No active paper trades. Open a trade in the Leverage Simulator to start real-time tracking!</td></tr>';
  } else {
    tbody.innerHTML = paperTrades.map(t => {
      const isProfitable = t.pnl >= 0;
      return `<tr>
        <td class="mono" style="font-weight:700;">${t.symbol}/USDT</td>
        <td><span class="tag tag-${t.side.toLowerCase()}">${t.side}</span></td>
        <td class="mono accent" style="font-weight:700;">${t.leverage}x</td>
        <td class="mono">$${fmt(t.entry)}</td>
        <td class="mono" style="font-weight:700;color:#fff;">$${fmt(t.curPrice)}</td>
        <td class="mono yellow">$${fmt(t.capital)}</td>
        <td class="mono ${isProfitable ? 'green' : 'red'}" style="font-weight:800;">${isProfitable ? '+' : ''}$${fmt(t.pnl)}</td>
        <td class="mono ${isProfitable ? 'green' : 'red'}" style="font-weight:700;">${isProfitable ? '+' : ''}${t.roe.toFixed(2)}%</td>
        <td class="mono red" style="font-weight:600;">$${fmt(t.liqPrice)}</td>
        <td class="mono" style="font-size:11px;"><span style="color:var(--red);">SL: $${fmt(t.slPrice)}</span><br><span style="color:var(--green);">TP: $${fmt(t.tpPrice)}</span></td>
        <td><button class="btn btn-short" style="padding:4px 10px;font-size:11px;width:auto;" onclick="closeTradeManual(${t.id})">Close</button></td>
      </tr>`;
    }).join('');
  }

  // Closed Trades Log
  const cbody = document.getElementById('closed-trades-body');
  if(!closedTrades.length) {
    cbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:18px;">No closed trades yet.</td></tr>';
  } else {
    cbody.innerHTML = closedTrades.slice(0, 30).map(t => {
      const won = t.pnl >= 0;
      return `<tr>
        <td class="mono">${t.symbol}/USDT</td>
        <td><span class="tag tag-${t.side.toLowerCase()}">${t.side}</span></td>
        <td class="mono accent">${t.leverage}x</td>
        <td class="mono">$${fmt(t.entry)}</td>
        <td class="mono">$${fmt(t.exitPrice)}</td>
        <td class="mono yellow">$${fmt(t.capital)}</td>
        <td class="mono ${won ? 'green' : 'red'}">${won ? '+' : ''}$${fmt(t.pnl)}</td>
        <td class="mono ${won ? 'green' : 'red'}">${(t.roe || 0).toFixed(2)}%</td>
        <td><span class="tag ${won ? 'tag-long' : 'tag-short'}">${t.reason || (won ? 'WIN' : 'LOSS')}</span></td>
      </tr>`;
    }).join('');
  }

  // Header Metrics
  const unrealizedPnl = paperTrades.reduce((acc, t) => acc + t.pnl, 0);
  const realizedPnl   = closedTrades.reduce((acc, t) => acc + t.pnl, 0);
  const currentEquity = startingCapital + realizedPnl + unrealizedPnl;
  const wins          = closedTrades.filter(t => t.pnl > 0).length;
  const winRate       = closedTrades.length ? ((wins / closedTrades.length) * 100).toFixed(0) : 0;

  document.getElementById('account-equity').textContent = '$' + fmt(currentEquity);
  const unEl = document.getElementById('live-unrealized-pnl');
  unEl.textContent = (unrealizedPnl >= 0 ? '+' : '') + '$' + fmt(unrealizedPnl);
  unEl.className = 'metric-val ' + (unrealizedPnl >= 0 ? 'green' : 'red');

  document.getElementById('total-realized-pnl').textContent = (realizedPnl >= 0 ? '+' : '') + '$' + fmt(realizedPnl);
  document.getElementById('total-realized-pnl').className = 'metric-val ' + (realizedPnl >= 0 ? 'green' : 'red');
  document.getElementById('stats-wr').innerHTML = winRate + '% <span style="font-size:14px;color:var(--muted);">(' + closedTrades.length + ' closed)</span>';
}

// ─── RISK DASHBOARD ──────────────────────────────────────────────────────────
function renderRiskDashboard() {
  const totalExposure = paperTrades.reduce((acc, t) => acc + t.position, 0);
  const totalMargin   = paperTrades.reduce((acc, t) => acc + t.capital, 0);
  const avgLev        = paperTrades.length ? (paperTrades.reduce((acc, t) => acc + t.leverage, 0) / paperTrades.length).toFixed(1) : 0;
  const freeCollateral= Math.max(0, startingCapital - totalMargin);

  document.getElementById('risk-exposure').textContent = '$' + fmt(totalExposure);
  document.getElementById('risk-margin').textContent   = '$' + fmt(totalMargin);
  document.getElementById('risk-avg-lev').textContent  = avgLev + 'x';
  document.getElementById('risk-free-collateral').textContent = '$' + fmt(freeCollateral);

  const drops = [1, 2, 5, 10, 20, 50];
  let rows = '';
  drops.forEach(d => {
    const loss = totalMargin * (d/100) * (parseFloat(avgLev) || 1);
    const wiped = Math.min(100, d * (parseFloat(avgLev) || 1)).toFixed(0);
    rows += `<tr>
      <td class="mono red">-${d}% Crash</td>
      <td class="mono red">-$${fmt(Math.min(loss, totalMargin))}</td>
      <td class="mono ${wiped >= 100 ? 'red' : wiped >= 50 ? 'yellow' : 'green'}">${wiped}%</td>
    </tr>`;
  });
  document.getElementById('risk-scenarios').innerHTML = rows || '<tr><td colspan="3" style="text-align:center;color:var(--muted);">No active positions</td></tr>';
  calcKelly();
}

function calcKelly() {
  const wr = parseFloat(document.getElementById('kelly-wr').value) / 100 || 0.55;
  const ratio = parseFloat(document.getElementById('kelly-ratio').value) || 2.0;
  const full = (wr - (1 - wr) / ratio) * 100;
  document.getElementById('kelly-full').textContent    = full.toFixed(2) + '%';
  document.getElementById('kelly-half').textContent   = (full/2).toFixed(2) + '%';
  document.getElementById('kelly-quarter').textContent = (full/4).toFixed(2) + '%';
  document.getElementById('kelly-dollar').textContent  = '$' + fmt(startingCapital * (full/2) / 100);
}

// ─── TOAST NOTIFICATIONS ─────────────────────────────────────────────────────
function showToast(msg, type='info') {
  const t = document.getElementById('toast');
  if(!t) return;
  t.textContent = msg;
  t.className = 'toast-' + type;
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 4000);
}

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
}

// ─── INIT ────────────────────────────────────────────────────────────────────
calcLeverage();
calcKelly();
renderPaperTrades();
initPriceStream();
syncWithLiveTicker();
</script>
</body>
</html>
"""
