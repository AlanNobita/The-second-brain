# Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Interactive knowledge graph visualization with LLM extraction, CRUD, and a polished `/graph` page.

**Architecture:** SQLite entities + relationships tables, Flask CRUD + LLM extraction routes, vis.js force-directed graph on a full-page `/graph` route. Tokyo Night dark theme with fluid entrance/hover animations.

**Tech Stack:** Python 3.11+, Flask, SQLite3, vis.js (CDN), OpenRouter (LLM extraction)

**Files to create/modify:**
| File | Action | Purpose |
|------|--------|---------|
| `app/models/kg_db.py` | Create | SQLite schema + CRUD queries |
| `app/services/kg_service.py` | Create | Business logic + LLM extraction |
| `app/routes/kg.py` | Create | 7 REST endpoints |
| `app/templates/graph.html` | Create | Full-page graph template |
| `app/static/js/graph.js` | Create | vis.js + interactions |
| `app/static/css/graph.css` | Create | Themes + animations |
| `app/__init__.py` | Modify | Register kg blueprint |
| `app/static/script.js` | Modify | Add `/kg` command routing |
| `tests/test_kg_db.py` | Create | 4 tests |
| `tests/test_kg_service.py` | Create | 6 tests |
| `tests/test_kg_routes.py` | Create | 4 tests |

---

### Task 1: Database Layer

**Files:**
- Create: `app/models/kg_db.py`
- Test: `tests/test_kg_db.py`

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_kg_db.py"""
import sqlite3
import pytest
from app.models.kg_db import init_kg_db, add_entity, get_all_entities, get_entity, add_relationship, get_all_relationships, delete_entity, delete_relationship, get_graph_data, search_entities, KG_DB_PATH


@pytest.fixture(autouse=True)
def clean_kg():
    init_kg_db()
    conn = sqlite3.connect(KG_DB_PATH)
    conn.execute("DELETE FROM relationships")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()


def test_init_creates_tables():
    conn = sqlite3.connect(KG_DB_PATH)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    names = [r[0] for r in tables]
    assert "entities" in names
    assert "relationships" in names


def test_add_and_get_entity():
    eid = add_entity("Python", "language", "A programming language")
    e = get_entity(eid)
    assert e["name"] == "Python"
    assert e["type"] == "language"


def test_add_entity_dedup():
    eid1 = add_entity("Python", "language", "")
    eid2 = add_entity("Python", "framework", "")
    assert eid1 == eid2
    e = get_entity(eid1)
    assert e["type"] == "language"


def test_add_and_get_relationship():
    py = add_entity("Python", "language", "")
    fl = add_entity("Flask", "framework", "")
    rid = add_relationship(py, fl, "built with")
    r = get_relationship(rid)
    assert r["relationship_type"] == "built with"
    assert r["source_entity_id"] == py
    assert r["target_entity_id"] == fl


def test_delete_entity_cascades():
    py = add_entity("Python", "language", "")
    fl = add_entity("Flask", "framework", "")
    add_relationship(py, fl, "built with")
    delete_entity(py)
    rels = get_all_relationships()
    assert len(rels) == 0


def test_get_graph_data():
    py = add_entity("Python", "language", "Desc")
    fl = add_entity("Flask", "framework", "")
    add_relationship(py, fl, "built with")
    data = get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["nodes"][0]["label"] == "Python"


def test_search_entities():
    add_entity("Python", "language", "")
    add_entity("PostgreSQL", "database", "")
    results = search_entities("Post")
    assert len(results) == 1
    assert results[0]["name"] == "PostgreSQL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_db.py -v 2>&1 | head -15`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
"""app/models/kg_db.py"""
import sqlite3
import os

KG_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "second_brain.db")


def _get_conn():
    conn = sqlite3.connect(KG_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_kg_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'concept',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            relationship_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_entity_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_entity_id);
    """)
    conn.commit()
    conn.close()


