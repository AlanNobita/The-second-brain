# Hybrid Search (FTS5 + Vector) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task.

**Goal:** Add FTS5 full-text search to complement ChromaDB vector search, merging both into a single ranked result set.

**Architecture:** New `hybrid_search.py` service normalizes BM25 scores + vector distances to [0,1] and blends them 50/50. FTS5 virtual table `messages_fts` backed by `messages` content, synced via triggers. `/search` endpoint gets `?mode=` parameter (hybrid, semantic, keyword).

**Tech Stack:** SQLite FTS5 (built-in), existing ChromaDB + SentenceTransformer, no new dependencies.

---

### Task 1: FTS5 Virtual Table + Init

**Files:**
- Modify: `app/models/db.py`
- Test: `tests/test_hybrid_search.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_hybrid_search.py`:

```python
import pytest
from app.models.db import get_connection, init_db, init_fts, save_message


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    init_fts()
    conn = get_connection()
    conn.execute("DELETE FROM messages_fts")
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


def test_init_fts_creates_table():
    conn = get_connection()
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts'").fetchone()
    conn.close()
    assert row is not None


def test_fts_backfill():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s1', 'user', 'hello world')")
    conn.commit()
    conn.close()
    init_fts()
    conn = get_connection()
    row = conn.execute("SELECT rowid, content FROM messages_fts WHERE content MATCH 'hello'").fetchone()
    conn.close()
    assert row is not None
    assert row["content"] == "hello world"


def test_fts_search_returns_ranked():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s1', 'user', 'python programming')")
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s2', 'user', 'python is great for data science')")
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s3', 'user', 'i like javascript')")
    conn.commit()
    conn.close()
    init_fts()
    from app.models.db import search_messages_fts
    results = search_messages_fts("python")
    assert len(results) == 2
    assert results[0][1] <= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alan/Documents/code/the-second-brain && source .venv/bin/activate && python -m pytest tests/test_hybrid_search.py -v`
Expected: FAIL with ModuleNotFoundError or function not defined

- [ ] **Step 3: Add `init_fts()` and `search_messages_fts()` to `app/models/db.py`**

Add after `init_db()`:

```python
def init_fts():
    conn = get_connection()
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
        USING fts5(content=content)
    """)
    count = conn.execute("SELECT count(*) FROM messages_fts").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO messages_fts(rowid, content) SELECT id, content FROM messages")
    conn.commit()
    conn.close()


def search_messages_fts(query, limit=20):
    if not query:
        return []
    conn = get_connection()
    safe = query.replace('"', '""')
    rows = conn.execute(
        "SELECT rowid, rank FROM messages_fts WHERE content MATCH ? ORDER BY rank LIMIT ?",
        (safe, limit)
    ).fetchall()
    conn.close()
    return [(r["rowid"], r["rank"]) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/alan/Documents/code/the-second-brain && source .venv/bin/activate && python -m pytest tests/test_hybrid_search.py::test_init_fts_creates_table tests/test_hybrid_search.py::test_fts_backfill tests/test_hybrid_search.py::test_fts_search_returns_ranked -v`

- [ ] **Step 5: Commit**

```bash
git add app/models/db.py tests/test_hybrid_search.py
git commit -m "feat: add FTS5 virtual table and search function"
```

---

### Task 2: INSERT Trigger for FTS Sync

**Files:**
- Modify: `app/models/db.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_hybrid_search.py`:

```python
def test_fts_auto_sync_on_insert():
    init_fts()
    mid = save_message("s1", "user", "unique phrase for testing")
    conn = get_connection()
    row = conn.execute("SELECT rowid FROM messages_fts WHERE content MATCH 'unique phrase'").fetchone()
    conn.close()
    assert row is not None
    assert row["rowid"] == mid


def test_fts_sync_preserves_existing():
    init_fts()
    mid = save_message("s2", "assistant", "something else entirely")
    conn = get_connection()
    row = conn.execute("SELECT rowid FROM messages_fts WHERE content MATCH 'entirely'").fetchone()
    conn.close()
    assert row is not None
    assert row["rowid"] == mid
```

- [ ] **Step 2: Run to confirm failure**

- [ ] **Step 3: Add AFTER INSERT trigger in `init_fts()`**

Modify `init_fts()` to add after the backfill:

```python
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS messages_fts_insert
        AFTER INSERT ON messages
        BEGIN
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END
    """)
```

- [ ] **Step 4: Run tests to verify**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: auto-sync FTS index via INSERT trigger"
```

---

### Task 3: Hybrid Search Service

**Files:**
- Create: `app/services/hybrid_search.py`
- Test: extend `tests/test_hybrid_search.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_hybrid_search.py`:

```python
from unittest.mock import patch


def test_hybrid_search_returns_list():
    from app.services.hybrid_search import search
    result = search("python")
    assert isinstance(result, list)


