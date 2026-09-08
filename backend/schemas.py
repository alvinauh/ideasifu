"""Shared Pydantic models for the IdeaSifu multi-agent pipeline.

These types are the contract between the agents, the orchestrator, and the
frontend. Keep them in sync with `frontend/src/lib/types.ts`.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Tier = Literal["university"]
AssignmentType = Literal["essay", "research_proposal", "project", "presentation"]


class Brief(BaseModel):
    """The student's short brief — the only required input."""
    subject: str = Field(..., description="Subject or topic, e.g. 'climate change in Southeast Asia'")
    tier: Tier = "university"
    level: str = Field("", description="Exact year/level, e.g. 'Form 5' or 'Year 2 undergraduate'")
    interests: str = Field("", description="Optional angle / interests")
    assignment_type: AssignmentType = "essay"


class ScoutFinding(BaseModel):
    title: str
    summary: str
    url: Optional[str] = None
    hook: str = Field("", description="Why this is a compelling real-world hook for a student")


class ScoutReport(BaseModel):
    context: str = Field(..., description="Synthesized current context of the topic")
    findings: list[ScoutFinding] = []
    debates: list[str] = Field([], description="Live debates / tensions in the field")


class IdeaCandidate(BaseModel):
    id: str
    title: str
    statement: str = Field(..., description="Thesis statement (uni) or guiding question (HS)")
    why_it_matters: str
    angle: str
    scope: str
    difficulty: Literal["approachable", "moderate", "ambitious"] = "moderate"


class MindMapNode(BaseModel):
    id: str
    label: str
    type: Literal["thesis", "question", "argument", "evidence", "counter"] = "argument"
    parent: Optional[str] = None
    prompt: str = Field("", description="The 'keep thinking' prompt attached to this node")
    source_id: Optional[str] = Field(None, description="Cross-link to a Source, for evidence nodes")


class MindMap(BaseModel):
    nodes: list[MindMapNode] = []


class Source(BaseModel):
    id: str
    kind: Literal["article", "book", "paper", "web"] = "article"
    title: str
    authors: str = ""
    year: str = ""
    citation: str = Field("", description="Formatted citation (APA/MLA for uni, plain for HS)")
    url: Optional[str] = None
    credibility: Literal["high", "medium", "unverified"] = "medium"
    why: str = Field("", description="One-line: why this source matters to the idea")


class VideoScene(BaseModel):
    n: int
    visual: str = Field(..., description="What is on screen")
    narration: str = Field(..., description="Voiceover line")
    seconds: int = 8


class VideoSummary(BaseModel):
    title: str
    hook: str
    scenes: list[VideoScene] = []
    total_seconds: int = 60


class IdeaResult(BaseModel):
    """The full payload for a chosen idea."""
    idea: IdeaCandidate
    mind_map: MindMap
    sources: list[Source] = []
    video: VideoSummary


# --- API request/response envelopes ---

class GenerateIdeasResponse(BaseModel):
    scout: ScoutReport
    candidates: list[IdeaCandidate]


class BuildRequest(BaseModel):
    brief: Brief
    scout: ScoutReport
    idea: IdeaCandidate


class MoreIdeasRequest(BaseModel):
    brief: Brief
    scout: ScoutReport


class RefineRequest(BaseModel):
    brief: Brief
    idea: IdeaCandidate
    nudge: str = Field(..., description="How the student wants the idea changed")


# --- Corpus search (the "Corpus" tab): semantic search over ThesisSifu's
# Qdrant corpus of ~7.1M OpenAlex papers, embedded with bge-m3. IdeaSifu proxies
# to ThesisSifu's /search; the corpus payload only has title + openalex_id. ---

class CorpusSearchRequest(BaseModel):
    query: str = Field(..., description="Free-text query, any language (bge-m3 is multilingual)")
    top_k: int = Field(20, ge=1, le=50, description="Number of results to return")


class CorpusHit(BaseModel):
    title: str
    openalex_id: Optional[str] = None
    score: float = Field(..., description="Cosine similarity (0-1); higher = closer")


class CorpusSearchResponse(BaseModel):
    status: str = "ok"
    count: int = 0
    results: list[CorpusHit] = []
    message: Optional[str] = None


# --- The Dojo: a written-up sample thesis, one chapter at a time. ---
# The student fills in their research questions (the required gate); every other
# section is then written up on demand as a capped, sample writeup that directly
# answers those questions. Examples/sources are pulled from ThesisSifu's corpus
# so the writeup is grounded in real literature. Output language is the student's
# choice (BM/EN).

DojoDegree = Literal["undergraduate", "masters", "phd"]
DojoLang = Literal["en", "bm"]
# The chapters/sections the Dojo writes up. `research_questions` is student-filled;
# all others are generatable.
DojoSection = Literal[
    "title",
    "research_questions",
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
]


