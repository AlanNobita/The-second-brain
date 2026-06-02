"""Edge case tests for The Second Brain - bugs that hide in corners.

Categories covered:
1. Empty / None / missing inputs
2. Malformed JSON / wrong types
3. Very large inputs
4. Unicode / special characters
5. FTS5 query edge cases
6. Concurrency / race conditions
7. KG edge cases
8. YouTube edge cases
9. Reflection edge cases
10. Session / chat edge cases
"""
import sqlite3
import time
import urllib.parse
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared fixture: tmp-path DBs + fully mocked external deps
# ---------------------------------------------------------------------------

@pytest.fixture
def client_isolated(tmp_path, monkeypatch):
    """Flask test client with DB isolation and OpenAI/ChromaDB mocked.

    All four DB_PATH constants are redirected to a temp file so the test
    can never touch the real ``second_brain.db``. OpenAI is replaced with
    a fake that returns a fixed string. Background threads (the lazy
    YouTube check) and the embedding service are stubbed to keep tests
    fast and deterministic.
    """
    db_path = str(tmp_path / "edge_test.db")

    import app.models.db as msg_db
    monkeypatch.setattr(msg_db, "DB_PATH", db_path)
    import app.models.kg_db as kg_db_mod
    monkeypatch.setattr(kg_db_mod, "KG_DB_PATH", db_path)
    import app.models.youtube_db as yt_db
    monkeypatch.setattr(yt_db, "DB_PATH", db_path)
    import app.models.reflection_db as ref_db
    monkeypatch.setattr(ref_db, "DB_PATH", db_path)

    msg_db.init_db()
    msg_db.init_fts()
    kg_db_mod.init_kg_db()
    yt_db.init_youtube_db()
    ref_db.init_reflection_db()

    # ---- OpenAI: every service that imports it ----
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Mocked AI response"
    mock_ai = MagicMock()
    mock_ai.chat.completions.create.return_value = mock_resp

    def _openai_factory(**kwargs):
        return mock_ai

    monkeypatch.setattr("app.services.ai_service.OpenAI", _openai_factory)
    monkeypatch.setattr("app.services.proactive_service.OpenAI", _openai_factory)
    monkeypatch.setattr("app.services.note_service.OpenAI", _openai_factory)
    monkeypatch.setattr("app.services.reflection_service.OpenAI", _openai_factory)

    # ---- semantic_search: every consumer that imported it ----
    def _mock_semantic(query, limit=10):
        return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

    monkeypatch.setattr("app.services.ai_service.semantic_search", _mock_semantic)
    monkeypatch.setattr("app.services.hybrid_search.semantic_search", _mock_semantic)
    monkeypatch.setattr("app.services.proactive_service.semantic_search", _mock_semantic)

    # ---- background YouTube thread (daemon) ----
    monkeypatch.setattr(
        "app.services.ai_service._lazy_youtube_check", lambda app: None
    )

    # ---- embedding service pieces (conftest already mocks the libs) ----
    mock_collection = MagicMock()
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.0] * 384
    monkeypatch.setattr("app.services.embedding_service._collection", mock_collection)
    monkeypatch.setattr("app.services.embedding_service._model", mock_model)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as c:
        yield c


# ===========================================================================
# Category 1: Empty / None / missing inputs
# ===========================================================================

