// state management
const state = {
    sessionsCompleted: 0,
    failures: 0,
    nLevel: 1,
    nbackTrialsCompleted: 0,
    nbackScore: 0,
};

// Navigation
const navLinks = document.querySelectorAll('.nav-links li');
const views = document.querySelectorAll('.view');

navLinks.forEach(link => {
    link.addEventListener('click', () => {
        // Update active class
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        // Show view
        const targetId = `view-${link.dataset.target}`;
        views.forEach(v => {
            v.classList.remove('active-view');
            if(v.id === targetId) v.classList.add('active-view');
        });
    });
});

// Update Dashboard UI
function updateDashboard() {
    document.getElementById('dash-sessions').innerText = state.sessionsCompleted;
    document.getElementById('dash-failures').innerText = state.failures;
    document.getElementById('dash-current-n').innerText = state.nLevel;
    
    document.getElementById('nav-focus-score').innerText = state.sessionsCompleted - state.failures;
    document.getElementById('nav-n-level').innerText = state.nLevel;
    document.getElementById('nback-current-n').innerText = state.nLevel;
    
    if (state.nbackTrialsCompleted > 0) {
        const accuracy = Math.round((state.nbackScore / state.nbackTrialsCompleted) * 100);
        document.getElementById('dash-accuracy').innerText = `${accuracy}%`;
    }
}

// --- ISOLATION CHAMBER (FOCUS PROTOCOL) ---
let focusTimer = null;
let timeLeft = 25 * 60; // 25 mins
let isFocusing = false;

const timerDisplay = document.getElementById('timer-text');
const btnTimerStart = document.getElementById('btn-timer-start');
const btnTimerStop = document.getElementById('btn-timer-stop');
const timerStatusMsg = document.getElementById('timer-status-msg');

function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

function stopFocus(failed = false) {
    clearInterval(focusTimer);
    isFocusing = false;
    btnTimerStart.classList.remove('hidden');
    btnTimerStop.classList.add('hidden');
    timeLeft = 25 * 60;
    timerDisplay.innerText = formatTime(timeLeft);
    
    if (failed) {
        state.failures++;
        timerStatusMsg.innerHTML = '<span class="error-text">BREACH DETECTED. Session Failed.</span>';
        timerDisplay.style.color = 'var(--danger-color)';
        setTimeout(() => timerDisplay.style.color = '', 3000);
    } else {
        timerStatusMsg.innerText = 'System Idle.';
    }
    updateDashboard();
}

btnTimerStart.addEventListener('click', () => {
    isFocusing = true;
    btnTimerStart.classList.add('hidden');
    btnTimerStop.classList.remove('hidden');
    timerStatusMsg.innerHTML = '<span style="color: var(--primary-color)">DEEP WORK ACTIVE. Do not switch tabs.</span>';
    
    focusTimer = setInterval(() => {
        timeLeft--;
        timerDisplay.innerText = formatTime(timeLeft);
        if(timeLeft <= 0) {
            state.sessionsCompleted++;
            timerStatusMsg.innerHTML = '<span style="color: var(--success-color)">SESSION COMPLETE. Great focus.</span>';
            stopFocus(false);
        }
    }, 1000);
});

btnTimerStop.addEventListener('click', () => {
    stopFocus(true); // manually aborting counts as failure
});

// The core mechanic: Tab switching fails the timer
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isFocusing) {
        stopFocus(true);
        alert("CRITICAL ERROR: You broke focus. The Isolation Chamber has logged a failure.");
    }
});


// --- N-BACK ENGINE ---
const nbackGrid = document.getElementById('nback-grid');
const cells = document.querySelectorAll('.grid-cell');
const btnNbackStart = document.getElementById('btn-nback-start');
const btnNbackMatch = document.getElementById('btn-nback-match');
const nbackTrialsEl = document.getElementById('nback-trials');
const nbackScoreEl = document.getElementById('nback-score');

let nbackSequence = [];
let currentTrial = 0;
let maxTrials = 20;
let nbackTimer = null;
let userMatchedCurrent = false;
let isNbackRunning = false;

function flashCell(index) {
    cells.forEach(c => c.classList.remove('active-cell'));
    if (index !== null) {
        cells[index].classList.add('active-cell');
        setTimeout(() => {
            cells[index].classList.remove('active-cell');
        }, 1200); // stay lit for 1.2s
    }
}

function nextNbackTrial() {
    if (currentTrial >= maxTrials) {
        endNbackSession();
        return;
    }
    
    userMatchedCurrent = false;
    btnNbackMatch.disabled = false;
    
    // Generate next position (20% chance to force a match, otherwise random)
    let nextPos;
    if (currentTrial >= state.nLevel && Math.random() < 0.3) {
        nextPos = nbackSequence[currentTrial - state.nLevel];
    } else {
        nextPos = Math.floor(Math.random() * 9);
    }
    
    nbackSequence.push(nextPos);
    flashCell(nextPos);
    currentTrial++;
    
    nbackTrialsEl.innerText = `${currentTrial}/${maxTrials}`;
    
    // Check if user missed a match after the interval
    nbackTimer = setTimeout(() => {
        btnNbackMatch.disabled = true;
        
        // Did they miss a valid match?
        if (currentTrial > state.nLevel) {
            const isMatch = nbackSequence[currentTrial - 1] === nbackSequence[currentTrial - 1 - state.nLevel];
            if (isMatch && !userMatchedCurrent) {
                // missed it!
            }
        }
        
        nextNbackTrial();
    }, 3000); // 3 seconds between trials
}