class DojoGenerateRequest(BaseModel):
    """Generate one sample thesis section, grounded in the corpus."""
    section: DojoSection = Field(..., description="Which section to write")
    degree: DojoDegree = "undergraduate"
    language: DojoLang = Field("en", description="Output language: 'en' or 'bm'")
    topic: str = Field("", description="Working thesis title/topic (optional)")
    research_questions: str = Field(
        ..., description="The student's research questions — the required input"
    )
    notes: str = Field(
        "", description="Optional: what the student briefly wants this section to cover"
    )
    pro: bool = Field(False, description="Pro tier: 3× word cap, paid model")
    session_token: Optional[str] = Field(
        None, description="Anonymous session token; if provided, Dojo quota is checked and decremented"
    )


class DojoCorpusExample(BaseModel):
    title: str
    openalex_id: Optional[str] = None
    score: float = 0.0
    # Enriched from OpenAlex (best-effort; blank if the lookup failed).
    authors: str = Field("", description="Formatted author list, APA order")
    year: Optional[int] = None
    venue: str = Field("", description="Journal / source name")
    doi: Optional[str] = Field(None, description="DOI URL, if the record has one")
    reference: str = Field("", description="Full APA-style citation, ready to render")
    intext: str = Field("", description="APA in-text citation form, e.g. '(Tan & Lim, 2022)'")
    abstract: str = Field("", description="Abstract snippet (~180 words) for critical grounding")


class DojoSectionResult(BaseModel):
    section: DojoSection
    heading: str = Field(..., description="The section's title in the chosen language")
    content: str = Field(..., description="A capped, sample write-up of the section (markdown)")
    corpus_examples: list[DojoCorpusExample] = Field(
        [], description="Real papers from the ThesisSifu corpus that informed the writeup"
    )
    language: DojoLang = "en"
    word_count: int = 0


# --- Community / social feature ---

ContributionType = Literal["challenge", "extend", "source"]


class SessionInfo(BaseModel):
    token: str
    credits: int = 0
    dojo_quota: int = 3


class SessionInitRequest(BaseModel):
    token: str


class ShareIdeaRequest(BaseModel):
    session_token: str
    idea: IdeaCandidate


class SharedIdea(BaseModel):
    id: str
    title: str
    statement: str
    angle: str
    shared_at: str
    contribution_count: int = 0


class ContributionItem(BaseModel):
    id: str
    type: ContributionType
    text: str
    quality_ok: bool
    credits_awarded: int
    created_at: str


class SharedIdeaDetail(BaseModel):
    id: str
    title: str
    statement: str
    angle: str
    shared_at: str
    contribution_count: int = 0
    contributions: list[ContributionItem] = []


class ContributionRequest(BaseModel):
    idea_id: str
    contributor_token: str
    type: ContributionType
    text: str


class ContributionResult(BaseModel):
    id: str
    credits_awarded: int
    quality_ok: bool
    quality_reason: str
    new_credits: int


class CommunityFeedResponse(BaseModel):
    ideas: list[SharedIdea]
    total: int


# --- Data Analysis (DataSifu in the Dojo) ---

class AnalysisMethod(BaseModel):
    name: str
    rationale: str
    chosen: bool = False


class GroupStat(BaseModel):
    group: str
    n: int
    mean: float = 0.0
    sd: float = 0.0
    median: float = 0.0


class DataStructure(BaseModel):
    rows: int
    columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    text_columns: list[str]


class QuantitativeResult(BaseModel):
    test_name: str
    variables: list[str] = []
    group_stats: list[GroupStat] = []
    test_statistic_label: str = ""
    test_statistic_value: Optional[float] = None
    p_value: Optional[float] = None
    significant: bool = False
    effect_size_label: str = ""
    effect_size_value: Optional[float] = None
    effect_size_interpretation: str = ""
    post_hoc: list[dict] = []
    normality_used: bool = False
    normality_note: str = ""


class QualTheme(BaseModel):
    name: str
    description: str
    frequency: int = 0
    quotes: list[str] = []


class DataAnalysisResponse(BaseModel):
    data_type: Literal["quantitative", "qualitative", "mixed"]
    detected_structure: DataStructure
    recommended_methods: list[AnalysisMethod] = []
    quantitative_results: Optional[QuantitativeResult] = None
    qualitative_themes: Optional[list[QualTheme]] = None
    interpretation: str = ""
    qualitative_summary: str = ""
    language: DojoLang = "en"
    word_count: int = 0


# --- FormatSifu: journal format matching ---

class JournalStyle(BaseModel):
    chapter_label_format: str
    subheading_format: str
    numbering_scheme: str
    section_order: list[str] = []
    abstract_present: bool = True
    keywords_present: bool = True
    reference_style: str = ""
    formatting_notes: str = ""


class FormatIssue(BaseModel):
    location: str
    current: str
    expected: str
    severity: str  # 'high' | 'medium' | 'low'
    suggestion: str


class HeadingReplacement(BaseModel):
    original: str
    replacement: str
    level: int


class FormatMatchResponse(BaseModel):
    journal_style: JournalStyle
    issues: list[FormatIssue] = []
    missing_sections: list[str] = []
    heading_map: list[HeadingReplacement] = []
    reformatted_outline: str = ""
    summary: str = ""
    match_score: int = 0
