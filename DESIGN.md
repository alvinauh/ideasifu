# IdeaSifu — Product & UX Design Specification

> **Role of this document.** IdeaSifu is designed by a UI/UX designer with a
> teaching-and-learning background. This spec is written for that lens first:
> every screen decision is justified by how secondary and tertiary students
> actually *think, plan, and get unstuck* — not by what looks impressive.
> Engineering details live in `README.md` and the code; this file is the
> product-design source of truth.

---

## 1. Product in one sentence

**IdeaSifu is the generative sibling of ThesisSifu.** Where ThesisSifu *audits*
a finished draft, IdeaSifu sits at the empty-page moment and helps a student go
from *"I have to write about... something?"* to a **contextualized, defensible
research/assignment idea**, complete with a **critical-thinking mind map**,
**citations, references and books**, and a **short video summary** they can
watch to internalize the idea.

It is a **multi-agent** tool: a small crew of specialist AI agents crawl the
web, reason, and hand off to each other — visible to the student, so the *process
of thinking* is itself a teaching moment.

```
   ThesisSifu  →  evaluates what you wrote        (red pen, rigor, audit)
   IdeaSifu    →  generates what you could write   (spark, scaffolding, exploration)
```

---

## 2. Who it's for (the adaptive spine)

One app, two calibrated modes. The **tier toggle** is the most important control
in the product — it re-tunes vocabulary, scaffolding depth, citation rigor, and
tone. It is *not* a cosmetic theme switch.

| Dimension | 🎒 High-School mode | 🎓 University mode |
|---|---|---|
| Framing question | "What are you curious about?" | "What gap are you addressing?" |
| Idea shape | Guiding question + why-it-matters | Thesis statement + research gap + scope |
| Vocabulary | Plain, concrete, encouraging | Academic register, discipline-aware |
| Scaffolding | More steps, more examples, more "why" | Denser, assumes methodology literacy |
| Critical-thinking map | Claim → Reasons → Examples → "What if?" | Thesis → Arguments → Evidence → Counter-arguments → Gaps |
| Citations | 3–5 accessible sources + 1–2 books, explained | Formal references (APA/MLA), seminal + recent, DOIs |
| Video summary | 45–60s, story-led, plain language | 60–90s, structured, scholarly |
| Tone | Warm coach | Rigorous supervisor |

**Why adaptive, not two apps:** learners move *up* the ladder. A Form-5 student
and a first-year undergrad are often the same person 8 months apart. The toggle
lets the product grow with them and lets a teacher demonstrate rigor by sliding
the same idea from one mode to the next.

**Pedagogical stance:** IdeaSifu scaffolds *thinking*, it does not hand over
*writing*. Ideas are framed as **starting points to defend and refine**, every
claim is paired with a "how would you check this?" prompt, and sources are
presented as **things to read**, not things to quote blindly. This is a
deliberate guard against passive AI dependence.

---

## 3. The multi-agent crew (the "Sifus")

The crew is a first-class part of the UX. Students *see* the agents work,
hand off, and cite their reasoning. Each has a name, an icon, a color, and a
single clear job.

| Agent | Job | Student-facing label | Signature color |
|---|---|---|---|
| 🧭 **Scout** | Crawls/searches the web for current context, debates, real-world hooks, and recent developments in the topic. | "Scouting the field" | cyan |
| 💡 **Ideator** | Turns raw context into 3 distinct, tier-calibrated idea candidates; contextualizes the chosen one (why it matters, angle, scope). | "Shaping ideas" | violet (primary) |
| 🕸️ **Cartographer** | Builds the critical-thinking mind map: claims, reasons, evidence, counter-arguments, and open questions as a navigable graph. | "Mapping the thinking" | teal/green |
| 📚 **Librarian** | Attaches citations, references, and recommended books; grades each source's credibility and explains *why* it's relevant. | "Gathering sources" | amber |
| 🎬 **Director** | Writes a short narrated video summary (script + scene storyboard) of the contextualized idea. | "Filming the summary" | pink |

**Orchestrator** runs them as a pipeline with visible progress. Scout →
Ideator (fan-out to 3 candidates) → [student picks] → Cartographer + Librarian
(parallel) → Director. The student is in the loop at the pick step; everything
else streams.

**Why show the agents?** Naming and animating the crew turns an opaque "AI did
it" black box into a **worked example of the research process** — scout the
field, form a claim, map the reasoning, back it with sources, communicate it.
That sequence *is* the transferable skill we want students to absorb.

---

## 4. Core screens & flows

