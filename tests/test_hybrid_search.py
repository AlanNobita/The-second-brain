import pytest
from unittest.mock import patch
from app.models.db import get_connection, init_db, init_fts, save_message, search_messages_fts
from app.models import db as db_module


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temp DB so tests don't pollute the real second_brain.db."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_hybrid.db"))
    init_db()
    init_fts()


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
    results = search_messages_fts("python")
    assert len(results) == 2
    assert results[0][1] < results[1][1]


def test_fts_syntax_error_returns_empty():
    """Malformed FTS5 query should not crash, return empty instead"""
    results = search_messages_fts('"unclosed')
    assert results == []


def test_fts_auto_sync_on_insert():
    mid = save_message("s1", "user", "unique phrase for testing")
    conn = get_connection()
    row = conn.execute("SELECT rowid FROM messages_fts WHERE content MATCH 'unique phrase'").fetchone()
    conn.close()
    assert row is not None
    assert row["rowid"] == mid


def test_fts_sync_preserves_existing():
    mid = save_message("s2", "assistant", "something else entirely")
    conn = get_connection()
    row = conn.execute("SELECT rowid FROM messages_fts WHERE content MATCH 'entirely'").fetchone()
    conn.close()
    assert row is not None
    assert row["rowid"] == mid


def test_hybrid_search_returns_list():
    with patch("app.services.hybrid_search.semantic_search") as mock_vec:
        mock_vec.return_value = {"ids": [[]], "distances": [[]], "metadatas": [[]]}
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
    id1 = conn.execute("SELECT id FROM messages WHERE session_id='s1'").fetchone()["id"]
    id2 = conn.execute("SELECT id FROM messages WHERE session_id='s2'").fetchone()["id"]
    conn.close()
    init_fts()
    with patch("app.services.hybrid_search.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [[str(id1), str(id2)]],
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
    conn = get_connection()
    conn.execute("INSERT INTO messages (session_id, role, content) VALUES ('s1', 'user', 'some content')")
    conn.commit()
    mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    from app.services.hybrid_search import search
    with patch("app.services.hybrid_search.semantic_search") as mock_vec:
        mock_vec.return_value = {
            "ids": [[str(mid)]],
            "distances": [[0.2]],
            "metadatas": [[{"session_id": "s1", "role": "user"}]]
        }
        results = search("anything", mode="semantic")
        assert len(results) > 0
        for r in results:
            assert r["_source"] == "semantic"


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
