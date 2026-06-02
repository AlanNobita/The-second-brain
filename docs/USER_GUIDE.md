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
| Markdown | Renders it | Renders it (headings, lists, code, tables, **bold**, *italic*, etc.) |

## Quick Start

```bash
# Setup
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .example.env .env
# Edit .env — add your OPENROUTER_API_KEY

# Build the frontend (Vite → Flask static dir)
cd frontend && npm install && npm run build && cd ..

# Run
python run.py
```

Open `http://localhost:5000`

## Chat Interface

The main screen has:
- **Left sidebar** — conversation history; click any session to reload it
- **Main area** — chat messages (assistant replies render full markdown)
- **Bottom input** — type messages or slash commands
- **Top search bar** — search across all past messages

### Normal Chat

Just type a message and press Enter. The AI responds with full context of your current conversation + relevant past knowledge. **Bold**, *italic*, `code`, lists, tables, and other markdown in the AI's reply all render properly.

Clicking any capitalized word in an AI reply (e.g. "Python", "PostgreSQL") opens it as a node in the knowledge graph.

### Chat Commands

Start a message with `/` to use special commands. Every command result is rendered as a **card block** below your input — dismissable with the × button.

| Command | What it does |
|---|---|
| `/ytsearch <query>` | Search YouTube — result cards with an **Ingest** button on each |
| `/reflections` | List recent daily reflections (date + summary + topic chips) |
| `/reflection-today` | Get or generate today's reflection |
| `/subscriptions` | List YouTube channel subscriptions (active + inactive + reason) |
| `/kg add <name>,<type>,<desc>` | Add an entity to the knowledge graph — confirmation card |
| `/kg list` | List all knowledge graph entities as cards |
| `/kg` | Open the interactive knowledge graph view |
| `/kg help` (or unknown subcommand) | Show the list of `/kg` subcommands |

> Note: YouTube channel ingest (`POST /yt/channel`) is still managed through the REST API (see `docs/API.md`). Subscribe/unsubscribe and listing can be done from the chat via `/subscriptions`.

Examples:
- `/ytsearch python tutorial 2026` → click **Ingest** on the card you like
- `/kg add Python,language,A programming language`
- `/reflections` → browse past summaries

## YouTube Ingestion

Search, fetch transcripts, and save YouTube videos as structured notes.

### How it works

1. Run `/ytsearch <query>` — get a list of result cards
2. Click **Ingest** on a card — the button shows a spinner, then "Ingested"
3. Transcript is fetched (via `youtube-transcript-api`, with `yt-dlp` fallback)
4. OpenRouter de-bloats the transcript (removes greetings, sponsor plugs, filler)
5. Saved as an Obsidian-compatible `.md` file in `obsidian-ingest/`
6. Embedding stored in ChromaDB for semantic search

Ingested videos become available as RAG context for any future chat question.

The transcript save path is `obsidian-ingest/YYYY-MM-DD-video-title.md`.

## Knowledge Graph

Run `/kg` to open the interactive graph, or `/kg list` to see entities as cards.

### How it works

Nodes = concepts (Python, Flask, databases, etc.)
Edges = relationships between them (is a, uses, related to, etc.)

### Using the graph

- **Click a node** → see its details and relationships in the right sidebar
- **Double-click a node** → expand to show only its 1-hop neighborhood
- **Search** (top bar) → type to find and focus on a concept
- **Zoom** (bottom-right buttons) → zoom in/out/reset
- **Theme toggle** (top-right) → cycle through 4 themes
- **Delete** (sidebar) → remove a node and all its connections

### Adding to the graph

Three ways:

1. **Chat**: `/kg add Django,framework,Web framework`
2. **REST API**: `POST /kg/extract` with free text (see `docs/API.md`)
3. **From chat messages**: click any capitalized word in an AI reply

## Hybrid Search

The search bar at the top of the chat page searches ALL your past messages using two methods blended together:

- **Semantic** (ChromaDB) — understands meaning, not just keywords
- **Keyword** (FTS5) — finds exact word matches fast

Results show a badge indicating which mode matched (hybrid/keyword/semantic).

## Subscriptions

YouTube channel subscriptions (auto-ingest on a schedule) are managed through the REST API:

```
POST /yt/subscribe    {"channel_url": "https://youtube.com/@sentdex"}
GET  /yt/subscriptions
POST /yt/unsubscribe  {"sub_id": 1}
POST /yt/channel      {"channel_url": "..."}    # one-shot ingest of latest videos
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
| Built frontend | `app/static/` (output of `npm run build`) |
| Environment config | `.env` |

## Tips

- The AI remembers **everything** you tell it. If you want it to forget something, delete the session from the sidebar.
- The graph theme persists only for the current tab session. Refresh resets to Tokyo Night.
- YouTube search uses `yt-dlp` (no API key) but is slower than the official YouTube API.
- If a video has no transcript, ingestion will fail with an error message on the card.

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| "OpenRouter API key not configured" | Missing `.env` | Create `.env` with your key |
| "Transcript not available" | Video has no captions | Try a different video |
| Page loads but shows blank screen | Stale frontend build | `cd frontend && npm run build` |
| Can't start app | Port 5000 in use | Kill the other process or change port in `run.py` |
| Graph shows empty | No entities added yet | Use `/kg add` or `/kg list` first |
| AI replies show literal `**` asterisks | Very old browser cache | Hard-refresh (Ctrl+Shift+R) |
