# YouTube Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add YouTube transcript ingestion pipeline with chat commands, channel subscriptions, APScheduler background checks, and Obsidian file output.

**Architecture:** New `youtube_db.py` for SQLite tables, `youtube_service.py` for transcript fetching (3-tier fallback), `note_service.py` for LLM de-bloat + file writing, `subscription_service.py` for subscription management, `scheduler.py` for background checks, and `routes/youtube.py` for HTTP endpoints. Frontend detects `/yt` commands in chat input.

**Tech Stack:** Flask, SQLite, ChromaDB, OpenRouter, `youtube-transcript-api`, `yt-dlp`, `APScheduler`

---

## File Structure

### New Files

| File | Responsibility |
|---|---|
| `app/models/youtube_db.py` | SQLite CRUD for `subscriptions` and `ingested_videos` tables |
| `app/services/youtube_service.py` | Transcript fetch with 3-tier fallback; YouTube search; channel video listing |
| `app/services/note_service.py` | De-bloat via OpenRouter; write `.md` to Obsidian folder |
| `app/services/subscription_service.py` | Subscribe/unsub/list/check logic |
| `app/services/scheduler.py` | APScheduler init + shutdown |
| `app/routes/youtube.py` | 6 HTTP endpoints for commands |
| `tests/test_youtube_db.py` | Tests for youtube_db queries |
| `tests/test_youtube_service.py` | Tests for service (mocked HTTP) |
| `tests/test_note_service.py` | Tests for de-bloat + file writing |
| `tests/test_subscription_service.py` | Tests for subscription logic |
| `tests/test_youtube_routes.py` | Integration tests for endpoints |

### Modified Files

| File | Change |
|---|---|
| `app/__init__.py` | Register `youtube_bp` blueprint + call `init_scheduler(app)` |
| `app/services/ai_service.py` | Add lazy subscription check thread before AI call |
| `app/static/script.js` | Add `/yt` command detection + handlers |
| `requirements.txt` | Add 4 new dependencies |
| `app/config.py` | Add `YT_CHECK_INTERVAL_HOURS`, `YT_MAX_PER_CHECK`, `OBSIDIAN_NOTES_PATH` |

---

### Task 1: Database Layer — `youtube_db.py`

**Files:**
- Create: `app/models/youtube_db.py`
- Test: `tests/test_youtube_db.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.models.youtube_db import (
    init_youtube_db, add_subscription, remove_subscription,
    get_subscriptions, get_subscription, update_last_checked,
    mark_subscription_inactive, add_ingested_video,
    is_video_ingested, get_ingested_videos
)

def test_init_youtube_db():
    init_youtube_db()
    # Just ensure no exception; tables should be idempotent

def test_add_and_get_subscription():
    sub = add_subscription("https://youtube.com/@channel", "Test Channel")
    assert sub["channel_name"] == "Test Channel"
    assert sub["active"] == 1

def test_get_subscriptions_returns_active():
    subs = get_subscriptions()
    assert len(subs) >= 1
    assert all(s["active"] == 1 for s in subs)

def test_remove_subscription():
    sub = add_subscription("https://youtube.com/@remove", "Remove Me")
    result = remove_subscription(sub["id"])
    assert result is True
    fetched = get_subscription(sub["id"])
    assert fetched["active"] == 0

def test_update_last_checked():
    sub = add_subscription("https://youtube.com/@check", "Check Me")
    update_last_checked(sub["id"])
    fetched = get_subscription(sub["id"])
    assert fetched["last_checked"] is not None

def test_mark_inactive():
    sub = add_subscription("https://youtube.com/@fail", "Fail Me")
    mark_subscription_inactive(sub["id"])
    fetched = get_subscription(sub["id"])
    assert fetched["active"] == 0

def test_is_video_ingested_false():
    assert is_video_ingested("nonexistent_video_id") is False

def test_is_video_ingested_true():
    add_ingested_video("test_vid_123", "Test Channel", "Test Title", "https://youtube.com/watch?v=test_vid_123", "sess_001")
    assert is_video_ingested("test_vid_123") is True

def test_get_ingested_videos():
    videos = get_ingested_videos()
    assert len(videos) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_db.py -v`
Expected: ImportError — module not found

