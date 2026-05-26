/* ─── Peptide Tracker — Simplified ─── */

var STATE_KEY = "peptide_tracker_v3";
var COLORS = ["#d93838", "#e86f3a", "#f0b34b", "#4cd964", "#5ac8fa", "#af6ee8", "#ff6b9d", "#50c8a0"];
var state = loadState();
var activeId = null;
var weekOff = 0;

/* ─── Helpers ─── */
function getWeekKey(d) {
  var dt = new Date(d);
  var y = dt.getFullYear();
  var jan1 = new Date(y, 0, 1);
  var days = Math.floor((dt - jan1) / 86400000);
  var w = Math.ceil((days + jan1.getDay() + 1) / 7);
  return y + "-W" + String(w).padStart(2, "0");
}

function todayStr() { return new Date().toISOString().split("T")[0]; }
function nowStr() { return new Date().toTimeString().slice(0, 5); }
function escHtml(v) { return String(v || "").replace(/[&<>"']/g, function (m) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[m]; }); }

function loadState() {
  try { var raw = localStorage.getItem(STATE_KEY); if (raw) return JSON.parse(raw); } catch (_) {}
  return { peptides: {}, logs: {} };
}

function saveState() { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }

/* ─── Peptide CRUD ─── */
function addPeptide(name, doseMg, freq) {
  var id = "p" + Date.now() + Math.random().toString(36).slice(2, 6);
  state.peptides[id] = {
    id: id, name: name.trim(), doseMg: parseFloat(doseMg) || 0,
    freq: parseInt(freq) || 1,
    color: COLORS[Object.keys(state.peptides).length % COLORS.length],
    created: new Date().toISOString(),
  };
  if (!state.logs[id]) state.logs[id] = {};
  saveState();
  renderTabs();
  if (!activeId) setActive(id);
  return id;
}

function deletePeptide(id) {
  if (!confirm('Delete "' + state.peptides[id].name + '" and all its logs?')) return;
  delete state.peptides[id];
  delete state.logs[id];
  saveState();
  var keys = Object.keys(state.peptides);
  activeId = keys.length ? keys[0] : null;
  renderAll();
}

/* ─── Inline add form ─── */
function openAddForm() {
  document.getElementById("add_form").style.display = "block";
  document.getElementById("add_name").value = "";
  document.getElementById("add_dose").value = "";
  document.getElementById("add_freq").value = "3";
  setTimeout(function () { document.getElementById("add_name").focus(); }, 50);
}

function closeAddForm() { document.getElementById("add_form").style.display = "none"; }

function saveAddPeptide() {
  var name = document.getElementById("add_name").value.trim();
  var dose = document.getElementById("add_dose").value;
  var freq = document.getElementById("add_freq").value;
  if (!name) return;
  addPeptide(name, dose, freq);
  closeAddForm();
}

/* ─── Logging (current time) ─── */
function logDoseNow(pepId, doseVal) {
  _logDose(pepId, doseVal, todayStr(), nowStr());
}

/* ─── Logging (backdated) ─── */
function logDoseBackdated(pepId) {
  var date = document.getElementById("bd_date").value;
  var time = document.getElementById("bd_time").value;
  var dose = parseFloat(document.getElementById("bd_dose").value);
  if (!date || !time || !dose) return;
  _logDose(pepId, dose, date, time);
  toggleBackdate();
}

function _logDose(pepId, doseVal, date, time) {
  var p = state.peptides[pepId];
  if (!p || !doseVal || doseVal <= 0) return;
  var weekKey = getWeekKey(date);
  if (!state.logs[pepId][weekKey]) state.logs[pepId][weekKey] = [];
  state.logs[pepId][weekKey].push({ dose: doseVal, timestamp: date + "T" + time, date: date, time: time });
  saveState();
  renderActive();
}

function logDoseCustom(pepId) {
  var inp = document.getElementById("custom_dose");
  var val = parseFloat(inp.value);
  if (val && val > 0) logDoseNow(pepId, val);
}

function toggleBackdate() {
  var el = document.getElementById("bd_row");
  el.style.display = el.style.display === "flex" ? "none" : "flex";
  if (el.style.display === "flex") {
    document.getElementById("bd_date").value = todayStr();
    document.getElementById("bd_time").value = nowStr();
    var p = state.peptides[activeId];
    if (p) document.getElementById("bd_dose").value = p.doseMg || "";
  }
}

function deleteLog(pepId, weekKey, idx) {
  if (!state.logs[pepId] || !state.logs[pepId][weekKey]) return;
  state.logs[pepId][weekKey].splice(idx, 1);
  if (!state.logs[pepId][weekKey].length) delete state.logs[pepId][weekKey];
  saveState();
  renderActive();
}

/* ─── Week nav ─── */
function weekOffset(delta) { weekOff += delta; renderActive(); }

function getCurrentWeekKey() {
  var d = new Date();
  d.setDate(d.getDate() + weekOff * 7);
  return { key: getWeekKey(d), start: d };
}

/* ─── Render ─── */
function renderAll() { renderTabs(); renderActive(); }

function renderTabs() {
  var bar = document.getElementById("tab_bar");
  var keys = Object.keys(state.peptides);
  var html = "";
  for (var i = 0; i < keys.length; i++) {
    var p = state.peptides[keys[i]];
    var act = keys[i] === activeId ? " active" : "";
    html += '<button class="tab-btn' + act + '" onclick="setActive(\'' + keys[i] + '\')">' +
      '<span class="tab-dot" style="background:' + p.color + '"></span>' + escHtml(p.name) +
      ' <span class="tab-del" onclick="event.stopPropagation();deletePeptide(\'' + keys[i] + '\')">✕</span></button>';
  }
  html += '<button class="tab-add" onclick="openAddForm()" title="Add peptide">+</button>';
  bar.innerHTML = html;
}

function setActive(id) {
  activeId = id;
  weekOff = 0;
  renderTabs();
  renderActive();
}

function renderActive() {
  var panel = document.getElementById("active_panel");
  var p = state.peptides[activeId];

  if (!p || !Object.keys(state.peptides).length) {
    panel.innerHTML = '<div class="empty-tracker" style="animation:fadeSlide 0.5s ease-out"><p>No peptides yet.</p><button class="big-add-btn" onclick="openAddForm()">+ Add your first peptide</button></div>';
    return;
  }

  var wk = getCurrentWeekKey();
  var weekKey = wk.key;
  var logs = (state.logs[activeId] || {})[weekKey] || [];
  var freq = p.freq;

  // ─── Log bar ───
  var dose = p.doseMg || 0;
  var halfDose = (dose / 2).toFixed(2);
  var html = '<div class="log-bar">' +
    '<span class="pep-name" id="pep_name_display" onclick="startRename(\'' + activeId + '\')">' + escHtml(p.name) + '</span>' +
    '<span class="sep">|</span>';

  if (dose > 0) {
    html += '<button class="quick-btn primary" onclick="logDoseNow(\'' + activeId + '\',' + dose + ')">+' + dose.toFixed(1) + 'mg</button>' +
      '<button class="quick-btn" onclick="logDoseNow(\'' + activeId + '\',' + halfDose + ')">+' + halfDose + 'mg</button>';
  }

  html += '<input class="dose-input" id="custom_dose" type="number" step="0.01" min="0.01" placeholder="mg" onkeydown="if(event.key===\'Enter\')logDoseCustom(\'' + activeId + '\')">' +
    '<button class="quick-btn" onclick="logDoseCustom(\'' + activeId + '\')">Log</button>' +
    '<button class="bd-toggle" onclick="toggleBackdate()">←</button>' +
    '</div>';

  // ─── Backdate row (hidden) ───
  html += '<div class="bd-row" id="bd_row" style="display:none">' +
    '<input type="date" id="bd_date">' +
    '<input type="time" id="bd_time">' +
    '<input type="number" id="bd_dose" step="0.01" min="0.01" placeholder="mg" class="dose-input">' +
    '<button class="quick-btn primary" onclick="logDoseBackdated(\'' + activeId + '\')">Save</button>' +
    '</div>';

  // ─── Insights ───
  var weekTotal = logs.reduce(function (s, l) { return s + l.dose; }, 0);
  var actual = logs.length;
  var expected = Math.max(freq, 1);
  var compliance = expected > 0 ? Math.min(Math.round((actual / expected) * 100), 100) : 0;

  var allLogs = [];
  for (var wk2 in (state.logs[activeId] || {})) {
    for (var li = 0; li < (state.logs[activeId][wk2] || []).length; li++) allLogs.push(state.logs[activeId][wk2][li]);
  }
  allLogs.sort(function (a, b) { return b.timestamp.localeCompare(a.timestamp); });

  var lastStr = "—";
  if (allLogs.length) {
    var hours = Math.round((Date.now() - new Date(allLogs[0].timestamp)) / 3600000);
    lastStr = hours < 24 ? hours + "h ago" : Math.round(hours / 24) + "d ago";
  }

  html += '<div class="insights">' +
    '<div class="insight-card"><div class="val">' + weekTotal.toFixed(1) + '</div><div class="lbl">Week total</div></div>' +
    '<div class="insight-card"><div class="val">' + compliance + '%</div><div class="lbl">' + actual + '/' + expected + ' doses</div></div>' +
    '<div class="insight-card"><div class="val">' + lastStr + '</div><div class="lbl">Last dose</div></div>' +
    '<div class="insight-card"><div class="val">' + (allLogs.length) + '</div><div class="lbl">Total logs</div></div>' +
    '</div>';

  // ─── Chart ───
  html += '<div class="chart-wrap"><canvas id="dose_chart"></canvas></div>';

  // ─── Logs list ───
  html += '<div class="logs-section"><div class="logs-head">' +
    '<h3>Dose history</h3>' +
    '<div class="week-nav"><button onclick="weekOffset(-1)">←</button><span>' + (weekOff === 0 ? "This week" : weekKey) + '</span><button onclick="weekOffset(1)">→</button></div>' +
    '<div class="l-actions">' +
    '<button onclick="exportCSV(\'' + activeId + '\')">CSV</button>' +
    '<button onclick="exportJSON()">JSON</button>' +
    '<button onclick="document.getElementById(\'import_input\').click()">Import</button>' +
    '</div></div>' +
    '<input type="file" id="import_input" accept=".json" style="display:none" onchange="importData(event)">' +
    '<div id="logs_list">';

  if (!logs.length) {
    html += '<div class="empty-logs">No doses this week.</div>';
  } else {
    var sorted = logs.slice().sort(function (a, b) { return b.timestamp.localeCompare(a.timestamp); });
    for (var li2 = 0; li2 < sorted.length; li2++) {
      var l = sorted[li2];
      var origIdx = logs.indexOf(l);
      html += '<div class="log-row">' +
        '<div class="l-left"><span class="dot" style="background:' + p.color + '"></span>' +
        '<span class="date">' + escHtml(l.date) + '</span>' +
        '<span class="time">' + escHtml(l.time) + '</span></div>' +
        '<span class="dose">' + l.dose.toFixed(2) + ' mg</span>' +
        '<button class="del" onclick="deleteLog(\'' + activeId + '\',\'' + weekKey + '\',' + origIdx + ')">✕</button></div>';
    }
  }

  html += '</div></div>';
  panel.innerHTML = html;

  // ─── Render chart ───
  renderChart(activeId, logs);
}

/* ─── Chart ─── */
function renderChart(pepId, weekLogs) {
  var canvas = document.getElementById("dose_chart");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width - 28;
  canvas.height = 100;

  var w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  var byDate = {};
  for (var i = 0; i < weekLogs.length; i++) {
    var d = weekLogs[i].date;
    if (!byDate[d]) byDate[d] = 0;
    byDate[d] += weekLogs[i].dose;
  }

  var days = [];
  var today = new Date();
  for (var j = 6; j >= 0; j--) {
    var d2 = new Date(today);
    d2.setDate(d2.getDate() - j);
    var key = d2.toISOString().split("T")[0];
    days.push({ key: key, val: byDate[key] || 0 });
  }

  var maxVal = Math.max.apply(null, days.map(function (d) { return d.val; })) || 1;
  var pad = 8;
  var barW = (w - pad * 2) / 7;
  var pp = state.peptides[activeId];
  var color = pp ? pp.color : "#d93838";

  // Dim background bars
  ctx.fillStyle = "rgba(255,255,255,0.03)";
  for (var kk = 0; kk < days.length; kk++) {
    var x = pad + kk * barW;
    ctx.beginPath();
    ctx.roundRect(x + 3, 4, barW - 6, h - 14, [3, 3, 0, 0]);
    ctx.fill();
  }

  for (var k = 0; k < days.length; k++) {
    var x = pad + k * barW;
    var barH = (days[k].val / maxVal) * (h - 28);
    var y = h - 8 - barH;

    // Brighter bar with glow
    ctx.shadowColor = color;
    ctx.shadowBlur = days[k].val > 0 ? 8 : 0;
    ctx.fillStyle = days[k].val > 0 ? color : "transparent";
    ctx.beginPath();
    ctx.roundRect(x + 3, y, barW - 6, Math.max(barH, 0), [4, 4, 0, 0]);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Day label — bright white when data exists
    ctx.fillStyle = days[k].val > 0 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.15)";
    ctx.font = "9px 'Inter', system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(days[k].key.slice(-2), x + barW / 2, h - 2);
  }
}

/* ─── Calculator ─── */
function calcUnits() {
  var vial = parseFloat(document.getElementById("calc_vial").value) || 5;
  var water = parseFloat(document.getElementById("calc_water").value) || 1;
  var dose = parseFloat(document.getElementById("calc_dose").value) || 0;
  var units = dose / (vial / water) * 100;
  document.getElementById("calc_result").textContent = Math.round(units);
}

/* ─── Export / Import ─── */
function exportCSV(pepId) {
  var p = state.peptides[pepId];
  if (!p) return;
  var rows = [["Date", "Time", "Dose (mg)", "Peptide"]];
  var allLogs = [];
  for (var wk in (state.logs[pepId] || {})) {
    for (var i = 0; i < (state.logs[pepId][wk] || []).length; i++) allLogs.push(state.logs[pepId][wk][i]);
  }
  allLogs.sort(function (a, b) { return a.timestamp.localeCompare(b.timestamp); });
  for (var j = 0; j < allLogs.length; j++) rows.push([allLogs[j].date, allLogs[j].time, allLogs[j].dose, p.name]);
  download(rows.map(function (r) { return r.join(","); }).join("\n"), "peptide_logs_" + p.name + ".csv", "text/csv");
}

function exportJSON() { download(JSON.stringify(state, null, 2), "peptide_tracker_backup.json", "application/json"); }

function importData(e) {
  var file = e.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function (ev) {
    try {
      var data = JSON.parse(ev.target.result);
      if (data.peptides && data.logs) {
        state = data;
        saveState();
        var keys = Object.keys(state.peptides);
        activeId = keys.length ? keys[0] : null;
        renderAll();
      }
    } catch (_) { alert("Invalid file format."); }
  };
  reader.readAsText(file);
  e.target.value = "";
}

function download(content, filename, mime) {
  var blob = new Blob([content], { type: mime });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ─── Init ─── */
document.addEventListener("DOMContentLoaded", function () {
  var keys = Object.keys(state.peptides);
  if (keys.length) activeId = keys[0];
  renderAll();
  calcUnits();
});
