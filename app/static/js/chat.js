import { escapeHtml, api, debounce, formatDate, truncate, showToast } from './utils.js';

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
const themeToggle = document.getElementById('theme-toggle');
const themeIconDark = document.getElementById('theme-icon-dark');
const themeIconLight = document.getElementById('theme-icon-light');
const newChatBtn = document.getElementById('new-chat-btn');

function addMessage(role, content, isHtml = false) {
  emptyState?.remove();
  const div = document.createElement('div');
  div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`;

  const isUser = role === 'user';
  const maxWidth = role === 'user' ? 'max-w-[75%]' : 'max-w-[85%] md:max-w-[75%]';

  const bubble = document.createElement('div');
  bubble.className = `${maxWidth} px-4 py-3 rounded-2xl text-sm leading-relaxed message-content ${
    isUser
      ? 'rounded-br-md'
      : 'rounded-bl-md'
  }`;

  Object.assign(bubble.style, {
    background: isUser ? 'var(--user-bubble)' : 'var(--assistant-bubble)',
    color: isUser ? 'white' : 'var(--text)',
    border: isUser ? 'none' : '1px solid var(--border)',
  });

  if (isHtml) {
    bubble.innerHTML = content;
  } else {
    bubble.textContent = content;
  }

  if (role === 'assistant' && !isHtml) {
    const rendered = marked.parse(content);
    bubble.innerHTML = rendered;
    applyCodeBlocks(bubble);
  }

  div.appendChild(bubble);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function applyCodeBlocks(container) {
  container.querySelectorAll('pre code').forEach((block) => {
    const pre = block.parentElement;
    pre.style.position = 'relative';
    pre.style.background = 'var(--elevated)';
    pre.style.border = '1px solid var(--border)';
    pre.style.borderRadius = 'var(--radius-md)';
    pre.style.padding = '16px';
    pre.style.overflow = 'auto';
    pre.style.fontSize = '12px';
    pre.style.lineHeight = '1.6';
    pre.style.margin = '8px 0';

    const copyBtn = document.createElement('button');
    copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="4" y="4" width="10" height="10" rx="1"/><path d="M1 11V3a2 2 0 012-2h8"/></svg>';
    copyBtn.title = 'Copy code';
    Object.assign(copyBtn.style, {
      position: 'absolute', top: '8px', right: '8px',
      width: '28px', height: '28px', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      border: '1px solid var(--border)', borderRadius: '6px',
      background: 'var(--surface)', cursor: 'pointer',
      color: 'var(--text-secondary)', transition: 'all 0.15s',
    });
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(block.textContent);
      copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 15 15" fill="none" stroke="#22C55E" stroke-width="1.5"><path d="M3 8l3 3 6-6"/></svg>';
      setTimeout(() => {
        copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="4" y="4" width="10" height="10" rx="1"/><path d="M1 11V3a2 2 0 012-2h8"/></svg>';
      }, 2000);
    };
    pre.appendChild(copyBtn);
  });

  container.querySelectorAll('table').forEach((table) => {
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.fontSize = '13px';
    table.style.margin = '8px 0';
    table.querySelectorAll('th, td').forEach((cell) => {
      cell.style.border = '1px solid var(--border)';
      cell.style.padding = '8px 12px';
      cell.style.textAlign = 'left';
    });
    table.querySelectorAll('th').forEach((th) => {
      th.style.background = 'var(--elevated)';
      th.style.fontWeight = '600';
    });
  });

  container.querySelectorAll('blockquote').forEach((q) => {
    q.style.borderLeft = '3px solid var(--accent)';
    q.style.paddingLeft = '12px';
    q.style.margin = '8px 0';
    q.style.opacity = '0.8';
  });
}

function showTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'flex justify-start animate-fade-in';
  div.id = 'typing-indicator';
  const bubble = document.createElement('div');
  bubble.className = 'px-4 py-4 rounded-2xl rounded-bl-md flex gap-1.5 items-center';
  Object.assign(bubble.style, {
    background: 'var(--assistant-bubble)',
    border: '1px solid var(--border)',
  });
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.style.cssText = `width:7px;height:7px;border-radius:50%;background:var(--text-tertiary);display:inline-block;animation:pulse-dot 1.4s infinite ease-in-out both;animation-delay:${-0.32 + i * 0.16}s`;
    bubble.appendChild(dot);
  }
  div.appendChild(bubble);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById('typing-indicator')?.remove();
}

function markdownToHtml(text) {
  return marked.parse(text);
}

async function handleYTCommand(command, args) {
  switch (command) {
    case 'ytsearch': {
      const results = await api(`/yt/search?q=${encodeURIComponent(args)}`);
      let html = '<div class="space-y-2">';
      html += '<div class="font-semibold text-sm mb-3" style="color:var(--cyan);">YouTube Search Results</div>';
      results.forEach((v, i) => {
        html += `<div class="p-3 rounded-xl" style="background:var(--elevated);border:1px solid var(--border);">
          <div class="font-semibold text-sm mb-1">${escapeHtml(v.title)}</div>
          <div class="text-xs mb-2" style="color:var(--text-secondary);">${escapeHtml(v.channel)} &middot; ${v.published_at || ''}</div>
          <div class="flex gap-2">
            <button class="yt-ingest-btn text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-150 hover:opacity-90 active:scale-95" style="background:var(--accent);color:white;" data-url="${escapeHtml(v.url)}">Ingest</button>
            <a href="${escapeHtml(v.url)}" target="_blank" class="text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-150" style="background:var(--elevated);border:1px solid var(--border);color:var(--text-secondary);">Watch</a>
          </div>
        </div>`;
      });
      html += '</div>';
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
            e.target.style.background = 'var(--success)';
            showToast('Video ingested successfully', 'success');
          } catch {
            e.target.textContent = 'Failed';
            e.target.style.background = 'var(--error)';
            showToast('Ingestion failed', 'error');
          }
        });
      });
      return true;
    }
    case 'ytchannel': {
      addMessage('assistant', '<div class="flex items-center gap-2"><svg width="16" height="16" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="7.5" cy="7.5" r="5" stroke-dasharray="10" stroke-dashoffset="3" style="animation:spin 0.8s linear infinite;transform-origin:center"/></svg> Fetching channel videos...</div>', true);
      const data = await api('/yt/channel', {
        method: 'POST',
        body: JSON.stringify({ channel_url: args }),
      });
      removeTypingIndicator();
      addMessage('assistant', `<div style="color:var(--success);">✅ Ingested ${data.ingested_count} videos from channel.</div>`, true);
      showToast(`Ingested ${data.ingested_count} videos`, 'success');
      return true;
    }
    case 'ytsub': {
      const data = await api('/yt/subscribe', {
        method: 'POST',
        body: JSON.stringify({ channel_url: args }),
      });
      addMessage('assistant', `<div style="color:var(--success);">✅ Subscribed to ${escapeHtml(data.channel_name)}. Auto-ingesting every 6h.</div>`, true);
      showToast(`Subscribed to ${data.channel_name}`, 'success');
      return true;
    }
    case 'ytunsub': {
      const data = await api('/yt/unsubscribe', {
        method: 'POST',
        body: JSON.stringify({ sub_id: parseInt(args) }),
      });
      const ok = data.status === 'ok';
      addMessage('assistant', `<div style="color:${ok ? 'var(--success)' : 'var(--error)'};">${ok ? '✅ Unsubscribed.' : '❌ Not found.'}</div>`, true);
      if (ok) showToast('Unsubscribed', 'success');
      return true;
    }
    case 'ytsubs': {
      const subs = await api('/yt/subscriptions');
      if (subs.length === 0) {
        addMessage('assistant', '<div style="color:var(--text-secondary);">No active subscriptions.</div>', true);
        return true;
      }
      let html = '<div class="font-semibold text-sm mb-3" style="color:var(--cyan);">Subscriptions</div>';
      subs.forEach((s) => {
        html += `<div class="p-3 rounded-xl mb-2" style="background:var(--elevated);border:1px solid var(--border);">
          <div class="font-medium text-sm">${escapeHtml(s.channel_name)}</div>
          <div class="text-xs mt-1" style="color:var(--text-secondary);">Last checked: ${s.last_checked || 'never'} &middot; ID: ${s.id}</div>
        </div>`;
      });
      addMessage('assistant', html, true);
      return true;
    }
    default:
      return false;
  }
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
      addMessage('assistant', '<div style="color:var(--success);">✅ Relationships extracted.</div>', true);
      showToast('Relationships extracted', 'success');
      return true;
    }
    case 'add': {
      const parts = rest.split(',').map((s) => s.trim());
      const data = await api('/kg/entity', {
        method: 'POST',
        body: JSON.stringify({ name: parts[0], type: parts[1] || 'concept', description: parts[2] || '' }),
      });
      addMessage('assistant', `<div style="color:var(--success);">✅ Created entity: ${escapeHtml(data.name)} (ID: ${data.id})</div>`, true);
      return true;
    }
    case 'relate': {
      const parts = rest.split('|').map((s) => s.trim());
      if (parts.length < 2) {
        addMessage('assistant', '<div style="color:var(--warning);">Usage: /kg relate source | target | relation</div>', true);
        return true;
      }
      const data = await api('/kg/relation', {
        method: 'POST',
        body: JSON.stringify({ source_name: parts[0], target_name: parts[1], relationship_type: parts[2] || 'related to' }),
      });
      addMessage('assistant', `<div style="color:var(--success);">✅ Related ${escapeHtml(parts[0])} → ${escapeHtml(parts[1])}</div>`, true);
      return true;
    }
    case 'list': {
      const entities = await api('/kg/entities');
      if (entities.length === 0) {
        addMessage('assistant', '<div style="color:var(--text-secondary);">No entities in the knowledge graph.</div>', true);
        return true;
      }
      let html = '<div class="font-semibold text-sm mb-3" style="color:var(--cyan);">Knowledge Graph Entities</div>';
      entities.forEach((e, i) => {
        html += `<div class="flex items-center gap-3 p-2.5 rounded-lg mb-1.5" style="background:var(--elevated);border:1px solid var(--border);">
          <span class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0" style="background:var(--accent-soft);color:var(--accent);">${i + 1}</span>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">${escapeHtml(e.name)}</div>
            <div class="text-xs" style="color:var(--text-secondary);">${escapeHtml(e.type)}${e.description ? ` — ${escapeHtml(e.description)}` : ''}</div>
          </div>
        </div>`;
      });
      addMessage('assistant', html, true);
      return true;
    }
    default:
      addMessage('assistant', `<div class="text-sm" style="color:var(--text-secondary);">KG commands: extract &lt;text&gt;, add &lt;name&gt;[,type,desc], relate src | tgt | rel, list</div>`, true);
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
    input.style.height = 'auto';

    try {
      if (await handleYTCommand(command, args)) return;
      if (await handleKGCommand(command, args)) return;
    } catch (err) {
      addMessage('assistant', `<div style="color:var(--error);">❌ ${escapeHtml(err.message)}</div>`, true);
      showToast(err.message, 'error');
      return;
    }

    addMessage('assistant', `<div style="color:var(--text-secondary);">Unknown command: /${escapeHtml(command)}</div>`, true);
    return;
  }

  addMessage('user', text);
  input.value = '';
  input.style.height = 'auto';
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
    addMessage('assistant', data.reply);
    loadSessions();
  } catch (err) {
    removeTypingIndicator();
    addMessage('assistant', `<div style="color:var(--error);">Error: ${escapeHtml(err.message)}</div>`, true);
    showToast(err.message, 'error');
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    sendIcon.style.display = 'block';
    sendSpinner.style.display = 'none';
    input.focus();
  }
}

async function loadSessions() {
  const sessions = await api('/sessions');
  sessionListEl.innerHTML = '';
  sessions.forEach((s) => {
    const item = document.createElement('div');
    const isActive = s.session_id === sessionId;
    item.className = `px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 ${isActive ? 'font-medium' : ''}`;
    Object.assign(item.style, {
      background: isActive ? 'var(--accent-soft)' : 'transparent',
      color: isActive ? 'var(--accent)' : 'var(--text)',
    });
    item.onmouseenter = () => { if (!isActive) item.style.background = 'rgba(255,255,255,0.03)'; };
    item.onmouseleave = () => { if (!isActive) item.style.background = 'transparent'; };

    const title = document.createElement('div');
    title.className = 'text-sm truncate';
    title.textContent = s.title || '(empty)';

    const meta = document.createElement('div');
    meta.className = 'text-xs mt-0.5';
    meta.style.color = 'var(--text-tertiary)';
    meta.textContent = `${s.message_count} messages`;

    item.appendChild(title);
    item.appendChild(meta);
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
  }
}

async function performSearch(query) {
  const results = await api(`/search?q=${encodeURIComponent(query)}`);
  messagesEl.innerHTML = '';
  if (results.length === 0) {
    addMessage('assistant', `No messages found for "${query}"`);
    return;
  }
  let html = `<div class="font-semibold text-sm mb-3" style="color:var(--cyan);">Search results for "${escapeHtml(query)}"</div>`;
  results.forEach((m) => {
    const source = m._source || 'semantic';
    const badgeColor = source === 'hybrid' ? 'var(--accent)' : source === 'semantic' ? 'var(--cyan)' : 'var(--warning)';
    html += `<div class="p-3 rounded-xl mb-2 cursor-pointer transition-all duration-150 hover:opacity-80" style="background:var(--elevated);border:1px solid var(--border);" data-sid="${escapeHtml(m.session_id)}">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded" style="background:${badgeColor}20;color:${badgeColor};">${source}</span>
        <span class="text-xs" style="color:var(--text-tertiary);">${escapeHtml(m.session_id.slice(0, 8))}...</span>
      </div>
      <div class="text-sm">${escapeHtml(m.content.slice(0, 200))}${m.content.length > 200 ? '...' : ''}</div>
    </div>`;
  });
  addMessage('assistant', html, true);
  document.querySelectorAll('[data-sid]').forEach((el) => {
    el.addEventListener('click', () => loadSession(el.dataset.sid));
  });
}

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
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

sidebarToggle?.addEventListener('click', () => {
  sidebar.dataset.open = 'true';
});

sidebarClose?.addEventListener('click', () => {
  sidebar.dataset.open = 'false';
});

newChatBtn?.addEventListener('click', () => {
  sessionId = null;
  messagesEl.innerHTML = '';
  messagesEl.appendChild(emptyState);
  loadSessions();
  input.focus();
});

themeToggle?.addEventListener('click', () => {
  const isDark = document.documentElement.classList.toggle('dark');
  document.body.classList.toggle('dark', isDark);
  document.body.classList.toggle('light', !isDark);
  themeIconDark.style.display = isDark ? '' : 'none';
  themeIconLight.style.display = isDark ? 'none' : '';
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
});

const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
  document.documentElement.classList.remove('dark');
  document.body.classList.remove('dark');
  document.body.classList.add('light');
  themeIconDark.style.display = 'none';
  themeIconLight.style.display = '';
}

loadSessions();
