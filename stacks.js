/* ─── State ─── */
var currentGoal = null;
var resultsRoot = document.getElementById('stack_results');

/* ─── Helpers ─── */
function escapeHtml(v) {
  return String(v || '').replace(/[&<>"']/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
  });
}

function tierPill(tier) {
  return '<span class="pill pill-tier-' + tier.toLowerCase() + '">' + escapeHtml(tier) + '</span>';
}

/* ─── Goal Selection ─── */
function selectGoal(goal) {
  currentGoal = goal;
  var cards = document.querySelectorAll('.goal-card');
  for (var i = 0; i < cards.length; i++) {
    cards[i].classList.toggle('selected', cards[i].dataset.goal === goal);
  }
  fetchStacks(goal);
}

/* ─── Fetch Stacks ─── */
async function fetchStacks(goal) {
  resultsRoot.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span><span></span><span></span></div>';

  try {
    var res = await fetch('/stack-recommend?goal=' + encodeURIComponent(goal));
    if (!res.ok) throw new Error('Failed to load recommendations.');
    var data = await res.json();
    renderStacks(data);
  } catch (err) {
    resultsRoot.innerHTML = '<div class="empty-state"><p>Could not load recommendations. Try again.</p></div>';
  }
}

/* ─── Render Stacks ─── */
function renderStacks(data) {
  var recs = data.recommendations || [];
  if (!recs.length) {
    resultsRoot.innerHTML = '<div class="empty-state"><p>No stack recommendations found for this goal.</p></div>';
    return;
  }

  var html = '';
  for (var i = 0; i < recs.length; i++) {
    var r = recs[i];
    var stack = r.stack || [];
    var stackName = stack.join(' + ') || 'Unknown stack';
    var score = r.score || 0;
    var tier = r.evidence_tier || 'LIMITED';
    var rationale = r.rationale || [];
    var tierTags = r.tier_tags || [];
    var deep = r.deep_research || {};
    var protocol = r.protocol || null;

    html += '<div class="stack-result">';

    // Header (collapsible)
    html += '<div class="stack-header" onclick="toggleStack(this)" role="button" tabindex="0">';
    html += '<div class="stack-header-left">';
    html += '<span class="stack-name">' + escapeHtml(stackName) + '</span>';
    html += '<div class="stack-pills">';
    html += '<span class="pill pill-score">Score: ' + score + '</span>';
    html += '<span class="pill pill-score" style="background:rgba(90,200,250,0.1);color:#5ac8fa">' + escapeHtml(tier) + '</span>';
    for (var t = 0; t < tierTags.length; t++) {
      html += tierPill(tierTags[t].tier || 'D');
    }
    html += '</div>';
    html += '</div>';
    html += '<span class="stack-expand-icon">&#9660;</span>';
    html += '</div>';

    // Body (collapsible)
    html += '<div class="stack-body">';
    html += '<div class="stack-body-inner">';

    // Rationale section
    if (rationale.length) {
      html += '<div class="stack-section"><h4>Rationale</h4><ul>';
      for (var j = 0; j < rationale.length; j++) {
        html += '<li>' + escapeHtml(rationale[j]) + '</li>';
      }
      html += '</ul></div>';
    }

    // Mechanism map
    var mechMap = deep.mechanism_map || [];
    if (mechMap.length) {
      html += '<div class="stack-section"><h4>How each peptide works</h4>';
      for (var m = 0; m < mechMap.length; m++) {
        var mp = mechMap[m];
        html += '<div style="margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid var(--hairline)">' +
          '<strong style="font-size:0.85rem;color:var(--ink)">' + escapeHtml(mp.peptide) + '</strong> ' +
          tierPill(mp.evidence_tier || 'D') +
          '<p style="margin:4px 0 0;font-size:0.8rem;color:var(--ink-muted);line-height:1.45">' +
          escapeHtml(mp.what_it_does || '') + '</p></div>';
      }
      html += '</div>';
    }

    // Risk flags
    var risks = deep.risk_profile || [];
    if (risks.length) {
      html += '<div class="stack-section"><h4>Risk considerations</h4><ul>';
      for (var k = 0; k < risks.length; k++) {
        html += '<li><strong>' + escapeHtml(risks[k].risk_type || '') + ':</strong> ' +
          escapeHtml(risks[k].detail || '') + ' <em>(' + escapeHtml(risks[k].severity || '') + ')</em></li>';
      }
      html += '</ul></div>';
    }

    // Evidence gaps
    var gaps = deep.evidence_gaps || [];
    if (gaps.length) {
      html += '<div class="stack-section"><h4>Evidence gaps</h4><ul>';
      for (var g = 0; g < gaps.length; g++) {
        html += '<li>' + escapeHtml(gaps[g].gap || '') + '</li>';
      }
      html += '</ul></div>';
    }

    // === PROTOCOL SECTION ===
    if (protocol) {
      html += '<div class="stack-section"><h4 style="color:var(--primary)">Protocol</h4>';

      // Cycle info
      html += '<div class="protocol-meta">';
      if (protocol.cycle_weeks > 0) {
        html += '<span><strong>Cycle:</strong> ' + protocol.cycle_weeks + ' weeks</span>';
      }
      if (protocol.off_weeks > 0) {
        html += '<span><strong>Off:</strong> ' + protocol.off_weeks + ' weeks</span>';
      }
      html += '</div>';

      // Protocol phases
      var phases = protocol.phases || [];
      for (var p = 0; p < phases.length; p++) {
        var ph = phases[p];
        html += '<div class="protocol-phase">' +
          '<div class="phase-label">Phase ' + (ph.phase || (p + 1)) + ' &mdash; Weeks ' + escapeHtml(ph.weeks || '') + '</div>' +
          '<div class="phase-text">' + escapeHtml(ph.protocol || '') + '</div>' +
          (ph.dosing_details ? '<div class="phase-detail"><strong>Dosing:</strong> ' + escapeHtml(ph.dosing_details) + '</div>' : '') +
          (ph.timing ? '<div class="phase-detail"><strong>Timing:</strong> ' + escapeHtml(ph.timing) + '</div>' : '') +
        '</div>';
      }

      // Post-cycle
      if (protocol.post_cycle) {
        html += '<div class="protocol-phase" style="margin-top:8px;border-left:2px solid var(--warning)">' +
          '<div class="phase-label" style="color:var(--warning)">Post-Cycle</div>' +
          '<div class="phase-text">' + escapeHtml(protocol.post_cycle) + '</div></div>';
      }

      // Sources
      var protoSources = protocol.sources || [];
      if (protoSources.length) {
        html += '<div style="margin-top:10px"><h4 style="font-size:0.78rem;color:var(--ink-tertiary);margin:0 0 6px">Protocol sources</h4><ul>';
        for (var s = 0; s < protoSources.length; s++) {
          html += '<li style="font-size:0.75rem;color:var(--ink-tertiary);margin-bottom:3px">' + escapeHtml(protoSources[s]) + '</li>';
        }
        html += '</ul></div>';
      }

      // Evidence summary
      if (protocol.evidence_summary) {
        html += '<div style="margin-top:8px;padding:10px;border-radius:var(--radius-sm);background:rgba(245,166,35,0.06);border:1px solid rgba(245,166,35,0.12)">' +
          '<strong style="font-size:0.75rem;color:var(--warning)">Evidence summary:</strong> ' +
          '<span style="font-size:0.78rem;color:var(--ink-subtle)">' + escapeHtml(protocol.evidence_summary) + '</span></div>';
      }

      html += '</div>'; // end protocol stack-section
    } else {
      // No protocol available
      html += '<div class="stack-section"><h4 style="color:var(--ink-tertiary)">Protocol</h4>' +
        '<p style="color:var(--ink-tertiary);font-size:0.8rem">Detailed protocol data not yet available for this specific combination. Evidence summaries above still apply.</p></div>';
    }

    // Sources
    var sources = r.sources || [];
    if (sources.length) {
      html += '<div class="stack-section"><h4>Sources</h4><div class="source-grid" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">';
      for (var u = 0; u < sources.length; u++) {
        html += '<a class="source-link" href="' + escapeHtml(sources[u].url) + '" target="_blank" rel="noopener" style="font-size:0.78rem;padding:8px 12px">' + escapeHtml(sources[u].label) + '</a>';
      }
      html += '</div></div>';
    }

    html += '</div></div>'; // end body-inner, end body
    html += '</div>'; // end stack-result
  }

  resultsRoot.innerHTML = html;
}

/* ─── Toggle Stack Details ─── */
function toggleStack(header) {
  header.classList.toggle('open');
  var body = header.nextElementSibling;
  if (body) body.classList.toggle('open');
}

/* ─── Init — select first goal on load ─── */
document.addEventListener('DOMContentLoaded', function () {
  var first = document.querySelector('.goal-card');
  if (first) selectGoal(first.dataset.goal);
});
