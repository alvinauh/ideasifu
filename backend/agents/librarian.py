"""Librarian agent — attaches citations, references and books to a chosen idea,
grades each source's credibility, and explains why it matters.

Sources are presented as things to READ, not things to quote blindly.

Signature color: amber. Student-facing label: "Gathering sources".
"""
from __future__ import annotations

from pydantic import BaseModel

from schemas import Brief, IdeaCandidate, Source
from agents.llm import generate


class _Sources(BaseModel):
    items: list[Source]


_SYSTEM = (
    "You are Librarian, the source-gatherer of the IdeaSifu crew. You use the "
    "web to find real, readable sources for a student's chosen idea. Rules:\n"
    "- Return 4-6 sources, and AT LEAST ONE must be a book (kind='book').\n"
    "- Mix credibility honestly: mark each 'high', 'medium', or 'unverified'. "
    "Do not inflate credibility.\n"
    "- Each source has a one-line `why`: why THIS source matters to THIS idea.\n"
    "- Sources are things to READ and evaluate, not things to quote blindly. "
    "Never fabricate a citation you are not reasonably confident exists; if "
    "unsure, mark it 'unverified' and say so in `why`.\n"
    "Give real authors, years and URLs where you can."
)


def _tier_guidance(brief: Brief) -> str:
    return (
        "TIER: UNIVERSITY. Citation format is APA. Write `citation` as a "
        "properly formatted APA reference (include DOI/URL where available). "
        "Favor a mix of seminal and recent scholarly work: peer-reviewed "
        "papers, academic books, and authoritative reports."
    )


def gather(brief: Brief, idea: IdeaCandidate) -> list[Source]:
    """Find 4-6 tier-appropriate sources (incl. >=1 book) for the idea."""
    user = (
        f"Gather sources for this chosen idea.\n\n"
        f"Title: {idea.title}\n"
        f"Statement: {idea.statement}\n"
        f"Angle: {idea.angle}\n"
        f"Scope: {idea.scope}\n"
        f"Subject: {brief.subject}\n\n"
        f"{_tier_guidance(brief)}\n\n"
        "Use web search to ground the sources in reality. Return a JSON object "
        '{"items": [ ... 4-6 Source objects ... ]}. Give stable ids '
        "'s1', 's2', ... Each Source needs: id, kind ('article'|'book'|"
        "'paper'|'web'), title, authors, year, citation, url (if known), "
        "credibility ('high'|'medium'|'unverified'), and why. At least one "
        "must have kind='book'."
    )
    result = generate(_SYSTEM, user, _Sources, web=True)
    sources = result.items[:6]
    for i, src in enumerate(sources, start=1):
        src.id = f"s{i}"
    return sources
