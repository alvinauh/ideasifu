import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  GraduationCap,
  Loader2,
  Sparkles,
  Lock,
  BookMarked,
  ExternalLink,
  Copy,
  Check,
  RotateCcw,
} from "lucide-react";
import * as api from "@/lib/api";
import { USING_MOCK } from "@/lib/api";
import type {
  DojoDegree,
  DojoLang,
  DojoSection,
  DojoSectionResult,
} from "@/lib/types";

// The generatable sections, in thesis order. `research_questions` is the
// student-filled gate and is handled separately (not in this list).
const SECTIONS: { key: Exclude<DojoSection, "research_questions">; label: string; blurb: string }[] = [
  { key: "title", label: "Title", blurb: "Sharp, researchable candidate titles tied to your questions." },
  { key: "introduction", label: "Introduction", blurb: "Background, problem, significance — funnelling into your questions." },
  { key: "literature_review", label: "Literature Review", blurb: "Themed synthesis of prior work, ending on the gap you fill." },
  { key: "methodology", label: "Methodology", blurb: "Design, sample, instruments and analysis, justified by your questions." },
  { key: "results", label: "Results", blurb: "A simulated dataset with tables, written up one research question at a time." },
  { key: "discussion", label: "Discussion", blurb: "Interpretation of the simulated findings — implications, limitations, future work." },
];

const DEGREES: { value: DojoDegree; label: string }[] = [
  { value: "undergraduate", label: "Undergraduate" },
  { value: "masters", label: "Master's" },
  { value: "phd", label: "PhD" },
];

const LANGS: { value: DojoLang; label: string }[] = [
  { value: "en", label: "English" },
  { value: "bm", label: "Bahasa Melayu" },
];

type SectionKey = (typeof SECTIONS)[number]["key"];

interface DojoState {
  degree: DojoDegree;
  language: DojoLang;
  topic: string;
  researchQuestions: string;
  notes: Partial<Record<SectionKey, string>>;
  results: Partial<Record<SectionKey, DojoSectionResult>>;
}

const STORAGE_KEY = "ideasifu.dojo";

function loadState(): DojoState {
  const base: DojoState = {
    degree: "undergraduate",
    language: "en",
    topic: "",
    researchQuestions: "",
    notes: {},
    results: {},
  };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return base;
    return { ...base, ...(JSON.parse(raw) as Partial<DojoState>) };
  } catch {
    return base;
  }
}

