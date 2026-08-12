"""IdeaSifu backend — FastAPI app exposing the multi-agent idea generator.

IdeaSifu is the generative sibling of ThesisSifu: it takes a student's short
brief and runs a crew of specialist Claude agents (Scout, Ideator, Cartographer,
Librarian, Director) to produce a contextualized, defensible research/assignment
idea, complete with a critical-thinking mind map, citations and books, and a
short narrated video summary.

The pipeline runs end-to-end with NO API key: the orchestrator serves
deterministic, topic-aware mock data whenever a live LLM client isn't
configured or an agent call fails. Set GROQ_API_KEY and/or OPENROUTER_API_KEY
to go live (see agents/llm.py for the provider chain).

Endpoints:
    GET  /health        -> {"status": "ok", "live_llm": bool}
    POST /generate-ideas -> GenerateIdeasResponse (Scout report + 3 candidates)
    POST /generate       -> legacy alias of /generate-ideas
    POST /more-ideas     -> list[IdeaCandidate] (fresh batch for a Scout report)
    POST /build          -> IdeaResult (mind map + sources + video for an idea)
    POST /refine         -> IdeaCandidate (a single idea regenerated with a nudge)
    POST /search-corpus  -> CorpusSearchResponse (semantic search over ThesisSifu's
                            ~7.1M-paper OpenAlex corpus; proxies ThesisSifu /search)

Run:  uvicorn main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    Brief,
    BuildRequest,
    CorpusSearchRequest,
    CorpusSearchResponse,
    DojoCorpusExample,
    DojoGenerateRequest,
    DojoSectionResult,
    GenerateIdeasResponse,
    IdeaCandidate,
    IdeaResult,
    MoreIdeasRequest,
    RefineRequest,
)
from agents.llm import is_live
import orchestrator

# ThesisSifu's additive /search endpoint (embeds with the bge-m3 model it already
# has loaded, then vector-searches its Qdrant corpus). Reached over the shared
# `thesissifu_project_default` Docker network — see docker-compose.yml. Override
# via env for local runs.
THESISSIFU_SEARCH_URL = os.environ.get(
    "THESISSIFU_SEARCH_URL", "http://api:8000/search"
)

app = FastAPI(
    title="IdeaSifu",
    description="A multi-agent thesis/assignment idea generator for students.",
    version="1.0.0",
)

# Permissive CORS (mirrors the ThesisSifu sibling app).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "live_llm": is_live()}


@app.post("/generate-ideas", response_model=GenerateIdeasResponse)
@app.post("/generate", response_model=GenerateIdeasResponse)  # legacy alias
def generate(brief: Brief) -> GenerateIdeasResponse:
    """Scout the field, then fan out to 3 tier-calibrated idea candidates."""
    scout = orchestrator.run_scout(brief)
    candidates = orchestrator.run_ideate(brief, scout)
    return GenerateIdeasResponse(scout=scout, candidates=candidates)


@app.post("/more-ideas", response_model=list[IdeaCandidate])
def more_ideas(req: MoreIdeasRequest) -> list[IdeaCandidate]:
    """Generate a fresh batch of candidates against an existing Scout report."""
    return orchestrator.run_ideate(req.brief, req.scout)


@app.post("/build", response_model=IdeaResult)
def build(req: BuildRequest) -> IdeaResult:
    """Build the full payload (mind map + sources + video) for a chosen idea."""
    return orchestrator.build_idea(req.brief, req.idea)


@app.post("/refine", response_model=IdeaCandidate)
def refine(req: RefineRequest) -> IdeaCandidate:
    """Regenerate a single idea, nudged toward what the student wants."""
    return orchestrator.refine_idea(req)


async def _corpus_search(query: str, top_k: int) -> CorpusSearchResponse:
    """Shared ThesisSifu /search proxy used by the Corpus tab and the Dojo.

    Owns the async httpx call to ThesisSifu (which has the bge-m3 model + Qdrant
    client). Degrades gracefully to an empty result set + message if the corpus
    service is unreachable, so callers never hard-crash.
    """
    query = (query or "").strip()
    if not query:
        return CorpusSearchResponse(status="error", message="Please enter a search query.")
    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                THESISSIFU_SEARCH_URL,
                json={"query": query, "top_k": top_k},
            )
            resp.raise_for_status()
            data = resp.json()
        return CorpusSearchResponse(
            status=data.get("status", "ok"),
            count=data.get("count", len(data.get("results", []))),
            results=data.get("results", []),
            message=data.get("message"),
        )
    except Exception as exc:  # network error, timeout, bad JSON, corpus down
        return CorpusSearchResponse(
            status="error",
            message=f"Corpus search is unavailable right now ({type(exc).__name__}).",
        )


@app.post("/search-corpus", response_model=CorpusSearchResponse)
async def search_corpus(req: CorpusSearchRequest) -> CorpusSearchResponse:
    """Semantic search over ThesisSifu's ~7.1M-paper OpenAlex corpus."""
    return await _corpus_search(req.query, req.top_k)


# OpenAlex work-metadata API. The ThesisSifu corpus returns only title +
# openalex_id, so we enrich the Dojo's grounding papers here (authors, year,
# venue, DOI) to render real references. Best-effort: any failure degrades to
# title-only grounding, never a hard error.
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "han@iegcampus.com")


def _oa_short_id(openalex_id: str | None) -> str:
    """'https://openalex.org/W123' (or 'W123') -> 'W123'."""
    return (openalex_id or "").rstrip("/").split("/")[-1]


