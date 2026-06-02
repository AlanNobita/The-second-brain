# What Changed and Why — Second Brain Source Attribution

A review of the source-attribution feature, data recovery, and supporting fixes added to The Second Brain project.

---

## The Original Problem

The user asked a question like *"What did Danny K say about healthcare insurance?"* and the AI gave a great, transcript-grounded answer — but the user had **no way to know where that answer came from**. Worse, the AI was labeling transcript chunks the same way as old chat messages in its system prompt, so it wasn't even being told they were "knowledge" vs. "memory."

Three concrete bugs were lurking:

1. **Test suite was silently destroying the database** on every test run.
2. **171 of 175 ChromaDB vectors were orphans** (pointing to non-existent SQLite rows).
3. **RAG treated YouTube transcripts and chat history identically** when constructing the system prompt.

---

## Change 1: Source-Aware RAG in `app/services/ai_service.py`

### Before

Every retrieved chunk was labeled the same way in the system prompt:

```python
rag_content = "\n\n".join(
    f'[Previous conversation - {m["session_id"][:8]}...] {m["role"]}: {m["content"]}'
    for m in rag_messages[:3]
)

system_prompt = (
    "You are a Second Brain AI assistant. "
    "Here are relevant past messages from the user's history: \n\n"
    f"{rag_content}"
    "Use them for context when answering the current question."
)
```

The AI couldn't tell the difference between a chunk from a Sentdex YouTube video and a chunk from a chat we had three messages ago. It would treat them as the same kind of evidence.

### After

Each chunk is classified by source and labeled appropriately:

```python
if yt_chunks:
    yt_content = "\n\n".join(
        f'[Knowledge from YouTube video: {title}]\n{m["content"]}'
        for m in yt_chunks
    )
    system_prompt_parts.append(
        "You have access to transcripts from YouTube videos the user has "
        "previously watched or subscribed to. Treat these as authoritative "
        "knowledge the user has chosen to remember.\n\n"
        f"{yt_content}"
    )

if chat_chunks:
    chat_content = "\n\n".join(
        f'[Memory: past conversation - {sid[:8]}...] {m["role"]}: {m["content"]}'
        for m in chat_chunks
    )
    system_prompt_parts.append(
        "The following are excerpts from the user's past conversations "
        "with you. Use them for personal context and continuity.\n\n"
        f"{chat_content}"
    )
```

### Why It's Better — Concrete Example

**Query:** *"How does Danny K feel about Medicare for All?"*

| Source Type | Before | After |
|---|---|---|
| YouTube transcript | `[Previous conversation - yt_633c5...] assistant: [YouTube] How AI Agents Could Fix Healthcare Burnout (1/1)...` | `[Knowledge from YouTube video: How AI Agents Could Fix Healthcare Burnout] [YouTube] How AI Agents Could Fix Healthcare Burnout (1/1)...` |
| Old chat | `[Previous conversation - 73f3da2b...] user: What did he say about insurance?` | `[Memory: past conversation - 73f3da2b...] user: What did he say about insurance?` |

The AI now sees these as fundamentally different evidence: **knowledge** (authoritative, drawn from content the user subscribed to) vs. **memory** (recalled from prior conversations). It weights them differently when answering.

---

## Change 2: Source Attribution Returned to Client

### Before

`get_ai_response` returned `(ai_content, suggestion)` — no way to tell the user where the answer came from.

### After

Returns a 3-tuple `(ai_content, suggestion, sources)` where `sources` looks like:

```python
[
    {
        "type": "youtube",
        "title": "How AI Agents Could Fix Healthcare Burnout",
        "url": "https://youtube.com/watch?v=NRahVwYfp-Q",
        "session_id": "yt_633c5b31bb6e"
    },
    {
        "type": "youtube",
        "title": "Danny K - Outdacontrol",
        "url": "https://www.youtube.com/results?search_query=Danny+K+-+Outdacontrol",
        "session_id": "yt_e07c26e785b9"
    }
]
```

The fallback to a YouTube search URL is important: when the `ingested_videos` table doesn't have a row matching the `session_id` (e.g., the chunk came from the backfill with a new session_id), we still give the user a working link.

### Why It's Better

The user can now see *which videos* informed the AI's answer. If the AI gets something wrong, the user can click through and verify. If it cites something they don't remember, they can rewatch. It also signals **confidence** — when 2 YouTube sources are listed, the answer is well-grounded; when none are listed, it's a pure model response.

---

## Change 3: Source Pills in the UI

### Before

The chat bubble just showed the AI's text. No metadata, no sources.

### After (`app/static/js/chat.js` + `app/static/css/main.css`)

Below the AI's bubble, a row of clickable pills appears:

```
┌──────────────────────────────────────────────┐
│ Reinforcement learning (RL) for humanoid     │
│ robots like the Unitree G1 is a machine      │
│ learning method...                           │
└──────────────────────────────────────────────┘
SOURCES:  [▶ Reinforcement learning with    ]  [▶ Training a Unitree G1 to
          [  Unitree G1 humanoid — Dev w G1 ]     [  Walk w Reinforcement    ]
          [  P5 (youtube.com)              ]     [  Learning (youtube.com)  ]
          [                                ]     [                          ]
          └───────────────────────────────┘     └──────────────────────────┘
```

The pills are styled differently for YouTube (red accent with play icon) so they stand out from regular chat metadata.

### Why It's Better

- **Trust** — the user can audit the AI's claims.
- **Discoverability** — clicking a pill takes them to the source video.
- **Visual feedback** — the user knows immediately whether the answer came from "knowledge" or "the model just guessing."

---

## Change 4: Smart RAG Selection (YouTube Priority)

### Before

