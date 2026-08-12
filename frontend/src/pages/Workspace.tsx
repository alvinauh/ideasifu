import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Lightbulb,
  Network,
  BookMarked,
  Clapperboard,
  Compass,
  Ruler,
  Sparkles,
  Save,
  Check,
  Loader2,
} from "lucide-react";
import MindMap from "@/components/MindMap";
import SourcesPanel from "@/components/SourcesPanel";
import VideoPlayer from "@/components/VideoPlayer";
import { store, useStore } from "@/lib/store";
import { useTier } from "@/lib/tier";
import * as api from "@/lib/api";

type Tab = "idea" | "map" | "sources" | "video";

const TABS: { id: Tab; label: string; icon: typeof Lightbulb; colorVar: string }[] = [
  { id: "idea", label: "Idea", icon: Lightbulb, colorVar: "var(--color-ideator)" },
  { id: "map", label: "Mind map", icon: Network, colorVar: "var(--color-cartographer)" },
  { id: "sources", label: "Sources", icon: BookMarked, colorVar: "var(--color-librarian)" },
  { id: "video", label: "Video", icon: Clapperboard, colorVar: "var(--color-director)" },
];

export default function Workspace() {
  const navigate = useNavigate();
  const { copy } = useTier();
  const current = useStore((s) => s.current);
  const brief = useStore((s) => s.brief);

  const [tab, setTab] = useState<Tab>("idea");
  const [highlightSource, setHighlightSource] = useState<string | null>(null);
  const [nudge, setNudge] = useState("");
  const [refining, setRefining] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!current) navigate("/", { replace: true });
  }, [current, navigate]);

  if (!current || !brief) return null;
  const { idea, mind_map, sources, video } = current;

  function goToSource(id: string) {
    setTab("sources");
    setHighlightSource(id);
    setTimeout(() => {
      document
        .getElementById(`source-${id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  }

  async function handleRefine(e: React.FormEvent) {
    e.preventDefault();
    if (!nudge.trim() || !brief || !current) return;
    setRefining(true);
    const refined = await api.refineIdea(brief, current.idea, nudge.trim());
    // Rebuild the full payload around the refined idea so map/sources/video stay
    // coherent with the new framing.
    const rebuilt = await api.buildIdea(
      brief,
      store.getState().scout ?? { context: "", findings: [], debates: [] },
      refined,
    );
    store.setCurrent(rebuilt);
    setNudge("");
    setRefining(false);
    setSaved(false);
  }

  function handleSave() {
    store.saveCurrentToLibrary();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      {/* Header = contextualized idea */}
      <header className="card-shadow rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[color:var(--color-librarian)]">
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              A starting point to defend — not a finished answer
            </p>
            <h1 className="mt-2 font-display text-2xl font-semibold leading-tight sm:text-3xl">
              {idea.title}
            </h1>
            <p className="mt-3 text-xs font-medium uppercase tracking-wide text-muted">
              {copy.statementLabel}
            </p>
            <p className="mt-1 text-lg leading-relaxed text-foreground/90">
              {idea.statement}
            </p>
          </div>
          <button
            onClick={handleSave}
            className="flex shrink-0 items-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            {saved ? (
              <>
                <Check className="h-4 w-4 text-[color:var(--color-success)]" aria-hidden />
                Saved
              </>
            ) : (
              <>
                <Save className="h-4 w-4" aria-hidden />
                Save to Library
              </>
            )}
          </button>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <Meta icon={Sparkles} label="Why it matters" value={idea.why_it_matters} />
          <Meta icon={Compass} label="Angle" value={idea.angle} />
          <Meta icon={Ruler} label="Scope" value={idea.scope} />
        </div>

        {/* Refine */}
        <form onSubmit={handleRefine} className="mt-5 flex flex-wrap gap-2">
          <input
            value={nudge}
            onChange={(e) => setNudge(e.target.value)}
            placeholder="Refine: e.g. make it more local, add an ethics angle…"
            className="min-w-0 flex-1 rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <button
            type="submit"
            disabled={!nudge.trim() || refining}
            className="flex items-center gap-2 rounded-xl bg-gradient-idea px-5 py-2.5 text-sm font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
          >
            {refining ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Lightbulb className="h-4 w-4" aria-hidden />
            )}
            Refine
          </button>
        </form>
      </header>

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="Idea workspace panels"
        className="mt-6 flex flex-wrap gap-2"
      >
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={active}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                active
                  ? "border-transparent bg-surface"
                  : "border-border text-muted hover:text-foreground"
              }`}
              style={active ? { boxShadow: `0 0 0 1px ${t.colorVar}` } : undefined}
            >
              <Icon
                className="h-4 w-4"
                style={{ color: active ? t.colorVar : undefined }}
                aria-hidden
              />
              {t.label}
            </button>
          );
        })}
      </div>

      <section className="mt-5" role="tabpanel">
        {tab === "idea" && <IdeaPanel />}
        {tab === "map" && (
          <MindMap data={mind_map} sources={sources} onGoToSource={goToSource} />
        )}
        {tab === "sources" && (
          <SourcesPanel sources={sources} highlightId={highlightSource} />
        )}
        {tab === "video" && <VideoPlayer video={video} />}
      </section>
    </main>
  );

  function IdeaPanel() {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="The framing" colorVar="var(--color-ideator)">
          <p className="text-sm leading-relaxed text-foreground/90">
            {idea.statement}
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Treat this as a claim to test, sharpen, and defend. Open the mind map
            to see the reasons, evidence, and — importantly — the
            counter-arguments you'll need to answer.
          </p>
        </Card>
        <Card title="Why it matters" colorVar="var(--color-librarian)">
          <p className="text-sm leading-relaxed text-foreground/90">
            {idea.why_it_matters}
          </p>
        </Card>
        <Card title="Angle" colorVar="var(--color-scout)">
          <p className="text-sm leading-relaxed text-foreground/90">{idea.angle}</p>
        </Card>
        <Card title="Scope" colorVar="var(--color-cartographer)">
          <p className="text-sm leading-relaxed text-foreground/90">{idea.scope}</p>
          <p className="mt-2 text-xs text-muted">
            {brief!.tier === "university"
              ? "Keep the scope tight enough to defend with real evidence."
              : "A smaller, well-explored idea beats a big, vague one."}
          </p>
        </Card>
      </div>
    );
  }
}

function Meta({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Lightbulb;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-2 p-3">
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {label}
      </p>
      <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{value}</p>
    </div>
  );
}

function Card({
  title,
  colorVar,
  children,
}: {
  title: string;
  colorVar: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card-shadow rounded-2xl border border-border bg-surface p-5">
      <h3 className="font-display text-sm font-semibold uppercase tracking-wide" style={{ color: colorVar }}>
        {title}
      </h3>
      <div className="mt-2">{children}</div>
    </div>
  );
}
