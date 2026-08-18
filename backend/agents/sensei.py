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
            "Write a full introduction chapter with the following structure — each "
            "section should be substantive, not a single sentence:\n"
            "  1. BACKGROUND — establish the broad context with evidence; cite corpus "
            "papers to show the prevalence or significance of the problem. Do not "
            "just assert that the topic is important — demonstrate it with specifics "
            "from the literature.\n"
            "  2. PROBLEM STATEMENT — articulate the specific gap or deficiency. "
            "Critically note why existing studies have not resolved it: name specific "
            "papers, state what they investigated, and explain exactly what they "
            "failed to examine or whom they failed to include.\n"
            "  3. SIGNIFICANCE — explain the theoretical and practical value of "
            "addressing this gap; tie the significance to the research questions.\n"
            "  4. SCOPE AND LIMITATIONS — clarify the boundaries of the study.\n"
            "  5. RESEARCH QUESTIONS — restate them as they will guide the study.\n"
            "Throughout, cite corpus papers not as decoration but as evidence: state "
            "what each cited study found and how it supports or motivates your argument."
        ),
        "words": 1000,
    },
    "literature_review": {
        "heading_en": "Chapter 2: Literature Review",
        "heading_bm": "Bab 2: Tinjauan Literatur",
        "purpose": (
            "Organise the review into 3–4 thematic sub-sections tied to the research "
            "questions. Within each theme, CRITICALLY ENGAGE with each corpus paper "
            "you cite — do ALL four of the following for every paper:\n"
            "  (a) STATE the specific findings or argument of that study (not just "
            "its topic — what exactly did it find or claim?);\n"
            "  (b) ANALYSE the methodology — what design did it use, what was the "
            "sample, what are the strengths and weaknesses of that approach?;\n"
            "  (c) CRITIQUE at least one concrete limitation of that study (e.g. "
            "small sample, single context, cross-sectional design, self-report bias, "
            "limited generalisability);\n"
            "  (d) CONNECT it explicitly to the research questions — does it support, "
            "contradict, or leave unanswered what this study seeks to find out?\n"
            "Show where scholars agree, where they diverge, and why the divergences "
            "matter for the current study. End with a synthesis paragraph that names "
            "the specific gap in the literature and maps it directly onto each "
            "research question."
        ),
        "words": 1400,
    },
    "methodology": {
        "heading_en": "Chapter 3: Methodology",
        "heading_bm": "Bab 3: Metodologi",
        "purpose": (
            "Write a full methodology chapter with the following components:\n"
            "  1. RESEARCH DESIGN — justify the chosen approach (qualitative, "
            "quantitative, or mixed). Cite corpus papers that used a similar design "
            "and explain why that design suits the research questions; also "
            "acknowledge the limitations of the chosen design.\n"
            "  2. PARTICIPANTS / SAMPLE — describe the target population, sampling "
            "strategy, sample size (and justify it with reference to similar studies "
            "or power analysis), and inclusion/exclusion criteria.\n"
            "  3. INSTRUMENTS / DATA SOURCES — for each instrument, cite the study "
            "that developed or validated it, report its reliability (Cronbach's alpha "
            "or equivalent), and explain why it operationalises the relevant construct "
            "in the research questions.\n"
            "  4. PROCEDURE — describe data collection step by step.\n"
            "  5. DATA ANALYSIS — specify the analysis technique and connect each "
            "technique to the research question it addresses.\n"
            "  6. VALIDITY, RELIABILITY, AND ETHICS — state strategies used and "
            "any ethical considerations."
        ),
        "words": 1000,
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
            "belongs in the Discussion. Devote a separate sub-section to each "
            "research question so the reader can see exactly how each one was answered."
        ),
        "words": 1100,
    },
    "discussion": {
        "heading_en": "Chapter 5: Discussion",
        "heading_bm": "Bab 5: Perbincangan",
        "purpose": (
            "Write a full discussion chapter addressing each research question in a "
            "dedicated sub-section. For each research question:\n"
            "  (a) INTERPRET the simulated finding — what does it mean?;\n"
            "  (b) COMPARE to corpus papers — do the simulated results align with or "
            "diverge from what those studies found? Be specific: name the paper, "
            "state its finding, and explain the agreement or divergence;\n"
            "  (c) EXPLAIN the divergence or alignment — differences in methodology, "
            "sample, context, or theoretical framework;\n"
            "  (d) STATE implications — what does this mean theoretically and "
            "practically for the field?\n"
            "Critically engage with at least 2 corpus papers per research question. "
            "After addressing all RQs, write sub-sections on: Limitations of the "
            "study (including the simulated nature of the data), Recommendations for "
            "practice, and Directions for future research."
        ),
        "words": 1200,
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
    "You are Sensei, the thesis writer of the IdeaSifu Dojo. You write finished "
    "academic thesis sections — real prose as it would appear in the thesis, never "
    "advice or instructions to the student.\n\n"
    "CRITICAL ENGAGEMENT IS MANDATORY. For every corpus paper you cite:\n"
    "  • State what that study specifically found or argued (not just its topic).\n"
    "  • Evaluate how it was done — the design, sample, and analytical approach.\n"
    "  • Identify a concrete limitation of that study.\n"
    "  • Connect it explicitly to the research questions — what it tells us and "
    "what it leaves unanswered.\n"
    "Never drop a citation without this dissection. Weave papers into paragraph-level "
    "arguments; do not list them. Never fabricate a citation not given to you.\n\n"
    "Do NOT address the student. Do NOT give writing tips. Write the section itself."
)