/** Minimal markdown-lite renderer: paragraphs, **bold**, *italic*, line breaks. */
function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(<strong key={k++}>{tok.slice(2, -2)}</strong>);
    else out.push(<em key={k++} className="text-muted">{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Is this line a markdown table separator, e.g. `| --- | :--: |`? */
function isTableSeparator(line: string): boolean {
  return line.includes("-") && /^\s*\|?[\s:|-]+\|?\s*$/.test(line);
}

/** Split a `| a | b |` row into trimmed cells. */
function parseTableRow(line: string): string[] {
  return line
    .replace(/^\s*\|/, "")
    .replace(/\|\s*$/, "")
    .split("|")
    .map((c) => c.trim());
}

function TableBlock({ lines }: { lines: string[] }) {
  const header = parseTableRow(lines[0]);
  const rows = lines.slice(2).filter((l) => l.includes("|")).map(parseTableRow);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border">
            {header.map((c, i) => (
              <th key={i} className="px-3 py-2 text-left font-display font-semibold text-foreground">
                {renderInline(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-b border-border/50">
              {row.map((c, ci) => (
                <td key={ci} className="px-3 py-1.5 text-foreground/90">
                  {renderInline(c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RichText({ content }: { content: string }) {
  const blocks = content.trim().split(/\n\n+/);
  return (
    <div className="space-y-3 text-sm leading-relaxed text-foreground/90">
      {blocks.map((block, i) => {
        const lines = block.split("\n");

        // A markdown pipe table: a header row + a `|---|` separator + rows.
        if (
          lines.length >= 2 &&
          lines[0].includes("|") &&
          isTableSeparator(lines[1])
        ) {
          return <TableBlock key={i} lines={lines} />;
        }

        // A heading line (#, ##, ###) — render as a bold sub-heading.
        const headingMatch = lines[0].match(/^(#{1,4})\s+(.*)$/);
        if (lines.length === 1 && headingMatch) {
          return (
            <p key={i} className="pt-1 font-display text-sm font-semibold text-foreground">
              {renderInline(headingMatch[2])}
            </p>
          );
        }

        // A bullet list block (lines starting with - or *).
        if (lines.every((l) => /^\s*[-*]\s+/.test(l))) {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {lines.map((l, j) => (
                <li key={j}>{renderInline(l.replace(/^\s*[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        // Default: a paragraph, preserving single line breaks.
        return (
          <p key={i}>
            {lines.map((line, j) => {
              const h = line.match(/^(#{1,4})\s+(.*)$/);
              return (
                <span key={j}>
                  {h ? <strong>{renderInline(h[2])}</strong> : renderInline(line)}
                  {j < lines.length - 1 && <br />}
                </span>
              );
            })}
          </p>
        );
      })}
    </div>
  );
}

export default function Dojo() {
  const [state, setState] = useState<DojoState>(loadState);
  const [loading, setLoading] = useState<Partial<Record<SectionKey, boolean>>>({});
  const [errors, setErrors] = useState<Partial<Record<SectionKey, string>>>({});
  const [copied, setCopied] = useState<SectionKey | null>(null);
  const saveTimer = useRef<number | null>(null);

  // Persist (debounced) so a student never loses their questions/drafts.
  useEffect(() => {
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch {
        /* storage full / unavailable — non-fatal */
      }
    }, 400);
    return () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    };
  }, [state]);

  const rqFilled = state.researchQuestions.trim().length > 0;

  function patch(p: Partial<DojoState>) {
    setState((s) => ({ ...s, ...p }));
  }
  function setNote(key: SectionKey, v: string) {
    setState((s) => ({ ...s, notes: { ...s.notes, [key]: v } }));
  }

  async function generate(key: SectionKey) {
    if (!rqFilled || loading[key]) return;
    setLoading((l) => ({ ...l, [key]: true }));
    setErrors((e) => ({ ...e, [key]: "" }));
    try {
      const result = await api.generateDojoSection({
        section: key,
        degree: state.degree,
        language: state.language,
        topic: state.topic.trim(),
        research_questions: state.researchQuestions.trim(),
        notes: (state.notes[key] ?? "").trim(),
      });
      setState((s) => ({ ...s, results: { ...s.results, [key]: result } }));
    } catch (e) {
      setErrors((er) => ({
        ...er,
        [key]: `Couldn't generate this section: ${
          e instanceof Error ? e.message : "unknown error"
        }`,
      }));
    } finally {
      setLoading((l) => ({ ...l, [key]: false }));
    }
  }

  async function copy(key: SectionKey) {
    const r = state.results[key];
    if (!r) return;
    try {
      await navigator.clipboard.writeText(`${r.heading}\n\n${r.content}`);
      setCopied(key);
      window.setTimeout(() => setCopied((c) => (c === key ? null : c)), 1500);
    } catch {
      /* clipboard blocked — ignore */
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      {/* Header */}
      <div className="mb-6">
        <p className="flex items-center gap-2 text-sm text-muted">
          <GraduationCap className="h-4 w-4" aria-hidden />
          The Dojo · a written-up sample thesis
        </p>
        <h1 className="mt-1 font-display text-2xl font-semibold sm:text-3xl">
          Your thesis, written up <span className="text-gradient">one chapter at a time</span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Start with your research questions. Sensei then writes up a sample of
          each chapter — Title, Introduction, Literature Review, Methodology,
          Results and Discussion — directly answering those questions and grounded
          in real papers from the ThesisSifu corpus, in English or Bahasa Melayu.
        </p>
      </div>

      {/* Global controls: degree + language + topic */}
      <section className="card-shadow mb-6 rounded-2xl border border-border bg-surface p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium text-muted">
              Degree level
            </label>
            <div className="flex flex-wrap gap-2">
              {DEGREES.map((d) => {
                const active = state.degree === d.value;
                return (
                  <button
                    key={d.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => patch({ degree: d.value })}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      active
                        ? "border-primary bg-primary/15 text-foreground"
                        : "border-border text-muted hover:text-foreground"
                    }`}
                  >
                    {d.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-muted">
              Output language
            </label>
            <div className="flex flex-wrap gap-2">
              {LANGS.map((l) => {
                const active = state.language === l.value;
                return (
                  <button
                    key={l.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => patch({ language: l.value })}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      active
                        ? "border-primary bg-primary/15 text-foreground"
                        : "border-border text-muted hover:text-foreground"
                    }`}
                  >
                    {l.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor="dojo-topic" className="mb-2 block text-sm font-medium text-muted">
            Working title / topic <span className="text-muted/60">(optional)</span>
          </label>
          <input
            id="dojo-topic"
            value={state.topic}
            onChange={(e) => patch({ topic: e.target.value })}
            placeholder="e.g. Parental involvement in special education in Malaysia"
            className="w-full rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
      </section>

      {/* Research questions — the required gate */}
      <section className="card-shadow mb-8 rounded-2xl border border-primary/40 bg-surface p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-display text-lg font-semibold">
            Research Questions
            <span className="ml-2 align-middle text-xs font-normal text-primary">
              required
            </span>
          </h2>
          {rqFilled && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-600">
              <Check className="h-3 w-3" aria-hidden />
              Sections unlocked
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted">
          These are the spine of your whole thesis — everything else is generated
          to serve them. Write one per line.
        </p>
        <textarea
          value={state.researchQuestions}
          onChange={(e) => patch({ researchQuestions: e.target.value })}
          rows={4}
          placeholder={
            "1. How does parental involvement affect learning outcomes for students with special needs?\n2. What barriers limit parental involvement, and how can schools reduce them?"
          }
          className="mt-3 w-full resize-y rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </section>

      {/* Generatable sections */}
      <div className="space-y-4">
        {SECTIONS.map((sec) => {
          const result = state.results[sec.key];
          const isLoading = loading[sec.key];
          const err = errors[sec.key];
          return (
            <section
              key={sec.key}
              className={`card-shadow rounded-2xl border bg-surface p-5 transition-opacity ${
                rqFilled ? "border-border" : "border-border opacity-60"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="flex items-center gap-2 font-display text-lg font-semibold">
                    {!rqFilled && <Lock className="h-4 w-4 text-muted" aria-hidden />}
                    {sec.label}
                  </h3>
                  <p className="mt-0.5 text-sm text-muted">{sec.blurb}</p>
                </div>
                <button
                  onClick={() => generate(sec.key)}
                  disabled={!rqFilled || isLoading}
                  title={rqFilled ? "" : "Fill in your research questions first"}
                  className="flex shrink-0 items-center gap-2 rounded-xl bg-gradient-idea px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : result ? (
                    <RotateCcw className="h-4 w-4" aria-hidden />
                  ) : (
                    <Sparkles className="h-4 w-4" aria-hidden />
                  )}
                  {isLoading ? "Drafting…" : result ? "Regenerate" : "Generate"}
                </button>
              </div>

              {/* Optional per-section brief */}
              <textarea
                value={state.notes[sec.key] ?? ""}
                onChange={(e) => setNote(sec.key, e.target.value)}
                disabled={!rqFilled}
                rows={2}
                placeholder={`Optional — briefly, what should this ${sec.label.toLowerCase()} cover? Leave blank to let Sensei decide.`}
                className="mt-3 w-full resize-y rounded-xl border border-border bg-surface-2 px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
              />

              {err && (
                <p className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
                  {err}
                </p>
              )}

              {isLoading && !result && (
                <div className="mt-4 grid min-h-[120px] place-items-center rounded-xl border border-dashed border-border">
                  <div className="text-center">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" aria-hidden />
                    <p className="mt-2 text-xs text-muted">
                      Pulling examples from the corpus and drafting a sample chapter…
                    </p>
                  </div>
                </div>
              )}

              {result && (
                <div className="mt-4 rounded-xl border border-border bg-surface-2 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="font-display text-sm font-semibold text-foreground">
                      {result.heading}
                    </p>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted">
                        ~{result.word_count} words · sample
                      </span>
                      <button
                        onClick={() => copy(sec.key)}
                        className="inline-flex items-center gap-1 text-xs text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                      >
                        {copied === sec.key ? (
                          <Check className="h-3.5 w-3.5" aria-hidden />
                        ) : (
                          <Copy className="h-3.5 w-3.5" aria-hidden />
                        )}
                        {copied === sec.key ? "Copied" : "Copy"}
                      </button>
                    </div>
                  </div>

                  <RichText content={result.content} />

                  {result.corpus_examples.length > 0 && (
                    <div className="mt-4">
                      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted">
                        <BookMarked className="h-3.5 w-3.5" aria-hidden />
                        References · grounded in the ThesisSifu corpus
                      </p>
                      <ol className="mt-2 space-y-2">
                        {result.corpus_examples.map((ex, i) => {
                          const link = ex.doi || ex.openalex_id || undefined;
                          return (
                            <li key={i} className="text-sm leading-relaxed text-foreground/90">
                              <span>{ex.reference || ex.title}</span>
                              {link && (
                                <a
                                  href={link}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="ml-2 inline-flex items-center gap-1 text-xs text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                >
                                  <ExternalLink className="h-3 w-3" aria-hidden />
                                  {ex.doi ? "DOI" : "OpenAlex"}
                                </a>
                              )}
                            </li>
                          );
                        })}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>

      <p className="mt-8 text-center text-xs text-muted">
        {USING_MOCK
          ? "Demo mode — showing sample write-ups. Connect the backend for live, corpus-grounded generation."
          : "Sensei writes up a capped sample of each chapter, answering your research questions and grounded in the ThesisSifu corpus."}
      </p>
    </main>
  );
}
