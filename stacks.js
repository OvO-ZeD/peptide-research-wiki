/* ─── State ─── */
var resultsRoot = document.getElementById('stack_results');
var SAVED_STACKS_KEY = 'peptide_saved_stacks';
var _lastResponse = null;
var _lastGoal = '';
var _lastGoalLabel = '';

/* ─── Saved stacks (localStorage) ─── */
function loadSavedStacks() {
  try { var raw = localStorage.getItem(SAVED_STACKS_KEY); return raw ? JSON.parse(raw) : []; } catch (_) { return []; }
}

function saveStackToLocal(stack) {
  var saved = loadSavedStacks();
  var id = stackName(stack);
  if (!saved.some(function (s) { return stackName(s) === id; })) {
    saved.push(stack);
    localStorage.setItem(SAVED_STACKS_KEY, JSON.stringify(saved));
  }
}

function removeStackFromLocal(stack) {
  var saved = loadSavedStacks();
  var id = stackName(stack);
  saved = saved.filter(function (s) { return stackName(s) !== id; });
  localStorage.setItem(SAVED_STACKS_KEY, JSON.stringify(saved));
}

function isStackSaved(stack) {
  var saved = loadSavedStacks();
  var id = stackName(stack);
  return saved.some(function (s) { return stackName(s) === id; });
}

function stackName(r) {
  var stk = r.stack || [];
  return stk.join(' + ') || 'Unknown';
}

/* ─── Helpers ─── */
function escapeHtml(v) {
  return String(v || '').replace(/[&<>"']/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
  });
}

function badgeTier(tier) {
  return '<span class="badge badge-tier-' + tier.toLowerCase() + '">' + escapeHtml(tier) + '</span>';
}

/* ─── Skeleton ─── */
function renderSkeleton() {
  var html = '';
  for (var i = 0; i < 4; i++) {
    html += '<div class="skeleton-card" style="animation:fadeSlide 0.4s ease-out both;animation-delay:' + (i * 0.06) + 's">' +
      '<div class="skeleton-line short"></div>' +
      '<div class="skeleton-line" style="width:45%"></div>' +
      '<div style="display:flex;gap:6px;margin-top:10px">' +
        '<div class="skeleton-badge"></div>' +
        '<div class="skeleton-badge" style="width:60px"></div>' +
      '</div>' +
    '</div>';
  }
  resultsRoot.innerHTML = html;
}

/* ─── Fetch Stacks ─── */
async function fetchStacks(goal) {
  _lastGoal = goal;
  renderSkeleton();

  try {
    var res = await fetch('/stack-recommend?goal=' + encodeURIComponent(goal));
    if (!res.ok) throw new Error('Failed to load.');
    var data = await res.json();
    _lastResponse = data;
    _lastGoalLabel = data.goal_label || goal;
    renderStacks(data, goal);
  } catch (err) {
    resultsRoot.innerHTML = '<div class="empty-state"><p>Could not load recommendations.</p></div>';
  }
}

/* ─── Copy protocol ─── */
function copyProtocol(el, name) {
  // Find the protocol text from the card
  var card = el.closest('.stack-card');
  var body = card && card.querySelector('.stack-body-inner');
  if (!body) return;
  // Get visible text, clean up
  var text = body.textContent || body.innerText || '';
  text = name + '\n' + '='.repeat(name.length) + '\n\n' + text.trim();
  navigator.clipboard.writeText(text).then(function () {
    if (typeof showToast === 'function') showToast('Protocol copied', '📋');
  }).catch(function () {
    // Fallback
    var ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    if (typeof showToast === 'function') showToast('Protocol copied', '📋');
  });
}

