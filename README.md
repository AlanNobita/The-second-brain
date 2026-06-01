# The Second Brain

Spend less time tracking knowledge — more time using it, thinking, and creating.

> AI-powered persistent memory system and cognitive assistant. Chat with an LLM that remembers everything and surfaces relevant past knowledge via semantic search.

## Quick Start

Requires `uv` (install via `pip install uv`).

```bash
uv venv .venv && source .venv/bin/activate
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
| Knowledge Graph (entities + relationships) | ✅ |
| Hybrid search (FTS5 + vector) | ✅ |

## Documentation

## Documentation

| Guide | What it covers |
|---|---|
| [User Guide](docs/USER_GUIDE.md) | How to use everything — chat, commands, graph, YouTube |
| [API Reference](docs/API.md) | All HTTP endpoint documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, diagrams |
| [Development](docs/DEVELOPMENT.md) | Setup, testing, conventions |
