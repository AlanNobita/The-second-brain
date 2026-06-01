# Second Brain — User Guide

## What Is This?

A persistent AI chat companion that remembers everything you tell it across sessions and helps you organize knowledge. Think of it as a second brain that never forgets.

### What makes it different from ChatGPT?

| | ChatGPT | Second Brain |
|---|---|---|
| Memory | Forgets after conversation ends | Remembers everything forever |
| Cross-session | Each chat is isolated | Surfaces relevant past conversations via RAG |
| YouTube | Can't ingest video transcripts | Fetches + summarizes YouTube transcripts |
| Knowledge Graph | No structured memory | Builds a visual concept map you can explore |
| Search | Basic | Hybrid (semantic + keyword) across all messages |

## Quick Start

```bash
# Setup
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .example.env .env
# Edit .env — add your OPENROUTER_API_KEY

# Run
python run.py
```

Open `http://localhost:5000`

## Chat Interface

The main screen has:
- **Left sidebar** — conversation history; click any session to reload it
- **Main area** — chat messages
- **Bottom input** — type messages or commands
- **Top search bar** — search across all past messages

### Normal Chat

Just type a message and press Enter. The AI responds with full context of your current conversation + relevant past knowledge.

### Chat Commands

Start a message with `/` to use special commands:

| Command | What it does |
|---|---|
| `/ytsearch <query>` | Search YouTube videos |
| `/ytchannel <url>` | Fetch & ingest latest videos from a channel |
| `/ytsub <url>` | Subscribe to a channel (auto-ingests new videos every 6h) |
| `/ytunsub <id>` | Unsubscribe (get the ID from `/ytsubs`) |
| `/ytsubs` | List your subscriptions |
| `/kg add <name>,<type>,<desc>` | Add a concept to the knowledge graph |
| `/kg relate src \| tgt \| rel` | Link two concepts with a relationship |
| `/kg extract <text>` | Parse free text into graph relationships |
| `/kg list` | List all concepts in the graph |

Examples:
- `/ytsearch python tutorial 2026`
- `/ytsub https://youtube.com/@sentdex`
- `/kg add Python,language,A programming language`
- `/kg relate Python | Flask | framework of`
- `/kg extract Python is a language. Flask is a framework for Python.`

## Knowledge Graph

Open `http://localhost:5000/graph` to see the interactive graph.

### How it works

Nodes = concepts (Python, Flask, databases, etc.)
Edges = relationships between them (is a, uses, related to, etc.)

### Using the graph

- **Click a node** → see its details and relationships in the right sidebar
- **Double-click a node** → expand to show only its 1-hop neighborhood
- **Search** (top bar) → type to find and focus on a concept
- **Zoom** (bottom-right buttons) → zoom in/out/reset
- **Theme toggle** (top-right) → cycle through 4 themes: Tokyo Night, Light, GitHub Dark, Obsidian
- **Delete** (sidebar) → remove a node and all its connections

### Adding to the graph

Three ways:

1. **Chat**: `/kg add Django,framework,Web framework` or `/kg relate Python | Django | powers`
2. **Bulk extract**: `/kg extract Python is a language. Flask is a framework written in Python.` — parses sentences into nodes and edges
3. **Manual**: Use the REST API (see `docs/API.md`)

## YouTube Ingestion

Search, fetch transcripts, and save YouTube videos as structured notes.

### How it works

1. Search YouTube or provide a video URL
2. Transcript is fetched (via `youtube-transcript-api`, with `yt-dlp` fallback)
3. OpenRouter de-bloats the transcript (removes greetings, sponsor plugs, filler)
4. Saved as an Obsidian-compatible `.md` file in `obsidian-ingest/`
5. Embedding stored in ChromaDB for semantic search

### Example

```
> /ytsearch rust vs go 2026
[Results appear with Ingest links]

> Click "Ingest" on a video
📥 Ingesting video...
✅ Video ingested!
```

The note is saved as `obsidian-ingest/2026-06-01-video-title.md`.

## Hybrid Search

The search bar at the top of the chat page searches ALL your past messages using two methods blended together:

- **Semantic** (ChromaDB) — understands meaning, not just keywords
- **Keyword** (FTS5) — finds exact word matches fast

Results show a badge indicating which mode matched (hybrid/keyword/semantic).

## Subscriptions

Subscribe to YouTube channels for automatic ingestion:

```
> /ytsub https://youtube.com/@sentdex
✅ Subscribed to Sentdex. Auto-ingesting every 6h.
```

The scheduler checks every 6 hours for new videos. A lazy check also runs whenever you send any chat message.

## Configuration

Edit `.env`:

| Variable | Required | Default | What it does |
|---|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | — | API key for AI responses |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | Alternative API endpoint |
| `YT_CHECK_INTERVAL_HOURS` | No | `6` | How often to check subscriptions |
| `YT_MAX_PER_CHECK` | No | `5` | Max videos to ingest per check |
| `OBSIDIAN_NOTES_PATH` | No | `./obsidian-ingest` | Where to save de-bloated transcripts |

## File Locations

| What | Where |
|---|---|
| Chat database | `second_brain.db` |
| Vector embeddings | `chromadb/` directory |
| YouTube channel tracking | `second_brain.db` (subscriptions table) |
| Knowledge Graph | `second_brain.db` (entities + relationships tables) |
| De-bloated transcripts | `obsidian-ingest/` |
| Environment config | `.env` |

## Tips

- The AI remembers **everything** you tell it. If you want it to forget something, delete the session from the sidebar.
- `/kg extract` works best with simple declarative sentences: _"Python is a language. Flask is written in Python. Flask uses Jinja2."_
- The graph theme persists only for the current tab session. Refresh resets to Tokyo Night.
- YouTube search uses `yt-dlp` (no API key) but is slower than the official YouTube API.
- If a video has no transcript, ingestion will fail with an error message.

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| "OpenRouter API key not configured" | Missing `.env` | Create `.env` with your key |
| "Transcript not available" | Video has no captions | Try a different video |
| Can't start app | Port 5000 in use | Kill the other process or change port in `run.py` |
| Graph shows empty | No entities added yet | Use `/kg add` or `/kg extract` first |
