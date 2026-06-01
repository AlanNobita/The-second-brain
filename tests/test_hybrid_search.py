import pytest
from app.models.db import get_connection, init_db, init_fts, search_messages_fts


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
    results = search_messages_fts("python")
    assert len(results) == 2
    assert results[0][1] < results[1][1]


def test_fts_syntax_error_returns_empty():
    """Malformed FTS5 query should not crash, return empty instead"""
    results = search_messages_fts('"unclosed')
    assert results == []
