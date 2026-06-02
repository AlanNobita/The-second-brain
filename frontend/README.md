# Second Brain — Frontend

Vite + React 18 + TypeScript SPA that consumes the Flask backend's API. The production build is written directly into `app/static/` (configured in `vite.config.ts`) so Flask can serve it as a single bundle — no CDN, no separate static server.

## Quick start

```bash
# Install dependencies
npm install

# Run dev server (proxies /api, /chat, /sessions, etc. to http://localhost:5000)
npm run dev

# Build for production (outputs to ../app/static, base path /static/)
npm run build
```

The Flask backend must be running on `http://localhost:5000` for the dev proxy to work.

## Tech stack

- **Vite 6** — dev server + bundler
- **React 18** + **TypeScript 5**
- **Tailwind CSS v4** (via `@tailwindcss/vite`)
- **Motion** (formerly Framer Motion) for animations
- **Lucide React** for icons
- **React Flow** for the knowledge graph
- **react-markdown** + **remark-gfm** for markdown rendering (AI chat + slash command output)
- Plain `fetch` via `src/lib/api.ts` — no TanStack Query or other data layer

## Project structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx              # entry
    ├── App.tsx               # top-level state, view switching, slash command dispatch
    ├── styles.css            # Tailwind v4 + design tokens (oklch)
    ├── lib/
    │   ├── api.ts            # typed fetch wrapper
    │   └── types.ts          # backend response shapes
    └── components/
        ├── layout/
        │   ├── AppShell.tsx
        │   ├── Sidebar.tsx
        │   └── PulseDivider.tsx
        ├── chat/
        │   ├── ChatSplash.tsx
        │   ├── ChatView.tsx
        │   ├── ChatInput.tsx
        │   ├── MessageBubble.tsx       # renders assistant messages via react-markdown
        │   ├── AIStatus.tsx
        │   ├── CommandChip.tsx
        │   └── CommandResults.tsx      # card UI for /ytsearch, /reflections, /kg, etc.
        ├── graph/
        │   ├── KnowledgeGraph.tsx
        │   ├── GraphNode.tsx
        │   ├── NodeDetailsPanel.tsx
        │   └── ParticleField.tsx
        └── ui/
            └── RippleButton.tsx
```

## Component-to-route map

| Component | Flask endpoint |
|---|---|
| `Sidebar` chat list | `GET /sessions` |
| `Sidebar` search input | `GET /search?q=...` |
| `Sidebar` delete button | `DELETE /session/<id>` |
| `AIStatus` | `GET /api/health` |
| `ChatInput` | `POST /chat/send` |
| `ChatView` history | `GET /chat/history?session_id=...` |
| `MessageBubble` sources | rendered from `sources` field in `/chat/send` response |
| `MessageBubble` markdown | `react-markdown` + `remark-gfm` over `reply` field |
| `KnowledgeGraph` | `GET /kg/graph` |
| `KnowledgeGraph` create entity | `POST /kg/entity` |
| `CommandResults` `/ytsearch` | `GET /yt/search?q=...` + `POST /yt/ingest` per card |
| `CommandResults` `/reflections` | `GET /api/reflections` |
| `CommandResults` `/reflection-today` | `GET /api/reflection/today` |
| `CommandResults` `/kg list` | `GET /kg/entities` |
| `CommandResults` `/kg add` | `POST /kg/entity` |
| `CommandResults` `/kg help` | (local — no API) |

## Slash command rendering

Slash commands are intercepted in `App.tsx` `handleSend` and produce a typed `CommandResult` instead of a plain text message. `CommandResults.tsx` is a discriminated-union switch on `result.kind` that renders a card block:

| `kind` | Triggered by | Renders |
|---|---|---|
| `youtube-search` | `/ytsearch <q>` | Thumbnail cards with per-card Ingest button |
| `reflections` | `/reflections` | Date-stamped reflection cards with topic chips |
| `reflection-today` | `/reflection-today` | Single reflection card or empty state |
| `kg-list` | `/kg list` | Entity cards (name, type pill, description) |
| `kg-add` | `/kg add <name>[,type,desc]` | Confirmation card for the new entity |
| `kg-help` | unknown `/kg` subcommand | Reference list of `/kg` subcommands |

The block is dismissable (X button) and clears when the user starts a new chat or switches sessions.

## Markdown rendering

`MessageBubble.tsx` renders assistant messages through `ReactMarkdown` with `remark-gfm`. A `processChildren` helper walks string children of paragraph/list/heading elements and splits capitalized tokens (3+ chars) into clickable nodes that call `onNodeClick(label)` — the same "click a concept to open the graph" behavior the chat had before. Inline `**bold**`, `*italic*`, `` `code` ``, links, tables, task lists, blockquotes, and GitHub-flavored strikethrough all render correctly.

Custom component overrides in `MessageBubble.tsx` apply the existing design tokens (`text-sm`, `leading-relaxed`, `text-muted-foreground`, `bg-primary/15`, etc.) so the rendered output matches the rest of the chat surface.

## Build / deploy

`vite.config.ts` sets:

- `base: "/static/"` so the emitted `index.html` references `/static/assets/...` (Flask's default static URL)
- `build.outDir: "../app/static"` and `build.emptyOutDir: true` so the production build is written into Flask's static directory and stale bundles are removed

This means a single command — `npm run build` from the `frontend/` directory — produces a deployable bundle that `python run.py` will serve on port 5000. No CDN, no separate static server, no path-config drift.

## Design system

All colors use `oklch` and are defined in `src/styles.css`. To change the palette, edit the `:root` block — every Tailwind utility class (`bg-primary`, `text-foreground`, etc.) maps to a CSS custom property in `@theme inline`.

Animations (`pulse-glow`, `divider-pulse`, `float-sway`, `ripple-anim`, `fade-in-up`) are also in `styles.css` and applied via class names like `.pulse-dot`, `.float-sway`, etc.