/* ─── Render one stack card ─── */
function renderStackCard(r, saved) {
  var stack = r.stack || [];
  var name = stackName(r);
  var score = r.score || 0;
  var tier = r.evidence_tier || 'LIMITED';
  var rationale = r.rationale || [];
  var tierTags = r.tier_tags || [];
  var deep = r.deep_research || {};
  var protocol = r.protocol || null;
  var isSaved = saved !== undefined ? saved : isStackSaved(r);

  var html = '<div class="stack-card" data-stack-name="' + escapeHtml(name) + '">';

  html += '<button class="stack-trigger" onclick="toggleStack(this)">';
  html += '<span class="stack-trigger-left">';
  html += '<span class="stack-name">' + escapeHtml(name) + '</span>';
  html += '<span class="stack-badges">';
  html += '<span class="badge badge-score">' + score + '</span>';
  html += '<span class="badge" style="background:rgba(90,200,250,0.1);color:#5ac8fa">' + escapeHtml(tier) + '</span>';
  for (var t = 0; t < tierTags.length; t++) {
    html += badgeTier(tierTags[t].tier || 'D');
  }
  html += '</span></span>';
  html += '<span class="save-btn' + (isSaved ? ' saved' : '') + '" onclick="event.stopPropagation();toggleSave(this, \'' + escapeHtml(name) + '\')" title="' + (isSaved ? 'Unsave' : 'Save') + '">' +
    (isSaved ? '&#9733;' : '&#9734;') + '</span>';
  html += '<svg class="stack-chevron" viewBox="0 0 18 18" fill="none"><path d="M4.5 6.75L9 11.25L13.5 6.75" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  html += '</button>';

  html += '<div class="stack-body"><div class="stack-body-inner">';

  if (rationale.length) {
    html += '<div class="section-block"><h4>Rationale</h4><ul>';
    for (var j = 0; j < rationale.length; j++) {
      html += '<li>' + escapeHtml(rationale[j]) + '</li>';
    }
    html += '</ul></div>';
  }

  var mechMap = deep.mechanism_map || [];
  if (mechMap.length) {
    html += '<div class="section-block"><h4>How each works</h4>';
    for (var m = 0; m < mechMap.length; m++) {
      var mp = mechMap[m];
      html += '<div class="mech-item">' +
        '<span class="mech-name">' + escapeHtml(mp.peptide) + '</span>' +
        badgeTier(mp.evidence_tier || 'D') +
        '<span class="mech-desc">' + escapeHtml(mp.what_it_does || '') + '</span></div>';
    }
    html += '</div>';
  }

  var risks = deep.risk_profile || [];
  if (risks.length) {
    html += '<div class="section-block"><h4>Risk considerations</h4><ul>';
    for (var k = 0; k < risks.length; k++) {
      html += '<li><strong>' + escapeHtml(risks[k].risk_type || '') + ':</strong> ' +
        escapeHtml(risks[k].detail || '') + ' <em>(' + escapeHtml(risks[k].severity || '') + ')</em></li>';
    }
    html += '</ul></div>';
  }

  var gaps = deep.evidence_gaps || [];
  if (gaps.length) {
    html += '<div class="section-block"><h4>Evidence gaps</h4><ul>';
    for (var g = 0; g < gaps.length; g++) {
      html += '<li>' + escapeHtml(gaps[g].gap || '') + '</li>';
    }
    html += '</ul></div>';
  }

  if (protocol) {
    html += '<div class="section-block"><h4 style="color:var(--primary)">Protocol</h4>';
    if (protocol.cycle_weeks > 0 || protocol.off_weeks > 0) {
      html += '<div class="cycle-meta">';
      if (protocol.cycle_weeks > 0) html += '<span><strong>Cycle:</strong> ' + protocol.cycle_weeks + ' weeks</span>';
      if (protocol.off_weeks > 0) html += '<span><strong>Off:</strong> ' + protocol.off_weeks + ' weeks</span>';
      html += '</div>';
    }
    var phases = protocol.phases || [];
    for (var p = 0; p < phases.length; p++) {
      var ph = phases[p];
      html += '<div class="protocol-phase">' +
        '<div class="phase-head">' +
          '<span class="phase-label">Phase ' + (ph.phase || (p + 1)) + '</span>' +
          '<span class="phase-weeks">Weeks ' + escapeHtml(ph.weeks || '') + '</span>' +
        '</div>' +
        '<div class="phase-desc">' + escapeHtml(ph.protocol || '') + '</div>' +
        (ph.dosing_details ? '<div class="phase-meta"><strong>Dosing:</strong> ' + escapeHtml(ph.dosing_details) + '</div>' : '') +
        (ph.timing ? '<div class="phase-meta"><strong>Timing:</strong> ' + escapeHtml(ph.timing) + '</div>' : '') +
      '</div>';
    }
    if (protocol.post_cycle) {
      html += '<div class="post-cycle-block">' +
        '<div class="phase-head"><span class="phase-label" style="color:var(--warning)">Post-Cycle</span></div>' +
        '<div class="phase-desc">' + escapeHtml(protocol.post_cycle) + '</div></div>';
    }
    var protoSources = protocol.sources || [];
    if (protoSources.length) {
      html += '<div style="margin-top:8px"><h4 style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--ink-tertiary);margin:0 0 4px">Protocol sources</h4><ul>';
      for (var s = 0; s < protoSources.length; s++) {
        html += '<li style="font-size:0.74rem;color:var(--ink-tertiary);margin-bottom:3px">' + escapeHtml(protoSources[s]) + '</li>';
      }
      html += '</ul></div>';
    }
    if (protocol.evidence_summary) {
      html += '<div class="evidence-note"><div class="phase-desc"><strong style="color:var(--warning);font-weight:600">Evidence summary:</strong> ' + escapeHtml(protocol.evidence_summary) + '</div></div>';
    }
    html += '</div>';
  } else {
    html += '<div class="section-block"><h4 style="color:var(--ink-tertiary)">Protocol</h4><p style="font-size:0.78rem;color:var(--ink-tertiary)">No protocol data for this combination.</p></div>';
  }

  // Copy button + Sources
  html += '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
    '<button class="copy-btn" onclick="copyProtocol(this,\'' + escapeHtml(name) + '\')">Copy protocol</button>';

  var sources = r.sources || [];
  if (sources.length) {
    html += '<div class="sources-mini" style="flex:1">';
    for (var u = 0; u < sources.length; u++) {
      html += '<a class="source-chip" href="' + escapeHtml(sources[u].url) + '" target="_blank">' + escapeHtml(sources[u].label) + '</a>';
    }
    html += '</div>';
  }

  html += '</div>';

  html += '</div></div></div>';
  return html;
}

