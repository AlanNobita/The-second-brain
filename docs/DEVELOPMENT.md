# Development Guide

## Prerequisites

- Python 3.10+
- OpenRouter API key (or any OpenAI-compatible provider)

## Setup

```bash
# Virtual environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

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
# Run tests (pytest comes with uv)
uv run pytest

# Run a single category
uv run pytest tests/test_edge_cases.py -v
```

### Test Coverage (170 tests)

**Core (3):**

| Test | Route | Asserts |
|---|---|---|
| `test_health_endpoing` | `GET /api/health` | Returns `{"status": "ok"}` |
| `test_index_route` | `GET /` | Returns 200, contains "Second" |

**YouTube (30 unit tests, 1 E2E script):**

| Test file | Tests | What it covers |
|---|---|---|
| `test_youtube_db.py` | 10 | Subscription CRUD, dedup, reactivation, `mark_inactive`, ingested videos, idempotent add |
| `test_youtube_service.py` | 12 | URL parsing (all formats), transcript fetch, search, channel videos |
| `test_note_service.py` | 4 | De-bloat cleanup, substance preservation, markdown format, file save |
| `test_subscription_service.py` | 5 | Subscribe/unsub, due checking, auto-ingest pipeline |
| `test_youtube_routes.py` | 4 | HTTP 200/400 responses for all endpoints |
| `e2e_youtube_manual.py` | 6 | Full pipeline (skips if API keys missing) |

**Knowledge Graph (21 unit tests):**

| Test file | Tests | What it covers |
|---|---|---|
| `test_kg_db.py` | 7 | Entity/relationship CRUD, dedup, cascade delete, graph data, search |
| `test_kg_service.py` | 9 | Service-layer CRUD, triple extraction, dedup, entity lookup, relationship delete |
| `test_kg_routes.py` | 5 | HTTP 200/201/400/404, entity CRUD, relationship create, triple extraction |

**Chat / Hybrid Search / AI (39 unit tests):**

| Test file | Tests | What it covers |
|---|---|---|
| `test_chat_routes.py` | 5 | `/chat/send`, `/chat/history`, `/sessions`, `/session/<id>` DELETE, `/search` |
| `test_hybrid_search.py` | 14 | FTS / vector / hybrid merge, dedup, score normalization, ordering |
| `test_ai_source_attribution.py` | 10 | Source-aware RAG (YouTube vs chat classification, source list returned) |

**Reflections (11 unit tests):**

| Test file | Tests | What it covers |
|---|---|---|
| `test_reflection_db.py` | 5 | Save / get / list / exists for daily reflection rows |
| `test_reflection_routes.py` | 6 | `GET /api/reflection/today`, `POST /api/reflection/generate`, list |
| `test_proactive_service.py` | 4 | Proactive suggestions: recent cutoff, narrative generation, empty state |

**Edge Cases (61 unit tests, `test_edge_cases.py`):**

Ten categories of "what if a real user does this?" — empty / null / missing inputs, malformed JSON, 100 KB payloads, Unicode (Latin/CJK/emoji/Arabic), FTS5 special syntax (`*`, `AND`, `NEAR`, unclosed quotes, 1 000-char queries), concurrency, KG validation, YouTube edge cases, reflection edge cases, session lifecycle.

If this file fails, the production code is wrong — do **not** change the test.

**Senior None-Check Regression (6 unit tests, `test_senior_none_checks.py`):**

Pinpoints a half-dozen silent-killer `None` checks added across services (kg_service, ai_service, proactive_service, reflection_service, embedding_service). Each test names the production file and line range, so a regression points directly at the spot to re-fix.

**Run a single category:**

