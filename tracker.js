/* ─── Peptide Tracker — Simplified ─── */

var STATE_KEY = "peptide_tracker_v3";
var COLORS = ["#d93838", "#e86f3a", "#f0b34b", "#4cd964", "#5ac8fa", "#af6ee8", "#ff6b9d", "#50c8a0"];
var state = loadState();
var activeId = null;
var weekOff = 0;
var _contextTarget = null;

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

function daysBetween(a, b) {
  var da = new Date(a), db = new Date(b);
  return Math.round((db - da) / 86400000);
}

function loadState() {
  try { var raw = localStorage.getItem(STATE_KEY); if (raw) return JSON.parse(raw); } catch (_) {}
  return { peptides: {}, logs: {}, order: [] };
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
  if (!state.order) state.order = [];
  state.order.push(id);
  saveState();
  renderTabs();
  if (!activeId) setActive(id);
  return id;
}

function deletePeptide(id) {
  if (!confirm('Delete "' + state.peptides[id].name + '" and all its logs?')) return;
  delete state.peptides[id];
  delete state.logs[id];
  if (state.order) state.order = state.order.filter(function (o) { return o !== id; });
  saveState();
  var keys = peptideIds();
  activeId = keys.length ? keys[0] : null;
  renderAll();
}

function peptideIds() {
  var ids = Object.keys(state.peptides);
  if (state.order && state.order.length) {
    var ordered = state.order.filter(function (o) { return ids.indexOf(o) > -1; });
    var remaining = ids.filter(function (i) { return ordered.indexOf(i) === -1; });
    return ordered.concat(remaining);
  }
  return ids;
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

/* ─── Logging ─── */
function logDoseNow(pepId, doseVal) {
  _logDose(pepId, doseVal, todayStr(), nowStr());
}

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

function editLog(pepId, weekKey, idx) {
  var logs = (state.logs[pepId] || {})[weekKey] || [];
  if (!logs[idx]) return;
  var newDose = prompt("Edit dose (mg):", logs[idx].dose);
  if (newDose !== null && parseFloat(newDose) > 0) {
    logs[idx].dose = parseFloat(newDose);
    saveState();
    renderActive();
  }
}

/* ─── Quick copy last week ─── */
function copyLastWeek(pepId) {
  var wk = getCurrentWeekKey();
  var curWeekKey = wk.key;
  var logs = (state.logs[pepId] || {})[curWeekKey] || [];
  if (logs.length) {
    if (typeof showToast === 'function') showToast('This week already has logs', '');
    return;
  }
  // Find previous week
  var allWeeks = Object.keys(state.logs[pepId] || {}).sort();
  var idx2 = allWeeks.indexOf(curWeekKey);
  if (idx2 <= 0) {
    if (typeof showToast === 'function') showToast('No previous week to copy', '');
    return;
  }
  var prevWeek = allWeeks[idx2 - 1];
  var prevLogs = state.logs[pepId][prevWeek] || [];
  if (!prevLogs.length) {
    if (typeof showToast === 'function') showToast('No logs in previous week', '');
    return;
  }
  // Calculate date offset between weeks
  var curStart = new Date(wk.start);
  curStart.setDate(curStart.getDate() - curStart.getDay() + 1);
  var prevStart = new Date(curStart);
  prevStart.setDate(prevStart.getDate() - 7);
  var offset = 7;

  if (!state.logs[pepId][curWeekKey]) state.logs[pepId][curWeekKey] = [];
  for (var i = 0; i < prevLogs.length; i++) {
    var pl = prevLogs[i];
    if (pl.date) {
      var d = new Date(pl.date);
      d.setDate(d.getDate() + offset);
      var newDate = d.toISOString().split("T")[0];
      var newTime = pl.time || "08:00";
      state.logs[pepId][curWeekKey].push({
        dose: pl.dose,
        timestamp: newDate + "T" + newTime,
        date: newDate,
        time: newTime,
      });
    }
  }
  saveState();
  renderActive();
  if (typeof showToast === 'function') showToast('Copied last week\'s schedule', '📋');
}

/* ─── Week nav ─── */
function weekOffset(delta) { weekOff += delta; renderActive(); }

function getCurrentWeekKey() {
  var d = new Date();
  d.setDate(d.getDate() + weekOff * 7);
  return { key: getWeekKey(d), start: d };
}

/* ─── Streak calc ─── */
function calcStreak(pepId) {
  var allLogs = [];
  for (var wk in (state.logs[pepId] || {})) {
    for (var i = 0; i < (state.logs[pepId][wk] || []).length; i++) {
      allLogs.push(state.logs[pepId][wk][i]);
    }
  }
  if (!allLogs.length) return { streak: 0, current: false };
  var dates = {};
  for (var j = 0; j < allLogs.length; j++) dates[allLogs[j].date] = true;
  var dayKeys = Object.keys(dates).sort();
  var today = todayStr();
  var yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
  var yesStr = yesterday.toISOString().split("T")[0];
  var check = dates[today] ? today : (dates[yesterday] ? yesterday : null);
  if (!check) return { streak: 0, current: false };
  var streak = 1;
  var cur = new Date(check);
  for (var k = 0; k < 365; k++) {
    cur.setDate(cur.getDate() - 1);
    var ds = cur.toISOString().split("T")[0];
    if (dates[ds]) { streak++; } else { break; }
  }
  return { streak: streak, current: true };
}

/* ─── Sparkline data ─── */
function getSparklineData(pepId) {
  var byDate = {};
  for (var wk in (state.logs[pepId] || {})) {
    for (var i = 0; i < (state.logs[pepId][wk] || []).length; i++) {
      var l = state.logs[pepId][wk][i];
      if (!byDate[l.date]) byDate[l.date] = 0;
      byDate[l.date] += l.dose;
    }
  }
  var days = [];
  var today = new Date();
  for (var j = 6; j >= 0; j--) {
    var d = new Date(today);
    d.setDate(d.getDate() - j);
    days.push(byDate[d.toISOString().split("T")[0]] || 0);
  }
  return days;
}

function renderSparkline(data, color) {
  var max = Math.max.apply(null, data) || 1;
  var html = '<span class="sparkline-wrap">';
  for (var i = 0; i < data.length; i++) {
    var h = Math.max(2, (data[i] / max) * 22);
    html += '<span class="sparkline-bar" style="height:' + h + 'px;background:' + (data[i] > 0 ? color : 'var(--surface-4)') + '"></span>';
  }
  html += '</span>';
  return html;
}

/* ─── Trend calc ─── */
function calcTrend(pepId) {
  var allLogs = [];
  for (var wk in (state.logs[pepId] || {})) {
    for (var i = 0; i < (state.logs[pepId][wk] || []).length; i++) {
      allLogs.push(state.logs[pepId][wk][i]);
    }
  }
  allLogs.sort(function (a, b) { return a.timestamp.localeCompare(b.timestamp); });
  if (allLogs.length < 4) return 0;
  var recent = allLogs.slice(-4);
  var firstHalf = (recent[0].dose + recent[1].dose) / 2;
  var secondHalf = (recent[2].dose + recent[3].dose) / 2;
  if (secondHalf > firstHalf * 1.1) return 1;
  if (secondHalf < firstHalf * 0.9) return -1;
  return 0;
}

/* ─── Render ─── */
function renderAll() { renderTabs(); renderActive(); }

function renderTabs() {
  var bar = document.getElementById("tab_bar");
  var ids = peptideIds();
  var html = "";
  for (var i = 0; i < ids.length; i++) {
    var p = state.peptides[ids[i]];
    if (!p) continue;
    var act = ids[i] === activeId ? " active" : "";
    html += '<button class="tab-btn' + act + '" draggable="true" data-id="' + ids[i] + '" ondragstart="tabDragStart(event)" ondragover="tabDragOver(event)" ondrop="tabDrop(event)" ondragend="tabDragEnd(event)" onclick="setActive(\'' + ids[i] + '\')">' +
      '<span class="tab-dot" style="background:' + p.color + '"></span>' + escHtml(p.name) +
      ' <span class="tab-del" onclick="event.stopPropagation();deletePeptide(\'' + ids[i] + '\')">✕</span></button>';
  }
  html += '<button class="tab-add" onclick="openAddForm()" title="Add peptide">+</button>';
  bar.innerHTML = html;
}

/* ─── Drag tabs ─── */
var _dragId = null;
function tabDragStart(e) {
  _dragId = e.target.getAttribute('data-id');
  e.target.classList.add('tab-dragging');
  e.dataTransfer.effectAllowed = 'move';
}
function tabDragOver(e) {
  e.preventDefault();
  var id = e.target.closest('.tab-btn');
  if (id) id.classList.add('tab-drag-over');
}
function tabDrop(e) {
  e.preventDefault();
  var target = e.target.closest('.tab-btn');
  if (!target || !_dragId) return;
  var targetId = target.getAttribute('data-id');
  if (_dragId === targetId) return;
  if (!state.order) state.order = peptideIds();
  var fromIdx = state.order.indexOf(_dragId);
  var toIdx = state.order.indexOf(targetId);
  if (fromIdx > -1 && toIdx > -1) {
    state.order.splice(fromIdx, 1);
    state.order.splice(toIdx, 0, _dragId);
    saveState();
    renderTabs();
  }
  _dragId = null;
}
function tabDragEnd(e) {
  e.target.classList.remove('tab-dragging');
  var overs = document.querySelectorAll('.tab-drag-over');
  for (var i = 0; i < overs.length; i++) overs[i].classList.remove('tab-drag-over');
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

  // Streak
  var streakInfo = calcStreak(activeId);
  var streakHtml = streakInfo.streak > 1 ? '<span class="streak-badge ' + (streakInfo.current ? 'on' : 'off') + '">' +
    (streakInfo.current ? '🔥' : '') + streakInfo.streak + ' day streak</span>' : '';

  var html = '<div class="log-bar">' +
    '<span class="pep-name" id="pep_name_display" onclick="startRename(\'' + activeId + '\')">' + escHtml(p.name) + '</span>' +
    streakHtml +
    '<span class="sep">|</span>';

  if (dose > 0) {
    html += '<button class="quick-btn primary" onclick="logDoseNow(\'' + activeId + '\',' + dose + ')">+' + dose.toFixed(1) + 'mg</button>' +
      '<button class="quick-btn" onclick="logDoseNow(\'' + activeId + '\',' + halfDose + ')">+' + halfDose + 'mg</button>';
  }

  html += '<input class="dose-input" id="custom_dose" type="number" step="0.01" min="0.01" placeholder="mg" onkeydown="if(event.key===\'Enter\')logDoseCustom(\'' + activeId + '\')">' +
    '<button class="quick-btn" onclick="logDoseCustom(\'' + activeId + '\')">Log</button>' +
    '<button class="bd-toggle" onclick="toggleBackdate()">←</button>' +
    '</div>';

  // ─── Backdate row ───
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

  // Sparkline
  var sparkData = getSparklineData(activeId);
  var sparkHtml = renderSparkline(sparkData, p.color);

  // Trend
  var trend = calcTrend(activeId);
  var trendHtml = '';
  if (trend !== 0) {
    trendHtml = '<span class="trend-arrow ' + (trend > 0 ? 'trend-up' : 'trend-down') + '">' + (trend > 0 ? '↑' : '↓') + '</span>';
  }

  html += '<div class="insights">' +
    '<div class="insight-card"><div class="val" style="color:' + p.color + '">' + weekTotal.toFixed(1) + '</div><div class="lbl">Week total' + trendHtml + '</div></div>' +
    '<div class="insight-card"><div class="val" style="color:' + p.color + '">' + compliance + '%</div><div class="lbl">' + actual + '/' + expected + ' doses</div></div>' +
    '<div class="insight-card"><div class="val" style="color:' + p.color + '">' + lastStr + '</div><div class="lbl">Last dose</div></div>' +
    '<div class="insight-card"><div class="val" style="color:' + p.color + '">' + (allLogs.length) + '</div><div class="lbl">Total logs' + sparkHtml + '</div></div>' +
    '</div>';

  // ─── Chart ───
  html += '<div class="chart-wrap"><canvas id="dose_chart"></canvas></div>';

  // ─── Logs list ───
  html += '<div class="logs-section"><div class="logs-head">' +
    '<h3>Dose history</h3>' +
    '<div class="week-nav"><button onclick="weekOffset(-1)">←</button><span>' + (weekOff === 0 ? "This week" : weekKey) + '</span><button onclick="weekOffset(1)">→</button>' +
    '<button class="timeline-toggle" onclick="toggleTimeline()" title="Timeline view">&#8986;</button>' +
    '<button class="timeline-toggle" onclick="copyLastWeek(\'' + activeId + '\')" title="Copy last week">&#128203;</button>' +
    '</div>' +
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
      html += '<div class="log-row" oncontextmenu="showContextMenu(event,\'' + activeId + '\',\'' + weekKey + '\',' + origIdx + ')">' +
        '<div class="l-left"><span class="dot" style="background:' + p.color + '"></span>' +
        '<span class="date">' + escHtml(l.date) + '</span>' +
        '<span class="time">' + escHtml(l.time) + '</span></div>' +
        '<span class="dose">' + l.dose.toFixed(2) + ' mg</span>' +
        '<button class="del" onclick="deleteLog(\'' + activeId + '\',\'' + weekKey + '\',' + origIdx + ')">✕</button></div>';
    }
  }

  html += '</div></div>';

  // ─── Timeline ───
  html += '<div id="timeline_view" class="timeline-view" style="display:none"></div>';

  panel.innerHTML = html;
  panel.classList.remove('tab-panel-enter');
  void panel.offsetWidth;
  panel.classList.add('tab-panel-enter');

  // ─── Render chart ───
  renderChart(activeId, logs);
}