def _fmt_authors(names: list[str]) -> str:
    """Format a list of 'First Middle Last' display names into APA author order.

    'Che Noraini Hashim' -> 'Hashim, C. N.'  Multiple authors are joined with an
    ampersand; 21+ authors are elided per APA (first 19 … last).
    """
    def one(n: str) -> str:
        parts = [p for p in n.replace(".", "").split() if p]
        if not parts:
            return n.strip()
        surname = parts[-1]
        initials = " ".join(f"{p[0].upper()}." for p in parts[:-1])
        return f"{surname}, {initials}" if initials else surname

    formatted = [one(n) for n in names if n and n.strip()]
    if not formatted:
        return ""
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    return ", ".join(formatted[:19]) + ", … " + formatted[-1]


def _intext_cite(names: list[str], year) -> str:
    """APA in-text form: (Surname, Year) / (A & B, Year) / (A et al., Year)."""
    surnames = [n.split()[-1] for n in names if n and n.strip()]
    yr = year if year else "n.d."
    if not surnames:
        return ""
    if len(surnames) == 1:
        tag = surnames[0]
    elif len(surnames) == 2:
        tag = f"{surnames[0]} & {surnames[1]}"
    else:
        tag = f"{surnames[0]} et al."
    return f"({tag}, {yr})"


def _apa_reference(m: dict, authors: str) -> str:
    """Build a plain-text APA-style citation from OpenAlex metadata (no URL —
    the DOI/OpenAlex link is rendered separately)."""
    year = m.get("year")
    title = (m.get("title") or "").strip().rstrip(".")
    venue = (m.get("venue") or "").strip()
    vol, issue = m.get("volume"), m.get("issue")
    fp, lp = m.get("first_page"), m.get("last_page")

    parts: list[str] = []
    if authors:
        parts.append(authors)
    parts.append(f"({year})." if year else "(n.d.).")
    if title:
        parts.append(f"{title}.")
    if venue:
        seg = venue
        if vol:
            seg += f", {vol}"
            if issue:
                seg += f"({issue})"
        if fp:
            seg += f", {fp}" + (f"–{lp}" if lp else "")
        parts.append(seg + ".")
    return " ".join(parts).strip()


async def _enrich_corpus(corpus: list[DojoCorpusExample]) -> None:
    """Populate authors/year/venue/doi/reference on each example, in place."""
    ids = [_oa_short_id(c.openalex_id) for c in corpus if c.openalex_id]
    ids = [i for i in ids if i]
    if not ids:
        return
    params = {
        "filter": "openalex:" + "|".join(ids),
        "per-page": str(min(len(ids), 50)),
        "select": "id,title,publication_year,authorships,primary_location,biblio,doi",
        "mailto": OPENALEX_MAILTO,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.get(OPENALEX_WORKS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # OpenAlex down/slow/rate-limited -> keep title-only
        return

    by_id: dict[str, dict] = {}
    for w in data.get("results", []):
        loc = (w.get("primary_location") or {}).get("source") or {}
        bib = w.get("biblio") or {}
        by_id[_oa_short_id(w.get("id"))] = {
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "authors": [
                a["author"]["display_name"]
                for a in (w.get("authorships") or [])
                if a.get("author")
            ],
            "venue": loc.get("display_name"),
            "volume": bib.get("volume"),
            "issue": bib.get("issue"),
            "first_page": bib.get("first_page"),
            "last_page": bib.get("last_page"),
            "doi": w.get("doi"),
        }

    for c in corpus:
        m = by_id.get(_oa_short_id(c.openalex_id))
        if not m:
            continue
        authors = _fmt_authors(m.get("authors") or [])
        c.authors = authors
        c.year = m.get("year")
        c.venue = m.get("venue") or ""
        c.doi = m.get("doi")
        c.reference = _apa_reference(m, authors)
        c.intext = _intext_cite(m.get("authors") or [], m.get("year"))


def _dojo_corpus_query(req: DojoGenerateRequest) -> str:
    """Build the corpus query for a Dojo section from the student's inputs.

    bge-m3 is multilingual, so we can query in whatever language the student
    typed. Topic + research questions describe the study best; the section notes
    sharpen the retrieval toward what this chapter is about.
    """
    parts = [req.topic, req.research_questions, req.notes]
    return " ".join(p.strip() for p in parts if p and p.strip())[:1000]


@app.post("/dojo/generate", response_model=DojoSectionResult)
async def dojo_generate(req: DojoGenerateRequest) -> DojoSectionResult:
    """Write one capped, corpus-grounded sample thesis section (the Dojo).

    Pulls real papers from ThesisSifu's corpus to ground the writeup, then hands
    them to Sensei (or the deterministic mock) to draft the section. The research
    questions are required; every other section is generatable on demand.
    """
    if not req.research_questions.strip():
        # Should be caught client-side, but guard the contract here too.
        req.research_questions = ""

    corpus: list[DojoCorpusExample] = []
    hits = await _corpus_search(_dojo_corpus_query(req), top_k=6)
    if hits.status == "ok":
        corpus = [
            DojoCorpusExample(
                title=h.title, openalex_id=h.openalex_id, score=h.score
            )
            for h in hits.results
        ]
        # Enrich with real reference metadata (authors/year/venue/DOI) so the
        # grounding panel shows full citations, not bare titles.
        await _enrich_corpus(corpus)

    return orchestrator.run_dojo(req, corpus)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
