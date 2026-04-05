# EgoVault Frontend — Design Spec

**Date:** 2026-03-28
**Status:** Approved — pending implementation plan
**Scope:** `frontend/` only — prerequisite: `api/` implemented and running
**Spec API:** `docs/superpowers/specs/2026-03-27-api-design.md`

---

## Concept

Single-screen "sci-fi control room" interface. No navigation, no separate pages — everything happens on one screen. The app **is** the pipeline. The user permanently sees the state of their knowledge factory.

Complement to MCP (LLM clients) and Obsidian (note reading/editing): EgoVault frontend covers manual ingestion and monitoring. No duplication.

**Roadmap:**
- **Now:** Next.js dev server → browser (`localhost:3000`), Canvas 2D, PC-first
- **Later:** Tauri wrapper (zero frontend code change), tablet scaling
- **Future:** Chat becomes the main view when the LLM is ready

---

## Key decisions

### Single-page factory floor

No Next.js router used as main navigation. The `/` page is the only screen. Drawers and tooltips give access to details without leaving the view.

### React + Canvas 2D for the factory

Machines, pipes, and transit animations are rendered on a `<canvas>`. The React DOM manages UI layers on top (tooltips, drawers, status bar, drop zone).

Reason: pixel-perfect positioning of machines, smooth animations of objects in transit, pixel art sprite rendering — impossible to do cleanly in DOM.

### Royalty-free pixel art sprites

32×32 or 16×16 assets, CC0 as priority (OpenGameArt.org). Paid itch.io pack ($2-3) as fallback if CC0 rendering is insufficient. Final decision at implementation.

Identified sources:
- CC0 priority: https://opengameart.org/content/190-pixel-art-assets-sci-fi-forest
- Free permissive: https://zofiab.itch.io/sci-fi-asset-pack-free
- Paid (backup): factory pack Blood_seller + spaceship tileset winlu (itch.io)

### shadcn/ui + Tailwind for UI layers

Side drawer, tooltips, status bar, drop zone, buttons — everything above the Canvas uses shadcn/ui + Tailwind. Consistency with the Next.js ecosystem, no fragile external dependency.

### SWR for job polling

Conditional `refreshInterval` — stops when all jobs are in a terminal state.

### PC-first, Canvas scaling for tablet

Target viewport: 1280px+ (1080p / 1440p). On tablet: CSS `transform: scale()` on the Canvas to adapt proportionally. No mobile — the pixel art interface does not make sense on 375px.

---

## Visual palette

Inspired by the spaceship/sci-fi top-down style (reference: spaceship tileset winlu, factory asset Blood_seller).

| Role | Color | Usage |
|---|---|---|
| Floor / background | `#545d70` | Pixel art tiles |
| Walls / borders | `#2d3142` | Screen edges |
| Machine background | `#2d3142` | Machine bodies |
| Active machine | `#4dd9e8` (cyan) | Border + glow + lights |
| Completed machine | `#68d391` (green) | Border + lights |
| Warning machine | `#e8943a` (orange) | Border + pulse |
| Error machine | `#fc6b6b` (red) | Border + alert |
| Drop zone | `#e8943a` | Hazard stripes |
| Note accent | `#b39ddb` (purple) | "Write a note" button |
| Main text | `#a0b4cc` | Labels, stats |
| Dim text | `#4a5568` | Inactive, secondary |

