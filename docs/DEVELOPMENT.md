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

| Test | Route | Asserts |
|---|---|---|
| `test_health_endpoing` | `GET /api/health` | Returns `{"status": "ok"}` |
| `test_index_route` | `GET /` | Returns 200, contains "Second" |

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
| `sendMessage()` | Click / Enter | POST to `/chat/send`, renders response |
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