function endNbackSession() {
    clearTimeout(nbackTimer);
    isNbackRunning = false;
    btnNbackStart.classList.remove('hidden');
    btnNbackMatch.disabled = true;
    cells.forEach(c => c.classList.remove('active-cell'));
    
    // Level up logic
    const accuracy = state.nbackScore / maxTrials;
    if (accuracy > 0.8) {
        state.nLevel++;
        alert(`Performance exceptional. Upgrading to N-Level: ${state.nLevel}`);
    }
    updateDashboard();
}

btnNbackStart.addEventListener('click', () => {
    isNbackRunning = true;
    nbackSequence = [];
    currentTrial = 0;
    state.nbackTrialsCompleted = 0;
    state.nbackScore = 0;
    
    nbackScoreEl.innerText = '0';
    nbackTrialsEl.innerText = `0/${maxTrials}`;
    
    btnNbackStart.classList.add('hidden');
    
    setTimeout(nextNbackTrial, 1000);
});

btnNbackMatch.addEventListener('click', () => {
    if (!isNbackRunning || userMatchedCurrent) return;
    userMatchedCurrent = true;
    btnNbackMatch.disabled = true; // prevent double clicks
    
    if (currentTrial > state.nLevel) {
        const isMatch = nbackSequence[currentTrial - 1] === nbackSequence[currentTrial - 1 - state.nLevel];
        state.nbackTrialsCompleted++;
        
        if (isMatch) {
            state.nbackScore++;
            nbackScoreEl.innerText = state.nbackScore;
            // visual feedback
            cells[nbackSequence[currentTrial-1]].style.boxShadow = '0 0 30px var(--success-color)';
        } else {
            // wrong match
            cells[nbackSequence[currentTrial-1]].style.boxShadow = '0 0 30px var(--danger-color)';
        }
        
        setTimeout(() => {
            cells.forEach(c => c.style.boxShadow = '');
        }, 500);
    }
});


// --- MENTAL MODELS ---
const models = [
    {
        scenario: "Your father's business has a logistics bottleneck that delays orders by 3 days. Everyone assumes it's the shipping company's fault.",
        options: [
            { text: "Occam's Razor (The simplest explanation is usually right)", correct: false },
            { text: "Inversion (Assume it's your own warehouse's fault and prove it)", correct: true },
            { text: "Sunk Cost Fallacy (Keep doing the same thing)", correct: false }
        ],
        feedback: "Correct. By using Inversion, you flip the problem backwards. Instead of proving the shipping company is slow, try to prove your own internal packaging process is broken. You often find the true bottleneck internally."
    },
    {
        scenario: "You are building a new marketing plan. You look at three competitors who succeeded and try to copy their exact strategy.",
        options: [
            { text: "Survivorship Bias (You are ignoring the 97 companies who used the same strategy and failed)", correct: true },
            { text: "First Principles (Breaking it down to atoms)", correct: false },
            { text: "Pareto Principle (80/20 rule)", correct: false }
        ],
        feedback: "Correct. Survivorship Bias is dangerous. You only see the winners. To survive, you must study the failures."
    }
];

let currentDrill = 0;
const scenarioEl = document.getElementById('model-scenario');
const optionsEl = document.getElementById('model-options');
const feedbackEl = document.getElementById('model-feedback');
const btnModelNext = document.getElementById('btn-model-next');

function loadDrill() {
    const drill = models[currentDrill];
    scenarioEl.innerText = drill.scenario;
    optionsEl.innerHTML = '';
    feedbackEl.innerText = '';
    btnModelNext.classList.add('hidden');
    
    drill.options.forEach((opt, idx) => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.innerText = opt.text;
        btn.onclick = () => handleModelAnswer(btn, opt.correct, drill.feedback);
        optionsEl.appendChild(btn);
    });
}

function handleModelAnswer(btn, isCorrect, feedbackText) {
    // Disable all options
    document.querySelectorAll('.option-btn').forEach(b => b.style.pointerEvents = 'none');
    
    if (isCorrect) {
        btn.classList.add('correct');
        feedbackEl.innerHTML = `<span style="color: var(--success-color)">Logic Optimal.</span> ${feedbackText}`;
    } else {
        btn.classList.add('wrong');
        feedbackEl.innerHTML = `<span style="color: var(--danger-color)">Logic Flawed.</span> Review your mental models.`;
    }
    
    btnModelNext.classList.remove('hidden');
}

btnModelNext.addEventListener('click', () => {
    currentDrill++;
    if (currentDrill >= models.length) {
        currentDrill = 0; // loop back for demo
    }
    loadDrill();
});

// Initialize first view
updateDashboard();
loadDrill();
