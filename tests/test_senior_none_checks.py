"""
Regression tests for 6 None-check bugs fixed by a senior engineer.

If any test in this file fails, do NOT 'fix' the test — find the regression
in the production code. Each test verifies that a specific None-check
guard is in place in the corresponding production code path.

Bug list (production code location : line range : fix summary):
  1. app/services/kg_service.py  : 73-78 : extract_triples skips None entities
  2. app/models/kg_db.py         : 50-52 : add_entity raises on missing fallback row
  3. app/routes/kg.py            : 61-67 : create_relation_route returns 500 on None entity
  4. app/services/note_service.py: 50-52 : debloat_and_structure stage-1 None check
  5. app/services/note_service.py: 74-77 : debloat_and_structure stage-2 None check
  6. app/routes/youtube.py       : 34-40 : yt_ingest returns 500 on None markdown
"""

import sqlite3
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_kg():
    """Reset the knowledge-graph tables before each test (same pattern as
    the existing test_kg_*.py suites, which all share the real DB file)."""
    from app.models.kg_db import init_kg_db, KG_DB_PATH
    init_kg_db()
    conn = sqlite3.connect(KG_DB_PATH)
    conn.execute("DELETE FROM relationships")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def stub_embedding_and_logger(client, monkeypatch):
    """Stub the embedding service to no-ops and silence the Flask logger
    so exception traces from `current_app.logger.exception(...)` calls
    in the route handlers do not pollute test output."""
    monkeypatch.setattr(client.application, "logger", MagicMock())
    monkeypatch.setattr("app.services.embedding_service.init_embedding_service", lambda: None)
    monkeypatch.setattr("app.services.embedding_service.store_embedding", lambda *a, **kw: None)
    monkeypatch.setattr("app.services.embedding_service.semantic_search", lambda *a, **kw: [])


# ---------------------------------------------------------------------------
# TEST 1: kg_service.extract_triples skips triples where create_entity returns None
# ---------------------------------------------------------------------------

def test_extract_triples_skips_none_entities(monkeypatch):
    """
    Without the fix (app/services/kg_service.py:75-76):
        The function would call `create_relationship(s["id"], t["id"])` while
        `s` is None and crash with:
            TypeError: 'NoneType' object is not subscriptable

    With the fix:
        The None-check (`if s is None or t is None: continue`) skips the
        triple. `create_relationship` is never called for the bad triple,
        and the function returns a valid result dict.
    """
    from app.services import kg_service

    create_relationship_calls = []

    def mock_create_entity(name, type="concept", description=""):
        if name == "A":
            return None  # Simulate create_entity returning None for the source
        return {"id": 1, "name": name, "type": type, "description": description}

    def mock_create_relationship(source_id, target_id, rel_type, weight=1.0):
        create_relationship_calls.append((source_id, target_id, rel_type))
        return {
            "id": 1, "source_entity_id": source_id, "target_entity_id": target_id,
            "relationship_type": rel_type, "weight": weight,
        }

    monkeypatch.setattr(kg_service, "create_entity", mock_create_entity)
    monkeypatch.setattr(kg_service, "create_relationship", mock_create_relationship)

    # This call would raise TypeError without the fix.
    result = kg_service.extract_triples([("A", "rel", "B")])

    # Assertion: the function returned a valid result instead of crashing.
    assert result is not None
    # Assertion: the triple was SKIPPED — create_relationship was never called.
    assert len(create_relationship_calls) == 0


# ---------------------------------------------------------------------------
# TEST 2: kg_db.add_entity raises if the IntegrityError fallback SELECT returns no row
# ---------------------------------------------------------------------------

def test_add_entity_raises_on_missing_fallback_row(monkeypatch):
    """
    Without the fix (app/models/kg_db.py:50-52):
        After the INSERT raises IntegrityError, the SELECT inside the
        handler also returns no row. The function would either silently
        fall through to `eid = row["id"]` (crash) or return a corrupt
        None value, masking the real DB problem from the caller.

    With the fix:
        The `if row is None: raise` guard re-raises the IntegrityError,
        surfacing the failure loudly to the caller.
    """
    from app.models import kg_db

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # SELECT returns no row.

    # First execute() = INSERT, raises IntegrityError.
    # Second execute() = fallback SELECT, returns the mock cursor
    # (whose fetchone() returns None).
    mock_conn.execute.side_effect = [
        sqlite3.IntegrityError("UNIQUE constraint failed: entities.name"),
        mock_cursor,
    ]

    monkeypatch.setattr(kg_db, "_get_conn", lambda: mock_conn)

    # With the fix, add_entity re-raises the original IntegrityError.
    # Without the fix, `row["id"]` would raise TypeError ('NoneType' is
    # not subscriptable) instead — masking the real DB problem.
    with pytest.raises(sqlite3.IntegrityError):
        kg_db.add_entity("X", "y", "z")


# ---------------------------------------------------------------------------
# TEST 3: kg routes — create_relation_route returns 500 on None entity
# ---------------------------------------------------------------------------

