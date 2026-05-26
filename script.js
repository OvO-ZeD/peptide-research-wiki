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

function makePanel(title, content) {
  return '<section class="panel"><h2>' + escapeHtml(title) + '</h2>' + content + '</section>';
}

/* ─── Renderers ─── */
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

function renderSources(sources) {
  if (!sources || !sources.length) return '<p class="empty">No source links provided.</p>';
  return '<div class="source-grid">' + sources.map(function (s) {
    return '<a class="source-link" href="' + escapeHtml(s.url) + '" target="_blank" rel="noopener">' + escapeHtml(s.label) + '</a>';
  }).join('') + '</div>';
}

/* ─── Build Response ─── */
function buildResponse(response, title) {
  var topTerm = response.peptide_name || response.normalized_term || title || 'Peptide';
  var html = '';

  // Clinical Trials
  if (response.clinical_trials && response.clinical_trials.length) {
    html += makePanel('Clinical Trials', renderTrials(response.clinical_trials));
  }

  // PubMed
  if (response.top_pubmed_articles || response.pubmed_articles) {
    html += makePanel('PubMed Articles', renderArticles(response.top_pubmed_articles || response.pubmed_articles));
  }

  // Sources
  if (response.sources && response.sources.length) {
    html += makePanel('Sources', renderSources(response.sources));
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