def test_hybrid_search_empty_query():
    from app.services.hybrid_search import search
    result = search("")
    assert result == []


def test_hybrid_search_merges_results():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s1', 'user', 'python programming')")
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s2', 'user', 'rust is fast')")
    conn.commit()
    conn.close()
    init_fts()
    with patch("app.services.embedding_service.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [["1", "2"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[{"session_id": "s1", "role": "user"}, {"session_id": "s2", "role": "user"}]]
        }
        from app.services.hybrid_search import search
        results = search("programming", limit=10)
        assert len(results) > 0
        assert all("_source" in r for r in results)
        assert all("_score" in r for r in results)


def test_hybrid_search_keyword_mode():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s3', 'user', 'hello keyword test')")
    conn.commit()
    conn.close()
    init_fts()
    from app.services.hybrid_search import search
    results = search("keyword", mode="keyword")
    assert isinstance(results, list)
    for r in results:
        assert r["_source"] == "keyword"


def test_hybrid_search_semantic_mode():
    from app.services.hybrid_search import search
    with patch("app.services.embedding_service.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [["1"]],
            "distances": [[0.2]],
            "metadatas": [[{"session_id": "s1", "role": "user"}]]
        }
        results = search("anything", mode="semantic")
        assert len(results) > 0
        for r in results:
            assert r["_source"] == "semantic"
```

- [ ] **Step 2: Run to confirm failure**

- [ ] **Step 3: Create `app/services/hybrid_search.py`**

```python
from ..models.db import get_messages_by_ids, search_messages_fts
from .embedding_service import semantic_search


def search(query, limit=20, mode="hybrid"):
    if not query:
        return []

    if mode == "semantic":
        return _pure_vector(query, limit)

    if mode == "keyword":
        return _pure_fts(query, limit)

    fts_results = search_messages_fts(query, limit=limit * 2)
    vec_raw = semantic_search(query, limit=limit * 2)
    vec_results = _parse_vec_results(vec_raw)

    return _merge_ranked(fts_results, vec_results, limit)


def _pure_vector(query, limit):
    vec_raw = semantic_search(query, limit=limit)
    vec_ids = _parse_vec_results(vec_raw)
    ids = [msg_id for msg_id, _ in vec_ids]
    messages = get_messages_by_ids(ids)
    for m in messages:
        m["_source"] = "semantic"
        m["_score"] = _find_score(vec_ids, m["id"])
    return messages


def _pure_fts(query, limit):
    results = search_messages_fts(query, limit=limit)
    ids = [msg_id for msg_id, _ in results]
    messages = get_messages_by_ids(ids)
    for m in messages:
        m["_source"] = "keyword"
        m["_score"] = _find_score(results, m["id"])
    return messages


def _parse_vec_results(vec_raw):
    ids = vec_raw["ids"][0]
    dists = vec_raw["distances"][0]
    return [(int(i), d) for i, d in zip(ids, dists)]


def _find_score(pairs, target_id):
    for msg_id, score in pairs:
        if msg_id == target_id:
            return score
    return 0


def _merge_ranked(fts_results, vec_results, limit):
    fts_map = dict(fts_results)
    vec_map = dict(vec_results)

    if fts_map:
        fts_norm = {k: 2.0 / (1.0 + abs(v)) for k, v in fts_map.items()}
    else:
        fts_norm = {}

    if vec_map:
        dists = list(vec_map.values())
        max_dist = max(dists) if max(dists) > 0 else 1.0
        vec_norm = {k: 1.0 - (v / max_dist) for k, v in vec_map.items()}
    else:
        vec_norm = {}

    all_ids = set(fts_norm.keys()) | set(vec_norm.keys())
    scored = []
    for msg_id in all_ids:
        fts_score = fts_norm.get(msg_id, 0.0)
        vec_score = vec_norm.get(msg_id, 0.0)
        combined = 0.5 * fts_score + 0.5 * vec_score
        scored.append((msg_id, combined))

    scored.sort(key=lambda x: -x[1])
    top_ids = [msg_id for msg_id, _ in scored[:limit]]

    messages = get_messages_by_ids(top_ids)
    id_order = {msg_id: i for i, msg_id in enumerate(top_ids)}
    messages.sort(key=lambda m: id_order.get(m["id"], 999))

    for m in messages:
        m_id = m["id"]
        has_fts = m_id in fts_map
        has_vec = m_id in vec_map
        if has_fts and has_vec:
            m["_source"] = "hybrid"
        elif has_fts:
            m["_source"] = "keyword"
        else:
            m["_source"] = "semantic"
        m["_score"] = _find_score(scored, m_id)

    return messages
