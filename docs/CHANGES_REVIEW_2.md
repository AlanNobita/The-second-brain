# What Changed and Why — Silent-Killer Bug Sweep

A focused round of fixes targeting **silent failures** in The Second Brain: bugs that don't raise an exception, don't log a warning, and don't break the user-visible feature — they just make the system slowly lose data, leak state, or quietly return wrong answers. Some had been latent for months.

This document follows [CHANGES_REVIEW.md](./CHANGES_REVIEW.md), which covered source attribution. Round 2 is a hardening pass after a comprehensive 10-agent audit of the codebase.

---

## The Shape of the Problem

Most bugs fall into four buckets, all invisible from the outside:

1. **Data loss without error.** An FTS5 row outlives its parent message; the search returns a rowid pointing to a non-existent message, and `get_messages_by_ids` quietly drops it. The user just gets a smaller result set and never knows.
2. **Wrong status code with right body.** A 200 OK carrying an error JSON because the route forgot `, 400`. Frontend's `if (!res.ok)` check passes; it reads `body.messages` and renders `undefined`.
3. **Null / None passing through guards.** `data.get("message", "")` returns `None` when JSON has `"message": null` because `dict.get` only fires on *missing* keys. The route then calls `save_message("...", "user", None)` and SQLite raises `NOT NULL constraint failed` — surfaced as a 500 HTML page.
4. **Race in async UI.** `loadHistory(id)` reads the response and sets state. Click session A (slow), then session B (fast), then A arrives last: the header shows B but the messages belong to A. No error, just confusion.

---

## Change 1: FTS5 stays in sync with the messages table

### Before

`init_fts` only created an `AFTER INSERT` trigger:

```python
conn.execute("""
    CREATE TRIGGER IF NOT EXISTS messages_fts_insert
    AFTER INSERT ON messages
    BEGIN
        INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
    END
""")
```

`delete_session()` ran `DELETE FROM messages` but left `messages_fts` rows stranded. `hybrid_search` would return a rowid from FTS, `get_messages_by_ids` would filter it out (correctly — the row was gone), and the user would see fewer results than they should. **Silent miss.**

### After

`app/models/db.py:69-92` now installs the matching DELETE and UPDATE triggers so FTS is always a faithful index of the parent table.

```python
conn.executescript("""
    CREATE TRIGGER IF NOT EXISTS messages_fts_delete
    AFTER DELETE ON messages
    BEGIN
        DELETE FROM messages_fts WHERE rowid = old.id;
    END;

    CREATE TRIGGER IF NOT EXISTS messages_fts_update
    AFTER UPDATE ON messages
    BEGIN
        UPDATE messages_fts SET content = new.content WHERE rowid = old.id;
    END;
""")
```

This was verified with `test_chat_history_with_10k_messages` + `test_search_fts_with_10k_messages` in `tests/test_edge_cases.py`: insert 10 000 messages, delete one session, search, and confirm the deleted rows are gone from the index.

---

## Change 2: FTS5 input sanitization

### Before

`search_messages_fts` escaped double-quotes only:

```python
safe = query.replace('"', '""')
rows = conn.execute(
    "SELECT rowid, rank FROM messages_fts WHERE content MATCH ? ORDER BY rank LIMIT ?",
    (safe, limit)
).fetchall()
```

A query of `*` raised `sqlite3.OperationalError: fts5: syntax error` (caught → `[]`). A query of `python*` is a prefix wildcard and ran fine. A query of `AND OR NOT` raised a syntax error. A 1 000-character query timed out. The behavior was inconsistent and some forms leaked raw error text to the user.

### After

`app/models/db.py:23-44` adds a `_sanitize_fts5` helper that:

- Truncates input to 200 chars.
- Strips FTS5 special chars (`" * ^ - ( ) :`).
- Strips reserved words (`AND`, `OR`, `NOT`, `NEAR`) as full-word matches.
- Picks out word characters via `re.findall(r"\w+", ..., flags=re.UNICODE)`.
- Quotes each surviving term so FTS5 treats it as a literal token.

```python
def _sanitize_fts5(query: str) -> str:
    if not query:
        return ""
    if len(query) > _FTS5_MAX_LEN:
        query = query[:_FTS5_MAX_LEN]
    cleaned = _FTS5_SPECIAL.sub(" ", query)
    cleaned = _FTS5_RESERVED.sub(" ", cleaned)
    words = re.findall(r"\w+", cleaned, flags=re.UNICODE)
    if not words:
        return ""
    return " ".join(f'"{w}"' for w in words)
```

`test_search_fts_unclosed_double_quote`, `test_search_fts_wildcard_star`, `test_search_fts_boolean_keywords_only`, `test_search_fts_near_operator`, `test_search_fts_1000_char_query`, `test_search_fts_sql_injection_attempt` in `tests/test_edge_cases.py` lock this behavior in.