### 4.1 Landing
- Bold hero, tier toggle front-and-center, one input: *"What subject or topic
  are you working on?"* plus optional interests.
- The five agents shown as a living "crew" strip so the value prop is legible
  before first run.
- Sibling link to ThesisSifu ("Already have a draft? Audit it →").

### 4.2 Compose (the brief)
Three light fields — **Subject/topic**, **Level** (auto-set from tier, editable
to exact year), **Interests/angle** (optional) — plus assignment type
(essay / research proposal / project / presentation). Deliberately short: the
point is to remove the empty-page paralysis, not add a form-filling chore.

### 4.3 Generation (the crew at work) — *the signature screen*
- Live **agent activity feed**: each Sifu lights up, streams a one-line status,
  and hands off. This is the "show the thinking" moment.
- When the Ideator finishes, generation **pauses** and presents **3 idea cards**.
  The student **chooses** (or asks for 3 more). Choosing is a teaching act —
  it forces comparison and commitment.
- After the pick, Cartographer + Librarian + Director complete.

### 4.4 Idea Workspace — *the payload*
A focused workspace with the contextualized idea as the header and four panels:
1. **Idea** — thesis/guiding question, why it matters, angle, scope, and a
   "Refine" affordance (regenerate with a nudge).
2. **Mind map** — interactive critical-thinking diagram (see §5).
3. **Sources** — citations, references, and books, each with credibility badge,
   one-line "why this matters", and copy-citation.
4. **Video** — narrated summary player (script + storyboard scenes; TTS/video
   optional). Doubles as a revision aid.

### 4.5 Library / History
Saved ideas, re-openable, exportable. Lets a teacher assign and a student build
a portfolio of *thinking*, not just outputs.

---

## 5. The critical-thinking mind map (design detail)

The map is the intellectual heart of the product, so it gets explicit rules.

- **Node types** are visually distinct and pedagogically named:
  - `THESIS` / `QUESTION` (root) — the central claim or guiding question
  - `ARGUMENT` / `REASON` — supporting lines of reasoning
  - `EVIDENCE` — facts, data, quotes (link to a Source when possible)
  - `COUNTER` — objections and counter-arguments (**always present** — a map
    with no counters is a red flag we surface)
  - `QUESTION`/`GAP` — open questions and "what if?" prompts that push further
- **Every branch ends in a prompt, not a period.** Leaf nodes pose "How would
  you test this?" / "Who disagrees, and why?" — keeping the student in an
  active, questioning posture.
- **Evidence nodes cross-link to the Sources panel** so the map and the
  bibliography reinforce each other.
- Layout: radial from the root; color follows node type; counters use the
  warning hue to read as tension, deliberately.

---

## 6. Visual language

IdeaSifu is a **sibling** of ThesisSifu and the IEG learning apps: same
dark-first, high-energy, "neon on deep violet" DNA (Space Grotesk display +
Inter body, generous rounding, glow). It earns its own identity through an
**ideation gradient** — violet → cyan — and an **amber "spark"** accent, versus
ThesisSifu's audit-red. Full token values live in `frontend/src/styles.css`.

- **Canvas:** deep violet, near-black. Focus stays on content and the glowing crew.
- **Primary:** electric violet (shared family signature).
- **Accents:** cyan (discovery/Scout), teal-green (mapping/Cartographer),
  amber (sources + "spark"), pink (video/Director). Each agent owns a hue so the
  UI is legible at a glance.
- **Motion:** purposeful — agents pulse while thinking, hand-offs animate, nodes
  ease in. Motion communicates *process*, never decoration. Respects
  `prefers-reduced-motion`.
- **Accessibility:** WCAG AA contrast on all text; color is never the only
  signal (icons + labels accompany every hue); full keyboard nav; the mind map
  has a list-view fallback.

---

## 7. Design principles (the rubric I held every screen to)

1. **Beat the blank page.** The fastest possible path from "nothing" to "a real
   idea I can defend." Minimize input, front-load momentum.
2. **Show the thinking.** The multi-agent process is taught, not hidden — the
   crew is a visible model of the research method.
3. **Scaffold, don't substitute.** Output is a *starting point*: every idea and
   claim invites refinement, checking, and disagreement.
4. **One app, grows with the learner.** The tier toggle re-tunes rigor so the
   product serves a 14-year-old and a postgrad without forking.
5. **Sibling, not clone.** Visually and conceptually part of the ThesisSifu
   family, with a distinct generative identity.
6. **Everything is legible at a glance.** Color + icon + label together; motion
   with meaning; accessible by default.
