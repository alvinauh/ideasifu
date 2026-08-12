# IdeaSifu — Deployment Plan & Status

_Working notes for dockerizing & deploying IdeaSifu. Last updated: 2026-07-18._

## Goal

Dockerize & deploy IdeaSifu as a **self-contained, standalone stack** — API +
frontend served together, reachable on a host port. TLS/public domain left for
later.

## Relationship to ThesisSifu / ThesisCoach — NONE (standalone)

**IdeaSifu is a separate project and will NOT be wired to ThesisSifu.**

- It does **not** use Qdrant (the Librarian agent uses live web search, not a
  vector DB — confirmed by grep: no `qdrant`/`6333`/`embed` refs in the backend).
- Its compose will use its **own Docker network**, not `thesissifu_project_default`.
- It will **not** attach to the shared Caddy, not read ThesisSifu's model
  weights, and not depend on the scanner stack being up.
- The only reason the sibling projects (`thesissifu_project`, `thesiscoach_project`)
  were examined was to copy **conventions** (host-port numbering, `start.sh`
  style, Dockerfile shape) — not to create any runtime coupling.

Port convention observed on this host (for picking a free port, nothing more):
`8002` = thesissifu api, `8003` = thesiscoach. So IdeaSifu takes **8004/8005**.

## Deployment decisions (confirmed with user)

- **Serve both** frontend + API in one self-contained stack (one `bash start.sh`).
- **Host port only**, own network. No shared Caddy, no public domain yet.

## Key findings from the code

1. **Backend already has graceful mock fallback** (`orchestrator.py` +
   `agents/llm.py`): with no `ANTHROPIC_API_KEY`, every stage serves
   deterministic mock data. So it deploys & runs end-to-end with zero creds.
   Model in use: `claude-opus-4-8` + server-side `web_search` tool.

2. **Frontend↔backend API contract mismatch (MUST FIX before wiring live):**

   | Frontend calls (`frontend/src/lib/api.ts`) | Backend has (`backend/main.py`) | Status |
   |---|---|---|
   | `POST /generate-ideas` (body `Brief`) | `POST /generate` | ❌ path mismatch |
   | `POST /more-ideas` (`{brief, scout}`) | — | ❌ missing route |
   | `POST /build` (`{brief, scout, idea}`) | `POST /build` (`BuildRequest`) | ✅ |
   | `POST /refine` (`{brief, idea, nudge}`) | `POST /refine` (`RefineRequest`) | ✅ |

3. **Existing `frontend/dist` is a MOCK build.** It was built with an empty
   `VITE_API_BASE_URL`, and `api.ts` sets `USING_MOCK = (BASE.length === 0)`.
   So serving the stale `dist/` as-is would never call the backend. The frontend
   must be **rebuilt** with a non-empty base to talk to the live API.

## Planned changes

### A. Backend contract fix (so the wired frontend works)
- `backend/schemas.py`: add `MoreIdeasRequest { brief: Brief; scout: ScoutReport }`.
- `backend/main.py`:
  - Serve `POST /generate-ideas` (keep `POST /generate` as a legacy alias).
  - Add `POST /more-ideas` → `orchestrator.run_ideate(brief, scout)`.

_(This edit was drafted but paused pending your review — nothing applied yet.)_

### B. Deployment files (all new, under `/root/ideasifu_project/`)
- `frontend/Dockerfile` — multi-stage: `node` build stage (build with
  `VITE_API_BASE_URL=/api`) → `caddy:2-alpine` serving the SPA and
  reverse-proxying `/api/*` → the API container.
- `frontend/Caddyfile` — static SPA with `try_files … /index.html` (react-router
  v7) + `handle_path /api/*` → `reverse_proxy ideasifu-api:8000`.
- `frontend/.dockerignore`, `backend/.dockerignore`.
- `docker-compose.yml` — two services on IdeaSifu's **own** network:
  - `ideasifu-web` (Caddy): host **8004** → main entry (UI + `/api` proxy).
  - `ideasifu-api` (uvicorn): host **8005** → direct `/docs` & `/health`.
  - `ANTHROPIC_API_KEY` passed through from the environment
    (`${ANTHROPIC_API_KEY:-}`); empty → graceful mock mode. No secret written to disk.
- `start.sh` — `docker compose up -d --build`, warn if `ANTHROPIC_API_KEY` unset.

### Why same-origin `/api` proxy (not a baked absolute URL)
There's no public domain and Vite bakes `VITE_API_BASE_URL` at build time.
Baking `http://localhost:8004` only works from the same machine. Serving the UI
and proxying `/api/*` from one origin makes it work however the host is reached
(localhost, server IP, SSH tunnel), with no CORS surprises.

## Status — DEPLOYED 2026-07-30
- [x] Investigated codebase, runtime, sibling conventions
- [x] Confirmed deployment shape with user (serve both, host-port only, standalone)
- [x] Identified contract mismatch + stale-mock-build issue
- [x] Apply backend contract fix (`/generate-ideas` + `/more-ideas`, `/generate` alias)
- [x] Add deployment files (frontend Dockerfile/Caddyfile, compose, start.sh)
- [x] Build & smoke-test — `/health` `live_llm:true`, generate → build flow verified

### LLM provider swap (Anthropic → Groq + OpenRouter)
Per user, the backend no longer uses Anthropic. `backend/agents/llm.py` now uses
OpenAI-compatible clients (keys shared from `/root/kuasaprestij/.env`, read at
launch by `start.sh` — never written into this repo):
- Non-web agents (Ideator/Cartographer/Director/refine): Groq
  `llama-3.3-70b-versatile` → OpenRouter free Llama fallback.
- Web agents (Scout/Librarian): OpenRouter `:online` (Exa web search; Groq can't
  search so it's only a no-web fallback). `requirements.txt`: `anthropic`→`openai`.

### Live now
- UI: `http://localhost:8004` · API docs: `http://localhost:8005/docs`
- Compose project `ideasifu`, network `ideasifu_net` — does not touch thesissifu.
- No public domain / TLS yet (host-port only, as agreed).