- [ ] **Step 3: Write minimal implementation**

```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "second_brain.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_youtube_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_url  TEXT    NOT NULL UNIQUE,
            channel_name TEXT    NOT NULL,
            last_checked TEXT,
            fail_count   INTEGER NOT NULL DEFAULT 0,
            active       INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS ingested_videos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id     TEXT    NOT NULL UNIQUE,
            channel_name TEXT    NOT NULL,
            video_title  TEXT    NOT NULL,
            video_url    TEXT    NOT NULL,
            ingested_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            session_id   TEXT    NOT NULL,
            file_path    TEXT
        );
    """)
    conn.commit()
    conn.close()

def add_subscription(channel_url, channel_name):
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO subscriptions (channel_url, channel_name) VALUES (?, ?)",
        (channel_url, channel_name)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE channel_url = ?", (channel_url,)
    ).fetchone()
    conn.close()
    return dict(row)

def get_subscription(sub_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE id = ?", (sub_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_subscriptions(only_active=True):
    conn = _get_conn()
    if only_active:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE active = 1 ORDER BY channel_name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY channel_name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def remove_subscription(sub_id):
    conn = _get_conn()
    conn.execute("UPDATE subscriptions SET active = 0 WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
    return True

def update_last_checked(sub_id):
    conn = _get_conn()
    conn.execute(
        "UPDATE subscriptions SET last_checked = datetime('now'), fail_count = 0 WHERE id = ?",
        (sub_id,)
    )
    conn.commit()
    conn.close()

def mark_subscription_inactive(sub_id):
    conn = _get_conn()
    conn.execute(
        "UPDATE subscriptions SET active = 0 WHERE id = ?", (sub_id,)
    )
    conn.commit()
    conn.close()

def add_ingested_video(video_id, channel_name, video_title, video_url, session_id, file_path=None):
    conn = _get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO ingested_videos
           (video_id, channel_name, video_title, video_url, session_id, file_path)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (video_id, channel_name, video_title, video_url, session_id, file_path)
    )
    conn.commit()
    conn.close()

def is_video_ingested(video_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM ingested_videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    conn.close()
    return row is not None

def get_ingested_videos(limit=50):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM ingested_videos ORDER BY ingested_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_db.py -v`
Expected: all tests PASS (note: some may fail if `init_youtube_db` hasn't been called — ensure `app/__init__.py` calls it before tests run, or call it in conftest.py)

- [ ] **Step 5: Commit**

```bash
git add app/models/youtube_db.py tests/test_youtube_db.py
git commit -m "feat: add youtube db layer for subscriptions and ingested videos"
```

---

### Task 2: YouTube Service — Transcript Fetching

**Files:**
- Create: `app/services/youtube_service.py`
- Test: `tests/test_youtube_service.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.services.youtube_service import (
    fetch_transcript,
    search_youtube,
    get_channel_videos,
    extract_channel_id,
    TranscriptError,
)

def test_extract_channel_id_from_handle():
    cid = extract_channel_id("https://youtube.com/@channelhandle")
    assert cid == "@channelhandle"

def test_extract_channel_id_from_custom():
    cid = extract_channel_id("https://youtube.com/c/CustomName")
    assert cid == "CustomName"

def test_extract_channel_id_from_id():
    cid = extract_channel_id("https://youtube.com/channel/UC123abc")
    assert cid == "UC123abc"

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_service.py -v`
Expected: ImportError — module not found

- [ ] **Step 3: Write minimal implementation**

```python
import re
import subprocess
import json
from urllib.parse import urlparse, parse_qs

class TranscriptError(Exception):
    pass

def extract_channel_id(url):
    path = urlparse(url).path.strip("/")
    # @handle
    if path.startswith("@"):
        return path
    # /c/name or /channel/ID
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[-1]
    return path

def fetch_transcript(video_url):
    # Strategy 1: youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id = extract_video_id(video_url)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(segment["text"] for segment in transcript_list)
    except Exception as e:
        pass

    # Strategy 2: yt-dlp
    try:
        result = subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "en",
             "--convert-subs", "srt", "-o", "/tmp/%(id)s", video_url],
            capture_output=True, text=True, timeout=60
        )
        video_id = extract_video_id(video_url)
        srt_path = f"/tmp/{video_id}.en.srt"
        if os.path.exists(srt_path):
            with open(srt_path, "r") as f:
                raw = f.read()
            os.remove(srt_path)
            return strip_srt(raw)
    except Exception:
        pass

    raise TranscriptError(f"No captions available for {video_url}")

def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/")
    qs = parse_qs(parsed.query)
    return qs.get("v", [None])[0]

def strip_srt(srt_text):
    lines = srt_text.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        if line and not line.startswith("<"):
            text_lines.append(line)
    return " ".join(text_lines)

def search_youtube(query, max_results=5):
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch{max_results}:{query}", "--dump-json", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            videos.append({
                "video_id": data["id"],
                "title": data["title"],
                "channel": data.get("channel", "Unknown"),
                "channel_url": data.get("channel_url", ""),
                "published_at": data.get("upload_date", ""),
                "url": f"https://youtube.com/watch?v={data['id']}",
            })
        return videos[:max_results]
    except Exception as e:
        return []

def get_channel_videos(channel_url, max_results=5):
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch{max_results}:{channel_url}", "--dump-json", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        return search_youtube(channel_url, max_results)
    except Exception:
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/youtube_service.py tests/test_youtube_service.py
git commit -m "feat: add youtube transcript fetching with fallback chain"
```

---

### Task 3: Note Service — De-bloat + Obsidian Export

**Files:**
- Create: `app/services/note_service.py`
- Test: `tests/test_note_service.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
import tempfile
import os
from app.services.note_service import debloat_and_structure, save_note_file

SAMPLE_TRANSCRIPT = """
hey guys welcome back to the channel today we're talking about python
before we start don't forget to like and subscribe
python is a dynamically typed language which means you don't need to declare types
it was created by guido van rossum in 1991
one key feature is that indentation matters for block structure
another important thing is that python has automatic memory management
thanks to our sponsor raid shadow legends for making this video possible
check them out at the link below
so to summarize python is great for beginners and experts alike
make sure to hit that bell icon for more content
"""

def test_debloat_removes_greetings():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert "hey guys" not in result.lower()
    assert "like and subscribe" not in result.lower()
    assert "sponsor" not in result.lower()

def test_debloat_preserves_substance():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert "dynamically typed" in result
    assert "Guido van Rossum" in result or "guido van rossum" in result.lower()
    assert "1991" in result
    assert "indentation" in result
    assert "memory management" in result

def test_debloat_returns_markdown():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert result.startswith("#") or "##" in result
    assert "Key Concepts" in result or "Notes" in result

def test_save_note_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_note_file("# Test\n\nContent", "Test Video Title", "2026-06-01", output_dir=tmpdir)
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "Test Video Title" in content
        assert "2026-06-01" in content
```

Note: `debloat_and_structure` calls OpenRouter API. When testing, a real API call will cost tokens. Consider mocking `openai` in tests — but for initial dev, test with a simple regex-based filter as fallback if no API key.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_note_service.py -v`
Expected: ImportError — module not found

- [ ] **Step 3: Write minimal implementation**

```python
import os
import re
from openai import OpenAI
from flask import current_app

def debloat_and_structure(transcript, video_title, channel):
    system_prompt = """You are a note-taking AI. Extract substance from a YouTube transcript.

RULES (strict):
1. Extract ONLY content present in the transcript. No additions, inferences, or summaries.
2. Remove: greetings ("hey guys", "welcome back"), sponsor segments, channel plugs, CTAs, off-topic banter.
3. Preserve: ALL data points, arguments, examples, code, quotes, statistics, references, tools, people, timelines.
4. Organize by ## topic sections. Use natural topic shifts in the transcript as boundaries.
5. Code blocks: verbatim with ``` fences.
6. Do NOT condense. Full substance without filler.
7. Do not guess. Omit or mark [unclear] if not in transcript.
8. No imaginary content. No elaborating on what the speaker said.

Format:
## Key Concepts
- ...

## Notes
[de-bloated full context organized by topic]

## Takeaways
- ...

## References
- ..."""

    try:
        client = OpenAI(
            api_key=current_app.config["OPENROUTER_API_KEY"],
            base_url=current_app.config["OPENROUTER_BASE_URL"],
        )
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {video_title}\nChannel: {channel}\n\nTranscript:\n{transcript}"}
            ]
        )
        return response.choices[0].message.content
    except Exception:
        return _fallback_debloat(transcript)

