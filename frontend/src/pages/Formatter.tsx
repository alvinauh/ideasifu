import { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Info,
  Loader2,
  Upload,
  XCircle,
} from "lucide-react";
import * as api from "@/lib/api";
import { USING_MOCK } from "@/lib/api";
import type { FormatIssue, FormatMatchResponse, JournalStyle } from "@/lib/types";

// ── helpers ──────────────────────────────────────────────────────────────────

function scoreColor(n: number): string {
  if (n >= 80) return "text-emerald-600";
  if (n >= 50) return "text-amber-600";
  return "text-red-500";
}

function scoreBg(n: number): string {
  if (n >= 80) return "border-emerald-500/30 bg-emerald-500/10";
  if (n >= 50) return "border-amber-500/30 bg-amber-500/10";
  return "border-red-500/30 bg-red-500/10";
}

function severityBorder(s: string): string {
  if (s === "high") return "border-red-500/40 bg-red-500/5";
  if (s === "medium") return "border-amber-500/40 bg-amber-500/5";
  return "border-blue-500/30 bg-blue-500/5";
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "high"
      ? "bg-red-500/15 text-red-600"
      : severity === "medium"
      ? "bg-amber-500/15 text-amber-600"
      : "bg-blue-500/15 text-blue-500";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${cls}`}>
      {severity}
    </span>
  );
}

// ── file drop zone ────────────────────────────────────────────────────────────

interface DropZoneProps {
  label: string;
  hint: string;
  file: File | null;
  onFile: (f: File) => void;
  accept: string;
}

function DropZone({ label, hint, file, onFile, accept }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-colors
        ${dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/40 hover:bg-surface-2"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />
      {file ? (
        <div className="flex flex-col items-center gap-2">
          <FileText className="h-8 w-8 text-primary" aria-hidden />
          <p className="text-sm font-medium text-foreground">{file.name}</p>
          <p className="text-xs text-muted">{(file.size / 1024).toFixed(0)} KB · click to replace</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <Upload className="h-8 w-8 text-muted" aria-hidden />
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted">{hint}</p>
        </div>
      )}
    </div>
  );
}

// ── journal style card ────────────────────────────────────────────────────────

function StyleCard({ style }: { style: JournalStyle }) {
  const rows: [string, string][] = [
    ["Chapter format", style.chapter_label_format],
    ["Sub-heading format", style.subheading_format],
    ["Numbering scheme", style.numbering_scheme],
    ["Reference style", style.reference_style || "not detected"],
    ["Abstract", style.abstract_present ? "present" : "not present"],
    ["Keywords", style.keywords_present ? "present" : "not present"],
  ];
  return (
    <div className="card-shadow rounded-2xl border border-border bg-surface p-5">
      <h2 className="mb-3 font-display text-base font-semibold">Journal Format Detected</h2>
      <dl className="grid gap-2 sm:grid-cols-2">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs font-medium uppercase tracking-wide text-muted">{k}</dt>
            <dd className="mt-0.5 text-sm text-foreground">{v}</dd>
          </div>
        ))}
      </dl>
      {style.section_order.length > 0 && (
        <div className="mt-3">
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">Section order</dt>
          <dd className="mt-1 flex flex-wrap gap-1.5">
            {style.section_order.map((s, i) => (
              <span key={i} className="rounded-full border border-border bg-surface-2 px-2.5 py-0.5 text-xs">
                {s}
              </span>
            ))}
          </dd>
        </div>
      )}
      {style.formatting_notes && (
        <p className="mt-3 text-xs text-muted">
          <Info className="mr-1 inline h-3.5 w-3.5" aria-hidden />
          {style.formatting_notes}
        </p>
      )}
    </div>
  );
}

// ── issue card ────────────────────────────────────────────────────────────────

function IssueCard({ issue }: { issue: FormatIssue }) {
  const [open, setOpen] = useState(true);
  return (
    <div className={`rounded-2xl border p-4 ${severityBorder(issue.severity)}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start justify-between gap-3 text-left focus:outline-none"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={issue.severity} />
            <span className="text-sm font-medium text-foreground">{issue.location}</span>
          </div>
          {!open && (
            <p className="mt-1 truncate text-xs text-muted">{issue.suggestion}</p>
          )}
        </div>
        {open ? (
          <ChevronUp className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
        ) : (
          <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
        )}
      </button>

      {open && (
        <div className="mt-3 space-y-2.5 text-sm">
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
              <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wide text-red-500">Current</p>
              <p className="text-foreground/90">{issue.current}</p>
            </div>
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
              <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-600">Expected</p>
              <p className="text-foreground/90">{issue.expected}</p>
            </div>
          </div>
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2">
            <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted">How to fix</p>
            <p className="text-foreground/90">{issue.suggestion}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function Formatter() {
  const [journalFile, setJournalFile] = useState<File | null>(null);
  const [docFile, setDocFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [transforming, setTransforming] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<FormatMatchResponse | null>(null);
  const [showOutline, setShowOutline] = useState(false);

  async function analyze() {
    if (!journalFile || !docFile || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await api.formatMatch(journalFile, docFile);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function downloadConverted() {
    if (!docFile || !result || transforming) return;
    if (!docFile.name.toLowerCase().endsWith(".docx")) {
      setError("Document transformation is only supported for DOCX files. PDF conversion is not available.");
      return;
    }
    setTransforming(true);
    setError("");
    try {
      const blob = await api.formatTransform(
        docFile,
        result.heading_map,
        result.journal_style.section_order,
        result.missing_sections,
        journalFile ?? undefined,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = docFile.name.replace(/\.docx$/i, "_converted.docx");
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transform failed. Please try again.");
    } finally {
      setTransforming(false);
    }
  }

  const highCount = result?.issues.filter((i) => i.severity === "high").length ?? 0;
  const medCount = result?.issues.filter((i) => i.severity === "medium").length ?? 0;
  const lowCount = result?.issues.filter((i) => i.severity === "low").length ?? 0;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      {/* Header */}
      <div className="mb-6">
        <p className="flex items-center gap-2 text-sm text-muted">
          <FileText className="h-4 w-4" aria-hidden />
          FormatSifu · Journal Format Converter
        </p>
        <h1 className="mt-1 font-display text-2xl font-semibold sm:text-3xl">
          Match your document to any{" "}
          <span className="text-gradient">journal format</span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Upload a reference journal article and your document. FormatSifu extracts the
          journal's heading style, numbering scheme, and section order — then finds every
          mismatch in your document and tells you exactly how to fix it.
        </p>
      </div>

      {USING_MOCK && (
        <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
          <Info className="mr-1.5 inline h-4 w-4" aria-hidden />
          Format matching requires the live backend — connect{" "}
          <code className="font-mono text-xs">VITE_API_BASE_URL</code> to use this feature.
        </div>
      )}

      {/* Upload zone */}
      <section className="card-shadow mb-6 rounded-2xl border border-border bg-surface p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-medium text-muted">
              1. Reference journal{" "}
              <span className="text-muted/60">(DOCX or PDF)</span>
            </p>
            <DropZone
              label="Drop journal article here"
              hint="The format you want to match · DOCX or PDF"
              file={journalFile}
              onFile={setJournalFile}
              accept=".docx,.pdf"
            />
          </div>
          <div>
            <p className="mb-2 text-sm font-medium text-muted">
              2. Your document{" "}
              <span className="text-muted/60">(DOCX or PDF)</span>
            </p>
            <DropZone
              label="Drop your document here"
              hint="The document to check and convert · DOCX or PDF"
              file={docFile}
              onFile={setDocFile}
              accept=".docx,.pdf"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={analyze}
          disabled={!journalFile || !docFile || loading || USING_MOCK}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-idea py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Analysing format…
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4" aria-hidden />
              Analyse Format
            </>
          )}
        </button>
      </section>

      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {error}
        </div>
      )}

      {loading && (
        <div className="mb-6 grid min-h-[140px] place-items-center rounded-2xl border border-dashed border-border">
          <div className="text-center">
            <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" aria-hidden />
            <p className="mt-2 text-sm text-muted">
              Extracting structure and comparing formats…
            </p>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-5">
          {/* Score + summary */}
          <div className={`card-shadow flex flex-wrap items-center gap-5 rounded-2xl border p-5 ${scoreBg(result.match_score)}`}>
            <div className="text-center">
              <p className={`font-display text-5xl font-bold leading-none ${scoreColor(result.match_score)}`}>
                {result.match_score}
              </p>
              <p className="mt-1 text-xs font-medium uppercase tracking-wide text-muted">
                / 100 match
              </p>
            </div>
            <div className="flex-1">
              <p className="text-sm leading-relaxed text-foreground/90">{result.summary}</p>
              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                {highCount > 0 && (
                  <span className="flex items-center gap-1 text-red-600">
                    <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                    {highCount} high
                  </span>
                )}
                {medCount > 0 && (
                  <span className="flex items-center gap-1 text-amber-600">
                    <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                    {medCount} medium
                  </span>
                )}
                {lowCount > 0 && (
                  <span className="flex items-center gap-1 text-blue-500">
                    <Info className="h-3.5 w-3.5" aria-hidden />
                    {lowCount} low
                  </span>
                )}
                {result.missing_sections.length > 0 && (
                  <span className="flex items-center gap-1 text-muted">
                    <XCircle className="h-3.5 w-3.5" aria-hidden />
                    {result.missing_sections.length} missing section
                    {result.missing_sections.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Transform download */}
          {docFile?.name.toLowerCase().endsWith(".docx") && (
            <div className="card-shadow flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/30 bg-primary/5 p-5">
              <div>
                <p className="text-sm font-medium text-foreground">
                  Download converted manuscript
                </p>
                <p className="mt-0.5 text-xs text-muted">
                  {[
                    result.heading_map.length > 0 && `${result.heading_map.length} heading${result.heading_map.length !== 1 ? "s" : ""} rewritten`,
                    result.missing_sections.length > 0 && `${result.missing_sections.length} missing section${result.missing_sections.length !== 1 ? "s" : ""} added`,
                    "sections reordered",
                    "journal styles applied",
                  ].filter(Boolean).join(" · ")}
                </p>
              </div>
              <button
                type="button"
                onClick={downloadConverted}
                disabled={transforming}
                className="flex shrink-0 items-center gap-2 rounded-xl bg-gradient-idea px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                {transforming ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    Converting…
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" aria-hidden />
                    Download Converted DOCX
                  </>
                )}
              </button>
            </div>
          )}

          {/* Journal style */}
          <StyleCard style={result.journal_style} />

          {/* Missing sections */}
          {result.missing_sections.length > 0 && (
            <div className="card-shadow rounded-2xl border border-border bg-surface p-5">
              <h2 className="mb-3 font-display text-base font-semibold">
                Missing Sections
              </h2>
              <ul className="flex flex-wrap gap-2">
                {result.missing_sections.map((s, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/5 px-3 py-1 text-sm text-red-600"
                  >
                    <XCircle className="h-3.5 w-3.5" aria-hidden />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Issues */}
          {result.issues.length > 0 && (
            <div>
              <h2 className="mb-3 font-display text-base font-semibold">
                Formatting Issues
                <span className="ml-2 text-sm font-normal text-muted">
                  ({result.issues.length} total)
                </span>
              </h2>
              <div className="space-y-3">
                {result.issues.map((issue, i) => (
                  <IssueCard key={i} issue={issue} />
                ))}
              </div>
            </div>
          )}

          {result.issues.length === 0 && result.missing_sections.length === 0 && (
            <div className="flex items-center gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
              <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-600" aria-hidden />
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                No formatting issues found — your document already matches the journal format.
              </p>
            </div>
          )}

          {/* Corrected outline */}
          {result.reformatted_outline && (
            <div className="card-shadow rounded-2xl border border-border bg-surface p-5">
              <button
                type="button"
                onClick={() => setShowOutline((o) => !o)}
                className="flex w-full items-center justify-between gap-3 text-left focus:outline-none"
              >
                <h2 className="font-display text-base font-semibold">
                  Corrected Document Outline
                </h2>
                {showOutline ? (
                  <ChevronUp className="h-4 w-4 text-muted" aria-hidden />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted" aria-hidden />
                )}
              </button>
              {showOutline && (
                <pre className="mt-3 overflow-x-auto rounded-xl border border-border bg-surface-2 p-4 text-xs leading-relaxed text-foreground/90 whitespace-pre-wrap">
                  {result.reformatted_outline}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
