"""Orchestrator — runs the IdeaSifu agent pipeline with automatic mock fallback.

For every stage: if a live Claude client is configured, try the real agent; on
LLMUnavailable OR any other exception, log a warning and serve the deterministic
mock instead. This keeps the whole app running end-to-end with zero credentials.

Pipeline (per DESIGN.md section 3):
    Scout -> Ideator (fan-out to 3) -> [student picks]
          -> Cartographer + Librarian + Director -> IdeaResult
"""
from __future__ import annotations

import logging

from schemas import (
    Brief,
    DojoCorpusExample,
    DojoGenerateRequest,
    DojoSectionResult,
    IdeaCandidate,
    IdeaResult,
    RefineRequest,
    ScoutReport,
)

from agents import scout as scout_agent
from agents import ideator as ideator_agent
from agents import cartographer as cartographer_agent
from agents import librarian as librarian_agent
from agents import director as director_agent
from agents import sensei as sensei_agent
from agents.llm import LLMUnavailable, is_live

import mocks

log = logging.getLogger("ideasifu.orchestrator")


def _run(stage: str, live_fn, mock_fn):
    """Try the live agent when a client is configured; fall back to the mock."""
    if is_live():
        try:
            return live_fn()
        except LLMUnavailable:
            log.warning("[%s] LLM unavailable — using mock.", stage)
        except Exception as exc:  # noqa: BLE001 — deliberate broad fallback
            log.warning("[%s] live agent failed (%s) — using mock.", stage, exc)
    else:
        log.info("[%s] no live LLM — using mock.", stage)
    return mock_fn()


def run_scout(brief: Brief) -> ScoutReport:
    return _run(
        "scout",
        lambda: scout_agent.scout(brief),
        lambda: mocks.mock_scout(brief),
    )


def run_ideate(brief: Brief, scout: ScoutReport) -> list[IdeaCandidate]:
    return _run(
        "ideate",
        lambda: ideator_agent.ideate(brief, scout),
        lambda: mocks.mock_candidates(brief),
    )


def build_idea(brief: Brief, idea: IdeaCandidate) -> IdeaResult:
    """Run Cartographer + Librarian + Director and assemble the full payload."""
    mind_map = _run(
        "cartographer",
        lambda: cartographer_agent.map_idea(brief, idea),
        lambda: mocks.mock_mindmap(brief, idea),
    )
    sources = _run(
        "librarian",
        lambda: librarian_agent.gather(brief, idea),
        lambda: mocks.mock_sources(brief, idea),
    )
    video = _run(
        "director",
        lambda: director_agent.film(brief, idea),
        lambda: mocks.mock_video(brief, idea),
    )
    return IdeaResult(idea=idea, mind_map=mind_map, sources=sources, video=video)


def refine_idea(req: RefineRequest) -> IdeaCandidate:
    """Re-run ideator-style refinement, nudged toward what the student wants."""

    def _mock() -> IdeaCandidate:
        idea = req.idea.model_copy(deep=True)
        nudge = req.nudge.strip()
        idea.title = f"{idea.title} (refined)"
        idea.statement = f"{idea.statement} — now taking into account: {nudge}."
        idea.angle = f"{idea.angle}, adjusted for the student's nudge"
        return idea

    return _run(
        "refine",
        lambda: _refine_live(req),
        _mock,
    )


def run_dojo(
    req: DojoGenerateRequest,
    corpus: list[DojoCorpusExample],
) -> DojoSectionResult:
    """Write one sample thesis section (Sensei), grounded in the corpus hits.

    The corpus search is done by the caller (main.py, which owns the async httpx
    client to ThesisSifu's /search) and passed in, so this stays synchronous like
    the rest of the pipeline. Falls back to a deterministic mock chapter.
    """
    return _run(
        "sensei",
        lambda: sensei_agent.write_section(req, corpus),
        lambda: mocks.mock_dojo(req, corpus),
    )


def _refine_live(req: RefineRequest) -> IdeaCandidate:
    """Ask the Ideator to regenerate a single candidate honoring the nudge."""
    from agents.llm import generate

    system = ideator_agent._SYSTEM  # reuse the Ideator persona
    tier = req.brief.tier
    tier_line = "TIER: UNIVERSITY — statement is a thesis with a research gap."
    user = (
        f"Refine this ONE idea according to the student's nudge, keeping it a "
        f"defensible starting point (not a finished answer).\n\n"
        f"Subject: {req.brief.subject}\n"
        f"Current title: {req.idea.title}\n"
        f"Current statement: {req.idea.statement}\n"
        f"Current angle: {req.idea.angle}\n"
        f"Current scope: {req.idea.scope}\n"
        f"Current difficulty: {req.idea.difficulty}\n\n"
        f"STUDENT NUDGE: {req.nudge}\n\n"
        f"{tier_line}\n\n"
        f"Return a single IdeaCandidate JSON object (keep id "
        f"'{req.idea.id}') with the refined title, statement, why_it_matters, "
        f"angle, scope, and difficulty."
    )
    refined = generate(system, user, IdeaCandidate)
    refined.id = req.idea.id
    return refined
