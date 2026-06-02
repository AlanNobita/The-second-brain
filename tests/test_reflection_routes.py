import tempfile
import os
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_db():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    import app.models.reflection_db as mod
    original_reflection_path = mod.DB_PATH
    import app.models.db as msg_mod
    original_msg_path = msg_mod.DB_PATH
    mod.DB_PATH = db_path
    msg_mod.DB_PATH = db_path
    mod.init_reflection_db()
    msg_mod.init_db()
    msg_mod.init_fts()
    yield
    mod.DB_PATH = original_reflection_path
    msg_mod.DB_PATH = original_msg_path
    os.unlink(db_path)


def test_list_reflections_empty(client, isolated_db):
    resp = client.get("/api/reflections")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_reflections_with_data(client, isolated_db):
    from app.models.reflection_db import save_reflection
    save_reflection("2026-06-01", "first day summary", topics=["flask"])
    resp = client.get("/api/reflections")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-06-01"


def test_todays_reflection_missing(client, isolated_db):
    resp = client.get("/api/reflection/today")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is None


def test_todays_reflection_returns_existing(client, isolated_db):
    import datetime
    today = datetime.date.today().isoformat()
    from app.models.reflection_db import save_reflection
    save_reflection(today, "today's learning", topics=["python"])
    resp = client.get("/api/reflection/today")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["date"] == today
    assert "today" in data["summary"]


@patch("app.routes.reflections.generate_daily_reflection")
def test_generate_reflection_no_messages(mock_generate, client, isolated_db):
    mock_generate.return_value = None
    resp = client.post("/api/reflection/generate")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@patch("app.routes.reflections.generate_daily_reflection")
def test_generate_reflection_success(mock_generate, client, isolated_db):
    mock_generate.return_value = {
        "date": "2026-06-01",
        "summary": "great learning day",
        "topics": ["flask", "testing"],
    }
    resp = client.post("/api/reflection/generate")
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["date"] == "2026-06-01"
    assert "flask" in data["topics"]