def _fallback_debloat(transcript):
    lines = transcript.split("\n")
    cleaned = []
    skip_phrases = [
        "hey guys", "welcome back", "don't forget to like", "like and subscribe",
        "hit that bell", "thanks to our sponsor", "check them out", "raid shadow legends",
        "before we start", "make sure to"
    ]
    for line in lines:
        lower = line.strip().lower()
        if any(phrase in lower for phrase in skip_phrases):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    return f"# {video_title}\n\n**Channel:** {channel}\n\n## Notes\n\n{text.strip()}\n\n## Takeaways\n\n-\n\n## References\n\n-"

def save_note_file(markdown, video_title, ingested_date, output_dir=None):
    if output_dir is None:
        output_dir = os.environ.get("OBSIDIAN_NOTES_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "obsidian-ingest"))
    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r'[^\w\s-]', '', video_title).strip().replace(' ', '-')[:80]
    filename = f"{ingested_date}-{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(markdown)
    return filepath
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_note_service.py -v`
Expected: PASS (note: tests that call `debloat_and_structure` will hit OpenRouter unless mocked)

- [ ] **Step 5: Commit**

```bash
git add app/services/note_service.py tests/test_note_service.py
git commit -m "feat: add note de-bloat service and obsidian export"
```

---

### Task 4: Subscription Service

**Files:**
- Create: `app/services/subscription_service.py`
- Test: `tests/test_subscription_service.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.services.subscription_service import (
    subscribe, unsubscribe, list_subscriptions,
    check_subscription, check_all_subscriptions,
    has_due_subscriptions, check_due_subscriptions
)

