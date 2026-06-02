# Roadmap

## Done

- [x] AI chat with session context + RAG
- [x] Persistent message storage (SQLite)
- [x] Semantic search with ChromaDB
- [x] Cross-session memory retrieval
- [x] YouTube ingestion (transcript, de-bloat, search)
- [x] YouTube channel subscriptions (auto-ingest, scheduler)
- [x] Obsidian note export
- [x] Hybrid search (FTS5 + ChromaDB 50/50 blend)
- [x] Knowledge Graph (entities, relationships, React Flow view, chat commands)
- [x] uv dependency management
- [x] Daily reflection — summarize what was learned each day
- [x] Proactive suggestions — AI notices connections during chat
- [x] Background periodic tasks (daily reflection, weekly cleanup/VACUUM)
- [x] Frontend migration: vanilla JS → Vite + React 18 + TypeScript SPA
- [x] Markdown rendering: AI replies via `react-markdown` + `remark-gfm` (headings, lists, **bold**, *italic*, `code`, tables, task lists, strikethrough)
- [x] Card-based slash command UI: `/ytsearch`, `/reflections`, `/reflection-today`, `/kg*` all render as typed `CommandResult` blocks via `CommandResults.tsx`
- [x] Per-card Ingest button on YouTube search results (idle → loading → success → error)
- [x] Vite build wired directly into `app/static/` (single `npm run build` → deployable bundle)

## Future Ideas

- [ ] Web page ingestion (fetch URL → de-bloat → embed)
- [ ] RSS/feed subscription (newsletters, blogs → auto-ingest)
- [ ] Browser bookmarklet to save pages to Second Brain
- [ ] Document upload (PDF, text, markdown drag-and-drop)
- [ ] Auto-extract KG entities from chat messages
- [ ] KG cluster detection (find communities of related concepts)
- [ ] KG import/export (share graph data)
- [ ] Obsidian plugin integration
- [ ] Mobile-friendly UI
- [ ] REST API for external apps to write data
- [ ] Multi-device sync
- [ ] Export/backup all data
- [ ] Search index rebuild tool
- [ ] Streaming responses (replace the current wait-for-full-reply UX)
- [ ] Code-block copy button + syntax highlighting (currently plain `<pre><code>`)
- [ ] User authentication + per-user sessions (currently single-user)

