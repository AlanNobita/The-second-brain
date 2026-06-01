# Knowledge Graph — Design Spec

## Overview

Interactive knowledge graph visualization for the Second Brain. Users explore entities and their relationships as a force-directed graph, search/filter by concept, extract triples from chat via LLM, and manage the graph through CRUD commands.

## Architecture

```
Chat (/yt, /kg extract) → Routes (kg.py) → Service (kg_service.py) → SQLite
                                                         ↓
                                              Graph page (/graph)
                                              vis.js force-directed
                                              Search · Sidebar · Zoom
```

### Backend

**New files:**
- `app/models/kg_db.py` — SQLite schema (entities, relationships tables)
- `app/services/kg_service.py` — CRUD + LLM extraction logic
- `app/routes/kg.py` — 7 endpoints, Blueprint registered in `create_app()`

**Models:**

```
entities
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  name        TEXT NOT NULL UNIQUE
  type        TEXT NOT NULL DEFAULT 'concept'
  description TEXT
  created_at  TEXT DEFAULT (datetime('now'))

relationships
  id                  INTEGER PRIMARY KEY AUTOINCREMENT
  source_entity_id    INTEGER NOT NULL REFERENCES entities(id)
  target_entity_id    INTEGER NOT NULL REFERENCES entities(id)
  relationship_type   TEXT NOT NULL
  weight              REAL DEFAULT 1.0
  created_at          TEXT DEFAULT (datetime('now'))
```

**API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/kg/graph` | All entities + relationships (vis.js JSON) |
| GET | `/kg/graph?q=python` | Center graph on matching entity |
| POST | `/kg/extract` | LLM extracts triples from text → stores |
| POST | `/kg/entity` | Create entity |
| POST | `/kg/relation` | Create relationship |
| DELETE | `/kg/entity/<id>` | Delete entity + its relationships |
| DELETE | `/kg/relation/<id>` | Delete relationship |

**LLM Extraction** (`POST /kg/extract`):
- On-demand only (not automatic)
- Accepts `{ "text": "..." }` or `{ "message_id": 123 }`
- Uses OpenRouter to extract triples `(entity → relationship → entity)`
- Creates entities + relationships in a transaction
- Returns created count

### Frontend

**New files:**
- `app/templates/graph.html` — Full-page graph layout
- `app/static/js/graph.js` — vis.js setup, interactions, API calls
- `app/static/css/graph.css` — Tokyo Night theme, animations

**Page: `/graph`**
- Full viewport layout (not embedded in chat)
- vis.js Network with force-directed layout
- Search bar to find and center on a concept
- Click node → sidebar opens with details + relationships
- Double-click node → expand 1-hop neighborhood
- Zoom controls (+/−/reset)

## UI Design (Approved Mockup v8)

### Layout
- Canvas (flex: 1) + Sidebar (260px) split
- Top bar: menu icon + "Knowledge Graph" title + search input + settings gear
- Zoom controls: bottom-right corner (stacked +/−/⟲)
- Stats: bottom-left corner ("7 concepts, 8 relationships")

### Color Themes
| Theme | Background | Surface | Border |
|-------|-----------|---------|--------|
| Tokyo Night (default) | `#1a1b26` | `#1e1f2e` | `#2a2b3d` |
| Light | `#ffffff` | `#f8f9fa` | `#e0e0e0` |
| GitHub Dark | `#0d1117` | `#161b22` | `#30363d` |
| Obsidian Light | `#faf8f5` | `#f5f0eb` | `#e0d5c7` |

### Node Colors (categorical)
| Type | Color | Glow |
|------|-------|------|
| Python | `#5a7fd4` | `rgba(90,127,212,0.4)` |
| Framework | `#8b5cf6` | `rgba(139,92,246,0.4)` |
| Database | `#6bae44` | `rgba(107,174,68,0.4)` |
| Service | `#d4872e` | `rgba(212,135,46,0.4)` |
| AI | `#d4506a` | `rgba(212,80,106,0.35)` |
| Frontend | `#4db8e8` | `rgba(77,184,232,0.35)` |
| Integration | `#c8943a` | `rgba(200,148,58,0.3)` |

### Connection Lines
- Thickness: 1.5px stroke
- Opacity: 0.35–0.50 range
- Blur glow: `feGaussianBlur stdDeviation="2.5"`
- Center-to-center routing (solid circles cover endpoints)
- Edge labels in pill-shaped badges

### Animations
| Element | Type | Curve | Duration |
|---------|------|-------|----------|
| Node entrance | scale(0.6→1) + fade + blur(4→0) | `cubic-bezier(0.16, 1, 0.3, 1)` | 500ms |
| Node hover | scale(1.3) + brightness(1.15) | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 400ms |
| Float idle | multi-keyframe translateY (0→-5→-3→-6→0) | `ease-in-out` | 5s loop |
| Sidebar enter | translateX(20→0) + fade | `cubic-bezier(0.16, 1, 0.3, 1)` | 400ms |
| Standard transitions | — | `cubic-bezier(0.4, 0, 0.2, 1)` | 200-300ms |
| Press feedback | scale(0.92) | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 150ms |

Stagger delays per node: 0.1s, 0.2s, 0.35s, 0.45s, 0.55s, 0.65s, 0.75s.

### Sidebar (Node Details)
- Node icon (colored square) + name + type
- Description text
- Relationships list (colored dots + relationship type + target)
- Action buttons: Focus (centers graph on node), Delete

### Accessibility
- Color is not the only indicator (text labels on all nodes)
- Keyboard navigation for search
- `prefers-reduced-motion` respected (disables entrance float animations)
- Focus states on interactive elements
- Touch targets ≥44px (zoom buttons, sidebar actions)

## Data Flow

```
User types "/kg extract" → POST /kg/extract
  → LLM returns [("Python", "built with", "Flask"), ...]
  → kg_service.create_entity() for each (upsert by name)
  → kg_service.create_relationship() for each
  → Returns { "entities_created": 3, "relationships_created": 4 }

User navigates to /graph → GET /kg/graph
  → kg_service.get_all() returns entities + relationships
  → vis.js renders force-directed layout

User clicks node → sidebar shows details
  → vis.js "click" event → highlight node + load sidebar
  → "Focus" button → vis.js.focus() on node

User searches "python" → GET /kg/graph?q=python
  → vis.js searches + focuses matching node
```

## Implementation Plan

See `docs/superpowers/plans/2026-06-01-knowledge-graph-plan.md`.

### Task Breakdown

1. **Database layer** — `app/models/kg_db.py` with entities + relationships tables, init function, 4 tests
2. **Service layer** — `app/services/kg_service.py` CRUD + LLM extraction, 6 tests
3. **Routes** — `app/routes/kg.py` with 7 endpoints, Blueprint registration, 4 tests
4. **Graph page** — `app/templates/graph.html` + `app/static/js/graph.js` + `app/static/css/graph.css`, vis.js integration
5. **Chat commands** — `/kg` routing in `app/static/script.js`, 4 commands (extract, add, relate, list)
6. **Polish** — Animation refinement, theme switching, keyboard shortcuts, empty states

## Commit

Commit the design document before proceeding.
