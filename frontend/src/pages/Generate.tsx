import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Loader2, Users } from "lucide-react";
import AgentFeed, { type AgentStatus } from "@/components/AgentFeed";
import IdeaCandidateCard from "@/components/IdeaCandidateCard";
import { AGENTS, type AgentId } from "@/data/agents";
import { store, useStore } from "@/lib/store";
import * as api from "@/lib/api";
import { useTier } from "@/lib/tier";
import type { IdeaCandidate } from "@/lib/types";

type Phase = "generating" | "choosing" | "building";

const IDEATE_AGENTS = AGENTS.filter(
  (a) => a.id === "scout" || a.id === "ideator",
);
const BUILD_AGENTS = AGENTS.filter(
  (a) => a.id === "cartographer" || a.id === "librarian" || a.id === "director",
);

function initialStatus(): Record<AgentId, AgentStatus> {
  return {
    scout: "pending",
    ideator: "pending",
    cartographer: "pending",
    librarian: "pending",
    director: "pending",
  };
}

export default function Generate() {
  const navigate = useNavigate();
  const { copy } = useTier();
  const brief = useStore((s) => s.brief);
  const scout = useStore((s) => s.scout);
  const candidates = useStore((s) => s.candidates);

  const [phase, setPhase] = useState<Phase>("generating");
  const [status, setStatus] = useState<Record<AgentId, AgentStatus>>(
    initialStatus,
  );
  const [loadingMore, setLoadingMore] = useState(false);
  const startedRef = useRef(false);

  const setAgent = useCallback((id: AgentId, s: AgentStatus) => {
    setStatus((prev) => ({ ...prev, [id]: s }));
  }, []);

  // If someone lands here without a brief, send them home.
  useEffect(() => {
    if (!brief) navigate("/", { replace: true });
  }, [brief, navigate]);

  // Kick off generation once.
  useEffect(() => {
    if (!brief || startedRef.current) return;
    startedRef.current = true;

    (async () => {
      setAgent("scout", "active");
      const res = await api.generateIdeas(brief);
      // Scout finishes first, then Ideator (mock has staged delays; we reflect
      // the handoff visually here).
      setAgent("scout", "done");
      setAgent("ideator", "active");
      await new Promise((r) => setTimeout(r, 500));
      store.setGeneration(res.scout, res.candidates);
      setAgent("ideator", "done");
      setPhase("choosing");
    })();
  }, [brief, setAgent]);

  async function handleShowMore() {
    if (!brief || !scout) return;
    setLoadingMore(true);
    const more = await api.moreIdeas(brief, scout);
    store.appendCandidates(more);
    setLoadingMore(false);
  }

  async function handleChoose(idea: IdeaCandidate) {
    if (!brief || !scout) return;
    setPhase("building");

    setAgent("cartographer", "active");
    // Sequence the three build agents' visuals against the staged mock delays.
    const buildPromise = api.buildIdea(brief, scout, idea);
    await new Promise((r) => setTimeout(r, 800));
    setAgent("cartographer", "done");
    setAgent("librarian", "active");
    await new Promise((r) => setTimeout(r, 700));
    setAgent("librarian", "done");
    setAgent("director", "active");
    const result = await buildPromise;
    await new Promise((r) => setTimeout(r, 400));
    setAgent("director", "done");

    store.setCurrent(result);
    navigate("/idea");
  }

  if (!brief) return null;

  const activeAgents = phase === "building" ? BUILD_AGENTS : IDEATE_AGENTS;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-8">
        <p className="text-sm text-muted">
          {phase === "building" ? "Building your idea" : "Generating ideas for"}
        </p>
        <h1 className="font-display text-2xl font-semibold sm:text-3xl">
          <span className="text-gradient">{brief.subject}</span>
        </h1>
        <p className="mt-1 text-sm text-muted">
          {brief.tier === "university" ? "University" : "High school"} ·{" "}
          {brief.level} · {labelForAssignment(brief.assignment_type)}
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,360px)_1fr]">
        {/* Crew feed */}
        <section aria-label="Agent activity">
          <h2 className="mb-3 flex items-center gap-2 font-display text-sm font-medium uppercase tracking-wider text-muted">
            <Users className="h-4 w-4" aria-hidden />
            The crew at work
          </h2>
          <AgentFeed agents={activeAgents} status={status} />

          {scout && (
            <div className="card-shadow mt-4 rounded-xl border border-border bg-surface p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--color-scout)]">
                Scout's read of the field
              </p>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {scout.context}
              </p>
              {scout.debates.length > 0 && (
                <>
                  <p className="mt-3 text-xs font-medium uppercase tracking-wide text-muted">
                    Live debates
                  </p>
                  <ul className="mt-1.5 space-y-1 text-sm text-muted">
                    {scout.debates.map((d, i) => (
                      <li key={i} className="flex gap-2">
                        <span aria-hidden className="text-[color:var(--color-scout)]">
                          ·
                        </span>
                        {d}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </section>

        {/* Candidates / status */}
        <section aria-label="Idea candidates" aria-live="polite">
          {phase === "generating" && (
            <div className="grid h-full min-h-[300px] place-items-center rounded-2xl border border-dashed border-border">
              <div className="text-center">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" aria-hidden />
                <p className="mt-3 text-sm text-muted">
                  Scouting the field, then shaping three distinct ideas…
                </p>
              </div>
            </div>
          )}

          {phase === "choosing" && (
            <>
              <div className="mb-4">
                <h2 className="font-display text-xl font-semibold">
                  Pick an idea to build
                </h2>
                <p className="mt-1 text-sm text-muted">
                  Choosing is a teaching act — compare the framings, then commit
                  to the one you'd most enjoy defending. Nothing here is final.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {candidates.map((c, i) => (
                  <IdeaCandidateCard
                    key={c.id}
                    candidate={c}
                    index={i}
                    onChoose={handleChoose}
                  />
                ))}
              </div>
              <button
                onClick={handleShowMore}
                disabled={loadingMore}
                className="mt-5 flex items-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
              >
                {loadingMore ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Plus className="h-4 w-4" aria-hidden />
                )}
                Show 3 more
              </button>
            </>
          )}

          {phase === "building" && (
            <div className="grid h-full min-h-[300px] place-items-center rounded-2xl border border-dashed border-border">
              <div className="max-w-sm text-center">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" aria-hidden />
                <p className="mt-3 font-display font-medium">
                  Building your {copy.statementLabel.toLowerCase()}
                </p>
                <p className="mt-1 text-sm text-muted">
                  Mapping the thinking, gathering sources, and filming the
                  summary…
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function labelForAssignment(t: string): string {
  switch (t) {
    case "research_proposal":
      return "Research proposal";
    case "project":
      return "Project";
    case "presentation":
      return "Presentation";
    default:
      return "Essay";
  }
}