def test_create_relation_route_500_on_none_entity(client, monkeypatch):
    """
    Without the fix (app/routes/kg.py:61-67):
        The route would pass None to `create_relationship(s["id"], t["id"])`
        and crash with TypeError, producing a 500 with no controlled JSON.

    With the fix:
        The route checks the result of create_entity and returns a
        500 JSON response with an "error" key.
    """
    from app.routes import kg

    def mock_create_entity(name, type="concept", description=""):
        return None  # Simulate a failed entity create/fetch.

    # Patch the symbol as it is used inside the route module (not the
    # service module — the route holds its own imported reference).
    monkeypatch.setattr(kg, "create_entity", mock_create_entity)

    response = client.post("/kg/relation", json={
        "source_name": "Python",
        "target_name": "Flask",
        "relationship_type": "built with",
    })

    assert response.status_code == 500
    body = response.get_json()
    assert body is not None
    assert "error" in body


# ---------------------------------------------------------------------------
# TEST 4: note_service.debloat_and_structure — stage-1 None check
# ---------------------------------------------------------------------------

def test_debloat_stage1_returns_fallback_on_none(monkeypatch, client):
    """
    Without the fix (app/services/note_service.py:50-52):
        The function would continue past `filtered = ...` (which is None),
        invoke the second OpenAI call, and ultimately return None.
        yt_ingest would then crash on None.split("\\n").

    With the fix:
        The function short-circuits on `if filtered is None:` and returns
        the deterministic fallback note. The second OpenAI call is never
        made.
    """
    from app.services import note_service

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None  # Stage 1 returns None.

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setattr(note_service, "OpenAI", lambda **kwargs: mock_client)

    with client.application.app_context():
        result = note_service.debloat_and_structure(
            "transcript text", "Title", "Channel"
        )

    # The fix short-circuits: the second OpenAI call must NOT be made.
    # Without the fix, call_count would be 2 (stage 1 + stage 2).
    assert mock_client.chat.completions.create.call_count == 1
    # The result is the deterministic fallback (non-None string).
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# TEST 5: note_service.debloat_and_structure — stage-2 None check
# ---------------------------------------------------------------------------

def test_debloat_stage2_returns_filtered_on_none(monkeypatch, client):
    """
    Without the fix (app/services/note_service.py:74-77):
        If the second OpenAI call (the merge pass) returned content=None,
        the function would return None. yt_ingest would then crash on
        None.split("\\n"), surfacing as an unhandled exception.

    With the fix:
        When the stage-2 response content is None, debloat_and_structure
        returns the stage-1 (filtered) output, which is a non-None string.
    """
    from app.services import note_service

    stage1_content = "## Notes\n\nStage 1 filtered content here"
    stage1_response = MagicMock()
    stage1_response.choices = [MagicMock()]
    stage1_response.choices[0].message.content = stage1_content

    stage2_response = MagicMock()
    stage2_response.choices = [MagicMock()]
    stage2_response.choices[0].message.content = None  # Stage 2 returns None.

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [stage1_response, stage2_response]

    monkeypatch.setattr(note_service, "OpenAI", lambda **kwargs: mock_client)

    with client.application.app_context():
        result = note_service.debloat_and_structure(
            "transcript", "Title", "Channel"
        )

    # With the fix, the result is the stage-1 (filtered) content.
    # Without the fix, result would be None.
    assert result is not None
    assert result == stage1_content


# ---------------------------------------------------------------------------
# TEST 6: youtube routes — yt_ingest returns 500 on None markdown
# ---------------------------------------------------------------------------

def test_yt_ingest_500_on_none_markdown(client, monkeypatch):
    """
    Without the fix (app/routes/youtube.py:34-40):
        yt_ingest would call None.split("\\n") and crash with:
            AttributeError: 'NoneType' object has no attribute 'split'
        The route's outer `except Exception` swallows the AttributeError
        and returns a 500 with the raw Python error string in the body
        (e.g., "'NoneType' object has no attribute 'split'"), leaking
        internals to the client.

    With the fix:
        yt_ingest checks the result of debloat_and_structure first and
        returns a 500 JSON response with the controlled message
        "failed to structure transcript".
    """
    from app.routes import youtube

    # Patch the symbols as they are used inside the youtube route module.
    monkeypatch.setattr(youtube, "fetch_transcript", lambda url: "Sample transcript text")
    monkeypatch.setattr(youtube, "extract_video_id", lambda url: "abc123")
    monkeypatch.setattr(youtube, "debloat_and_structure", lambda t, title, channel: None)

    response = client.post("/yt/ingest", json={
        "video_url": "https://youtube.com/watch?v=abc123"
    })

    assert response.status_code == 500
    body = response.get_json()
    assert body is not None
    assert "error" in body
    # The fix returns a specific controlled error message. Without the
    # fix, the body would contain the raw Python AttributeError text
    # ("'NoneType' object has no attribute 'split'") instead.
    assert body["error"] == "failed to structure transcript"
