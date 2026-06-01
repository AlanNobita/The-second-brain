"""Test youtube_db module using a fresh temp database per test."""
import importlib.util
import os
import pytest

# Import youtube_db module directly, bypassing Flask dependency
_SPEC = importlib.util.spec_from_file_location(
    "youtube_db",
    os.path.join(os.path.dirname(__file__), "..", "app", "models", "youtube_db.py")
)
youtube_db = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(youtube_db)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Use a temp database for each test so tests are fully isolated."""
    original_db_path = youtube_db.DB_PATH
    youtube_db.DB_PATH = str(tmp_path / "test.db")
    youtube_db.init_youtube_db()
    yield
    youtube_db.DB_PATH = original_db_path


def test_add_and_get_subscription():
    sub = youtube_db.add_subscription("https://youtube.com/@channel", "Test Channel")
    assert sub["channel_name"] == "Test Channel"
    assert sub["active"] == 1


def test_get_subscriptions_returns_active():
    youtube_db.add_subscription("https://youtube.com/@a", "Channel A")
    youtube_db.add_subscription("https://youtube.com/@b", "Channel B")
    subs = youtube_db.get_subscriptions()
    assert len(subs) == 2
    assert all(s["active"] == 1 for s in subs)


def test_remove_subscription():
    sub = youtube_db.add_subscription("https://youtube.com/@remove", "Remove Me")
    result = youtube_db.remove_subscription(sub["id"])
    assert result is True
    fetched = youtube_db.get_subscription(sub["id"])
    assert fetched["active"] == 0


def test_remove_subscription_nonexistent():
    result = youtube_db.remove_subscription(999)
    assert result is False


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
    youtube_db.add_ingested_video("v1", "Chan", "T1", "url1", "s1")
    youtube_db.add_ingested_video("v2", "Chan", "T2", "url2", "s2")
    videos = youtube_db.get_ingested_videos()
    assert len(videos) == 2


def test_add_subscription_reactivates():
    """Subscribing again should re-activate a previously removed channel."""
    sub = youtube_db.add_subscription("https://youtube.com/@reactivate", "Reactivate Me")
    youtube_db.remove_subscription(sub["id"])
    re_sub = youtube_db.add_subscription("https://youtube.com/@reactivate", "Reactivate Me")
    assert re_sub["active"] == 1
