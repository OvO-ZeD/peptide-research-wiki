/* ─── Peptide Tracker — Client Logic ─── */

/* ─── State ─── */
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

function loadState() {
  try {
    var raw = localStorage.getItem(STATE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return { peptides: {}, logs: {} };
}

function saveState() {
  localStorage.setItem(STATE_KEY, JSON.stringify(state));
}

/* ─── Peptide CRUD ─── */
function addPeptide(name, doseMg, freq) {
  var id = "p" + Date.now() + Math.random().toString(36).slice(2, 6);
  state.peptides[id] = {
    id: id,
    name: name.trim(),
    doseMg: parseFloat(doseMg) || 0,
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
  delete state.peptides[id];
  delete state.logs[id];
  saveState();
  if (activeId === id) {
    var keys = Object.keys(state.peptides);
    activeId = keys.length ? keys[0] : null;
  }
  renderTabs();
  renderActive();
}

function updatePeptide(id, name, doseMg, freq) {
  var p = state.peptides[id];
  if (!p) return;
  p.name = name.trim();
  p.doseMg = parseFloat(doseMg) || 0;
  p.freq = parseInt(freq) || 1;
  saveState();
  renderTabs();
  renderActive();
}

/* ─── Logging ─── */
function logDose(e) {
  e.preventDefault();
  if (!activeId) return false;
  var dose = parseFloat(document.getElementById("log_dose").value);
  var date = document.getElementById("log_date").value;
  var time = document.getElementById("log_time").value;
  if (!dose || !date || !time) return false;
  var dt = new Date(date + "T" + time);
  var weekKey = getWeekKey(date);
  if (!state.logs[activeId][weekKey]) state.logs[activeId][weekKey] = [];
  state.logs[activeId][weekKey].push({
    dose: dose,
    timestamp: dt.toISOString(),
    date: date,
    time: time,
  });
  saveState();
  renderActive();
  return false;
}

function deleteLog(pepId, weekKey, idx) {
  if (!state.logs[pepId] || !state.logs[pepId][weekKey]) return;
  state.logs[pepId][weekKey].splice(idx, 1);
  if (!state.logs[pepId][weekKey].length) delete state.logs[pepId][weekKey];
  saveState();
  renderActive();
}

/* ─── Week navigation ─── */
function weekOffset(delta) {
  weekOff += delta;
  renderActive();
}

function getCurrentWeekKey() {
  var d = new Date();
  d.setDate(d.getDate() + weekOff * 7);
  return { key: getWeekKey(d), start: d };
}

/* ─── Render tabs ─── */
function renderTabs() {
  var bar = document.getElementById("tab_bar");
  var keys = Object.keys(state.peptides);
  var html = "";
  for (var i = 0; i < keys.length; i++) {
    var p = state.peptides[keys[i]];
    var activeClass = keys[i] === activeId ? " active" : "";
    var logCount = 0;
    for (var wk in (state.logs[keys[i]] || {})) logCount += state.logs[keys[i]][wk].length;
    html += '<button class="tab-btn' + activeClass + '" onclick="setActive(\'' + keys[i] + '\')" style="border-left:2px solid ' + p.color + '">' +
      escHtml(p.name) + ' <span class="tab-badge">' + logCount + '</span></button>';
  }
  html += '<button class="tab-btn add-tab" onclick="openAddPeptideModal()">+</button>';
  bar.innerHTML = html;
}

/* ─── Set active ─── */
function setActive(id) {
  activeId = id;
  weekOff = 0;
  renderTabs();
  renderActive();
}

/* ─── Render active panel ─── */
function renderActive() {
  var p = state.peptides[activeId];
  var panel = document.getElementById("active_panel");
  if (!p) {
    panel.innerHTML = '<div class="empty-logs">Add a peptide to start tracking.</div>';
    return;
  }

  // Log form header
  document.getElementById("log_color").style.background = p.color;
  document.getElementById("log_pep_name").textContent = p.name;
  document.getElementById("log_dose").value = p.doseMg || "";
  document.getElementById("log_date").value = todayStr();
  document.getElementById("log_time").value = nowStr();

  // Current week
  var wk = getCurrentWeekKey();
  var weekKey = wk.key;
  document.getElementById("week_label").textContent = weekOff === 0 ? "This week" : weekKey;

  var logs = (state.logs[activeId] || {})[weekKey] || [];
  var freq = p.freq;

  // Insights
  var weekTotal = logs.reduce(function (s, l) { return s + l.dose; }, 0);
  document.getElementById("insight_total").textContent = weekTotal.toFixed(1) + "mg";

  var expected = Math.max(freq, 1);
  var actual = logs.length;
  var compliance = expected > 0 ? Math.round((actual / expected) * 100) : 0;
  document.getElementById("insight_compliance").textContent = Math.min(compliance, 100) + "%";
  document.getElementById("insight_expected").textContent = actual + "/" + expected + " doses";

  // Last dose
  var allLogs = [];
  for (var wk2 in (state.logs[activeId] || {})) {
    for (var li = 0; li < (state.logs[activeId][wk2] || []).length; li++) {
      allLogs.push(state.logs[activeId][wk2][li]);
    }
  }
  allLogs.sort(function (a, b) { return b.timestamp.localeCompare(a.timestamp); });
  if (allLogs.length) {
    var last = new Date(allLogs[0].timestamp);
    var hours = Math.round((Date.now() - last) / 3600000);
    document.getElementById("insight_last").textContent = hours < 24 ? hours + "h ago" : Math.round(hours / 24) + "d ago";
  } else {
    document.getElementById("insight_last").textContent = "—";
  }

  // Streak
  var streak = 0;
  if (allLogs.length) {
    var checkDate = new Date();
    // Normalize to midnight
    for (var s = 0; s < 365; s++) {
      var check = new Date(checkDate);
      check.setDate(check.getDate() - s);
      var checkStr = check.toISOString().split("T")[0];
      var hasLog = false;
      for (var lc = 0; lc < allLogs.length; lc++) {
        if (allLogs[lc].date === checkStr) { hasLog = true; break; }
      }
      if (hasLog) streak++;
      else if (s > 0) break;
      else { /* today has no log yet, that's ok */ }
    }
  }
  document.getElementById("insight_streak").textContent = streak + "d";

  // Chart
  renderChart(activeId, logs);

  // Logs list
  var listEl = document.getElementById("logs_list");
  if (!logs.length) {
    listEl.innerHTML = '<div class="empty-logs">No doses logged this week.</div>';
  } else {
    // Sort newest first
    var sorted = logs.slice().sort(function (a, b) { return b.timestamp.localeCompare(a.timestamp); });
    var html = "";
    for (var li2 = 0; li2 < sorted.length; li2++) {
      var l = sorted[li2];
      // Find original index for delete
      var origIdx = logs.indexOf(l);
      html += '<div class="log-entry">' +
        '<div class="log-entry-left">' +
          '<span class="dot" style="background:' + p.color + '"></span>' +
          '<span class="date">' + escHtml(l.date) + '</span>' +
          '<span class="time">' + escHtml(l.time) + '</span>' +
        '</div>' +
        '<span class="dose">' + l.dose.toFixed(2) + ' mg</span>' +
        '<button class="del" onclick="deleteLog(\'' + activeId + '\',\'' + weekKey + '\',' + origIdx + ')">✕</button>' +
        '</div>';
    }
    listEl.innerHTML = html;
  }
}

/* ─── Chart ─── */
function renderChart(pepId, weekLogs) {
  var canvas = document.getElementById("dose_chart");
  var ctx = canvas.getContext("2d");
  var rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width - 32;
  canvas.height = 120;

  var w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Group by date
  var byDate = {};
  for (var i = 0; i < weekLogs.length; i++) {
    var d = weekLogs[i].date;
    if (!byDate[d]) byDate[d] = 0;
    byDate[d] += weekLogs[i].dose;
  }

  // Get last 7 days
  var days = [];
  var today = new Date();
  for (var j = 6; j >= 0; j--) {
    var d2 = new Date(today);
    d2.setDate(d2.getDate() - j);
    var key = d2.toISOString().split("T")[0];
    var val = byDate[key] || 0;
    days.push({ key: key, val: val });
  }

  var maxVal = Math.max.apply(null, days.map(function (d) { return d.val; })) || 1;
  var pad = 8;
  var barW = (w - pad * 2) / 7;
  var p = state.peptides[activeId];

  for (var k = 0; k < days.length; k++) {
    var x = pad + k * barW;
    var barH = (days[k].val / maxVal) * (h - 30);
    var y = h - 10 - barH;

    // Bar
    ctx.fillStyle = days[k].val > 0 ? p.color : "rgba(255,255,255,0.04)";
    ctx.beginPath();
    ctx.roundRect(x + 3, y, barW - 6, barH, [3, 3, 0, 0]);
    ctx.fill();

    // Day label
    var dayName = days[k].key.slice(-2);
    ctx.fillStyle = days[k].val > 0 ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.15)";
    ctx.font = "9px system-ui";
    ctx.textAlign = "center";
    ctx.fillText(dayName, x + barW / 2, h - 1);
  }
}

/* ─── Calculator ─── */
function calcUnits() {
  var vial = parseFloat(document.getElementById("calc_vial").value) || 5;
  var water = parseFloat(document.getElementById("calc_water").value) || 1;
  var dose = parseFloat(document.getElementById("calc_dose").value) || 0;
  var concentration = vial / water;
  var units = dose / concentration * 100;
  document.getElementById("calc_result").textContent = "= " + Math.round(units) + " units";
}

/* ─── Export / Import ─── */
function exportCSV() {
  if (!activeId) return;
  var p = state.peptides[activeId];
  var rows = [["Date", "Time", "Dose (mg)", "Peptide"]];
  var allLogs = [];
  for (var wk in (state.logs[activeId] || {})) {
    for (var i = 0; i < (state.logs[activeId][wk] || []).length; i++) {
      allLogs.push(state.logs[activeId][wk][i]);
    }
  }
  allLogs.sort(function (a, b) { return a.timestamp.localeCompare(b.timestamp); });
  for (var j = 0; j < allLogs.length; j++) {
    rows.push([allLogs[j].date, allLogs[j].time, allLogs[j].dose, p.name]);
  }
  var csv = rows.map(function (r) { return r.join(","); }).join("\n");
  download(csv, "peptide_logs_" + p.name + ".csv", "text/csv");
}

function exportJSON() {
  download(JSON.stringify(state, null, 2), "peptide_tracker_backup.json", "application/json");
}

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
        renderTabs();
        renderActive();
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

/* ─── Modal ─── */
function openAddPeptideModal(editId) {
  var existing = editId ? state.peptides[editId] : null;
  var title = existing ? "Edit peptide" : "Add peptide";
  var nameVal = existing ? existing.name : "";
  var doseVal = existing ? existing.doseMg : "";
  var freqVal = existing ? existing.freq : "3";

  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.onclick = function (e) { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML =
    '<div class="modal">' +
      '<h3>' + title + '</h3>' +
      '<div class="modal-field"><label>Name</label><input id="modal_name" value="' + escHtml(nameVal) + '" placeholder="e.g. Tesamorelin"></div>' +
      '<div class="modal-field"><label>Dose (mg)</label><input id="modal_dose" type="number" step="0.01" min="0.01" value="' + doseVal + '" placeholder="e.g. 2"></div>' +
      '<div class="modal-field"><label>Frequency / week</label><input id="modal_freq" type="number" min="1" max="14" value="' + freqVal + '"></div>' +
      '<div class="modal-actions">' +
        '<button class="secondary" onclick="this.closest(\'.modal-overlay\').remove()">Cancel</button>' +
        (existing ? '<button class="danger" onclick="deletePeptide(\'' + editId + '\'); this.closest(\'.modal-overlay\').remove()">Delete</button>' : '') +
        '<button class="primary" onclick="savePeptideModal(\'' + (editId || "") + '\')">Save</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);
  setTimeout(function () { document.getElementById("modal_name").focus(); }, 100);
}

function savePeptideModal(editId) {
  var name = document.getElementById("modal_name").value.trim();
  var dose = document.getElementById("modal_dose").value;
  var freq = document.getElementById("modal_freq").value;
  if (!name) return;
  if (editId) {
    updatePeptide(editId, name, dose, freq);
  } else {
    addPeptide(name, dose, freq);
  }
  document.querySelector(".modal-overlay").remove();
}

/* ─── Escaping ─── */
function escHtml(v) {
  return String(v || "").replace(/[&<>"']/g, function (m) {
    return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[m];
  });
}

/* ─── Init ─── */
document.addEventListener("DOMContentLoaded", function () {
  var keys = Object.keys(state.peptides);
  if (keys.length) activeId = keys[0];
  renderTabs();
  renderActive();
  calcUnits();
});
