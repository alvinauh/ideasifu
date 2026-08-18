// Built-in mock client. Used when VITE_API_BASE_URL is empty/undefined so the
// whole app is fully demoable with NO backend. Data is topic-aware: it
// interpolates the brief's subject/interests into realistic-feeling output.

import type {
  Brief,
  CommunityFeedResponse,
  ContributionRequest,
  ContributionResult,
  CorpusSearchResponse,
  DojoCorpusExample,
  DojoGenerateRequest,
  DojoSection,
  DojoSectionResult,
  GenerateIdeasResponse,
  IdeaCandidate,
  IdeaResult,
  MindMap,
  ScoutReport,
  SharedIdeaDetail,
  Source,
  VideoSummary,
} from "@/lib/types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Trim + title-case-ish a subject for interpolation. */
function subjectPhrase(brief: Brief): string {
  const s = brief.subject.trim();
  return s.length ? s : "your topic";
}

function isUni(brief: Brief): boolean {
  return brief.tier === "university";
}

function mockScout(brief: Brief): ScoutReport {
  const subj = subjectPhrase(brief);
  const interest = brief.interests.trim();
  const angle = interest ? ` with an eye toward ${interest}` : "";
  return {
    context: `${subj} is moving fast right now${angle}. Public debate has shifted from "is this real?" to "who decides, who pays, and who is left out?" — which is exactly the kind of tension a strong ${
      isUni(brief) ? "thesis" : "guiding question"
    } can live inside.`,
    findings: [
      {
        title: `Recent policy shifts around ${subj}`,
        summary: `Several regions changed rules on ${subj} in the last 18 months, creating natural before/after comparisons.`,
        url: "https://example.org/policy-shift",
        hook: "Policy changes give you a clean 'what changed and for whom?' angle.",
      },
      {
        title: `A contested case study in ${subj}`,
        summary: `One widely-reported case split experts — a useful anchor for weighing competing claims.`,
        url: "https://example.org/case-study",
        hook: "A single vivid case makes an abstract topic concrete for a reader.",
      },
      {
        title: `The data gap in ${subj}`,
        summary: `Measurement is uneven: the loudest voices often have the least data, and vice versa.`,
        url: "https://example.org/data-gap",
        hook: "A gap is an invitation — it is where your original contribution lives.",
      },
    ],
    debates: [
      `Whether ${subj} is best solved by individuals or by institutions.`,
      `Whether current evidence on ${subj} is strong enough to act on now.`,
      `Who bears the cost, and who captures the benefit, of ${subj}.`,
    ],
  };
}

function mockCandidates(brief: Brief): IdeaCandidate[] {
  const subj = subjectPhrase(brief);
  const uni = isUni(brief);
  const mk = (
    id: string,
    title: string,
    statement: string,
    why: string,
    angle: string,
    scope: string,
    difficulty: IdeaCandidate["difficulty"],
  ): IdeaCandidate => ({
    id,
    title,
    statement,
    why_it_matters: why,
    angle,
    scope,
    difficulty,
  });

  return [
    mk(
      "cand-1",
      `The uneven playing field of ${subj}`,
      uni
        ? `${cap(subj)} produces benefits and harms that are systematically unequally distributed, and existing policy frameworks fail to account for this distributional gap.`
        : `Does everyone experience ${subj} in the same way — and if not, who is left out?`,
      `It turns a broad topic into a question about fairness, which readers care about and which you can actually argue.`,
      "Equity / distribution lens",
      uni
        ? "One region or sector, 2015–present, comparative."
        : "Two contrasting groups or places you can describe well.",
      "approachable",
    ),
    mk(
      "cand-2",
      `Who gets to decide about ${subj}?`,
      uni
        ? `Decision-making authority over ${subj} has concentrated faster than accountability mechanisms have adapted, creating a legitimacy deficit.`
        : `Who is really in charge of ${subj}, and should they be?`,
      `Power and accountability questions force you to name actors and weigh evidence — the heart of critical thinking.`,
      "Governance / power lens",
      uni
        ? "Institutional analysis of 2–3 key actors."
        : "Follow one decision from start to finish.",
      "moderate",
    ),
    mk(
      "cand-3",
      `${cap(subj)} without the hype`,
      uni
        ? `Dominant narratives about ${subj} overstate short-term effects while understating structural, long-run change, distorting policy priorities.`
        : `What do people get wrong about ${subj}, and what does the evidence actually say?`,
      `Myth-busting teaches you to separate claim from evidence — the single most transferable research skill.`,
      "Evidence vs. narrative lens",
      uni
        ? "Systematic comparison of claims against 4–5 sources."
        : "Pick 3 common claims and test each one.",
      "ambitious",
    ),
  ];
}

