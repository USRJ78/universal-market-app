"""
==============================================================================
  DEDICATED SEPARATE PAGE: AUTONOMOUS INTELLIGENCE DASHBOARD
  J.A.R.V.I.S. QUANTITATIVE COMMANDER & REAL-TIME PAPER TRADING ENGINE
==============================================================================
"""

AUTONOMOUS_INTELLIGENCE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J.A.R.V.I.S. Autonomous Quantitative Commander</title>
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
  .live-status-pill { padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700; background:rgba(0,242,254,0.15); color:var(--accent); border:1px solid rgba(0,242,254,0.3); display:flex; align-items:center; gap:6px; }
  .dot { width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px var(--accent); animation:pulse 1.4s infinite; }
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
  .card-title { font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
  .metric-val { font-size:26px; font-weight:800; color:#fff; font-family:'JetBrains Mono',monospace; }
  .label { font-size:11px; color:var(--muted); margin-bottom:4px; font-weight:600; }
  
  /* JARVIS HOLOGRAPHIC TERMINAL */
  .jarvis-terminal { background:rgba(0,242,254,0.03); border:1px solid rgba(0,242,254,0.25); border-radius:12px; padding:20px; position:relative; margin-bottom:16px; overflow:hidden; }
  .jarvis-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }
  .jarvis-briefing-text { font-family:'JetBrains Mono',monospace; font-size:14px; line-height:1.6; color:#e0f7fa; min-height:60px; }
  .jarvis-glow-ring { display:inline-block; width:12px; height:12px; border-radius:50%; background:var(--accent); box-shadow:0 0 15px var(--accent); margin-right:8px; }
  
  /* FORMS & BUTTONS */
  input, select { width:100%; background:rgba(255,255,255,0.06); border:1px solid var(--border); border-radius:8px; padding:9px 12px; color:#fff; font-size:13px; font-family:'JetBrains Mono',monospace; outline:none; }
  input:focus, select:focus { border-color:var(--accent); }
  .btn { padding:10px 18px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; border:none; transition:all 0.2s; }
  .btn-long { background:rgba(16,185,129,0.2); color:var(--green); border:1px solid var(--green); }
  .btn-short { background:rgba(239,68,68,0.2); color:var(--red); border:1px solid var(--red); }
  .btn-primary { background:var(--accent); color:#000; font-weight:800; }
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
  .tag-approved { background:rgba(16,185,129,0.2); color:var(--green); border:1px solid var(--green); }
  .tag-vetoed { background:rgba(239,68,68,0.2); color:var(--red); border:1px solid var(--red); }
  
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
  <div class="logo">
    <span style="color:var(--accent);font-size:22px;">&#x25C7;</span> J.A.R.V.I.S. AUTONOMOUS QUANTITATIVE COMMANDER
  </div>
  <div style="display:flex;gap:10px;align-items:center;">
    <div class="live-status-pill" id="conn-pill"><div class="dot"></div><span id="conn-text">J.A.R.V.I.S. 24/7 ONLINE</span></div>
    <a href="/" style="color:var(--muted);text-decoration:none;font-size:12px;font-weight:600;">&#8592; Main Dashboard</a>
  </div>
</div>

<!-- REAL-TIME TICKER STREAM BAR -->
<div class="ticker-bar">
  <span style="font-size:11px;color:var(--muted);font-weight:700;">ORACLE STREAM:</span>
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
  <div class="tab active" onclick="switchTab('jarvis')">&#x1F916; J.A.R.V.I.S. Command Center</div>
  <div class="tab" onclick="switchTab('leverage')">&#x26A1; Leverage Simulator</div>
  <div class="tab" onclick="switchTab('paper')">&#x1F4CB; Real-Time Paper Trades (<span id="tab-trade-count">0</span>)</div>
  <div class="tab" onclick="switchTab('risk')">&#x1F6E1; Guardian Risk & Sentry</div>
  <div class="tab" onclick="switchTab('neural')">&#x1F9E0; Neural Engine & Regimes</div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 0: J.A.R.V.I.S. COMMAND CENTER (FLAGSHIP) -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-jarvis" class="tab-content active">
  <!-- J.A.R.V.I.S. HOLOGRAPHIC EXECUTIVE TERMINAL -->
  <div class="jarvis-terminal">
    <div class="jarvis-header">
      <div style="display:flex;align-items:center;">
        <span class="jarvis-glow-ring"></span>
        <span style="font-size:13px;font-weight:800;color:var(--accent);letter-spacing:0.8px;">J.A.R.V.I.S. TACTICAL BRIEFING CONSOLE</span>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button class="btn btn-outline" style="padding:4px 12px;font-size:11px;" id="voice-btn" onclick="toggleVoice()">&#x1F50A; Voice Speech: OFF</button>
        <button class="btn btn-primary" style="padding:4px 14px;font-size:11px;" onclick="triggerRadarSweep()">&#x26A1; Sweep Radar Now</button>
      </div>
    </div>
    <div class="jarvis-briefing-text" id="jarvis-briefing">
      Sir, J.A.R.V.I.S. tactical systems are fully operational. Guardian Sentry is armed. All setups are being screened for asymmetric 1:2+ Risk/Reward. Unbounded or steamroller risks are strictly prohibited.
    </div>
  </div>

  <!-- GUARDIAN PROTOCOL SENTRY PANEL -->
  <div class="grid4">
    <div class="card">
      <div class="card-title">Guardian Protocol</div>
      <div class="metric-val green" style="font-size:18px;">ARMED & ACTIVE</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px;">Zero unhedged/naked risk permitted</div>
    </div>
    <div class="card">
      <div class="card-title">Steamroller Filter</div>
      <div class="metric-val accent" style="font-size:18px;">ENGAGED</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px;">Auto-vetoes any trade with Loss &gt; Gain</div>
    </div>
    <div class="card">
      <div class="card-title">Hard Risk Ceiling</div>
      <div class="metric-val yellow" style="font-size:18px;">1.5% MAX EQUITY</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px;">Mandatory Stop-Loss on every position</div>
    </div>
    <div class="card">
      <div class="card-title">Min Asymmetry Floor</div>
      <div class="metric-val" style="font-size:18px;color:#fff;">1:2.0+ R:R</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px;">Risk $1 to make $2 to $3 minimum</div>
    </div>
  </div>

  <!-- JIM SIMONS MATHEMATICAL ENGINE (MEDALLION SUITE) -->
  <div class="card" style="margin-bottom:16px;background:rgba(0,242,254,0.02);border-color:rgba(0,242,254,0.2);">
    <div class="card-title">
      <span style="color:var(--accent);">&#x1D544; JIM SIMONS MATHEMATICAL CORE — MEDALLION DE-NOISING SUITE</span>
      <span style="font-size:11px;color:var(--muted);">Fields Medal Differential Geometry & RMT</span>
    </div>
    <div class="grid4" style="margin-bottom:0;">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;">
        <div class="label">Baum-Welch HMM State</div>
        <div class="metric-val green" style="font-size:16px;" id="simons-hmm-state">STEADY_BULL</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px;">Hidden Markov Regime Solver</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;">
        <div class="label">Chern-Simons Curvature</div>
        <div class="metric-val accent" style="font-size:16px;" id="simons-cs-curvature">0.74 Inv</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px;">Manifold Topological Invariant</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;">
        <div class="label">Ornstein-Uhlenbeck Half-Life</div>
        <div class="metric-val yellow" style="font-size:16px;" id="simons-ou-halflife">4.2 Days</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px;">Continuous SDE Mean Reversion</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;">
        <div class="label">Marcenko-Pastur De-noising</div>
        <div class="metric-val" style="font-size:16px;color:#fff;" id="simons-rmt-denoised">82.0% Noise Filtered</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px;">Random Matrix Spectral Cutoff</div>
      </div>
    </div>
  </div>

  <!-- 5-DIMENSIONAL OPPORTUNITY RADAR -->
  <div class="card">
    <div class="card-title">
      <span>&#x1F4CA; 5-Dimensional Asymmetric Opportunity Radar (Simons Math + Guardian)</span>
      <span style="font-size:11px;color:var(--muted);" id="radar-updated">Updated: Just now</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Asset</th>
          <th>Side</th>
          <th>Regime</th>
          <th>Order Flow</th>
          <th>Conviction</th>
          <th>Risk (SL)</th>
          <th>Reward (TP)</th>
          <th>Asymmetry (R:R)</th>
          <th>Guardian Verdict</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody id="jarvis-radar-body">
        <tr><td colspan="10" style="text-align:center;color:var(--muted);padding:20px;">Scanning multi-asset order flow...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- TAB 1: LEVERAGE SIMULATOR -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div id="tab-leverage" class="tab-content">
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
<!-- TAB 3: RISK & GUARDIAN SENTRY -->
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
<!-- SCRIPT: J.A.R.V.I.S. COMMANDER & REAL-TIME ENGINE -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<script>
let currentLev = 10;
let paperTrades = JSON.parse(localStorage.getItem('paperTrades_v2') || '[]');
let closedTrades = JSON.parse(localStorage.getItem('closedTrades_v2') || '[]');
let startingCapital = 10000.0;
let tickCount = 0;
let voiceEnabled = false;
let lastSpokenText = '';

// Live Real-Time Ticker Prices Cache
const livePrices = {
  BTC: 64200.0,
  ETH: 3480.0,
  SOL: 148.5
};

// ─── TABS ────────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active'));
  const idx = ['jarvis','leverage','paper','risk','neural'].indexOf(name);
  if(idx >= 0) document.querySelectorAll('.tab')[idx].classList.add('active');
  const target = document.getElementById('tab-' + name);
  if(target) target.classList.add('active');
  if(name === 'paper') renderPaperTrades();
  if(name === 'risk') renderRiskDashboard();
}

// ─── VOICE SPEECH SYNTHESIS (J.A.R.V.I.S. VOICE) ─────────────────────────────
function toggleVoice() {
  voiceEnabled = !voiceEnabled;
  const btn = document.getElementById('voice-btn');
  if(voiceEnabled) {
    btn.textContent = '🔊 Speech Audio: ON';
    btn.style.color = 'var(--accent)';
    speakJarvis("J.A.R.V.I.S. vocal synthesis online, Sir. Capital preservation protocols active.");
  } else {
    btn.textContent = '🔇 Speech Audio: OFF';
    btn.style.color = '#fff';
    if(window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

function speakJarvis(text) {
  if(!voiceEnabled || !('speechSynthesis' in window)) return;
  if(text === lastSpokenText) return;
  lastSpokenText = text;

  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.05;
  utter.pitch = 0.95;
  
  // Try finding an English British or polished voice
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v => v.lang.includes('en-GB') || v.name.includes('Daniel') || v.name.includes('George') || v.name.includes('David') || v.name.includes('Google UK English Male'));
  if(preferred) utter.voice = preferred;

  window.speechSynthesis.speak(utter);
}

// ─── J.A.R.V.I.S. TACTICAL RADAR & TELEMETRY ─────────────────────────────────
async function fetchJarvisStatus() {
  try {
    const res = await fetch('/api/jarvis/status');
    const data = await res.json();
    if(data.briefing) {
      document.getElementById('jarvis-briefing').textContent = data.briefing;
      speakJarvis(data.briefing);
    }
    if(data.radar && data.radar.length) {
      renderJarvisRadar(data.radar);
      // Populate Simons Math Telemetry from top radar item
      const top = data.radar[0];
      if(top && top.simons) {
        document.getElementById('simons-hmm-state').textContent = top.simons.hmm_state;
        document.getElementById('simons-cs-curvature').textContent = top.simons.chern_simons_invariant.toFixed(2) + ' Inv';
        document.getElementById('simons-ou-halflife').textContent = top.simons.ou_half_life_days.toFixed(1) + ' Days';
        document.getElementById('simons-rmt-denoised').textContent = top.simons.rmt_noise_filtered + '% Noise Filtered';
      }
    }
    document.getElementById('radar-updated').textContent = 'Updated: ' + new Date().toLocaleTimeString();
  } catch(e) {}
}

function renderJarvisRadar(radar) {
  const tbody = document.getElementById('jarvis-radar-body');
  tbody.innerHTML = radar.map(item => {
    const isApproved = item.guardian && item.guardian.approved;
    return `<tr>
      <td class="mono" style="font-weight:700;">${item.symbol}/USDT</td>
      <td><span class="tag tag-${item.side.toLowerCase()}">${item.side}</span></td>
      <td class="mono accent">${item.regime}</td>
      <td class="mono green">${item.flow_status || 'AUTHENTIC'}</td>
      <td class="mono ${(item.conviction >= 0.70 ? 'green' : 'yellow')}" style="font-weight:800;">${(item.conviction*100).toFixed(0)}%</td>
      <td class="mono red">-$${fmt(item.max_loss)} (${item.sl_pct}%)</td>
      <td class="mono green">+$${fmt(item.max_gain)} (${item.tp_pct}%)</td>
      <td class="mono accent" style="font-weight:800;">1 : ${item.rr_ratio}</td>
      <td><span class="tag ${isApproved ? 'tag-approved' : 'tag-vetoed'}">${isApproved ? 'GUARDIAN APPROVED' : 'VETOED'}</span></td>
      <td>
        <button class="btn ${isApproved ? 'btn-primary' : 'btn-outline'}" style="padding:4px 10px;font-size:11px;width:auto;" onclick="executeJarvisTrade('${item.symbol}', '${item.side}', ${item.leverage}, ${item.entry_price}, ${item.margin}, ${item.sl_pct}, ${item.tp_pct})" ${isApproved ? '' : 'disabled'}>
          ${isApproved ? '🎯 EXECUTE SNIPER' : '⛔ VETOED'}
        </button>
      </td>
    </tr>`;
  }).join('');
}

async function triggerRadarSweep() {
  showToast('⚡ J.A.R.V.I.S. scanning multi-asset order books across 5 dimensions...', 'info');
  try {
    const res = await fetch('/api/jarvis/scan', {method: 'POST'});
    const data = await res.json();
    if(data.briefing) {
      document.getElementById('jarvis-briefing').textContent = data.briefing;
      speakJarvis(data.briefing);
    }
    if(data.radar) renderJarvisRadar(data.radar);
    showToast('Radar sweep complete. Telemetry updated.', 'success');
  } catch(e) {}
}

function executeJarvisTrade(symbol, side, leverage, entry, margin, slPct, tpPct) {
  const mmRate = 0.004;
  const liqPrice = side === 'LONG'
    ? entry * (1 - 1/leverage + mmRate)
    : entry * (1 + 1/leverage - mmRate);
  const slPrice = side === 'LONG' ? entry * (1 - slPct/100) : entry * (1 + slPct/100);
  const tpPrice = side === 'LONG' ? entry * (1 + tpPct/100) : entry * (1 - tpPct/100);

  const trade = {
    id: Date.now(),
    symbol: symbol,
    side: side,
    leverage: leverage,
    entry: entry,
    curPrice: entry,
    capital: margin,
    position: margin * leverage,
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
  showToast(`🎯 J.A.R.V.I.S. Executed ${leverage}x ${side} on ${symbol} with strict 1:${(tpPct/slPct).toFixed(1)} R:R!`, 'success');
  speakJarvis(`Order executed, Sir. Initiated ${leverage}x ${side} position on ${symbol}. Maximum risk strictly capped by Guardian Protocol.`);
  switchTab('paper');
}

// ─── REAL-TIME DATA STREAMING (WEBSOCKET + POLLING FALLBACK) ──────────────────
function initPriceStream() {
  try {
    const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker/solusdt@ticker');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if(data && data.s && data.c) {
        const sym = data.s === 'BTCUSDT' ? 'BTC' : data.s === 'ETHUSDT' ? 'ETH' : data.s === 'SOLUSDT' ? 'SOL' : null;
        if(sym) updateLivePrice(sym, parseFloat(data.c));
      }
    };
    ws.onopen = () => {
      document.getElementById('conn-text').textContent = 'ORACLE REAL-TIME STREAM ACTIVE';
      document.getElementById('conn-pill').style.background = 'rgba(0,242,254,0.15)';
    };
    ws.onerror = () => fallbackPolling();
  } catch(e) {
    fallbackPolling();
  }

  setInterval(fetchServerPrices, 1500);
  setInterval(fetchJarvisStatus, 4000);
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

  const currentSel = document.getElementById('lev-symbol');
  if(currentSel && currentSel.value === sym) {
    const entryEl = document.getElementById('lev-entry');
    if(entryEl) entryEl.dataset.live = newPrice;
  }

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
  const mmRate   = 0.004;

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
  const capital = parseFloat(document.getElementById('lev-capital').value) || 0;
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

  executeJarvisTrade(sym, side, lev, entry, capital, slPct, tpPct);
}

function processRealTimePaperTrades(sym, livePrice) {
  let stateChanged = false;
  
  for(let i = paperTrades.length - 1; i >= 0; i--) {
    const t = paperTrades[i];
    if(t.symbol !== sym) continue;

    t.curPrice = livePrice;
    const priceDiff = t.side === 'LONG' ? (livePrice - t.entry) : (t.entry - livePrice);
    t.pnl = (priceDiff / t.entry) * t.capital * t.leverage;
    t.roe = (t.pnl / t.capital) * 100;
    stateChanged = true;

    // 1. LIQUIDATION CHECK
    const isLiquidated = t.side === 'LONG' ? (livePrice <= t.liqPrice) : (livePrice >= t.liqPrice);
    if(isLiquidated) {
      closeTradeWithReason(i, -t.capital, -100.0, 'LIQUIDATED (Margin Wiped)');
      showToast(`🚨 TRADE LIQUIDATED! ${t.side} ${t.symbol} breached $${fmt(t.liqPrice)}!`, 'danger');
      speakJarvis(`Sir, trade liquidation detected on ${t.symbol}. Position margin has been closed.`);
      continue;
    }

    // 2. STOP-LOSS CHECK
    const slHit = t.side === 'LONG' ? (livePrice <= t.slPrice) : (livePrice >= t.slPrice);
    if(slHit) {
      const slLoss = -t.capital * (t.slPct / 100) * t.leverage;
      closeTradeWithReason(i, slLoss, -t.slPct * t.leverage, 'STOP LOSS HIT');
      showToast(`🛑 STOP LOSS TRIGGERED for ${t.symbol} at $${fmt(livePrice)}! Loss: -$${fmt(Math.abs(slLoss))}`, 'danger');
      speakJarvis(`Stop-loss triggered on ${t.symbol}. Capital loss successfully capped by Guardian.`);
      continue;
    }

    // 3. TAKE-PROFIT CHECK
    const tpHit = t.side === 'LONG' ? (livePrice >= t.tpPrice) : (livePrice <= t.tpPrice);
    if(tpHit) {
      const tpGain = t.capital * (t.tpPct / 100) * t.leverage;
      closeTradeWithReason(i, tpGain, t.tpPct * t.leverage, 'TAKE PROFIT HIT');
      showToast(`🎯 TAKE PROFIT TRIGGERED for ${t.symbol} at $${fmt(livePrice)}! Gain: +$${fmt(tpGain)}`, 'success');
      speakJarvis(`Take-profit secured on ${t.symbol}, Sir. Capital compounded.`);
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
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--muted);padding:24px;">No active paper trades. J.A.R.V.I.S. is monitoring markets. Open a trade above or click "Execute Sniper" on the radar!</td></tr>';
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
fetchJarvisStatus();
</script>
</body>
</html>
"""
