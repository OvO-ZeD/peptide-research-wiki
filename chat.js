/* ─── Chat State ─── */
var conversationHistory = [];
var CHAT_HISTORY_KEY = 'peptide_chat_history';
var isGenerating = false;

/* ─── Initialize ─── */
(function initChat() {
  loadChatHistory();
  setupChatInput();
})();

/* ─── Setup ─── */
function setupChatInput() {
  var input = document.getElementById('chat_input');
  if (!input) return;

  // Auto-resize textarea
  input.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });

  // Handle Enter key (send) vs Shift+Enter (new line)
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Focus input on load
  input.focus();
}

/* ─── Send Message ─── */
function sendMessage() {
  var input = document.getElementById('chat_input');
  var message = (input.value || '').trim();

  if (!message || isGenerating) return;

  // Add user message to UI
  appendMessage('user', message, []);

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // Hide welcome message
  var welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.style.display = 'none';

  // Add to conversation history
  conversationHistory.push({ role: 'user', content: message });

  // Show typing indicator
  showTypingIndicator();
  isGenerating = true;

  // Send to backend with streaming
  streamChatMessage(message);
}

function sendSuggestion(btn) {
  var input = document.getElementById('chat_input');
  if (input) {
    input.value = btn.textContent;
    sendMessage();
  }
}

/* ─── Stream Chat Message ─── */
function streamChatMessage(message) {
  var aiMessageDiv = null;
  var aiContentDiv = null;
  var fullResponse = '';
  var firstChunkReceived = false;

  // Prepare the streaming URL
  var streamUrl = '/ask/stream?message=' + encodeURIComponent(message) +
    '&history=' + encodeURIComponent(JSON.stringify(conversationHistory.slice(0, -1)));

  // Use EventSource for Server-Sent Events
  var eventSource = new EventSource(streamUrl);

  eventSource.onmessage = function (event) {
    try {
      var data = JSON.parse(event.data);

      // Handle errors
      if (data.error) {
        hideTypingIndicator();
        isGenerating = false;
        eventSource.close();
        appendMessage('ai', 'Error: ' + data.error, []);
        return;
      }

      // Handle completion
      if (data.done) {
        hideTypingIndicator();
        isGenerating = false;
        eventSource.close();

        // Add full response to conversation history
        conversationHistory.push({ role: 'assistant', content: fullResponse });

        // Save to localStorage
        saveChatHistory();

        // Scroll to bottom
        scrollToBottom();
        return;
      }

      // Handle text chunks
      if (data.chunk) {
        // Hide typing indicator on first chunk
        if (!firstChunkReceived) {
          hideTypingIndicator();
          firstChunkReceived = true;

          // Create AI message container
          var messagesContainer = document.getElementById('chat_messages');
          if (messagesContainer) {
            aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'chat-message chat-message-ai';

            aiContentDiv = document.createElement('div');
            aiContentDiv.className = 'chat-message-content';

            aiMessageDiv.appendChild(aiContentDiv);
            messagesContainer.appendChild(aiMessageDiv);
          }
        }

        // Append chunk to response
        fullResponse += data.chunk;

        // Update UI with streamed content
        if (aiContentDiv) {
          var htmlContent = convertMarkdownToHtml(escapeHtml(fullResponse));
          aiContentDiv.innerHTML = htmlContent;
          scrollToBottom();
        }
      }
    } catch (e) {
      console.error('Error parsing SSE data:', e);
    }
  };

  eventSource.onerror = function (error) {
    hideTypingIndicator();
    isGenerating = false;
    eventSource.close();

    if (!firstChunkReceived) {
      appendMessage('ai', 'Error: Failed to connect to AI service. Please try again.', []);
    }

    console.error('EventSource error:', error);
  };
}

/* ─── Append Message ─── */
function appendMessage(role, content, sources) {
  var messagesContainer = document.getElementById('chat_messages');
  if (!messagesContainer) return;

  var messageDiv = document.createElement('div');
  messageDiv.className = 'chat-message chat-message-' + role;

  var contentDiv = document.createElement('div');
  contentDiv.className = 'chat-message-content';

  // Convert markdown links to HTML
  var htmlContent = convertMarkdownToHtml(escapeHtml(content));
  contentDiv.innerHTML = htmlContent;

  messageDiv.appendChild(contentDiv);

  // Add sources if available
  if (sources && sources.length > 0) {
    var sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'chat-sources';

    sources.forEach(function (source) {
      var badge = document.createElement('a');
      badge.className = 'chat-source-badge';
      badge.href = source.url;
      badge.target = '_blank';
      badge.rel = 'noopener noreferrer';
      badge.textContent = source.label;
      sourcesDiv.appendChild(badge);
    });

    messageDiv.appendChild(sourcesDiv);
  }

  messagesContainer.appendChild(messageDiv);
  scrollToBottom();
}

