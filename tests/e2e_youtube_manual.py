#!/usr/bin/env python3
"""
E2E manual test for YouTube ingestion pipeline.
Run: python tests/e2e_youtube_manual.py
Requires .env with OPENROUTER_API_KEY and a real YOUTUBE_API_KEY.
"""
import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv()

os.environ["YT_CHECK_INTERVAL_HOURS"] = "999"
os.environ["YT_MAX_PER_CHECK"] = "3"

_obsidian_dir = tempfile.mkdtemp(prefix="obsidian_e2e_")
os.environ["OBSIDIAN_NOTES_PATH"] = _obsidian_dir

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must patch BEFORE the import since create_app captures a local reference
import app.services.embedding_service as es_mod
es_mod.init_embedding_service = lambda: None
es_mod.generate_embedding = lambda text: [0.0] * 384
es_mod.store_embedding = lambda message_id, text, session_id, role: None
es_mod.semantic_search = lambda query, limit=10: {"ids": [[]], "distances": [[]], "metadatas": [[]]}

from app import create_app

app = create_app()
client = app.test_client()


def test_search():
    print("\n=== /yt/search ===")
    resp = client.get("/yt/search?q=python+tutorial")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    print(f"  Found {len(data)} results")
    if data:
        print(f"  First: {data[0]['title'][:60]}...")
    print("  PASS")


def test_search_no_query():
    print("\n=== /yt/search (no query) ===")
    resp = client.get("/yt/search")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print(f"  Response: {resp.get_json()}")
    print("  PASS")


has_youtube_key = bool(os.getenv("YOUTUBE_API_KEY"))
has_openrouter_key = bool(os.getenv("OPENROUTER_API_KEY"))


def test_channel_videos():
    if not has_youtube_key:
        print("\n=== /yt/channel (SKIP: no YOUTUBE_API_KEY) ===")
        return
    print("\n=== /yt/channel ===")
    channel_url = "https://www.youtube.com/@sentdex"
    resp = client.post("/yt/channel",
                       json={"channel_url": channel_url},
                       content_type="application/json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    print(f"  Ingested: {data.get('ingested_count', 'N/A')} videos")
    print(f"  Channel: {data.get('channel_name', 'N/A')}")
    print("  PASS")


def test_subscribe_unsubscribe():
    if not has_youtube_key:
        print("\n=== /yt/subscribe (SKIP: no YOUTUBE_API_KEY) ===")
        return
    print("\n=== /yt/subscribe ===")
    channel_url = "https://www.youtube.com/@sentdex"
    resp = client.post("/yt/subscribe",
                       json={"channel_url": channel_url},
                       content_type="application/json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    sub_id = data.get("id")
    channel_name = data.get("channel_name", "N/A")
    print(f"  Subscribed to: {channel_name} (id={sub_id})")

    print("\n=== /yt/subscriptions ===")
    resp = client.get("/yt/subscriptions")
    assert resp.status_code == 200
    subs = resp.get_json()
    print(f"  Active subscriptions: {len(subs)}")
    assert any(s["channel_name"] == channel_name for s in subs), "Missing subscription"

    if sub_id is not None:
        print("\n=== /yt/unsubscribe ===")
        resp = client.post("/yt/unsubscribe",
                           json={"sub_id": sub_id},
                           content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        print(f"  {data}")
        assert data.get("status") == "ok"

    print("  PASS")


def test_ingest():
    if not has_openrouter_key:
        print("\n=== /yt/ingest (SKIP: no OPENROUTER_API_KEY) ===")
        return
    print("\n=== /yt/ingest ===")
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    resp = client.post("/yt/ingest",
                       json={"video_url": video_url},
                       content_type="application/json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    print(f"  {data.get('status', 'N/A')} — title={data.get('title', 'N/A')[:50]}")
    print("  PASS")


def test_note_file_created():
    """Verify a .md file was written to obsidian folder from any of the above tests"""
    print("\n=== Obsidian note file check ===")
    files = os.listdir(_obsidian_dir)
    md_files = [f for f in files if f.endswith(".md")]
    print(f"  Notes in {_obsidian_dir}: {len(md_files)}")
    for f in md_files[:3]:
        path = os.path.join(_obsidian_dir, f)
        with open(path) as fh:
            content = fh.read(300)
        print(f"  {f}: {content[:80]}...")
    if md_files:
        print("  PASS")
    else:
        print("  WARN: No note files created (expected if ingest with OpenRouter ran)")


if __name__ == "__main__":
    tests = [
        test_search,
        test_search_no_query,
        test_channel_videos,
        test_ingest,
        test_note_file_created,
        test_subscribe_unsubscribe,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
