# IdeaSifu — "Query the ThesisSifu database" tab — Investigation & Plan

_Working notes. Last updated: 2026-07-30. Status: **investigated, NOT built — paused mid-decision.**_

## 🔖 PICK-UP HERE (session 2026-07-30, continued)

**Decisions made this session:**
- **Path A chosen** by user (IdeaSifu embeds queries itself + hits Qdrant directly).
  Coupling to ThesisSifu accepted for this feature.
- **Result display:** not finalized (default assumption = title → OpenAlex link).

**Verified live infra (2026-07-30):**
- Qdrant is UP: container `thesissifu_project-qdrant-1`, bound loopback-only
  `127.0.0.1:6333`, collection `thesissifu_v1` responding. Reach it from IdeaSifu
  by joining network `thesissifu_project_default` (hostname `qdrant:6333`).
- IdeaSifu containers: `ideasifu-api` (:8005), `ideasifu-web` (:8004), on `ideasifu_net`.
- bge-m3 weights already on disk: `/root/thesissifu_project/model_weights` = **3.8 GB**.

**Restart question — ANSWERED:** ThesisSifu does **NOT** need a restart for Path A.
`docker network connect thesissifu_project_default ideasifu-api` attaches IdeaSifu
to the network without touching any ThesisSifu container (zero downtime for `/audit`).
Only `ideasifu-api` gets rebuilt/restarted (our own project). To make the network
attach survive `docker compose up`, add `thesissifu_project_default` as an
`external` network in IdeaSifu's `docker-compose.yml`.

**VPS constraints (the real blockers):**
- Disk: **14 GB free / 91% used** on 150 GB. This is a HARD limit —
  **do NOT prune** docker cache/images (user: much of it isn't reclaimable, backs
  other stacks). See memory `vps-no-docker-prune`.
- RAM: 7.6 GB total, ~6 GB avail, **swap already 9 GB used** = real memory pressure.
- Path A cost without pruning: **bind-mount** the existing 3.8 GB weights (0 extra
  disk, do NOT copy into image), but torch+sentence-transformers still add ~3 GB
  image layers + ~1–2 GB transient build cache → lands ~9–10 GB free / ~93% used.
  Adds ~2.5 GB resident RAM (2nd model) on top of existing swap pressure. Works,
  but tight on both scarce resources.

**⏸ OPEN — the live reconsideration when picking back up:**
User picked Path A, but after the no-prune + tight-RAM findings, Claude flagged
that **both** scarce resources (disk + RAM) now favor **Path B** (add a small
`/search` route to ThesisSifu, reuse its already-loaded bge-m3 model, ~0 extra
disk/RAM in IdeaSifu; cost = one additive route + ThesisSifu `api` redeploy, no
data touched). **DECISION TO CONFIRM: stay on A, or switch to B.** Then build.

**Next action when resuming:** confirm A vs B → if A: bind-mount weights, add
external net to compose, add `POST /search-corpus` to IdeaSifu backend (embed
bge-m3 → query `qdrant:6333` `thesissifu_v1` → return title+openalex_id), new
frontend search tab, rebuild `ideasifu-api`+`ideasifu-web`, smoke-test, verify
ThesisSifu `/audit` still works.

---


## The request
Add a tab in IdeaSifu that lets a user **query the ThesisSifu database**.

## ⚠️ Conflict to resolve first
IdeaSifu's standing rule (see `DEPLOYMENT_PLAN.md` + memory `ideasifu-standalone`)
is: **standalone, own Docker network, no shared Qdrant, no coupling to ThesisSifu.**
This feature *reverses* that rule — it introduces the first real coupling between
the two projects. Building it is a deliberate decision to accept that coupling.

Also corrected a misconception (2026-07-30): **IdeaSifu does NOT currently pull
from ThesisSifu's Qdrant.** Verified by grep — zero `qdrant`/`6333`/`embed`/
`vector` refs in `backend/`. Scout & Librarian use **live web search** (now
OpenRouter `:online`), not a vector DB. So this tab is brand-new wiring, not
hooking up something that already exists.

## What "the ThesisSifu database" actually is
ThesisSifu (`/root/thesissifu_project`) has two stores:

1. **Qdrant vector DB** — this is the real corpus.
   - Collection: **`thesissifu_v1`**
   - **7,123,705 points**, vectors **1024-dim, Cosine** distance.
   - Payload per point is minimal: **`title`** (paper title) + **`openalex_id`**
     (e.g. `https://openalex.org/W286148134`).
   - It's an **OpenAlex academic-paper corpus** — millions of paper titles,
     embedded for semantic search.
   - Runs at `127.0.0.1:6333` on the host; container hostname `qdrant:6333` on
     the `thesissifu_project_default` Docker network. **Loopback-only** port bind.

2. **SQLite `thesissifu_education.db`** — NOT interesting. One table `users`
   (`email`, `tokens`), 1 row. Just auth/token accounting. Ignore for search.

