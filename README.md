# The Second Brain

Spend less time tracking knowledge — more time using it, thinking, and creating.

> AI-powered persistent memory system and cognitive assistant. Chat with an LLM that remembers everything and surfaces relevant past knowledge via semantic search.

## Quick Start

Requires `uv` (install via `pip install uv`).

```bash
python -m venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .example.env .env   # add your OPENROUTER_API_KEY
python run.py
```

Open `http://localhost:5000`

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
| Knowledge Graph (entities + relationships) | 🔄 Phase 5 |
| Hybrid search (FTS5 + vector) | 🔄 Phase 4+ |

## Documentation

Full documentation is in [`docs/`](docs/README.md):

| File | Contents |
|---|---|
| [docs/README.md](docs/README.md) | Overview, features, tech stack |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, Mermaid diagrams |
| [docs/API.md](docs/API.md) | Complete HTTP endpoint reference |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, testing, conventions, deployment |
