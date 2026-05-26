/* ─── State ─── */
var resultsRoot = null;
var FAV_KEY = 'peptide_favorites';
var RECENT_KEY = 'peptide_recent_searches';

/* ─── Particles ─── */
(function initParticles() {
  var canvas = document.getElementById('particles');
  if (!canvas) return;
  if (window.innerWidth < 480) { canvas.style.display = 'none'; return; }
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

/* ─── Theme Toggle ─── */
function initTheme() {
  var btn = document.getElementById('theme_btn');
  if (!btn) return;
  var saved = localStorage.getItem('peptide_theme');
  if (saved === 'light') document.body.classList.add('light-theme');
  btn.textContent = document.body.classList.contains('light-theme') ? '☀' : '☾';
  btn.addEventListener('click', function () {
    document.body.classList.toggle('light-theme');
    var isLight = document.body.classList.contains('light-theme');
    localStorage.setItem('peptide_theme', isLight ? 'light' : 'dark');
    btn.textContent = isLight ? '☀' : '☾';
  });
}

/* ─── Progress Bar ─── */
function initProgressBar() {
  var bar = document.getElementById('progress_bar');
  if (!bar) return;
  window.addEventListener('scroll', function () {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var pct = h > 0 ? (window.scrollY / h) * 100 : 0;
    bar.style.width = pct + '%';
  });
}

/* ─── Typeahead ─── */
function initTypeahead(inputId, listId) {
  var input = document.getElementById(inputId);
  var list = document.getElementById(listId);
  if (!input || !list) return;
  var wrap = document.createElement('div');
  wrap.className = 'suggestions-wrap';
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);

  var dd = document.createElement('div');
  dd.className = 'suggestions-dropdown';
  wrap.appendChild(dd);

  var options = list.querySelectorAll('option');
  var peptides = [];
  for (var i = 0; i < options.length; i++) peptides.push(options[i].value);

  input.addEventListener('input', function () {
    var val = input.value.toLowerCase().trim();
    if (!val) { dd.classList.remove('active'); dd.innerHTML = ''; return; }
    var matches = [];
    for (var j = 0; j < peptides.length; j++) {
      if (peptides[j].toLowerCase().indexOf(val) > -1) matches.push(peptides[j]);
      if (matches.length >= 8) break;
    }
    if (!matches.length) { dd.classList.remove('active'); dd.innerHTML = ''; return; }
    var html = '';
    for (var k = 0; k < matches.length; k++) {
      var idx = matches[k].toLowerCase().indexOf(val);
      var label = idx > -1 ? matches[k].slice(0, idx) + '<span class="s-match">' + matches[k].slice(idx, idx + val.length) + '</span>' + matches[k].slice(idx + val.length) : escapeHtml(matches[k]);
      html += '<div class="suggestion-item" onclick="pickSuggestion(\'' + escapeHtml(matches[k]) + '\',\'' + inputId + '\')">' + label + '</div>';
    }
    dd.innerHTML = html;
    dd.classList.add('active');
  });

  input.addEventListener('blur', function () { setTimeout(function () { dd.classList.remove('active'); }, 200); });
  input.addEventListener('focus', function () { if (input.value.trim()) input.dispatchEvent(new Event('input')); });
}

function pickSuggestion(val, inputId) {
  document.getElementById(inputId).value = val;
  if (inputId === 'term_input') searchPeptide();
}

/* ─── Recent Searches ─── */
function initRecent() {
  var container = document.getElementById('recent_searches');
  if (!container) return;
  var input = document.getElementById('term_input');
  if (!input) return;

  function render() {
    var items = loadRecent();
    if (!items.length) { container.classList.remove('active'); return; }
    var html = '<span class="recent-label">Recent</span>';
    for (var i = 0; i < items.length; i++) {
      html += '<span class="recent-chip" onclick="document.getElementById(\'term_input\').value=\'' + escapeHtml(items[i]) + '\';searchPeptide()">' + escapeHtml(items[i]) +
        '<span class="recent-del" onclick="event.stopPropagation();removeRecent(\'' + escapeHtml(items[i]) + '\')">✕</span></span>';
    }
    container.innerHTML = html;
    container.classList.add('active');
  }

  input.addEventListener('focus', render);
  input.addEventListener('blur', function () { setTimeout(function () { container.classList.remove('active'); }, 200); });
  render();
}

function loadRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY)) || []; } catch (_) { return []; }
}