```bash
# Run all YouTube tests
pytest tests/test_youtube_db.py tests/test_youtube_service.py tests/test_note_service.py tests/test_subscription_service.py tests/test_youtube_routes.py -v

# Run only edge case + regression tests
pytest tests/test_edge_cases.py tests/test_senior_none_checks.py -v

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
│   ├── db.py           # Messages CRUD + FTS5
│   ├── youtube_db.py   # YouTube subscriptions
│   └── kg_db.py        # Knowledge Graph entities + relationships
├── services/   # Business logic — AI, embeddings, KG
│   ├── ai_service.py
│   ├── embedding_service.py
│   ├── youtube_service.py
│   ├── note_service.py
│   ├── subscription_service.py
│   ├── scheduler.py
│   └── kg_service.py   # KG CRUD + triple extraction
└── routes/     # HTTP layer — Flask blueprints
    ├── chat.py
    ├── health.py
    ├── youtube.py
    └── kg.py           # KG REST endpoints + /graph page
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

### Knowledge Graph Services

| Service | File | Role |
|---|---|---|
| **kg_db** | `app/models/kg_db.py` | SQLite tables: `entities`, `relationships`; CRUD, graph data query, search |
| **kg_service** | `app/services/kg_service.py` | Entity/relationship CRUD wrappers, triple extraction, text parsing |

### `models/db.py`

Raw SQLite data access:
- `get_connection()` — returns connection with `Row` factory
- `init_db()` — creates `messages` table if not exists
- `save_message()` — insert with session
- `get_message()` — history by session, ordered by time
- `get_sessions()` — distinct sessions with title and count
- `search_messages()` — `LIKE`-based keyword search
- `get_messages_by_ids()` — bulk fetch by primary keys

## Frontend (`frontend/` → `app/static/`)

Vite + React 18 + TypeScript SPA. The Vite build is configured to write directly into `../app/static/` with base path `/static/`, so Flask serves the bundle as its own static files — no separate static server, no CDN at runtime.

### Stack

- **Vite 6** — dev server + bundler
- **React 18** + **TypeScript 5**
- **Tailwind CSS v4** (via `@tailwindcss/vite`) with `oklch` design tokens
- **Motion** (formerly Framer Motion) for animations
- **Lucide React** for icons
- **React Flow** for the knowledge graph view
- **react-markdown** + **remark-gfm** for assistant-message markdown rendering

### Frontend module layout

```
frontend/src/
├── main.tsx                 # entry
├── App.tsx                  # top-level state, view switching, slash command dispatch
├── styles.css               # Tailwind v4 + design tokens (oklch)
├── lib/
│   ├── api.ts               # typed fetch wrapper, all backend calls
│   └── types.ts             # Message, Session, Source, YoutubeResult, Reflection, ...
└── components/
    ├── layout/              # AppShell, Sidebar, PulseDivider
    ├── chat/                # ChatSplash, ChatView, ChatInput, MessageBubble,
    │                        #   AIStatus, CommandChip, CommandResults
    ├── graph/               # KnowledgeGraph, GraphNode, NodeDetailsPanel, ParticleField
    └── ui/                  # RippleButton
```

### Key components

| Component | Role |
|---|---|
| `App.tsx` | Top-level state. Holds `view`, `sessionId`, `messages`, `commandResult`. `handleSend` intercepts `/`-prefixed input and dispatches to either a slash command or the regular chat endpoint. |
| `AppShell` | Sidebar + main content shell. |
| `ChatView` | Renders `messages` + the active `commandResult` block + the chat input. Auto-scrolls to bottom on new content. |
| `MessageBubble` | Renders a single message. User messages use `whitespace-pre-wrap`; assistant messages go through `ReactMarkdown` with `remark-gfm` and custom component overrides. The `processChildren` helper walks string children of paragraph/list/heading elements and splits capitalized tokens (3+ chars) into clickable nodes that call `onNodeClick(label)`. |
| `CommandResults` | Single component, discriminated-union switch on `result.kind`. Renders one of: `youtube-search`, `reflections`, `reflection-today`, `kg-list`, `kg-add`, `kg-help`. Each block has a header (icon + count + dismiss ×). The YouTube variant has a per-card Ingest button with idle / loading / success / error states. |
| `KnowledgeGraph` | React Flow view of the KG, opened via `/kg` slash command. |

### Slash command → result flow

```text
User types "/ytsearch python"
        │
        ▼
App.handleSend
        │
        ├── yt_search(q) → YoutubeResult[]
        │
        ▼
setCommandResult({ kind: "youtube-search", query, results })
        │
        ▼
ChatView re-renders → <CommandResultsWrapper result={...} />
        │
        ▼
CommandResults dispatches on kind → YouTube cards with Ingest buttons
        │
        ▼ (user clicks Ingest on one card)
api.ytIngest(videoUrl) → 200 OK → card flips to "Ingested" ✓
```

### Vite → Flask build

`frontend/vite.config.ts`:

```ts
base: "/static/",                              // emitted <script src="/static/...">
build: { outDir: "../app/static", emptyOutDir: true }
```

This means `cd frontend && npm run build` produces a deployable bundle that `python run.py` serves on port 5000. `emptyOutDir: true` removes stale `index-*.js`/`index-*.css` hashes on every build so the served HTML always matches the latest bundle.

### Dev workflow

```bash
# Terminal 1: backend
python run.py          # http://localhost:5000

# Terminal 2: frontend with HMR
cd frontend
npm run dev            # http://localhost:5173, proxies /api, /chat, /kg, /yt, /search to :5000
```

When you're ready to ship, `npm run build` writes the production bundle into `app/static/` and Flask picks it up immediately.

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
| Hybrid Search | FTS5 keyword + ChromaDB vector blend (50/50) | ✅ |
| Phase 5 | Knowledge Graph — entities, relationships, React Flow view (replaced legacy vis.js page) | ✅ |
| Frontend | Vanilla JS → Vite + React 18 + TypeScript SPA, builds to `app/static/` | ✅ |
| Markdown | Assistant replies via `react-markdown` + `remark-gfm` | ✅ |
| Slash commands | Card-based UI via `CommandResults.tsx` (discriminated `CommandResult` union) | ✅ |

## Upcoming Phases

### Phase 6: Proactive Agents

- Daily reflection summarizing day's notes
- Proactive suggestions during chat
- Background ChromaDB queries while typing
