"""Deterministic, topic-aware mock data for IdeaSifu.

Lets the whole app run end-to-end with NO API key — for demos and design work.
Every function mirrors an agent and interpolates `brief.subject` (and the chosen
idea) so the output feels topic-aware, and branches on `brief.tier` for tone.

These are intentionally realistic — the mock mind map genuinely includes
thesis/argument/evidence/counter/question nodes so the UI looks right.
"""
from __future__ import annotations

from schemas import (
    Brief,
    DojoCorpusExample,
    DojoGenerateRequest,
    DojoSectionResult,
    IdeaCandidate,
    MindMap,
    MindMapNode,
    ScoutFinding,
    ScoutReport,
    Source,
    VideoScene,
    VideoSummary,
)


# --------------------------------------------------------------------------- #
# Scout
# --------------------------------------------------------------------------- #
def mock_scout(brief: Brief) -> ScoutReport:
    subj = brief.subject.strip() or "your topic"
    context = (
        f"Scholarship on {subj} has expanded rapidly in the last few years, "
        f"but the literature remains contested on both mechanisms and "
        f"policy implications. Recent empirical work has opened gaps that a "
        f"focused student project could meaningfully engage."
    )
    findings = [
        ScoutFinding(
            title=f"Recent developments in {subj}",
            summary=(
                f"There have been notable recent events and reporting related to "
                f"{subj} that are concrete enough to build an idea around."
            ),
            url="https://example.org/news",
            hook=(
                f"A real, recent example gives you something specific to anchor "
                f"your {brief.assignment_type} to."
            ),
        ),
        ScoutFinding(
            title=f"Data and evidence on {subj}",
            summary=(
                f"Datasets and studies on {subj} exist and are (partly) publicly "
                f"available, so claims can be checked against numbers."
            ),
            url="https://example.org/data",
            hook="Evidence you can actually examine keeps the idea honest.",
        ),
        ScoutFinding(
            title=f"A human story behind {subj}",
            summary=(
                f"People are directly affected by {subj}; there are voices and "
                f"cases that make the abstract concrete."
            ),
            url="https://example.org/story",
            hook="A human angle makes the idea matter to a reader.",
        ),
    ]
    debates = [
        f"How much of {subj} is driven by individuals versus systems?",
        f"Do current responses to {subj} actually work, or just look good?",
        f"Who benefits, and who pays, when we act on {subj}?",
    ]
    return ScoutReport(context=context, findings=findings, debates=debates)


# --------------------------------------------------------------------------- #
# Ideator
# --------------------------------------------------------------------------- #
def mock_candidates(brief: Brief) -> list[IdeaCandidate]:
    subj = brief.subject.strip() or "your topic"
    interest = brief.interests.strip()
    angle_tag = f" through the lens of {interest}" if interest else ""

    specs = [
        (
            f"Rethinking the drivers of {subj}",
            f"Contrary to the dominant framing, {subj} is best explained by "
            f"structural rather than individual factors.",
            "structural-causation angle",
            "Bounded literature synthesis; excludes primary data collection.",
            "approachable",
        ),
        (
            f"The accountability gap in {subj}",
            f"Current governance of {subj} systematically misallocates "
            f"responsibility, producing predictable policy failure.",
            "governance / accountability angle",
            "Comparative case analysis of two policy regimes.",
            "moderate",
        ),
        (
            f"Measuring what interventions in {subj} actually achieve",
            f"Prevailing interventions in {subj} are evaluated on proxies "
            f"that overstate their real-world impact.",
            "measurement / evaluation angle",
            "Critique of evaluation methodology using secondary data.",
            "ambitious",
        ),
    ]

    candidates: list[IdeaCandidate] = []
    for i, (title, statement, angle, scope, difficulty) in enumerate(specs, start=1):
        why = (
            f"This addresses a live gap in how {subj} is understood"
            f"{angle_tag}, and is tractable at the {brief.level or 'your'} "
            f"level as a {brief.assignment_type}."
        )
        candidates.append(
            IdeaCandidate(
                id=f"idea-{i}",
                title=title,
                statement=statement,
                why_it_matters=why,
                angle=angle,
                scope=scope,
                difficulty=difficulty,  # type: ignore[arg-type]
            )
        )
    return candidates