def test_subscribe():
    sub = subscribe("https://youtube.com/@testchannel")
    assert sub["channel_name"] is not None
    # Cleanup
    from app.models.youtube_db import remove_subscription
    remove_subscription(sub["id"])

def test_list_subscriptions():
    subs = list_subscriptions()
    assert isinstance(subs, list)

def test_has_due_subscriptions():
    result = has_due_subscriptions()
    assert isinstance(result, bool)

def test_unsubscribe():
    sub = subscribe("https://youtube.com/@unsubtest")
    result = unsubscribe(sub["id"])
    assert result is True

def test_check_all_subscriptions():
    result = check_all_subscriptions()
    assert "checked" in result
    assert "new_videos" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_subscription_service.py -v`
Expected: ImportError — module not found

- [ ] **Step 3: Write minimal implementation**

```python
from ..models.youtube_db import (
    add_subscription as db_add_sub,
    remove_subscription as db_remove_sub,
    get_subscriptions as db_get_subs,
    get_subscription as db_get_sub,
    update_last_checked, mark_subscription_inactive,
    add_ingested_video, is_video_ingested,
)
from .youtube_service import get_channel_videos, fetch_transcript, extract_channel_id
from .note_service import debloat_and_structure, save_note_file
from ..models.db import save_message
from .embedding_service import store_embedding
from uuid import uuid4
from datetime import datetime, timedelta

def subscribe(channel_url):
    cid = extract_channel_id(channel_url)
    channel_name = cid.lstrip("@").replace("-", " ").title()
    sub = db_add_sub(channel_url, channel_name)
    check_subscription(sub["id"])
    return sub

def unsubscribe(sub_id):
    return db_remove_sub(sub_id)

def list_subscriptions():
    return db_get_subs(only_active=True)

def check_subscription(sub_id):
    sub = db_get_sub(sub_id)
    if not sub or not sub["active"]:
        return 0
    try:
        videos = get_channel_videos(sub["channel_url"], max_results=5)
    except Exception:
        return 0
    new_count = 0
    for video in videos:
        if is_video_ingested(video["video_id"]):
            continue
        _ingest_single_video(video, sub["channel_name"])
        new_count += 1
    update_last_checked(sub_id)
    return new_count

def check_all_subscriptions():
    subs = db_get_subs(only_active=True)
    checked = 0
    total_new = 0
    for sub in subs:
        try:
            n = check_subscription(sub["id"])
            checked += 1
            total_new += n
        except Exception:
            continue
    return {"checked": checked, "new_videos": total_new}

