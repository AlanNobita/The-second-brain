import { escapeHtml, api, debounce, showToast } from './utils.js';

let sessionId = null;
let isSending = false;

const messagesEl = document.getElementById('messages');
const emptyState = document.getElementById('empty-state');
const sessionListEl = document.getElementById('session-list');
const input = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const sendIcon = document.getElementById('send-icon');
const sendSpinner = document.getElementById('send-spinner');
const searchInput = document.getElementById('search-input');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebarClose = document.getElementById('sidebar-close-btn');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const themeToggle = document.getElementById('theme-toggle');
const themeIconDark = document.getElementById('theme-icon-dark');
const themeIconLight = document.getElementById('theme-icon-light');
const newChatBtn = document.getElementById('new-chat-btn');
const activeSessionTitle = document.getElementById('active-session-title');

function addMessage(role, content, isHtml = false, sources = null) {
  emptyState?.remove();

  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble message-content';

  if (isHtml) {
    bubble.innerHTML = content;
  } else if (role === 'assistant') {
    bubble.innerHTML = marked.parse(content);
  } else {
    bubble.textContent = content;
  }

  row.appendChild(bubble);

  if (role === 'assistant' && sources && sources.length > 0) {
    const sourcesEl = document.createElement('div');
    sourcesEl.className = 'msg-sources';
    const label = document.createElement('span');
    label.className = 'msg-sources-label';
    label.textContent = 'Sources:';
    sourcesEl.appendChild(label);
    sources.forEach((s) => {
      const pill = document.createElement(s.url ? 'a' : 'span');
      pill.className = `source-pill source-${s.type}`;
      pill.textContent = s.title || s.type;
      if (s.url) {
        pill.href = s.url;
        pill.target = '_blank';
        pill.rel = 'noopener noreferrer';
      }
      pill.title = s.url || s.session_id;
      sourcesEl.appendChild(pill);
    });
    row.appendChild(sourcesEl);
  }

  messagesEl.appendChild(row);
  scrollToBottom();
  return row;
}

