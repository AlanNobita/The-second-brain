# YouTube Ingestion System — Design Spec

## Overview

Add a YouTube ingestion pipeline to the Second Brain that fetches video transcripts, de-bloats them into structured markdown notes (preserving full substance, removing filler), stores them in the RAG system (ChromaDB) and as `.md` files on disk (Obsidian-compatible), and supports both manual chat commands and automatic channel subscriptions via background scheduler.

## Data Model

### SQLite Tables

```sql
CREATE TABLE subscriptions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_url  TEXT    NOT NULL UNIQUE,
    channel_name TEXT    NOT NULL,
    last_checked TEXT,
    fail_count   INTEGER NOT NULL DEFAULT 0,
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE ingested_videos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id     TEXT    NOT NULL UNIQUE,
    channel_name TEXT    NOT NULL,
    video_title  TEXT    NOT NULL,
    video_url    TEXT    NOT NULL,
    ingested_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    session_id   TEXT    NOT NULL,
    file_path    TEXT
);
```

`ingested_videos.session_id` links to the chat session containing the de-bloated notes (which are already embedded in ChromaDB).

### ChromaDB

Notes are stored as chat messages in a normal session (session_id = `yt_{video_id}`), so they get embedded into the existing `"messages"` ChromaDB collection automatically via `store_embedding()`. No separate collection needed.

### Obsidian Files

Notes saved to `OBSIDIAN_NOTES_PATH` (configurable in `.env`, default `./obsidian-ingest/`) as `.md` files with YAML frontmatter:

```markdown
---
title: "Video Title"
channel: "Channel Name"
video_url: "https://youtube.com/watch?v=..."
ingested: "2026-06-01"
tags: [youtube, ingested]
---

# Video Title

**Channel:** Channel Name

## Key Concepts

- ...

## Notes

[de-bloated full context organized by topic segments]

## Takeaways

- ...

## References

- ...
```

## Architecture

### New Files

```
app/
├── models/
│   └── youtube_db.py        # SQLite queries for subs + ingested_videos
├── services/
│   ├── youtube_service.py   # Transcript fetch with fallback chain
│   ├── note_service.py      # De-bloat via OpenRouter, write .md file
│   └── subscription_service.py  # Subscribe/unsub/check logic
├── routes/
│   └── youtube.py           # HTTP endpoints for commands
└── static/
    └── (chat command parsing in script.js, zero new files)
```

### Component Design

#### `youtube_service.py`

```python
def fetch_transcript(video_url: str) -> str:
    # 1. Try youtube-transcript-api (fastest, no download)
    # 2. Fallback to yt-dlp (downloads auto-generated captions)
    # 3. Fallback to YouTube Data API (if configured in .env)
    # Returns raw transcript text
    # On failure, raises VideoTranscriptError

def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    # Uses YouTube Data API search endpoint
    # Returns [{video_id, title, channel_name, published_at, url}]
    # If no API key, use yt-dlp's ytsearch (yt-dlp ytsearch5:query)

def get_channel_videos(channel_url: str, max_results: int = 5) -> list[dict]:
    # Identifies channel ID from URL
    # Fetches latest videos
    # Returns same format as search_youtube
```

Transcript fetch chain:

```
youtube-transcript-api
    ↓ (fails: no captions)
yt-dlp (auto-captions fallback)
    ↓ (fails: restricted / live / etc)
YouTube Data API captions (if key configured)
    ↓ (all fail)
→ error message to user: "No captions available for this video"
```

#### `note_service.py`

```python
def debloat_and_structure(transcript: str, video_title: str, channel: str) -> str:
    # Calls OpenRouter with strict extraction prompt
    # Returns markdown string

def save_note_file(markdown: str, video_title: str, ingested_date: str) -> str:
    # Sanitizes title for filename
    # Writes to OBSIDIAN_NOTES_PATH/{date}-{sanitized_title}.md
    # Returns file path

def ingest_video(video_url: str, session_id: str) -> dict:
    # Orchestrates: fetch -> debloat -> save as chat msgs -> save .md file -> track in DB
    # Returns {session_id, file_path, title}
```

