/* ==========================================================================
   SWARM ALPHA V6.0 — LIVE DASHBOARD LOGIC & CANVAS PAYOFF ENGINE
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initRadarList();
  initPayoffSimulator();
  initTradeLog();
});

// 1. Live Radar Matrix Mock Data (Reflecting Engine Output)
const radarData = [
  { asset: "BTC-USD", name: "Bitcoin Perpetual", type: "Crypto", score: 85, signal: "PARABOLIC MOMENTUM (1.5x Leverage)", status: "EXECUTE" },
  { asset: "ETH-USD", name: "Ethereum Perpetual", type: "Crypto", score: 80, signal: "VOL SQUEEZE (ATR Ratio 0.88)", status: "EXECUTE" },
  { asset: "SOL-USD", name: "Solana Perpetual", type: "Crypto", score: 75, signal: "EMA 20/50 ALIGNED", status: "EXECUTE" },
  { asset: "^NSEI", name: "Nifty 50 Index", type: "Equity", score: 85, signal: "ZERO DEBIT 1x2 RATIO SPREAD", status: "EXECUTE" },
  { asset: "^NSEBANK", name: "Bank Nifty Index", type: "Equity", score: 78, signal: "TRAPPED LIQUIDITY REVERSAL", status: "EXECUTE" },
  { asset: "RELIANCE.NS", name: "Reliance Industries", type: "Equity", score: 80, signal: "52W BREAKOUT RETEST", status: "EXECUTE" }
];

function initRadarList() {
  const container = document.getElementById("radarList");
  if (!container) return;

  container.innerHTML = radarData.map(item => `
    <div class="radar-item">
      <div class="asset-info">
        <div>
          <div class="asset-name">${item.asset}</div>
          <div class="asset-type">${item.name} • ${item.signal}</div>
        </div>
      </div>
      <div class="score-bar-box">
        <span class="score-num ${item.score >= 75 ? 'cyan' : 'gold'}">${item.score}%</span>
        <div class="score-progress">
          <div class="score-fill" style="width: ${item.score}%;"></div>
        </div>
      </div>
    </div>
  `).join('');
}

// 2. Interactive Canvas Payoff Simulator for 1x2 Ratio Call Spread
function initPayoffSimulator() {
  const spotSlider = document.getElementById("sliderSpot");
  const k1Slider = document.getElementById("sliderK1");
  const k2Slider = document.getElementById("sliderK2");

  if (!spotSlider || !k1Slider || !k2Slider) return;

  const update = () => {
    const spot = parseFloat(spotSlider.value);
    const k1 = parseFloat(k1Slider.value);
    const k2 = parseFloat(k2Slider.value);

    document.getElementById("lblSpot").innerText = spot.toLocaleString();
    document.getElementById("lblK1").innerText = k1.toLocaleString();
    document.getElementById("lblK2").innerText = k2.toLocaleString();

    drawPayoffCurve(spot, k1, k2);
  };

  spotSlider.addEventListener("input", update);
  k1Slider.addEventListener("input", update);
  k2Slider.addEventListener("input", update);

  update();
}

function drawPayoffCurve(spot, k1, k2) {
  const canvas = document.getElementById("payoffCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  // Background
  ctx.fillStyle = "#0d1322";
  ctx.fillRect(0, 0, width, height);

  // Price range: K1 * 0.90 to K2 * 1.10
  const minP = k1 * 0.90;
  const maxP = k2 * 1.12;

  const getX = (p) => ((p - minP) / (maxP - minP)) * width;
  
  // Payoff calculation: Buy 1x K1 Call, Sell 2x K2 Call
  const getPayoff = (p) => {
    const call1 = Math.max(p - k1, 0);
    const call2 = 2 * Math.max(p - k2, 0);
    return call1 - call2;
  };

  // Max payoff occurs at K2
  const maxPnl = getPayoff(k2);
  const minPnl = getPayoff(maxP);

  const getY = (pnl) => {
    const zeroY = height * 0.70;
    if (pnl >= 0) {
      return zeroY - (pnl / (maxPnl + 1e-9)) * (zeroY - 30);
    } else {
      return zeroY + (Math.abs(pnl) / (Math.abs(minPnl) + 1e-9)) * (height - zeroY - 20);
    }
  };

  const zeroY = getY(0);

  // Zero Line
  ctx.strokeStyle = "#30363d";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(0, zeroY);
  ctx.lineTo(width, zeroY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Plot Payoff Curve
  ctx.beginPath();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#00ffcc";

  let first = true;
  for (let xPx = 0; xPx <= width; xPx += 2) {
    const p = minP + (xPx / width) * (maxP - minP);
    const pnl = getPayoff(p);
    const yPx = getY(pnl);

    if (first) {
      ctx.moveTo(xPx, yPx);
      first = false;
    } else {
      ctx.lineTo(xPx, yPx);
    }
  }
  ctx.stroke();

  // Draw Strike Markers (K1, K2)
  const drawMarker = (p, label, color) => {
    const x = getX(p);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(x, 10);
    ctx.lineTo(x, height - 10);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = color;
    ctx.font = "11px JetBrains Mono";
    ctx.fillText(`${label}: $${p.toLocaleString()}`, x + 5, 25);
  };

  drawMarker(k1, "K1 (ATM)", "#e3b341");
  drawMarker(k2, "K2 (OTM)", "#39d353");

  // Current Spot Marker
  const spotX = getX(spot);
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(spotX, getY(getPayoff(spot)), 6, 0, 2 * Math.PI);
  ctx.fill();

  // Metrics update
  document.getElementById("valMaxPayoff").innerText = `+$${maxPnl.toLocaleString()} (+${((maxPnl/k1)*100).toFixed(1)}%)`;
  const upperBE = k2 + maxPnl;
  document.getElementById("valUpperBE").innerText = `$${upperBE.toLocaleString()}`;
}

// 3. Tab Switcher
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));

  event.target.classList.add("active");
  document.getElementById(tabId).classList.remove("hidden");
}

// 4. Executed Trade Log
function initTradeLog() {
  const table = document.getElementById("tradeLogTable");
  if (!table) return;

  const mockTrades = [
    { date: "2026-07-25", asset: "BTC-USD", type: "Crypto 1.5x", entry: "$64,200", exit: "$67,800", pnlPct: "+8.4%", pnlUsd: "+$1,008.00" },
    { date: "2026-07-21", asset: "^NSEI", type: "Equity 1x2 Spread", entry: "24,500", exit: "25,400", pnlPct: "+145.0%", pnlUsd: "+$1,160.00" },
    { date: "2026-07-15", asset: "ETH-USD", type: "Crypto 1.5x", entry: "$3,450", exit: "$3,710", pnlPct: "+11.3%", pnlUsd: "+$904.00" },
    { date: "2026-07-08", asset: "RELIANCE.NS", type: "Equity 1x2 Spread", entry: "3,100", exit: "3,240", pnlPct: "+118.0%", pnlUsd: "+$944.00" },
    { date: "2026-06-29", asset: "SOL-USD", type: "Crypto 1.5x", entry: "$138.00", exit: "$152.00", pnlPct: "+15.2%", pnlUsd: "+$1,216.00" }
  ];

  table.innerHTML = mockTrades.map(tr => `
    <tr>
      <td>${tr.date}</td>
      <td class="cyan">${tr.asset}</td>
      <td>${tr.type}</td>
      <td>${tr.entry}</td>
      <td>${tr.exit}</td>
      <td class="green">${tr.pnlPct}</td>
      <td class="green font-mono">${tr.pnlUsd}</td>
    </tr>
  `).join('');
}