---

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  [top wall — cyan ceiling lights]   EGOVAULT · local     │
├──┬──────────────────────────────────────────────────┬───┤
│  │                                                  │   │
│  │   [DROP ZONE]       [PIPELINE CANVAS]  [STATS]   │   │
│  │   orange hazard     machines + pipes   mural     │   │
│  │   ▶ YouTube         connected, animated vault    │   │
│  │   🎙 Audio                              API/Ollama│   │
│  │   📄 PDF                                🔍 search │   │
│  │   ✏️ Note                                💬 chat  │   │
│  │                                                  │   │
├──┴──────────────────────────────────────────────────┴───┤
│  [STATUS BAR] active jobs · API · Ollama · version       │
└─────────────────────────────────────────────────────────┘
```

- **Walls** on all 4 edges: dark (#2d3142), ceiling lights on the top wall
- **Drop zone**: left, orange hazard stripes, source buttons
- **Pipeline Canvas**: center + right, occupies ~70% of the surface
- **Stats panel**: right wall mural, integrated into the scene (not a floating widget)
- **Status bar**: bottom, React DOM, always visible

---

## Pipeline — graph structure

The pipeline is not linear. It branches based on the ingested source. All paths are permanently visible — inactive ones are dim, active ones light up.

```
DROP ZONE
│
├── YouTube ──→ [fetch_subtitles] ──→ ─────────────────┐
│                    ↓ (fallback if no subtitles)        │
│              [extract_audio] ──────────────────────┐  │
│                                                    ▼  ▼
├── Audio ────→ [extract_audio] ──────────────→ [transcribe]
│                                                    │
└── PDF ──────→ [extract_pdf] ───────────────────────┤
                                                     │
                                              [chunk]
                                                 │
                                           [embed] ──→ [summarize] ─┐
                                                 │                   ▼
                                                 └──────────→ [create_note]
                                                                     │
                                                            [finalize_source]