/* ─── Symptom Search ─── */

async function doSymptomSearch() {
  var input = document.getElementById('symptom_search_input');
  var resultsContainer = document.getElementById('symptom_search_results');
  var statusEl = document.getElementById('symptom_search_status');
  var query = (input && input.value.trim()) || '';

  if (!query) {
    if (statusEl) statusEl.textContent = 'Please describe what you are looking for.';
    return;
  }

  resultsContainer.style.display = 'block';
  resultsContainer.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span><span></span><span></span></div>';
  if (statusEl) statusEl.textContent = 'Searching for "' + escapeHtml(query) + '"...';

  try {
    var res = await fetch('/symptom-search?q=' + encodeURIComponent(query));
    if (!res.ok) {
      var errData = await res.json().catch(function () { return {}; });
      throw new Error(errData.error || 'Search failed.');
    }
    var data = await res.json();

    if (statusEl) {
      statusEl.textContent = 'Found ' + data.total_peptides_matched + ' peptide(s) and ' + data.total_stacks_matched + ' stack pairing(s) for "' + escapeHtml(query) + '".';
    }

    resultsContainer.innerHTML = renderSymptomResults(data);
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    resultsContainer.innerHTML = '<div class="empty-state"><p>' + escapeHtml(err.message || 'Could not complete search.') + '</p><p style="font-size:0.78rem">Try simpler terms like "fat loss", "sleep", "anxiety", or a specific condition.</p></div>';
    if (statusEl) statusEl.textContent = 'Could not complete search.';
  }
}

function renderSymptomResults(data) {
  var html = '';

  var conditions = data.matched_conditions || [];
  if (conditions.length) {
    html += '<div style="margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">' +
      '<span style="font-size:0.68rem;color:var(--ink-tertiary);font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Matched:</span>';
    for (var c = 0; c < Math.min(conditions.length, 8); c++) {
      html += '<span class="badge" style="background:var(--surface-2);color:var(--ink-muted);border:1px solid var(--hairline-strong)">' +
        escapeHtml(conditions[c]) + '</span>';
    }
    html += '</div>';
  }

  var peptides = data.peptide_results || [];
  if (peptides.length) {
    html += '<div class="results-header"><h3 class="results-title">Matched Peptides</h3></div>';
    html += '<div class="stack-results">';
    for (var i = 0; i < peptides.length; i++) {
      html += renderSymptomPeptideCard(peptides[i], i);
    }
    html += '</div>';
  }

  var stacks = data.matched_stacks || [];
  if (stacks.length) {
    html += '<div class="results-header" style="margin-top:16px"><h3 class="results-title">Recommended Stack Pairings</h3></div>';
    html += '<div class="stack-results">';
    for (var s = 0; s < stacks.length; s++) {
      html += renderSymptomStackCard(stacks[s], s);
    }
    html += '</div>';
  }

  if (!peptides.length && !stacks.length) {
    html += '<div class="empty-state"><p>No matches found for your search.</p><p style="font-size:0.78rem">Try simpler terms like "fat loss", "sleep", "anxiety", or a specific condition name.</p></div>';
  }

  return html;
}

