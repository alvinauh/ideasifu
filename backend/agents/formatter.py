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

Your tasks:
  A. Extract the journal's formatting conventions precisely (heading hierarchy,
     numbering scheme, section order, abstract/keywords, citation style).
  B. Walk every heading and section in the student's document and find every
     mismatch against the journal's conventions.
  C. For each mismatch write a specific, actionable suggestion — show the
     student EXACTLY what to change, not general advice.
  D. List sections from the journal that are absent from the student document.
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


def analyze(journal_outline: str, document_outline: str) -> FormatMatchResponse:
    """Compare document structure to journal format and return issues + suggestions."""
    user = (
        "REFERENCE JOURNAL STRUCTURE:\n"
        f"{journal_outline}\n\n"
        "---\n\n"
        "STUDENT DOCUMENT STRUCTURE:\n"
        f"{document_outline}\n\n"
        "---\n\n"
        "Analyze the student's document against the journal's formatting conventions. "
        "Identify all mismatches with specific suggestions, list missing sections, "
        "produce the corrected outline, and give a match score."
    )

    out = generate(_SYSTEM, user, _FormatterOutput, max_tokens=4000)
    return FormatMatchResponse(
        journal_style=out.journal_style,
        issues=out.issues,
        missing_sections=out.missing_sections,
        heading_map=out.heading_map,
        reformatted_outline=out.reformatted_outline,
        summary=out.summary,
        match_score=min(100, max(0, out.match_score)),
    )
