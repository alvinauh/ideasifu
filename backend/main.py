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

import io
import os
import tempfile
import uuid

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    AnalysisMethod,
    Brief,
    BuildRequest,
    CommunityFeedResponse,
    ContributionRequest,
    ContributionResult,
    CorpusSearchRequest,
    CorpusSearchResponse,
    DataAnalysisResponse,
    DataStructure,
    DojoCorpusExample,
    DojoGenerateRequest,
    DojoSectionResult,
    FormatMatchResponse,
    GenerateIdeasResponse,
    IdeaCandidate,
    IdeaResult,
    MoreIdeasRequest,
    RefineRequest,
    SessionInfo,
    SessionInitRequest,
    ShareIdeaRequest,
    SharedIdea,
    SharedIdeaDetail,
    ContributionItem,
)
from agents.llm import is_live
from agents.assessor import assess
from agents.formatter import analyze as format_analyze
import orchestrator
import db

try:
    import pandas as pd
    import analysis as _analysis
    from agents.analyst import code_themes, interpret_quantitative
    HAS_ANALYSIS = True
except ImportError:
    HAS_ANALYSIS = False

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

@app.on_event("startup")
def startup():
    db.init_db()

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


def _decode_abstract(inv_index: dict | None) -> str:
    """Reconstruct abstract text from OpenAlex's inverted index format."""
    if not inv_index:
        return ""
    words: dict[int, str] = {}
    for word, positions in inv_index.items():
        for pos in positions:
            words[pos] = word
    if not words:
        return ""
    text = " ".join(words[i] for i in sorted(words))
    parts = text.split()
    if len(parts) > 180:
        text = " ".join(parts[:180]) + "…"
    return text


