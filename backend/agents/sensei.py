"""Sensei agent — the Dojo's thesis writer.

Given a student's research questions (the required input) and an optional brief
of what they want to cover, Sensei writes a capped, *sample* write-up for one
thesis section that directly answers those questions — calibrated to the degree
level (undergraduate / masters / PhD) and written in the student's chosen
language (English or Bahasa Melayu).

It is handed real papers from the ThesisSifu corpus (fetched by the orchestrator
via ThesisSifu's /search) and is told to weave those examples/sources into the
writeup, so the draft is grounded in genuine literature rather than invented.

The output is CAPPED to a representative sample of the section — a focused,
well-structured write-up, not a whole padded chapter. Sensei writes the section
up for the student; it does not explain how to write it.

Student-facing label: "Sensei is writing the chapter".
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from schemas import (
    DojoCorpusExample,
    DojoGenerateRequest,
    DojoSectionResult,
)
from agents.llm import generate


class _SenseiOutput(BaseModel):
    """Minimal model Sensei is asked to return. Kept to just the writeup so the
    schema handed to the LLM is tiny — weaker models (Groq 8B) then can't echo a
    huge schema or hallucinate corpus_examples. The app owns every other field."""
    content: str = Field(..., description="The sample writeup as markdown prose")
    word_count: int = 0

# Per-section metadata: bilingual heading + what the section must do + the word
# cap for the sample. Caps keep the LLM to a "full chapter sample", not a whole
# chapter — enough to model the structure and register without doing the work.
SECTIONS: dict[str, dict] = {
    "title": {
        "heading_en": "Thesis Title",
        "heading_bm": "Tajuk Tesis",
        "purpose": (
            "Propose exactly 3 candidate thesis titles. Each title MUST satisfy ALL "
            "of the following criteria:\n"
            "  1. SPECIFICITY — names the exact key construct or phenomenon under "
            "study (not a vague umbrella term).\n"
            "  2. POPULATION / CONTEXT — identifies who or where (e.g. 'among "
            "secondary school teachers in Malaysia', 'in public universities', "
            "'among adolescents with autism').\n"
            "  3. RESEARCH ORIENTATION — hints at approach only when it adds meaning "
            "(e.g. 'A Qualitative Exploration', 'A Mixed-Methods Analysis'); omit if "
            "obvious from the topic.\n"
            "  4. PRECISION — 10 to 20 words; no filler openers ('A Study of', "
            "'An Investigation into') unless they add necessary nuance; use a colon "
            "to separate the conceptual hook from scope/context.\n"
            "  5. DEGREE CALIBRATION — vocabulary and framing appropriate to the "
            "stated degree level (undergraduate titles are clear and direct; PhD "
            "titles assert an original contribution).\n"
            "  6. FULL COVERAGE — collectively addresses all research questions, not "
            "just the first one.\n\n"
            "After the three titles, write a 'Recommended' section that: names which "
            "title you recommend, explains in 3–4 sentences WHY it best captures the "
            "study's scope and contribution, identifies the specific weakness of each "
            "of the two non-recommended titles, and notes any revision that would "
            "strengthen the recommended title further."
        ),
        "words": 320,
    },
    "introduction": {
        "heading_en": "Chapter 1: Introduction",
        "heading_bm": "Bab 1: Pengenalan",
        "purpose": (
            "Set the background and context, state the problem, establish the "
            "significance and scope, and lead naturally into the research questions."
        ),
        "words": 700,
    },
    "literature_review": {
        "heading_en": "Chapter 2: Literature Review",
        "heading_bm": "Bab 2: Tinjauan Literatur",
        "purpose": (
            "Synthesise (do NOT merely list) prior work into themes, show where "
            "scholars agree and disagree, and surface the gap the study addresses. "
            "Cite the provided corpus papers by title/author where they fit."
        ),
        "words": 750,
    },
    "methodology": {
        "heading_en": "Chapter 3: Methodology",
        "heading_bm": "Bab 3: Metodologi",
        "purpose": (
            "Justify a research design, describe participants/sample, instruments, "
            "data-collection procedure, and analysis plan, tying each choice back "
            "to the research questions. State validity/reliability and ethics."
        ),
        "words": 700,
    },
    "results": {
        "heading_en": "Chapter 4: Results",
        "heading_bm": "Bab 4: Dapatan Kajian",
        "purpose": (
            "SIMULATE a small, realistic dataset appropriate to the study's method "
            "(e.g. descriptive statistics, group comparisons with a t-test/ANOVA, "
            "correlations, regression, or — for qualitative work — coded themes with "
            "frequencies) and WRITE UP the findings that answer each research "
            "question in turn. You MUST include at least one markdown table of the "
            "simulated data with concrete numbers, captioned like 'Table 4.1 "
            "(simulated data)', and refer to it in the prose (report exact figures: "
            "means, SDs, n, and a test statistic with p-value where the design "
            "implies one). State clearly at the top that the data are simulated and "
            "for illustration. Report neutrally — do NOT interpret; interpretation "
            "belongs in the Discussion."
        ),
        "words": 900,
    },
    "discussion": {
        "heading_en": "Chapter 5: Discussion",
        "heading_bm": "Bab 5: Perbincangan",
        "purpose": (
            "Interpret the SIMULATED findings from the Results chapter against the "
            "literature: cite plausible simulated figures (means/effects/themes) as "
            "you answer each research question explicitly, state theoretical and "
            "practical implications, acknowledge limitations (including that the "
            "findings rest on simulated, illustrative data, not real fieldwork), and "
            "recommend future work."
        ),
        "words": 750,
    },
}

_DEGREE = {
    "undergraduate": (
        "DEGREE: UNDERGRADUATE thesis. Expect a clear, well-organised argument "
        "with correct academic register; depth of a final-year project. Keep "
        "theory grounded and scope modest."
    ),
    "masters": (
        "DEGREE: MASTER'S thesis. Expect sharper theoretical framing, methodological "
        "rigour, and critical engagement with the literature, not just description."
    ),
    "phd": (
        "DEGREE: PhD thesis. Expect an original contribution to knowledge, deep "
        "theoretical sophistication, methodological justification at the frontier "
        "of the field, and confident critical synthesis."
    ),
}

_LANG = {
    "en": "LANGUAGE: Write the entire section in ENGLISH, in formal academic prose.",
    "bm": (
        "LANGUAGE: Tulis keseluruhan bahagian ini dalam BAHASA MELAYU akademik yang "
        "formal dan baku. Gunakan istilah akademik Bahasa Melayu yang betul."
    ),
}

_SYSTEM = (
    "You are Sensei, the thesis writer of the IdeaSifu Dojo. Given a student's "
    "research questions, you WRITE UP a strong sample of a thesis section that "
    "directly answers those questions — in finished academic prose, not advice. "
    "Do NOT explain how to write the section, do NOT give the student instructions "
    "or tips, and do NOT address the student; simply produce the write-up itself, "
    "as it would appear in the thesis. You ground every section in the research "
    "questions provided and in the real corpus papers you are given — you weave "
    "those in honestly and never invent a citation you were not given. "
    "For the Title section specifically: produce titles that are precise, specific "
    "to the population and context, and appropriate for the degree level — avoid "
    "generic phrasing and ensure your justification is critical and detailed. "
    "Respect the word cap for all other sections; a focused, well-structured "
    "sample beats long and padded."
)

_SYSTEM_PRO = (
    "You are Sensei, the thesis writer of the IdeaSifu Dojo. Given a student's "
    "research questions, you WRITE a complete, full-length thesis chapter that "
    "directly answers those questions — in finished academic prose, not advice. "
    "Do NOT explain how to write the section, do NOT give the student instructions "
    "or tips, and do NOT address the student; simply produce the chapter itself, "
    "as it would appear in the final thesis. You ground every section in the "
    "research questions provided and in the real corpus papers you are given — "
    "weave those in honestly and never invent a citation you were not given. "
    "You MUST meet the minimum word count stated in the user message — it is a "
    "hard floor, not a suggestion. Write with depth: expand every argument, add "
    "sub-section headings, provide concrete examples from the corpus, explain "
    "implications, and keep going until you have genuinely reached the minimum."
)


def _corpus_block(examples: list[DojoCorpusExample]) -> str:
    if not examples:
        return (
            "CORPUS PAPERS: (none retrieved — write from the research questions "
            "alone, and do NOT fabricate specific citations; refer to literature "
            "in general terms instead.)"
        )
    lines = []
    for e in examples:
        cite = e.reference or e.title
        tag = f"  → cite in-text as {e.intext}" if e.intext else ""
        lines.append(f"- {cite}{tag}")
    return (
        "CORPUS PAPERS (real references from the ThesisSifu academic corpus). When "
        "you draw on one, cite it in-text using EXACTLY the APA short form shown "
        "after it (e.g. (Tan & Lim, 2022)) — never list every author in-text. Do "
        "not invent other sources:\n"
        + "\n".join(lines)
    )


def write_section(
    req: DojoGenerateRequest,
    corpus: list[DojoCorpusExample],
) -> DojoSectionResult:
    """Write one capped, corpus-grounded sample thesis section."""
    meta = SECTIONS.get(req.section)
    if meta is None:  # research_questions is student-filled; nothing to generate
        raise ValueError(f"Section '{req.section}' is not generatable.")

    heading = meta["heading_bm"] if req.language == "bm" else meta["heading_en"]
    free_cap = meta["words"]
    pro_min = max(400, int(free_cap * 1.5))  # floor: 400 w; typical: 1050-1350 w
    cap = pro_min if req.pro else free_cap
    system = _SYSTEM_PRO if req.pro else _SYSTEM

    if req.pro:
        length_instruction = (
            f"MINIMUM LENGTH: {cap} words — this is a firm minimum, not a suggestion. "
            f"Write a thorough, full chapter draft. Develop every argument with "
            f"supporting evidence, sub-section headings, and detailed explanation. "
            f"Do NOT stop writing until you have reached at least {cap} words; "
            f"an under-length response is considered incomplete.\n\n"
        )
        section_label = "a complete chapter draft"
    else:
        length_instruction = (
            f"HARD LENGTH CAP: about {cap} words (a sample, not the whole chapter). "
            f"Do not exceed it. Use short paragraphs; you may use simple subheadings.\n\n"
        )
        section_label = "a finished SAMPLE"

    user = (
        f"Write up the '{heading}' section as {section_label} — the actual "
        f"academic prose as it would appear in the thesis, answering the research "
        f"questions. Do not explain how to write it or give the student any tips.\n\n"
        f"WORKING TITLE / TOPIC: {req.topic or '(not yet fixed — you may propose one)'}\n\n"
        f"RESEARCH QUESTIONS (the spine of the whole thesis — everything must serve these):\n"
        f"{req.research_questions.strip()}\n\n"
        f"STUDENT'S BRIEF FOR THIS SECTION: "
        f"{req.notes.strip() or '(none — use your best judgement)'}\n\n"
        f"WHAT THIS SECTION MUST DO: {meta['purpose']}\n\n"
        f"{_DEGREE.get(req.degree, _DEGREE['undergraduate'])}\n"
        f"{_LANG.get(req.language, _LANG['en'])}\n\n"
        f"{_corpus_block(corpus)}\n\n"
        f"{length_instruction}"
        f"Return a JSON object with exactly two keys:\n"
        f"- content: the writeup as markdown prose\n"
        f"- word_count: your best estimate of the content word count (integer)"
    )

    # Pro: generous token budget (~2 tokens/word + schema headroom).
    # Free: tighter cap keeps responses focused.
    max_tokens = int(cap * 2.5) + 600 if req.pro else int(cap * 2.4) + 400
    out = generate(system, user, _SenseiOutput, pro=req.pro, max_tokens=max_tokens)

    # The app owns every field except the writeup itself.
    return DojoSectionResult(
        section=req.section,
        heading=heading,
        content=out.content,
        corpus_examples=corpus,
        language=req.language,
        word_count=out.word_count or len(out.content.split()),
    )
