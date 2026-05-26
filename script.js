var resultsRoot = null;

window.addEventListener('DOMContentLoaded', function () {
  resultsRoot = document.getElementById('results');
});

function toggleTheme() {
  document.body.classList.toggle('theme-light');
  document.body.classList.toggle('theme-dark');
}

function setStatus(message, type) {
  var status = document.getElementById('status_message');
  if (!status) {
    return;
  }
  status.textContent = message;
  status.className = 'status-message ' + (type || '');
}

function escapeHtml(value) {
  return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function createSection(title, content) {
  return '<section class="panel card"><h2>' + escapeHtml(title) + '</h2>' + content + '</section>';
}

function buildItemList(items) {
  if (!items || !items.length) {
    return '<p class="empty">No data available.</p>';
  }
  return '<ul class="data-list">' + items.map(function (item) {
    return '<li>' + escapeHtml(item) + '</li>';
  }).join('') + '</ul>';
}

function renderSourceLinks(sources) {
  if (!sources || !sources.length) {
    return '<p class="empty">No source links provided.</p>';
  }
  return '<div class="source-grid">' + sources.map(function (source) {
    return '<a class="source-link" href="' + escapeHtml(source.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(source.label) + '</a>';
  }).join('') + '</div>';
}

function renderTrials(trials) {
  if (!trials || !trials.length) {
    return '<p class="empty">No clinical trials found for this peptide.</p>';
  }
  return '<div class="trial-list">' + trials.slice(0, 4).map(function (trial) {
    var title = trial.title || 'Untitled study';
    var status = trial.status || 'Unknown status';
    var summary = trial.lay_summary || '';
    return '<article class="trial-item"><h3>' + escapeHtml(title) + '</h3><p class="meta">' + escapeHtml(status) + '</p><p>' + escapeHtml(summary) + '</p><a href="' + escapeHtml(trial.link) + '" target="_blank" rel="noopener noreferrer">View trial details</a></article>';
  }).join('') + '</div>';
}

function renderArticles(articles) {
  if (!articles || !articles.length) {
    return '<p class="empty">No PubMed articles were returned.</p>';
  }
  return '<ol class="article-list">' + articles.slice(0, 5).map(function (article) {
    return '<li><a href="' + escapeHtml(article.link) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(article.title || 'Untitled article') + '</a><span>' + escapeHtml(article.pubdate || '') + '</span></li>';
  }).join('') + '</ol>';
}

function renderClinicalSnapshot(snapshot) {
  if (!snapshot) {
    return '<p class="empty">No clinical snapshot available.</p>';
  }
  return '<div class="snapshot-grid">' + ['primary_effect', 'mechanism_pathway', 'expected_body_outcomes', 'clinical_context'].map(function (key) {
    var label = {
      primary_effect: 'Primary effect',
      mechanism_pathway: 'Mechanism / pathway',
      expected_body_outcomes: 'Expected outcomes',
      clinical_context: 'Clinical context'
    }[key];
    return '<div class="snapshot-item"><strong>' + escapeHtml(label) + '</strong><p>' + escapeHtml(snapshot[key] || '') + '</p></div>';
  }).join('') + '</div>';
}

function renderResponse(response, title) {
  var score = response.evidence_score ? response.evidence_score.score : 'N/A';
  var tier = response.evidence_score ? response.evidence_score.tier : 'N/A';
  var topTerm = response.peptide_name || response.normalized_term || title || 'Peptide';
  var html = '';

  html += createSection('Research overview', '<div class="hero-card"><h3>' + escapeHtml(topTerm) + '</h3><p>' + escapeHtml(response.plain_summary || response.medical_definition || 'No summary available.') + '</p><div class="hero-metrics"><span>Evidence score: ' + escapeHtml(score) + '</span><span>Tier: ' + escapeHtml(tier) + '</span><span>Reliability: ' + escapeHtml(response.reliability || 'Unknown') + '</span></div></div>');
  html += createSection('Clinical snapshot', renderClinicalSnapshot(response.clinical_snapshot));
  html += createSection('Benefits', buildItemList(response.benefits || []));
  html += createSection('Concerns', buildItemList(response.cons || []));
  html += createSection('Top clinical trials', renderTrials(response.clinical_trials));
  html += createSection('Top PubMed articles', renderArticles(response.top_pubmed_articles || response.pubmed_articles));
  html += createSection('Sources', renderSourceLinks(response.sources));

  return html;
}

async function fetchSearch(term) {
  var url = '/search?term=' + encodeURIComponent(term);
  var response = await fetch(url, { method: 'GET' });
  if (!response.ok) {
    var errorText = 'Search failed with status ' + response.status;
    try {
      var errorData = await response.json();
      if (errorData && errorData.error) {
        errorText = errorData.error;
      }
    } catch (err) {
      // keep default
    }
    throw new Error(errorText);
  }
  return response.json();
}

async function searchPeptide() {
  var term = document.getElementById('term_input').value.trim();
  var compare = document.getElementById('compare_input').value.trim();

  if (!term) {
    setStatus('Please enter a peptide name before searching.', 'error');
    return;
  }

  resultsRoot.innerHTML = '';
  setStatus('Loading research results…', 'loading');
  document.getElementById('search_button').disabled = true;

  try {
    var primary = await fetchSearch(term);
    var html = '<div class="result-panel">' + renderResponse(primary, term) + '</div>';

    if (compare) {
      var secondary = await fetchSearch(compare);
      html = '<div class="compare-grid"><div>' + renderResponse(primary, term) + '</div><div>' + renderResponse(secondary, compare) + '</div></div>';
    }

    resultsRoot.innerHTML = html;
    setStatus('Results loaded successfully.', 'success');
  } catch (error) {
    resultsRoot.innerHTML = '';
    setStatus(error.message || 'Unable to load peptide research results.', 'error');
  } finally {
    document.getElementById('search_button').disabled = false;
  }
}