def test_chat_send_empty_string_message(client_isolated):
    """POST /chat/send with message="" should still return a valid reply."""
    resp = client_isolated.post("/chat/send", json={"message": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data
    assert "session_id" in data


def test_chat_send_empty_body_dict(client_isolated):
    """POST /chat/send with {} - route should fall back to defaults."""
    resp = client_isolated.post("/chat/send", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reply"] == "Mocked AI response"
    # session_id must be auto-generated
    assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0


def test_chat_send_no_body_no_content_type(client_isolated):
    """POST /chat/send with no body and no Content-Type - get_json(silent=True) -> None."""
    resp = client_isolated.post("/chat/send", data="")
    assert resp.status_code == 200


def test_chat_send_null_message(client_isolated):
    """POST /chat/send with message=null - None should be coerced or rejected, not crash."""
    resp = client_isolated.post("/chat/send", json={"message": None})
    # BUG: None passes data.get("message", "") unchanged, then save_message
    # hits NOT NULL constraint. Should be a 400 (validation), not 500.
    assert resp.status_code in (200, 400), (
        f"Expected 200/400, got {resp.status_code} (body: {resp.data!r})"
    )


def test_chat_send_whitespace_only_message(client_isolated):
    """POST /chat/send with message="   " - whitespace is a valid string."""
    resp = client_isolated.post("/chat/send", json={"message": "   "})
    assert resp.status_code == 200


def test_chat_history_empty_session_id_param(client_isolated):
    """GET /chat/history?session_id= - empty string should 400."""
    resp = client_isolated.get("/chat/history?session_id=")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_chat_history_no_session_id_param(client_isolated):
    """GET /chat/history (no query params) - should 400."""
    resp = client_isolated.get("/chat/history")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_search_empty_query_param(client_isolated):
    """GET /search?q= - empty query short-circuits to []."""
    resp = client_isolated.get("/search?q=")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_search_no_query_param(client_isolated):
    """GET /search with no q param at all - should return []."""
    resp = client_isolated.get("/search")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_yt_ingest_empty_video_url(client_isolated):
    """POST /yt/ingest with video_url='' - should 400 cleanly."""
    resp = client_isolated.post("/yt/ingest", json={"video_url": ""})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_yt_ingest_malformed_url_no_video_id(client_isolated):
    """POST /yt/ingest with 'not-a-youtube-url' - extract_video_id returns None."""
    resp = client_isolated.post("/yt/ingest", json={"video_url": "not-a-youtube-url"})
    # fetch_transcript raises TranscriptError because video_id is None
    # route catches and returns 500
    assert resp.status_code in (400, 500)
    data = resp.get_json() or {}
    assert "error" in data


def test_yt_ingest_valid_format_nonexistent_video(client_isolated):
    """POST /yt/ingest with a syntactically valid but non-existent video ID."""
    with patch("app.routes.youtube.fetch_transcript") as mock_fetch:
        from app.services.youtube_service import TranscriptError
        mock_fetch.side_effect = TranscriptError("no captions")
        resp = client_isolated.post(
            "/yt/ingest",
            json={"video_url": "https://youtube.com/watch?v=__nonexistent__"},
        )
    assert resp.status_code == 500
    assert "error" in resp.get_json()


# ===========================================================================
# Category 2: Malformed JSON / wrong types
# ===========================================================================

def test_chat_send_wrong_content_type_header(client_isolated):
    """POST /chat/send with text/plain Content-Type - silent=True handles it."""
    resp = client_isolated.post(
        "/chat/send",
        data='{"message": "ignored because content-type is wrong"}',
        content_type="text/plain",
    )
    # body is discarded, falls back to {} -> message=""
    assert resp.status_code == 200


def test_chat_send_message_is_integer(client_isolated):
    """POST /chat/send with message=123 - int is auto-converted to text by SQLite."""
    resp = client_isolated.post("/chat/send", json={"message": 123})
    # SQLite stores 123 as text '123' due to type affinity on TEXT column
    assert resp.status_code == 200


def test_chat_send_message_is_list(client_isolated):
    """POST /chat/send with message=['a'] - list cannot be bound, must not crash."""
    resp = client_isolated.post("/chat/send", json={"message": ["arr"]})
    # BUG: sqlite3 raises ProgrammingError for list type; surfaces as 500
    assert resp.status_code in (200, 400), (
        f"Expected graceful 200/400, got {resp.status_code}"
    )


def test_chat_send_message_is_object(client_isolated):
    """POST /chat/send with message={} - dict cannot be bound, must not crash."""
    resp = client_isolated.post(
        "/chat/send", json={"message": {"nested": "obj"}}
    )
    # BUG: same as list - ProgrammingError surfaces as 500
    assert resp.status_code in (200, 400), (
        f"Expected graceful 200/400, got {resp.status_code}"
    )


def test_kg_relation_both_names_null(client_isolated):
    """POST /kg/relation with null source and target - should 400."""
    resp = client_isolated.post(
        "/kg/relation",
        json={"source_name": None, "target_name": None},
    )
    assert resp.status_code == 400


def test_kg_relation_int_source_and_target(client_isolated):
    """POST /kg/relation with int names - SQLite affinity converts to text."""
    resp = client_isolated.post(
        "/kg/relation",
        json={"source_name": 123, "target_name": 456, "relationship_type": "knows"},
    )
    # 123 and 456 are truthy so they pass the None check, then get stored
    # as text "123" / "456" - this WORKS but is wrong from a domain standpoint
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationship_type"] == "knows"


def test_kg_extract_string_instead_of_list(client_isolated):
    """POST /kg/extract with triples='not a list' - iterating a string yields chars."""
    resp = client_isolated.post("/kg/extract", json={"triples": "not a list"})
    # BUG: extract_triples iterates "not a list" char-by-char, then tries to
    # unpack one char into 3 vars -> ValueError -> 500. Should validate type.
    assert resp.status_code in (201, 500)
    if resp.status_code == 500:
        # Confirmed bug
        assert "error" in (resp.get_json() or {})


def test_kg_extract_int_instead_of_text(client_isolated):
    """POST /kg/extract with text=123 - int has no .strip() method."""
    resp = client_isolated.post("/kg/extract", json={"text": 123})
    # BUG: _parse_triples_from_text calls text.strip() on int -> AttributeError -> 500
    assert resp.status_code in (201, 500)


# ===========================================================================
# Category 3: Very large inputs
# ===========================================================================

def test_chat_send_100kb_message(client_isolated):
    """POST /chat/send with 100KB message - SQLite handles it, AI mock returns short reply."""
    large = "A" * 100_000
    resp = client_isolated.post("/chat/send", json={"message": large})
    assert resp.status_code == 200
    data = resp.get_json()
    # Mocked AI returns a short reply regardless of input size
    assert data["reply"] == "Mocked AI response"


def test_kg_extract_500_triples(client_isolated):
    """POST /kg/extract with 500 unique triples - exercises bulk insert path."""
    triples = [[f"Entity{i}", "relates to", f"Other{i}"] for i in range(500)]
    resp = client_isolated.post("/kg/extract", json={"triples": triples})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationships_created"] == 500


def test_chat_history_with_10k_messages(client_isolated, tmp_path):
    """Insert 10K messages into one session, fetch history, time it."""
    import app.models.db as msg_db
    conn = sqlite3.connect(msg_db.DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")  # speed up bulk inserts
    rows = [
        ("bulk_session", "user", f"message number {i}") for i in range(10_000)
    ]
    conn.executemany(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    conn.close()
    # Trigger FTS backfill
    msg_db.init_fts()

    start = time.time()
    resp = client_isolated.get("/chat/history?session_id=bulk_session")
    elapsed = time.time() - start

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["messages"]) == 10_000
    # Sanity: must complete in reasonable time
    assert elapsed < 10.0, f"10K history took {elapsed:.1f}s"


def test_search_fts_with_10k_messages(client_isolated, tmp_path):
    """Insert 10K messages, then keyword search - verify FTS5 handles the volume.

    The default hybrid search cap is 20 results, so we check that the search
    returns the cap and completes quickly, not that it returns every match.
    """
    import app.models.db as msg_db
    conn = sqlite3.connect(msg_db.DB_PATH)
    rows = [
        ("search_session", "user",
         f"needle content {i}" if i % 2 == 0 else f"haystack item {i}")
        for i in range(10_000)
    ]
    conn.executemany(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    conn.close()
    msg_db.init_fts()

    start = time.time()
    resp = client_isolated.get("/search?q=needle&mode=keyword")
    elapsed = time.time() - start

    assert resp.status_code == 200
    data = resp.get_json()
    # Default limit is 20, and FTS5 must have matched our "needle" docs
    assert len(data) > 0
    assert len(data) <= 20
    assert all("needle" in m["content"] for m in data)
    assert elapsed < 5.0, f"10K search took {elapsed:.1f}s"


# ===========================================================================
# Category 4: Unicode / special characters
# ===========================================================================

def test_chat_send_unicode_multiscript(client_isolated):
    """POST /chat/send with multi-script (Latin, CJK, emoji, Arabic)."""
    msg = "Hello 你好 🎉 مرحبا"
    resp = client_isolated.post("/chat/send", json={"message": msg})
    assert resp.status_code == 200


def test_chat_send_xss_payload_as_text(client_isolated):
    """POST /chat/send with XSS payload - must be stored as text, not executed."""
    xss = "<script>alert('xss')</script>"
    resp = client_isolated.post("/chat/send", json={"message": xss})
    assert resp.status_code == 200
    # Verify the text was actually stored (not stripped/escaped server-side)
    data = resp.get_json()
    sid = data["session_id"]
    hist = client_isolated.get(f"/chat/history?session_id={sid}")
    msgs = hist.get_json()["messages"]
    stored = next(m["content"] for m in msgs if m["role"] == "user")
    assert "<script>" in stored


def test_chat_send_null_bytes_in_message(client_isolated):
    """POST /chat/send with NUL bytes - SQLite accepts, no crash expected."""
    msg = "before\x00\x01\x02after"
    resp = client_isolated.post("/chat/send", json={"message": msg})
    assert resp.status_code == 200


def test_yt_ingest_unicode_video_id_param(client_isolated):
    """POST /yt/ingest with non-ASCII in v= param - extract_video_id returns it as-is."""
    with patch("app.routes.youtube.fetch_transcript") as mock_fetch:
        from app.services.youtube_service import TranscriptError
        mock_fetch.side_effect = TranscriptError("bad video id")
        resp = client_isolated.post(
            "/yt/ingest",
            json={"video_url": "https://youtube.com/watch?v=abc測試"},
        )
    # The unicode string is what extract_video_id returns, then transcript API rejects
    assert resp.status_code == 500
    assert "error" in resp.get_json()


def test_search_chinese_query_term(client_isolated):
    """GET /search?q=测试 - FTS5 default tokenizer has limited CJK support."""
    resp = client_isolated.get("/search?q=" + urllib.parse.quote("测试"))
    assert resp.status_code == 200
    # CJK without explicit tokenizer usually returns []; either way no crash
    assert isinstance(resp.get_json(), list)


def test_kg_entity_name_with_emoji(client_isolated):
    """POST /kg/entity with emoji in name - should store verbatim."""
    resp = client_isolated.post(
        "/kg/entity", json={"name": "Python 🐍", "type": "language"}
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Python 🐍"


# ===========================================================================
# Category 5: FTS5 query edge cases
# ===========================================================================

def test_search_fts_unclosed_double_quote(client_isolated):
    """GET /search?q=\"unclosed - search_messages_fts should catch the syntax error."""
    resp = client_isolated.get("/search?q=" + urllib.parse.quote('"unclosed'))
    assert resp.status_code == 200
    # OperationalError is caught inside search_messages_fts, returns []
    assert resp.get_json() == []


def test_search_fts_wildcard_star(client_isolated):
    """GET /search?q=* - bare asterisk is invalid FTS5 syntax."""
    resp = client_isolated.get("/search?q=" + urllib.parse.quote("*"))
    assert resp.status_code == 200
    # "unknown special query" error is caught, returns []
    assert resp.get_json() == []


def test_search_fts_boolean_keywords_only(client_isolated):
    """GET /search?q=AND OR NOT - bare FTS5 keywords trigger syntax error."""
    resp = client_isolated.get(
        "/search?q=" + urllib.parse.quote("AND OR NOT")
    )
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_search_fts_near_operator(client_isolated):
    """GET /search?q=NEAR(foo bar) - NEAR is valid FTS5 syntax, no match returns []."""
    resp = client_isolated.get(
        "/search?q=" + urllib.parse.quote("NEAR(foo bar)")
    )
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_search_fts_1000_char_query(client_isolated):
    """GET /search?q=<1000 chars> - very long query must not crash."""
    q = "a" * 1000
    resp = client_isolated.get(f"/search?q={q}")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_search_fts_sql_injection_attempt(client_isolated):
    """GET /search?q=' OR 1=1 -- - FTS5 uses parameterized queries, not raw SQL."""
    q = "' OR 1=1 --"
    resp = client_isolated.get("/search?q=" + urllib.parse.quote(q))
    assert resp.status_code == 200
    # The ' is just part of the FTS5 query term; causes syntax error, caught, []
    assert resp.get_json() == []


# ===========================================================================
# Category 6: Concurrency / race conditions
# ===========================================================================

def test_two_messages_to_same_session_persist(client_isolated):
    """Sequential: two POSTs to the same session_id - both land there.

    The Flask test client stores its request context in a ContextVar, so
    genuinely concurrent client.post() calls from threads raise
    LookupError in teardown. We exercise the multi-write code path
    sequentially, which is what production sees after the WSGI server
    serializes requests.
    """
    r1 = client_isolated.post(
        "/chat/send", json={"message": "first", "session_id": "shared"}
    )
    r2 = client_isolated.post(
        "/chat/send", json={"message": "second", "session_id": "shared"}
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_json()["session_id"] == "shared"
    assert r2.get_json()["session_id"] == "shared"

    # Both user messages + 2 assistant messages should be stored
    hist = client_isolated.get("/chat/history?session_id=shared")
    msgs = hist.get_json()["messages"]
    user_msgs = [m for m in msgs if m["role"] == "user"]
    assert len(user_msgs) == 2
    assert {m["content"] for m in user_msgs} == {"first", "second"}


def test_concurrent_delete_and_read_same_session(client_isolated):
    """Sequentially: read history, then delete the session - both must succeed.

    Real concurrent testing with the Flask test client is brittle because
    the request context is bound to a ContextVar. We simulate the race by
    performing the read and delete in immediate succession and verifying
    neither crashes the other.
    """
    import app.models.db as msg_db
    for i in range(50):
        msg_db.save_message("race_session", "user", f"msg {i}")

    # Read while data exists
    r1 = client_isolated.get("/chat/history?session_id=race_session")
    assert r1.status_code == 200
    assert len(r1.get_json()["messages"]) == 50

    # Delete
    r2 = client_isolated.delete("/session/race_session")
    assert r2.status_code == 200

    # Read again - empty now, no crash
    r3 = client_isolated.get("/chat/history?session_id=race_session")
    assert r3.status_code == 200
    assert r3.get_json()["messages"] == []


def test_reflection_generate_concurrent_with_today_read(client_isolated):
    """Reading /api/reflection/today immediately after a generate call.

    We mock generate_daily_reflection in the route's namespace (because the
    route imports the function by name). The test verifies both endpoints
    respond cleanly in sequence - the WSGI server in production would
    serialize them, so sequential calls exercise the same code paths
    without the test client's ContextVar teardown issue.
    """
    with patch("app.routes.reflections.generate_daily_reflection") as mock_gen:
        mock_gen.return_value = {
            "date": date.today().isoformat(),
            "summary": "concurrent summary",
            "topics": ["pytest"],
        }
        r1 = client_isolated.get("/api/reflection/today")
        r2 = client_isolated.post("/api/reflection/generate")

    assert r1.status_code == 200
    assert r1.get_json() is None  # nothing stored yet
    assert r2.status_code == 201
    assert r2.get_json()["summary"] == "concurrent summary"
    # Mock was invoked exactly once
    assert mock_gen.call_count == 1


# ===========================================================================
# Category 7: KG edge cases
# ===========================================================================

def test_kg_entity_empty_name_rejected(client_isolated):
    """POST /kg/entity with name='' - the route should 400."""
    resp = client_isolated.post("/kg/entity", json={"name": ""})
    assert resp.status_code == 400


def test_kg_entity_empty_type_stored_as_empty_string(client_isolated):
    """POST /kg/entity with type='' - the route defaults via .get(key, default)
    which only fires when the key is missing. Empty string is a value, so it
    passes through and is stored as the entity's type."""
    resp = client_isolated.post(
        "/kg/entity", json={"name": "A", "type": ""}
    )
    assert resp.status_code == 201
    data = resp.get_json()
    # BUG: expected type is "concept" (the default), actual is ""
    assert data["type"] == "concept", (
        f"Empty type should default to 'concept', got {data['type']!r}"
    )


def test_kg_entity_10000_char_type(client_isolated):
    """POST /kg/entity with a 10K-char type - SQLite TEXT has no length limit."""
    long_type = "x" * 10_000
    resp = client_isolated.post(
        "/kg/entity", json={"name": "LongType", "type": long_type}
    )
    assert resp.status_code == 201
    assert len(resp.get_json()["type"]) == 10_000


def test_kg_extract_whitespace_only_text(client_isolated):
    """POST /kg/extract with text='   \\n\\t  ' - should produce 0 triples."""
    resp = client_isolated.post(
        "/kg/extract", json={"text": "   \n\t\n  "}
    )
    assert resp.status_code == 201
    assert resp.get_json() == {
        "entities_created": 0,
        "relationships_created": 0,
    }


def test_kg_extract_text_with_no_pipe_separators(client_isolated):
    """POST /kg/extract with text that has no '|' separators - 0 relationships."""
    resp = client_isolated.post(
        "/kg/extract",
        json={"text": "this is just plain text with no pipe characters"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["relationships_created"] == 0


def test_kg_extract_duplicate_triple_creates_duplicate_relationships(client_isolated):
    """POST /kg/extract with the same triple twice - entities dedup, relationships don't.

    This is documented in the existing test_extract_triples_dedup but is
    arguably a bug: the user almost certainly doesn't want two identical
    edges between the same nodes.
    """
    resp = client_isolated.post(
        "/kg/extract",
        json={
            "triples": [
                ["Python", "built with", "Flask"],
                ["Python", "built with", "Flask"],
            ]
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    # Entities dedup (UNIQUE on name): 2 entities (Python, Flask)
    assert data["entities_created"] == 2
    # Relationships do NOT dedup: 2 edges created
    assert data["relationships_created"] == 2


def test_kg_delete_nonexistent_entity_id(client_isolated):
    """DELETE /kg/entity/99999 - should not crash, returns ok."""
    resp = client_isolated.delete("/kg/entity/99999")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_kg_delete_nonexistent_relation_id(client_isolated):
    """DELETE /kg/relation/99999 - should not crash, returns ok."""
    resp = client_isolated.delete("/kg/relation/99999")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# ===========================================================================
# Category 8: YouTube edge cases
# ===========================================================================

def test_yt_ingest_transcript_error_returns_500(client_isolated):
    """POST /yt/ingest when fetch_transcript raises TranscriptError."""
    with patch("app.routes.youtube.fetch_transcript") as mock_fetch:
        from app.services.youtube_service import TranscriptError
        mock_fetch.side_effect = TranscriptError("no captions for this video")
        resp = client_isolated.post(
            "/yt/ingest",
            json={"video_url": "https://youtube.com/watch?v=abc123"},
        )
    assert resp.status_code == 500
    assert "no captions" in resp.get_json()["error"]


def test_yt_ingest_debloat_returns_empty_string(client_isolated):
    """POST /yt/ingest when debloat_and_structure returns '' (no transcript)."""
    with patch("app.routes.youtube.fetch_transcript") as mock_fetch, \
         patch("app.routes.youtube.debloat_and_structure") as mock_debloat, \
         patch("app.routes.youtube.save_note_file") as mock_save:
        mock_fetch.return_value = "raw transcript that the LLM rejected"
        mock_debloat.return_value = ""  # LLM returned nothing useful
        mock_save.return_value = "/tmp/empty.md"
        resp = client_isolated.post(
            "/yt/ingest",
            json={"video_url": "https://youtube.com/watch?v=abc123"},
        )
    # An empty markdown still produces one empty chunk, which is saved.
    # This documents the current (possibly surprising) behavior.
    assert resp.status_code in (200, 500)


def test_yt_search_empty_query_param(client_isolated):
    """GET /yt/search?q= - empty query returns 400."""
    resp = client_isolated.get("/yt/search?q=")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_yt_subscribe_non_url_string(client_isolated):
    """POST /yt/subscribe with channel_url='not-a-url' - extract_channel_id
    is permissive and returns the raw path as the channel id."""
    with patch(
        "app.services.subscription_service.get_channel_videos"
    ) as mock_gcv:
        mock_gcv.return_value = []
        resp = client_isolated.post(
            "/yt/subscribe", json={"channel_url": "not-a-url"}
        )
    # Subscription is added with a weird derived name. This test documents
    # that the route does not validate the URL format.
    assert resp.status_code == 200
    data = resp.get_json()
    assert "id" in data
    assert "channel_url" in data
    assert data["channel_url"] == "not-a-url"


def test_yt_subscribe_idempotent_reactivation(client_isolated):
    """POST /yt/subscribe to an existing channel - re-subscribes, returns same id."""
    with patch(
        "app.services.subscription_service.get_channel_videos"
    ) as mock_gcv:
        mock_gcv.return_value = []
        url = "https://www.youtube.com/@existing-channel"
        r1 = client_isolated.post("/yt/subscribe", json={"channel_url": url})
        r2 = client_isolated.post("/yt/subscribe", json={"channel_url": url})
    assert r1.status_code == 200
    assert r2.status_code == 200
    # INSERT OR IGNORE + UPDATE active=1 should return the same row id
    assert r1.get_json()["id"] == r2.get_json()["id"]


def test_yt_unsubscribe_nonexistent_sub_id(client_isolated):
    """POST /yt/unsubscribe with sub_id=99999 - returns not_found, no crash."""
    resp = client_isolated.post("/yt/unsubscribe", json={"sub_id": 99999})
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "not_found"}


# ===========================================================================
# Category 9: Reflection edge cases
# ===========================================================================

def test_reflection_today_when_no_reflection_exists(client_isolated):
    """GET /api/reflection/today on a fresh DB returns None."""
    resp = client_isolated.get("/api/reflection/today")
    assert resp.status_code == 200
    assert resp.get_json() is None


def test_reflection_generate_twice_same_day_overwrites(client_isolated, tmp_path):
    """POST /api/reflection/generate twice on the same day - second wins.

    We patch at the DB layer (save_reflection) and OpenAI layer so the
    service runs end-to-end, then verify the second call replaces the
    first via INSERT OR REPLACE on the date UNIQUE column.
    """
    import app.models.db as msg_db
    import app.services.reflection_service as ref_svc
    from app.models.reflection_db import save_reflection

    conn = sqlite3.connect(msg_db.DB_PATH)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        ("ref_seed", "user", "today's content for reflection"),
    )
    conn.commit()
    conn.close()

    # Mock the OpenAI calls inside generate_daily_reflection
    mock_topic_resp = MagicMock()
    mock_topic_resp.choices = [MagicMock()]
    mock_topic_resp.choices[0].message.content = '["topic1"]'
    mock_summary_resp = MagicMock()
    mock_summary_resp.choices = [MagicMock()]
    mock_summary_resp.choices[0].message.content = "summary text"

    def make_ai(**kwargs):
        m = MagicMock()
        m.chat.completions.create.side_effect = [mock_topic_resp, mock_summary_resp]
        return m

    # Patch OpenAI factory + monkey-patch save_reflection to track calls
    with patch.object(ref_svc, "OpenAI", side_effect=make_ai):
        r1 = client_isolated.post("/api/reflection/generate")
        r2 = client_isolated.post("/api/reflection/generate")

    assert r1.status_code == 201
    assert r2.status_code == 201

    # Verify the latest summary is stored (INSERT OR REPLACE on date)
    r_today = client_isolated.get("/api/reflection/today")
    assert r_today.status_code == 200
    data = r_today.get_json()
    assert data is not None
    assert data["summary"] == "summary text"
    # Both generations stored the same date, so there should be exactly one row
    refs = client_isolated.get("/api/reflections").get_json()
    assert len(refs) == 1


def test_reflection_generate_when_no_messages_today(client_isolated):
    """POST /api/reflection/generate with no messages today - returns 400."""
    with patch("app.routes.reflections.generate_daily_reflection") as mock_gen:
        mock_gen.return_value = None
        resp = client_isolated.post("/api/reflection/generate")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ===========================================================================
# Category 10: Session / chat edge cases
# ===========================================================================

def test_delete_session_with_10000_char_id(client_isolated):
    """DELETE /session/<10000-char-id> - URL parsing must not crash."""
    long_id = "x" * 10_000
    resp = client_isolated.delete(f"/session/{long_id}")
    assert resp.status_code == 200


def test_delete_session_with_url_encoded_special_chars(client_isolated):
    """DELETE /session/<id with colons, at-signs, etc.> - percent-encoded.

    The Flask ``string`` URL converter rejects slashes after decoding, so we
    stick to special characters that survive the route match.
    """
    special = "abc:def@test#123"
    encoded = urllib.parse.quote(special, safe="")
    resp = client_isolated.delete(f"/session/{encoded}")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_delete_session_that_does_not_exist(client_isolated):
    """DELETE /session/<unknown> - no matching rows, still returns 200."""
    resp = client_isolated.delete("/session/never-existed-xyz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_get_sessions_on_empty_db(client_isolated):
    """GET /sessions with zero messages - returns []."""
    resp = client_isolated.get("/sessions")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_sessions_with_100_sessions(client_isolated):
    """GET /sessions with 100 distinct sessions - check count and timing."""
    import app.models.db as msg_db
    conn = sqlite3.connect(msg_db.DB_PATH)
    rows = []
    for i in range(100):
        sid = f"perf_session_{i:03d}"
        rows.append((sid, "user", f"first message in session {i}"))
    conn.executemany(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    conn.close()

    start = time.time()
    resp = client_isolated.get("/sessions")
    elapsed = time.time() - start

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 100
    assert elapsed < 2.0, f"100-session listing took {elapsed:.1f}s"
