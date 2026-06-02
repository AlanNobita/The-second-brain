# The Second Brain

Spend less time tracking knowledge — more time using it, thinking, and creating.

> AI-powered persistent memory system and cognitive assistant. Chat with an LLM that remembers everything and surfaces relevant past knowledge via semantic search.

## Quick Start

Requires `uv` (install via `pip install uv`) and Node 18+ for the frontend.

```bash
# Backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .example.env .env   # add your OPENROUTER_API_KEY

# Frontend (Vite + React, builds straight into app/static/)
cd frontend
npm install
npm run build           # writes ../app/static/index.html + assets/
cd ..

# Run
python run.py
```

Open `http://localhost:5000`. For dev with HMR: `cd frontend && npm run dev` (proxies API to `:5000`).

## Features

| Feature | Status |
|---|---|
| AI chat with session context | ✅ |
| Persistent message storage (SQLite) | ✅ |
| Semantic search with RAG (ChromaDB) | ✅ |
| Cross-session memory retrieval | ✅ |
| YouTube ingestion (transcript, search) | ✅ |
| YouTube channel subscriptions | ✅ |
| Obsidian note export | ✅ |
| Knowledge Graph (entities + relationships, React Flow view) | ✅ |
| Hybrid search (FTS5 + vector) | ✅ |
| Markdown rendering (`react-markdown` + GFM) | ✅ |
| Card-based slash command UI (`/ytsearch`, `/reflections`, `/kg*`) | ✅ |
| Daily reflection + proactive suggestions | ✅ |

## Documentation

| Guide | What it covers |
|---|---|
| [User Guide](docs/USER_GUIDE.md) | How to use everything — chat, commands, graph, YouTube |
| [API Reference](docs/API.md) | All HTTP endpoint documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, diagrams |
| [Development](docs/DEVELOPMENT.md) | Setup, testing, conventions |
| [Frontend README](frontend/README.md) | Vite/React/TS stack, build, components |
| [Changes Review (source attribution)](docs/CHANGES_REVIEW.md) | RAG source-aware classification & data recovery |
| [Changes Review (silent-killer sweep)](docs/CHANGES_REVIEW_2.md) | FTS5 triggers, status codes, race conditions, hardening |
