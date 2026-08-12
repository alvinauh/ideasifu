"""Ideator agent — turns Scout's raw context into 3 distinct, tier-calibrated
idea candidates. The student picks one; that pick is a teaching act.

Signature color: violet (primary). Student-facing label: "Shaping ideas".
"""
from __future__ import annotations

from pydantic import BaseModel

from schemas import Brief, IdeaCandidate, ScoutReport
from agents.llm import generate


class _Candidates(BaseModel):
    """Wrapper so the model returns a top-level object it can validate."""

    items: list[IdeaCandidate]


_SYSTEM = (
    "You are Ideator, the idea-shaper of the IdeaSifu crew. You take a scout's "
    "field report and forge exactly THREE distinct, defensible starting points "
    "for a student's assignment. These are NOT finished theses to copy — they "
    "are launch pads the student must defend, refine and check. Make the three "
    "genuinely different from each other in angle and scope, not three flavors "
    "of the same idea. Give each an honest difficulty rating so the student can "
    "choose with eyes open. You scaffold thinking; you never hand over writing."
)


def _tier_guidance(brief: Brief) -> str:
    if brief.tier == "highschool":
        return (
            "TIER: HIGH SCHOOL. Each idea's `statement` must be a GUIDING "
            "QUESTION (something open and answerable, not a yes/no). "
            "`why_it_matters` should connect to the student's world in plain, "
            "encouraging language. `scope` should describe a project a "
            "secondary student can realistically pull off. Keep vocabulary "
            "concrete."
        )
    return (
        "TIER: UNIVERSITY. Each idea's `statement` must be a THESIS STATEMENT "
        "(an arguable claim). `why_it_matters` should articulate the RESEARCH "
        "GAP it addresses. `scope` should define boundaries with methodology "
        "awareness (what's in, what's out, how it could be investigated). Use "
        "an academic register."
    )


def ideate(brief: Brief, scout: ScoutReport) -> list[IdeaCandidate]:
    """Return exactly 3 distinct, tier-calibrated idea candidates."""
    findings = "\n".join(
        f"- {f.title}: {f.summary} (hook: {f.hook})" for f in scout.findings
    ) or "(no findings)"
    debates = "\n".join(f"- {d}" for d in scout.debates) or "(no debates listed)"

    user = (
        f"Shape ideas for this student.\n\n"
        f"Subject/topic: {brief.subject}\n"
        f"Level: {brief.level or '(unspecified)'}\n"
        f"Interests / angle: {brief.interests or '(none given)'}\n"
        f"Assignment type: {brief.assignment_type}\n\n"
        f"SCOUT CONTEXT:\n{scout.context}\n\n"
        f"SCOUT FINDINGS:\n{findings}\n\n"
        f"LIVE DEBATES:\n{debates}\n\n"
        f"{_tier_guidance(brief)}\n\n"
        "Produce EXACTLY 3 candidates as a JSON object of the form "
        '{"items": [ ... 3 IdeaCandidate objects ... ]}. '
        "Give them stable ids 'idea-1', 'idea-2', 'idea-3'. Each needs: id, "
        "title (short, memorable), statement, why_it_matters, angle (the "
        "distinctive lens), scope, and difficulty (one of 'approachable', "
        "'moderate', 'ambitious'). Make the three differ in difficulty and "
        "angle so the choice is a real one."
    )
    result = generate(_SYSTEM, user, _Candidates)
    candidates = result.items[:3]
    # Enforce stable ids regardless of what the model returned.
    for i, cand in enumerate(candidates, start=1):
        cand.id = f"idea-{i}"
    return candidates
