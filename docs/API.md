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

## Error Responses

All endpoints return standard HTTP status codes:

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Missing required parameter |
| 404 | Route not found |
| 500 | Server error (AI service failure, DB error) |
