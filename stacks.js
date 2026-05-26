/* ─── State ─── */
var resultsRoot = document.getElementById('stack_results');

/* ─── Helpers ─── */
function escapeHtml(v) {
  return String(v || '').replace(/[&<>"']/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
  });
}

function badgeTier(tier) {
  return '<span class="badge badge-tier-' + tier.toLowerCase() + '">' + escapeHtml(tier) + '</span>';
}

/* ─── Fetch Stacks ─── */
async function fetchStacks(goal) {
  resultsRoot.innerHTML = '<div class="loading-wrap"><div class="loading-dots"><span></span><span></span><span></span><span></span><span></span></div></div>';

  try {
    var res = await fetch('/stack-recommend?goal=' + encodeURIComponent(goal));
    if (!res.ok) throw new Error('Failed to load.');
    var data = await res.json();
    renderStacks(data);
  } catch (err) {
    resultsRoot.innerHTML = '<div class="empty-state"><p>Could not load recommendations.</p></div>';
  }
}

/* ─── Render Stacks ─── */
function renderStacks(data) {
  var recs = data.recommendations || [];
  if (!recs.length) {
    resultsRoot.innerHTML = '<div class="empty-state"><p>No stacks found for this goal.</p></div>';
    return;
  }

  var html = '';
  for (var i = 0; i < recs.length; i++) {
    var r = recs[i];
    var stack = r.stack || [];
    var stackName = stack.join(' + ') || 'Unknown';
    var score = r.score || 0;
    var tier = r.evidence_tier || 'LIMITED';
    var rationale = r.rationale || [];
    var tierTags = r.tier_tags || [];
    var deep = r.deep_research || {};
    var protocol = r.protocol || null;

    html += '<div class="stack-card">';

    // Trigger
    html += '<button class="stack-trigger" onclick="toggleStack(this)">';
    html += '<span class="stack-trigger-left">';
    html += '<span class="stack-name">' + escapeHtml(stackName) + '</span>';
    html += '<span class="stack-badges">';
    html += '<span class="badge badge-score">' + score + '</span>';
    html += '<span class="badge" style="background:rgba(90,200,250,0.1);color:#5ac8fa">' + escapeHtml(tier) + '</span>';
    for (var t = 0; t < tierTags.length; t++) {
      html += badgeTier(tierTags[t].tier || 'D');
    }
    html += '</span>';
    html += '</span>';
    html += '<svg class="stack-chevron" viewBox="0 0 18 18" fill="none"><path d="M4.5 6.75L9 11.25L13.5 6.75" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    html += '</button>';

    // Body
    html += '<div class="stack-body"><div class="stack-body-inner">';

    // Rationale
    if (rationale.length) {
      html += '<div class="section-block"><h4>Rationale</h4><ul>';
      for (var j = 0; j < rationale.length; j++) {
        html += '<li>' + escapeHtml(rationale[j]) + '</li>';
      }
      html += '</ul></div>';
    }

    // Mechanism
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

    // Risks
    var risks = deep.risk_profile || [];
    if (risks.length) {
      html += '<div class="section-block"><h4>Risk considerations</h4><ul>';
      for (var k = 0; k < risks.length; k++) {
        html += '<li><strong>' + escapeHtml(risks[k].risk_type || '') + ':</strong> ' +
          escapeHtml(risks[k].detail || '') + ' <em>(' + escapeHtml(risks[k].severity || '') + ')</em></li>';
      }
      html += '</ul></div>';
    }

    // Evidence gaps
    var gaps = deep.evidence_gaps || [];
    if (gaps.length) {
      html += '<div class="section-block"><h4>Evidence gaps</h4><ul>';
      for (var g = 0; g < gaps.length; g++) {
        html += '<li>' + escapeHtml(gaps[g].gap || '') + '</li>';
      }
      html += '</ul></div>';
    }

    // === PROTOCOL ===
    if (protocol) {
      html += '<div class="section-block"><h4 style="color:var(--primary)">Protocol</h4>';

      // Cycle meta
      html += '<div class="cycle-meta">';
      if (protocol.cycle_weeks > 0) html += '<span><strong>Cycle:</strong> ' + protocol.cycle_weeks + ' weeks</span>';
      if (protocol.off_weeks > 0) html += '<span><strong>Off:</strong> ' + protocol.off_weeks + ' weeks</span>';
      html += '</div>';

      // Phases
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

      // Post-cycle
      if (protocol.post_cycle) {
        html += '<div class="post-cycle-block">' +
          '<div class="phase-head"><span class="phase-label" style="color:var(--warning)">Post-Cycle</span></div>' +
          '<div class="phase-desc">' + escapeHtml(protocol.post_cycle) + '</div></div>';
      }

      // Protocol sources
      var protoSources = protocol.sources || [];
      if (protoSources.length) {
        html += '<div style="margin-top:8px"><h4 style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--ink-tertiary);margin:0 0 4px">Protocol sources</h4><ul>';
        for (var s = 0; s < protoSources.length; s++) {
          html += '<li style="font-size:0.72rem;color:var(--ink-tertiary);margin-bottom:2px">' + escapeHtml(protoSources[s]) + '</li>';
        }
        html += '</ul></div>';
      }

      // Evidence summary
      if (protocol.evidence_summary) {
        html += '<div class="evidence-note"><div class="phase-desc"><strong style="color:var(--warning)">Evidence summary:</strong> ' + escapeHtml(protocol.evidence_summary) + '</div></div>';
      }

      html += '</div>'; // end protocol section
    } else {
      html += '<div class="section-block"><h4 style="color:var(--ink-tertiary)">Protocol</h4><p style="font-size:0.78rem;color:var(--ink-tertiary)">No protocol data for this combination.</p></div>';
    }

    // Sources
    var sources = r.sources || [];
    if (sources.length) {
      html += '<div class="section-block"><h4>Sources</h4><div class="sources-mini">';
      for (var u = 0; u < sources.length; u++) {
        html += '<a class="source-chip" href="' + escapeHtml(sources[u].url) + '" target="_blank">' + escapeHtml(sources[u].label) + '</a>';
      }
      html += '</div></div>';
    }

    html += '</div></div>'; // end body-inner, body
    html += '</div>'; // end stack-card
  }

  resultsRoot.innerHTML = html;
}

/* ─── Toggle ─── */
function toggleStack(btn) {
  btn.parentElement.classList.toggle('open');
}

/* ─── Dropdown change ─── */
document.addEventListener('DOMContentLoaded', function () {
  var sel = document.getElementById('goal_select');
  if (!sel) return;
  sel.addEventListener('change', function () {
    fetchStacks(this.value);
  });
  fetchStacks(sel.value);
});
