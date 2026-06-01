var network = null;
var nodes = new vis.DataSet([]);
var edges = new vis.DataSet([]);
var allData = { nodes: [], edges: [] };
var themes = ['tokyo-night', 'light', 'github-dark', 'obsidian'];
var themeIndex = 0;

var container = document.getElementById('graph-container');
var searchInput = document.getElementById('search-input');
var nodeCountEl = document.getElementById('node-count');
var edgeCountEl = document.getElementById('edge-count');
var sidebarContent = document.getElementById('sidebar-content');

async function loadGraph() {
  var resp = await fetch('/kg/graph');
  allData = await resp.json();
  nodes = new vis.DataSet(allData.nodes);
  edges = new vis.DataSet(allData.edges);
  nodeCountEl.textContent = allData.nodes.length;
  edgeCountEl.textContent = allData.edges.length;

  var options = {
    nodes: {
      shape: 'dot',
      size: 20,
      font: { color: '#a9b1d6', size: 13 },
      borderWidth: 0,
      color: {
        background: '#5a7fd4',
        border: '#5a7fd4',
        highlight: { background: '#7aa2f7', border: '#7aa2f7' },
      },
      shadow: { enabled: true, color: 'rgba(90,127,212,0.4)', size: 10 },
    },
    edges: {
      width: 1.5,
      color: { color: 'rgba(137,148,188,0.5)', highlight: 'rgba(122,162,247,0.8)', hover: 'rgba(122,162,247,0.6)' },
      smooth: { enabled: true, type: 'continuous' },
      font: {
        color: '#565870', size: 11,
        background: 'rgba(26,27,38,0.9)', strokeWidth: 0,
      },
      shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 4 },
    },
    physics: {
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -40, centralGravity: 0.005, springLength: 180, springConstant: 0.02 },
      stabilization: { iterations: 100 },
    },
    interaction: { hover: true, tooltipDelay: 200, navigationButtons: false, keyboard: true },
    layout: { improvedLayout: true },
  };

  network = new vis.Network(container, { nodes: nodes, edges: edges }, options);

  network.on('click', function(params) {
    if (params.nodes.length > 0) {
      showNodeDetails(params.nodes[0]);
      network.selectNodes([params.nodes[0]]);
    } else {
      clearSidebar();
    }
  });

  network.on('doubleClick', function(params) {
    if (params.nodes.length > 0) {
      network.focus(params.nodes[0], { scale: 1.5, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }
  });

  searchInput.addEventListener('input', function() {
    var q = this.value.trim();
    if (!q) return;
    var matching = allData.nodes.filter(function(n) { return n.label.toLowerCase().indexOf(q.toLowerCase()) !== -1; });
    if (matching.length > 0) {
      network.focus(matching[0].id, { scale: 1.5, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
      network.selectNodes([matching[0].id]);
      showNodeDetails(matching[0].id);
    }
  });
}

function showNodeDetails(nodeId) {
  var node = allData.nodes.find(function(n) { return n.id === nodeId; });
  if (!node) return;
  var rels = allData.edges.filter(function(e) { return e.from === nodeId || e.to === nodeId; });
  var colors = ['#5a7fd4', '#8b5cf6', '#6bae44', '#d4872e', '#d4506a', '#4db8e8', '#c8943a'];
  var color = colors[nodeId % colors.length];

  var relHtml = '';
  rels.forEach(function(r) {
    var isSource = r.from === nodeId;
    var otherId = isSource ? r.to : r.from;
    var other = allData.nodes.find(function(n) { return n.id === otherId; });
    var direction = isSource ? '\u2192' : '\u2190';
    relHtml += '<div class="sidebar-rel-item" onclick="showNodeDetails(' + otherId + ')">' +
      '<div class="sidebar-rel-dot" style="background:' + color + '"></div>' +
      '<div><div class="sidebar-rel-name">' + (r.label || 'related to') + '</div>' +
      '<div class="sidebar-rel-target">' + direction + ' ' + (other ? other.label : 'unknown') + '</div></div></div>';
  });

  sidebarContent.innerHTML =
    '<div><div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">' +
    '<div class="sidebar-node-icon" style="background:' + color + '">' + node.label.charAt(0).toUpperCase() + '</div>' +
    '<div><div class="sidebar-node-name">' + node.label + '</div>' +
    '<div class="sidebar-node-type">' + (node.title || 'concept') + '</div></div></div>' +
    '<div class="sidebar-node-desc">' + (node.description || 'No description') + '</div>' +
    '<div class="sidebar-section-title">Relationships</div>' +
    (relHtml || '<div style="color:#565870;font-size:12px">None</div>') +
    '<div class="sidebar-actions">' +
    '<button class="sidebar-btn sidebar-btn-focus" onclick="network.focus(' + nodeId + ',{scale:1.5,animation:{duration:400,easingFunction:\'easeInOutQuad\'}})">Focus</button>' +
    '<button class="sidebar-btn sidebar-btn-delete" onclick="deleteEntity(' + nodeId + ')">Delete</button></div></div>';
}

function clearSidebar() {
  sidebarContent.innerHTML = '<div class="sidebar-empty">Select a node to view details</div>';
}

async function deleteEntity(id) {
  if (!confirm('Delete this entity and all its relationships?')) return;
  await fetch('/kg/entity/' + id, { method: 'DELETE' });
  loadGraph();
  clearSidebar();
}

document.getElementById('zoom-in').addEventListener('click', function() {
  var scale = network.getScale();
  network.moveTo({ scale: scale * 1.3, animation: { duration: 200, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('zoom-out').addEventListener('click', function() {
  var scale = network.getScale();
  network.moveTo({ scale: scale * 0.7, animation: { duration: 200, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('zoom-reset').addEventListener('click', function() {
  network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
});

document.getElementById('theme-toggle').addEventListener('click', function() {
  themeIndex = (themeIndex + 1) % themes.length;
  document.body.className = 'theme-' + themes[themeIndex];
});

loadGraph();
