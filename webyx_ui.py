"""
Webyx UI - Web Accessibility Auditing RL Environment
FastAPI + HTML/JS (replacement for Gradio/Streamlit)

Run:
    pip install fastapi uvicorn requests
    python webyx_ui.py

Then open: http://localhost:7860
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Webyx — Accessibility Auditor</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0d0f12;
    --bg2: #13161b;
    --bg3: #1a1e26;
    --border: #2a2f3a;
    --accent: #00e5a0;
    --accent2: #0af;
    --warn: #ffb300;
    --danger: #ff4f4f;
    --text: #e8eaf0;
    --muted: #7a8394;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'IBM Plex Sans', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    font-size: 14px;
  }

  /* TOP BAR */
  #topbar {
    display: flex;
    align-items: center;
    gap: 0;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 52px;
  }
  #topbar .logo {
    font-family: var(--mono);
    font-weight: 600;
    font-size: 18px;
    color: var(--accent);
    letter-spacing: -0.5px;
    margin-right: 32px;
    flex-shrink: 0;
  }
  .stat-pill {
    display: flex;
    flex-direction: column;
    padding: 0 20px;
    border-left: 1px solid var(--border);
    min-width: 110px;
  }
  .stat-pill .s-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
    font-family: var(--mono);
  }
  .stat-pill .s-val {
    font-family: var(--mono);
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
  }
  #done-banner {
    display: none;
    margin-left: auto;
    background: var(--accent);
    color: #000;
    font-family: var(--mono);
    font-weight: 600;
    font-size: 13px;
    padding: 6px 16px;
    border-radius: 4px;
    letter-spacing: 0.5px;
  }

  /* MAIN LAYOUT */
  #main {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 1px;
    background: var(--border);
    height: calc(100vh - 52px - 220px);
    min-height: 380px;
  }
  .panel {
    background: var(--bg2);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .panel-header {
    font-family: var(--mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--muted);
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg3);
    flex-shrink: 0;
  }
  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 0;
  }
  .panel-body::-webkit-scrollbar { width: 4px; }
  .panel-body::-webkit-scrollbar-track { background: transparent; }
  .panel-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  /* HTML VIEWER */
  #html-code {
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.7;
    padding: 16px;
    white-space: pre-wrap;
    word-break: break-all;
    color: #a8d8a8;
    background: transparent;
    min-height: 100%;
  }

  /* VIOLATIONS TABLE */
  #violations-section {
    border-top: 1px solid var(--border);
    flex-shrink: 0;
    max-height: 200px;
    overflow-y: auto;
  }
  #violations-section::-webkit-scrollbar { width: 4px; }
  #violations-section::-webkit-scrollbar-thumb { background: var(--border); }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    font-family: var(--mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
    padding: 8px 12px;
    text-align: left;
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
  }
  tbody tr { border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.1s; }
  tbody tr:hover { background: rgba(255,255,255,0.04); }
  tbody td { padding: 8px 12px; font-size: 13px; }
  .badge {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    display: inline-block;
  }
  .badge-A    { background: rgba(255,79,79,0.18); color: #ff7070; border: 1px solid rgba(255,79,79,0.3); }
  .badge-AA   { background: rgba(255,179,0,0.18); color: #ffb300; border: 1px solid rgba(255,179,0,0.3); }
  .badge-AAA  { background: rgba(255,220,80,0.15); color: #ffe566; border: 1px solid rgba(255,220,0,0.25); }
  tr.level-A  { background: rgba(255,79,79,0.05); }
  tr.level-AA { background: rgba(255,179,0,0.05); }
  tr.level-AAA{ background: rgba(255,220,80,0.04); }

  /* RIGHT PANEL — CONTROLS */
  .ctrl-group { padding: 14px 16px; border-bottom: 1px solid var(--border); }
  .ctrl-label {
    font-family: var(--mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
    margin-bottom: 6px;
    display: block;
  }
  select, input, textarea {
    width: 100%;
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--mono);
    font-size: 13px;
    padding: 8px 10px;
    border-radius: 4px;
    outline: none;
    resize: none;
    transition: border-color 0.15s;
  }
  select:focus, input:focus, textarea:focus {
    border-color: var(--accent);
  }
  select option { background: var(--bg2); }
  .btn-row { display: flex; gap: 8px; padding: 14px 16px; }
  .btn {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
    letter-spacing: 0.5px;
  }
  .btn:active { transform: scale(0.97); }
  .btn-exec { background: var(--accent); color: #000; }
  .btn-exec:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-reset { background: var(--bg3); color: var(--text); border: 1px solid var(--border); }
  .btn-reset:hover { border-color: var(--muted); }

  .rem-counts {
    display: flex;
    gap: 6px;
    padding: 0 16px 12px;
  }
  .rem-pill {
    flex: 1;
    text-align: center;
    padding: 6px 4px;
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 11px;
  }
  .rem-A   { background: rgba(255,79,79,0.12); color: #ff7070; border: 1px solid rgba(255,79,79,0.2); }
  .rem-AA  { background: rgba(255,179,0,0.12); color: #ffb300; border: 1px solid rgba(255,179,0,0.2); }
  .rem-AAA { background: rgba(255,220,80,0.1); color: #ffe566; border: 1px solid rgba(255,220,0,0.2); }

  #error-msg {
    display: none;
    margin: 0 16px 10px;
    padding: 8px 12px;
    background: rgba(255,79,79,0.1);
    border: 1px solid rgba(255,79,79,0.3);
    border-radius: 4px;
    color: #ff7070;
    font-size: 12px;
    font-family: var(--mono);
  }

  /* BOTTOM SECTION */
  #bottom {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1px;
    background: var(--border);
    height: 220px;
    border-top: 1px solid var(--border);
  }
  #history-panel { background: var(--bg2); display: flex; flex-direction: column; overflow: hidden; }
  #chart-panel   { background: var(--bg2); display: flex; flex-direction: column; }
  .bottom-header {
    font-family: var(--mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--muted);
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg3);
    flex-shrink: 0;
  }
  #history-table-wrap { flex: 1; overflow-y: auto; }
  #history-table-wrap::-webkit-scrollbar { width: 4px; }
  #history-table-wrap::-webkit-scrollbar-thumb { background: var(--border); }
  #history-table thead th { font-size: 9px; padding: 6px 10px; }
  #history-table tbody td { padding: 5px 10px; font-size: 12px; }
  #chart-wrap { flex: 1; padding: 10px 14px; position: relative; }
</style>
</head>
<body>

<!-- TOP BAR -->
<div id="topbar">
  <span class="logo">⬡ Webyx</span>
  <div class="stat-pill">
    <span class="s-label">Task</span>
    <span class="s-val" id="s-task">—</span>
  </div>
  <div class="stat-pill">
    <span class="s-label">Progress</span>
    <span class="s-val" id="s-step">—</span>
  </div>
  <div class="stat-pill">
    <span class="s-label">Episode score</span>
    <span class="s-val" id="s-score">—</span>
  </div>
  <div class="stat-pill">
    <span class="s-label">Cumulative reward</span>
    <span class="s-val" id="s-cumrew">—</span>
  </div>
  <div id="done-banner">✓ EPISODE COMPLETE</div>
</div>

<!-- MAIN -->
<div id="main">

  <!-- LEFT: HTML + violations -->
  <div class="panel" style="display:flex;flex-direction:column;">
    <div class="panel-header">HTML snippet</div>
    <div class="panel-body" style="flex:1;overflow-y:auto;">
      <pre id="html-code">Hit Reset to start an episode.</pre>
    </div>
    <div id="violations-section">
      <div class="panel-header" style="position:sticky;top:0;z-index:1;">Violations</div>
      <table id="violations-table">
        <thead><tr><th>Level</th><th>Selector</th><th>Description</th></tr></thead>
        <tbody id="violations-body"></tbody>
      </table>
    </div>
  </div>

  <!-- RIGHT: Controls -->
  <div class="panel">
    <div class="panel-header">Actions</div>
    <div class="panel-body">

      <div class="ctrl-group">
        <label class="ctrl-label">Action type</label>
        <select id="action-type">
          <option value="detect">detect</option>
          <option value="fix">fix</option>
          <option value="skip">skip</option>
        </select>
      </div>

      <div class="ctrl-group">
        <label class="ctrl-label">Target (CSS selector) <span style="color:var(--accent);font-size:9px;">— click a violation to fill</span></label>
        <input id="target" type="text" placeholder=".btn, #hero img, …"/>
      </div>

      <div class="ctrl-group">
        <label class="ctrl-label">Proposed fix</label>
        <textarea id="proposed-fix" rows="3" placeholder='alt="descriptive text", role="button", …'></textarea>
      </div>

      <div id="error-msg"></div>

      <div class="btn-row">
        <button class="btn btn-exec" id="exec-btn" onclick="executeStep()" disabled>Execute</button>
        <button class="btn btn-reset" onclick="resetEnv()">Reset</button>
      </div>

      <div class="rem-counts">
        <div class="rem-pill rem-A">
          <div style="font-size:9px;margin-bottom:2px;">A</div>
          <div id="rem-A">—</div>
        </div>
        <div class="rem-pill rem-AA">
          <div style="font-size:9px;margin-bottom:2px;">AA</div>
          <div id="rem-AA">—</div>
        </div>
        <div class="rem-pill rem-AAA">
          <div style="font-size:9px;margin-bottom:2px;">AAA</div>
          <div id="rem-AAA">—</div>
        </div>
      </div>

    </div>
  </div>
</div>

<!-- BOTTOM -->
<div id="bottom">
  <div id="history-panel">
    <div class="bottom-header">Step history</div>
    <div id="history-table-wrap">
      <table id="history-table" style="width:100%;border-collapse:collapse;">
        <thead>
          <tr>
            <th>Step</th><th>Action</th><th>Target</th><th>Fix</th><th>Reward</th><th>Event</th>
          </tr>
        </thead>
        <tbody id="history-body"></tbody>
      </table>
    </div>
  </div>
  <div id="chart-panel">
    <div class="bottom-header">Reward per step</div>
    <div id="chart-wrap">
      <canvas id="reward-chart"></canvas>
    </div>
  </div>
</div>

<script>
const BACKEND = "http://localhost:8000";

let rewardChart = null;
let chartLabels = [];
let chartData   = [];

function initChart() {
  const ctx = document.getElementById("reward-chart").getContext("2d");
  if (rewardChart) rewardChart.destroy();
  chartLabels = [];
  chartData   = [];
  rewardChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: chartLabels,
      datasets: [{
        label: "Reward",
        data: chartData,
        borderColor: "#00e5a0",
        backgroundColor: "rgba(0,229,160,0.08)",
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: "#00e5a0",
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1a1e26",
          borderColor: "#2a2f3a",
          borderWidth: 1,
          titleColor: "#7a8394",
          bodyColor: "#e8eaf0",
          titleFont: { family: "'IBM Plex Mono'" },
          bodyFont:  { family: "'IBM Plex Mono'" },
        }
      },
      scales: {
        x: {
          ticks: { color: "#7a8394", font: { family: "'IBM Plex Mono'", size: 10 } },
          grid:  { color: "rgba(255,255,255,0.04)" }
        },
        y: {
          ticks: { color: "#7a8394", font: { family: "'IBM Plex Mono'", size: 10 } },
          grid:  { color: "rgba(255,255,255,0.04)" }
        }
      }
    }
  });
}

function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.style.display = msg ? "block" : "none";
}

function updateUI(obs, reward) {
  // top bar
  document.getElementById("s-task").textContent  = obs.task_id || "—";
  document.getElementById("s-step").textContent  = obs.step_number + "/" + obs.max_steps;
  document.getElementById("s-score").textContent = obs.metadata?.episode_score?.toFixed(3) ?? "—";
  document.getElementById("s-cumrew").textContent= obs.metadata?.cumulative_reward?.toFixed(3) ?? "—";

  // html snippet
  document.getElementById("html-code").textContent = obs.html_snippet || "";

  // violations table
  const tbody = document.getElementById("violations-body");
  tbody.innerHTML = "";
  (obs.violations || []).forEach(v => {
    const tr = document.createElement("tr");
    tr.className = "level-" + v.level;
    tr.innerHTML = `
      <td><span class="badge badge-${v.level}">${v.level}</span></td>
      <td style="font-family:var(--mono);font-size:12px;color:#a8d8a8;">${escHtml(v.selector)}</td>
      <td style="color:var(--muted);">${escHtml(v.description)}</td>`;
    tr.onclick = () => {
      document.getElementById("target").value = v.selector;
      document.getElementById("action-type").value = "fix";
    };
    tbody.appendChild(tr);
  });

  // remaining counts
  const rem = obs.remaining_violations || {};
  document.getElementById("rem-A").textContent   = rem.A   ?? "—";
  document.getElementById("rem-AA").textContent  = rem.AA  ?? "—";
  document.getElementById("rem-AAA").textContent = rem.AAA ?? "—";

  // chart
  if (reward !== undefined && obs.step_number > 0) {
    chartLabels.push("S" + obs.step_number);
    chartData.push(parseFloat(reward.toFixed(3)));
    rewardChart.update();
  }

  // done banner
  if (obs.done) {
    const banner = document.getElementById("done-banner");
    banner.style.display = "block";
    const score = obs.metadata?.episode_score?.toFixed(3) ?? "N/A";
    banner.textContent = "✓ DONE — Final score: " + score;
    document.getElementById("exec-btn").disabled = true;
  }

  // history row
  if (window._lastAction && reward !== undefined) {
    const a = window._lastAction;
    const tbody2 = document.getElementById("history-body");
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid var(--border)";
    tr.innerHTML = `
      <td>${obs.step_number}</td>
      <td><span class="badge" style="background:rgba(0,170,255,0.12);color:#0af;border:1px solid rgba(0,170,255,0.25);">${escHtml(a.action_type)}</span></td>
      <td style="font-family:var(--mono);font-size:11px;color:#a8d8a8;">${escHtml(a.target)}</td>
      <td style="color:var(--muted);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(a.proposed_fix)}">${escHtml(a.proposed_fix)}</td>
      <td style="font-family:var(--mono);color:${reward >= 0 ? '#00e5a0' : '#ff4f4f'};">${reward.toFixed(3)}</td>
      <td style="color:var(--muted);font-size:11px;">${escHtml(obs.metadata?.event || "")}</td>`;
    tbody2.prepend(tr);
    window._lastAction = null;
  }
}

function escHtml(s) {
  return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

async function resetEnv() {
  showError("");
  document.getElementById("exec-btn").disabled = false;
  document.getElementById("done-banner").style.display = "none";
  document.getElementById("history-body").innerHTML = "";
  document.getElementById("violations-body").innerHTML = "";
  initChart();

  try {
    const res = await fetch(BACKEND + "/reset", { method: "POST" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const obs = await res.json();
    updateUI(obs);
  } catch(e) {
    showError("Reset failed: " + e.message);
  }
}

async function executeStep() {
  showError("");
  const action = {
    action_type:  document.getElementById("action-type").value,
    target:       document.getElementById("target").value,
    proposed_fix: document.getElementById("proposed-fix").value,
  };
  window._lastAction = action;
  document.getElementById("exec-btn").disabled = true;

  try {
    const res = await fetch(BACKEND + "/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    // support both flat and nested response shapes
    const obs    = data.observation ?? data;
    const reward = data.reward ?? obs.reward ?? 0;
    updateUI(obs, reward);
    if (!obs.done) document.getElementById("exec-btn").disabled = false;
  } catch(e) {
    showError("Step failed: " + e.message);
    window._lastAction = null;
    document.getElementById("exec-btn").disabled = false;
  }
}

// init chart on load
window.addEventListener("load", initChart);
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML

if __name__ == "__main__":
    print("\\n  Webyx UI  →  http://localhost:7860\\n")
    uvicorn.run(app, host="0.0.0.0", port=7860)