```python
rag_results = semantic_search(user_message, limit=3)
```

The AI got the top 3 closest vectors, regardless of source. In real-world usage, when the user asks a unique question, the top 3 are usually relevant. But in edge cases, the top 3 might be dominated by old chat history.

### After

```python
rag_results = semantic_search(user_message, limit=30)
# ... filter out in-session messages ...
# Boost YouTube chunks to the front if not already there
yt_in_top3 = [m for m in rag_messages[:3] if _classify_source(...) == "youtube"]
if yt_in_candidates and len(yt_in_top3) < 2:
    # swap chat chunks for YouTube chunks
```

### Why It's Better

When the user asks "Tell me about the Jetson Thor devkit":

- The top 3 by vector distance might include: a previous user query about Jetson, an AI response about Jetson, and a YouTube chunk about Jetson.
- That's 1 YouTube out of 3 → only 1 source attribution.
- The new logic ensures **at least 2 YouTube chunks** if available, so the user sees multiple sources and the AI has rich knowledge to draw on.

---

## Change 5: Database Recovery Scripts

Three scripts under `scripts/` that fix data-sync issues.

### `backfill_yt_messages.py`

Re-creates `yt_*` session message chunks from `obsidian-ingest/*.md` files. This is the source of truth on disk — the de-bloated markdown notes we already wrote.

### `clear_orphan_embeddings.py`

**This was the critical fix.** It compares ChromaDB vector IDs to SQLite message IDs and deletes any orphans.

```python
orphans = [id_ for id_ in chroma_ids if str(id_) not in db_ids]
collection.delete(ids=orphans)
# "ChromaDB vectors: 175, DB rows: 8, orphans: 171"
# "Deleted 171 orphan vectors"
```

### `reembed_yt_messages.py`

Finds SQLite messages without embeddings and stores them. Run after the orphan-cleaner.

### Why It's Better

Before these scripts existed, the only way to fix ChromaDB/SQLite drift was to manually nuke both and start over, losing everything. Now there's a 3-step recovery: **backfill → clear orphans → re-embed**. Idempotent and safe to re-run.

---

## Change 6: Test Suite Bug Fix (Critical)

### The Bug

`tests/test_hybrid_search.py` had this:

```python
@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    init_fts()
    conn = get_connection()
    conn.execute("DELETE FROM messages_fts")  # ← WIPES REAL DB
    conn.execute("DELETE FROM messages")      # ← WIPES REAL DB
    conn.commit()
    conn.close()
```

Every test run was silently deleting all messages from the real `second_brain.db`. That's why I kept losing my backfilled YouTube data.

### The Fix

```python
@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temp DB so tests don't pollute the real second_brain.db."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_hybrid.db"))
    init_db()
    init_fts()
```

### Why It's Better

Tests now run in complete isolation. Running `pytest tests/` 100 times no longer touches the real database. Also added the missing `search_messages_fts` import that was causing 2 pre-existing test failures.

### Concrete Example of the Damage

- After first backfill: 41 yt messages.
- After running test suite: 8 messages (everything not in the 2 most recent test sessions).
- Now: 50 yt messages, preserved across test runs.

---

## Change 7: Cleanup of Unused Files

Deleted `app/static/script.js` (17KB) and `app/static/style.css` (15KB) — these were left over from an older Tailwind-based frontend. The current frontend uses `app/static/js/chat.js` and `app/static/css/main.css` exclusively.

Added `graphify-out/` to `.gitignore` so the 1.1MB of graph visualization outputs don't get committed.

---

## Test Coverage

| Test File | Tests | What it Covers |
|---|---|---|
| `test_ai_source_attribution.py` | 10 | `_classify_source`, `_extract_yt_title`, regex pattern |
| `test_chat_routes.py` | 5 | `/chat/send` returns `sources`, `suggestion`, preserves `session_id` |
| `test_hybrid_search.py` (fixed) | 14 | Now uses temp DB, fixed missing import |

**Total: 103/103 passing** (was 88, +15 from new tests, with the 2 pre-existing failures also fixed).

---

## End-to-End Live Demo

**Request:**

```bash
curl -X POST http://localhost:5000/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message":"What is reinforcement learning for humanoid robots?"}'
```

**Response (truncated):**

```json
{
  "reply": "Reinforcement learning (RL) for humanoid robots like the Unitree G1 is a machine learning method where the robot learns a control policy—essentially the \"brain\" that dictates its movements—through trial and error in simulation...",
  "session_id": "abc-123",
  "sources": [
    {
      "type": "youtube",
      "title": "Reinforcement learning with Unitree G1 humanoid — Dev w G1 P5",
      "url": "https://www.youtube.com/results?search_query=..."
    },
    {
      "type": "youtube",
      "title": "Training a Unitree G1 to Walk w Reinforcement Learning",
      "url": "https://www.youtube.com/results?search_query=..."
    }
  ]
}
```

The AI is clearly using transcript content (specific details about Unitree G1, the "brain" metaphor, simulation training) and the UI now shows the user exactly which videos informed the answer.

---

## Summary of Impact

| Metric | Before | After |
|---|---|---|
| YouTube chunks usable in RAG | ~4 (orphans) | 50+ (clean, embedded) |
| Source attribution in API response | None | Up to 3 YouTube sources per reply |
| Test runs that touch real DB | 100% of suite | 0 |
| Test pass rate | 86/88 (2 pre-existing failures) | 103/103 |
| Distinct data-recovery scripts | 0 | 3 (backfill, clear, reembed) |

The biggest win is **trust and auditability** — the user can now see *why* the AI said what it said and click through to verify. The second-biggest win is fixing the test-suite bug, which was silently destroying hours of curated data on every `pytest` run.