function saveRecent(term) {
  var items = loadRecent();
  items = items.filter(function (s) { return s !== term; });
  items.unshift(term);
  if (items.length > 6) items = items.slice(0, 6);
  localStorage.setItem(RECENT_KEY, JSON.stringify(items));
}

function removeRecent(term) {
  var items = loadRecent().filter(function (s) { return s !== term; });
  localStorage.setItem(RECENT_KEY, JSON.stringify(items));
  var container = document.getElementById('recent_searches');
  if (container) {
    var html = '<span class="recent-label">Recent</span>';
    for (var i = 0; i < items.length; i++) {
      html += '<span class="recent-chip" onclick="document.getElementById(\'term_input\').value=\'' + escapeHtml(items[i]) + '\';searchPeptide()">' + escapeHtml(items[i]) +
        '<span class="recent-del" onclick="event.stopPropagation();removeRecent(\'' + escapeHtml(items[i]) + '\')">✕</span></span>';
    }
    container.innerHTML = html;
  }
}

/* ─── Favorites ─── */
function loadFavorites() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch (_) { return []; }
}

function addFavorite(name) {
  var favs = loadFavorites();
  if (favs.indexOf(name) === -1) { favs.push(name); localStorage.setItem(FAV_KEY, JSON.stringify(favs)); }
  renderFavBar();
}

function removeFavorite(name) {
  var favs = loadFavorites().filter(function (s) { return s !== name; });
  localStorage.setItem(FAV_KEY, JSON.stringify(favs));
  renderFavBar();
  // Update star icons
  var stars = document.querySelectorAll('.fav-star[data-name="' + escapeHtml(name) + '"]');
  for (var i = 0; i < stars.length; i++) {
    stars[i].classList.remove('active');
    stars[i].textContent = '☆';
  }
}

function toggleFavorite(name, el) {
  var favs = loadFavorites();
  if (favs.indexOf(name) > -1) {
    removeFavorite(name);
    if (el) { el.classList.remove('active'); el.textContent = '☆'; }
    if (typeof showToast === 'function') showToast('Removed from favorites', '☆');
  } else {
    addFavorite(name);
    if (el) { el.classList.add('active'); el.textContent = '★'; }
    if (typeof showToast === 'function') showToast('Added to favorites', '★');
  }
}

function renderFavBar() {
  var bar = document.getElementById('fav_bar');
  if (!bar) return;
  var favs = loadFavorites();
  if (!favs.length) { bar.classList.remove('active'); bar.innerHTML = ''; return; }
  var html = '';
  for (var i = 0; i < favs.length; i++) {
    html += '<span class="fav-chip"><span onclick="searchFav(\'' + escapeHtml(favs[i]) + '\')">' + escapeHtml(favs[i]) + '</span><span class="fav-del" onclick="removeFavorite(\'' + escapeHtml(favs[i]) + '\');renderFavBar();if(typeof showToast===\'function\')showToast(\'Removed\',\'☆\')">✕</span></span>';
  }
  bar.innerHTML = html;
  bar.classList.add('active');
}

function searchFav(name) {
  document.getElementById('term_input').value = name;
  searchPeptide();
}

/* ─── Search filter (within results) ─── */
function initSearchFilter() {
  var filter = document.getElementById('results_filter');
  if (!filter) return;
  filter.addEventListener('input', function () {
    var q = this.value.toLowerCase().trim();
    var panels = resultsRoot.querySelectorAll('.panel');
    for (var i = 0; i < panels.length; i++) {
      var text = panels[i].textContent || '';
      panels[i].style.display = (!q || text.toLowerCase().indexOf(q) > -1) ? '' : 'none';
    }
  });
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

/* ─── PWA Install ─── */
var _deferredPrompt = null;
function initPwaInstall() {
  var banner = document.getElementById('install_banner');
  if (!banner) return;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    _deferredPrompt = e;
    banner.classList.add('active');
  });
  document.getElementById('install_btn').addEventListener('click', function () {
    if (!_deferredPrompt) return;
    _deferredPrompt.prompt();
    _deferredPrompt.userChoice.then(function () { _deferredPrompt = null; banner.classList.remove('active'); });
  });
  document.getElementById('install_dismiss').addEventListener('click', function () {
    banner.classList.remove('active');
  });
}

