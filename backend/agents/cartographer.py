"""Cartographer agent — builds the critical-thinking mind map for a chosen idea.

Per DESIGN.md section 5: a root thesis/question node, argument nodes, evidence
nodes, at least one counter node (always present — a map with no counters is a
red flag), and open question nodes. Every node's `prompt` is a "keep thinking"
question, never a period.

Signature color: teal/green. Student-facing label: "Mapping the thinking".
"""
from __future__ import annotations

from schemas import Brief, IdeaCandidate, MindMap, MindMapNode
from agents.llm import generate

_SYSTEM = (
    "You are Cartographer, the map-maker of the IdeaSifu crew. You turn a "
    "chosen idea into a navigable critical-thinking mind map. The map is the "
    "intellectual heart of the product, so it follows strict pedagogy:\n"
    "- Exactly ONE root node (type 'thesis') with parent=None.\n"
    "- Several 'argument' nodes hanging off the root (supporting lines of "
    "reasoning).\n"
    "- 'evidence' nodes under arguments (facts/data to go find and verify).\n"
    "- AT LEAST ONE 'counter' node — an objection or counter-argument. A map "
    "with no counters is a failure. Counters read as tension, deliberately.\n"
    "- One or more open 'question' nodes ('what if?' / 'what's missing?').\n"
    "CRUCIAL RULE: every single node's `prompt` field is a 'keep thinking' "
    "QUESTION, never a statement and never a period. Leaf nodes especially "
    "must pose 'How would you test this?' / 'Who disagrees, and why?'. You keep "
    "the student in an active, questioning posture. Ideas are starting points "
    "to defend, not conclusions to accept."
)


def _tier_guidance(brief: Brief) -> str:
    return (
        "TIER: UNIVERSITY. Root node type is 'thesis'. Use an academic "
        "register. Arguments are lines of reasoning, evidence points to "
        "sources/data to gather, counters are genuine scholarly objections. "
        "Prompts push methodological rigor, e.g. 'What data would falsify "
        "this claim?'"
    )


def map_idea(brief: Brief, idea: IdeaCandidate) -> MindMap:
    """Build a critical-thinking mind map for the chosen idea."""
    user = (
        f"Map the thinking for this chosen idea.\n\n"
        f"Title: {idea.title}\n"
        f"Statement: {idea.statement}\n"
        f"Why it matters: {idea.why_it_matters}\n"
        f"Angle: {idea.angle}\n"
        f"Scope: {idea.scope}\n"
        f"Subject: {brief.subject}\n\n"
        f"{_tier_guidance(brief)}\n\n"
        "Return a MindMap: a `nodes` list of 8-12 nodes. Use stable ids "
        "'n1', 'n2', 'n3', ... The root is 'n1' with parent=null. Set every "
        "other node's `parent` to the id of its parent node so the graph is "
        "connected. Include: 1 root, 3-4 arguments, 3-4 evidence nodes "
        "(children of arguments), AT LEAST 1 counter, and 1-2 open questions. "
        "Every node MUST have a `prompt` phrased as a keep-thinking question "
        "ending in a question mark. Set `type` correctly on each node."
    )
    mind_map = generate(_SYSTEM, user, MindMap)
    _ensure_valid(mind_map, brief, idea)
    return mind_map


def _ensure_valid(mind_map: MindMap, brief: Brief, idea: IdeaCandidate) -> None:
    """Guardrail: guarantee a root and at least one counter node exist."""
    if not mind_map.nodes:
        root_type = "thesis"
        mind_map.nodes.append(
            MindMapNode(
                id="n1",
                label=idea.title,
                type=root_type,
                parent=None,
                prompt="Where would you start defending this?",
            )
        )
    # Ensure a root (a node with parent=None) exists.
    if not any(n.parent is None for n in mind_map.nodes):
        mind_map.nodes[0].parent = None
    # Ensure at least one counter node exists.
    if not any(n.type == "counter" for n in mind_map.nodes):
        root_id = next((n.id for n in mind_map.nodes if n.parent is None), "n1")
        mind_map.nodes.append(
            MindMapNode(
                id=f"n{len(mind_map.nodes) + 1}",
                label="The strongest objection",
                type="counter",
                parent=root_id,
                prompt="Who would disagree with this, and what is their best point?",
            )
        )
