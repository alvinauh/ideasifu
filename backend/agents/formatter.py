"""FormatSifu agent — compares a student's document against a journal's format.

Given structural outlines extracted from:
  1. A reference journal article (PDF or DOCX) — the target format
  2. The student's document (DOCX) — what needs to change

The agent extracts the journal's formatting conventions (heading style, chapter
numbering scheme, section order) then walks the student's document to produce
a list of specific, actionable issues and suggestions.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from agents.llm import generate


class HeadingReplacement(BaseModel):
    original: str = Field(..., description="Exact heading text as it appears in the student's document")
    replacement: str = Field(..., description="Corrected heading text that matches the journal's format")
    level: int = Field(..., description="Target heading level: 1 for chapter, 2 for section, 3 for subsection")


class _JournalStyle(BaseModel):
    chapter_label_format: str = Field(
        ...,
        description="How main chapters are labeled, e.g. 'Chapter 1: Title', '1. Title', 'CHAPTER 1', or 'ALL CAPS TITLE'",
    )
    subheading_format: str = Field(
        ...,
        description="How sub-sections are labeled, e.g. '1.1 Sub-section Title', '1.1.1 Title', or 'bold unnumbered'",
    )
    numbering_scheme: str = Field(
        ...,
        description="Numbering style used: 'arabic', 'roman', 'alphanumeric', 'none'",
    )
    section_order: list[str] = Field(
        ...,
        description="Sections/chapters in the order they appear in the journal",
    )
    abstract_present: bool = Field(True)
    keywords_present: bool = Field(True)
    reference_style: str = Field(
        "", description="Citation/reference style, e.g. 'APA', 'IEEE', 'Vancouver', or 'unknown'"
    )
    formatting_notes: str = Field(
        "", description="Other notable formatting conventions (e.g. all headings bold, section numbering restarts per chapter)"
    )


class FormatIssue(BaseModel):
    location: str = Field(..., description="Which heading or section has the issue, e.g. 'Chapter 2 heading'")
    current: str = Field(..., description="Exact text or style as it appears in the student's document")
    expected: str = Field(..., description="What it should be per the journal's format")
    severity: str = Field(..., description="'high' (structural), 'medium' (labeling), or 'low' (cosmetic)")
    suggestion: str = Field(..., description="Specific, concrete fix: tell the student exactly what to type or change")


class _FormatterOutput(BaseModel):
    journal_style: _JournalStyle
    issues: list[FormatIssue] = Field(
        [], description="All formatting mismatches found in the student's document, most severe first"
    )
    missing_sections: list[str] = Field(
        [], description="Sections present in the journal that are absent from the student's document"
    )
    heading_map: list[HeadingReplacement] = Field(
        [],
        description=(
            "One entry per heading in the student's document that needs changing. "
            "original must match the heading text exactly as it appears. "
            "replacement is the corrected text. level is the target Word heading level (1/2/3)."
        ),
    )
    reformatted_outline: str = Field(
        "", description="The student's document headings rewritten to match the journal format — show what the corrected structure should look like"
    )
    summary: str = Field(
        ..., description="2-3 sentence overall assessment: how well the document matches and the top priorities"
    )
    match_score: int = Field(
        ..., description="Format compliance score 0-100, where 100 = perfect match to the journal"
    )


class FormatMatchResponse(BaseModel):
    journal_style: _JournalStyle
    issues: list[FormatIssue] = []
    missing_sections: list[str] = []
    heading_map: list[HeadingReplacement] = []
    reformatted_outline: str = ""
    summary: str = ""
    match_score: int = 0


_SYSTEM = """\
You are FormatSifu, an expert in academic document formatting.

You receive the structural outline of two documents:
  1. REFERENCE JOURNAL — this defines the required target format.
  2. STUDENT DOCUMENT — this must be checked and corrected against the journal.

CRITICAL RULE — confirmed-present sections:
  The student document outline may begin with a line like:
    [KEY SECTIONS CONFIRMED PRESENT: ABSTRACT, KEYWORDS, REFERENCES, ...]
  Any section listed there IS present in the student's document even if it does
  not appear as a heading in the outline (it may use a non-heading style).
  You MUST NOT list a confirmed-present section in missing_sections.

