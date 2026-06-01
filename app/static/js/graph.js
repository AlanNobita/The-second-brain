var network = null;
var nodes = new vis.DataSet([]);
var edges = new vis.DataSet([]);
var allData = { nodes: [], edges: [] };

var container = document.getElementById('graph-container');
var searchInput = document.getElementById('search-input');
var nodeCountEl = document.getElementById('node-count');
var edgeCountEl = document.getElementById('edge-count');
var sidebarContent = document.getElementById('sidebar-content');
var searchTimer;

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function themeColors() {
  return {
    text: cssVar('--text'),
    textSecondary: cssVar('--text-secondary'),
    textTertiary: cssVar('--text-tertiary'),
    accent: cssVar('--accent'),
    elevated: cssVar('--elevated'),
    border: cssVar('--border'),
    surface: cssVar('--surface'),
    accentSoft: cssVar('--accent-soft'),
    cyan: cssVar('--cyan'),
  };
}

var typeColors = {
  python: '#6366F1',
  framework: '#8B5CF6',
  database: '#22C55E',
  concept: '#F59E0B',
  tool: '#EF4444',
  library: '#06B6D4',
  language: '#EAB308',
  algorithm: '#6366F1',
  system: '#22C55E',
  protocol: '#A855F7',
};

function getNodeColor(type) {
  var t = (type || 'concept').toLowerCase();
  return typeColors[t] || cssVar('--text-tertiary');
}

async function loadGraph() {
  var resp = await fetch('/kg/graph');
  allData = await resp.json();
  nodes = new vis.DataSet(allData.nodes);
  edges = new vis.DataSet(allData.edges);
  nodeCountEl.textContent = allData.nodes.length;
  edgeCountEl.textContent = allData.edges.length;

  var colors = themeColors();

  var options = {
    nodes: {
      shape: 'dot',
      size: 18,
      font: { color: colors.text, size: 12, face: 'Inter, system-ui, sans-serif' },
      borderWidth: 0,
      color: {
        background: colors.accent,
        border: colors.accent,
        highlight: { background: colors.accent, border: colors.accent },
      },
      shadow: { enabled: true, color: 'rgba(99,102,241,0.3)', size: 8 },
    },
    edges: {
      width: 1.2,
      color: { color: colors.textTertiary, highlight: colors.accent, hover: colors.accent },
      smooth: { enabled: true, type: 'continuous' },
      font: {
        color: colors.textSecondary, size: 10,
        background: cssVar('--deep'),
        strokeWidth: 0,
        face: 'Inter, system-ui, sans-serif',
      },
      shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 4 },
    },
    physics: {
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -40,
        centralGravity: 0.005,
        springLength: 180,
        springConstant: 0.02,
      },
      stabilization: { iterations: 80 },
    },
    interaction: { hover: true, tooltipDelay: 200, keyboard: true },
  };

  network = new vis.Network(container, { nodes: nodes, edges: edges }, options);

  allData.nodes.forEach(function (n) {
    var c = getNodeColor(n.title || 'concept');
    nodes.update({ id: n.id, color: { background: c, border: c } });
  });

  network.on('click', function (params) {
    if (params.nodes.length > 0) {
      showNodeDetails(params.nodes[0]);
      network.selectNodes([params.nodes[0]]);
    } else {
      clearSidebar();
    }
  });

  network.on('doubleClick', function (params) {
    if (params.nodes.length > 0) {
      var nodeId = params.nodes[0];
      var connected = allData.edges.filter(function (e) { return e.from === nodeId || e.to === nodeId; });
      var connectedIds = new Set();
      connectedIds.add(nodeId);
      connected.forEach(function (e) { connectedIds.add(e.from === nodeId ? e.to : e.from); });
      var visibleNodes = allData.nodes.filter(function (n) { return connectedIds.has(n.id); });
      nodes.clear();
      edges.clear();
      nodes.add(visibleNodes);
      edges.add(connected);
      visibleNodes.forEach(function (n) {
        var c = getNodeColor(n.title || 'concept');
        nodes.update({ id: n.id, color: { background: c, border: c } });
      });
      network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }
  });

  network.on('stabilizationIterationsDone', function () {
    network.setOptions({ physics: { enabled: false } });
  });

  searchInput.addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      var q = searchInput.value.trim();
      if (!q) return;
      var matching = allData.nodes.filter(function (n) {
        return n.label.toLowerCase().indexOf(q.toLowerCase()) !== -1;
      });
      if (matching.length > 0) {
        network.focus(matching[0].id, { scale: 1.5, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
        network.selectNodes([matching[0].id]);
        showNodeDetails(matching[0].id);
      }
    }, 300);
  });
}