async def _enrich_corpus(corpus: list[DojoCorpusExample]) -> None:
    """Populate authors/year/venue/doi/reference/abstract on each example, in place."""
    ids = [_oa_short_id(c.openalex_id) for c in corpus if c.openalex_id]
    ids = [i for i in ids if i]
    if not ids:
        return
    params = {
        "filter": "openalex:" + "|".join(ids),
        "per-page": str(min(len(ids), 50)),
        "select": "id,title,publication_year,authorships,primary_location,biblio,doi,abstract_inverted_index",
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
            "abstract": _decode_abstract(w.get("abstract_inverted_index")),
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
        c.abstract = m.get("abstract") or ""


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

    When a session_token is provided, checks and decrements the session's Dojo
    quota (free allowance + earned credits). Students earn more quota by
    contributing substantively to the community. Without a token, runs freely
    (backwards-compatible / demo mode).
    """
    if not req.research_questions.strip():
        req.research_questions = ""

    if req.session_token:
        session = db.get_or_create_session(req.session_token)
        allowed = db.consume_dojo_quota(req.session_token)
        if not allowed:
            raise HTTPException(
                status_code=402,
                detail=(
                    "No Dojo quota remaining. "
                    "Contribute to ideas in the Community tab to earn more credits."
                ),
            )

    corpus: list[DojoCorpusExample] = []
    hits = await _corpus_search(_dojo_corpus_query(req), top_k=10)
    if hits.status == "ok":
        corpus = [
            DojoCorpusExample(
                title=h.title, openalex_id=h.openalex_id, score=h.score
            )
            for h in hits.results
        ]
        await _enrich_corpus(corpus)

    return orchestrator.run_dojo(req, corpus)


# ---------------------------------------------------------------------------
# Community / social endpoints
# ---------------------------------------------------------------------------

@app.post("/session/init", response_model=SessionInfo)
def session_init(req: SessionInitRequest) -> SessionInfo:
    """Create or retrieve an anonymous session by its UUID token."""
    data = db.get_or_create_session(req.token)
    return SessionInfo(
        token=data["token"],
        credits=data["credits"],
        dojo_quota=data["dojo_quota"],
    )


@app.get("/session/{token}", response_model=SessionInfo)
def session_get(token: str) -> SessionInfo:
    data = db.get_session(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionInfo(
        token=data["token"],
        credits=data["credits"],
        dojo_quota=data["dojo_quota"],
    )


@app.post("/community/share", response_model=SharedIdea)
def community_share(req: ShareIdeaRequest) -> SharedIdea:
    """Share an idea to the community pool (idempotent — safe to call twice)."""
    db.get_or_create_session(req.session_token)
    data = db.share_idea(
        idea_id=req.idea.id,
        session_token=req.session_token,
        title=req.idea.title,
        statement=req.idea.statement,
        angle=req.idea.angle,
    )
    return SharedIdea(**data)


@app.get("/community/feed", response_model=CommunityFeedResponse)
def community_feed(limit: int = 20, offset: int = 0) -> CommunityFeedResponse:
    """Paginated list of community-shared ideas (newest first)."""
    ideas = db.get_shared_ideas(limit=limit, offset=offset)
    total = db.count_shared_ideas()
    return CommunityFeedResponse(
        ideas=[SharedIdea(**i) for i in ideas],
        total=total,
    )


@app.get("/community/idea/{idea_id}", response_model=SharedIdeaDetail)
def community_idea_detail(idea_id: str) -> SharedIdeaDetail:
    """Retrieve one shared idea with its (anonymized) contributions."""
    idea = db.get_shared_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found.")
    contribs = db.get_contributions_for_idea(idea_id)
    return SharedIdeaDetail(
        **idea,
        contributions=[ContributionItem(**c) for c in contribs],
    )


@app.post("/community/contribute", response_model=ContributionResult)
def community_contribute(req: ContributionRequest) -> ContributionResult:
    """Submit a structured contribution to a shared idea.

    The contribution is assessed by the Assessor agent for quality. Substantive
    contributions (not empty agreement or filler) earn the contributor 3 credits,
    which can be spent on Dojo section generations.
    """
    idea = db.get_shared_idea(req.idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found.")

    db.get_or_create_session(req.contributor_token)

    verdict = assess(
        idea_title=idea["title"],
        idea_statement=idea["statement"],
        contribution_type=req.type,
        contribution_text=req.text,
    )

    credits_awarded = db.CONTRIBUTION_CREDITS if verdict.quality_ok else 0
    new_credits = 0
    if verdict.quality_ok:
        new_credits = db.award_credits(req.contributor_token, credits_awarded)
    else:
        session = db.get_session(req.contributor_token)
        new_credits = session["credits"] if session else 0

    contrib_id = str(uuid.uuid4())
    db.add_contribution(
        contrib_id=contrib_id,
        idea_id=req.idea_id,
        contributor_token=req.contributor_token,
        type_=req.type,
        text=req.text,
        quality_ok=verdict.quality_ok,
        quality_reason=verdict.reason,
        credits_awarded=credits_awarded,
    )

    return ContributionResult(
        id=contrib_id,
        credits_awarded=credits_awarded,
        quality_ok=verdict.quality_ok,
        quality_reason=verdict.reason,
        new_credits=new_credits,
    )


# ---------------------------------------------------------------------------
# Data Analysis endpoint (DataSifu in the Dojo)
# ---------------------------------------------------------------------------

_MAX_FILE_MB = 10
_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".sav"}


async def _load_dataframe(file: UploadFile) -> "pd.DataFrame":
    content = await file.read()
    if len(content) > _MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_MB} MB limit.")

    name = (file.filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Upload CSV, Excel (.xlsx/.xls), SPSS (.sav), or TXT.",
        )

    if ext == ".csv":
        return pd.read_csv(io.BytesIO(content))
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(content))
    if ext == ".txt":
        text = content.decode("utf-8", errors="replace")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [l.strip() for l in text.splitlines() if l.strip()]
        return pd.DataFrame({"response": paragraphs})
    if ext == ".sav":
        try:
            import pyreadstat
        except ImportError:
            raise HTTPException(
                status_code=422,
                detail="SPSS (.sav) support requires pyreadstat. Use CSV or Excel instead.",
            )
        with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            df, _ = pyreadstat.read_sav(tmp_path)
        finally:
            os.unlink(tmp_path)
        return df

    raise HTTPException(status_code=415, detail="Unrecognised file extension.")


@app.post("/dojo/analyze", response_model=DataAnalysisResponse)
async def dojo_analyze(
    file: UploadFile = File(...),
    research_question: str = Form(""),
    language: str = Form("en"),
    degree: str = Form("undergraduate"),
    session_token: str = Form(""),
) -> DataAnalysisResponse:
    """Upload raw data (CSV/Excel/SPSS/TXT) and receive statistical analysis
    plus an LLM-written, thesis-ready interpretation or thematic coding.

    Auto-selects the appropriate test (t-test, ANOVA, Wilcoxon, chi-square,
    correlation, regression) based on data shape and normality. For text
    responses, performs qualitative thematic analysis (Braun & Clarke, 2006).
    """
    if not HAS_ANALYSIS:
        raise HTTPException(
            status_code=503,
            detail="Analysis libraries (pandas/scipy) are not installed. Rebuild the container.",
        )

    if language not in ("en", "bm"):
        language = "en"
    if degree not in ("undergraduate", "masters", "phd"):
        degree = "undergraduate"

    df = await _load_dataframe(file)
    if df.empty or len(df.columns) == 0:
        raise HTTPException(status_code=422, detail="The uploaded file appears to be empty.")

    # Limit to first 5000 rows for performance
    if len(df) > 5000:
        df = df.head(5000)

    numeric_cols, categorical_cols, text_cols = _analysis.detect_column_types(df)
    data_type = _analysis.detect_data_type(numeric_cols, categorical_cols, text_cols)

    structure = DataStructure(
        rows=len(df),
        columns=df.columns.tolist(),
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        text_columns=text_cols,
    )

    quant_result, methods, detected_type = _analysis.analyze(df)

    interpretation = ""
    qual_themes = None
    qual_summary = ""

    # Quantitative interpretation via LLM
    if quant_result is not None and quant_result.test_name != "Descriptive Statistics":
        try:
            stats_block = _analysis.build_stats_summary(quant_result)
            interpretation, _ = interpret_quantitative(
                stats_summary=stats_block,
                research_question=research_question,
                degree=degree,
                language=language,
            )
        except Exception:
            interpretation = ""  # degrade gracefully; raw stats still returned

    # Qualitative thematic coding via LLM
    if text_cols:
        texts: list[str] = []
        for col in text_cols:
            texts.extend(df[col].dropna().astype(str).tolist())
        if texts:
            try:
                themes, qual_summary = code_themes(
                    texts=texts,
                    research_question=research_question,
                    degree=degree,
                    language=language,
                )
                qual_themes = themes
            except Exception:
                qual_themes = None

    word_count = len(interpretation.split()) + len(qual_summary.split())

    return DataAnalysisResponse(
        data_type=detected_type,
        detected_structure=structure,
        recommended_methods=methods,
        quantitative_results=quant_result,
        qualitative_themes=qual_themes,
        interpretation=interpretation,
        qualitative_summary=qual_summary,
        language=language,
        word_count=word_count,
    )


# ---------------------------------------------------------------------------
# FormatSifu: journal format matching
# ---------------------------------------------------------------------------

def _extract_docx_outline(content: bytes) -> str:
    """Return a structured outline of headings and first-line body text from a DOCX."""
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(io.BytesIO(content))
        lines: list[str] = []
        for para in doc.paragraphs:
            style = para.style.name if para.style else "Normal"
            text = para.text.strip()
            if not text:
                continue
            if style.startswith("Heading"):
                level_str = style.replace("Heading ", "").strip()
                level = int(level_str) if level_str.isdigit() else 1
                indent = "  " * (level - 1)
                lines.append(f"{indent}[{style}] {text}")
            elif style in ("Normal", "Body Text") and len(lines) > 0:
                snippet = text[:120] + ("…" if len(text) > 120 else "")
                lines.append(f"{'  ' * 2}[Body] {snippet}")
        return "\n".join(lines[:80]) or "(no structured content detected)"
    except Exception as exc:
        return f"(DOCX extraction failed: {exc})"


def _extract_pdf_outline(content: bytes) -> str:
    """Return raw text from a PDF (best-effort; no semantic heading detection)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        lines: list[str] = []
        for page in reader.pages[:20]:
            page_text = page.extract_text() or ""
            for line in page_text.split("\n"):
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        return "\n".join(lines[:150]) or "(no text extracted from PDF)"
    except Exception as exc:
        return f"(PDF extraction failed: {exc})"


def _outline_from_upload(file_content: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf_outline(file_content)
    if name.endswith(".docx"):
        return _extract_docx_outline(file_content)
    raise HTTPException(
        status_code=415,
        detail=f"Unsupported file type '{filename}'. Upload a DOCX or PDF.",
    )


_FORMAT_MAX_MB = 10


@app.post("/format-match", response_model=FormatMatchResponse)
async def format_match(
    journal_file: UploadFile = File(..., description="Reference journal article (DOCX or PDF)"),
    document_file: UploadFile = File(..., description="Student's document to check (DOCX or PDF)"),
) -> FormatMatchResponse:
    """Upload a reference journal and a student document.

    Extracts the journal's formatting conventions (heading style, numbering,
    section order) then walks the student's document to find every mismatch
    and produce specific, actionable suggestions.
    """
    j_bytes = await journal_file.read()
    d_bytes = await document_file.read()

    if len(j_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Journal file exceeds {_FORMAT_MAX_MB} MB.")
    if len(d_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document file exceeds {_FORMAT_MAX_MB} MB.")

    journal_outline = _outline_from_upload(j_bytes, journal_file.filename or "journal.docx")
    document_outline = _outline_from_upload(d_bytes, document_file.filename or "document.docx")

    return format_analyze(journal_outline, document_outline)


def _apply_heading_transforms(docx_bytes: bytes, heading_map: list[dict]) -> bytes:
    """Apply heading text/level replacements to a DOCX and return modified bytes."""
    from docx import Document as DocxDocument
    lookup = {entry["original"]: entry for entry in heading_map}
    doc = DocxDocument(io.BytesIO(docx_bytes))
    for para in doc.paragraphs:
        style = para.style.name if para.style else ""
        if not style.startswith("Heading"):
            continue
        text = para.text.strip()
        if text not in lookup:
            continue
        entry = lookup[text]
        target_level = max(1, min(9, int(entry["level"])))
        target_style = f"Heading {target_level}"
        try:
            para.style = doc.styles[target_style]
        except KeyError:
            pass
        replacement = entry["replacement"]
        if para.runs:
            para.runs[0].text = replacement
            for run in para.runs[1:]:
                run.text = ""
        else:
            para.add_run(replacement)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@app.post("/format-transform")
async def format_transform(
    document_file: UploadFile = File(..., description="Student's DOCX to transform"),
    heading_map: str = Form(..., description="JSON array of {original, replacement, level} objects"),
):
    """Apply heading transformations to a DOCX and return the modified file."""
    import json
    from fastapi.responses import Response

    d_bytes = await document_file.read()
    if len(d_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document file exceeds {_FORMAT_MAX_MB} MB.")

    fname = document_file.filename or "document.docx"
    if not fname.lower().endswith(".docx"):
        raise HTTPException(status_code=415, detail="Only DOCX files can be transformed.")

    try:
        replacements = json.loads(heading_map)
    except Exception:
        raise HTTPException(status_code=422, detail="heading_map must be valid JSON.")

    try:
        result_bytes = _apply_heading_transforms(d_bytes, replacements)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transform failed: {exc}")

    stem = fname.rsplit(".", 1)[0]
    out_name = f"{stem}_converted.docx"
    return Response(
        content=result_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
