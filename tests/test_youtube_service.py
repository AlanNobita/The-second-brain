"""Test youtube_service module directly, bypassing Flask app import chain."""
import importlib.util
import os
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "youtube_service",
    os.path.join(os.path.dirname(__file__), "..", "app", "services", "youtube_service.py")
)
ys = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ys)


TranscriptError = ys.TranscriptError
fetch_transcript = ys.fetch_transcript
search_youtube = ys.search_youtube
get_channel_videos = ys.get_channel_videos
extract_channel_id = ys.extract_channel_id
extract_video_id = ys.extract_video_id


def test_extract_channel_id_from_handle():
    cid = extract_channel_id("https://youtube.com/@channelhandle")
    assert cid == "@channelhandle"


def test_extract_channel_id_from_custom():
    cid = extract_channel_id("https://youtube.com/c/CustomName")
    assert cid == "CustomName"


def test_extract_channel_id_from_id():
    cid = extract_channel_id("https://youtube.com/channel/UC123abc")
    assert cid == "UC123abc"


def test_extract_video_id_from_watch_url():
    vid = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"


def test_extract_video_id_from_short_url():
    vid = extract_video_id("https://youtu.be/dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"


def test_extract_video_id_from_embed_url():
    vid = extract_video_id("https://youtube.com/embed/dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"


def test_extract_video_id_from_shorts_url():
    vid = extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ")
    assert vid == "dQw4w9WgXcQ"


def test_extract_video_id_returns_none():
    vid = extract_video_id("https://example.com")
    assert vid is None


def test_fetch_transcript_raises_on_bad_url():
    with pytest.raises(TranscriptError):
        fetch_transcript("https://youtube.com/watch?v=nonexistent_video_xyz")


def test_search_youtube_returns_list():
    results = search_youtube("python tutorial", max_results=3)
    assert len(results) <= 3
    if results:
        assert "video_id" in results[0]
        assert "title" in results[0]
        assert "url" in results[0]


def test_get_channel_videos_returns_list():
    results = get_channel_videos("https://youtube.com/@Fireship", max_results=2)
    assert len(results) <= 2
    if results:
        assert "video_id" in results[0]
        assert "title" in results[0]
