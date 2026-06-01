export function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

export function $(id) {
  return document.getElementById(id);
}

export async function api(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export function debounce(fn, ms = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

export function truncate(text, len = 60) {
  return text.length > len ? text.slice(0, len) + '...' : text;
}

export function showToast(message, type = 'info', duration = 4000) {
  const existing = document.querySelector('.toast-container');
  let container = existing;
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed', bottom: '24px', right: '24px',
      zIndex: '9999', display: 'flex', flexDirection: 'column', gap: '8px',
    });
    document.body.appendChild(container);
  }

  const colors = {
    success: 'var(--success)',
    error: 'var(--error)',
    info: 'var(--accent)',
    warning: 'var(--warning)',
  };

  const toast = document.createElement('div');
  toast.className = 'animate-fade-in-up';
  Object.assign(toast.style, {
    background: 'var(--elevated)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)', padding: '12px 16px',
    fontSize: '13px', color: 'var(--text)',
    borderLeft: `3px solid ${colors[type] || colors.info}`,
    boxShadow: 'var(--shadow-md)',
    maxWidth: '360px', cursor: 'pointer',
  });
  toast.textContent = message;
  toast.onclick = () => toast.remove();
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.2s ease-out';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}
