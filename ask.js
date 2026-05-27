(function () {
  'use strict';

  var input = document.getElementById('ask_input');
  var sendBtn = document.getElementById('ask_send_btn');
  var messages = document.getElementById('chat_messages');
  var welcome = document.getElementById('welcome_state');
  var suggestions = document.getElementById('suggestions');

  /* ─── State ─── */
  var isSending = false;

  /* ─── Toast ─── */
  function showToast(msg) {
    var t = document.createElement('div');
    t.className = 'toast-mini';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2000);
  }

  /* ─── Helpers ─── */
  function scrollBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addMsg(text, role, extra) {
    if (welcome) welcome.style.display = 'none';

    var div = document.createElement('div');
    div.className = 'msg msg-' + (role === 'user' ? 'user' : 'ai');

    if (role === 'user') {
      div.textContent = text;
    } else if (role === 'interaction') {
      /* Render interaction results as chat message */
      var label = document.createElement('div');
      label.className = 'msg-label';
      label.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:12px;height:12px;vertical-align:middle;margin-right:4px"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg> Interaction Check';
      div.appendChild(label);
      var content = document.createElement('div');
      content.innerHTML = text;
      div.appendChild(content);
    } else {
      /* Parse markdown-style formatting */
      var html = '';
      var lines = text.split('\n');
      var inList = false;
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/`(.+?)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:3px;font-size:0.85em">$1</code>');
        if (line.match(/^[-*]\s/)) {
          if (!inList) { html += '<ul>'; inList = true; }
          html += '<li>' + line.replace(/^[-*]\s/, '') + '</li>';
        } else {
          if (inList) { html += '</ul>'; inList = false; }
          var nm = line.match(/^(\d+)\.\s(.+)/);
          if (nm) {
            if (!inList) { html += '<ol>'; inList = 'ol'; }
            html += '<li>' + nm[2] + '</li>';
          } else {
            if (inList === 'ol') { html += '</ol>'; inList = false; }
            if (line.trim() === '') {
              html += '<br>';
            } else {
              html += '<p>' + line + '</p>';
            }
          }
        }
      }
      if (inList) html += (inList === 'ol' ? '</ol>' : '</ul>');

      var label = document.createElement('div');
      label.className = 'msg-label';
      label.textContent = 'Ask AI';
      div.appendChild(label);

      var content = document.createElement('div');
      content.innerHTML = html;
      div.appendChild(content);

      /* Citations */
      if (extra && extra.citations && extra.citations.length) {
        var citeDiv = document.createElement('div');
        citeDiv.className = 'citations';
        for (var ci = 0; ci < extra.citations.length; ci++) {
          var c = extra.citations[ci];
          var chip = document.createElement('a');
          chip.className = 'citation-chip';
          chip.href = '/search?term=' + encodeURIComponent(c.peptide || c.source);
          chip.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"/></svg> ' + (c.label || c.source);
          chip.target = '_blank';
          citeDiv.appendChild(chip);
        }
        div.appendChild(citeDiv);
      }

      /* Stack links */
      if (extra && extra.stacks && extra.stacks.length) {
        var stackDiv = document.createElement('div');
        stackDiv.style.cssText = 'margin-top:8px;display:flex;flex-wrap:wrap;gap:4px';
        for (var si = 0; si < extra.stacks.length; si++) {
          var s = extra.stacks[si];
          var chip = document.createElement('a');
          chip.className = 'citation-chip';
          chip.href = '/stacks?s=' + encodeURIComponent(s);
          chip.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><rect x="4" y="10" width="16" height="10" rx="1.5"/><path d="M6 10 V8a2 2 0 0 1 2-2 h8a2 2 0 0 1 2 2 v2"/></svg> ' + s;
          chip.target = '_blank';
          stackDiv.appendChild(chip);
        }
        div.appendChild(stackDiv);
      }

      /* Action buttons: Copy, Dosage, Safety, Interactions */
      var actions = document.createElement('div');
      actions.className = 'msg-actions';

      /* Copy button */
      var copyBtn = document.createElement('button');
      copyBtn.className = 'msg-action-btn';
      copyBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy';
      copyBtn.addEventListener('click', function () {
        var plainText = text
          .replace(/\*\*(.+?)\*\*/g, '$1')
          .replace(/<[^>]+>/g, '')
          .replace(/\n{3,}/g, '\n\n')
          .trim();
        navigator.clipboard.writeText(plainText).then(function () {
          showToast('Copied to clipboard');
        }).catch(function () {
          showToast('Failed to copy');
        });
      });
      actions.appendChild(copyBtn);

      /* Dosage, Safety, Interactions — require citations */
      if (extra && extra.citations && extra.citations.length) {
        var pepList = [];
        for (var ci2 = 0; ci2 < extra.citations.length; ci2++) {
          pepList.push(extra.citations[ci2].peptide || extra.citations[ci2].source);
        }
        var firstPep = pepList[0];

        var dosageBtn = document.createElement('button');
        dosageBtn.className = 'msg-action-btn';
        dosageBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="4" y="4" width="16" height="16" rx="2"/><line x1="8" y1="12" x2="16" y2="12"/></svg> Dosage';
        dosageBtn.addEventListener('click', function () {
          fetchDosage(firstPep, dosageBtn);
        });
        actions.appendChild(dosageBtn);

        var safetyBtn = document.createElement('button');
        safetyBtn.className = 'msg-action-btn';
        safetyBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="0.5"/></svg> Safety';
        safetyBtn.addEventListener('click', function () {
          fetchSafety(firstPep, safetyBtn);
        });
        actions.appendChild(safetyBtn);

        /* Interactions button — only when 2+ citations */
        if (pepList.length >= 2) {
          var ixBtn = document.createElement('button');
          ixBtn.className = 'msg-action-btn';
          ixBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg> Interactions';
          ixBtn.addEventListener('click', function () {
            showInteractions(pepList);
          });
          actions.appendChild(ixBtn);
        }
      }

      div.appendChild(actions);
    }

    messages.appendChild(div);
    scrollBottom();
  }

  function addTyping() {
    var div = document.createElement('div');
    div.className = 'msg msg-ai';
    div.id = 'typing_indicator';
    div.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    messages.appendChild(div);
    scrollBottom();
  }

  function removeTyping() {
    var el = document.getElementById('typing_indicator');
    if (el) el.remove();
  }

  function setLoading(v) {
    isSending = v;
    sendBtn.disabled = v || !input.value.trim();
    sendBtn.style.opacity = (v || !input.value.trim()) ? '0.5' : '';
  }

  /* ─── Dosage / Safety fetchers ─── */
  function fetchDosage(pep, btn) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/dosage/' + encodeURIComponent(pep), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        showDosageCard(data.dosage, btn);
      } else {
        showToast('No dosage data available');
      }
    };
    xhr.onerror = function () { showToast('Network error'); };
    xhr.send();
  }

  function showDosageCard(d, btn) {
    var existing = btn.parentNode.parentNode.querySelector('.inline-dosage-card');
    if (existing) { existing.remove(); return; }

    var card = document.createElement('div');
    card.className = 'inline-dosage-card';
    card.style.cssText = 'margin-top:8px;padding:10px 12px;background:rgba(255,255,255,0.03);border:1px solid var(--hairline);border-radius:var(--radius-lg);font-size:0.75rem;line-height:1.6;';
    card.innerHTML =
      '<div style="font-weight:600;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--ink-subtle);margin-bottom:4px">Dosage Reference</div>' +
      '<div><strong>Typical dose:</strong> ' + (d.typical_dose || 'N/A') + '</div>' +
      '<div><strong>Route:</strong> ' + (d.route || 'N/A') + '</div>' +
      '<div><strong>Half-life:</strong> ' + (d.half_life || 'N/A') + '</div>' +
      (d.notes ? '<div style="color:var(--ink-muted);margin-top:4px">' + d.notes + '</div>' : '') +
      (d.max_safe ? '<div style="color:var(--warning);margin-top:2px"><strong>Max safe:</strong> ' + d.max_safe + '</div>' : '');
    btn.parentNode.parentNode.appendChild(card);
  }

  function fetchSafety(pep, btn) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/safety/' + encodeURIComponent(pep), true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        showSafetyCard(data.safety, btn);
      } else {
        showToast('No safety data available');
      }
    };
    xhr.onerror = function () { showToast('Network error'); };
    xhr.send();
  }

  function showSafetyCard(s, btn) {
    var existing = btn.parentNode.parentNode.querySelector('.safety-card');
    if (existing) { existing.remove(); return; }

    var card = document.createElement('div');
    card.className = 'safety-card';

    var toggle = document.createElement('button');
    toggle.className = 'safety-toggle';
    toggle.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> ' + (s.title || 'Safety Info');
    card.appendChild(toggle);

    var body = document.createElement('div');
    body.className = 'safety-body';
    if (s.points && s.points.length) {
      var ul = document.createElement('ul');
      for (var pi = 0; pi < s.points.length; pi++) {
        var li = document.createElement('li');
        li.textContent = s.points[pi];
        ul.appendChild(li);
      }
      body.appendChild(ul);
    }
    card.appendChild(body);

    toggle.addEventListener('click', function () {
      body.classList.toggle('open');
    });

    btn.parentNode.parentNode.appendChild(card);
  }

  /* ─── Interaction Checker (chat-based) ─── */
  function showInteractions(peps) {
    if (!peps || peps.length < 2) return;

    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'msg msg-ai msg-interim';
    loadingDiv.innerHTML = '<div class="msg-label">Interaction Check</div><div style="font-size:0.75rem;color:var(--ink-subtle);padding:4px 0">Checking ' + peps.length + ' peptides...</div>';
    messages.appendChild(loadingDiv);
    scrollBottom();

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/interactions', true);
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onload = function () {
      loadingDiv.remove();
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        var ix = data.interactions || [];
        renderInteractionMessage(ix, peps);
      } else {
        addMsg('Failed to check interactions.', 'ai');
      }
    };
    xhr.onerror = function () {
      loadingDiv.remove();
      addMsg('Network error while checking interactions.', 'ai');
    };
    xhr.send(JSON.stringify({ peptides: peps }));
  }

  function renderInteractionMessage(interactions, peps) {
    var html = '';
    if (!interactions.length) {
      html = '**No known interactions** between **' + peps.join(' + ') + '**.';
    } else {
      html = '**Interaction Results**:';
      for (var i = 0; i < interactions.length; i++) {
        var ix = interactions[i];
        var typeLabel = ix.type.charAt(0).toUpperCase() + ix.type.slice(1);
        html += '<div class="interaction-card ' + ix.type + '" style="margin-top:6px">' +
          '<div class="pair-names"><span class="interaction-type-badge">' + typeLabel + '</span>' + ix.peptide_a + ' + ' + ix.peptide_b + '</div>' +
          '<div class="pair-note">' + ix.note + '</div>' +
          (ix.evidence ? '<div class="pair-evidence">Evidence: ' + ix.evidence + '</div>' : '') +
          '</div>';
      }
    }
    addMsg(html, 'interaction');
  }

  /* ─── Send ─── */
  function sendMessage(text) {
    if (!text.trim() || isSending) return;

    addMsg(text.trim(), 'user');
    input.value = '';
    sendBtn.disabled = true;
    addTyping();
    setLoading(true);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/ask', true);
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onload = function () {
      removeTyping();
      setLoading(false);

      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        addMsg(data.answer, 'ai', {
          citations: data.citations || [],
          stacks: data.stacks || []
        });
      } else {
        var errData;
        try { errData = JSON.parse(xhr.responseText); } catch (e) { errData = {}; }
        var errMsg = errData.error || 'Something went wrong. Please try again.';
        var div = document.createElement('div');
        div.className = 'msg msg-error';
        div.textContent = errMsg;
        messages.appendChild(div);
        scrollBottom();
      }
    };

    xhr.onerror = function () {
      removeTyping();
      setLoading(false);
      var div = document.createElement('div');
      div.className = 'msg msg-error';
      div.textContent = 'Network error. Please check your connection.';
      messages.appendChild(div);
      scrollBottom();
    };

    xhr.send(JSON.stringify({ question: text.trim() }));
  }

  /* ─── Events ─── */
  input.addEventListener('input', function () {
    sendBtn.disabled = isSending || !input.value.trim();
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  sendBtn.addEventListener('click', function () {
    sendMessage(input.value);
  });

  if (suggestions) {
    suggestions.addEventListener('click', function (e) {
      var chip = e.target.closest('.suggestion-chip');
      if (chip) {
        sendMessage(chip.getAttribute('data-q'));
      }
    });
  }

  /* ─── Init ─── */
  var initialQ = window.location.search.match(/[?&]q=([^&]+)/);
  if (initialQ) {
    var q = decodeURIComponent(initialQ[1]);
    setTimeout(function () { sendMessage(q); }, 300);
  }
})();
