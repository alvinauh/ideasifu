import { useState } from "react";
import {
  Book,
  FileText,
  Globe,
  GraduationCap,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Copy,
  Check,
  ExternalLink,
} from "lucide-react";
import type { Credibility, Source, SourceKind } from "@/lib/types";

const KIND_META: Record<SourceKind, { icon: typeof Book; label: string }> = {
  book: { icon: Book, label: "Book" },
  article: { icon: FileText, label: "Article" },
  paper: { icon: GraduationCap, label: "Paper" },
  web: { icon: Globe, label: "Web" },
};

const CRED_META: Record<
  Credibility,
  { icon: typeof ShieldCheck; label: string; colorVar: string }
> = {
  high: { icon: ShieldCheck, label: "High credibility", colorVar: "var(--color-success)" },
  medium: { icon: ShieldAlert, label: "Medium credibility", colorVar: "var(--color-warning)" },
  unverified: { icon: ShieldQuestion, label: "Unverified", colorVar: "var(--color-muted)" },
};

export default function SourcesPanel({
  sources,
  highlightId,
}: {
  sources: Source[];
  highlightId?: string | null;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Sources are <span className="text-foreground">things to read</span>, not
        things to quote blindly. Each one shows why it matters and how far to
        trust it.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {sources.map((s) => (
          <SourceCard key={s.id} source={s} highlighted={highlightId === s.id} />
        ))}
      </div>
    </div>
  );
}

function SourceCard({
  source,
  highlighted,
}: {
  source: Source;
  highlighted: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const kind = KIND_META[source.kind];
  const cred = CRED_META[source.credibility];
  const KindIcon = kind.icon;
  const CredIcon = cred.icon;

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(source.citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <article
      id={`source-${source.id}`}
      className="card-shadow flex flex-col rounded-2xl border bg-surface p-4 transition-shadow"
      style={
        highlighted
          ? { borderColor: "var(--color-primary)", boxShadow: "var(--shadow-glow)" }
          : undefined
      }
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-medium text-muted">
          <KindIcon className="h-4 w-4" aria-hidden />
          {kind.label}
        </span>
        <span
          className="flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
          style={{
            color: cred.colorVar,
            backgroundColor: "color-mix(in oklab, currentColor 16%, transparent)",
          }}
        >
          <CredIcon className="h-3.5 w-3.5" aria-hidden />
          {cred.label}
        </span>
      </div>

      <h3 className="mt-3 font-display text-base font-semibold leading-snug">
        {source.title}
      </h3>
      <p className="mt-1 text-xs text-muted">
        {source.authors}
        {source.year ? ` · ${source.year}` : ""}
      </p>

      <p className="mt-3 text-sm leading-relaxed text-foreground/90">
        <span className="font-medium text-[color:var(--color-librarian)]">Why: </span>
        {source.why}
      </p>

      <p className="mt-3 rounded-lg bg-surface-2 p-2.5 text-xs leading-relaxed text-muted">
        {source.citation}
      </p>

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={copyCitation}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-[color:var(--color-success)]" aria-hidden />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" aria-hidden />
              Copy citation
            </>
          )}
        </button>
        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            Open
          </a>
        )}
      </div>
    </article>
  );
}
