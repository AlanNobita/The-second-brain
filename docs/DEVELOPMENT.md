# Development Guide

## Prerequisites

- Python 3.10+
- OpenRouter API key (or any OpenAI-compatible provider)

## Setup

```bash
# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Environment config
cp .example.env .env
```

### `.env` Configuration

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# YouTube (optional — without these, transcript ingest uses yt-dlp fallback)
YT_CHECK_INTERVAL_HOURS=6
YT_MAX_PER_CHECK=5
OBSIDIAN_NOTES_PATH=./obsidian-ingest
```

## Running

```bash
python run.py
```

Server starts at `http://localhost:5000` in debug mode.

First startup creates:
- `second_brain.db` — SQLite database
- `chroma_db/` — ChromaDB persistent storage

## Testing

```bash
# Install test dependency
pip install pytest

# Run tests
pytest
```

### Test Coverage

**Core:**

| Test | Route | Asserts |
|---|---|---|
| `test_health_endpoing` | `GET /api/health` | Returns `{"status": "ok"}` |
| `test_index_route` | `GET /` | Returns 200, contains "Second" |

**YouTube (31 unit tests, 1 E2E script):**

| Test file | Tests | What it covers |
|---|---|---|
| `test_youtube_db.py` | 9 | Subscription CRUD, dedup, reactivation, ingested videos |
| `test_youtube_service.py` | 12 | URL parsing (all formats), transcript fetch, search, channel videos |
| `test_note_service.py` | 4 | De-bloat cleanup, substance preservation, markdown format, file save |
| `test_subscription_service.py` | 5 | Subscribe/unsub, due checking, auto-ingest pipeline |
| `test_youtube_routes.py` | 4 | HTTP 200/400 responses for all endpoints |
| `e2e_youtube_manual.py` | 6 | Full pipeline (skips if API keys missing) |

```bash
# Run all YouTube tests
pytest tests/test_youtube_db.py tests/test_youtube_service.py tests/test_note_service.py tests/test_subscription_service.py tests/test_youtube_routes.py -v

# Manual E2E
python tests/e2e_youtube_manual.py
```

## Code Conventions

### Naming

- **Files**: snake_case (e.g., `ai_service.py`, `embedding_service.py`)
- **Functions**: snake_case (e.g., `get_ai_response`, `store_embedding`)
- **Classes**: PascalCase (e.g., `Config`)
- **Routes**: kebab-case paths (e.g., `/chat/send`, `/chat/history`)
- **Blueprint variables**: suffix `_bp` (e.g., `chat_bp`, `health_bp`)

### Module Structure

```
app/
├── models/     # Data access layer — raw SQL
├── services/   # Business logic — AI, embeddings
└── routes/     # HTTP layer — Flask blueprints
```

Key rules:
- **Models** never import from services or routes
- **Services** import from models and external libraries
- **Routes** import from services (thin controllers)
- All `__init__.py` files are empty (packages only)

### Imports

```python
# Standard library first
import sqlite3
import os

# Third-party
from flask import Blueprint, jsonify
from openai import OpenAI

# Internal
from ..models.db import save_message
from ..services.ai_service import get_ai_response
```

## Key Services

### `ai_service.py`

Orchestrates the full AI pipeline:
1. Saves user message with embedding
2. Fetches session history
3. Runs semantic RAG across all sessions
4. Builds prompt with cross-session context
5. Calls OpenRouter
6. Saves AI response with embedding

Model: `nvidia/nemotron-3-super-120b-a12b:free`

### `embedding_service.py`

Singleton service initialized at startup:
- Model: `SentenceTransformer("all-MiniLM-L6-v2")` (384-dim vectors)
- Vector DB: ChromaDB with `PersistentClient`
- Collection: `"messages"` with metadata `{session_id, role}`

### YouTube Services

| Service | File | Role |
|---|---|---|
| **youtube_service** | `app/services/youtube_service.py` | Transcript fetch (youtube-transcript-api → yt-dlp fallback), video ID extraction, search, channel videos |
| **note_service** | `app/services/note_service.py` | De-bloat transcript via OpenRouter (regex fallback), save as Obsidian `.md` |
| **subscription_service** | `app/services/subscription_service.py` | Channel subscribe/unsub/list, check due, auto-ingest pipeline |
| **scheduler** | `app/services/scheduler.py` | APScheduler in-process, 6-hour interval, atexit shutdown |
| **youtube_db** | `app/models/youtube_db.py` | SQLite tables: `subscriptions`, `ingested_videos` |

Transcript fetch fallback chain:
1. `youtube-transcript-api` (fast, no deps)
2. `yt-dlp` (downloads auto-subs, no API key needed)

YouTube search and channel listing use `yt-dlp` directly (no API key required for basic usage).

### `models/db.py`

Raw SQLite data access:
- `get_connection()` — returns connection with `Row` factory
- `init_db()` — creates `messages` table if not exists
- `save_message()` — insert with session
- `get_message()` — history by session, ordered by time
- `get_sessions()` — distinct sessions with title and count
- `search_messages()` — `LIKE`-based keyword search
- `get_messages_by_ids()` — bulk fetch by primary keys

## Frontend (`app/static/`)

Vanilla JS with no build step. CDN dependency: `marked.js` (not currently used in rendering, loaded for future use).

### Key Functions (`script.js`)

| Function | Trigger | Behavior |
|---|---|---|
| `sendMessage()` | Click / Enter | Intercepts `/` commands, else POST to `/chat/send` |
| `handleYTCommand()` | `/yt` prefix | Routes `/ytsearch`, `/ytchannel`, `/ytsub`, `/ytunsub`, `/ytsubs` to API |
| `loadSessions()` | Page load, after send | Fills sidebar from `/sessions` |
| `loadSession(id)` | Click session | GET `/chat/history`, renders messages |
| `performSearch(query)` | Type in search box | GET `/search`, renders results |
| `showTypingIndicator()` | Before fetch | Animated dots |
| `removeTypingIndicator()` | After response | Removes dots |
| `escapeHtml(text)` | Helper | XSS-safe text rendering |

## Logging & Debugging

- Flask runs in `debug=True` mode (auto-reload on changes)
- ChromaDB stores state in `chroma_db/` directory
- SQLite DB file is `second_brain.db` (in `.gitignore`)

## Production Considerations

Areas to address for production deployment:

| Area | Current State | Recommendation |
|---|---|---|
| **Connection pooling** | New connection per request | Use `flask.g` or connection pool |
| **Error handling** | Minimal | Add structured error responses and logging |
| **Rate limiting** | None | Add per-IP or per-session limits |
| **Authentication** | None | Add user auth + session isolation |
| **CORS** | Same-origin only | Configure for production domain |
| **Model selection** | Hardcoded free model | Make configurable |
| **Async** | Synchronous requests | Add background task queue (Celery) |

## Completed Phases

| Phase | What | Status |
|---|---|---|
| 0-4 | Foundation, CRUD, AI Chat, Semantic Memory | ✅ |
| YouTube | Transcript ingestion, de-bloat, subscriptions, scheduler | ✅ |

## Upcoming Phases

### Phase 5: Knowledge Graph

```sql
-- Proposed schema additions
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES concepts(id),
    target_id INTEGER REFERENCES concepts(id),
    relationship_type TEXT NOT NULL
);
```

### Phase 6: Proactive Agents

- Daily reflection summarizing day's notes
- Proactive suggestions during chat
- Background ChromaDB queries while typing