function renderSymptomPeptideCard(pep, index) {
  var name = pep.peptide || '';
  var reason = pep.reason || '';
  var category = pep.category || '';
  var snapshot = pep.snapshot || {};
  var sk = pep.stack_knowledge || {};
  var tier = sk.tier || 'D';
  var effects = sk.effects || [];

  var html = '<div class="stack-card" style="animation:fadeSlide 0.4s ease-out both;animation-delay:' + (index * 0.04) + 's">';
  html += '<button class="stack-trigger" onclick="toggleStack(this)">';
  html += '<span class="stack-trigger-left">';
  html += '<span class="stack-name">' + escapeHtml(name) + '</span>';
  html += '<span class="stack-badges">';
  html += badgeTier(tier);
  if (category) {
    html += '<span class="badge" style="background:rgba(90,200,250,0.08);color:#5ac8fa">' + escapeHtml(category) + '</span>';
  }
  html += '</span></span>';
  html += '<svg class="stack-chevron" viewBox="0 0 18 18" fill="none"><path d="M4.5 6.75L9 11.25L13.5 6.75" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  html += '</button>';

  html += '<div class="stack-body"><div class="stack-body-inner">';

  html += '<div class="section-block"><h4>Why it matches</h4>' +
    '<p>' + escapeHtml(reason) + '</p></div>';

  if (sk.summary) {
    html += '<div class="section-block"><h4>Evidence summary</h4>' +
      '<p>' + escapeHtml(sk.summary) + '</p></div>';
  }

  if (snapshot.primary_effect) {
    html += '<div class="section-block"><h4>Primary effect</h4>' +
      '<p>' + escapeHtml(snapshot.primary_effect) + '</p></div>';
  }
  if (snapshot.mechanism_pathway) {
    html += '<div class="section-block"><h4>How it works</h4>' +
      '<p>' + escapeHtml(snapshot.mechanism_pathway) + '</p></div>';
  }
  if (snapshot.expected_body_outcomes) {
    html += '<div class="section-block"><h4>Expected outcomes</h4>' +
      '<p>' + escapeHtml(snapshot.expected_body_outcomes) + '</p></div>';
  }

  html += '<div class="section-block"><h4>Effect profile</h4>' +
    '<div style="display:flex;gap:4px;flex-wrap:wrap">';
  for (var e = 0; e < effects.length; e++) {
    html += '<span class="badge" style="background:var(--surface-3);color:var(--ink-subtle);font-size:0.6rem">' +
      escapeHtml(effects[e].replace(/_/g, ' ')) + '</span>';
  }
  html += '</div></div>';

  html += '<div style="margin-top:8px">' +
    '<a href="/?term=' + encodeURIComponent(name) + '" class="source-chip" style="display:inline-flex;gap:6px">' +
      'Full research profile for ' + escapeHtml(name) +
    '</a></div>';

  html += '</div></div></div>';
  return html;
}

function renderSymptomStackCard(stack, index) {
  var name = stack.name || stack.stack_key || '';
  var goal = stack.goal || '';
  var relevance = stack.relevance || 0;
  var protocol = stack.protocol || {};
  var matchedPeps = stack.matched_peptides || [];

  var html = '<div class="stack-card" style="animation:fadeSlide 0.4s ease-out both;animation-delay:' + (index * 0.06) + 's">';
  html += '<button class="stack-trigger" onclick="toggleStack(this)">';
  html += '<span class="stack-trigger-left">';
  html += '<span class="stack-name">' + escapeHtml(name) + '</span>';
  html += '<span class="stack-badges">';
  html += '<span class="badge badge-score">' + Math.round(relevance * 100) + '% match</span>';
  html += '</span></span>';
  html += '<svg class="stack-chevron" viewBox="0 0 18 18" fill="none"><path d="M4.5 6.75L9 11.25L13.5 6.75" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  html += '</button>';

  html += '<div class="stack-body"><div class="stack-body-inner">';

  if (goal) {
    html += '<div class="section-block"><h4>Goal</h4><p>' + escapeHtml(goal) + '</p></div>';
  }

  html += '<div class="section-block"><h4>Contains</h4>' +
    '<div style="display:flex;gap:4px;flex-wrap:wrap">';
  for (var p = 0; p < matchedPeps.length; p++) {
    html += '<span class="badge" style="background:var(--primary-soft);color:var(--primary)">' +
      escapeHtml(matchedPeps[p]) + '</span>';
  }
  html += '</div></div>';

  if (protocol.cycle_weeks > 0 || protocol.off_weeks > 0) {
    html += '<div class="cycle-meta">';
    if (protocol.cycle_weeks > 0) html += '<span><strong>Cycle:</strong> ' + protocol.cycle_weeks + ' weeks</span>';
    if (protocol.off_weeks > 0) html += '<span><strong>Off:</strong> ' + protocol.off_weeks + ' weeks</span>';
    html += '</div>';
  }

  var phases = protocol.phases || [];
  for (var ph = 0; ph < phases.length; ph++) {
    var pdata = phases[ph];
    html += '<div class="protocol-phase">' +
      '<div class="phase-head">' +
        '<span class="phase-label">Phase ' + (pdata.phase || (ph + 1)) + '</span>' +
        '<span class="phase-weeks">Weeks ' + escapeHtml(pdata.weeks || '') + '</span>' +
      '</div>' +
      '<div class="phase-desc">' + escapeHtml(pdata.protocol || '') + '</div>' +
      (pdata.dosing_details ? '<div class="phase-meta"><strong>Dosing:</strong> ' + escapeHtml(pdata.dosing_details) + '</div>' : '') +
      (pdata.timing ? '<div class="phase-meta"><strong>Timing:</strong> ' + escapeHtml(pdata.timing) + '</div>' : '') +
    '</div>';
  }
  if (protocol.post_cycle) {
    html += '<div class="post-cycle-block">' +
      '<div class="phase-head"><span class="phase-label" style="color:var(--warning)">Post-Cycle</span></div>' +
      '<div class="phase-desc">' + escapeHtml(protocol.post_cycle) + '</div></div>';
  }
  if (protocol.evidence_summary) {
    html += '<div class="evidence-note"><div class="phase-desc"><strong style="color:var(--warning);font-weight:600">Evidence:</strong> ' + escapeHtml(protocol.evidence_summary) + '</div></div>';
  }

  html += '</div></div></div>';
  return html;
}

