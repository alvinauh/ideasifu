# IdeaSifu — Frontend

The runnable frontend for **IdeaSifu**, a thesis/assignment *idea generator* for
students (high-school to university). It is the generative sibling of
**ThesisSifu** (an evaluator): where ThesisSifu audits a finished draft, IdeaSifu
sits at the empty-page moment and helps a student go from *"I have to write about
something?"* to a **contextualized, defensible idea** — complete with a
critical-thinking mind map, cited sources, and a short video summary.

A small crew of five specialist AI agents (Scout, Ideator, Cartographer,
Librarian, Director) work visibly and hand off to each other, so the *process of
thinking* is itself the teaching moment.

## Stack

- Vite + React 19 + TypeScript
- Tailwind CSS v4 (`@tailwindcss/vite`)
- react-router-dom v7
- lucide-react icons

## Run it

```bash
npm install
npm run dev
```

Then open the printed local URL. **No backend is required** — see below.

Other scripts:

```bash
npm run build     # type-check + production build to dist/
npm run preview   # serve the production build locally
```

## Backend vs. mock (demo mode)

The API client reads `VITE_API_BASE_URL`:

- **Empty / unset (default):** the app uses a built-in **mock client**
  (`src/lib/mockApi.ts`) that returns realistic, topic-aware data with small
  staged delays so the "crew at work" animation reads well. The whole app is
  fully demoable with no server. A **Demo** badge appears in the header.
- **Set to a backend URL:** the app POSTs to that backend instead.

Point at a real backend:

```bash
cp .env.example .env
# then edit .env:
# VITE_API_BASE_URL=http://localhost:8000
```

Expected endpoints (see `src/lib/api.ts` and `../backend/schemas.py`):

| Method + path        | Request body                 | Response                |
| -------------------- | ---------------------------- | ----------------------- |
| `POST /generate-ideas` | `Brief`                     | `GenerateIdeasResponse` |
| `POST /more-ideas`     | `{ brief, scout }`          | `IdeaCandidate[]`       |
| `POST /build`          | `{ brief, scout, idea }`    | `IdeaResult`            |
| `POST /refine`         | `{ brief, idea, nudge }`    | `IdeaCandidate`         |

## Structure

```
src/
  components/    TierToggle, SiteHeader, AgentFeed, IdeaCandidateCard,
                 MindMap, SourcesPanel, VideoPlayer
  data/agents.ts crew metadata (id, name, icon, color, tagline, statusVerb)
  lib/
    types.ts     TS mirror of backend/schemas.py
    api.ts       API client (mock fallback)
    mockApi.ts   topic-aware demo data
    tier.tsx     tier context (HS ↔ University) + tier-aware copy
    store.ts     module store + localStorage library
  pages/         Landing, Generate, Workspace, Library
  styles.css     design tokens (Tailwind v4 theme)
```

## Notes

- The **tier toggle** (🎒 High School ↔ 🎓 University) re-tunes vocabulary,
  rigor, and copy — it is not a cosmetic theme switch. It persists to
  localStorage.
- The **mind map** has an accessible list/outline fallback, a node-type legend,
  and every node carries a "keep thinking" prompt; evidence nodes cross-link to
  the Sources panel.
- Motion respects `prefers-reduced-motion` (handled in `styles.css`).
- Saved ideas persist to `localStorage` under `ideasifu.library`.
```