function showTypingIndicator() {
  removeTypingIndicator();
  const row = document.createElement('div');
  row.className = 'typing-row';
  row.id = 'typing-indicator';
  const bubble = document.createElement('div');
  bubble.className = 'typing-bubble';
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.className = 'typing-dot';
    bubble.appendChild(dot);
  }
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById('typing-indicator')?.remove();
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showSuggestion(suggestion) {
  const row = document.createElement('div');
  row.className = 'suggestion-row';
  const bubble = document.createElement('div');
  bubble.className = 'suggestion-bubble';
  bubble.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
      <circle cx="7.5" cy="7.5" r="3"/>
      <path d="M7.5 1v1M7.5 13v1M1 7.5h1M13 7.5h1"/>
    </svg>
    <span>${escapeHtml(suggestion.text)}</span>
  `;
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();
}

async function handleYTCommand(command, args) {
  switch (command) {
    case 'ytsearch': {
      const results = await api(`/yt/search?q=${encodeURIComponent(args)}`);
      let html = '<div class="cmd-results-title">YouTube Search Results</div>';
      results.forEach((v) => {
        html += `<div class="yt-result">
          <div class="yt-result-title">${escapeHtml(v.title)}</div>
          <div class="yt-result-meta">${escapeHtml(v.channel)} &middot; ${v.published_at || ''}</div>
          <div class="yt-result-actions">
            <button class="yt-ingest-btn" data-url="${escapeHtml(v.url)}">Ingest</button>
            <a href="${escapeHtml(v.url)}" target="_blank" class="yt-watch-btn">Watch</a>
          </div>
        </div>`;
      });
      addMessage('assistant', html, true);
      document.querySelectorAll('.yt-ingest-btn').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          const url = e.target.dataset.url;
          e.target.textContent = 'Ingesting...';
          e.target.disabled = true;
          try {
            await api('/yt/ingest', {
              method: 'POST',
              body: JSON.stringify({ video_url: url }),
            });
            e.target.textContent = 'Ingested';
            e.target.classList.add('done');
            showToast('Video ingested successfully', 'success');
          } catch {
            e.target.textContent = 'Failed';
            e.target.classList.add('failed');
            showToast('Ingestion failed', 'error');
          }
        });
      });
      return true;
    }
    case 'ytchannel': {
      addMessage('assistant', '<em>Fetching channel videos...</em>', true);
      const data = await api('/yt/channel', {
        method: 'POST',
        body: JSON.stringify({ channel_url: args }),
      });
      addMessage('assistant', `<div class="cmd-success">✅ Ingested ${data.ingested_count} videos from channel.</div>`, true);
      showToast(`Ingested ${data.ingested_count} videos`, 'success');
      return true;
    }
    case 'ytsub': {
      const data = await api('/yt/subscribe', {
        method: 'POST',
        body: JSON.stringify({ channel_url: args }),
      });
      addMessage('assistant', `<div class="cmd-success">✅ Subscribed to ${escapeHtml(data.channel_name)}. Auto-ingesting every 6h.</div>`, true);
      showToast(`Subscribed to ${data.channel_name}`, 'success');
      return true;
    }
    case 'ytunsub': {
      const data = await api('/yt/unsubscribe', {
        method: 'POST',
        body: JSON.stringify({ sub_id: parseInt(args) }),
      });
      const ok = data.status === 'ok';
      addMessage('assistant', `<div class="${ok ? 'cmd-success' : 'cmd-error'}">${ok ? '✅ Unsubscribed.' : '❌ Not found.'}</div>`, true);
      if (ok) showToast('Unsubscribed', 'success');
      return true;
    }
    case 'ytsubs': {
      const subs = await api('/yt/subscriptions');
      if (subs.length === 0) {
        addMessage('assistant', '<em>No active subscriptions.</em>', true);
        return true;
      }
      let html = '<div class="cmd-results-title">Subscriptions</div>';
      subs.forEach((s) => {
        html += `<div class="sub-item">
          <div class="sub-name">${escapeHtml(s.channel_name)}</div>
          <div class="sub-meta">Last checked: ${s.last_checked || 'never'} &middot; ID: ${s.id}</div>
        </div>`;
      });
      addMessage('assistant', html, true);
      return true;
    }
    default:
      return false;
  }
}

async function handleReflectionCommand(command, args) {
  if (command !== 'reflections' && command !== 'reflection-today') return false;

  if (command === 'reflections') {
    const refs = await api('/api/reflections');
    if (!refs || refs.length === 0) {
      addMessage('assistant', '<em>No daily reflections yet. They are generated automatically each day.</em>', true);
      return true;
    }
    let html = '<div class="cmd-results-title">Daily Reflections</div>';
    refs.forEach((r) => {
      const topics = r.topics || [];
      const topicTags = topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join(' ');
      html += `<div class="ref-item">
        <div class="ref-date">${escapeHtml(r.date)}</div>
        <div class="ref-summary">${marked.parse(r.summary)}</div>
        ${topicTags ? `<div class="ref-topics">${topicTags}</div>` : ''}
      </div>`;
    });
    addMessage('assistant', html, true);
    return true;
  }

  if (command === 'reflection-today') {
    let ref = await api('/api/reflection/today');
    if (!ref) {
      addMessage('assistant', '<em>No reflection for today yet. Generating now...</em>', true);
      ref = await api('/api/reflection/generate', { method: 'POST' });
    }
    if (!ref || ref.error) {
      addMessage('assistant', `<div class="cmd-warning">${escapeHtml(ref?.error || 'No messages today to reflect on.')}</div>`, true);
      return true;
    }
    const topics = ref.topics || [];
    const topicTags = topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join(' ');
    let html = `<div class="cmd-results-title">Today's Reflection</div>
      <div class="ref-summary">${marked.parse(ref.summary)}</div>`;
    if (topicTags) {
      html += `<div class="ref-topics">${topicTags}</div>`;
    }
    addMessage('assistant', html, true);
    return true;
  }

  return false;
}

async function handleKGCommand(command, args) {
  if (command !== 'kg') return false;
  const sub = args.split(' ')[0];
  const rest = args.slice(sub.length).trim();

  switch (sub) {
    case 'extract': {
      await api('/kg/extract', {
        method: 'POST',
        body: JSON.stringify({ triples: [[rest, 'related to', 'topic']] }),
      });
      addMessage('assistant', '<div class="cmd-success">✅ Relationships extracted.</div>', true);
      showToast('Relationships extracted', 'success');
      return true;
    }
    case 'add': {
      const parts = rest.split(',').map((s) => s.trim());
      const data = await api('/kg/entity', {
        method: 'POST',
        body: JSON.stringify({ name: parts[0], type: parts[1] || 'concept', description: parts[2] || '' }),
      });
      addMessage('assistant', `<div class="cmd-success">✅ Created entity: ${escapeHtml(data.name)} (ID: ${data.id})</div>`, true);
      return true;
    }
    case 'relate': {
      const parts = rest.split('|').map((s) => s.trim());
      if (parts.length < 2) {
        addMessage('assistant', '<div class="cmd-warning">Usage: /kg relate source | target | relation</div>', true);
        return true;
      }
      const data = await api('/kg/relation', {
        method: 'POST',
        body: JSON.stringify({ source_name: parts[0], target_name: parts[1], relationship_type: parts[2] || 'related to' }),
      });
      addMessage('assistant', `<div class="cmd-success">✅ Related ${escapeHtml(parts[0])} → ${escapeHtml(parts[1])}</div>`, true);
      return true;
    }
    case 'list': {
      const entities = await api('/kg/entities');
      if (entities.length === 0) {
        addMessage('assistant', '<em>No entities in the knowledge graph.</em>', true);
        return true;
      }
      let html = '<div class="cmd-results-title">Knowledge Graph Entities</div>';
      entities.forEach((e, i) => {
        html += `<div class="entity-item">
          <div class="entity-num">${i + 1}</div>
          <div class="entity-info">
            <div class="entity-name">${escapeHtml(e.name)}</div>
            <div class="entity-desc">${escapeHtml(e.type)}${e.description ? ` — ${escapeHtml(e.description)}` : ''}</div>
          </div>
        </div>`;
      });
      addMessage('assistant', html, true);
      return true;
    }
    default:
      addMessage('assistant', '<em>KG commands: extract &lt;text&gt;, add &lt;name&gt;[,type,desc], relate src | tgt | rel, list</em>', true);
      return true;
  }
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || isSending) return;

  if (text.startsWith('/')) {
    const spaceIdx = text.indexOf(' ');
    const command = spaceIdx === -1 ? text.slice(1) : text.slice(1, spaceIdx);
    const args = spaceIdx === -1 ? '' : text.slice(spaceIdx + 1);
    addMessage('user', text);
    input.value = '';
    resetInputHeight();

    try {
      if (await handleYTCommand(command, args)) return;
      if (await handleReflectionCommand(command, args)) return;
      if (await handleKGCommand(command, args)) return;
    } catch (err) {
      addMessage('assistant', `<div class="cmd-error">❌ ${escapeHtml(err.message)}</div>`, true);
      showToast(err.message, 'error');
      return;
    }

    addMessage('assistant', `<em>Unknown command: /${escapeHtml(command)}</em>`, true);
    return;
  }

  addMessage('user', text);
  input.value = '';
  resetInputHeight();
  isSending = true;
  sendBtn.disabled = true;
  sendIcon.style.display = 'none';
  sendSpinner.style.display = 'block';
  showTypingIndicator();

  try {
    const data = await api('/chat/send', {
      method: 'POST',
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });
    sessionId = data.session_id;
    removeTypingIndicator();
    addMessage('assistant', data.reply, false, data.sources || null);
    if (data.suggestion) {
      showSuggestion(data.suggestion);
    }
    loadSessions();
  } catch (err) {
    removeTypingIndicator();
    addMessage('assistant', `<div class="cmd-error">Error: ${escapeHtml(err.message)}</div>`, true);
    showToast(err.message, 'error');
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    sendIcon.style.display = 'block';
    sendSpinner.style.display = 'none';
    input.focus();
  }
}

function resetInputHeight() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
}

async function loadSessions() {
  const sessions = await api('/sessions');
  sessionListEl.innerHTML = '';
  sessions.forEach((s) => {
    const item = document.createElement('div');
    const isActive = s.session_id === sessionId;
    item.className = `session-item ${isActive ? 'active' : ''}`;
    item.innerHTML = `
      <div class="session-item-title">${escapeHtml(s.title || '(empty)')}</div>
      <div class="session-item-meta">${s.message_count} messages</div>
    `;
    item.addEventListener('click', () => loadSession(s.session_id));
    sessionListEl.appendChild(item);
  });
}

async function loadSession(id) {
  sessionId = id;
  const data = await api(`/chat/history?session_id=${id}`);
  messagesEl.innerHTML = '';
  data.messages.forEach((m) => addMessage(m.role, m.content));
  loadSessions();
  if (window.innerWidth < 768) {
    sidebar.dataset.open = 'false';
    sidebarOverlay.classList.remove('active');
  }
}

async function performSearch(query) {
  const results = await api(`/search?q=${encodeURIComponent(query)}`);
  messagesEl.innerHTML = '';
  if (results.length === 0) {
    addMessage('assistant', `No messages found for "${query}"`);
    return;
  }
  let html = `<div class="cmd-results-title">Search results for "${escapeHtml(query)}"</div>`;
  results.forEach((m) => {
    const source = m._source || 'semantic';
    html += `<div class="search-result" data-sid="${escapeHtml(m.session_id)}">
      <div class="search-source">${source}</div>
      <div class="search-content">${escapeHtml(m.content.slice(0, 200))}${m.content.length > 200 ? '...' : ''}</div>
    </div>`;
  });
  addMessage('assistant', html, true);
  document.querySelectorAll('.search-result').forEach((el) => {
    el.addEventListener('click', () => loadSession(el.dataset.sid));
  });
}

input.addEventListener('input', () => {
  resetInputHeight();
  sendBtn.disabled = !input.value.trim();
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

const debouncedSearch = debounce(async (query) => {
  if (query) await performSearch(query);
  else loadSessions();
}, 400);

searchInput.addEventListener('input', (e) => {
  debouncedSearch(e.target.value.trim());
});

function openSidebar() {
  sidebar.dataset.open = 'true';
  sidebarOverlay.classList.add('active');
}

function closeSidebar() {
  sidebar.dataset.open = 'false';
  sidebarOverlay.classList.remove('active');
}

sidebarToggle?.addEventListener('click', openSidebar);
sidebarClose?.addEventListener('click', closeSidebar);
sidebarOverlay?.addEventListener('click', closeSidebar);

newChatBtn?.addEventListener('click', () => {
  sessionId = null;
  messagesEl.innerHTML = '';
  if (emptyState) messagesEl.appendChild(emptyState);
  loadSessions();
  input.focus();
  if (window.innerWidth < 768) closeSidebar();
});

themeToggle?.addEventListener('click', () => {
  const isLight = document.body.classList.toggle('light');
  themeIconDark.style.display = isLight ? 'none' : '';
  themeIconLight.style.display = isLight ? '' : 'none';
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
});

const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
  document.body.classList.add('light');
  themeIconDark.style.display = 'none';
  themeIconLight.style.display = '';
}

loadSessions();
