# API Reference

Base URL: `http://localhost:5000`

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

## Error Responses

All endpoints return standard HTTP status codes:

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Missing required parameter |
| 404 | Route not found |
| 500 | Server error (AI service failure, DB error) |
