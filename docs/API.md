# API Reference

Base URL: `http://localhost:5000`

The frontend is a Vite + React SPA built from `frontend/`. The production bundle is written into `app/static/` and served by Flask — no separate API gateway, no CDN. The frontend consumes every endpoint listed below via `frontend/src/lib/api.ts`.

## Health Check

```
GET /api/health
```

**Response** `200 OK`

```json
{
    "status": "ok"
}
```

## Index

```
GET /
```

**Response** `200 OK`

```
Hello from the Second brain
```

## Send Message

```
POST /chat/send
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | yes | User message text |
| `session_id` | string | no | Existing session UUID; omitted or null starts a new session |

**Response** `200 OK`

```json
{
    "session_id": "a1b2c3d4-...",
    "reply": "AI response text"
}
```

**Flow:**
1. Saves user message to SQLite + ChromaDB (embedding)
2. Fetches full conversation history for the session
3. Performs semantic search across all messages (excluding current session)
4. Builds RAG system prompt with top-3 relevant cross-session messages
5. Calls OpenRouter LLM with history + RAG context
6. Saves AI response to SQLite + ChromaDB
7. Returns response

## List Sessions

```
GET /sessions
```

**Response** `200 OK`

```json
[
    {
        "session_id": "a1b2c3d4-...",
        "created_at": "2026-06-01 12:00:00",
        "message_count": 5,
        "title": "First user message in session"
    }
]
```

Each entry is the first `user` message content used as a title.

## Get Session History

```
GET /chat/history?session_id=<uuid>
```

**Query Parameters**

| Parameter | Required | Description |
|---|---|---|
| `session_id` | yes | UUID of the session |

**Response** `200 OK`

```json
{
    "session_id": "a1b2c3d4-...",
    "messages": [
        {
            "id": 1,
            "session_id": "a1b2c3d4-...",
            "role": "user",
            "content": "Hello",
            "created_at": "2026-06-01 12:00:00"
        }
    ]
}
```

**Error** `400` if `session_id` is missing.

## Search Messages

```
GET /search?q=<query>
```

**Query Parameters**

| Parameter | Required | Description |
|---|---|---|
| `q` | yes | Search query text |

**Response** `200 OK`

```json
[
    {
        "id": 5,
        "session_id": "a1b2c3d4-...",
        "role": "assistant",
        "content": "Matched message content...",
        "created_at": "2026-06-01 12:00:00"
    }
]
```

Returns messages ranked by semantic similarity using ChromaDB vector search.

**Error** `200` with empty array `[]` if `q` is empty.

## YouTube Search

```
GET /yt/search?q=<query>
```

**Query Parameters**

| Parameter | Required | Description |
|---|---|---|
| `q` | yes | Search query |

**Response** `200 OK`

```json
[
    {
        "video_id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up",
        "channel": "Rick Astley",
        "channel_url": "https://www.youtube.com/@RickAstley",
        "published_at": "20091025",
        "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
    }
]
```

Powered by `yt-dlp` search (no API key required).

**Error** `400` if `q` is missing.

## YouTube Ingest

```
POST /yt/ingest
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `video_url` | string | yes | Full YouTube URL |

**Response** `200 OK`

```json
{
    "session_id": "yt_abc123def456",
    "file_path": "/path/to/obsidian-ingest/2026-06-01-video-title.md",
    "title": "Video Title"
}
```

Pipeline: fetch transcript → de-bloat via OpenRouter → save as Obsidian `.md` → embed into ChromaDB for RAG.

**Error** `500` with `{"error": "..."}` if transcript unavailable or de-bloat fails.

## YouTube Channel Ingest

```
POST /yt/channel
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `channel_url` | string | yes | YouTube channel URL or handle (e.g. `@sentdex`) |

**Response** `200 OK`

```json
{
    "ingested_count": 3,
    "videos": [{"title": "...", "video_id": "..."}]
}
```

Fetches latest 5 videos from the channel and ingests each one.

## YouTube Subscriptions

### Subscribe

```
POST /yt/subscribe
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `channel_url` | string | yes | YouTube channel URL or handle |

**Response** `200 OK`

```json
{
    "id": 1,
    "channel_name": "Sentdex",
    "channel_url": "https://www.youtube.com/@sentdex"
}
```

### Unsubscribe