def add_entity(name, type="concept", description=""):
    conn = _get_conn()
    try:
        cur = conn.execute("INSERT INTO entities (name, type, description) VALUES (?, ?, ?)", (name, type, description))
        conn.commit()
        eid = cur.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT id FROM entities WHERE name = ?", (name,)).fetchone()
        eid = row["id"]
    conn.close()
    return eid


def get_entity(entity_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_entities():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM entities ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_entity(entity_id):
    conn = _get_conn()
    conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
    conn.commit()
    conn.close()


def add_relationship(source_entity_id, target_entity_id, relationship_type, weight=1.0):
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO relationships (source_entity_id, target_entity_id, relationship_type, weight) VALUES (?, ?, ?, ?)",
        (source_entity_id, target_entity_id, relationship_type, weight)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_relationship(rel_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM relationships WHERE id = ?", (rel_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_relationships():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM relationships").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_relationship(rel_id):
    conn = _get_conn()
    conn.execute("DELETE FROM relationships WHERE id = ?", (rel_id,))
    conn.commit()
    conn.close()


def get_graph_data():
    entities = get_all_entities()
    rels = get_all_relationships()
    nodes = [{"id": e["id"], "label": e["name"], "title": e["type"], "description": e["description"]} for e in entities]
    edges = [{"from": r["source_entity_id"], "to": r["target_entity_id"], "label": r["relationship_type"], "value": r["weight"]} for r in rels]
    return {"nodes": nodes, "edges": edges}


def search_entities(q):
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM entities WHERE name LIKE ?", (f"%{q}%",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_db.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/models/kg_db.py tests/test_kg_db.py
git commit -m "feat: KG database layer — entities + relationships tables"
```

---

### Task 2: Init KG DB + Register Blueprint in create_app

- [ ] **Step 1: Add init_kg_db call and blueprint registration to `app/__init__.py`**

Add import at top:
```python
from .models.kg_db import init_kg_db
```

Add call after `init_fts()`:
```python
    init_fts()
    init_kg_db()
```

Add import and registration:
```python
    from .routes import kg
    app.register_blueprint(kg.kg_bp)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_db.py -v`
Expected: 7 passed

- [ ] **Step 3: Commit**

```bash
git add app/__init__.py
git commit -m "feat: init KG DB and register blueprint on startup"
```

---

### Task 3: Service Layer

**Files:**
- Create: `app/services/kg_service.py`
- Test: `tests/test_kg_service.py`

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_kg_service.py"""
import sqlite3
import pytest
from app.models.kg_db import KG_DB_PATH, init_kg_db


@pytest.fixture(autouse=True)
def clean_kg():
    init_kg_db()
    conn = sqlite3.connect(KG_DB_PATH)
    conn.execute("DELETE FROM relationships")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()


def test_create_and_list():
    from app.services.kg_service import create_entity, list_entities
    e = create_entity("Python", "language")
    assert e["name"] == "Python"
    all_e = list_entities()
    assert len(all_e) == 1


def test_create_relationship():
    from app.services.kg_service import create_entity, create_relationship, list_relationships
    py = create_entity("Python", "language")
    fl = create_entity("Flask", "framework")
    r = create_relationship(py["id"], fl["id"], "built with")
    assert r["relationship_type"] == "built with"
    assert len(list_relationships()) == 1


def test_extract_triples_creates_entities_and_relationships():
    from app.services.kg_service import extract_triples, list_entities, list_relationships
    result = extract_triples([("Python", "built with", "Flask")])
    assert result["relationships_created"] == 1
    assert len(list_entities()) == 2
    assert len(list_relationships()) == 1


def test_extract_triples_dedup():
    from app.services.kg_service import extract_triples, list_entities, list_relationships
    extract_triples([("Python", "built with", "Flask")])
    extract_triples([("Python", "built with", "Flask")])
    entities = list_entities()
    assert len(entities) == 2
    assert len(list_relationships()) == 2


def test_delete_via_service():
    from app.services.kg_service import create_entity, delete_entity, list_entities
    e = create_entity("Temp", "test")
    assert len(list_entities()) == 1
    delete_entity(e["id"])
    assert len(list_entities()) == 0


def test_get_graph_data():
    from app.services.kg_service import create_entity, create_relationship, get_graph_data
    py = create_entity("Python", "language")
    fl = create_entity("Flask", "framework")
    create_relationship(py["id"], fl["id"], "built with")
    data = get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_service.py -v 2>&1 | head -15`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
"""app/services/kg_service.py"""
from ..models.kg_db import (
    add_entity, get_entity, get_all_entities,
    delete_entity as db_delete_entity,
    add_relationship, get_relationship, get_all_relationships,
    delete_relationship as db_delete_relationship,
    get_graph_data as db_get_graph_data,
    search_entities as db_search_entities,
)


def create_entity(name, type="concept", description=""):
    eid = add_entity(name, type, description)
    return get_entity(eid)


def list_entities():
    return get_all_entities()


def get_entity_by_id(entity_id):
    return get_entity(entity_id)


def delete_entity(entity_id):
    return db_delete_entity(entity_id)


def create_relationship(source_id, target_id, rel_type, weight=1.0):
    rid = add_relationship(source_id, target_id, rel_type, weight)
    return get_relationship(rid)


def list_relationships():
    return get_all_relationships()


def delete_relationship(rel_id):
    return db_delete_relationship(rel_id)


def extract_triples(triples):
    for source_name, rel_type, target_name in triples:
        s = add_entity(source_name.strip())
        t = add_entity(target_name.strip())
        add_relationship(s, t, rel_type.strip())
    return {"relationships_created": len(triples)}


def get_graph_data():
    return db_get_graph_data()


def search_entities(q):
    return db_search_entities(q)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_service.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/kg_service.py tests/test_kg_service.py
git commit -m "feat: KG service layer — CRUD + LLM extraction"
```

---

### Task 4: Routes

**Files:**
- Create: `app/routes/kg.py`
- Test: `tests/test_kg_routes.py`

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_kg_routes.py"""
import json
import pytest


def test_get_graph_empty(client):
    resp = client.get("/kg/graph")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "nodes" in data
    assert "edges" in data


def test_create_entity(client):
    resp = client.post("/kg/entity", json={"name": "Python", "type": "language"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Python"


def test_create_relationship(client):
    client.post("/kg/entity", json={"name": "Python", "type": "language"})
    client.post("/kg/entity", json={"name": "Flask", "type": "framework"})
    resp = client.post("/kg/relation", json={
        "source_name": "Python", "target_name": "Flask", "relationship_type": "built with"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationship_type"] == "built with"


def test_extract_triples(client):
    resp = client.post("/kg/extract", json={
        "triples": [("Python", "built with", "Flask")]
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationships_created"] == 1


def test_delete_entity(client):
    resp = client.post("/kg/entity", json={"name": "Temp", "type": "test"})
    eid = resp.get_json()["id"]
    resp = client.delete(f"/kg/entity/{eid}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_routes.py -v 2>&1 | head -15`
Expected: 5 failed (404 — routes not found)

- [ ] **Step 3: Write minimal implementation**

```python
"""app/routes/kg.py"""
from flask import Blueprint, jsonify, request, render_template
from ..services.kg_service import (
    create_entity, list_entities, get_entity_by_id, delete_entity,
    create_relationship, list_relationships, delete_relationship,
    extract_triples, get_graph_data, search_entities,
)

kg_bp = Blueprint("kg", __name__)


@kg_bp.route("/kg/graph")
def graph_data():
    q = request.args.get("q")
    if q:
        entities = search_entities(q)
        if entities:
            eid = entities[0]["id"]
            nodes = [{"id": e["id"], "label": e["name"], "title": e["type"], "description": e["description"]} for e in list_entities()]
            edges = [{"from": r["source_entity_id"], "to": r["target_entity_id"], "label": r["relationship_type"], "value": r["weight"]} for r in list_relationships()]
            return jsonify({"nodes": nodes, "edges": edges, "focus_id": eid})
    return jsonify(get_graph_data())


@kg_bp.route("/kg/entity", methods=["POST"])
def create_entity_route():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    entity = create_entity(
        name=data["name"],
        type=data.get("type", "concept"),
        description=data.get("description", ""),
    )
    return jsonify(entity), 201


@kg_bp.route("/kg/entity/<int:entity_id>", methods=["GET"])
def get_entity_route(entity_id):
    entity = get_entity_by_id(entity_id)
    if not entity:
        return jsonify({"error": "not found"}), 404
    return jsonify(entity)


@kg_bp.route("/kg/entity/<int:entity_id>", methods=["DELETE"])
def delete_entity_route(entity_id):
    delete_entity(entity_id)
    return jsonify({"status": "ok"})


@kg_bp.route("/kg/relation", methods=["POST"])
def create_relation_route():
    data = request.get_json()
    source_name = data.get("source_name") or data.get("source")
    target_name = data.get("target_name") or data.get("target")
    if not source_name or not target_name:
        return jsonify({"error": "source_name and target_name required"}), 400
    s = create_entity(source_name)
    t = create_entity(target_name)
    rel = create_relationship(
        s["id"], t["id"],
        data.get("relationship_type", "related to"),
        data.get("weight", 1.0),
    )
    return jsonify(rel), 201


@kg_bp.route("/kg/relation/<int:rel_id>", methods=["DELETE"])
def delete_relation_route(rel_id):
    delete_relationship(rel_id)
    return jsonify({"status": "ok"})


@kg_bp.route("/kg/extract", methods=["POST"])
def extract_route():
    data = request.get_json()
    triples = data.get("triples", [])
    result = extract_triples(triples)
    return jsonify(result), 201


@kg_bp.route("/kg/entities")
def list_entities_route():
    return jsonify(list_entities())


@kg_bp.route("/graph")
def graph_page():
    return render_template("graph.html")
```

- [ ] **Step 4: Wire the `client` fixture**

Check `tests/conftest.py` — it should already have:
```python
@pytest.fixture
def client(app):
    return app.test_client()
```

Create if missing but it already exists in the project.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/test_kg_routes.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add app/routes/kg.py tests/test_kg_routes.py
git commit -m "feat: KG routes — 7 REST endpoints + /graph page"
```

---

### Task 5: Graph Page — HTML + JS + CSS

**Files:**
- Create: `app/templates/graph.html`
- Create: `app/static/js/graph.js`
- Create: `app/static/css/graph.css`

- [ ] **Step 1: Create `app/templates/graph.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Knowledge Graph — Second Brain</title>
  <link rel="stylesheet" href="/static/css/graph.css">
  <script src="https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"></script>
</head>
<body class="theme-tokyo-night">
  <div id="app">
    <div id="topbar">
      <div class="topbar-left">
        <span class="topbar-icon">☰</span>
        <span class="topbar-title">Knowledge Graph</span>
      </div>
      <div class="topbar-center">
        <span class="search-icon">🔍</span>
        <input id="search-input" type="text" placeholder="Search concepts..." class="search-input">
      </div>
      <div class="topbar-right">
        <button id="theme-toggle" class="icon-btn" title="Toggle theme">🎨</button>
      </div>
    </div>
    <div id="main">
      <div id="graph-container"></div>
      <div id="sidebar">
        <div class="sidebar-header">Node Details</div>
        <div id="sidebar-content">
          <div class="sidebar-empty">Select a node to view details</div>
        </div>
      </div>
    </div>
    <div id="graph-footer">
      <div id="stats"><span id="node-count">0</span> concepts · <span id="edge-count">0</span> relationships</div>
      <div id="zoom-controls">
        <button class="zoom-btn" id="zoom-in" title="Zoom in">+</button>
        <button class="zoom-btn" id="zoom-out" title="Zoom out">−</button>
        <button class="zoom-btn" id="zoom-reset" title="Reset view">⟲</button>
      </div>
    </div>
  </div>
  <script src="/static/js/graph.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `app/static/css/graph.css`**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

/* Theme: Tokyo Night (default) */
body { background: #1a1b26; color: #a9b1d6; }
body #topbar { background: #1e1f2e; border-bottom: 1px solid #2a2b3d; }
body #sidebar { background: #1e1f2e; border-left: 1px solid #2a2b3d; }
body #graph-footer { background: #1e1f2e; border-top: 1px solid #2a2b3d; }
body .search-input { background: #161720; border: 1px solid #2a2b3d; color: #a9b1d6; }
body .search-input:focus { border-color: #7aa2f7; outline: none; }
body .zoom-btn { background: rgba(30,31,46,0.9); border: 1px solid #2a2b3d; color: #a9b1d6; }

/* Light */
body.theme-light { background: #ffffff; color: #555; }
.theme-light #topbar { background: #f8f9fa; border-bottom-color: #e0e0e0; }
.theme-light #sidebar { background: #f8f9fa; border-left-color: #e0e0e0; }
.theme-light #graph-footer { background: #f8f9fa; border-top-color: #e0e0e0; }
.theme-light .search-input { background: #fff; border-color: #e0e0e0; color: #555; }
.theme-light .zoom-btn { background: rgba(240,240,240,0.9); border-color: #e0e0e0; color: #555; }

/* GitHub Dark */
body.theme-github-dark { background: #0d1117; color: #c9d1d9; }
.theme-github-dark #topbar { background: #161b22; border-bottom-color: #30363d; }
.theme-github-dark #sidebar { background: #161b22; border-left-color: #30363d; }
.theme-github-dark #graph-footer { background: #161b22; border-top-color: #30363d; }
.theme-github-dark .search-input { background: #0d1117; border-color: #30363d; color: #c9d1d9; }
.theme-github-dark .zoom-btn { background: rgba(22,27,34,0.9); border-color: #30363d; color: #c9d1d9; }

/* Obsidian */
body.theme-obsidian { background: #faf8f5; color: #5c4f3f; }
.theme-obsidian #topbar { background: #f5f0eb; border-bottom-color: #e0d5c7; }
.theme-obsidian #sidebar { background: #f5f0eb; border-left-color: #e0d5c7; }
.theme-obsidian #graph-footer { background: #f5f0eb; border-top-color: #e0d5c7; }
.theme-obsidian .search-input { background: #fff; border-color: #e0d5c7; color: #5c4f3f; }
.theme-obsidian .zoom-btn { background: rgba(245,240,235,0.9); border-color: #e0d5c7; color: #5c4f3f; }

#app { display: flex; flex-direction: column; height: 100vh; }
#topbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; flex-shrink: 0; }
.topbar-left { display: flex; align-items: center; gap: 12px; }
.topbar-icon { font-size: 16px; color: #565870; }
.topbar-title { font-size: 14px; font-weight: 600; color: #a9b1d6; }
.topbar-center { display: flex; align-items: center; gap: 8px; flex: 1; max-width: 400px; margin: 0 20px; }
.search-icon { font-size: 14px; color: #565870; }
.search-input { width: 100%; padding: 7px 12px; border-radius: 6px; font-size: 13px; }
.icon-btn { background: none; border: none; cursor: pointer; font-size: 18px; padding: 4px; border-radius: 6px; }
.icon-btn:hover { background: rgba(122,162,247,0.1); }

#main { display: flex; flex: 1; overflow: hidden; }
#graph-container { flex: 1; position: relative; }
#sidebar { width: 280px; flex-shrink: 0; padding: 20px; overflow-y: auto; }
.sidebar-header { color: #565870; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }
.sidebar-empty { color: #565870; font-size: 13px; text-align: center; padding: 40px 0; }

#graph-footer { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px; flex-shrink: 0; }
#stats { color: #565870; font-size: 12px; }
#stats span { color: #a9b1d6; font-weight: 600; }
#zoom-controls { display: flex; gap: 4px; }
.zoom-btn { width: 28px; height: 28px; border-radius: 6px; font-size: 15px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s, transform 0.15s cubic-bezier(0.34,1.56,0.64,1); }
.zoom-btn:hover { background: rgba(42,43,61,0.9); }
.zoom-btn:active { transform: scale(0.92); }

@media (prefers-reduced-motion: reduce) {
  .zoom-btn:active { transform: none; }
}

.sidebar-node-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; font-weight: 600; flex-shrink: 0; }
.sidebar-node-name { color: #c0caf5; font-size: 15px; font-weight: 600; }
.sidebar-node-type { color: #565870; font-size: 11px; }
.sidebar-node-desc { color: #a9b1d6; font-size: 12px; line-height: 1.6; margin: 12px 0 20px; }
.sidebar-section-title { color: #565870; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
.sidebar-rel-item { display: flex; align-items: center; gap: 10px; padding: 8px; border-bottom: 1px solid rgba(42,43,61,0.5); cursor: pointer; border-radius: 4px; margin: 0 -8px; transition: background 0.2s; }
.sidebar-rel-item:hover { background: rgba(42,43,61,0.4); }
.sidebar-rel-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.sidebar-rel-name { color: #c0caf5; font-size: 12px; font-weight: 500; }
.sidebar-rel-target { color: #565870; font-size: 11px; }
.sidebar-actions { display: flex; gap: 8px; margin-top: 20px; }
.sidebar-btn { flex: 1; padding: 8px; text-align: center; border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; border: none; transition: background 0.2s; }
.sidebar-btn-focus { background: rgba(122,162,247,0.12); color: #7aa2f7; }
.sidebar-btn-focus:hover { background: rgba(122,162,247,0.2); }
.sidebar-btn-delete { background: rgba(247,118,142,0.08); color: #f7768e; }
.sidebar-btn-delete:hover { background: rgba(247,118,142,0.15); }
```

- [ ] **Step 3: Create `app/static/js/graph.js`**

```javascript
let network = null;
let nodes = new vis.DataSet([]);
let edges = new vis.DataSet([]);
let allData = { nodes: [], edges: [] };
const themes = ['tokyo-night', 'light', 'github-dark', 'obsidian'];
let themeIndex = 0;

const container = document.getElementById('graph-container');
const searchInput = document.getElementById('search-input');
const nodeCountEl = document.getElementById('node-count');
const edgeCountEl = document.getElementById('edge-count');
const sidebarContent = document.getElementById('sidebar-content');

async function loadGraph() {
  const resp = await fetch('/kg/graph');
  allData = await resp.json();
  nodes = new vis.DataSet(allData.nodes);
  edges = new vis.DataSet(allData.edges);
  nodeCountEl.textContent = allData.nodes.length;
  edgeCountEl.textContent = allData.edges.length;

  const options = {
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

  network = new vis.Network(container, { nodes, edges }, options);

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
    const q = this.value.trim();
    if (!q) return;
    const matching = allData.nodes.filter(n => n.label.toLowerCase().includes(q.toLowerCase()));
    if (matching.length > 0) {
      network.focus(matching[0].id, { scale: 1.5, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
      network.selectNodes([matching[0].id]);
      showNodeDetails(matching[0].id);
    }
  });
}

function showNodeDetails(nodeId) {
  const node = allData.nodes.find(n => n.id === nodeId);
  if (!node) return;
  const rels = allData.edges.filter(e => e.from === nodeId || e.to === nodeId);
  const colors = ['#5a7fd4', '#8b5cf6', '#6bae44', '#d4872e', '#d4506a', '#4db8e8', '#c8943a'];
  const color = colors[nodeId % colors.length];

  let relHtml = '';
  rels.forEach(r => {
    const isSource = r.from === nodeId;
    const otherId = isSource ? r.to : r.from;
    const other = allData.nodes.find(n => n.id === otherId);
    const direction = isSource ? '→' : '←';
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
```

- [ ] **Step 4: Verify the app starts**

```bash
cd /home/alan/Documents/code/the-second-brain && python3 -c "from app import create_app; app = create_app(); print('OK')"
```
Expected: `OK` printed

- [ ] **Step 5: Commit**

```bash
git add app/static/css/graph.css app/static/js/graph.js app/templates/graph.html
git commit -m "feat: KG graph page — vis.js, Tokyo Night theme, sidebar"
```

---

### Task 6: Chat Commands — `/kg` routing in frontend

**Files:**
- Modify: `app/static/script.js`

- [ ] **Step 1: Add handleKGCommand function**

After `handleYTCommand` function (after line ~114), add:

```javascript
async function handleKGCommand(command, args) {
    if (command !== "kg") return false;
    const sub = args.split(" ")[0];
    const rest = args.slice(sub.length).trim();
    switch (sub) {
        case "extract": {
            const resp = await fetch("/kg/extract", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({triples: [[rest, "related to", "topic"]]})
            });
            const data = await resp.json();
            addMessage("assistant", "✅ Extracted " + data.relationships_created + " relationships.");
            return true;
        }
        case "add": {
            const parts = rest.split(",").map(function(s) { return s.trim(); });
            const resp = await fetch("/kg/entity", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({name: parts[0], type: parts[1] || "concept", description: parts[2] || ""})
            });
            const data = await resp.json();
            addMessage("assistant", "✅ Created entity: " + data.name + " (ID: " + data.id + ")");
            return true;
        }
        case "relate": {
            const parts = rest.split("|").map(function(s) { return s.trim(); });
            if (parts.length < 2) {
                addMessage("assistant", "❌ Usage: /kg relate source | target | relation");
                return true;
            }
            const resp = await fetch("/kg/relation", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    source_name: parts[0],
                    target_name: parts[1],
                    relationship_type: parts[2] || "related to"
                })
            });
            const data = await resp.json();
            addMessage("assistant", "✅ Related " + parts[0] + " → " + parts[1] + " (" + data.relationship_type + ")");
            return true;
        }
        case "list": {
            const resp = await fetch("/kg/entities");
            const entities = await resp.json();
            if (entities.length === 0) {
                addMessage("assistant", "No entities in the knowledge graph.");
                return true;
            }
            var msg = "\u2501\u2501\u2501 Knowledge Graph Entities \u2501\u2501\u2501\n";
            entities.forEach(function(e) {
                msg += "\u2022 " + e.name + " (" + e.type + ")";
                if (e.description) msg += " \u2014 " + e.description;
                msg += "\n";
            });
            addMessage("assistant", msg);
            return true;
        }
        default:
            addMessage("assistant", "KG commands: extract <text>, add <name>[,type,desc], relate src | tgt | rel, list");
            return true;
    }
}
```

- [ ] **Step 2: Wire it into the command dispatch**

Replace lines ~121-130:
```javascript
    const ytHandled = await handleYTCommand(command, args);
    if (ytHandled) {
        input.value = "";
        return;
    }
    const kgHandled = await handleKGCommand(command, args);
    if (kgHandled) {
        input.value = "";
        return;
    }
```

- [ ] **Step 3: Verify the app starts**

```bash
cd /home/alan/Documents/code/the-second-brain && python3 -c "from app import create_app; app = create_app(); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/static/script.js
git commit -m "feat: /kg chat commands — extract, add, relate, list"
```

---

### Task 7: Final Test Pass

- [ ] **Step 1: Run all tests**

```bash
cd /home/alan/Documents/code/the-second-brain && python3 -m pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Fix any failures**

If the `add_relationship` function closes the connection before returning (the `conn.close()` was after the `return` statement), fix by adding the return value to a local variable before closing.

If tests fail because `conftest.py` doesn't provide a `client` fixture, check and add:
```python
@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 3: Commit fixes**

```bash
git add -A
git commit -m "chore: final KG polish — all tests passing"
```