# --------------------------------------------------------------------------- #
# Cartographer
# --------------------------------------------------------------------------- #
def mock_mindmap(brief: Brief, idea: IdeaCandidate) -> MindMap:
    subj = brief.subject.strip() or "the topic"
    nodes = [
        MindMapNode(
            id="n1",
            label=idea.title,
            type="thesis",
            parent=None,
            prompt="What would you need to be true for this to hold up?",
        ),
        MindMapNode(
            id="n2",
            label=f"Reason: {subj} has a clear cause worth naming",
            type="argument",
            parent="n1",
            prompt="What is the single strongest reason to believe this?",
        ),
        MindMapNode(
            id="n3",
            label=f"Reason: {subj} affects people unequally",
            type="argument",
            parent="n1",
            prompt="Who is most affected, and how would you show it?",
        ),
        MindMapNode(
            id="n4",
            label=f"Evidence: data and studies on {subj}",
            type="evidence",
            parent="n2",
            prompt="Where would you find this data, and could you trust it?",
            source_id="s1",
        ),
        MindMapNode(
            id="n5",
            label=f"Evidence: a concrete real-world example of {subj}",
            type="evidence",
            parent="n3",
            prompt="What example would make this undeniable?",
            source_id="s2",
        ),
        MindMapNode(
            id="n6",
            label="Counter-argument: the opposite view",
            type="counter",
            parent="n1",
            prompt="Who disagrees with this, and what is their best point?",
        ),
        MindMapNode(
            id="n7",
            label=f"Counter-evidence others cite about {subj}",
            type="evidence",
            parent="n6",
            prompt="How would you check whether their evidence is stronger?",
            source_id="s3",
        ),
        MindMapNode(
            id="n8",
            label="Open question: what's still missing?",
            type="question",
            parent="n1",
            prompt="What would you still need to investigate to be sure?",
        ),
        MindMapNode(
            id="n9",
            label=f"What if the usual assumption about {subj} is wrong?",
            type="question",
            parent="n1",
            prompt="What if the common assumption here turned out to be false?",
        ),
    ]
    return MindMap(nodes=nodes)


