import tempfile
import os

from app.models.reflection_db import (
    init_reflection_db,
    save_reflection,
    get_reflection,
    list_reflections,
    reflection_exists,
    get_connection,
)


def test_init_creates_table():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    try:
        import app.models.reflection_db as mod
        original_path = mod.DB_PATH
        mod.DB_PATH = db_path
        try:
            init_reflection_db()
            conn = mod.get_connection()
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            conn.close()
            names = [t["name"] for t in tables]
            assert "daily_reflections" in names
        finally:
            mod.DB_PATH = original_path
    finally:
        os.unlink(db_path)


def test_save_and_get_reflection():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    try:
        import app.models.reflection_db as mod
        original_path = mod.DB_PATH
        mod.DB_PATH = db_path
        try:
            init_reflection_db()
            save_reflection(
                "2026-06-01",
                "Today I learned about Flask and embeddings.",
                topics=["flask", "embeddings"],
                message_ids=[1, 2, 3],
            )
            ref = get_reflection("2026-06-01")
            assert ref is not None
            assert ref["date"] == "2026-06-01"
            assert "Flask" in ref["summary"]
            assert "flask" in ref["topics"]
            assert "1" in ref["message_ids"]
        finally:
            mod.DB_PATH = original_path
    finally:
        os.unlink(db_path)


def test_reflection_exists():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    try:
        import app.models.reflection_db as mod
        original_path = mod.DB_PATH
        mod.DB_PATH = db_path
        try:
            init_reflection_db()
            assert reflection_exists("2026-06-01") is False
            save_reflection("2026-06-01", "test summary")
            assert reflection_exists("2026-06-01") is True
        finally:
            mod.DB_PATH = original_path
    finally:
        os.unlink(db_path)


def test_list_reflections_ordered():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    try:
        import app.models.reflection_db as mod
        original_path = mod.DB_PATH
        mod.DB_PATH = db_path
        try:
            init_reflection_db()
            save_reflection("2026-06-02", "second day")
            save_reflection("2026-06-01", "first day")
            refs = list_reflections(limit=10)
            assert len(refs) == 2
            assert refs[0]["date"] == "2026-06-02"
            assert refs[1]["date"] == "2026-06-01"
        finally:
            mod.DB_PATH = original_path
    finally:
        os.unlink(db_path)


def test_save_reflection_replaces():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    try:
        import app.models.reflection_db as mod
        original_path = mod.DB_PATH
        mod.DB_PATH = db_path
        try:
            init_reflection_db()
            save_reflection("2026-06-01", "original")
            save_reflection("2026-06-01", "updated")
            ref = get_reflection("2026-06-01")
            assert ref["summary"] == "updated"
            refs = list_reflections(limit=10)
            assert len(refs) == 1  # no duplicate
        finally:
            mod.DB_PATH = original_path
    finally:
        os.unlink(db_path)