/* ─── Typing Indicator ─── */
function showTypingIndicator() {
  var indicator = document.getElementById('typing_indicator');
  if (indicator) indicator.style.display = 'flex';
  scrollToBottom();
}

function hideTypingIndicator() {
  var indicator = document.getElementById('typing_indicator');
  if (indicator) indicator.style.display = 'none';
}

/* ─── Scroll to Bottom ─── */
function scrollToBottom() {
  var messagesContainer = document.getElementById('chat_messages');
  if (messagesContainer) {
    setTimeout(function () {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
  }
}

/* ─── New Conversation ─── */
function newConversation() {
  if (isGenerating) return;

  if (conversationHistory.length > 0) {
    if (!confirm('Start a new conversation? Current chat will be cleared.')) return;
  }

  conversationHistory = [];
  saveChatHistory();

  var messagesContainer = document.getElementById('chat_messages');
  if (messagesContainer) {
    messagesContainer.innerHTML = '<div class="chat-welcome">' +
      '<div class="chat-welcome-icon">' +
      '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="1.5">' +
      '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
      '</svg>' +
      '</div>' +
      '<h3>Welcome to AI Research Assistant</h3>' +
      '<p>Ask me anything about peptides, clinical trials, treatment comparisons, and dosing protocols.</p>' +
      '<div class="chat-suggestions">' +
      '<button class="chat-suggestion" onclick="sendSuggestion(this)">What\'s better for hair loss: minoxidil or GHK-Cu?</button>' +
      '<button class="chat-suggestion" onclick="sendSuggestion(this)">Compare semaglutide vs tirzepatide for weight loss</button>' +
      '<button class="chat-suggestion" onclick="sendSuggestion(this)">What are the clinical protocols for BPC-157?</button>' +
      '<button class="chat-suggestion" onclick="sendSuggestion(this)">Tell me about tesamorelin for visceral fat</button>' +
      '</div>' +
      '</div>';
  }

  showToast('New conversation started');
}

/* ─── Export Conversation ─── */
function exportConversation() {
  if (conversationHistory.length === 0) {
    showToast('No conversation to export');
    return;
  }

  var exportText = 'Peptide Research Wiki - AI Chat Export\n';
  exportText += 'Exported: ' + new Date().toLocaleString() + '\n';
  exportText += '═'.repeat(50) + '\n\n';

  conversationHistory.forEach(function (msg, idx) {
    var role = msg.role === 'user' ? 'YOU' : 'AI';
    exportText += role + ':\n' + msg.content + '\n\n';
    exportText += '─'.repeat(50) + '\n\n';
  });

  // Create download
  var blob = new Blob([exportText], { type: 'text/plain' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'peptide-chat-' + Date.now() + '.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Conversation exported');
}

/* ─── Save/Load Chat History ─── */
function saveChatHistory() {
  try {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(conversationHistory));
  } catch (e) {
    console.error('Failed to save chat history:', e);
  }
}

function loadChatHistory() {
  try {
    var stored = localStorage.getItem(CHAT_HISTORY_KEY);
    if (stored) {
      conversationHistory = JSON.parse(stored);
      renderChatHistory();
    }
  } catch (e) {
    console.error('Failed to load chat history:', e);
    conversationHistory = [];
  }
}

function renderChatHistory() {
  if (conversationHistory.length === 0) return;

  var messagesContainer = document.getElementById('chat_messages');
  if (!messagesContainer) return;

  // Hide welcome message
  var welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.style.display = 'none';

  // Render all messages
  conversationHistory.forEach(function (msg) {
    appendMessage(msg.role, msg.content, []);
  });
}

/* ─── Markdown to HTML ─── */
function convertMarkdownToHtml(text) {
  // Convert markdown links [text](url) to HTML links
  var html = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (match, label, url) {
    return '<a href="' + url + '" target="_blank" rel="noopener noreferrer" class="chat-link">' + label + '</a>';
  });

  // Convert **bold** to <strong>
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Convert *italic* to <em>
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Convert line breaks to <br>
  html = html.replace(/\n/g, '<br>');

  return html;
}

/* ─── Escape HTML ─── */
function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