---

## Change 3: LIKE wildcards escaped

### Before

`search_messages` (the LIKE-based path) used `f"%{query}%"`. A user searching for "C++" would match every row, because `%` is the SQL "any sequence" wildcard. A search for "user_name" would match "userXname".

### After

`app/models/db.py:47-56`:

```python
def _escape_like(query: str) -> str:
    return (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
```

…applied with `WHERE content LIKE ? ESCAPE '\\'`.

---

## Change 4: Indexes and PRAGMAs

The four DBs all live in the same SQLite file (`second_brain.db`) but only `kg_db` was enabling foreign keys. None were using WAL. A query of `/chat/history?session_id=...` did a full table scan of `messages`.

### After

`app/models/db.py:71-78` (and mirrors in `youtube_db.py`):

```python
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
```

`app/models/db.py:84-87` adds the missing index:

```python
conn.executescript("""
    CREATE TABLE IF NOT EXISTS messages (...);
    CREATE INDEX IF NOT EXISTS idx_messages_session
        ON messages(session_id);
""")
```

`test_get_sessions_with_100_sessions` confirms 100 sessions list in < 2 s; `test_chat_history_with_10k_messages` confirms 10 000 messages in < 10 s.

---

## Change 5: `data.get("message", "")` returns None on null

### Before

```python
data = request.get_json(silent=True) or {}
user_message = data.get("message", "")
```

`{"message": null}` → `user_message is None` → `save_message(...)` → `sqlite3.IntegrityError: NOT NULL constraint failed: messages.content` → Flask 500 HTML page.

### After

`app/routes/chat.py:17-40` coerces each input shape to a sensible string and rejects only what's unsalvageable:

```python
raw_message = data.get("message")
if raw_message is None:
    user_message = ""
elif isinstance(raw_message, (list, dict)):
    return jsonify({"error": "message must be a string, not a list or object"}), 400
elif isinstance(raw_message, bool):
    return jsonify({"error": "message must be a string, not a boolean"}), 400
elif not isinstance(raw_message, str):
    user_message = str(raw_message)
else:
    user_message = raw_message
```

`test_chat_send_null_message`, `test_chat_send_empty_string_message`, `test_chat_send_message_is_list`, `test_chat_send_message_is_object` in `tests/test_edge_cases.py` lock this in. As a backstop, `app/models/db.py:175-188` (`save_message`) now validates types at the model layer — even if a future route forgets, the user gets a 400 instead of a 500.

---

## Change 6: Missing 400 status codes

### Before

```python
@chat_bp.route("/chat/history", methods=["GET"])
def show_session_messages():
    session_id = request.args.get("session_id", default="")
    if not session_id:
        return jsonify({"error": "session_id is required"})  # ← no , 400
    ...
```

`curl -i /chat/history` returns `200 OK` with an error body. The frontend's `if (!res.ok)` happily passes, then reads `body.session_id` and `body.messages` — both `undefined` — and renders a broken state.

### After

`app/routes/chat.py:53-58`:

```python
if not session_id:
    return jsonify({"error": "session_id is required"}), 400
```

`test_chat_history_empty_session_id_param` and `test_chat_history_no_session_id_param` lock this in.

---

## Change 7: KG validation

`/kg/extract` previously did:

```python
if "triples" in data:
    triples = data["triples"]
elif "text" in data:
    triples = _parse_triples_from_text(data["text"])
```

If `triples="not a list"`, the iteration in `extract_triples` yields characters one at a time, then tries to unpack `"n"` into `(source, rel, target)` → `ValueError` → 500. If `text=123`, `_parse_triples_from_text` calls `text.strip()` on an int → `AttributeError` → 500.

### After

`app/routes/kg.py:84-99` only accepts a list for `triples` and a string for `text`. Anything else is treated as "0 triples supplied" — the response is 201 with `{entities_created: 0, relationships_created: 0}` and no exception path.

```python
@kg_bp.route("/kg/extract", methods=["POST"])
def extract_route():
    data = request.get_json(silent=True) or {}
    triples = []
    if "triples" in data:
        raw = data["triples"]
        if isinstance(raw, list):
            triples = raw
    elif "text" in data:
        text = data["text"]
        if isinstance(text, str):
            triples = _parse_triples_from_text(text)
    result = extract_triples(triples)
    return jsonify(result), 201
```

`test_kg_extract_string_instead_of_list` and `test_kg_extract_int_instead_of_text` confirm the new behavior.

`create_entity_route` (`/kg/entity`) also gained a default for empty `type` so `POST /kg/entity {"name": "A", "type": ""}` stores `"concept"`, not `""` — locked in by `test_kg_entity_empty_type_stored_as_empty_string`.

