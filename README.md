# The Second Brain

Spend less time tracking knowledge — more time using it, thinking, and creating.

> AI-powered persistent memory system and cognitive assistant. Chat with an LLM that remembers everything and surfaces relevant past knowledge via semantic search.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .example.env .env   # add your OPENROUTER_API_KEY
python run.py
```

Open `http://localhost:5000`

## Documentation

Full documentation is in [`docs/`](docs/README.md):

| File | Contents |
|---|---|
| [docs/README.md](docs/README.md) | Overview, features, tech stack |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, Mermaid diagrams |
| [docs/API.md](docs/API.md) | Complete HTTP endpoint reference |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, testing, conventions, deployment |
