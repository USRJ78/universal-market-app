let activeLegs = [];
let payoffChart = null;
let equityChart = null;

const dropZone = document.getElementById('dropZone');
const legList = document.getElementById('legList');
const dropHint = document.querySelector('.drop-hint');

const modal = document.getElementById('tweakModal');
const modalSave = document.getElementById('modalSave');
let tempLeg = null;

// Setup Draggable Items
document.querySelectorAll('.drag-item').forEach(item => {
    item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', JSON.stringify({
            type: item.dataset.type,
            action: item.dataset.action
        }));
    });
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    
    // Open modal to configure strike/qty
    tempLeg = {
        id: Date.now(),
        type: data.type,
        action: data.action,
        strike: 100,
        qty: 1.0,
        dte: 90
    };
    
    if (data.type === 'future') {
        // Futures don't need strike or DTE config
        activeLegs.push(tempLeg);
        renderLegs();
        updatePayoffGraph();
    } else {
        document.getElementById('modalStrike').value = 100;
        document.getElementById('modalQty').value = 1.0;
        document.getElementById('modalDte').value = 90;
        modal.classList.remove('hidden');
    }
});

modalSave.addEventListener('click', () => {
    tempLeg.strike = parseFloat(document.getElementById('modalStrike').value);
    tempLeg.qty = parseFloat(document.getElementById('modalQty').value);
    tempLeg.dte = parseInt(document.getElementById('modalDte').value);
    activeLegs.push(tempLeg);
    modal.classList.add('hidden');
    renderLegs();
    updatePayoffGraph();
});

function removeLeg(id) {
    activeLegs = activeLegs.filter(l => l.id !== id);
    renderLegs();
    updatePayoffGraph();
}

function renderLegs() {
    legList.innerHTML = '';
    if(activeLegs.length > 0) dropHint.style.display = 'none';
    else dropHint.style.display = 'block';
    
    activeLegs.forEach(leg => {
        const li = document.createElement('li');
        const color = leg.action === 'buy' ? 'var(--success)' : 'var(--danger)';
        const desc = leg.type === 'future' 
            ? `<span style="color:${color}">${leg.action.toUpperCase()}</span> ${leg.qty}x FUTURE` 
            : `<span style="color:${color}">${leg.action.toUpperCase()}</span> ${leg.qty}x ${leg.type.toUpperCase()} @ ${leg.strike}%`;
            
        li.innerHTML = `<span>${desc}</span><button class="btn-remove" onclick="removeLeg(${leg.id})">X</button>`;
        legList.appendChild(li);
    });
}

function updatePayoffGraph() {
    if(activeLegs.length === 0) {
        if(payoffChart) payoffChart.destroy();
        return;
    }
    
    fetch('/api/payoff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ legs: activeLegs })
    }).then(r => r.json()).then(data => {
        drawPayoffChart(data.x, data.y);
    });
}

function drawPayoffChart(labels, dataPoints) {
    const ctx = document.getElementById('payoffChart').getContext('2d');
    if (payoffChart) payoffChart.destroy();
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 240, 255, 0.5)');
    gradient.addColorStop(1, 'rgba(0, 240, 255, 0.0)');
    
    const pointColors = dataPoints.map(y => y >= 0 ? '#2ed573' : '#ff4757');
    
    payoffChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Payoff at Expiry',
                data: dataPoints,
                borderColor: '#00f0ff',
                backgroundColor: gradient,
                borderWidth: 2,
                pointBackgroundColor: pointColors,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)', zeroLineColor: '#fff' } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

document.getElementById('simulateBtn').addEventListener('click', () => {
    if(activeLegs.length === 0) return;
    
    const payload = {
        legs: activeLegs,
        asset: document.getElementById('assetSelect').value,
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        capital: 100000
    };
    
    document.getElementById('simulateBtn').innerText = "Simulating... Fetching yfinance data...";
    
    fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
        document.getElementById('simulateBtn').innerText = "🚀 Run Historical Backtest";
        if(data.error) {
            alert(data.error);
            return;
        }
        
        document.getElementById('simulationResults').classList.remove('hidden');
        document.getElementById('resReturn').innerText = data.metrics.return + "%";
        document.getElementById('resDrawdown').innerText = data.metrics.drawdown + "%";
        document.getElementById('resSharpe').innerText = data.metrics.sharpe;
        
        drawEquityChart(data.dates, data.equity);
    });
});

function drawEquityChart(labels, dataPoints) {
    const ctx = document.getElementById('equityChart').getContext('2d');
    if (equityChart) equityChart.destroy();
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Portfolio Value',
                data: dataPoints,
                borderColor: '#9333ea',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { ticks: { maxTicksLimit: 10, color: '#94a3b8' }, grid: { display: false } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: { legend: { display: false } }
        }
    });
}
