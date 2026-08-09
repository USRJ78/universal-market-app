// Ensure Three.js is loaded
if (typeof THREE === 'undefined') {
    console.error("Three.js not loaded!");
}

// --- 3D ENGINE SETUP ---
const canvas = document.getElementById('gameCanvas');
const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#0a0a1a'); // Dark night sky
scene.fog = new THREE.FogExp2('#0a0a1a', 0.005);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(100, 200, 50);
dirLight.castShadow = true;
dirLight.shadow.camera.top = 200;
dirLight.shadow.camera.bottom = -200;
dirLight.shadow.camera.left = -200;
dirLight.shadow.camera.right = 200;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
scene.add(dirLight);

// Ground
const groundGeo = new THREE.PlaneGeometry(1000, 1000);
const groundMat = new THREE.MeshStandardMaterial({ color: '#111111', roughness: 0.8 });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// --- PLAYER MANNEQUIN ---
const playerGroup = new THREE.Group();

// Body
const bodyGeo = new THREE.BoxGeometry(2, 4, 1);
const bodyMat = new THREE.MeshStandardMaterial({ color: '#00ff9d' });
const body = new THREE.Mesh(bodyGeo, bodyMat);
body.position.y = 2; // half height
body.castShadow = true;
playerGroup.add(body);

// Head
const headGeo = new THREE.BoxGeometry(1.5, 1.5, 1.5);
const headMat = new THREE.MeshStandardMaterial({ color: '#ffaaaa' });
const head = new THREE.Mesh(headGeo, headMat);
head.position.y = 4.75;
head.castShadow = true;
playerGroup.add(head);

scene.add(playerGroup);

// --- CITY MAP ---
const buildings = [];
const mapData = [
    { id: 'safehouse', name: 'Safehouse', x: 0, z: -20, w: 20, h: 10, d: 20, color: '#1c2333', interactText: 'Access Trading Terminal' },
    { id: 'AERO', name: 'AeroCorp Factory', x: 100, z: -100, w: 40, h: 50, d: 40, color: '#442222', interactText: 'Sabotage Factory' },
    { id: 'FLY', name: 'FlyHigh HQ', x: 100, z: 100, w: 30, h: 80, d: 30, color: '#222244', interactText: 'Sabotage Servers' },
    { id: 'SEC', name: 'SecureTech Hub', x: -100, z: -50, w: 25, h: 60, d: 25, color: '#224422', interactText: 'Deploy Malware' },
    { id: 'DVT', name: 'DataVault Center', x: -80, z: 80, w: 35, h: 40, d: 35, color: '#444422', interactText: 'Trigger Data Breach' }
];

const bMatTemplate = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0.2 });