/* ─── Timeline toggle ─── */
var _timelineOpen = false;
function toggleTimeline() {
  _timelineOpen = !_timelineOpen;
  var el = document.getElementById('timeline_view');
  if (!el) return;
  if (_timelineOpen) {
    // Gather all logs across all peptides, sorted
    var items = [];
    for (var pid in state.peptides) {
      for (var wk in (state.logs[pid] || {})) {
        for (var i = 0; i < (state.logs[pid][wk] || []).length; i++) {
          var l = state.logs[pid][wk][i];
          items.push({ date: l.date, time: l.time, dose: l.dose, name: state.peptides[pid].name, color: state.peptides[pid].color });
        }
      }
    }
    items.sort(function (a, b) { return (a.date + 'T' + a.time).localeCompare(b.date + 'T' + b.time); });
    items.reverse();
    var html = '';
    for (var j = 0; j < Math.min(items.length, 50); j++) {
      html += '<div class="timeline-item">' +
        '<span class="t-date">' + escHtml(items[j].date) + ' ' + escHtml(items[j].time || '') + '</span>' +
        '<span class="t-dose">' + items[j].dose.toFixed(2) + ' mg</span>' +
        '<span class="t-pep" style="color:' + items[j].color + '">' + escHtml(items[j].name) + '</span>' +
        '</div>';
    }
    if (!items.length) html = '<div class="empty-logs">No logs yet.</div>';
    el.innerHTML = html;
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
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

    ctx.shadowColor = color;
    ctx.shadowBlur = days[k].val > 0 ? 8 : 0;
    ctx.fillStyle = days[k].val > 0 ? color : "transparent";
    ctx.beginPath();
    ctx.roundRect(x + 3, y, barW - 6, Math.max(barH, 0), [4, 4, 0, 0]);
    ctx.fill();
    ctx.shadowBlur = 0;

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

/* ─── Context Menu ─── */
function showContextMenu(e, pepId, weekKey, idx) {
  e.preventDefault();
  _contextTarget = { pepId: pepId, weekKey: weekKey, idx: idx };
  var menu = document.getElementById('context_menu');
  if (!menu) return;
  menu.style.left = Math.min(e.clientX, window.innerWidth - 160) + 'px';
  menu.style.top = Math.min(e.clientY, window.innerHeight - 100) + 'px';
  menu.classList.add('active');
}

function contextEdit() {
  if (_contextTarget) editLog(_contextTarget.pepId, _contextTarget.weekKey, _contextTarget.idx);
  closeContextMenu();
}

function contextDelete() {
  if (_contextTarget) deleteLog(_contextTarget.pepId, _contextTarget.weekKey, _contextTarget.idx);
  closeContextMenu();
}

function closeContextMenu() {
  var menu = document.getElementById('context_menu');
  if (menu) menu.classList.remove('active');
  _contextTarget = null;
}

/* ─── Pull to Refresh ─── */
var _pullStartY = 0;
var _pulling = false;
function initPullToRefresh() {
  var tracker = document.querySelector('.tracker-page');
  if (!tracker) return;
  tracker.addEventListener('touchstart', function (e) {
    if (window.scrollY > 0) return;
    _pullStartY = e.touches[0].clientY;
    _pulling = true;
  }, { passive: true });
  tracker.addEventListener('touchmove', function (e) {
    if (!_pulling || window.scrollY > 0) return;
    var dy = e.touches[0].clientY - _pullStartY;
    if (dy > 60) {
      _pulling = false;
      weekOffset(0);
      if (typeof showToast === 'function') showToast('Refreshed', '↻');
    }
  }, { passive: true });
  tracker.addEventListener('touchend', function () { _pulling = false; }, { passive: true });
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
  initPullToRefresh();

  // Click outside closes context menu
  document.addEventListener('click', function (e) {
    if (e.target.closest('.context-menu')) return;
    closeContextMenu();
  });
});