## The crux: the embedding model
The index was built (`thesissifu_project/bake_vectors.py`) with:

```python
model = SentenceTransformer('BAAI/bge-m3', device='cuda')  # 1024-dim, multilingual
model.max_seq_length = 512
```

The ThesisSifu API loads the same weights locally for its own use:
```python
# thesissifu_auditor.py
model = SentenceTransformer('/app/model_weights', device='cpu', local_files_only=True)
client = QdrantClient("qdrant", port=6333, timeout=60)
```
Weights live in `/root/thesissifu_project/model_weights` (bge-m3, ~2 GB:
`pytorch_model.bin` + safetensors + tokenizer).

**Implication:** a query string must be embedded with **bge-m3** to produce a
1024-dim vector; anything else returns garbage matches. This is the main design
driver.

## ThesisSifu API surface (`:8002`, public `https://api2.thesissifu.com`)
Only two routes exist — **no search/query endpoint**:
- `POST /audit` — audits an uploaded document.
- `GET  /download/{filename}`.

So "call the existing API" is NOT an option out of the box; a search path has to
be created somewhere.

## Two implementation paths

### Path A — IdeaSifu embeds + queries Qdrant directly (self-contained)
IdeaSifu backend loads bge-m3 itself, embeds the query, hits Qdrant
`/collections/thesissifu_v1/points/search`, returns `title` + `openalex_id`.
- Networking: attach `ideasifu-api` to the external `thesissifu_project_default`
  network to reach `qdrant:6333` (Qdrant's port is loopback-only, so joining the
  network is the clean way).
- **Cons:** ships a second ~2 GB bge-m3 model + `torch`/`sentence-transformers`
  into IdeaSifu's image (currently slim); slower cold start; duplicates the model
  already loaded next door; couples IdeaSifu directly to Qdrant (max coupling).

### Path B — add a `/search` endpoint to ThesisSifu, IdeaSifu calls it (RECOMMENDED)
Add one additive route to `thesissifu_auditor.py`:
`POST /search {query, top_k}` → embeds with the **already-loaded** bge-m3 model →
Qdrant search → returns `[{title, openalex_id, score}]`. IdeaSifu's new tab just
does an HTTP call (via the `/api` proxy or directly to `:8002`).
- **Pros:** reuses the model + Qdrant client already in memory (no duplicate 2 GB
  download, no torch in IdeaSifu); IdeaSifu stays light; coupling is HTTP-only and
  minimal; one small, low-risk change to ThesisSifu.
- **Cons:** touches the ThesisSifu project (adds an endpoint + a redeploy of the
  `api` container); needs CORS/allow for the IdeaSifu origin if called from the
  browser (cleaner: proxy through IdeaSifu's Caddy `/api`).

**Recommendation: Path B.** Smallest footprint, keeps IdeaSifu slim, coupling is
a single HTTP dependency instead of a shared vector store + duplicated model.

## Open decisions (need answers before building)
1. **Accept the coupling?** (This breaks the standalone rule — confirm.)
2. **Path A or Path B?** (Recommend B.)
3. **What should the tab show?** Payload only has `title` + `openalex_id`. Likely:
   result list of titles, each linking to its OpenAlex page
   (`openalex_id` is already a URL). Want anything richer (authors/year/abstract)?
   That would require enriching via the OpenAlex API at query time — extra work.
4. **Who can use it?** Same open/unauth exposure as the rest of IdeaSifu right now.

## Concrete next steps (once decided — assuming Path B)
- [ ] ThesisSifu: add `POST /search` to `thesissifu_auditor.py` (embed + Qdrant
      search + return top_k). Rebuild/redeploy the `api` container.
- [ ] IdeaSifu backend: add `POST /search-corpus` (or similar) that forwards to
      ThesisSifu's `/search` (keeps the browser same-origin via `/api`).
- [ ] IdeaSifu frontend: new tab/route with a search box + results list (titles →
      OpenAlex links). Wire in `frontend/src/lib/api.ts` + a page/tab component.
- [ ] Rebuild frontend (`VITE_API_BASE_URL=/api`) + redeploy `ideasifu-web`.
- [ ] Smoke-test: query returns relevant titles; confirm ThesisSifu `/audit` still
      works after its redeploy.

## Quick reference (verified 2026-07-30)
| Thing | Value |
|---|---|
| Qdrant collection | `thesissifu_v1` — 7,123,705 pts, 1024-dim, Cosine |
| Payload fields | `title`, `openalex_id` |
| Embedding model | `BAAI/bge-m3` (1024-dim, 512 max seq), weights in `thesissifu_project/model_weights` |
| Qdrant address | `qdrant:6333` on `thesissifu_project_default` net; host `127.0.0.1:6333` |
| ThesisSifu API | `:8002` / `https://api2.thesissifu.com` — only `/audit`, `/download/{f}` (NO search) |
| IdeaSifu live | UI `http://178.105.130.105:8004`, API `:8005`, net `ideasifu_net` |