/* ─── Build Response ─── */
function buildResponse(response, title) {
  var score = response.evidence_score ? response.evidence_score.score : 'N/A';
  var tier = (response.evidence_score ? response.evidence_score.tier : 'N/A') || 'N/A';
  var topTerm = response.peptide_name || response.normalized_term || title || 'Peptide';
  var summary = response.plain_summary || response.medical_definition || 'No summary available.';
  var dotClass = tier === 'HIGH' ? 'dot-high' : tier === 'MEDIUM' ? 'dot-medium' : 'dot-low';
  var isFav = loadFavorites().indexOf(topTerm) > -1;

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
    '<div style="display:flex;align-items:center;gap:8px">' +
      '<h3 style="margin:0;flex:1">' + escapeHtml(topTerm) + '</h3>' +
      '<span class="fav-star' + (isFav ? ' active' : '') + '" data-name="' + escapeHtml(topTerm) + '" onclick="toggleFavorite(\'' + escapeHtml(topTerm) + '\',this)">' + (isFav ? '★' : '☆') + '</span>' +
    '</div>' +
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

  saveRecent(term);
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

    document.getElementById('results_filter_wrap').style.display = 'block';
    setStatus('Results loaded successfully.', 'success');
    if (window.innerWidth < 480 && typeof openSheet === 'function') openSheet(term + (compare ? ' vs ' + compare : ''));
  } catch (error) {
    resultsRoot.innerHTML = '';
    setStatus(error.message || 'Unable to load peptide research results.', 'error');
  } finally {
    document.getElementById('search_button').disabled = false;
  }
}

/* ─── Pull to Refresh (Search) ─── */
var _pullSearchY = 0;
var _pullingSearch = false;
function initPullToRefreshSearch() {
  var page = document.querySelector('.page');
  if (!page) return;
  page.addEventListener('touchstart', function (e) {
    if (window.scrollY > 0 || document.querySelector('.sheet-container.open')) return;
    _pullSearchY = e.touches[0].clientY;
    _pullingSearch = true;
  }, { passive: true });
  page.addEventListener('touchmove', function (e) {
    if (!_pullingSearch || window.scrollY > 0 || document.querySelector('.sheet-container.open')) return;
    if (e.touches[0].clientY - _pullSearchY > 70) {
      _pullingSearch = false;
      if (document.getElementById('term_input') && document.getElementById('term_input').value.trim()) searchPeptide();
    }
  }, { passive: true });
  page.addEventListener('touchend', function () { _pullingSearch = false; }, { passive: true });
}

/* ─── Bottom Sheet (Search Results) ─── */
var _sheetStartY = 0;
var _sheetDragging = false;

function initBottomSheet() {
  var container = document.getElementById('sheet_container');
  if (!container) return;

  var handle = container.querySelector('.sheet-handle');
  if (!handle) return;

  handle.addEventListener('touchstart', function (e) {
    _sheetStartY = e.touches[0].clientY;
    _sheetDragging = true;
    container.style.transition = 'none';
  }, { passive: true });

  handle.addEventListener('touchmove', function (e) {
    if (!_sheetDragging) return;
    var dy = e.touches[0].clientY - _sheetStartY;
    if (dy > 0) container.style.transform = 'translateY(' + dy + 'px)';
  }, { passive: true });

  handle.addEventListener('touchend', function () {
    if (!_sheetDragging) return;
    _sheetDragging = false;
    container.style.transition = 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)';
    var dy = parseFloat(container.style.transform.replace('translateY(','').replace('px)','')) || 0;
    if (dy > 80) closeSheet();
    else container.style.transform = 'translateY(0)';
  }, { passive: true });
}

function openSheet(title) {
  var container = document.getElementById('sheet_container');
  var overlay = document.getElementById('sheet_overlay');
  var body = document.getElementById('sheet_body');
  var titleEl = document.getElementById('sheet_title');
  if (!container || !body) return;
  if (titleEl) titleEl.textContent = title || 'Results';
  body.innerHTML = resultsRoot ? resultsRoot.innerHTML : '';
  container.classList.add('open');
  if (overlay) overlay.classList.add('open');
  container.style.transform = '';
  document.body.classList.add('sheet-capable');
}

function closeSheet() {
  var container = document.getElementById('sheet_container');
  var overlay = document.getElementById('sheet_overlay');
  if (container) container.classList.remove('open');
  if (overlay) overlay.classList.remove('open');
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

  initTheme();
  initProgressBar();
  initTypeahead('term_input', 'peptide-list');
  initTypeahead('compare_input', 'peptide-list-compare');
  initRecent();
  initSearchFilter();
  renderFavBar();
  initPwaInstall();
  initPullToRefreshSearch();
  initBottomSheet();
});
