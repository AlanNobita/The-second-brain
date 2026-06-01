"""Test youtube_db module.

Uses importlib to import youtube_db directly, bypassing Flask dependency in app/__init__.py.
When Flask is available, switch to: from app.models.youtube_db import ...
"""
import importlib.util
import os
import sys

# Import youtube_db directly via importlib to avoid Flask dependency in app/__init__.py
_SPEC = importlib.util.spec_from_file_location(
    "youtube_db",
    os.path.join(os.path.dirname(__file__), "..", "app", "models", "youtube_db.py")
)
youtube_db = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(youtube_db)

db_path = youtube_db.DB_PATH
if os.path.exists(db_path):
    os.remove(db_path)


def test_init_youtube_db():
    youtube_db.init_youtube_db()


def test_add_and_get_subscription():
    sub = youtube_db.add_subscription("https://youtube.com/@channel", "Test Channel")
    assert sub["channel_name"] == "Test Channel"
    assert sub["active"] == 1


def test_get_subscriptions_returns_active():
    subs = youtube_db.get_subscriptions()
    assert len(subs) >= 1
    assert all(s["active"] == 1 for s in subs)


def test_remove_subscription():
    sub = youtube_db.add_subscription("https://youtube.com/@remove", "Remove Me")
    result = youtube_db.remove_subscription(sub["id"])
    assert result is True
    fetched = youtube_db.get_subscription(sub["id"])
    assert fetched["active"] == 0


def test_update_last_checked():
    sub = youtube_db.add_subscription("https://youtube.com/@check", "Check Me")
    youtube_db.update_last_checked(sub["id"])
    fetched = youtube_db.get_subscription(sub["id"])
    assert fetched["last_checked"] is not None


def test_mark_inactive():
    sub = youtube_db.add_subscription("https://youtube.com/@fail", "Fail Me")
    youtube_db.mark_subscription_inactive(sub["id"])
    fetched = youtube_db.get_subscription(sub["id"])
    assert fetched["active"] == 0


def test_is_video_ingested_false():
    assert youtube_db.is_video_ingested("nonexistent_video_id") is False


def test_is_video_ingested_true():
    youtube_db.add_ingested_video(
        "test_vid_123", "Test Channel", "Test Title",
        "https://youtube.com/watch?v=test_vid_123", "sess_001"
    )
    assert youtube_db.is_video_ingested("test_vid_123") is True


def test_get_ingested_videos():
    videos = youtube_db.get_ingested_videos()
    assert len(videos) >= 1