function showNodeDetails(nodeId) {
  var node = allData.nodes.find(function (n) { return n.id === nodeId; });
  if (!node) return;
  var rels = allData.edges.filter(function (e) { return e.from === nodeId || e.to === nodeId; });
  var color = getNodeColor(node.title || 'concept');

  var relHtml = '';
  rels.forEach(function (r) {
    var isSource = r.from === nodeId;
    var otherId = isSource ? r.to : r.from;
    var other = allData.nodes.find(function (n) { return n.id === otherId; });
    var direction = isSource ? '→' : '←';
    var otherColor = other ? getNodeColor(other.title || 'concept') : color;
    relHtml += '<div class="sidebar-rel-item" onclick="showNodeDetails(' + otherId + ')">' +
      '<div style="width:6px;height:6px;border-radius:50%;background:' + otherColor + ';flex-shrink:0;"></div>' +
      '<div style="flex:1;min-width:0;">' +
      '<div class="sidebar-rel-name">' + (r.label || 'related to') + '</div>' +
      '<div class="sidebar-rel-target">' + direction + ' ' + (other ? other.label : 'unknown') + '</div></div></div>';
  });

  sidebarContent.innerHTML =
    '<div>' +
    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">' +
    '<div style="width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;color:white;font-size:14px;font-weight:600;flex-shrink:0;background:' + color + ';">' +
    (node.label ? node.label.charAt(0).toUpperCase() : '?') + '</div>' +
    '<div><div class="sidebar-node-name">' + (node.label || 'Unknown') + '</div>' +
    '<div class="sidebar-node-type">' + (node.title || 'concept') + '</div></div></div>' +
    '<div class="sidebar-node-desc">' + (node.description || 'No description') + '</div>' +
    '<div class="sidebar-section-title">Relationships</div>' +
    (relHtml || '<div style="font-size:12px;color:var(--text-tertiary);">None</div>') +
    '<div style="display:flex;gap:8px;margin-top:20px;">' +
    '<button class="sidebar-btn sidebar-btn-focus" onclick="network.focus(' + nodeId + ',{scale:1.5,animation:{duration:400,easingFunction:\'easeInOutQuad\'}})">Focus</button>' +
    '<button class="sidebar-btn sidebar-btn-delete" onclick="deleteEntity(' + nodeId + ')">Delete</button></div></div>';
}

function clearSidebar() {
  sidebarContent.innerHTML = '<div class="text-sm text-center py-12" style="color:var(--text-tertiary);">Select a node to view details</div>';
}

async function deleteEntity(id) {
  if (!confirm('Delete this entity and all its relationships?')) return;
  await fetch('/kg/entity/' + id, { method: 'DELETE' });
  allData.nodes = allData.nodes.filter(function (n) { return n.id !== id; });
  allData.edges = allData.edges.filter(function (e) { return e.from !== id && e.to !== id; });
  loadGraph();
  clearSidebar();
}

document.getElementById('zoom-in').addEventListener('click', function () {
  var scale = network.getScale();
  network.moveTo({ scale: scale * 1.3, animation: { duration: 200, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('zoom-out').addEventListener('click', function () {
  var scale = network.getScale();
  network.moveTo({ scale: scale * 0.7, animation: { duration: 200, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('zoom-reset').addEventListener('click', function () {
  nodes.clear();
  edges.clear();
  nodes.add(allData.nodes);
  edges.add(allData.edges);
  allData.nodes.forEach(function (n) {
    var c = getNodeColor(n.title || 'concept');
    nodes.update({ id: n.id, color: { background: c, border: c } });
  });
  network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('theme-toggle').addEventListener('click', function () {
  var isDark = document.documentElement.classList.toggle('dark');
  document.body.classList.toggle('dark', isDark);
  document.body.classList.toggle('light', !isDark);
  var iconDark = document.getElementById('theme-icon-dark');
  var iconLight = document.getElementById('theme-icon-light');
  iconDark.style.display = isDark ? '' : 'none';
  iconLight.style.display = isDark ? 'none' : '';
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  rebuildNetwork();
});

function rebuildNetwork() {
  if (!network) return;
  var colors = themeColors();
  network.setOptions({
    nodes: { font: { color: colors.text } },
    edges: { color: { color: colors.textTertiary }, font: { color: colors.textSecondary, background: cssVar('--deep') } },
  });
  allData.nodes.forEach(function (n) {
    var c = getNodeColor(n.title || 'concept');
    nodes.update({ id: n.id, font: { color: colors.text }, color: { background: c, border: c } });
  });
  allData.edges.forEach(function (e) {
    edges.update({ id: e.id, font: { color: colors.textSecondary } });
  });
  var selected = network.getSelectedNodes();
  if (selected.length > 0) showNodeDetails(selected[0]);
}

var savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
  document.documentElement.classList.remove('dark');
  document.body.classList.remove('dark');
  document.body.classList.add('light');
  document.getElementById('theme-icon-dark').style.display = 'none';
  document.getElementById('theme-icon-light').style.display = '';
}

loadGraph();