def has_due_subscriptions():
    subs = db_get_subs(only_active=True)
    if not subs:
        return False
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    for sub in subs:
        if sub["last_checked"] is None or sub["last_checked"] < one_hour_ago:
            return True
    return False

def check_due_subscriptions():
    subs = db_get_subs(only_active=True)
    for sub in subs:
        try:
            check_subscription(sub["id"])
        except Exception:
            continue

def _ingest_single_video(video, channel_name):
    session_id = f"yt_{uuid4().hex[:12]}"
    try:
        transcript = fetch_transcript(video["url"])
        markdown = debloat_and_structure(transcript, video["title"], channel_name)
        lines = markdown.split("\n")
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) > 1800:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        for i, chunk in enumerate(chunks):
            prefix = f"[YouTube] {video['title']} ({i+1}/{len(chunks)})"
            msg_id = save_message(session_id, "assistant", f"{prefix}\n\n{chunk}")
            store_embedding(msg_id, f"{prefix}\n\n{chunk}", session_id, "assistant")
        ingested_date = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = save_note_file(markdown, video["title"], ingested_date)
        add_ingested_video(
            video_id=video["video_id"],
            channel_name=channel_name,
            video_title=video["title"],
            video_url=video["url"],
            session_id=session_id,
            file_path=file_path,
        )
    except Exception:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_subscription_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/subscription_service.py tests/test_subscription_service.py
git commit -m "feat: add subscription service with auto-ingest pipeline"
```

---

### Task 5: Scheduler

**Files:**
- Create: `app/services/scheduler.py`

- [ ] **Step 1: Write minimal implementation** (no tests — scheduler is integration-only)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

_scheduler = None

def init_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    interval = app.config.get("YT_CHECK_INTERVAL_HOURS", 6)
    _scheduler.add_job(
        func=_check_subs_job,
        trigger="interval",
        hours=interval,
        id="yt_sub_check",
        next_run_time=datetime.now() + timedelta(hours=1),
    )
    _scheduler.start()
    import atexit
    atexit.register(shutdown_scheduler)
    return _scheduler

def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None

def _check_subs_job():
    from .subscription_service import check_all_subscriptions
    check_all_subscriptions()
```

- [ ] **Step 2: Test manually** (run `python run.py`, wait, check logs)

Run: `cd /home/alan/Documents/code/the-second-brain && python run.py`
Expected: server starts, scheduler initializes (no crash)

- [ ] **Step 3: Commit**

```bash
git add app/services/scheduler.py
git commit -m "feat: add apscheduler for periodic youtube subscription checks"
```

---

### Task 6: Routes — YouTube Endpoints

**Files:**
- Create: `app/routes/youtube.py`
- Test: `tests/test_youtube_routes.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
import json

def test_yt_search(client):
    response = client.get("/yt/search?q=python+tutorial")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_yt_search_no_query(client):
    response = client.get("/yt/search")
    assert response.status_code == 400

def test_yt_subscribe(client):
    response = client.post("/yt/subscribe", json={"channel_url": "https://youtube.com/@test"})
    assert response.status_code == 200
    data = response.get_json()
    assert "id" in data
    assert "channel_name" in data

def test_yt_subscriptions(client):
    response = client.get("/yt/subscriptions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_yt_unsubscribe(client):
    # First subscribe
    sub_resp = client.post("/yt/subscribe", json={"channel_url": "https://youtube.com/@unsubroute"})
    sub_id = sub_resp.get_json()["id"]
    response = client.post("/yt/unsubscribe", json={"sub_id": sub_id})
    assert response.status_code == 200

def test_yt_ingest(client):
    response = client.post("/yt/ingest", json={"video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ"})
    assert response.status_code in (200, 202)  # may 202 if async
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_routes.py -v`
Expected: ImportError or 404 — blueprint not registered

- [ ] **Step 3: Write minimal implementation**