mapData.forEach(b => {
    const geo = new THREE.BoxGeometry(b.w, b.h, b.d);
    const mat = bMatTemplate.clone();
    mat.color.set(b.color);
    const mesh = new THREE.Mesh(geo, mat);
    
    // Position so bottom is on ground
    mesh.position.set(b.x, b.h / 2, b.z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    
    mesh.userData = { id: b.id, name: b.name, interactText: b.interactText };
    scene.add(mesh);
    buildings.push(mesh);
});

// Position player in front of safehouse
playerGroup.position.set(0, 0, 10);

// --- INPUT & MOVEMENT ---
const keys = { w: false, a: false, s: false, d: false, e: false };
let isUIPen = false;

window.addEventListener('keydown', e => {
    const k = e.key.toLowerCase();
    if(k in keys) keys[k] = true;
    if(e.key === 'Escape') closeAllUI();
});

window.addEventListener('keyup', e => {
    const k = e.key.toLowerCase();
    if(k in keys) keys[k] = false;
    if(k === 'e' && !isUIPen) {
        checkInteractions();
    }
});

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

const moveSpeed = 0.5;
const rotSpeed = 0.05;

// --- STOCK ENGINE ---
const state = {
    day: 1, cash: 100000, portfolioValue: 0, activeTicker: 'AERO', historyLength: 60, positions: {}
};

const companies = {
    AERO: { name: 'AeroCorp', price: 150.00, vol: 0.02, drift: 0.0001, comp: 'FLY', history: [] },
    FLY: { name: 'FlyHigh', price: 85.00, vol: 0.025, drift: -0.0001, comp: 'AERO', history: [] },
    SEC: { name: 'SecureTech', price: 210.00, vol: 0.015, drift: 0.0005, comp: 'DVT', history: [] },
    DVT: { name: 'DataVault', price: 195.00, vol: 0.018, drift: -0.0002, comp: 'SEC', history: [] }
};

let chart;
let currentSabotageTarget = null;

function initMarket() {
    Object.keys(companies).forEach(ticker => {
        for(let i=0; i<state.historyLength; i++) companies[ticker].history.push(companies[ticker].price);
        state.positions[ticker] = { shares: 0, avgPrice: 0 };
    });
    
    document.getElementById('btn-buy').onclick = () => trade(state.activeTicker, getTradeAmount(), 'buy');
    document.getElementById('btn-sell').onclick = () => trade(state.activeTicker, getTradeAmount(), 'sell');
    document.getElementById('btn-short').onclick = () => trade(state.activeTicker, getTradeAmount(), 'short');
    
    initChart();
    setInterval(marketTick, 2000);
}

function getTradeAmount() { return parseInt(document.getElementById('trade-shares').value) || 0; }

function marketTick() {
    state.day++;
    let totalPort = 0;

    Object.entries(companies).forEach(([ticker, c]) => {
        const shock = (Math.random() - 0.5) * 2;
        const ret = c.drift + c.vol * shock;
        
        c.price = Math.max(0.01, c.price * (1 + ret));
        c.history.push(c.price);
        if(c.history.length > state.historyLength) c.history.shift();
        
        if(c.drift > 0.001) c.drift *= 0.8;
        if(c.drift < -0.001) c.drift *= 0.8;

        const pos = state.positions[ticker];
        if(pos.shares > 0) totalPort += pos.shares * c.price;
        else if (pos.shares < 0) totalPort += (pos.avgPrice - c.price) * Math.abs(pos.shares);
    });

    state.portfolioValue = state.cash + totalPort;
    
    document.getElementById('hud-cash').innerText = `$${state.cash.toLocaleString(undefined, {minimumFractionDigits:2})}`;
    document.getElementById('hud-portfolio').innerText = `$${state.portfolioValue.toLocaleString(undefined, {minimumFractionDigits:2})}`;
    
    if(isUIPen) {
        updateChart();
        renderWatchlist();
        renderPositions();
    }
}

// --- TRADING UI ---
function openTerminal() {
    isUIPen = true;
    document.getElementById('trading-modal').classList.remove('hidden');
    renderWatchlist();
    setActiveTicker('AERO');
    renderPositions();
}

function closeTerminal() {
    isUIPen = false;
    document.getElementById('trading-modal').classList.add('hidden');
}

function closeAllUI() {
    closeTerminal();
    closeSabotage();
}

function renderWatchlist() {
    const wl = document.getElementById('watchlist');
    wl.innerHTML = '';
    Object.entries(companies).forEach(([ticker, data]) => {
        const div = document.createElement('div');
        div.className = `stock-item ${ticker === state.activeTicker ? 'active' : ''}`;
        div.onclick = () => setActiveTicker(ticker);
        const change = ((data.price - data.history[data.history.length-2]) / data.history[data.history.length-2]) * 100 || 0;
        div.innerHTML = `
            <div><div class="stock-name">${data.name}</div><div class="stock-ticker">${ticker}</div></div>
            <div style="text-align:right">
                <div class="stock-price">$${data.price.toFixed(2)}</div>
                <div class="stock-change ${change>=0?'up':'down'}">${change>0?'+':''}${change.toFixed(2)}%</div>
            </div>`;
        wl.appendChild(div);
    });
}

function setActiveTicker(ticker) {
    state.activeTicker = ticker;
    document.getElementById('active-ticker').innerText = `${companies[ticker].name} (${ticker})`;
    updateChart();
    renderWatchlist();
}

function initChart() {
    const ctx = document.getElementById('marketChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: state.historyLength}, (_, i) => i),
            datasets: [{ label: 'Price', data: companies['AERO'].history, borderColor: '#00d2ff', borderWidth: 2, pointRadius: 0, fill: false, tension: 0.1 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: true, position: 'right', ticks: { color: '#8b9bb4' } } }, animation: { duration: 0 } }
    });
}

function updateChart() {
    chart.data.datasets[0].data = companies[state.activeTicker].history;
    chart.update();
    document.getElementById('active-price').innerText = `$${companies[state.activeTicker].price.toFixed(2)}`;
}

function trade(ticker, shares, action) {
    if(shares <= 0) return;
    const price = companies[ticker].price;
    const pos = state.positions[ticker];
    const cost = price * shares;

    if(action === 'buy') {
        if(state.cash >= cost) {
            state.cash -= cost;
            pos.avgPrice = ((pos.shares * pos.avgPrice) + cost) / (pos.shares + shares);
            pos.shares += shares;
            logNews(`Bought ${shares} ${ticker}`);
        }
    } else if(action === 'sell' && pos.shares >= shares) {
        state.cash += cost;
        pos.shares -= shares;
        if(pos.shares === 0) pos.avgPrice = 0;
        logNews(`Sold ${shares} ${ticker}`);
    } else if(action === 'short' && state.cash >= cost * 0.5) {
        state.cash += cost;
        pos.avgPrice = ((Math.abs(pos.shares) * pos.avgPrice) + cost) / (Math.abs(pos.shares) + shares);
        pos.shares -= shares;
        logNews(`Shorted ${shares} ${ticker}`);
    }
    renderPositions();
}