# --------------------------------------------------------------------------- #
# Librarian
# --------------------------------------------------------------------------- #
def mock_sources(brief: Brief, idea: IdeaCandidate) -> list[Source]:
    subj = brief.subject.strip() or "the topic"
    return [
        Source(
            id="s1",
            kind="paper",
            title=f"Empirical patterns in {subj}: a systematic review",
            authors="Chen, L., & Adeyemi, O.",
            year="2024",
            citation=(
                f"Chen, L., & Adeyemi, O. (2024). Empirical patterns in {subj}: "
                f"A systematic review. Journal of Applied Studies, 41(3), "
                f"210-238. https://doi.org/10.0000/example"
            ),
            url="https://example.org/review",
            credibility="high",
            why="Recent peer-reviewed synthesis mapping the current evidence.",
        ),
        Source(
            id="s2",
            kind="book",
            title=f"Foundations of {subj}",
            authors="Novak, P.",
            year="2016",
            citation=(
                f"Novak, P. (2016). Foundations of {subj}. Academic Press."
            ),
            url=None,
            credibility="high",
            why="Seminal text establishing the core framework you'll engage.",
        ),
        Source(
            id="s3",
            kind="paper",
            title=f"Contesting the standard account of {subj}",
            authors="Haddad, R.",
            year="2023",
            citation=(
                f"Haddad, R. (2023). Contesting the standard account of {subj}. "
                f"Review of Critical Inquiry, 12(1), 44-67. "
                f"https://doi.org/10.0000/example2"
            ),
            url="https://example.org/contest",
            credibility="high",
            why="Supplies the counter-argument your thesis must answer.",
        ),
        Source(
            id="s4",
            kind="web",
            title=f"Policy report on {subj}",
            authors="Institute for Public Policy",
            year="2025",
            citation=(
                f"Institute for Public Policy. (2025). Policy report on {subj}. "
                f"Retrieved from ipp.example/reports"
            ),
            url="https://example.org/policy",
            credibility="medium",
            why="Grey-literature data point; corroborate against peer-reviewed work.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Director
# --------------------------------------------------------------------------- #
def mock_video(brief: Brief, idea: IdeaCandidate) -> VideoSummary:
    subj = brief.subject.strip() or "the topic"
    scenes = [
        VideoScene(
            n=1,
            visual="Clean title slide with the thesis",
            narration=f"Thesis: {idea.statement}",
            seconds=12,
        ),
        VideoScene(
            n=2,
            visual="Diagram of the research gap",
            narration=f"Here is the gap in how we currently understand {subj}.",
            seconds=13,
        ),
        VideoScene(
            n=3,
            visual="Evidence sources stacking up",
            narration="The argument rests on these lines of evidence.",
            seconds=13,
        ),
        VideoScene(
            n=4,
            visual="A prominent counter-argument slide",
            narration="A serious objection must be confronted, not ignored.",
            seconds=13,
        ),
        VideoScene(
            n=5,
            visual="Methodology flow",
            narration="Rigorous inquiry would test the claim like this.",
            seconds=12,
        ),
        VideoScene(
            n=6,
            visual="Closing slide with open questions",
            narration="Which questions remain, and how would you answer them?",
            seconds=12,
        ),
    ]
    title = f"{idea.title} — a research brief"
    hook = f"A 75-second scholarly framing of {subj}."

    return VideoSummary(
        title=title,
        hook=hook,
        scenes=scenes,
        total_seconds=sum(s.seconds for s in scenes),
    )


# --------------------------------------------------------------------------- #
# Dojo (Sensei) — sample thesis chapter, no API key required.
# --------------------------------------------------------------------------- #

# Bilingual headings, mirroring agents/sensei.SECTIONS.
_DOJO_HEADINGS = {
    "title": ("Thesis Title", "Tajuk Tesis"),
    "introduction": ("Chapter 1: Introduction", "Bab 1: Pengenalan"),
    "literature_review": ("Chapter 2: Literature Review", "Bab 2: Tinjauan Literatur"),
    "methodology": ("Chapter 3: Methodology", "Bab 3: Metodologi"),
    "results": ("Chapter 4: Results", "Bab 4: Dapatan Kajian"),
    "discussion": ("Chapter 5: Discussion", "Bab 5: Perbincangan"),
}


def _dojo_body_en(section: str, topic: str, rq: str, cited: str) -> str:
    t = topic or "the study's topic"
    if section == "title":
        return (
            f"**Candidate titles**\n\n"
            f"1. *{t.capitalize()}: An Analysis Guided by the Stated Research Questions*\n"
            f"2. *Understanding {t.capitalize()}: Evidence, Gaps, and Directions*\n"
            f"3. *Toward a Framework for {t.capitalize()}*\n\n"
            f"The first is the strongest: it names the phenomenon precisely and signals "
            f"an analytical stance without over-claiming, keeping the scope tied to the "
            f"research questions rather than a broad theme."
        )
    if section == "introduction":
        return (
            f"**Background.** Interest in {t} has grown as researchers and practitioners "
            f"confront its practical and theoretical stakes. {cited} This chapter sets out "
            f"why the problem matters and what remains unresolved.\n\n"
            f"**Problem statement.** Despite this attention, current understanding is "
            f"uneven: findings are fragmented across contexts and the mechanisms are not "
            f"fully specified. This study addresses that gap.\n\n"
            f"**Research questions.** The study is organised around the following "
            f"questions:\n\n{rq}\n\n"
            f"**Significance and scope.** Answering these questions contributes both "
            f"conceptual clarity and practical guidance, while keeping the scope bounded "
            f"to what the chosen design can credibly support."
        )
    if section == "literature_review":
        return (
            f"**Organising the field.** Rather than summarising studies one by one, the "
            f"literature on {t} can be grouped into recurring themes. {cited}\n\n"
            f"**Points of agreement.** Across studies, there is broad consensus on the "
            f"importance of the phenomenon and on several core constructs.\n\n"
            f"**Points of tension.** Scholars diverge, however, on measurement and on how "
            f"context shapes outcomes — a tension this study adjudicates.\n\n"
            f"**The gap.** Taken together, the literature leaves a specific question "
            f"under-examined, and it is precisely this gap the research questions target."
        )
    if section == "methodology":
        return (
            f"**Research design.** A design is chosen to fit the research questions on "
            f"{t}; the questions' form (exploratory vs. confirmatory) drives whether a "
            f"qualitative, quantitative, or mixed approach is warranted.\n\n"
            f"**Participants / sample.** The sampling strategy, size, and inclusion "
            f"criteria are specified and justified against the questions.\n\n"
            f"**Instruments and procedure.** Data-collection instruments are described, "
            f"with attention to validity and reliability, followed by the step-by-step "
            f"procedure.\n\n"
            f"**Analysis and ethics.** The analysis plan maps each research question to a "
            f"specific technique, and ethical safeguards (consent, confidentiality) are "
            f"stated."
        )
    if section == "results":
        return (
            f"*The data below are simulated for illustration only — not real fieldwork.*\n\n"
            f"A total of N = 120 respondents were simulated for the study on {t}, "
            f"split evenly between a high- and a low-exposure group.\n\n"
            f"**Table 4.1 (simulated data).** Descriptive statistics by group\n\n"
            f"| Group | n | Mean | SD |\n"
            f"| --- | --- | --- | --- |\n"
            f"| High | 60 | 4.10 | 0.62 |\n"
            f"| Low | 60 | 3.24 | 0.71 |\n\n"
            f"**RQ1.** As shown in Table 4.1, the high-exposure group scored higher "
            f"(M = 4.10, SD = 0.62) than the low-exposure group (M = 3.24, SD = 0.71). "
            f"An independent-samples t-test on the simulated data indicated the "
            f"difference was statistically significant, t(118) = 6.94, p < .001.\n\n"
            f"**Table 4.2 (simulated data).** Reported barriers (% of respondents)\n\n"
            f"| Barrier | % |\n"
            f"| --- | --- |\n"
            f"| Lack of time | 48 |\n"
            f"| Lack of information | 33 |\n"
            f"| Limited school support | 19 |\n\n"
            f"**RQ2.** The most frequently reported barrier was lack of time (48%), "
            f"followed by lack of information (33%) and limited school support (19%), "
            f"as summarised in Table 4.2.\n\n"
            f"**Summary.** Reported neutrally, the simulated findings answer each "
            f"research question in turn; interpretation is deferred to the Discussion."
        )
    # discussion
    return (
        f"*Interpretation of the simulated Chapter 4 findings.*\n\n"
        f"**Interpretation.** The simulated results on {t} are read against the "
        f"literature: the higher scores in the high-exposure group (M = 4.10 vs. "
        f"3.24) echo prior work, while the barrier pattern nuances it. {cited}\n\n"
        f"**Answering the questions.** RQ1 is answered by the significant group "
        f"difference (t(118) = 6.94, p < .001); RQ2 by the ranking of barriers, led "
        f"by lack of time (48%).\n\n"
        f"**Implications.** Taken at face value, the simulated results carry both "
        f"theoretical and practical implications, stated with appropriate caution.\n\n"
        f"**Limitations and future work.** The chief limitation is that these "
        f"findings rest on simulated, illustrative data rather than real fieldwork; "
        f"replication with collected data and concrete directions for future "
        f"research are proposed."
    )


def _dojo_body_bm(section: str, topic: str, rq: str, cited: str) -> str:
    t = topic or "topik kajian ini"
    if section == "title":
        return (
            f"**Cadangan tajuk**\n\n"
            f"1. *{t.capitalize()}: Satu Analisis Berpandukan Persoalan Kajian*\n"
            f"2. *Memahami {t.capitalize()}: Bukti, Jurang dan Hala Tuju*\n"
            f"3. *Ke Arah Satu Kerangka bagi {t.capitalize()}*\n\n"
            f"Tajuk pertama paling kukuh: ia menamakan fenomena dengan tepat dan "
            f"menunjukkan pendirian analitis tanpa membuat dakwaan berlebihan, sekali gus "
            f"mengekalkan skop selaras dengan persoalan kajian."
        )
    if section == "introduction":
        return (
            f"**Latar belakang.** Minat terhadap {t} semakin meningkat apabila penyelidik "
            f"dan pengamal berdepan dengan kepentingan praktikal serta teorinya. {cited} "
            f"Bab ini menjelaskan mengapa masalah ini penting dan apa yang masih belum "
            f"terjawab.\n\n"
            f"**Pernyataan masalah.** Walaupun mendapat perhatian, kefahaman semasa masih "
            f"tidak seimbang dan mekanismenya belum jelas. Kajian ini menangani jurang "
            f"tersebut.\n\n"
            f"**Persoalan kajian.** Kajian ini disusun berdasarkan persoalan berikut:\n\n"
            f"{rq}\n\n"
            f"**Kepentingan dan skop.** Menjawab persoalan ini menyumbang kejelasan konsep "
            f"dan panduan praktikal, sambil mengekalkan skop dalam batas reka bentuk kajian."
        )
    if section == "literature_review":
        return (
            f"**Menyusun bidang.** Berbanding merumus kajian satu persatu, literatur "
            f"tentang {t} boleh dikelompokkan mengikut tema berulang. {cited}\n\n"
            f"**Titik persetujuan.** Merentas kajian, terdapat kesepakatan tentang "
            f"kepentingan fenomena ini dan beberapa konstruk teras.\n\n"
            f"**Titik ketegangan.** Namun, sarjana berbeza pendapat tentang pengukuran dan "
            f"peranan konteks — perbezaan yang dirungkai oleh kajian ini.\n\n"
            f"**Jurang kajian.** Secara keseluruhan, literatur meninggalkan satu persoalan "
            f"yang kurang dikaji, dan inilah jurang yang disasarkan oleh persoalan kajian."
        )
    if section == "methodology":
        return (
            f"**Reka bentuk kajian.** Reka bentuk dipilih agar sepadan dengan persoalan "
            f"kajian tentang {t}; bentuk persoalan menentukan sama ada pendekatan "
            f"kualitatif, kuantitatif atau campuran yang sesuai.\n\n"
            f"**Peserta / sampel.** Strategi persampelan, saiz dan kriteria pemilihan "
            f"dinyatakan dan dijustifikasikan.\n\n"
            f"**Instrumen dan prosedur.** Instrumen pengumpulan data diterangkan dengan "
            f"memberi perhatian kepada kesahan dan kebolehpercayaan, diikuti prosedur "
            f"langkah demi langkah.\n\n"
            f"**Analisis dan etika.** Rancangan analisis memetakan setiap persoalan kajian "
            f"kepada teknik tertentu, dan langkah etika (persetujuan, kerahsiaan) dinyatakan."
        )
    if section == "results":
        return (
            f"*Data di bawah adalah simulasi untuk ilustrasi sahaja — bukan kerja "
            f"lapangan sebenar.*\n\n"
            f"Sejumlah N = 120 responden disimulasikan bagi kajian tentang {t}, "
            f"dibahagi sama rata kepada kumpulan pendedahan tinggi dan rendah.\n\n"
            f"**Jadual 4.1 (data simulasi).** Statistik deskriptif mengikut kumpulan\n\n"
            f"| Kumpulan | n | Min | SP |\n"
            f"| --- | --- | --- | --- |\n"
            f"| Tinggi | 60 | 4.10 | 0.62 |\n"
            f"| Rendah | 60 | 3.24 | 0.71 |\n\n"
            f"**PK1.** Seperti ditunjukkan dalam Jadual 4.1, kumpulan pendedahan tinggi "
            f"memperoleh skor lebih tinggi (Min = 4.10, SP = 0.62) berbanding kumpulan "
            f"pendedahan rendah (Min = 3.24, SP = 0.71). Ujian-t sampel bebas ke atas "
            f"data simulasi menunjukkan perbezaan ini signifikan, t(118) = 6.94, "
            f"p < .001.\n\n"
            f"**Jadual 4.2 (data simulasi).** Halangan dilaporkan (% responden)\n\n"
            f"| Halangan | % |\n"
            f"| --- | --- |\n"
            f"| Kekurangan masa | 48 |\n"
            f"| Kekurangan maklumat | 33 |\n"
            f"| Sokongan sekolah terhad | 19 |\n\n"
            f"**PK2.** Halangan paling kerap dilaporkan ialah kekurangan masa (48%), "
            f"diikuti kekurangan maklumat (33%) dan sokongan sekolah terhad (19%), "
            f"seperti diringkaskan dalam Jadual 4.2.\n\n"
            f"**Ringkasan.** Dilaporkan secara neutral, dapatan simulasi menjawab setiap "
            f"persoalan kajian; tafsiran ditangguhkan ke bab Perbincangan."
        )
    # discussion
    return (
        f"*Tafsiran dapatan simulasi daripada Bab 4.*\n\n"
        f"**Tafsiran.** Dapatan simulasi tentang {t} ditafsir berdasarkan literatur: "
        f"skor lebih tinggi bagi kumpulan pendedahan tinggi (Min = 4.10 berbanding "
        f"3.24) selari dengan kajian terdahulu, manakala corak halangan memperincikannya. "
        f"{cited}\n\n"
        f"**Menjawab persoalan.** PK1 dijawab oleh perbezaan kumpulan yang signifikan "
        f"(t(118) = 6.94, p < .001); PK2 oleh susunan halangan, diterajui kekurangan "
        f"masa (48%).\n\n"
        f"**Implikasi.** Jika diambil pada nilai muka, dapatan simulasi membawa implikasi "
        f"teori dan praktikal, dinyatakan dengan berhati-hati.\n\n"
        f"**Batasan dan kajian akan datang.** Batasan utama ialah dapatan ini "
        f"berasaskan data simulasi untuk ilustrasi, bukan kerja lapangan sebenar; "
        f"replikasi dengan data sebenar dan hala tuju konkrit untuk kajian akan datang "
        f"dicadangkan."
    )


def mock_dojo(
    req: DojoGenerateRequest,
    corpus: list[DojoCorpusExample],
) -> DojoSectionResult:
    """Deterministic sample thesis chapter — used when no live LLM is configured."""
    en, bm = _DOJO_HEADINGS.get(req.section, (req.section.title(), req.section.title()))
    heading = bm if req.language == "bm" else en

    rq = req.research_questions.strip() or (
        "1. (Nyatakan persoalan kajian anda di sini.)" if req.language == "bm"
        else "1. (State your research questions here.)"
    )
    # Weave one real corpus title into the prose when we have it.
    if corpus:
        top = corpus[0].title
        cited = (
            f"Sebagai contoh, kajian seperti \"{top}\" antara yang relevan di sini."
            if req.language == "bm"
            else f"For example, work such as \"{top}\" is directly relevant here."
        )
    else:
        cited = ""

    body_fn = _dojo_body_bm if req.language == "bm" else _dojo_body_en
    content = body_fn(req.section, req.topic.strip(), rq, cited)

    return DojoSectionResult(
        section=req.section,
        heading=heading,
        content=content,
        corpus_examples=corpus,
        language=req.language,
        word_count=len(content.split()),
    )
