# Hybrid Search (FTS5 + Vector) — Design Spec

## Overview

Add SQLite FTS5 full-text search to complement existing ChromaDB vector search. Merge both into a single ranked result set using a normalized 50/50 score blend.

## Architecture

```
User types in search box
        │
        ▼
  GET /search?q=<query>&mode=hybrid
        │
        ▼
 hybrid_search.search(query, limit=20)
        │
        ├──► search_messages_fts(query, limit)
        │       └── messages_fts (FTS5 table)
        │
        └──► semantic_search(query, limit)
                └── ChromaDB (vector)
        │
        ▼
 Normalize scores → blend 50/50 → dedup → sort
        │
        ▼
  Return JSON [{id, session_id, role, content, created_at, _score, _source}]
```

## Components

### 1. Data Layer — `app/models/db.py`

- `init_fts()`: Create `messages_fts` FTS5 virtual table if not exists, backfill from `messages`, add AFTER INSERT trigger for auto-sync
- `search_messages_fts(query, limit)`: Return `[(msg_id, bm25_score)]` ranked by FTS5 relevance

### 2. Service — `app/services/hybrid_search.py` (new)

- `search(query, limit=20, mode="hybrid")`: Main entry point
- Supports 3 modes: `hybrid` (default), `semantic` (pure vector), `keyword` (pure FTS5)
- `_merge_ranked()`: Normalize BM25 + vector scores to [0,1], blend 50/50, dedup, sort desc

### 3. Route — `app/routes/chat.py`

- `/search?q=<query>&mode=hybrid|semantic|keyword`
- Default mode is `hybrid`
- Legacy `semantic` mode unchanged for backward compat

### 4. Frontend — `app/static/script.js`

- `performSearch()` shows `_source` badge per result (hybrid/keyword/semantic)

### 5. Frontend — `app/static/style.css`

- `.result-source` badge styling

### 6. Init — `app/__init__.py`

- Call `init_fts()` after `init_db()` / `init_youtube_db()`

## Score Normalization

- **BM25** (FTS5): score ≤ 0 where 0 = perfect match. Map using `2/(1+|score|)` to (0, 1].
- **Vector distance** (ChromaDB): range [0, ~2]. Map using `1 - (dist/max_dist)` to [0, 1].
- **Blend**: `final = 0.5 * fts_norm + 0.5 * vec_norm`
- If a message only appears in one result set, the other leg contributes 0.

## Edge Cases

- Empty query → empty array
- FTS5 special chars escaped before MATCH
- ChromaDB unavailable → fallback to pure FTS5
- Very short queries (< 3 chars): FTS5 may return nothing, vector still works

## Migration

- `init_fts()` creates FTS5 table + backfills existing messages
- INSERT trigger syncs future messages automatically
- No data loss

## Testing

- `tests/test_hybrid_search.py` — init, backfill, trigger, FTS search, hybrid merge, modes, route integration