```

Each node = a machine on the Canvas. Each edge = a pipe.

---

## Machines — states and behavior

### 3 visual states

| State | Visual | Trigger |
|---|---|---|
| `off` | Dark body, lights off, dim border | No job on this step |
| `active` | Cyan glow, blinking lights, internal sprite animation | Job in progress on this step |
| `done` | Green border, fixed green lights | Step completed for the current job |
| `warn` | Orange pulse | Step waiting / throttled (e.g. Ollama busy) |
| `error` | Red border, red lights | Step in error |

### Interaction

- **Hover** → lightweight DOM tooltip: step name, current job (source title), elapsed duration, % if available
- **Click** → side drawer (shadcn Sheet) from the right: history of the N last runs on this step, average duration, recent errors, logs

### Transit animations

When a job moves from one machine to the next:
- An object (source icon — ▶ / 🎙 / 📄) enters the pipe with a **suction** effect (accelerates, scales down, disappears into the pipe)
- The object **emerges** from the other side of the next machine with a **pop/bounce**
- If multiple jobs run in parallel: multiple objects travel simultaneously on the graph

Implementation: SVG `animateMotion` or Canvas `requestAnimationFrame` depending on performance.

---

## Drop zone

Positioned on the left, delimited by orange hazard stripes (warehouse style).

```
⚠ INGESTION
┌──────────────────┐
│ ▶  YouTube URL   │  → text input (URL paste/type)
│ 🎙  Audio/Video  │  → file picker (audio/*, .mp4)
│ 📄  PDF          │  → file picker (.pdf)
│ ─────────────── │
│ ✏️  Write note   │  → drawer with simple Markdown editor
└──────────────────┘
```

**Behavior on submit:**
1. Button → "Sending..." spinner
2. POST `/ingest/*` → `job_id` received → button → "Processing..."
3. The corresponding machine lights up on the Canvas
4. `mutate()` SWR for immediate refresh

**Drag & drop:** audio and PDF files accepted by dragging onto the drop zone.

---

## Stats panel mural

Integrated into the scene on the right (terminal mural style from the tileset). React DOM on top of Canvas.

```
[ SYS STATUS ]
Notes     47
Sources   12
Active jobs  2
API       ● ONLINE
Ollama    ● ONLINE
─────────────
QUICK ACCESS
🔍 Search
💬 Chat — coming soon
```

Click "Search" → vector search drawer (input + results).
Chat: label visible but disabled — "Available soon".

---

## Status bar

Fixed strip at the bottom, React DOM. Always visible.

```
● podcast-ep43.mp3 — transcription in progress    ✓ video-econ.mp4 · 3min    [API ●] [Ollama ●] [local]
```

- Active jobs listed with blinking dot
- Recently completed jobs (last 5min) in grey
- API + Ollama: green/red dots
- Click on a job → job drawer (logs, duration, error if applicable)

---

## Detailed monitoring — Drawer

Accessible from:
- Click on a machine (drawer filtered on that step)
- Click on a job in the status bar (drawer filtered on that job)

Contents:
- History of the 20 last runs (source title, duration, status)
- Average duration per step
- Recent errors with message
- Benchmark scores if available (`/benchmark/results`)

---

## File structure

```
frontend/
├── app/
│   ├── layout.tsx              ← body + StatusBar, no nav
│   └── page.tsx                ← FactoryCanvas + overlays
├── components/
│   ├── factory/
│   │   ├── FactoryCanvas.tsx   ← <canvas> + render loop
│   │   ├── Pipeline.ts         ← machine graph + positions
│   │   ├── Machine.ts          ← sprite drawing + state
│   │   ├── Pipe.ts             ← pipe drawing + transit animation
│   │   └── TravelObject.ts     ← animated object on pipes
│   ├── overlays/
│   │   ├── DropZone.tsx        ← DOM drop zone
│   │   ├── StatsPanel.tsx      ← mural stats panel
│   │   ├── MachineTooltip.tsx  ← machine hover tooltip
│   │   ├── MachineDrawer.tsx   ← machine detail drawer
│   │   ├── JobDrawer.tsx       ← job detail drawer
│   │   └── SearchDrawer.tsx    ← vector search drawer
│   ├── ui/                     ← shadcn/ui components (copied)
│   └── StatusBar.tsx           ← bottom DOM strip
├── lib/
│   ├── api.ts                  ← typed fetch wrappers
│   ├── sprites.ts              ← sprite sheet loading + cache
│   └── hooks/
│       ├── useJobs.ts          ← SWR polling active jobs
│       ├── useJob.ts           ← SWR polling individual job
│       └── useSearch.ts        ← search on submit
├── assets/
│   └── sprites/                ← pixel art sprite sheets (PNG)
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

---

## FactoryCanvas component

Fullscreen canvas with `requestAnimationFrame` render loop.

Responsibilities:
- Draw the floor (tiled from sprite sheet)
- Draw machines according to their current state
- Draw pipes (active / inactive)
- Animate objects in transit
- Handle hover (→ position for DOM tooltip) and click (→ open drawer)

The canvas listens to `mousemove` and `click`. Tooltips and drawers are React DOM positioned absolutely on top.

---

## API Client

`lib/api.ts` — typed wrappers, base URL configurable via `NEXT_PUBLIC_API_URL`.

Endpoints used in this frontend:
- `POST /ingest/youtube`, `/ingest/audio`, `/ingest/pdf`
- `GET /jobs`, `GET /jobs/{id}`
- `GET /health` (API + Ollama status)
- `POST /search`
- `GET /benchmark/results` (monitoring drawer)

---

## Configuration

`.env.local` (gitignored):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

CORS on FastAPI side: `origins: ["http://localhost:3000"]`.
No Next.js proxy — direct calls to FastAPI (compatible with future Tauri).

---

## Tests

```
tests/frontend/
├── factory/
│   ├── Pipeline.test.ts        ← graph structure, machine positions
│   └── TravelObject.test.ts    ← trajectory calculation
├── components/
│   ├── DropZone.test.tsx       ← YouTube/Audio/PDF submit
│   └── MachineTooltip.test.tsx
└── hooks/
    ├── useJobs.test.ts         ← polling stops at terminal state
    └── useSearch.test.ts
```

Jest + React Testing Library. Canvas mocked (`jest-canvas-mock`). No E2E for MVP.

---

## Future chantiers (non-priority)

### Inline note editor

The "✏️ Write a note" button currently opens a drawer with a simple Markdown editor (textarea + preview). Future evolution: rich editor like CodeMirror or Milkdown.

### Chat as main view

When the LLM layer is integrated, Chat becomes the central view of the app. The factory moves to the background (minimized or accessible via toggle). Design to be specified separately.

### IngestVisualizer — Pokémon animation

Cable + Pokéballs animation as an evolution of the current transit animation. To be specified in a dedicated chantier.

### VaultConstellation

Notes projected in 2D via UMAP, pixel art star map aesthetic. Prerequisites: `/notes/constellation` endpoint on the API side.

### Tauri wrapper

Zero frontend code change required. Separate chantier on the desktop packaging side.

---

## What this frontend does NOT cover

- Note editing → Obsidian
- Note navigation / graph view → Obsidian
- Authentication (local-only for current scope)
- Mobile (375px — interface not adapted)
- i18n (interface in French, no switching)
- `pending_deletion` UI (requires API endpoint first)
