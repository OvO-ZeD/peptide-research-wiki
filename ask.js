(function () {
  'use strict';

  var input = document.getElementById('ask_input');
  var sendBtn = document.getElementById('ask_send_btn');
  var messages = document.getElementById('chat_messages');
  var welcome = document.getElementById('welcome_state');
  var suggestions = document.getElementById('suggestions');

  /* ─── State ─── */
  var isSending = false;
  var conversationHistory = [];

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

  /* ─── 1A: Typewriter streaming text reveal ─── */
  function revealText(element, html, onDone) {
    var tokens = html.split(/(<[^>]+>|&[a-z]+;)/g).filter(Boolean);
    var i = 0;
    var current = '';
    var interval = setInterval(function () {
      if (i >= tokens.length) {
        clearInterval(interval);
        element.innerHTML = html; // Set final to ensure clean HTML
        if (onDone) onDone();
        return;
      }
      // Append up to 3 tokens per tick for speed
      for (var j = 0; j < 3 && i < tokens.length; j++, i++) {
        current += tokens[i];
      }
      element.innerHTML = current;
      // Auto-scroll as text reveals
      var msgs = document.getElementById('chat_messages');
      if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }, 18); // ~55 words/sec
    return interval;
  }

  /* ─── 1B: Follow-up question chips ─── */
  function addFollowUpChips(citations) {
    var chips = [];
    if (citations && citations.length > 0) {
      var pep = citations[0].peptide || citations[0].label || '';
      if (pep) {
        chips.push('Show dosage protocol for ' + pep);
        chips.push('What are the side effects of ' + pep + '?');
        chips.push('How long does ' + pep + ' take to work?');
      }
      if (citations.length >= 2) {
        var pep2 = citations[1].peptide || citations[1].label || '';
        if (pep2 && pep2 !== pep) {
          chips.push('Compare ' + pep + ' vs ' + pep2);
        }
      }
    } else {
      chips.push('What peptides help with recovery?');
      chips.push('What is the safest peptide to start with?');
      chips.push('How do GLP-1 agonists work?');
    }
    chips = chips.slice(0, 3);

    var chipWrap = document.createElement('div');
    chipWrap.className = 'followup-chips';
    chips.forEach(function (q) {
      var chip = document.createElement('button');
      chip.className = 'followup-chip';
      chip.textContent = q;
      chip.onclick = function () {
        chipWrap.remove();
        sendMessage(q);
      };
      chipWrap.appendChild(chip);
    });
    messages.appendChild(chipWrap);
    scrollBottom();
  }

  /* ─── 1C: Comparison table rendering ─── */
  function renderComparisonTable(compData) {
    var treatments = compData.treatments || [];
    if (!treatments.length) return null;

    var wrap = document.createElement('div');
    wrap.className = 'comparison-table-wrap';

    var title = document.createElement('div');
    title.className = 'comparison-title';
    title.textContent = compData.title || 'Treatment Comparison';
    wrap.appendChild(title);

    var table = document.createElement('div');
    table.className = 'comparison-grid';
    table.style.gridTemplateColumns = 'repeat(' + treatments.length + ', 1fr)';

    treatments.forEach(function (tx) {
      var col = document.createElement('div');
      col.className = 'comparison-col';

      var tierClass = 'tier-' + (tx.evidence_tier || 'c').toLowerCase();
      col.innerHTML =
        '<div class="comp-name">' + tx.name + '</div>' +
        '<div class="comp-tier ' + tierClass + '">Tier ' + (tx.evidence_tier || '?') + '</div>' +
        '<div class="comp-type">' + tx.type + '</div>' +
        '<div class="comp-section-label">Efficacy</div>' +
        '<div class="comp-value">' + tx.efficacy + '</div>' +
        '<div class="comp-section-label">Safety</div>' +
        '<div class="comp-value">' + tx.safety + '</div>' +
        '<div class="comp-section-label">Cost</div>' +
        '<div class="comp-value">' + tx.cost + '</div>' +
        '<div class="comp-section-label">Pros</div>' +
        '<ul class="comp-list pros">' + (tx.pros || []).map(function (p) { return '<li>' + p + '</li>'; }).join('') + '</ul>' +
        '<div class="comp-section-label">Cons</div>' +
        '<ul class="comp-list cons">' + (tx.cons || []).map(function (c) { return '<li>' + c + '</li>'; }).join('') + '</ul>';

      table.appendChild(col);
    });
    wrap.appendChild(table);

    if (compData.recommendation) {
      var rec = document.createElement('div');
      rec.className = 'comp-recommendation';
      rec.innerHTML = '<strong>Recommendation:</strong> ' + compData.recommendation;
      wrap.appendChild(rec);
    }

    return wrap;
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
        var hm = line.match(/^(#{1,3})\s+(.+)/);
        if (hm) {
          var hLevel = hm[1].length;
          var hClass = hLevel === 1 ? 'msg-h1' : hLevel === 2 ? 'msg-h2' : 'msg-h3';
          html += '<div class="' + hClass + '">' + hm[2] + '</div>';
        } else if (line.match(/^[-*]\s/)) {
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
      div.appendChild(content);

      /* Sources cloud */
      var srcDiv = null;
      if (extra && extra.sources && extra.sources.length) {
        srcDiv = document.createElement('div');
        srcDiv.className = 'sources-cloud';
        for (var si = 0; si < extra.sources.length; si++) {
          var s = extra.sources[si];
          var pill = document.createElement('span');
          pill.className = 'source-pill ' + (s.id || '');
          pill.textContent = s.label || s.id;
          srcDiv.appendChild(pill);
        }
      }

      /* Stack links */
      var stackDiv = null;
      if (extra && extra.stacks && extra.stacks.length) {
        stackDiv = document.createElement('div');
        stackDiv.style.cssText = 'margin-top:8px;display:flex;flex-wrap:wrap;gap:4px';
        for (var si2 = 0; si2 < extra.stacks.length; si2++) {
          var s2 = extra.stacks[si2];
          var chip = document.createElement('a');
          chip.className = 'citation-chip';
          chip.href = '/stacks?s=' + encodeURIComponent(s2);
          chip.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><rect x="4" y="10" width="16" height="10" rx="1.5"/><path d="M6 10 V8a2 2 0 0 1 2-2 h8a2 2 0 0 1 2 2 v2"/></svg> ' + s2;
          chip.target = '_blank';
          stackDiv.appendChild(chip);
        }
      }

      /* Action buttons — built after reveal */
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
      var firstPep = null;
      var pepList = [];
      if (extra && extra.citations && extra.citations.length) {
        for (var ci2 = 0; ci2 < extra.citations.length; ci2++) {
          pepList.push(extra.citations[ci2].peptide || extra.citations[ci2].source);
        }
        firstPep = pepList[0];

        var dosageBtn = document.createElement('button');
        dosageBtn.className = 'msg-action-btn';
        dosageBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="4" y="4" width="16" height="16" rx="2"/><line x1="8" y1="12" x2="16" y2="12"/></svg> Dosage';
        (function (pep, btn) {
          btn.addEventListener('click', function () {
            fetchDosage(pep, btn);
          });
        }(firstPep, dosageBtn));
        actions.appendChild(dosageBtn);

        var safetyBtn = document.createElement('button');
        safetyBtn.className = 'msg-action-btn';
        safetyBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="0.5"/></svg> Safety';
        (function (pep, btn) {
          btn.addEventListener('click', function () {
            fetchSafety(pep, btn);
          });
        }(firstPep, safetyBtn));
        actions.appendChild(safetyBtn);

        /* Interactions button — only when 2+ citations */
        if (pepList.length >= 2) {
          var ixBtn = document.createElement('button');
          ixBtn.className = 'msg-action-btn';
          ixBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg> Interactions';
          (function (peps, btn) {
            btn.addEventListener('click', function () {
              showInteractions(peps);
            });
          }(pepList, ixBtn));
          actions.appendChild(ixBtn);
        }
      }

      /* Append the message bubble now, then reveal text */
      messages.appendChild(div);
      scrollBottom();

      /* 1A: Reveal text word-by-word, then show decorations */
      revealText(content, html, function () {
        if (srcDiv) div.appendChild(srcDiv);
        if (stackDiv) div.appendChild(stackDiv);
        div.appendChild(actions);
        scrollBottom();
        /* 1B: Follow-up chips */
        addFollowUpChips(extra ? extra.citations : null);
      });

      return; // Early return — appendChild already done above
    }

    messages.appendChild(div);
    scrollBottom();
  }

  function addTyping() {
    var div = document.createElement('div');
    div.className = 'msg msg-ai';
    div.id = 'typing_indicator';
    div.innerHTML =
      '<div class="msg-label">Ask AI</div>' +
      '<div class="typing-indicator">' +
        '<div class="typing-pulse"></div>' +
        '<div class="typing-pulse"></div>' +
        '<div class="typing-pulse"></div>' +
        '<span class="typing-label">Searching research database…</span>' +
      '</div>';
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

  /* ─── 1F: Export conversation ─── */
  function exportConversation() {
    var msgs = document.querySelectorAll('.msg');
    if (!msgs.length) { showToast('No conversation to export'); return; }
    var lines = ['Peptide Research Wiki — Ask AI Conversation', 'Exported: ' + new Date().toLocaleString(), '---', ''];
    msgs.forEach(function (m) {
      if (m.classList.contains('msg-user')) {
        lines.push('YOU: ' + m.textContent.trim());
      } else if (m.classList.contains('msg-ai')) {
        var labelEl = m.querySelector('.msg-label');
        var contentEl = m.querySelector('div:not(.msg-label):not(.msg-actions):not(.citations)');
        lines.push('AI: ' + (contentEl ? contentEl.textContent.trim() : m.textContent.trim()));
      }
      lines.push('');
    });
    var blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'peptide-ai-conversation.txt';
    a.click();
    showToast('Conversation exported');
  }

  /* ─── Send ─── */
  function sendMessage(text) {
    if (!text.trim() || isSending) return;

    /* 1E: Push to history */
    conversationHistory.push({ role: 'user', content: text.trim() });
    conversationHistory = conversationHistory.slice(-6);

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

        /* 1E: Push AI response to history */
        if (data.answer) {
          conversationHistory.push({ role: 'assistant', content: data.answer });
          conversationHistory = conversationHistory.slice(-6);
        }

        /* 1C: Render comparison table above the text message */
        if (data.comparison_data) {
          var tableEl = renderComparisonTable(data.comparison_data);
          if (tableEl) {
            messages.appendChild(tableEl);
          }
        }

        addMsg(data.answer, 'ai', {
          citations: data.citations || [],
          stacks: data.stacks || [],
          sources: data.sources || []
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

    /* 1E: Include history in request */
    xhr.send(JSON.stringify({ question: text.trim(), history: conversationHistory }));
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

  /* ─── 4C: Animated border on input focus ─── */
  var inputWrap = document.querySelector('.ask-input-wrap');
  if (inputWrap) {
    var inp = inputWrap.querySelector('textarea, input');
    if (inp) {
      inp.addEventListener('focus', function () { inputWrap.classList.add('focused'); });
      inp.addEventListener('blur', function () { inputWrap.classList.remove('focused'); });
    }
  }

  /* ─── 1D: Voice input via Web Speech API ─── */
  function initVoiceInput() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return; // Not supported — don't show button

    var micBtn = document.getElementById('ask_mic_btn');
    if (!micBtn) return;

    var recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    var recording = false;

    micBtn.addEventListener('click', function () {
      if (recording) {
        recognition.stop();
        return;
      }
      recognition.start();
    });

    recognition.onstart = function () {
      recording = true;
      micBtn.classList.add('recording');
      micBtn.title = 'Listening... click to stop';
    };

    recognition.onresult = function (e) {
      var transcript = e.results[0][0].transcript;
      input.value = transcript;
      sendBtn.disabled = !transcript.trim();
      input.focus();
    };

    recognition.onend = function () {
      recording = false;
      micBtn.classList.remove('recording');
      micBtn.title = 'Voice input';
    };

    recognition.onerror = function () {
      recording = false;
      micBtn.classList.remove('recording');
      showToast('Voice input not available');
    };
  }
  initVoiceInput();

  /* ─── Export button wiring ─── */
  var exportBtn = document.getElementById('ask_export_btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', exportConversation);
  }

  /* ─── Init ─── */
  var initialQ = window.location.search.match(/[?&]q=([^&]+)/);
  if (initialQ) {
    var q = decodeURIComponent(initialQ[1]);
    setTimeout(function () { sendMessage(q); }, 300);
  }
})();
