"""Director agent — writes a short narrated video summary (script + storyboard)
of the contextualized idea. Doubles as a revision aid.

Signature color: pink. Student-facing label: "Filming the summary".
"""
from __future__ import annotations

from schemas import Brief, IdeaCandidate, VideoSummary
from agents.llm import generate

_SYSTEM = (
    "You are Director, the storyteller of the IdeaSifu crew. You write a short "
    "narrated video summary of a student's chosen idea — a script plus a scene "
    "storyboard the student can watch to internalize the idea. Each scene has a "
    "visual (what's on screen), narration (the voiceover line), and a length in "
    "seconds. The video should teach the idea as a piece of thinking to defend, "
    "not sell it as a finished answer. Keep narration crisp and speakable. "
    "Make total_seconds roughly equal to the sum of the scene seconds."
)


def _tier_guidance(brief: Brief) -> str:
    if brief.tier == "highschool":
        return (
            "TIER: HIGH SCHOOL. Target 45-60 seconds total, 5-7 scenes. "
            "Story-led and plain-language: open with a relatable hook, walk "
            "through the guiding question warmly, end by inviting the student "
            "to go investigate. Encouraging tone."
        )
    return (
        "TIER: UNIVERSITY. Target 60-90 seconds total, 5-7 scenes. Structured "
        "and scholarly: state the thesis, frame the gap, sketch the argument "
        "and a counter-argument, close on what rigorous inquiry would look "
        "like. Precise, supervisor-like tone."
    )


def film(brief: Brief, idea: IdeaCandidate) -> VideoSummary:
    """Write a short narrated video summary for the chosen idea."""
    lo, hi = (45, 60) if brief.tier == "highschool" else (60, 90)
    user = (
        f"Film a short summary of this chosen idea.\n\n"
        f"Title: {idea.title}\n"
        f"Statement: {idea.statement}\n"
        f"Why it matters: {idea.why_it_matters}\n"
        f"Angle: {idea.angle}\n"
        f"Scope: {idea.scope}\n"
        f"Subject: {brief.subject}\n\n"
        f"{_tier_guidance(brief)}\n\n"
        "Return a VideoSummary with: title, hook (a one-line opener), scenes "
        "(5-7 VideoScene objects each with n starting at 1, visual, narration, "
        f"seconds), and total_seconds (~{lo}-{hi}, roughly the sum of the "
        "scene seconds)."
    )
    video = generate(_SYSTEM, user, VideoSummary)
    # Normalize scene numbering and total.
    for i, scene in enumerate(video.scenes, start=1):
        scene.n = i
    if video.scenes:
        video.total_seconds = sum(s.seconds for s in video.scenes)
    return video