```

- [ ] **Step 4: Run tests to verify**

- [ ] **Step 5: Commit**

```bash
git add app/services/hybrid_search.py tests/test_hybrid_search.py
git commit -m "feat: add hybrid search service (FTS5 + vector merge)"
```

---

### Task 4: Update /search Route + Init

**Files:**
- Modify: `app/routes/chat.py`
- Modify: `app/__init__.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_hybrid_search.py`:

```python
def test_search_route_hybrid_default():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s_route', 'user', 'route test content here')")
    conn.commit()
    conn.close()
    init_fts()
    with patch("app.services.embedding_service.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [["1"]],
            "distances": [[0.5]],
            "metadatas": [[{"session_id": "s_route", "role": "user"}]]
        }
        from app import create_app
        import os
        os.environ["OPENROUTER_API_KEY"] = "test"
        app = create_app()
        client = app.test_client()
        resp = client.get("/search?q=route")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


def test_search_route_mode_semantic():
    with patch("app.services.embedding_service.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }
        from app import create_app
        import os
        os.environ["OPENROUTER_API_KEY"] = "test"
        app = create_app()
        client = app.test_client()
        resp = client.get("/search?q=test&mode=semantic")
        assert resp.status_code == 200


def test_search_route_mode_keyword():
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s_route_k', 'user', 'keyword mode test')")
    conn.commit()
    conn.close()
    init_fts()
    from app import create_app
    import os
    os.environ["OPENROUTER_API_KEY"] = "test"
    app = create_app()
    client = app.test_client()
    resp = client.get("/search?q=keyword&mode=keyword")
    assert resp.status_code == 200
    data = resp.get_json()
    for m in data:
        assert m["_source"] == "keyword"
```

- [ ] **Step 2: Update route in `app/routes/chat.py`**

Replace existing `/search`:

```python
@chat_bp.route("/search", methods=["GET"])
def find_message():
    query = request.args.get("q", "")
    mode = request.args.get("mode", "hybrid")

    if not query:
        return jsonify([])

    if mode == "semantic":
        results = semantic_search(query)
        message_ids = [int(id_) for id_ in results["ids"][0]]
        messages = get_messages_by_ids(message_ids)
        for m in messages:
            m["_source"] = "semantic"
            m["_score"] = 0
        return jsonify(messages)

    from ..services.hybrid_search import search as hybrid_search
    return jsonify(hybrid_search(query, mode=mode))
```

- [ ] **Step 3: Call `init_fts()` in `app/__init__.py`**

```python
from .models.db import init_db, init_fts
# after init_youtube_db():
init_fts()
```

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: wire hybrid search into /search route"
```

---

### Task 5: Frontend Source Badge

**Files:**
- Modify: `app/static/script.js`
- Modify: `app/static/style.css`

- [ ] **Step 1: Update `performSearch()` in `app/static/script.js`**

Replace the existing `performSearch` function:

```javascript
async function performSearch(query) {
    const response = await fetch("/search?q=" + encodeURIComponent(query))
    const results = await response.json();
    messagesDiv.innerHTML = "";
    if (results.length === 0) { 
        addMessage("assistant", "No messages found for \"" + query + "\"");
        return ;
    }
    addMessage("assistant", "Search results for \"" + query + "\"")
    results.forEach(m => {
        const sessionLabel = "Session: " + m.session_id.slice(0, 8) + "...";
        const div = document.createElement("div");
        div.className = "message " + m.role;
        div.style.cursor = "pointer";
        div.addEventListener("click", () => loadSession(m.session_id));
        const source = m._source || "semantic";
        const badge = document.createElement("span");
        badge.className = "result-source";
        badge.textContent = source;
        const textSpan = document.createElement("span");
        textSpan.textContent = "[" + sessionLabel + "] " + m.content;
        div.appendChild(badge);
        div.appendChild(textSpan);
        messagesDiv.appendChild(div);
    });
}
```

- [ ] **Step 2: Add CSS for `.result-source`**

Add to `app/static/style.css` before the `@keyframes` block:

```css
.result-source {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: #ccc;
    color: #555;
    padding: 2px 6px;
    border-radius: 4px;
    margin-right: 6px;
    vertical-align: middle;
}
```

- [ ] **Step 3: Commit**

```bash
git add app/static/script.js app/static/style.css
git commit -m "feat: show search source badge in frontend"
```

---

### Task 6: Run All Tests & Verify

- [ ] **Step 1: Run all YouTube + hybrid tests**

```bash
cd /home/alan/Documents/code/the-second-brain
source .venv/bin/activate
python -m pytest tests/test_hybrid_search.py tests/test_youtube_db.py tests/test_youtube_service.py tests/test_note_service.py tests/test_subscription_service.py tests/test_youtube_routes.py -v
```

- [ ] **Step 2: Fix any issues**

- [ ] **Step 3: Final commit if fixes needed**