Your tasks:
  A. Extract the journal's formatting conventions precisely (heading hierarchy,
     numbering scheme, section order, abstract/keywords, citation style).
  B. Walk every heading and section in the student's document and find every
     mismatch against the journal's conventions.
  C. For each mismatch write a specific, actionable suggestion — show the
     student EXACTLY what to change, not general advice.
  D. List sections from the journal that are absent from the student document.
     Only include a section in missing_sections if you are certain it is absent
     (i.e. it is NOT listed in KEY SECTIONS CONFIRMED PRESENT and NOT visible
     in the outline).
  E. Produce a heading_map: for EVERY heading in the student's document that
     needs a text or level change, emit one HeadingReplacement with the exact
     original text, the corrected replacement text, and the target level (1/2/3).
     Headings that are already correct may be omitted.
  F. Produce a "reformatted outline": rewrite the student's heading list as it
     should look after all fixes are applied.
  G. Give a match_score (0-100) and a 2-3 sentence summary.

Be precise. A student must be able to apply every suggestion without further
clarification. Number formatting is a high-severity issue; minor label differences
are medium; cosmetic things like bold/italic are low."""


class _ApaOut(BaseModel):
    references: list[str]


_APA_SYSTEM = """\
You are an expert in APA 7th edition citation formatting.
Reformat each reference entry to comply precisely with APA 7th edition.
Return references in the SAME ORDER, one per list entry.
Do not add, remove, merge, or split entries.
Preserve every piece of information (authors, year, title, journal, volume, issue, pages, DOI/URL).

Key APA 7th rules:
- Authors: Surname, Initials. List ALL authors up to 20; for 21+ list first 19 … last author.
- Year in parentheses after authors: (2020).
- Article title: sentence case (capitalise first word and proper nouns only).
- Journal name: Title Case, italicised in the reference list.
- Volume: italicised. Issue: (non-italicised) in parentheses immediately after volume.
- No "pp." for journal page ranges; use plain numbers e.g. 123-145.
- DOI formatted as: https://doi.org/xxxxx
- Book: Author(s). (Year). Title in sentence case. Publisher.
- Chapter: Author(s). (Year). Chapter title. In Editor(s) (Eds.), Book title (pp. xx-xx). Publisher."""


def reformat_references_apa(raw_refs: list[str]) -> list[str]:
    """Reformat a list of reference strings to APA 7th edition via LLM."""
    if not raw_refs:
        return raw_refs
    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(raw_refs))
    user = (
        "Reformat every reference below to APA 7th edition. "
        "Return them in the SAME ORDER, one string per entry.\n\n"
        f"{numbered}"
    )
    try:
        out = generate(_APA_SYSTEM, user, _ApaOut, max_tokens=4096)
        if len(out.references) == len(raw_refs):
            return out.references
    except Exception:
        pass
    return raw_refs  # fallback: keep originals on any error


def analyze(journal_outline: str, document_outline: str, journal_is_spec: bool = False) -> FormatMatchResponse:
    """Compare document structure to journal format and return issues + suggestions."""
    if journal_is_spec:
        ref_label = "FORMATTING SPECIFICATION (plain-language style guide — treat every rule stated here as authoritative)"
        task_line = (
            "Analyze the student's document against every formatting rule stated in the specification above. "
            "The specification is the authoritative source of truth — do not infer conventions; read them directly. "
            "Identify all mismatches with specific suggestions, list missing sections, "
            "produce the corrected outline, and give a match score."
        )
    else:
        ref_label = "REFERENCE JOURNAL STRUCTURE"
        task_line = (
            "Analyze the student's document against the journal's formatting conventions. "
            "Identify all mismatches with specific suggestions, list missing sections, "
            "produce the corrected outline, and give a match score."
        )

    user = (
        f"{ref_label}:\n"
        f"{journal_outline}\n\n"
        "---\n\n"
        "STUDENT DOCUMENT STRUCTURE:\n"
        f"{document_outline}\n\n"
        "---\n\n"
        f"{task_line}"
    )

    out = generate(_SYSTEM, user, _FormatterOutput, max_tokens=8192)
    return FormatMatchResponse(
        journal_style=out.journal_style,
        issues=out.issues,
        missing_sections=out.missing_sections,
        heading_map=out.heading_map,
        reformatted_outline=out.reformatted_outline,
        summary=out.summary,
        match_score=min(100, max(0, out.match_score)),
    )
