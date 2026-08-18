"""Assessor agent: judges whether a community contribution is substantive.

Returns a simple quality verdict. Called inline during POST /community/contribute —
a fast, cheap LLM call (non-web, small token budget). Falls back to a basic
heuristic when no LLM is configured (mock/demo mode).
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from agents.llm import LLMUnavailable, generate

log = logging.getLogger("ideasifu.assessor")

_TYPE_CRITERIA = {
    "challenge": (
        "A CHALLENGE must identify a specific assumption, limitation, logical gap, or "
        "counter-argument in the idea. It must explain WHY or HOW it is a problem. "
        "Simply saying 'I disagree' or 'this won't work' without specifics is NOT acceptable."
    ),
    "extend": (
        "An EXTEND must propose a specific, named angle, sub-topic, dimension, or related "
        "area that would genuinely enrich the idea. It must be concrete and actionable. "
        "Vague suggestions like 'you could add more context' are NOT acceptable."
    ),
    "source": (
        "A SOURCE must name a specific author, paper title, academic journal, or well-defined "
        "research area relevant to the idea. Simply saying 'there is research on this topic' "
        "or 'you should read more' is NOT acceptable."
    ),
}

_FILLER_STARTS = {
    "i agree", "great idea", "this is good", "good idea", "i agree with",
    "sounds good", "looks good", "nice idea", "nice work", "well done",
    "good work", "i like this", "this looks good",
}

_SYSTEM = """You are a quality assessor for a peer academic contribution tool.
Students contribute to each other's research ideas anonymously to earn credits.
Your job is to judge whether a contribution is substantive and genuinely helpful —
NOT whether you agree with it.

A contribution PASSES if it is:
- Specific (names something concrete, not vague platitudes)
- Relevant (clearly relates to the idea being discussed)
- Adds value beyond empty agreement, empty praise, or filler

A contribution FAILS if it is:
- Purely agreement or praise ("Great idea!", "I agree", "This is good")
- Too vague to act on ("you should add more", "there is research on this")
- Off-topic or incoherent
- Very short with no substance (fewer than ~15 meaningful words)

Be lenient — if in doubt, PASS it. The bar is "mildly helpful", not "excellent"."""


class AssessorVerdict(BaseModel):
    quality_ok: bool
    reason: str  # Short explanation shown to the contributor (1-2 sentences)


def assess(
    idea_title: str,
    idea_statement: str,
    contribution_type: str,
    contribution_text: str,
) -> AssessorVerdict:
    """Return a quality verdict for a community contribution."""
    criteria = _TYPE_CRITERIA.get(contribution_type, "")
    user = (
        f"IDEA TITLE: {idea_title}\n"
        f"IDEA STATEMENT: {idea_statement}\n\n"
        f"CONTRIBUTION TYPE: {contribution_type.upper()}\n"
        f"Criteria for this type: {criteria}\n\n"
        f"CONTRIBUTION TEXT:\n{contribution_text}\n\n"
        "Does this contribution meet the quality bar?"
    )
    try:
        return generate(_SYSTEM, user, AssessorVerdict, web=False, max_tokens=200)
    except LLMUnavailable:
        return _heuristic_verdict(contribution_text)


def _heuristic_verdict(text: str) -> AssessorVerdict:
    """Fallback when no LLM is available: simple length + filler check."""
    stripped = text.strip()
    normalized = stripped.lower()
    is_filler = (
        any(normalized.startswith(p) for p in _FILLER_STARTS)
        or len(stripped.split()) < 15
    )
    if is_filler:
        return AssessorVerdict(
            quality_ok=False,
            reason=(
                "Your contribution needs more specifics. Try explaining the 'why', "
                "naming a concrete example, or pointing to a real source."
            ),
        )
    return AssessorVerdict(quality_ok=True, reason="Contribution accepted.")