#### `subscription_service.py`

```python
def subscribe(channel_url: str) -> dict:
    # Validates + gets channel name
    # Inserts into DB
    # Immediately checks new videos
    # Returns sub info

def unsubscribe(sub_id: int) -> bool:
    # Sets active = 0

def list_subscriptions() -> list[dict]:
    # Returns all active subs

def check_subscription(sub_id: int) -> int:
    # Gets latest videos, filters ingested, ingests new, updates last_checked
    # Returns count

def check_all_subscriptions() -> dict:
    # Loops active subs, checks each, returns {checked, new_videos}
```

#### `scheduler.py`

```python
def init_scheduler(app):
    scheduler = BackgroundScheduler()
    interval = app.config.get("YT_CHECK_INTERVAL_HOURS", 6)
    scheduler.add_job(
        func=lambda: check_all_subscriptions(),
        trigger="interval",
        hours=interval,
        id="yt_sub_check",
        next_run_time=datetime.utcnow() + timedelta(hours=1)
    )
    scheduler.start()
    return scheduler
```

### Routes (`routes/youtube.py`)

| Endpoint | Method | Params | Response |
|---|---|---|---|
| `/yt/search` | GET | `q` | `[{video_id, title, channel, published_at, url}]` |
| `/yt/ingest` | POST | `video_url` | `{session_id, file_path, title}` |
| `/yt/subscribe` | POST | `channel_url` | `{id, channel_name, status}` |
| `/yt/unsubscribe` | POST | `sub_id` | `{status}` |
| `/yt/subscriptions` | GET | — | `[{id, channel_name, channel_url, last_checked, active}]` |
| `/yt/channel` | POST | `channel_url` | `{ingested_count, videos: [{title, session_id}]}` |

### Frontend Commands

Parsed client-side in `script.js`:

| Input | Endpoint |
|---|---|
| `/ytsearch <query>` | `GET /yt/search?q=...` |
| `/ytchannel <url>` | `POST /yt/channel` |
| `/ytsub <url>` | `POST /yt/subscribe` |
| `/ytunsub <id>` | `POST /yt/unsubscribe` |
| `/ytsubs` | `GET /yt/subscriptions` |

### Lazy Check

In `get_ai_response()`, before the AI call, fire a thread:

```python
if subscription_service.has_due_subscriptions():
    t = threading.Thread(target=subscription_service.check_due_subscriptions)
    t.start()
```

### Dependencies

```
youtube-transcript-api==1.0.2
yt-dlp>=2024.12.0
google-api-python-client>=2.150.0
APScheduler>=3.10.4
```

## De-bloat Prompt

```
You are a note-taking AI. Extract substance from a YouTube transcript.

RULES (strict):
1. Extract ONLY content present in the transcript. No additions, inferences, or summaries.
2. Remove: greetings, sponsor segments, channel plugs, CTAs, off-topic banter.
3. Preserve: ALL data points, arguments, examples, code, quotes, statistics, references, tools, people, timelines.
4. Organize by ## topic sections. Use natural topic shifts as boundaries.
5. Code blocks: verbatim with ``` fences.
6. Do NOT condense. Full substance without filler.
7. Do not guess. Omit or mark [unclear] if not in transcript.
8. No imaginary content. No elaborating. Pure extraction.

Format:
## Key Concepts
- ...

## Notes
[full de-bloated context]

## Takeaways
- ...

## References
- ...
```

## Edge Cases

| Case | Handling |
|---|---|
| No captions | All 3 fallbacks tried; user notified |
| Live stream | Try yt-dlp auto-captions; skip if none |
| Transcript > 100K chars | Chunk before LLM call, concatenate results |
| Rate limited | Backoff, retry next cycle; increment fail_count |
| 100+ new videos | Only ingest latest YT_MAX_PER_CHECK (default 5) |
| 3 consecutive failures | Mark channel inactive, notify user |
| Duplicate ingest | UNIQUE constraint on video_id |
| Obsidian path missing | Create on first write |
