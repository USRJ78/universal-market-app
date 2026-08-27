/* ==============================================================================
   CHRONOPULSE — TIME TRACKER FRONTEND APPLICATION ENGINE
   ============================================================================== */

const API_BASE = "http://" + window.location.host;

let timerInterval = null;
let activeTimerState = null;
let selectedCategory = "Coding & Dev";
let categoryChart = null;

// DOM Elements
const digitalClock = document.getElementById("digital-clock");
const activeStatus = document.getElementById("active-status");
const activityInput = document.getElementById("activity-name");
const notesInput = document.getElementById("task-notes");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const categoryPills = document.querySelectorAll(".pill");
const logTableBody = document.getElementById("log-table-body");
const searchInput = document.getElementById("search-log");

// Stats Elements
const statTotalTime = document.getElementById("stat-total-time");
const statTotalTasks = document.getElementById("stat-total-tasks");
const statTopCategory = document.getElementById("stat-top-category");

// Category Selection
categoryPills.forEach(pill => {
  pill.addEventListener("click", () => {
    categoryPills.forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    selectedCategory = pill.getAttribute("data-category");
  });
});

// Format Seconds to HH:MM:SS
function formatSeconds(sec) {
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const secs = Math.floor(sec % 60);
  return [hrs, mins, secs].map(v => v < 10 ? "0" + v : v).join(":");
}

function formatDurationReadable(sec) {
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins} min`;
}

// Fetch Initial Data
async function loadData() {
  try {
    const res = await fetch(`${API_BASE}/api/logs`);
    const data = await res.json();
    
    if (data.active_timer) {
      activeTimerState = data.active_timer;
      startClockInterval();
    } else {
      activeTimerState = None;
      stopClockInterval();
    }
    
    renderLogs(data.logs || []);
    renderAnalytics(data.logs || []);
  } catch (err) {
    console.error("API Fetch Error:", err);
  }
}

// Timer Controls
function startClockInterval() {
  if (timerInterval) clearInterval(timerInterval);
  activeStatus.textContent = "TRACKING LIVE";
  activeStatus.className = "status-indicator running";
  btnStart.disabled = true;
  btnStop.disabled = false;

  if (activeTimerState) {
    activityInput.value = activeTimerState.activity || "";
    notesInput.value = activeTimerState.notes || "";
  }

  timerInterval = setInterval(() => {
    if (!activeTimerState) return;
    const elapsed = Math.floor(Date.now() / 1000 - activeTimerState.start_time);
    digitalClock.textContent = formatSeconds(elapsed);
  }, 1000);
}

function stopClockInterval() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
  activeTimerState = null;
  digitalClock.textContent = "00:00:00";
  activeStatus.textContent = "IDLE";
  activeStatus.className = "status-indicator idle";
  btnStart.disabled = false;
  btnStop.disabled = true;
}

btnStart.addEventListener("click", async () => {
  const activity = activityInput.value.trim() || "Untitled Activity";
  const notes = notesInput.value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/timer/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activity, category: selectedCategory, notes })
    });
    const result = await res.json();
    activeTimerState = result.active_timer;
    startClockInterval();
  } catch (err) {
    alert("Failed to start timer");
  }
});

btnStop.addEventListener("click", async () => {
  const notes = notesInput.value.trim();
  try {
    const res = await fetch(`${API_BASE}/api/timer/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes })
    });
    stopClockInterval();
    activityInput.value = "";
    notesInput.value = "";
    loadData();
  } catch (err) {
    alert("Failed to stop timer");
  }
});

// Render Logs Table
function renderLogs(logs) {
  const query = searchInput.value.toLowerCase().trim();
  const filtered = logs.filter(l => 
    l.activity.toLowerCase().includes(query) || 
    l.category.toLowerCase().includes(query) || 
    (l.notes && l.notes.toLowerCase().includes(query))
  );

  if (filtered.length === 0) {
    logTableBody.innerHTML = `<tr><td colspan="6" class="empty-msg">No entries found matching search.</td></tr>`;
    return;
  }

  logTableBody.innerHTML = filtered.map(log => {
    const dateStr = new Date(log.start_time * 1000).toLocaleString();
    return `
      <tr>
        <td>${dateStr}</td>
        <td><span class="category-tag">${log.category}</span></td>
        <td><strong>${log.activity}</strong></td>
        <td><span class="duration-badge">${formatDurationReadable(log.duration_seconds)}</span></td>
        <td>${log.notes || '—'}</td>
        <td>
          <button class="delete-btn" onclick="deleteEntry(${log.id})">
            <i data-lucide="trash-2"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");

  if (window.lucide) lucide.createIcons();
}

async function deleteEntry(id) {
  if (!confirm("Are you sure you want to delete this log entry?")) return;
  try {
    await fetch(`${API_BASE}/api/logs/${id}`, { method: "DELETE" });
    loadData();
  } catch (err) {
    alert("Failed to delete entry");
  }
}

// Render Analytics
function renderAnalytics(logs) {
  let totalSec = 0;
  const catMap = {};

  logs.forEach(l => {
    totalSec += l.duration_seconds || 0;
    const cat = l.category || "General";
    catMap[cat] = (catMap[cat] || 0) + (l.duration_seconds || 0);
  });

  statTotalTime.textContent = formatDurationReadable(totalSec);
  statTotalTasks.textContent = logs.length;

  let topCat = "—";
  let maxDur = 0;
  for (const [c, d] of Object.entries(catMap)) {
    if (d > maxDur) {
      maxDur = d;
      topCat = c;
    }
  }
  statTopCategory.textContent = topCat;

  // Chart Rendering
  const labels = Object.keys(catMap);
  const chartData = Object.values(catMap).map(s => Math.round(s / 60)); // Minutes

  const ctx = document.getElementById("categoryChart").getContext("2d");

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels.length > 0 ? labels : ["No Data"],
      datasets: [{
        data: chartData.length > 0 ? chartData : [1],
        backgroundColor: [
          "#0284c7", "#10b981", "#8b5cf6", "#f59e0b", "#f43f5e", "#64748b"
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#94a3b8", font: { size: 11 } }
        }
      }
    }
  });
}

// Search Filter Listener
searchInput.addEventListener("input", () => {
  fetch(`${API_BASE}/api/logs`).then(r => r.json()).then(d => renderLogs(d.logs || []));
});

// Manual Entry Modal Logic
const modal = document.getElementById("manual-modal");
const btnManual = document.getElementById("btn-manual");
const modalClose = document.getElementById("modal-close");
const manualForm = document.getElementById("manual-form");

btnManual.addEventListener("click", () => modal.classList.add("active"));
modalClose.addEventListener("click", () => modal.classList.remove("active"));

manualForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const activity = document.getElementById("manual-activity").value;
  const category = document.getElementById("manual-category").value;
  const duration_minutes = parseInt(document.getElementById("manual-duration").value, 10);
  const notes = document.getElementById("manual-notes").value;

  try {
    await fetch(`${API_BASE}/api/logs/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activity, category, duration_minutes, notes })
    });
    modal.classList.remove("active");
    manualForm.reset();
    loadData();
  } catch (err) {
    alert("Failed to add manual entry");
  }
});

// Clear All Data
document.getElementById("btn-clear-all").addEventListener("click", async () => {
  if (!confirm("Are you sure you want to reset all tracked time logs?")) return;
  try {
    await fetch(`${API_BASE}/api/logs/clear`, { method: "POST" });
    stopClockInterval();
    loadData();
  } catch (err) {
    alert("Failed to clear data");
  }
});

// Initialize on Load
loadData();