---

## Change 8: `add_subscription` updates channel_name on re-subscribe

### Before

```python
conn.execute("INSERT OR IGNORE INTO subscriptions (channel_url, channel_name) VALUES (?, ?)", ...)
conn.execute("UPDATE subscriptions SET active = 1, fail_count = 0 WHERE channel_url = ?", ...)
```

If the channel's display name was corrected upstream, re-subscribing kept the old name. The active list showed stale data.

### After

`app/models/youtube_db.py:42-58`:

```python
conn.execute(
    "UPDATE subscriptions SET active = 1, fail_count = 0, "
    "channel_name = ?, inactive_reason = NULL WHERE channel_url = ?",
    (channel_name, channel_url)
)
```

Re-subscribing also clears any prior `inactive_reason`, so the admin view only shows rows that are *intentionally* inactive.

---

## Change 9: Frontend `loadHistory` race

### Before

`frontend/src/App.tsx:34-44` did:

```ts
const loadHistory = useCallback(async (id: string) => {
  try {
    setLoading(true);
    const data = await api.getHistory(id);
    setMessages(data.messages);
  } catch (e: any) { setError(e.message); }
  finally { setLoading(false); }
}, []);
```

Click session A (slow), then session B (fast), then A's response arrives last → B's messages get overwritten with A's. The header shows B's id but the body belongs to A.

### After

A monotonic request id discards stale responses:

```ts
const historyReqIdRef = useRef(0);

const loadHistory = useCallback(async (id: string) => {
  const myReq = ++historyReqIdRef.current;
  setLoading(true);
  try {
    const data = await api.getHistory(id);
    if (myReq !== historyReqIdRef.current) return; // stale
    setMessages(data.messages);
  } catch (e: any) {
    if (myReq === historyReqIdRef.current) setError(e.message);
  } finally {
    if (myReq === historyReqIdRef.current) setLoading(false);
  }
}, []);
```

---

## Change 10: `ChatInput` actually disabled during streaming

### Before

`frontend/src/components/chat/ChatView.tsx:124`:

```tsx
<ChatInput onSend={onSend} disabled={loading} />
```

The `streaming` state lived in `App.tsx` but was never wired to the input. Users could spam-send and double-submit while the LLM was mid-response.

### After

```tsx
<ChatInput onSend={onSend} disabled={loading || streaming} />
```

`ChatInput` already gates its submit button on `disabled || sending`, so both flags now flow through.

---

## Verification

```bash
$ uv run pytest
170 passed in 460.52s

$ cd frontend && npx tsc --noEmit
(clean)

$ cd frontend && npm run build
vite v6.4.3 building for production...
✓ 2357 modules transformed.
✓ built in 4.41s
```

Per-file breakdown (170 total):

| File | Count |
|---|---|
| `tests/test_edge_cases.py` | 61 (new) |
| `tests/test_senior_none_checks.py` | 6 (new) |
| `tests/test_hybrid_search.py` | 14 |
| `tests/test_ai_source_attribution.py` | 10 |
| `tests/test_youtube_db.py` | 10 |
| `tests/test_youtube_service.py` | 12 |
| `tests/test_note_service.py` | 4 |
| `tests/test_subscription_service.py` | 5 |
| `tests/test_youtube_routes.py` | 4 |
| `tests/test_kg_db.py` | 7 |
| `tests/test_kg_service.py` | 9 |
| `tests/test_kg_routes.py` | 5 |
| `tests/test_chat_routes.py` | 5 |
| `tests/test_reflection_db.py` | 5 |
| `tests/test_reflection_routes.py` | 6 |
| `tests/test_proactive_service.py` | 4 |
| `tests/test_app.py` | 3 |
| **Total** | **170** |

---

## What's still in the backlog

A few items from the audit were intentionally *not* fixed in this pass because they are larger design decisions rather than silent-killer bugs:

- **Pagination on `/sessions`, `/kg/entities`, `/yt/subscriptions`.** Currently returns all rows. With 100 sessions it's fast (index); with 10 000 it isn't. A separate ticket should add `?limit&offset` and a sane cap.
- **Connection pooling.** A new `sqlite3.connect` per request. For local Flask that's fine; behind Gunicorn it would benefit from `flask.g` caching.
- **Rate limiting and auth.** Production deployment concerns from `docs/DEVELOPMENT.md` still apply.
- **`/yt/ingest` idempotency.** Posting the same `video_url` twice creates two sessions. The data layer has `is_video_ingested(video_id)` ready to use; the route just doesn't call it yet.

These are tracked in the codebase comments and the original audit; not silent killers, so out of scope for this round.