_SYSTEM_PRO = (
    "You are Sensei, the thesis writer of the IdeaSifu Dojo. You write complete, "
    "full-length thesis chapters — real prose as it would appear in the final thesis, "
    "never advice or instructions to the student.\n\n"
    "CRITICAL ENGAGEMENT IS MANDATORY. For every corpus paper you cite:\n"
    "  • State what that study specifically found or argued (not just its topic).\n"
    "  • Evaluate the methodology — design, sample, strengths, and weaknesses.\n"
    "  • Identify a concrete limitation of that study.\n"
    "  • Connect it explicitly to the research questions — what it contributes and "
    "what gap it leaves that the current study fills.\n"
    "Never drop a citation without this dissection. Weave papers into paragraph-level "
    "arguments; do not list them. Never fabricate a citation not given to you.\n\n"
    "You MUST meet the minimum word count — it is a hard floor. Write with full depth: "
    "develop every argument, use sub-section headings, engage each corpus paper "
    "critically, explain all implications. Do NOT stop before the minimum is reached.\n\n"
    "Do NOT address the student. Do NOT give writing tips. Write the chapter itself."
)


def _corpus_block(examples: list[DojoCorpusExample]) -> str:
    if not examples:
        return (
            "CORPUS PAPERS: (none retrieved — write from the research questions "
            "alone; do NOT fabricate specific citations; refer to literature in "
            "general terms only.)"
        )
    lines = []
    for e in examples:
        cite = e.reference or e.title
        intext = f"\n  → In-text citation: {e.intext}" if e.intext else ""
        abstract = f"\n  → Abstract: {e.abstract}" if e.abstract else ""
        lines.append(f"- {cite}{intext}{abstract}\n")
    return (
        "CORPUS PAPERS (real references from the ThesisSifu academic corpus).\n\n"
        "For EACH paper you draw on, you MUST critically engage — do not just cite it:\n"
        "  1. State what the study found or argued (use the abstract — be specific).\n"
        "  2. Comment on its methodology, sample, or scope.\n"
        "  3. Identify a limitation of that study.\n"
        "  4. Explain how it relates to the research questions.\n"
        "Cite in-text using EXACTLY the APA short form shown (e.g. (Tan & Lim, 2022)).\n"
        "Do NOT invent sources not listed here.\n\n"
        "PAPERS:\n"
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
    pro_min = max(800, int(free_cap * 2.2))  # floor: 800 w; typical: 2200-3100 w
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

    # ~2 tokens/word on average for academic prose; add headroom for JSON wrapper.
    max_tokens = int(cap * 2.6) + 900 if req.pro else int(cap * 2.6) + 600
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