/* ─── Filter stacks ─── */
function filterStacks(val) {
  var q = val.toLowerCase().trim();
  var cards = resultsRoot.querySelectorAll('.stack-card');
  for (var i = 0; i < cards.length; i++) {
    var name = cards[i].getAttribute('data-stack-name') || '';
    cards[i].style.display = (!q || name.toLowerCase().indexOf(q) > -1) ? '' : 'none';
  }
}

/* ─── Render Stacks ─── */
function renderStacks(data, currentGoal) {
  var recs = data.recommendations || [];
  var saved = loadSavedStacks();
  var html = '';

  // ─── Saved stacks section ───
  if (saved.length) {
    html += '<div class="saved-section"><div class="saved-header">' +
      '<h3 class="saved-title">&#9733; Saved Stacks</h3>' +
      '<span class="saved-count">' + saved.length + '</span></div>';
    for (var si = 0; si < saved.length; si++) {
      html += renderStackCard(saved[si], true);
    }
    html += '</div>';
  }

  // ─── Current results ───
  if (!recs.length) {
    html += '<div class="empty-state"><p>No stacks found for this goal.</p></div>';
  } else {
    html += '<div class="results-header"><h3 class="results-title">' + escapeHtml(_lastGoalLabel || currentGoal || '') + '</h3></div>';
    for (var i = 0; i < recs.length; i++) {
      html += renderStackCard(recs[i]);
    }
  }

  resultsRoot.innerHTML = html;
}

/* ─── Toggle stack body ─── */
function toggleStack(btn) {
  btn.parentElement.classList.toggle('open');
}

/* ─── Save / Unsave ─── */
function toggleSave(el, name) {
  var isSaved = el.classList.contains('saved');

  if (isSaved) {
    removeStackFromLocal({ stack: name.split(' + ') });
    if (typeof showToast === 'function') showToast('Stack unsaved', '☆');
  } else {
    var recs = (_lastResponse && _lastResponse.recommendations) || [];
    var found = null;
    for (var i = 0; i < recs.length; i++) {
      if (stackName(recs[i]) === name) { found = recs[i]; break; }
    }
    if (found) {
      saveStackToLocal(found);
      if (typeof showToast === 'function') showToast('Stack saved', '★');
    }
  }

  renderStacks(_lastResponse || { recommendations: [] }, _lastGoal);
}

/* ─── Dropdown change ─── */
document.addEventListener('DOMContentLoaded', function () {
  var sel = document.getElementById('goal_select');
  if (!sel) return;
  sel.addEventListener('change', function () {
    fetchStacks(this.value);
  });

  // Stack filter input
  var filter = document.getElementById('stack_filter');
  if (filter) {
    filter.addEventListener('input', function () { filterStacks(this.value); });
  }

  // Symptom search
  var symptomInput = document.getElementById('symptom_search_input');
  var symptomBtn = document.getElementById('symptom_search_btn');
  if (symptomInput) {
    symptomInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); doSymptomSearch(); }
    });
  }
  if (symptomBtn) {
    symptomBtn.addEventListener('click', function (e) { e.preventDefault(); doSymptomSearch(); });
  }

  fetchStacks(sel.value);
});