/** A second batch for the "Show 3 more" affordance. */
function mockMoreCandidates(brief: Brief): IdeaCandidate[] {
  const subj = subjectPhrase(brief);
  const uni = isUni(brief);
  return [
    {
      id: "cand-4",
      title: `${cap(subj)} across generations`,
      statement: uni
        ? `Generational cohorts diverge sharply in how they frame ${subj}, and this divergence predicts policy support more than income does.`
        : `Do younger and older people see ${subj} differently — and why?`,
      why_it_matters:
        "A generational angle is easy to relate to and lets you use surveys or interviews.",
      angle: "Generational / attitudes lens",
      scope: uni ? "Two cohorts, one survey dataset." : "Interview 2 people from each group.",
      difficulty: "approachable",
    },
    {
      id: "cand-5",
      title: `The hidden cost of ${subj}`,
      statement: uni
        ? `The true cost of ${subj} is externalized onto third parties, and standard accounting renders these costs invisible.`
        : `What costs of ${subj} do we usually ignore?`,
      why_it_matters:
        "Hidden-cost framing rewards careful, skeptical reasoning about what gets counted.",
      angle: "Externalities lens",
      scope: uni ? "One cost type, quantified." : "List and rank three overlooked costs.",
      difficulty: "moderate",
    },
    {
      id: "cand-6",
      title: `A better way to measure ${subj}`,
      statement: uni
        ? `Current metrics for ${subj} optimize for what is easy to measure rather than what matters, and an alternative indicator would change conclusions.`
        : `How should we measure ${subj} to be fair?`,
      why_it_matters:
        "Questioning the measure itself is advanced critical thinking — a standout move.",
      angle: "Measurement / methods lens",
      scope: uni ? "Propose and defend one new indicator." : "Compare two ways of measuring.",
      difficulty: "ambitious",
    },
  ];
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function mockSources(brief: Brief): Source[] {
  const subj = subjectPhrase(brief);
  const uni = isUni(brief);
  return [
    {
      id: "src-1",
      kind: "book",
      title: `The Field Guide to ${cap(subj)}`,
      authors: "R. Mendez & A. Osei",
      year: "2022",
      citation: uni
        ? `Mendez, R., & Osei, A. (2022). The Field Guide to ${cap(subj)}. Beacon Academic Press.`
        : `R. Mendez & A. Osei (2022), The Field Guide to ${cap(subj)}.`,
      url: null,
      credibility: "high",
      why: "A book gives you the big picture and vocabulary before you dive into articles.",
    },
    {
      id: "src-2",
      kind: "paper",
      title: `Distributional effects in ${subj}: a review`,
      authors: "L. Haddad et al.",
      year: "2023",
      citation: uni
        ? `Haddad, L., Ng, S., & Pereira, T. (2023). Distributional effects in ${subj}: a review. Journal of Applied Policy, 41(3), 210–238. https://doi.org/10.1000/japp.2023.041`
        : `L. Haddad and others (2023), "Distributional effects in ${subj}: a review."`,
      url: "https://example.org/paper-review",
      credibility: "high",
      why: "A recent peer-reviewed review is the fastest way to see what is settled and what is contested.",
    },
    {
      id: "src-3",
      kind: "article",
      title: `Explainer: what ${subj} means for you`,
      authors: "The Civic Desk",
      year: "2024",
      citation: uni
        ? `The Civic Desk. (2024). Explainer: what ${subj} means for you. Retrieved from https://example.org/explainer`
        : `The Civic Desk (2024), "Explainer: what ${subj} means for you."`,
      url: "https://example.org/explainer",
      credibility: "medium",
      why: "A plain-language explainer helps you sanity-check that you actually understand the basics.",
    },
    {
      id: "src-4",
      kind: "paper",
      title: `Counter-evidence: rethinking ${subj}`,
      authors: "D. Kovač",
      year: "2021",
      citation: uni
        ? `Kovač, D. (2021). Counter-evidence: rethinking ${subj}. Review of Contested Studies, 12(1), 45–67.`
        : `D. Kovač (2021), "Counter-evidence: rethinking ${subj}."`,
      url: "https://example.org/counter",
      credibility: "high",
      why: "Deliberately included to disagree with your idea — engaging it will make your argument stronger.",
    },
    {
      id: "src-5",
      kind: "web",
      title: `Community forum thread on ${subj}`,
      authors: "Various contributors",
      year: "2025",
      citation: `Community forum thread on ${subj} (2025). https://example.org/forum`,
      url: "https://example.org/forum",
      credibility: "unverified",
      why: "Useful for real-world hooks and lived experience — but verify every claim before you cite it.",
    },
  ];
}

function mockMindMap(brief: Brief, idea: IdeaCandidate): MindMap {
  const uni = isUni(brief);
  const root = uni ? ("thesis" as const) : ("question" as const);
  return {
    nodes: [
      {
        id: "n-root",
        label: idea.statement,
        type: root,
        parent: null,
        prompt: uni
          ? "Can you state this in one sentence a skeptic would still find precise?"
          : "Could you explain this to a friend in one breath? If not, tighten it.",
      },
      {
        id: "n-arg-1",
        label: uni ? "Argument: the distribution is uneven" : "Reason: not everyone is affected equally",
        type: "argument",
        parent: "n-root",
        prompt: "What is the strongest single fact behind this reason?",
      },
      {
        id: "n-arg-2",
        label: uni ? "Argument: existing frameworks miss it" : "Reason: the usual story leaves people out",
        type: "argument",
        parent: "n-root",
        prompt: "Whose perspective is missing from the usual story?",
      },
      {
        id: "n-ev-1",
        label: uni ? "Evidence: review data (Haddad 2023)" : "Example: the review by Haddad",
        type: "evidence",
        parent: "n-arg-1",
        prompt: "How was this measured, and could it be measured differently?",
        source_id: "src-2",
      },
      {
        id: "n-ev-2",
        label: uni ? "Evidence: contested case study" : "Example: the case everyone argued about",
        type: "evidence",
        parent: "n-arg-1",
        prompt: "Is this one case typical, or an outlier? How would you know?",
        source_id: "src-3",
      },
      {
        id: "n-ev-3",
        label: uni ? "Evidence: framework analysis" : "Example: who gets left out",
        type: "evidence",
        parent: "n-arg-2",
        prompt: "What would change your mind about this?",
        source_id: "src-1",
      },
      {
        id: "n-counter-1",
        label: uni
          ? "Counter: effects may equalize over time (Kovač 2021)"
          : "But wait: maybe it evens out eventually?",
        type: "counter",
        parent: "n-root",
        prompt: "Who disagrees with you, and what is their best point?",
        source_id: "src-4",
      },
      {
        id: "n-counter-2",
        label: uni ? "Counter: measurement artifact?" : "But wait: are we even measuring the right thing?",
        type: "counter",
        parent: "n-arg-1",
        prompt: "If the measure is flawed, does your whole argument survive?",
      },
      {
        id: "n-q-1",
        label: uni ? "Gap: no longitudinal data" : "What if: we followed this over ten years?",
        type: "question",
        parent: "n-root",
        prompt: "What is the one study you wish existed? Could you do a small version of it?",
      },
      {
        id: "n-q-2",
        label: uni ? "Open question: scope boundaries" : "What if: this looks different in another place?",
        type: "question",
        parent: "n-arg-2",
        prompt: "Where would you look next to test this?",
      },
    ],
  };
}

function mockVideo(brief: Brief, idea: IdeaCandidate): VideoSummary {
  const subj = subjectPhrase(brief);
  const uni = isUni(brief);
  const scenes = [
    {
      n: 1,
      visual: `Title card: "${idea.title}" over a slow drift of ${subj} imagery.`,
      narration: uni
        ? `Here is a thesis worth defending: ${idea.statement}`
        : `Let's start with a question: ${idea.statement}`,
      seconds: uni ? 12 : 9,
    },
    {
      n: 2,
      visual: "Split screen: the common view on the left, the twist on the right.",
      narration: `Most people think about ${subj} one way. ${idea.why_it_matters}`,
      seconds: 10,
    },
    {
      n: 3,
      visual: "Animated map/graph highlighting an uneven pattern.",
      narration: `The first clue: things are not as even as they look. ${idea.angle} helps us see it.`,
      seconds: 10,
    },
    {
      n: 4,
      visual: "A single source card flips over to reveal a key finding.",
      narration: "The evidence backs part of this up — but only part, and that is where it gets interesting.",
      seconds: 10,
    },
    {
      n: 5,
      visual: "A red-tinted 'objection' bubble rises, then gets addressed.",
      narration: "Now, someone will disagree. A good idea invites the objection instead of hiding from it.",
      seconds: 10,
    },
    {
      n: 6,
      visual: `Closing card: three "keep thinking" prompts, then the IdeaSifu spark.`,
      narration: uni
        ? "Your job now: test it, scope it, and find the gap only you can fill."
        : "Your job now: pick one clue and go find out if it's true.",
      seconds: uni ? 12 : 9,
    },
  ];
  return {
    title: idea.title,
    hook: uni
      ? `A ${idea.difficulty} thesis on ${subj}, in 60 seconds.`
      : `${cap(subj)} — the question, in under a minute.`,
    scenes,
    total_seconds: scenes.reduce((a, s) => a + s.seconds, 0),
  };
}

// --- Public mock API surface ---

export async function generateIdeas(
  brief: Brief,
): Promise<GenerateIdeasResponse> {
  await delay(700); // Scout crawling
  const scout = mockScout(brief);
  await delay(900); // Ideator shaping
  const candidates = mockCandidates(brief);
  return { scout, candidates };
}

export async function moreIdeas(brief: Brief): Promise<IdeaCandidate[]> {
  await delay(900);
  return mockMoreCandidates(brief);
}

export async function buildIdea(
  brief: Brief,
  _scout: ScoutReport,
  idea: IdeaCandidate,
): Promise<IdeaResult> {
  await delay(800); // Cartographer
  const mind_map = mockMindMap(brief, idea);
  await delay(700); // Librarian
  const sources = mockSources(brief);
  await delay(800); // Director
  const video = mockVideo(brief, idea);
  return { idea, mind_map, sources, video };
}

export async function refineIdea(
  _brief: Brief,
  idea: IdeaCandidate,
  nudge: string,
): Promise<IdeaCandidate> {
  await delay(900);
  const tag = nudge.trim();
  return {
    ...idea,
    title: `${idea.title} (refined)`,
    statement: `${idea.statement} — reframed toward "${tag}".`,
    angle: tag ? `${idea.angle}, nudged: ${tag}` : idea.angle,
    why_it_matters: `${idea.why_it_matters} This refinement sharpens the focus on ${
      tag || "your chosen direction"
    }.`,
  };
}

// --- The Dojo: sample thesis chapter (demo mode, no backend) ---

const DOJO_HEADINGS: Record<
  Exclude<DojoSection, "research_questions">,
  { en: string; bm: string }
> = {
  title: { en: "Thesis Title", bm: "Tajuk Tesis" },
  introduction: { en: "Chapter 1: Introduction", bm: "Bab 1: Pengenalan" },
  literature_review: {
    en: "Chapter 2: Literature Review",
    bm: "Bab 2: Tinjauan Literatur",
  },
  methodology: { en: "Chapter 3: Methodology", bm: "Bab 3: Metodologi" },
  results: { en: "Chapter 4: Results", bm: "Bab 4: Dapatan Kajian" },
  discussion: { en: "Chapter 5: Discussion", bm: "Bab 5: Perbincangan" },
};

function dojoBody(
  req: DojoGenerateRequest,
  cited: string,
): { content: string } {
  const t = req.topic.trim() || (req.language === "bm" ? "topik kajian ini" : "the study's topic");
  const rq = req.research_questions.trim();
  const s = req.section;
  const bm = req.language === "bm";

  const BODIES: Record<string, { en: string; bm: string }> = {
    title: {
      en: `**Candidate titles**\n\n1. *${cap(t)}: An Analysis Guided by the Stated Research Questions*\n2. *Understanding ${cap(t)}: Evidence, Gaps, and Directions*\n3. *Toward a Framework for ${cap(t)}*\n\nThe first is the strongest: it names the phenomenon precisely and signals an analytical stance without over-claiming, keeping the scope tied to the research questions.`,
      bm: `**Cadangan tajuk**\n\n1. *${cap(t)}: Satu Analisis Berpandukan Persoalan Kajian*\n2. *Memahami ${cap(t)}: Bukti, Jurang dan Hala Tuju*\n3. *Ke Arah Satu Kerangka bagi ${cap(t)}*\n\nTajuk pertama paling kukuh: ia menamakan fenomena dengan tepat dan menunjukkan pendirian analitis tanpa dakwaan berlebihan.`,
    },
    introduction: {
      en: `**Background.** Interest in ${t} has grown as researchers and practitioners confront its practical and theoretical stakes. ${cited} This chapter sets out why the problem matters and what remains unresolved.\n\n**Problem statement.** Despite this attention, current understanding is uneven and the mechanisms are not fully specified. This study addresses that gap.\n\n**Research questions.** The study is organised around:\n\n${rq}\n\n**Significance and scope.** Answering these questions contributes conceptual clarity and practical guidance, while keeping the scope bounded to what the design can support.`,
      bm: `**Latar belakang.** Minat terhadap ${t} semakin meningkat apabila penyelidik berdepan dengan kepentingan praktikal dan teorinya. ${cited} Bab ini menjelaskan mengapa masalah ini penting dan apa yang belum terjawab.\n\n**Pernyataan masalah.** Walaupun mendapat perhatian, kefahaman semasa masih tidak seimbang dan mekanismenya belum jelas. Kajian ini menangani jurang tersebut.\n\n**Persoalan kajian.** Kajian ini disusun berdasarkan:\n\n${rq}\n\n**Kepentingan dan skop.** Menjawab persoalan ini menyumbang kejelasan konsep dan panduan praktikal, dalam batas reka bentuk kajian.`,
    },
    literature_review: {
      en: `**Organising the field.** Rather than summarising studies one by one, the literature on ${t} can be grouped into recurring themes. ${cited}\n\n**Points of agreement.** Across studies there is broad consensus on the importance of the phenomenon and several core constructs.\n\n**Points of tension.** Scholars diverge on measurement and on how context shapes outcomes — a tension this study adjudicates.\n\n**The gap.** Taken together, the literature leaves a specific question under-examined, and it is precisely this gap the research questions target.`,
      bm: `**Menyusun bidang.** Berbanding merumus kajian satu persatu, literatur tentang ${t} boleh dikelompokkan mengikut tema berulang. ${cited}\n\n**Titik persetujuan.** Merentas kajian, terdapat kesepakatan tentang kepentingan fenomena ini dan beberapa konstruk teras.\n\n**Titik ketegangan.** Sarjana berbeza pendapat tentang pengukuran dan peranan konteks — perbezaan yang dirungkai oleh kajian ini.\n\n**Jurang kajian.** Secara keseluruhan, literatur meninggalkan satu persoalan yang kurang dikaji, dan inilah jurang yang disasarkan.`,
    },
    methodology: {
      en: `**Research design.** A design is chosen to fit the research questions on ${t}; their form (exploratory vs. confirmatory) drives whether a qualitative, quantitative, or mixed approach is warranted.\n\n**Participants / sample.** The sampling strategy, size, and inclusion criteria are specified and justified.\n\n**Instruments and procedure.** Instruments are described with attention to validity and reliability, followed by the step-by-step procedure.\n\n**Analysis and ethics.** The analysis plan maps each research question to a technique, and ethical safeguards (consent, confidentiality) are stated.`,
      bm: `**Reka bentuk kajian.** Reka bentuk dipilih agar sepadan dengan persoalan kajian tentang ${t}; bentuk persoalan menentukan sama ada pendekatan kualitatif, kuantitatif atau campuran yang sesuai.\n\n**Peserta / sampel.** Strategi persampelan, saiz dan kriteria pemilihan dinyatakan dan dijustifikasikan.\n\n**Instrumen dan prosedur.** Instrumen diterangkan dengan memberi perhatian kepada kesahan dan kebolehpercayaan, diikuti prosedur langkah demi langkah.\n\n**Analisis dan etika.** Rancangan analisis memetakan setiap persoalan kepada teknik tertentu, dan langkah etika dinyatakan.`,
    },
    results: {
      en: `*The data below are simulated for illustration only — not real fieldwork.*\n\nA total of N = 120 respondents were simulated for the study on ${t}, split evenly between a high- and a low-exposure group.\n\n**Table 4.1 (simulated data).** Descriptive statistics by group\n\n| Group | n | Mean | SD |\n| --- | --- | --- | --- |\n| High | 60 | 4.10 | 0.62 |\n| Low | 60 | 3.24 | 0.71 |\n\n**RQ1.** As shown in Table 4.1, the high-exposure group scored higher (M = 4.10, SD = 0.62) than the low-exposure group (M = 3.24, SD = 0.71). An independent-samples t-test on the simulated data indicated the difference was statistically significant, t(118) = 6.94, p < .001.\n\n**Table 4.2 (simulated data).** Reported barriers (% of respondents)\n\n| Barrier | % |\n| --- | --- |\n| Lack of time | 48 |\n| Lack of information | 33 |\n| Limited school support | 19 |\n\n**RQ2.** The most frequently reported barrier was lack of time (48%), followed by lack of information (33%) and limited school support (19%), as summarised in Table 4.2.\n\n**Summary.** Reported neutrally, the simulated findings answer each research question in turn; interpretation is deferred to the Discussion.`,
      bm: `*Data di bawah adalah simulasi untuk ilustrasi sahaja — bukan kerja lapangan sebenar.*\n\nSejumlah N = 120 responden disimulasikan bagi kajian tentang ${t}, dibahagi sama rata kepada kumpulan pendedahan tinggi dan rendah.\n\n**Jadual 4.1 (data simulasi).** Statistik deskriptif mengikut kumpulan\n\n| Kumpulan | n | Min | SP |\n| --- | --- | --- | --- |\n| Tinggi | 60 | 4.10 | 0.62 |\n| Rendah | 60 | 3.24 | 0.71 |\n\n**PK1.** Seperti ditunjukkan dalam Jadual 4.1, kumpulan pendedahan tinggi memperoleh skor lebih tinggi (Min = 4.10, SP = 0.62) berbanding kumpulan pendedahan rendah (Min = 3.24, SP = 0.71). Ujian-t sampel bebas ke atas data simulasi menunjukkan perbezaan ini signifikan, t(118) = 6.94, p < .001.\n\n**Jadual 4.2 (data simulasi).** Halangan dilaporkan (% responden)\n\n| Halangan | % |\n| --- | --- |\n| Kekurangan masa | 48 |\n| Kekurangan maklumat | 33 |\n| Sokongan sekolah terhad | 19 |\n\n**PK2.** Halangan paling kerap dilaporkan ialah kekurangan masa (48%), diikuti kekurangan maklumat (33%) dan sokongan sekolah terhad (19%), seperti diringkaskan dalam Jadual 4.2.\n\n**Ringkasan.** Dilaporkan secara neutral, dapatan simulasi menjawab setiap persoalan kajian; tafsiran ditangguhkan ke bab Perbincangan.`,
    },
    discussion: {
      en: `*Interpretation of the simulated Chapter 4 findings.*\n\n**Interpretation.** The simulated results on ${t} are read against the literature: the higher scores in the high-exposure group (M = 4.10 vs. 3.24) echo prior work, while the barrier pattern nuances it. ${cited}\n\n**Answering the questions.** RQ1 is answered by the significant group difference (t(118) = 6.94, p < .001); RQ2 by the ranking of barriers, led by lack of time (48%).\n\n**Implications.** Taken at face value, the simulated results carry theoretical and practical implications, stated with appropriate caution.\n\n**Limitations and future work.** The chief limitation is that these findings rest on simulated, illustrative data rather than real fieldwork; replication with collected data and concrete directions for future research are proposed.`,
      bm: `*Tafsiran dapatan simulasi daripada Bab 4.*\n\n**Tafsiran.** Dapatan simulasi tentang ${t} ditafsir berdasarkan literatur: skor lebih tinggi bagi kumpulan pendedahan tinggi (Min = 4.10 berbanding 3.24) selari dengan kajian terdahulu, manakala corak halangan memperincikannya. ${cited}\n\n**Menjawab persoalan.** PK1 dijawab oleh perbezaan kumpulan yang signifikan (t(118) = 6.94, p < .001); PK2 oleh susunan halangan, diterajui kekurangan masa (48%).\n\n**Implikasi.** Jika diambil pada nilai muka, dapatan simulasi membawa implikasi teori dan praktikal, dinyatakan dengan berhati-hati.\n\n**Batasan dan kajian akan datang.** Batasan utama ialah dapatan ini berasaskan data simulasi untuk ilustrasi, bukan kerja lapangan sebenar; replikasi dengan data sebenar dan hala tuju konkrit untuk kajian akan datang dicadangkan.`,
    },
  };

  const b = BODIES[s] ?? BODIES.introduction;
  return { content: bm ? b.bm : b.en };
}

export async function generateDojoSection(
  req: DojoGenerateRequest,
): Promise<DojoSectionResult> {
  await delay(1100);
  const heading =
    req.section === "research_questions"
      ? req.language === "bm"
        ? "Persoalan Kajian"
        : "Research Questions"
      : DOJO_HEADINGS[req.section][req.language];

  // Demo corpus examples (real corpus is ThesisSifu's ~7.1M-paper index).
  const q = (req.topic || req.research_questions).trim() || "your topic";
  const authors = ["Ahmad, S., & Lim, W.", "Tan, H. L.", "Rahman, N., & Yusof, K."];
  const corpus_examples: DojoCorpusExample[] = Array.from({ length: 3 }, (_, i) => {
    const title = `${cap(q)}: perspectives from the literature (sample ${i + 1})`;
    const year = 2021 - i;
    return {
      title,
      openalex_id: `https://openalex.org/W${2000000000 + i}`,
      score: Number((0.72 - i * 0.04).toFixed(3)),
      authors: authors[i],
      year,
      venue: "Journal of Educational Research",
      doi: null,
      reference: `${authors[i]} (${year}). ${title}. Journal of Educational Research, ${10 + i}(${i + 1}).`,
    };
  });

  const cited =
    req.language === "bm"
      ? `Sebagai contoh, kajian seperti "${corpus_examples[0].title}" antara yang relevan di sini.`
      : `For example, work such as "${corpus_examples[0].title}" is directly relevant here.`;

  const { content } = dojoBody(req, cited);
  return {
    section: req.section,
    heading,
    content,
    corpus_examples,
    language: req.language,
    word_count: content.split(/\s+/).length,
  };
}

export async function searchCorpus(
  query: string,
): Promise<CorpusSearchResponse> {
  await delay(700);
  const q = query.trim();
  if (!q) return { status: "error", count: 0, results: [], message: "Please enter a search query." };
  // Demo data — the real corpus is ThesisSifu's ~7.1M-paper OpenAlex index.
  const results = Array.from({ length: 8 }, (_, i) => ({
    title: `${q}: perspectives from the academic literature (sample ${i + 1})`,
    openalex_id: `https://openalex.org/W${1000000000 + i}`,
    score: Number((0.74 - i * 0.03).toFixed(3)),
  }));
  return { status: "ok", count: results.length, results, message: null };
}

// --- Community mock data ---

const MOCK_COMMUNITY_IDEAS = [
  {
    id: "mock-idea-community-1",
    title: "AI Bias in University Admissions Systems",
    statement: "Algorithmic admissions tools amplify socioeconomic inequity because they are trained on historical acceptance data that reflects human bias.",
    angle: "Ethical / sociological critique",
    shared_at: "2025-08-15T09:00:00",
    contribution_count: 3,
  },
  {
    id: "mock-idea-community-2",
    title: "Microplastics and Freshwater Biodiversity Loss",
    statement: "Microplastic contamination in river systems is a leading but underregulated driver of invertebrate biodiversity collapse.",
    angle: "Environmental science / policy gap",
    shared_at: "2025-08-14T14:30:00",
    contribution_count: 1,
  },
  {
    id: "mock-idea-community-3",
    title: "Digital Nomadism and Urban Housing Affordability",
    statement: "The rise of location-independent remote work intensifies housing price pressure in mid-sized cities by creating demand without increasing local supply.",
    angle: "Urban economics / social impact",
    shared_at: "2025-08-13T11:00:00",
    contribution_count: 5,
  },
];

export async function getCommunityFeed(): Promise<CommunityFeedResponse> {
  await delay(400);
  return { ideas: MOCK_COMMUNITY_IDEAS, total: MOCK_COMMUNITY_IDEAS.length };
}

export async function getIdeaDetail(ideaId: string): Promise<SharedIdeaDetail> {
  await delay(300);
  const idea = MOCK_COMMUNITY_IDEAS.find((i) => i.id === ideaId) ?? MOCK_COMMUNITY_IDEAS[0];
  return {
    ...idea,
    contributions: [
      {
        id: "mock-contrib-1",
        type: "challenge",
        text: "The framing assumes all bias originates in training data, but the choice of which features to include in the model is itself a human decision that deserves more scrutiny — this is often where proxy discrimination enters.",
        quality_ok: true,
        credits_awarded: 3,
        created_at: "2025-08-15T10:00:00",
      },
      {
        id: "mock-contrib-2",
        type: "source",
        text: "Obermeyer et al. (2019) in Science documented a commercial algorithm used in US healthcare that systematically underestimated Black patients' needs — a direct empirical parallel that would strengthen this argument.",
        quality_ok: true,
        credits_awarded: 3,
        created_at: "2025-08-15T12:00:00",
      },
    ],
  };
}

export async function contribute(req: ContributionRequest): Promise<ContributionResult> {
  await delay(1200);
  const wordCount = req.text.trim().split(/\s+/).length;
  const isSubstantive = wordCount >= 15 && !req.text.toLowerCase().startsWith("i agree");
  return {
    id: `mock-contrib-${Date.now()}`,
    credits_awarded: isSubstantive ? 3 : 0,
    quality_ok: isSubstantive,
    quality_reason: isSubstantive
      ? "Contribution accepted — well-reasoned and specific."
      : "Your contribution needs more specifics. Try explaining the 'why' or naming a concrete example.",
    new_credits: isSubstantive ? 9 : 6,
  };
}