```
POST /yt/unsubscribe
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `sub_id` | int | yes | Subscription ID from `/yt/subscriptions` |

**Response** `200 OK`

```json
{"status": "ok"}
```

### List Subscriptions

```
GET /yt/subscriptions
```

**Response** `200 OK`

```json
[
    {
        "id": 1,
        "channel_name": "Sentdex",
        "channel_url": "https://www.youtube.com/@sentdex",
        "last_checked": "2026-06-01 12:00:00"
    }
]
```

Subscriptions are checked every 6 hours (configurable via `YT_CHECK_INTERVAL_HOURS`). When a chat message is sent, a lazy background check also runs to catch new videos between scheduler intervals.

## Knowledge Graph

### 1. GET /kg/graph

Returns graph data as JSON (nodes + edges).

**Query Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `q` | no | Search query — returns all entities but focuses view on matching entity |

**Response** `200 OK`:

```json
{
    "nodes": [{"id": 1, "label": "Python", "title": "language", "description": "A programming language"}],
    "edges": [{"from": 1, "to": 2, "label": "related to", "value": 1.0}],
    "focus_id": 1
}
```

The `focus_id` field is only present when `?q=` is provided.

### 2. GET /graph

Returns the legacy standalone graph HTML page (vis.js). The primary way to view the graph in the React frontend is the `/kg` slash command, which opens a React Flow view of the same data. This legacy route is kept for backwards compatibility with bookmarks; new UI work happens in the React Flow component.

### 3. POST /kg/entity

Create a new entity.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Entity name (unique) |
| `type` | string | no | Entity type (default: "concept") |
| `description` | string | no | Description text |

**Response** `201 Created`:

```json
{"id": 1, "name": "Python", "type": "language", "description": "", "created_at": "2026-06-01 12:00:00"}
```

### 4. GET /kg/entity/\<id\>

Get a single entity by ID.

**Response** `200 OK` — same shape as POST response.
**Error** `404` if not found.

### 5. DELETE /kg/entity/\<id\>

Delete an entity and all its relationships (CASCADE).

**Response** `200 OK`:

```json
{"status": "ok"}
```

### 6. POST /kg/relation

Create a relationship between two entities.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `source_name` or `source` | string | yes | Source entity name |
| `target_name` or `target` | string | yes | Target entity name |
| `relationship_type` | string | no | Type (default: "related to") |
| `weight` | float | no | Edge weight (default: 1.0) |

Creates entities if they don't exist.

**Response** `201 Created`:

```json
{
    "id": 1, "source_entity_id": 1, "target_entity_id": 2,
    "relationship_type": "related to", "weight": 1.0,
    "created_at": "2026-06-01 12:00:00"
}
```

### 7. DELETE /kg/relation/\<id\>

Delete a relationship.

**Response** `200 OK`:

```json
{"status": "ok"}
```

### 8. POST /kg/extract

Extract triples from structured data or free text. Supports two input formats:

**Format A — Triples:**

```json
{"triples": [["Python", "is a", "language"], ["Flask", "is a", "framework"]]}
```

**Format B — Text (auto-parsed):**

```json
{"text": "Python is a language\nFlask | is a | framework\nTransformers relates to NLP"}
```

Text parsing supports:
- Pipe-separated: `A \| B \| C`
- Natural language: `A is a type of B`, `A relates to B`, `A is a B`

**Response** `201 Created`:

```json
{"entities_created": 3, "relationships_created": 2}
```

### 9. GET /kg/entities

List all entities.

**Response** `200 OK`:

```json
[
    {"id": 1, "name": "Python", "type": "language", "description": "", "created_at": "..."}
]
```

## Reflections

Daily AI-generated summaries of the user's chat history. Used by the `/reflections` and `/reflection-today` slash commands; the result renders as cards in `CommandResults`.

### 1. GET /api/reflections

List the most recent daily reflections (newest first).

**Response** `200 OK`:

```json
[
    {
        "date": "2026-06-02",
        "summary": "Today's session traced a compelling arc from high-level systems thinking...",
        "topics": ["healthcare policy and insurance", "Jetson Thor devkit", "Python tutorials"]
    }
]
```

### 2. GET /api/reflection/today

Fetch the reflection for today, if it has already been generated.

**Response** `200 OK` with a reflection object (same shape as the items in `/api/reflections`).

**Response** `200 OK` with `null` if no reflection has been generated for today yet.

### 3. POST /api/reflection/generate

Run the daily reflection job (sends the day's user messages to OpenRouter, extracts topics, writes a summary). Idempotent for the same day.

**Response** `201 Created` with the new reflection object on success.

**Error** `400 Bad Request` with `{"error": "No messages to reflect on today"}` if there are no user messages from today.

## Error Responses

All endpoints return standard HTTP status codes:

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Missing required parameter |
| 404 | Route not found |
| 500 | Server error (AI service failure, DB error) |
