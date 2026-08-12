# Sifu Suite — Integration Plan

> Created: 2026-08-12. Documents how IdeaSifu could be combined with thesis-aid-hub,
> thesissifu, and thesissifupro into a unified student-journey platform.

---

## What each piece does

| Repo | Role | Stage in student journey |
|---|---|---|
| **IdeaSifu** (this repo) | Multi-agent idea generator: Scout → Ideator → Cartographer → Librarian → Director. Has Dojo tab (sample thesis chapters) and Corpus tab (semantic search over 7.1M papers). Runs on VPS at :8004 (UI) / :8005 (API). | **Start** — empty page → research idea |
| **thesissifupro** | Multi-stage thesis auditor: Gemini (spine extraction, paragraph audit) + Claude (alignment audit, examiner report) → ZIP of PDF reports. Currently deployed on Railway, uses `$PORT`. | **End** — finished draft → examiner-style critique |
| **thesissifu** | Hosts the Qdrant corpus (bge-m3, 7.1M OpenAlex papers) that IdeaSifu already queries via `/search`. Likely the VPS-resident backend IdeaSifu proxies. | **Middle** — corpus / citation layer |
| **thesis-aid-hub** | Name and position suggest a portal / landing hub that routes students to the right tool. Exact internals unknown (repo was private at time of writing — confirm before planning). | **Gateway** — auth + routing |

> **Note:** `thesis-aid-hub` and `thesissifu` returned 404 on 2026-08-12 — either private
> or renamed. Verify access before proceeding.

---

## Full student journey (target state)

```
thesis-aid-hub  (portal / shared auth / Caddy gateway)
    │
    ├── /ideas   →  IdeaSifu        "I have nothing" → research idea + outline
    ├── /corpus  →  thesissifu      Paper discovery, semantic search, citations
    └── /audit   →  thesissifupro   "I wrote a draft" → examiner report + annotated PDF
```

---

## Integration approaches

### Option A — Shared portal, services stay independent (recommended)

Keep each service running as-is. `thesis-aid-hub` becomes a **landing page + auth
layer** that links to each tool. Caddy routes by path prefix; a shared JWT/session
cookie is passed across the tools.

**What needs to be added:**
- Shared login (JWT issued by a central auth service or thesis-aid-hub itself)
- A common nav bar / header component imported by each frontend
- Caddy config with route prefixes: `/ideas`, `/corpus`, `/audit`
- If thesissifupro stays on Railway: add a Caddy `reverse_proxy` block pointing to
  the Railway URL, so the user sees one domain

**Pros:** Zero re-architecture of working services; each tool evolves independently;
no extra disk pressure on VPS.

**Cons:** Auth cookie sharing across subpaths needs care (SameSite, domain config).

---

### Option B — Monorepo, unified frontend

Merge all frontends into one React app (sidebar/tab layout). All backends proxied
from a single Caddy config.

**What needs to be added:**
- thesissifupro's file-upload audit UI absorbed into IdeaSifu's frontend
- Shared component library (nav, auth state, tier toggle)
- thesissifupro migrated off Railway onto VPS (adds Gemini + Claude API load)

**Pros:** Coherent single-app UX, one deploy.

**Cons:** Larger rewrite; thesissifupro migration adds Gemini dependency + disk risk
(VPS disk is the hard limit — see memory note on no `docker prune`).

---

## Key blockers to resolve

| Blocker | Detail |
|---|---|
| thesissifupro runs on Railway | Uses `$PORT` + `Procfile`. To unify: either proxy it via Caddy (keep on Railway) or migrate to VPS and run as a Docker service. |
| thesis-aid-hub & thesissifu are private | Confirm repo access before planning their role. thesis-aid-hub may already be the intended portal. |
| Disk on VPS is tight | Do NOT run `docker prune`. Adding thesissifupro to VPS adds Gemini weight layer — audit disk before migrating. |
| IdeaSifu memory says "never couple to ThesisSifu" | This was a standalone-deployment rule, not a product rule. Integration is fine as long as each service's Docker network stays cleanly separated and IdeaSifu doesn't hard-depend on thesissifu being up. |

---

## Recommended next steps

1. **Confirm private repos** — get access to `thesis-aid-hub` and `thesissifu`;
   read their READMEs and docker-compose files.
2. **Decide on thesissifupro hosting** — Railway proxy vs VPS migration. Railway is
   simpler; VPS gives one-domain UX without CORS gymnastics.
3. **Design shared auth** — even a simple shared API key + student email session is
   enough for v1. Full OAuth is overkill until multi-institution use.
4. **Wire Caddy** — add route blocks in the VPS Caddy config so all tools live under
   one domain (e.g. `sifusuite.yourdomain.com/ideas`, `/audit`, `/corpus`).
5. **Common nav component** — a thin React component (or even a plain HTML snippet
   injected via Caddy's `header` directive) so users can move between tools.
