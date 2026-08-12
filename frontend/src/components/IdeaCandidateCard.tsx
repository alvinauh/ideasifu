import { Target, Compass, Ruler, ArrowRight } from "lucide-react";
import type { Difficulty, IdeaCandidate } from "@/lib/types";
import { useTier } from "@/lib/tier";

const DIFFICULTY_META: Record<Difficulty, { label: string; color: string }> = {
  approachable: { label: "Approachable", color: "var(--color-success)" },
  moderate: { label: "Moderate", color: "var(--color-scout)" },
  ambitious: { label: "Ambitious", color: "var(--color-warning)" },
};

interface Props {
  candidate: IdeaCandidate;
  index: number;
  onChoose: (c: IdeaCandidate) => void;
  disabled?: boolean;
}

export default function IdeaCandidateCard({
  candidate,
  index,
  onChoose,
  disabled,
}: Props) {
  const { copy } = useTier();
  const diff = DIFFICULTY_META[candidate.difficulty];

  return (
    <article
      className="card-shadow animate-rise-in flex flex-col rounded-2xl border border-border bg-surface p-5"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-medium"
          style={{
            color: diff.color,
            backgroundColor: "color-mix(in oklab, currentColor 16%, transparent)",
          }}
        >
          {diff.label}
        </span>
        <span className="text-xs font-medium text-muted">Option {index + 1}</span>
      </div>

      <h3 className="mt-3 font-display text-lg font-semibold leading-snug">
        {candidate.title}
      </h3>

      <p className="mt-2 text-xs font-medium uppercase tracking-wide text-muted">
        {copy.statementLabel}
      </p>
      <p className="mt-1 text-sm leading-relaxed text-foreground/90">
        {candidate.statement}
      </p>

      <p className="mt-3 text-sm leading-relaxed text-muted">
        {candidate.why_it_matters}
      </p>

      <dl className="mt-4 space-y-2 text-xs text-muted">
        <div className="flex items-start gap-2">
          <Compass className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <div>
            <dt className="sr-only">Angle</dt>
            <dd>
              <span className="font-medium text-foreground/80">Angle:</span>{" "}
              {candidate.angle}
            </dd>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Ruler className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <div>
            <dt className="sr-only">Scope</dt>
            <dd>
              <span className="font-medium text-foreground/80">Scope:</span>{" "}
              {candidate.scope}
            </dd>
          </div>
        </div>
      </dl>

      <button
        onClick={() => onChoose(candidate)}
        disabled={disabled}
        className="mt-5 flex items-center justify-center gap-2 rounded-xl border border-primary bg-primary/15 px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-primary/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Target className="h-4 w-4" aria-hidden />
        Build this idea
        <ArrowRight className="h-4 w-4" aria-hidden />
      </button>
    </article>
  );
}
