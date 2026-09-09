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
from agents.formatter import analyze as format_analyze, reformat_references_apa
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
    """Return a structured outline of headings plus a confirmed-present section list."""
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(io.BytesIO(content))
        all_texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        # Detect key academic sections regardless of heading style
        def _text_matches(candidates):
            return any(t.lower().strip() in candidates for t in all_texts)

        present: list[str] = []
        if _text_matches({"abstract"}):
            present.append("ABSTRACT")
        if any("keyword" in t.lower() for t in all_texts[:30]):
            present.append("KEYWORDS")
        if _text_matches({"references", "bibliography", "list of references", "reference list"}):
            present.append("REFERENCES")
        if _text_matches({"acknowledgment", "acknowledgement", "acknowledgments", "acknowledgements"}):
            present.append("ACKNOWLEDGMENT")
        if any("conflict of interest" in t.lower() for t in all_texts):
            present.append("CONFLICT OF INTEREST STATEMENT")
        if _text_matches({"appendix", "appendices"}):
            present.append("APPENDIX")

        lines: list[str] = []
        if present:
            lines.append(f"[KEY SECTIONS CONFIRMED PRESENT: {', '.join(present)}]")
            lines.append("")

        # Heading structure — show one body snippet per heading section
        shown_body = False
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
                shown_body = False
            elif not shown_body and style in ("Normal", "Body Text"):
                snippet = text[:120] + ("…" if len(text) > 120 else "")
                lines.append(f"    [Body] {snippet}")
                shown_body = True

        return "\n".join(lines[:150]) or "(no structured content detected)"
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
    document_file: UploadFile = File(..., description="Student's document to check (DOCX or PDF)"),
    journal_file: UploadFile | None = File(None, description="Reference journal article (DOCX or PDF)"),
    template_text: str = Form("", description="Plain-text formatting specification (alternative to uploading a journal file)"),
) -> FormatMatchResponse:
    """Upload a reference journal (or paste its formatting rules) and a student document.

    When template_text is provided it is used directly as the formatting specification,
    bypassing file extraction. Otherwise journal_file is required and its heading
    structure is extracted and compared against the student document.
    """
    has_text = bool(template_text.strip())
    if not has_text and journal_file is None:
        raise HTTPException(
            status_code=422,
            detail="Provide either a journal_file or paste the formatting rules in template_text.",
        )

    d_bytes = await document_file.read()
    if len(d_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document file exceeds {_FORMAT_MAX_MB} MB.")

    if has_text:
        journal_outline = template_text.strip()
        journal_is_spec = True
    else:
        j_bytes = await journal_file.read()  # type: ignore[union-attr]
        if len(j_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Journal file exceeds {_FORMAT_MAX_MB} MB.")
        journal_outline = _outline_from_upload(j_bytes, journal_file.filename or "journal.docx")  # type: ignore[union-attr]
        journal_is_spec = False

    document_outline = _outline_from_upload(d_bytes, document_file.filename or "document.docx")

    return format_analyze(journal_outline, document_outline, journal_is_spec)


def _copy_journal_styles(journal_bytes: bytes, student_doc) -> None:
    """Overwrite student document's style definitions with the journal's."""
    import copy
    from docx import Document as DocxDocument
    from docx.oxml.ns import qn

    journal_doc = DocxDocument(io.BytesIO(journal_bytes))
    j_styles = journal_doc.part.styles.element
    s_styles = student_doc.part.styles.element

    # Index existing student styles by styleId for fast lookup
    existing = {}
    for el in list(s_styles):
        sid = el.get(qn("w:styleId"))
        if sid:
            existing[sid] = el

    # Replace matching styles; append new ones
    for j_el in j_styles:
        sid = j_el.get(qn("w:styleId"))
        if not sid:
            continue
        if sid in existing:
            s_styles.remove(existing[sid])
        s_styles.append(copy.deepcopy(j_el))


_SECTION_TEMPLATES: dict[str, list[str]] = {
    "ABSTRACT": [
        "Purpose – [State the background and aims of the study.]",
        "Methodology – [State the research design, sampling design, sample size, instruments, and data analysis method.]",
        "Findings – [State the main results. Include key numerical outcomes where applicable.]",
        "Novelty – [State the originality or contribution of the research.]",
        "Significance – [State who would benefit from this study and how.]",
    ],
    "KEYWORDS": ["Keywords: [keyword1, keyword2, keyword3, keyword4, keyword5]"],
    "ACKNOWLEDGMENT": [
        "This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.",
    ],
    "CONFLICT OF INTEREST STATEMENT": [
        "The authors declare no conflict of interest.",
    ],
    "APPENDIX": ["[Insert supplementary materials, instruments, or data tables here.]"],
}

_REF_HEADING_ALIASES = {
    "references", "bibliography", "list of references", "reference list",
    "references cited", "works cited",
}


def _transform_document(
    docx_bytes: bytes,
    heading_map: list[dict],
    section_order: list[str],
    missing_sections: list[str],
    journal_bytes: bytes | None = None,
) -> bytes:
    """Fully convert a DOCX: rename headings, reorder sections, add missing placeholders,
    reformat the references section to APA 7th, and optionally inject journal styles."""
    import copy
    from docx import Document as DocxDocument
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = DocxDocument(io.BytesIO(docx_bytes))
    lookup = {e["original"]: e for e in heading_map}
    body = doc.element.body
    sectPr = body.find(qn("w:sectPr"))

    def _get_style_val(el):
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            return None
        pStyle = pPr.find(qn("w:pStyle"))
        return pStyle.get(qn("w:val")) if pStyle is not None else None

    def _el_text(el):
        return "".join(t.text or "" for t in el.iter(qn("w:t")))

    def _is_h1(el):
        style = _get_style_val(el)
        if style is None:
            return False
        s = style.lower().replace(" ", "")
        return s in ("heading1", "h1", "1") or s.startswith("heading1")

    def _is_any_heading(el):
        style = _get_style_val(el)
        if style is None:
            return False
        s = style.lower().replace(" ", "")
        return s.startswith("heading") or s in ("h1", "h2", "h3", "h4", "h5", "h6")

    def _set_heading(el, text, level):
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            el.insert(0, pPr)
        pStyle = pPr.find(qn("w:pStyle"))
        if pStyle is None:
            pStyle = OxmlElement("w:pStyle")
            pPr.insert(0, pStyle)
        pStyle.set(qn("w:val"), f"Heading{level}")
        for t in list(el.iter(qn("w:t"))):
            t.text = ""
        runs = el.findall(f".//{qn('w:r')}")
        if runs:
            t = runs[0].find(qn("w:t"))
            if t is None:
                t = OxmlElement("w:t")
                runs[0].append(t)
            t.text = text
            for r in runs[1:]:
                for t2 in r.findall(qn("w:t")):
                    t2.text = ""
        else:
            r = OxmlElement("w:r")
            t = OxmlElement("w:t")
            t.text = text
            r.append(t)
            el.append(r)

    def _make_heading_el(text, level):
        p = OxmlElement("w:p")
        pPr = OxmlElement("w:pPr")
        pStyle = OxmlElement("w:pStyle")
        pStyle.set(qn("w:val"), f"Heading{level}")
        pPr.append(pStyle)
        p.append(pPr)
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = text
        r.append(t)
        p.append(r)
        return p

    def _make_body_el(text):
        p = OxmlElement("w:p")
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = text
        r.append(t)
        p.append(r)
        return p

    def _set_run_text(el, text):
        """Replace all run text in an existing paragraph element."""
        for t in list(el.iter(qn("w:t"))):
            t.text = ""
        runs = el.findall(f".//{qn('w:r')}")
        if runs:
            t_el = runs[0].find(qn("w:t"))
            if t_el is None:
                t_el = OxmlElement("w:t")
                runs[0].append(t_el)
            t_el.text = text
            for r in runs[1:]:
                for t2 in r.findall(qn("w:t")):
                    t2.text = ""

    # Group body elements: preamble + list of (heading_el, [child_els])
    # Split on ANY heading (H1–H6) so sub-sections are not orphaned.
    preamble, sections, current_body = [], [], []
    current_heading = None
    for el in list(body):
        if el is sectPr:
            continue
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag == "p" and _is_any_heading(el):
            if current_heading is None:
                preamble = list(current_body)
            else:
                sections.append((current_heading, list(current_body)))
            current_heading = el
            current_body = []
        else:
            current_body.append(el)
    if current_heading is not None:
        sections.append((current_heading, list(current_body)))
    elif current_body:
        preamble = list(current_body)

    # Apply heading_map renames/level changes; detect which sections are H1
    renamed = []
    for h_el, body_els in sections:
        text = _el_text(h_el).strip()
        orig_is_h1 = _is_h1(h_el)
        if text in lookup:
            entry = lookup[text]
            new_text = entry["replacement"]
            new_level = max(1, min(9, int(entry["level"])))
        else:
            new_text = text
            new_level = 1 if orig_is_h1 else (
                int((_get_style_val(h_el) or "Heading1").replace("Heading", "").replace(" ", "") or "1")
                if _is_any_heading(h_el) else 1
            )
        _set_heading(h_el, new_text, new_level)
        renamed.append((new_text, new_level, h_el, body_els))

    # Reorder top-level (level-1) sections; sub-sections stay attached
    order_map = {name.strip().upper(): i for i, name in enumerate(section_order)}

    def _sort_key(s):
        if s[1] == 1:  # only reorder H1 sections
            return order_map.get(s[0].strip().upper(), 999)
        return 999

    renamed.sort(key=_sort_key)

    # Rebuild body
    for child in list(body):
        body.remove(child)
    for el in preamble:
        body.append(el)
    existing = {s[0].strip().upper() for s in renamed}
    refs_section_body_els: list = []  # collect ref paragraph elements for APA pass
    for new_text, new_level, h_el, body_els in renamed:
        body.append(h_el)
        for el in body_els:
            body.append(el)
        if new_text.strip().lower() in _REF_HEADING_ALIASES:
            refs_section_body_els = body_els

    # Append truly missing sections with structured templates
    for missing in missing_sections:
        key = missing.strip().upper()
        if key not in existing:
            body.append(_make_heading_el(missing, 1))
            templates = _SECTION_TEMPLATES.get(key, ["[Add content for this section]"])
            for line in templates:
                body.append(_make_body_el(line))

    if sectPr is not None:
        body.append(sectPr)

    # APA reformat pass — find body paragraphs under the References heading
    # and replace their text with properly formatted APA 7th edition entries.
    if refs_section_body_els:
        ref_paras = [
            el for el in refs_section_body_els
            if el.tag.split("}")[-1] == "p" and _el_text(el).strip()
        ]
        raw_refs = [_el_text(p).strip() for p in ref_paras]
        if raw_refs:
            reformatted = reformat_references_apa(raw_refs)
            for p_el, new_ref in zip(ref_paras, reformatted):
                _set_run_text(p_el, new_ref)

    if journal_bytes:
        _copy_journal_styles(journal_bytes, doc)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@app.post("/format-transform")
async def format_transform(
    document_file: UploadFile = File(..., description="Student's DOCX to transform"),
    heading_map: str = Form(..., description="JSON array of {original, replacement, level} objects"),
    section_order: str = Form("[]", description="JSON array of section names in target order"),
    missing_sections: str = Form("[]", description="JSON array of section names absent from the document"),
    journal_file: UploadFile = File(None, description="Reference journal DOCX to copy styles from (optional)"),
):
    """Fully convert a DOCX: rename headings, reorder sections, add missing placeholders,
    and apply the journal's style definitions."""
    import json
    from fastapi.responses import Response

    d_bytes = await document_file.read()
    if len(d_bytes) > _FORMAT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document file exceeds {_FORMAT_MAX_MB} MB.")

    fname = document_file.filename or "document.docx"
    if not fname.lower().endswith(".docx"):
        raise HTTPException(status_code=415, detail="Only DOCX files can be transformed.")

    j_bytes: bytes | None = None
    if journal_file is not None:
        j_bytes = await journal_file.read()
        jname = (journal_file.filename or "").lower()
        if not jname.endswith(".docx"):
            j_bytes = None  # silently skip style copy for non-DOCX journal

    try:
        replacements = json.loads(heading_map)
        order = json.loads(section_order)
        missing = json.loads(missing_sections)
    except Exception:
        raise HTTPException(status_code=422, detail="heading_map, section_order, and missing_sections must be valid JSON.")

    try:
        result_bytes = _transform_document(d_bytes, replacements, order, missing, j_bytes)
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
