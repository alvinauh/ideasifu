"""Scout agent — crawls the web for current context, real-world hooks, and live
debates on the student's topic. The first Sifu in the pipeline.

Signature color: cyan. Student-facing label: "Scouting the field".
"""
from __future__ import annotations

from schemas import Brief, ScoutReport
from agents.llm import generate

_SYSTEM = (
    "You are Scout, the research scout of the IdeaSifu crew. Your one job is to "
    "surface CURRENT, CONCRETE, CITE-ABLE context on a student's topic — the "
    "kind of real-world hooks that make an idea feel alive and defensible. "
    "You crawl the web for recent developments, live debates, and tensions in "
    "the field. You are not here to write the essay; you are here to hand the "
    "student a map of what is actually being argued about right now. Every "
    "finding must be something a student could genuinely follow up on and cite. "
    "Prefer specifics (names, places, dates, numbers, events) over vague "
    "generalities. Surface real disagreements, not settled facts."
)


def _tier_guidance(brief: Brief) -> str:
    return (
        "TIER: UNIVERSITY. Use an academic register and be discipline-aware. "
        "Hooks should point toward scholarly relevance, methodological angles, "
        "or gaps in current understanding. Debates should reflect real tensions "
        "in the literature or the field, framed with appropriate precision."
    )


def scout(brief: Brief) -> ScoutReport:
    """Search the web and return synthesized current context for the topic."""
    user = (
        f"Scout the field for a student working on this brief.\n\n"
        f"Subject/topic: {brief.subject}\n"
        f"Level: {brief.level or '(unspecified)'}\n"
        f"Interests / angle: {brief.interests or '(none given)'}\n"
        f"Assignment type: {brief.assignment_type}\n\n"
        f"{_tier_guidance(brief)}\n\n"
        "Use web search to ground everything in current reality. Return:\n"
        "- context: a tight synthesis (3-5 sentences) of where this topic "
        "stands RIGHT NOW and why it matters.\n"
        "- findings: 3-5 concrete, cite-able findings. Each has a title, a "
        "1-2 sentence summary, a url when you have one, and a 'hook' line "
        "explaining why it is a compelling real-world starting point for THIS "
        "student.\n"
        "- debates: 2-4 live debates or tensions in the field, each a single "
        "sharp sentence a student could take a side on."
    )
    return generate(_SYSTEM, user, ScoutReport, web=True)