function renderPositions() {
    const list = document.getElementById('positions-list');
    list.innerHTML = '';
    Object.entries(state.positions).forEach(([ticker, pos]) => {
        if(pos.shares !== 0) {
            const price = companies[ticker].price;
            const pnl = pos.shares > 0 ? (price - pos.avgPrice) * pos.shares : (pos.avgPrice - price) * Math.abs(pos.shares);
            const div = document.createElement('div');
            div.className = `position-item ${pos.shares < 0 ? 'short' : ''}`;
            div.innerHTML = `
                <div><strong>${ticker}</strong> ${pos.shares > 0 ? 'LONG' : 'SHORT'}</div>
                <div>${Math.abs(pos.shares)} shs</div>
                <div>@ $${pos.avgPrice.toFixed(2)}</div>
                <div class="pos-val ${pnl >= 0 ? 'up' : 'down'}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(0)}</div>`;
            list.appendChild(div);
        }
    });
}

// --- SABOTAGE ---
function openSabotage(targetId) {
    isUIPen = true;
    currentSabotageTarget = targetId;
    const c = companies[targetId];
    document.getElementById('sabotage-modal').classList.remove('hidden');
    document.getElementById('sabotage-title').innerText = `SABOTAGE ${c.name}?`;
}

function closeSabotage() {
    isUIPen = false;
    currentSabotageTarget = null;
    document.getElementById('sabotage-modal').classList.add('hidden');
}

function executeSabotage() {
    if(!currentSabotageTarget) return;
    const target = companies[currentSabotageTarget];
    const comp = companies[target.comp];
    
    target.drift = -0.4;
    comp.drift = 0.3;
    
    logNews(`Massive explosion reported at ${target.name}!`);
    closeSabotage();
}

function logNews(msg) {
    document.getElementById('news-scroll').innerText = msg;
}

// --- GAME LOOP ---
let nearestBuilding = null;

function checkProximity() {
    nearestBuilding = null;
    let minDist = 30; // Interaction radius
    
    buildings.forEach(b => {
        // Simple distance to center of building mesh
        const dist = playerGroup.position.distanceTo(b.position);
        // Adjust for building size
        const effectiveDist = dist - Math.max(b.geometry.parameters.width, b.geometry.parameters.depth)/2;
        
        if(effectiveDist < minDist) {
            minDist = effectiveDist;
            nearestBuilding = b;
        }
    });
    
    const prompt = document.getElementById('interaction-prompt');
    if(nearestBuilding && !isUIPen) {
        prompt.innerText = `[E] ${nearestBuilding.userData.interactText}`;
        prompt.classList.remove('hidden');
    } else {
        prompt.classList.add('hidden');
    }
}

function checkInteractions() {
    if(!nearestBuilding) return;
    if(nearestBuilding.userData.id === 'safehouse') {
        openTerminal();
    } else {
        openSabotage(nearestBuilding.userData.id);
    }
}

function animate() {
    requestAnimationFrame(animate);

    if(!isUIPen) {
        // Player Rotation
        if (keys.a) playerGroup.rotation.y += rotSpeed;
        if (keys.d) playerGroup.rotation.y -= rotSpeed;
        
        // Player Movement (Forward/Backward relative to facing)
        if (keys.w) playerGroup.translateZ(-moveSpeed);
        if (keys.s) playerGroup.translateZ(moveSpeed);

        // Simple world bounds
        if(playerGroup.position.x > 500) playerGroup.position.x = 500;
        if(playerGroup.position.x < -500) playerGroup.position.x = -500;
        if(playerGroup.position.z > 500) playerGroup.position.z = 500;
        if(playerGroup.position.z < -500) playerGroup.position.z = -500;
    }

    // Third Person Camera follow
    // Calculate offset based on player rotation
    const idealOffset = new THREE.Vector3(0, 15, 30);
    idealOffset.applyQuaternion(playerGroup.quaternion);
    idealOffset.add(playerGroup.position);
    
    // Smooth camera movement (Lerp)
    camera.position.lerp(idealOffset, 0.1);
    
    // Look at slightly above the player
    const lookAtPos = playerGroup.position.clone();
    lookAtPos.y += 5;
    camera.lookAt(lookAtPos);

    checkProximity();

    renderer.render(scene, camera);
}

initMarket();
animate();