```python
from flask import Blueprint, jsonify, request
from uuid import uuid4
from ..services.youtube_service import search_youtube, fetch_transcript, extract_video_id
from ..services.note_service import debloat_and_structure, save_note_file
from ..services.subscription_service import subscribe, unsubscribe, list_subscriptions
from ..models.youtube_db import add_subscription, remove_subscription
from ..models.db import save_message
from ..services.embedding_service import store_embedding

youtube_bp = Blueprint("youtube", __name__)

@youtube_bp.route("/yt/search", methods=["GET"])
def yt_search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    results = search_youtube(query, max_results=5)
    return jsonify(results)

@youtube_bp.route("/yt/ingest", methods=["POST"])
def yt_ingest():
    data = request.get_json()
    video_url = data.get("video_url", "")
    if not video_url:
        return jsonify({"error": "video_url is required"}), 400
    session_id = f"yt_{uuid4().hex[:12]}"
    try:
        transcript = fetch_transcript(video_url)
        from ..services.youtube_service import extract_video_id
        vid = extract_video_id(video_url)
        title = f"Ingested Video ({vid})"
        markdown = debloat_and_structure(transcript, title, "YouTube")
        lines = markdown.split("\n")
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) > 1800:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        for i, chunk in enumerate(chunks):
            prefix = f"[YouTube Ingestion] ({i+1}/{len(chunks)})"
            msg_id = save_message(session_id, "assistant", f"{prefix}\n\n{chunk}")
            store_embedding(msg_id, f"{prefix}\n\n{chunk}", session_id, "assistant")
        from datetime import datetime
        ingested_date = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = save_note_file(markdown, title, ingested_date)
        from ..models.youtube_db import add_ingested_video
        add_ingested_video(vid or "unknown", "YouTube", title, video_url, session_id, file_path)
        return jsonify({"session_id": session_id, "file_path": file_path, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@youtube_bp.route("/yt/subscribe", methods=["POST"])
def yt_subscribe():
    data = request.get_json()
    channel_url = data.get("channel_url", "")
    if not channel_url:
        return jsonify({"error": "channel_url is required"}), 400
    sub = subscribe(channel_url)
    return jsonify(sub)

@youtube_bp.route("/yt/unsubscribe", methods=["POST"])
def yt_unsubscribe():
    data = request.get_json()
    sub_id = data.get("sub_id")
    if not sub_id:
        return jsonify({"error": "sub_id is required"}), 400
    result = unsubscribe(sub_id)
    return jsonify({"status": "ok" if result else "not_found"})

@youtube_bp.route("/yt/subscriptions", methods=["GET"])
def yt_subscriptions():
    subs = list_subscriptions()
    return jsonify(subs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/test_youtube_routes.py -v`
Expected: PASS

- [ ] **Step 5: Register blueprint in `app/__init__.py`**

In `app/__init__.py`, add after the existing blueprint registrations:

```python
from .routes import youtube
app.register_blueprint(youtube.youtube_bp)
from .services.scheduler import init_scheduler
init_scheduler(app)
```

Also call `init_youtube_db()` next to `init_db()`:

```python
from .models.youtube_db import init_youtube_db
init_youtube_db()
```

- [ ] **Step 6: Commit**

```bash
git add app/routes/youtube.py tests/test_youtube_routes.py app/__init__.py
git commit -m "feat: add youtube routes and register blueprint"
```

---

### Task 7: Frontend — Chat Command Detection

**Files:**
- Modify: `app/static/script.js`

- [ ] **Step 1: Add command detection + handlers in `script.js`**

Before `sendBtn.addEventListener("click", sendMessage);`, add:

```javascript
async function handleYTCommand(command, args) {
    switch (command) {
        case "ytsearch": {
            const resp = await fetch("/yt/search?q=" + encodeURIComponent(args));
            const results = await resp.json();
            messagesDiv.innerHTML = "";
            addMessage("assistant", "━━━ YouTube Search Results ━━━");
            results.forEach((v, i) => {
                const div = document.createElement("div");
                div.className = "message assistant";
                div.innerHTML = `<strong>${i + 1}. ${escapeHtml(v.title)}</strong><br>
                    ${escapeHtml(v.channel)} · ${escapeHtml(v.published_at)}<br>
                    <a href="#" data-url="${escapeHtml(v.url)}" class="yt-ingest-link">📥 Ingest</a> ·
                    <a href="${escapeHtml(v.url)}" target="_blank">🔗 Watch</a>`;
                div.querySelector(".yt-ingest-link").addEventListener("click", async (e) => {
                    e.preventDefault();
                    addMessage("assistant", "📥 Ingesting video...");
                    await fetch("/yt/ingest", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({video_url: v.url})
                    });
                    addMessage("assistant", "✅ Video ingested!");
                });
                messagesDiv.appendChild(div);
            });
            return true;
        }
        case "ytchannel": {
            addMessage("assistant", "📥 Fetching latest videos from channel...");
            const resp = await fetch("/yt/channel", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({channel_url: args})
            });
            const data = await resp.json();
            addMessage("assistant", `✅ Ingested ${data.ingested_count} videos from channel.`);
            return true;
        }
        case "ytsub": {
            const resp = await fetch("/yt/subscribe", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({channel_url: args})
            });
            const data = await resp.json();
            addMessage("assistant", `✅ Subscribed to ${data.channel_name}. Auto-ingesting every 6h.`);
            return true;
        }
        case "ytunsub": {
            const resp = await fetch("/yt/unsubscribe", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({sub_id: parseInt(args)})
            });
            const data = await resp.json();
            addMessage("assistant", data.status === "ok" ? "✅ Unsubscribed." : "❌ Not found.");
            return true;
        }
        case "ytsubs": {
            const resp = await fetch("/yt/subscriptions");
            const subs = await resp.json();
            messagesDiv.innerHTML = "";
            if (subs.length === 0) {
                addMessage("assistant", "No active subscriptions.");
                return true;
            }
            addMessage("assistant", "━━━ Subscriptions ━━━");
            subs.forEach(s => {
                addMessage("assistant",
                    `${escapeHtml(s.channel_name)}\n` +
                    `Last checked: ${s.last_checked || "never"}\n` +
                    `ID: ${s.id}`
                );
            });
            return true;
        }
        default:
            return false;
    }
}
```

Then modify the `sendMessage` function to check for `/` commands:

```javascript
async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Check for YT commands
    if (text.startsWith("/")) {
        const spaceIdx = text.indexOf(" ");
        const command = spaceIdx === -1 ? text.slice(1) : text.slice(1, spaceIdx);
        const args = spaceIdx === -1 ? "" : text.slice(spaceIdx + 1);
        const handled = await handleYTCommand(command, args);
        if (handled) {
            input.value = "";
            return;
        }
    }

    // Normal chat flow (existing code)
    addMessage("user", text);
    input.value = "";
    sendBtn.disabled = true;
    showTypingIndicator();
    try {
        const response = await fetch("/chat/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId })
        });
        const data = await response.json();
        sessionId = data.session_id;
        removeTypingIndicator();
        addMessage("assistant", data.reply);
        loadSessions();
    } catch (err) {
        removeTypingIndicator();
        addMessage("assistant", "Error: could not reach the server.");
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}
```

- [ ] **Step 2: Test manually** — start server, type `/ytsearch python` in chat

Run: `cd /home/alan/Documents/code/the-second-brain && python run.py`
Then open browser, type `/ytsearch python` — verify search results appear as clickable cards.

- [ ] **Step 3: Commit**

```bash
git add app/static/script.js
git commit -m "feat: add /yt command detection in chat frontend"
```

---

### Task 8: Config + Dependencies

**Files:**
- Modify: `app/config.py`
- Modify: `requirements.txt`
- Modify: `.example.env`

- [ ] **Step 1: Add config variables to `app/config.py`**

Add inside `Config` class:

```python
    YT_CHECK_INTERVAL_HOURS = int(os.getenv("YT_CHECK_INTERVAL_HOURS", "6"))
    YT_MAX_PER_CHECK = int(os.getenv("YT_MAX_PER_CHECK", "5"))
    OBSIDIAN_NOTES_PATH = os.getenv("OBSIDIAN_NOTES_PATH", os.path.join(os.path.dirname(__file__), "..", "obsidian-ingest"))
```

- [ ] **Step 2: Update `requirements.txt`**

Append:

```
youtube-transcript-api==1.0.2
yt-dlp>=2024.12.0
google-api-python-client>=2.150.0
APScheduler>=3.10.4
```

- [ ] **Step 3: Update `.example.env`**

