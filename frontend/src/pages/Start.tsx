import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import TierToggle from "@/components/TierToggle";
import { AGENTS } from "@/data/agents";
import { useTier } from "@/lib/tier";
import { store } from "@/lib/store";
import type { AssignmentType, Brief } from "@/lib/types";

const ASSIGNMENT_OPTIONS: { value: AssignmentType; label: string }[] = [
  { value: "essay", label: "Essay" },
  { value: "research_proposal", label: "Research proposal" },
  { value: "project", label: "Project" },
  { value: "presentation", label: "Presentation" },
];

export default function Start() {
  const navigate = useNavigate();
  const { tier, copy } = useTier();

  const [subject, setSubject] = useState("");
  const [interests, setInterests] = useState("");
  const [level, setLevel] = useState("");
  const [assignment, setAssignment] = useState<AssignmentType>("essay");

  function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim()) return;
    const brief: Brief = {
      subject: subject.trim(),
      tier,
      level: level.trim() || "Undergraduate",
      interests: interests.trim(),
      assignment_type: assignment,
    };
    store.setBrief(brief);
    navigate("/dojo");
  }

  return (
    <main className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[520px]"
        style={{ background: "var(--gradient-glow)" }}
      />

      <div className="relative mx-auto max-w-4xl px-4 pb-24 pt-14 text-center">
        <div className="mb-8 flex justify-center">
          <TierToggle />
        </div>

        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
          <Sparkles className="h-3.5 w-3.5 text-[color:var(--color-librarian)]" aria-hidden />
          Your {copy.toneWord}, from blank page to defensible idea
        </p>

        <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
          Beat the blank page.
          <br />
          <span className="text-gradient">Spark your next idea.</span>
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted">
          {copy.heroSub}
        </p>

        <form
          onSubmit={handleGenerate}
          className="card-shadow mx-auto mt-10 max-w-2xl rounded-2xl border border-border bg-surface p-5 text-left"
        >
          <label className="block text-sm font-medium text-muted" htmlFor="subject">
            {copy.framingQuestion}
          </label>
          <input
            id="subject"
            autoFocus
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. climate change in Southeast Asia"
            className="mt-2 w-full rounded-xl border border-border bg-surface-2 px-4 py-3 text-lg text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          />

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-muted" htmlFor="interests">
                Interests / angle <span className="text-muted/60">(optional)</span>
              </label>
              <input
                id="interests"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="e.g. fishing communities, tech"
                className="mt-2 w-full rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted" htmlFor="level">
                Exact level <span className="text-muted/60">(optional)</span>
              </label>
              <input
                id="level"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                placeholder={tier === "university" ? "Year 2 undergraduate" : "Form 5"}
                className="mt-2 w-full rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
          </div>

          <fieldset className="mt-4">
            <legend className="mb-2 text-sm font-medium text-muted">
              Assignment type
            </legend>
            <div className="flex flex-wrap gap-2">
              {ASSIGNMENT_OPTIONS.map((opt) => {
                const active = assignment === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setAssignment(opt.value)}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      active
                        ? "border-primary bg-primary/15 text-foreground"
                        : "border-border text-muted hover:text-foreground"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <button
            type="submit"
            disabled={!subject.trim()}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-idea px-6 py-3.5 text-base font-semibold text-white transition-transform hover:scale-[1.01] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
          >
            Generate ideas
            <ArrowRight className="h-5 w-5" aria-hidden />
          </button>
        </form>

        <section className="mt-16" aria-labelledby="crew-heading">
          <h2 id="crew-heading" className="font-display text-sm font-medium uppercase tracking-wider text-muted">
            Your crew of five specialist Sifus
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {AGENTS.map((a) => {
              const Icon = a.icon;
              return (
                <div
                  key={a.id}
                  className="card-shadow rounded-xl border border-border bg-surface p-4 text-left"
                >
                  <span
                    className="grid h-9 w-9 place-items-center rounded-lg"
                    style={{
                      color: a.colorVar,
                      backgroundColor: "color-mix(in oklab, currentColor 16%, transparent)",
                    }}
                  >
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <p className="mt-3 font-display text-sm font-semibold" style={{ color: a.colorVar }}>
                    {a.name}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{a.tagline}</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
