# Second Brain

> An AI-powered persistent memory system and cognitive assistant. Transforms unstructured information into structured understanding over long periods of time.

## Purpose

Second Brain solves **information overload and fragmented knowledge**. Unlike standard chatbots or note-taking apps, it functions as a persistent AI learning companion that remembers context across sessions, surfaces semantically relevant past knowledge, and helps you think, learn, and synthesize information.

## Key Features

| Feature | Status |
|---|---|---|
| Session-based AI chat with context memory | ✅ |
| Persistent message storage (SQLite) | ✅ |
| Semantic search with RAG (ChromaDB) | ✅ |
| Cross-session memory retrieval | ✅ |
| Conversation sidebar & history | ✅ |
| YouTube ingestion (transcript, de-bloat, search) | ✅ |
| YouTube channel subscriptions (auto-ingest) | ✅ |
| Obsidian note export | ✅ |
| Knowledge Graph (concepts + relationships) | ❌ Phase 5 |
| Proactive agents & daily reflection | ❌ Phase 6 |
| Hybrid search (FTS5 + vector) | ❌ Phase 4+ |

## Tech Stack

| Layer | Current | Future |
|---|---|---|
| Backend | Python, Flask | FastAPI |
| Database | SQLite | PostgreSQL |
| Vector Storage | ChromaDB | ChromaDB (scaled) |
| AI Provider | OpenRouter API | OpenRouter + Local |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2) | — |
| Frontend | Vanilla HTML/CSS/JS | React / Next.js |

## Quick Start

```bash
# Clone & enter
cd the-second-brain

# Create virtual env
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .example.env .env
# Edit .env with your OPENROUTER_API_KEY and optional YOUTUBE_API_KEY

# Run
python run.py
```

Open `http://localhost:5000` in a browser.

## Project Status

Actively developed. Phases 0-4 complete plus YouTube ingestion pipeline. Phase 5 (Knowledge Graph) is the next milestone.

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, layering |
| [API.md](API.md) | All HTTP endpoint reference |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Setup, testing, conventions, deployment |