Append:

```
# YouTube Ingestion
YT_CHECK_INTERVAL_HOURS=6
YT_MAX_PER_CHECK=5
OBSIDIAN_NOTES_PATH=./obsidian-ingest
```

- [ ] **Step 4: Install new dependencies**

Run: `cd /home/alan/Documents/code/the-second-brain && pip install -r requirements.txt`
Expected: all 4 packages install without error

- [ ] **Step 5: Commit**

```bash
git add app/config.py requirements.txt .example.env
git commit -m "chore: add youtube ingestion config and dependencies"
```

---

### Task 9: Lazy Subscription Check in AI Service

**Files:**
- Modify: `app/services/ai_service.py`

- [ ] **Step 1: Add lazy check before AI call**

In `get_ai_response`, after saving the user message but before calling OpenRouter, add:

```python
    # Lazy subscription check
    from .subscription_service import has_due_subscriptions, check_due_subscriptions
    if has_due_subscriptions():
        import threading
        t = threading.Thread(target=check_due_subscriptions, daemon=True)
        t.start()
```

- [ ] **Step 2: Test manually** — subscribe to a channel, then send a chat message

Run: `cd /home/alan/Documents/code/the-second-brain && python run.py`
Expected: chat message triggers background subscription check (check logs/server output)

- [ ] **Step 3: Commit**

```bash
git add app/services/ai_service.py
git commit -m "feat: lazy subscription check before ai response"
```

---

### Task 10: Style Tweaks (optional)

**Files:**
- Modify: `app/static/style.css`

- [ ] **Step 1: Add minimal styles for YT result cards**

Add to `style.css`:

```css
.yt-result {
    background: #f0f8ff;
    border: 1px solid #cce5ff;
    border-radius: 8px;
    padding: 12px;
    margin: 4px 0;
}
.yt-result a {
    color: #007aff;
    text-decoration: none;
    margin-right: 8px;
}
.yt-ingest-link {
    cursor: pointer;
    font-weight: 600;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/style.css
git commit -m "style: add youtube result card styles"
```

---

### Task 11: End-to-End Manual Test

- [ ] **Step 1: Start the server**

Run: `cd /home/alan/Documents/code/the-second-brain && python run.py`

- [ ] **Step 2: Test `/ytsearch`**

Open browser → type `/ytsearch python async` → verify 5 results appear as clickable cards
Click "📥 Ingest" on one → verify "Ingesting..." followed by "✅ Video ingested!"

- [ ] **Step 3: Test `/ytsub`**

Type `/ytsub https://youtube.com/@Fireship` → verify subscription confirmation

- [ ] **Step 4: Test `/ytsubs`**

Type `/ytsubs` → verify subscription appears in list

- [ ] **Step 5: Test `/ytunsub`**

Type `/ytunsub 1` → verify unsubscribed

- [ ] **Step 6: Check Obsidian folder**

Run: `ls -la obsidian-ingest/` → verify `.md` files were created
Open one → verify YAML frontmatter and de-bloated content

- [ ] **Step 7: Check ChromaDB query**

Run: send a normal chat message asking about ingested content → verify AI retrieves relevant YouTube notes

- [ ] **Step 8: Run all tests**

Run: `cd /home/alan/Documents/code/the-second-brain && python -m pytest tests/ -v`
Expected: all tests pass

---

## Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| Data model (subscriptions + ingested_videos) | Task 1 |
| Transcript fetch with 3-tier fallback | Task 2 |
| De-bloat via OpenRouter | Task 3 |
| Save `.md` to Obsidian folder | Task 3 |
| Chat commands (search, ingest, subscribe, unsub, list) | Task 6 + 7 |
| Subscription CRUD | Task 4 |
| Background scheduler (APScheduler, 6h interval) | Task 5 |
| Lazy check on chat message | Task 9 |
| Obsidian file format with YAML frontmatter | Task 3 (`save_note_file`) |
| Hallucination guard in de-bloat prompt | Task 3 (`debloat_and_structure` system prompt) |
| Dedup via ingested_videos.video_id UNIQUE | Task 1 |
| Error handling (no captions, rate limits) | Task 2 + 4 |
| Config via `.env` | Task 8 |
| Styling for result cards | Task 10 |
