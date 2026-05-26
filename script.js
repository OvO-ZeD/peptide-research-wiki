/* ─── State ─── */
var resultsRoot = null;

/* ─── Particles ─── */
(function initParticles() {
  var canvas = document.getElementById('particles');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var particles = [];
  var w, h;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (var i = 0; i < 100; i++) {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 2 + 0.5,
      o: Math.random() * 0.3 + 0.05,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(217, 56, 56, ' + p.o + ')';
      ctx.fill();
    }
    for (var i = 0; i < particles.length; i++) {
      for (var j = i + 1; j < particles.length; j++) {
        var dx = particles[i].x - particles[j].x;
        var dy = particles[i].y - particles[j].y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = 'rgba(217, 56, 56, ' + (0.05 * (1 - dist / 150)) + ')';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

/* ─── 3D Tilt Effect ─── */
(function initTilt() {
  var ticking = false;
  document.addEventListener('mouseover', function (e) {
    var card = e.target.closest('.panel, .trial-item, .snapshot-item, .data-list li, .article-list li, .source-link, .search-section, .hero');
    if (!card) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var onMove = function (ev) {
      if (!ticking) {
        requestAnimationFrame(function () {
          var r = card.getBoundingClientRect();
          var x = (ev.clientX - r.left) / r.width - 0.5;
          var y = (ev.clientY - r.top) / r.height - 0.5;
          var tiltX = y * -10;
          var tiltY = x * 10;
          card.style.setProperty('--rx', tiltX + 'deg');
          card.style.setProperty('--ry', tiltY + 'deg');
          card.style.transform = 'perspective(600px) rotateX(var(--rx)) rotateY(var(--ry)) translateZ(4px)';
          card.style.transition = 'transform 0.06s linear';
          ticking = false;
        });
        ticking = true;
      }
    };

    // immediate first frame
    (function firstFrame() {
      var r = card.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = 'perspective(600px) rotateX(' + (y * -10) + 'deg) rotateY(' + (x * 10) + 'deg) translateZ(4px)';
      card.style.transition = 'transform 0.06s linear';
    })();

    document.addEventListener('mousemove', onMove);

    card.addEventListener('mouseleave', function reset() {
      document.removeEventListener('mousemove', onMove);
      card.style.transform = 'perspective(600px) rotateX(0deg) rotateY(0deg) translateZ(0)';
      card.style.transition = 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
    }, { once: true });
  }, true);
})();

/* ─── Status ─── */
function setStatus(message, type) {
  var status = document.getElementById('status_message');
  if (!status) return;
  status.textContent = message;
  status.className = 'status-message ' + (type || '');
}

/* ─── Helpers ─── */
function escapeHtml(v) {
  return String(v || '').replace(/[&<>"']/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
  });
}

function makePanel(title, content, extraClass) {
  return '<section class="panel' + (extraClass ? ' ' + extraClass : '') + '"><h2>' + escapeHtml(title) + '</h2>' + content + '</section>';
}

/* ─── Renderers ─── */
function renderSnapshot(snapshot) {
  if (!snapshot) return '';
  var keys = ['primary_effect', 'mechanism_pathway', 'expected_body_outcomes', 'clinical_context'];
  var labels = { primary_effect: 'Primary effect', mechanism_pathway: 'Mechanism / pathway', expected_body_outcomes: 'Expected outcomes', clinical_context: 'Clinical context' };
  return '<div class="snapshot-grid">' + keys.map(function (k) {
    return '<div class="snapshot-item"><strong>' + escapeHtml(labels[k]) + '</strong><p>' + escapeHtml(snapshot[k] || '') + '</p></div>';
  }).join('') + '</div>';
}

function renderTrials(trials) {
  if (!trials || !trials.length) return '<p class="empty">No clinical trials found.</p>';
  return '<div class="trial-list">' + trials.slice(0, 4).map(function (t) {
    var title = t.title || 'Untitled study';
    var status = t.status || 'Unknown';
    var summary = t.lay_summary || '';
    return '<article class="trial-item"><h3>' + escapeHtml(title) + '</h3><p class="meta">' + escapeHtml(status) + '</p><p>' + escapeHtml(summary) + '</p><a href="' + escapeHtml(t.link) + '" target="_blank" rel="noopener">View trial details</a></article>';
  }).join('') + '</div>';
}

function renderArticles(articles) {
  if (!articles || !articles.length) return '<p class="empty">No PubMed articles returned.</p>';
  return '<ol class="article-list">' + articles.slice(0, 5).map(function (a) {
    return '<li><a href="' + escapeHtml(a.link) + '" target="_blank" rel="noopener">' + escapeHtml(a.title || 'Untitled') + '</a><span>' + escapeHtml(a.pubdate || '') + '</span></li>';
  }).join('') + '</ol>';
}

function renderPdb(structures) {
  if (!structures || !structures.length) return '<p class="empty">No protein structures found.</p>';
  return '<div class="pdb-list">' + structures.slice(0, 3).map(function (s) {
    var label = s.structure_id || s.id || 'PDB entry';
    var desc = s.title || '';
    return '<a class="pdb-item" href="' + escapeHtml(s.url || '#') + '" target="_blank" rel="noopener">' +
      '<strong>' + escapeHtml(label) + '</strong>' +
      (desc ? '<span>' + escapeHtml(desc) + '</span>' : '') +
    '</a>';
  }).join('') + '</div>';
}

function renderUniprot(data) {
  if (!data) return '';
  var html = '';
  if (data.protein_name) {
    html += '<div class="snapshot-item"><strong>Protein name</strong><p>' + escapeHtml(data.protein_name) + '</p></div>';
  }
  if (data.accession) {
    html += '<div class="snapshot-item"><strong>Accession</strong><p>' + escapeHtml(data.accession) + '</p></div>';
  }
  if (data.function) {
    html += '<div class="snapshot-item" style="grid-column:1/-1"><strong>Biological function</strong><p>' + escapeHtml(data.function.slice(0, 600)) + '</p></div>';
  }
  if (data.pharmaceutical) {
    html += '<div class="snapshot-item" style="grid-column:1/-1"><strong>Pharmaceutical role</strong><p>' + escapeHtml(data.pharmaceutical.slice(0, 500)) + '</p></div>';
  }
  if (data.biotechnology) {
    html += '<div class="snapshot-item" style="grid-column:1/-1"><strong>Biotechnology</strong><p>' + escapeHtml(data.biotechnology.slice(0, 400)) + '</p></div>';
  }
  if (data.gene) {
    html += '<div class="snapshot-item"><strong>Gene</strong><p>' + escapeHtml(data.gene) + '</p></div>';
  }
  if (data.keywords && data.keywords.length) {
    html += '<div class="snapshot-item"><strong>Keywords</strong><p>' + escapeHtml(data.keywords.slice(0, 6).join(', ')) + '</p></div>';
  }
  return html ? '<div class="snapshot-grid">' + html + '</div>' : '';
}

function renderSources(sources) {
  if (!sources || !sources.length) return '<p class="empty">No source links provided.</p>';
  return '<div class="source-grid">' + sources.map(function (s) {
    return '<a class="source-link" href="' + escapeHtml(s.url) + '" target="_blank" rel="noopener">' + escapeHtml(s.label) + '</a>';
  }).join('') + '</div>';
}

/* ─── Build Response ─── */
function buildResponse(response, title) {
  var score = response.evidence_score ? response.evidence_score.score : 'N/A';
  var tier = (response.evidence_score ? response.evidence_score.tier : 'N/A') || 'N/A';
  var topTerm = response.peptide_name || response.normalized_term || title || 'Peptide';
  var summary = response.plain_summary || response.medical_definition || 'No summary available.';
  var dotClass = tier === 'HIGH' ? 'dot-high' : tier === 'MEDIUM' ? 'dot-medium' : 'dot-low';

  var html = '';

  // Overview card
  var chemInfo = '';
  if (response.pubchem) {
    var pc = response.pubchem;
    chemInfo = '<div class="metric-row" style="margin-top:10px">';
    if (pc.formula) chemInfo += '<span class="metric-tag">Formula: ' + escapeHtml(pc.formula) + '</span>';
    if (pc.molecular_weight) chemInfo += '<span class="metric-tag">MW: ' + escapeHtml(pc.molecular_weight) + '</span>';
    if (pc.log_p) chemInfo += '<span class="metric-tag">LogP: ' + escapeHtml(pc.log_p) + '</span>';
    chemInfo += '</div>';
  }

  html += '<section class="panel overview-card">' +
    '<h3>' + escapeHtml(topTerm) + '</h3>' +
    '<p>' + escapeHtml(summary) + '</p>' + chemInfo +
    '<div class="metric-row">' +
      '<span class="metric-tag"><span class="dot ' + dotClass + '"></span>Score: ' + escapeHtml(String(score)) + '</span>' +
      '<span class="metric-tag">Tier: ' + escapeHtml(String(tier)) + '</span>' +
      '<span class="metric-tag">Reliability: ' + escapeHtml(response.reliability || 'Unknown') + '</span>' +
    '</div>' +
  '</section>';

  // Clinical snapshot
  if (response.clinical_snapshot) {
    html += makePanel('Clinical Snapshot', renderSnapshot(response.clinical_snapshot));
  }

  // PDB structures
  if (response.pdb_structures && response.pdb_structures.length) {
    html += makePanel('Protein Structures (PDB)', renderPdb(response.pdb_structures), 'panel-compact');
  }

  // UniProt
  if (response.uniprot) {
    html += makePanel('UniProt Data', renderUniprot(response.uniprot), 'panel-compact');
  }

  // Clinical Trials
  if (response.clinical_trials && response.clinical_trials.length) {
    html += makePanel('Clinical Trials', renderTrials(response.clinical_trials), 'panel-compact');
  }

  // PubMed
  if (response.top_pubmed_articles || response.pubmed_articles) {
    html += makePanel('PubMed Articles', renderArticles(response.top_pubmed_articles || response.pubmed_articles), 'panel-compact');
  }

  // Sources
  if (response.sources && response.sources.length) {
    html += makePanel('Sources', renderSources(response.sources), 'panel-compact');
  }

  return html;
}

/* ─── Fetch ─── */
async function fetchSearch(term) {
  var url = '/search?term=' + encodeURIComponent(term);
  var response = await fetch(url, { method: 'GET' });
  if (!response.ok) {
    var msg = 'Search failed with status ' + response.status;
    try {
      var data = await response.json();
      if (data && data.error) msg = data.error;
    } catch (_) {}
    throw new Error(msg);
  }
  return response.json();
}

/* ─── Loading Spinner ─── */
function showLoading() {
  return '<div class="loading-dots"><span></span><span></span><span></span><span></span><span></span></div>';
}

/* ─── Main Search ─── */
async function searchPeptide() {
  var term = document.getElementById('term_input').value.trim();
  var compare = document.getElementById('compare_input').value.trim();

  if (!term) {
    setStatus('Please enter a peptide name before searching.', 'error');
    return;
  }

  resultsRoot.innerHTML = showLoading();
  setStatus('Loading research results…', 'loading');
  document.getElementById('search_button').disabled = true;

  try {
    var primary = await fetchSearch(term);

    if (compare) {
      var secondary = await fetchSearch(compare);
      var html = '<div class="compare-wrapper">' +
        '<div class="compare-col">' + buildResponse(primary, term) + '</div>' +
        '<div class="compare-col">' + buildResponse(secondary, compare) + '</div>' +
      '</div>';
      resultsRoot.innerHTML = html;
    } else {
      resultsRoot.innerHTML = buildResponse(primary, term);
    }

    setStatus('Results loaded successfully.', 'success');
  } catch (error) {
    resultsRoot.innerHTML = '';
    setStatus(error.message || 'Unable to load peptide research results.', 'error');
  } finally {
    document.getElementById('search_button').disabled = false;
  }
}

/* ─── Enter key & Init ─── */
document.addEventListener('DOMContentLoaded', function () {
  resultsRoot = document.getElementById('results');
  var input = document.getElementById('term_input');
  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') searchPeptide();
    });
  }
  var compareInput = document.getElementById('compare_input');
  if (compareInput) {
    compareInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') searchPeptide();
    });
  }
});
