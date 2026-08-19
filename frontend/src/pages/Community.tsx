import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Users,
  Swords,
  TrendingUp,
  BookOpen,
  Loader2,
  Coins,
  ChevronRight,
  X,
  CheckCircle,
  XCircle,
  PenLine,
  Plus,
  Link2,
  Check,
} from "lucide-react";
import * as api from "@/lib/api";
import { store, useStore, getOrCreateToken } from "@/lib/store";
import type {
  ContributionType,
  IdeaCandidate,
  SharedIdea,
  SharedIdeaDetail,
  ContributionResult,
} from "@/lib/types";

function generateId() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const CONTRIBUTION_TYPES: {
  id: ContributionType;
  label: string;
  icon: typeof Swords;
  description: string;
  placeholder: string;
}[] = [
  {
    id: "challenge",
    label: "Challenge",
    icon: Swords,
    description: "Identify a specific assumption, limitation, or counter-argument",
    placeholder:
      "e.g. The framing assumes X, but research by Y suggests this breaks down when… because…",
  },
  {
    id: "extend",
    label: "Extend",
    icon: TrendingUp,
    description: "Propose a specific angle or sub-topic that would enrich the idea",
    placeholder:
      "e.g. This idea could be strengthened by incorporating Z dimension, specifically by examining…",
  },
  {
    id: "source",
    label: "Source",
    icon: BookOpen,
    description: "Name a specific paper, author, or journal directly relevant to this idea",
    placeholder:
      "e.g. Author et al. (Year) in [Journal] showed that… which directly supports/challenges this because…",
  },
];

export default function Community() {
  const session = useStore((s) => s.session);
  const [ideas, setIdeas] = useState<SharedIdea[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SharedIdeaDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Contribution form state
  const [contribType, setContribType] = useState<ContributionType>("challenge");
  const [contribText, setContribText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ContributionResult | null>(null);

  const token = getOrCreateToken();

  // Direct post form state
  const [showPostForm, setShowPostForm] = useState(false);
  const [postTitle, setPostTitle] = useState("");
  const [postStatement, setPostStatement] = useState("");
  const [postPosting, setPostPosting] = useState(false);
  const [postDone, setPostDone] = useState(false);

  // Shareable-link support: auto-open an idea when ?idea=<id> is in the URL
  const [searchParams, setSearchParams] = useSearchParams();

  // Init session and load feed on mount; auto-open linked idea after feed loads
  useEffect(() => {
    (async () => {
      const [, feedData] = await Promise.all([
        api.initSession(token).then((s) => store.setSession(s)),
        api.getCommunityFeed(),
      ]);
      setIdeas(feedData.ideas);
      setTotal(feedData.total);
      setLoading(false);

      const linkedId = searchParams.get("idea");
      if (linkedId) {
        setLoadingDetail(true);
        const detail = await api.getIdeaDetail(linkedId).catch(() => null);
        if (detail) setSelected(detail);
        setLoadingDetail(false);
      }
    })();
  }, []);

  async function openIdea(idea: SharedIdea) {
    setSelected(null);
    setResult(null);
    setContribText("");
    setContribType("challenge");
    setLoadingDetail(true);
    setSearchParams({ idea: idea.id }, { replace: true });
    const detail = await api.getIdeaDetail(idea.id);
    setSelected(detail);
    setLoadingDetail(false);
  }

  function closeIdea() {
    setSelected(null);
    setResult(null);
    setSearchParams({}, { replace: true });
  }

  async function handlePost(e: React.FormEvent) {
    e.preventDefault();
    if (!postTitle.trim() || !postStatement.trim()) return;
    setPostPosting(true);
    const idea: IdeaCandidate = {
      id: generateId(),
      title: postTitle.trim(),
      statement: postStatement.trim(),
      why_it_matters: postStatement.trim(),
      angle: "Open Question",
      scope: "Open",
      difficulty: "approachable",
    };
    try {
      const shared = await api.shareIdea(token, idea);
      store.markIdeaShared(shared.id);
      setIdeas((prev) => [shared, ...prev]);
      setTotal((t) => t + 1);
      setPostDone(true);
      setPostTitle("");
      setPostStatement("");
      setTimeout(() => { setPostDone(false); setShowPostForm(false); }, 3000);
    } finally {
      setPostPosting(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !contribText.trim()) return;
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.contribute({
        idea_id: selected.id,
        contributor_token: token,
        type: contribType,
        text: contribText.trim(),
      });
      setResult(res);
      // Refresh session credits
      if (res.quality_ok) {
        store.setSession({
          token,
          credits: res.new_credits,
          dojo_quota: session?.dojo_quota ?? 0,
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  const credits = session?.credits ?? 0;
  const dojoQuota = session?.dojo_quota ?? 0;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      {/* Page header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold sm:text-3xl">
            Community
          </h1>
          <p className="mt-1 text-sm text-muted">
            Contribute to a fellow student's idea anonymously — earn credits to
            unlock more Dojo sections.
          </p>
        </div>
        <SessionBadge credits={credits} dojoQuota={dojoQuota} />
      </div>

      {/* Credit explainer */}
      <div className="mb-6 rounded-2xl border border-border bg-surface p-4">
        <div className="flex flex-wrap gap-6 text-sm">
          <CreditRule
            label="New session"
            value={`${3} free Dojo sections`}
            color="var(--color-scout)"
          />
          <CreditRule
            label="Substantive contribution"
            value="+3 credits"
            color="var(--color-ideator)"
          />
          <CreditRule
            label="1 credit"
            value="= 1 extra Dojo section"
            color="var(--color-cartographer)"
          />
          <CreditRule
            label="Low-effort / filler"
            value="No credits awarded"
            color="var(--color-muted, #888)"
          />
        </div>
      </div>

      {/* Direct post form */}
      <div className="mb-6 rounded-2xl border border-border bg-surface">
        <button
          onClick={() => setShowPostForm(!showPostForm)}
          className="flex w-full items-center justify-between px-5 py-4 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-expanded={showPostForm}
        >
          <div className="flex items-center gap-2">
            <PenLine className="h-4 w-4 text-primary" aria-hidden />
            <span className="text-sm font-semibold">Post your research problem directly</span>
            <span className="hidden rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary sm:inline">
              No generation needed
            </span>
          </div>
          <Plus className={`h-4 w-4 text-muted transition-transform ${showPostForm ? "rotate-45" : ""}`} aria-hidden />
        </button>

        {showPostForm && !postDone && (
          <form onSubmit={handlePost} className="space-y-4 border-t border-border px-5 pb-5 pt-4">
            <p className="text-xs text-muted">
              Share your research question without going through idea generation — peers can Challenge, Extend, or Source directly.
            </p>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-muted">
                Research question or topic
              </label>
              <input
                value={postTitle}
                onChange={(e) => setPostTitle(e.target.value)}
                placeholder="e.g. How does social media use affect academic performance in undergraduates?"
                className="mt-1.5 w-full rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wide text-muted">
                Brief description
              </label>
              <textarea
                value={postStatement}
                onChange={(e) => setPostStatement(e.target.value)}
                placeholder="What is the core problem or angle you're exploring? What makes this interesting or challenging?"
                rows={3}
                className="mt-1.5 w-full resize-none rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!postTitle.trim() || !postStatement.trim() || postPosting}
                className="flex items-center gap-2 rounded-xl bg-gradient-idea px-5 py-2.5 text-sm font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
              >
                {postPosting ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <PenLine className="h-4 w-4" aria-hidden />
                )}
                Share to Community
              </button>
            </div>
          </form>
        )}

        {showPostForm && postDone && (
          <div className="border-t border-border px-5 pb-5 pt-4">
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4 shrink-0" aria-hidden />
              Your problem is now live in the community feed below!
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Feed panel */}
        <div>
          <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wide text-muted">
            {loading ? "Loading…" : `${total} shared idea${total !== 1 ? "s" : ""}`}
          </h2>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading community ideas…
            </div>
          ) : ideas.length === 0 ? (
            <div className="rounded-2xl border border-border bg-surface p-6 text-sm text-muted">
              No ideas shared yet. Generate an idea and share it from the Workspace!
            </div>
          ) : (
            <ul className="space-y-3">
              {ideas.map((idea) => (
                <IdeaCard
                  key={idea.id}
                  idea={idea}
                  active={selected?.id === idea.id}
                  loading={loadingDetail && selected?.id !== idea.id}
                  onClick={() => openIdea(idea)}
                />
              ))}
            </ul>
          )}
        </div>

        {/* Contribution panel */}
        <div>
          {loadingDetail && (
            <div className="flex h-48 items-center justify-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading idea…
            </div>
          )}

          {!loadingDetail && !selected && (
            <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-border text-sm text-muted">
              Select an idea on the left to contribute
            </div>
          )}

          {!loadingDetail && selected && (
            <div className="card-shadow rounded-2xl border border-border bg-surface p-5">
              {/* Idea summary */}
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted">
                    Contributing to
                  </p>
                  <h3 className="mt-1 font-display text-base font-semibold leading-snug">
                    {selected.title}
                  </h3>
                  <p className="mt-1 text-sm text-foreground/80">
                    {selected.statement}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <CopyLinkButton ideaId={selected.id} />
                  <button
                    onClick={closeIdea}
                    className="rounded-lg p-1 hover:bg-surface-2 focus:outline-none"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4 text-muted" />
                  </button>
                </div>
              </div>

              {/* Existing contributions */}
              {selected.contributions.length > 0 && (
                <div className="mb-4 space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted">
                    {selected.contributions.length} contribution
                    {selected.contributions.length !== 1 ? "s" : ""} so far
                  </p>
                  {selected.contributions.map((c) => (
                    <div
                      key={c.id}
                      className="rounded-xl border border-border bg-surface-2 p-3"
                    >
                      <div className="mb-1 flex items-center gap-2">
                        <TypePill type={c.type} />
                      </div>
                      <p className="text-xs leading-relaxed text-foreground/80">
                        {c.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Anonymous session notice */}
              {!session && (
                <div className="mb-4 rounded-xl border border-border bg-surface-2 px-4 py-3 text-xs text-muted">
                  You're contributing <strong>anonymously</strong> — your session is private to this device. No account needed.
                </div>
              )}

              {/* Contribution form */}
              {result ? (
                <ContributionFeedback
                  result={result}
                  onReset={() => {
                    setResult(null);
                    setContribText("");
                  }}
                />
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Type selector */}
                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                      Contribution type
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {CONTRIBUTION_TYPES.map((ct) => {
                        const Icon = ct.icon;
                        const active = contribType === ct.id;
                        return (
                          <button
                            key={ct.id}
                            type="button"
                            onClick={() => setContribType(ct.id)}
                            className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                              active
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border text-muted hover:text-foreground"
                            }`}
                          >
                            <Icon className="h-3.5 w-3.5" aria-hidden />
                            {ct.label}
                          </button>
                        );
                      })}
                    </div>
                    <p className="mt-1.5 text-xs text-muted">
                      {CONTRIBUTION_TYPES.find((t) => t.id === contribType)?.description}
                    </p>
                  </div>

                  {/* Text area */}
                  <textarea
                    value={contribText}
                    onChange={(e) => setContribText(e.target.value)}
                    placeholder={
                      CONTRIBUTION_TYPES.find((t) => t.id === contribType)?.placeholder
                    }
                    rows={4}
                    className="w-full resize-none rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm text-foreground placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />

                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-muted">
                      Be specific — vague or empty contributions earn no credits.
                    </p>
                    <button
                      type="submit"
                      disabled={!contribText.trim() || submitting}
                      className="flex shrink-0 items-center gap-2 rounded-xl bg-gradient-idea px-5 py-2.5 text-sm font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
                    >
                      {submitting ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      ) : (
                        <Coins className="h-4 w-4" aria-hidden />
                      )}
                      Submit
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CopyLinkButton({ ideaId }: { ideaId: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    const url = `${window.location.origin}/community?idea=${ideaId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button
      onClick={copy}
      title={copied ? "Link copied!" : "Copy shareable link"}
      className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-muted hover:bg-surface-2 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-green-500" aria-hidden />
          <span className="text-green-500">Copied!</span>
        </>
      ) : (
        <>
          <Link2 className="h-3.5 w-3.5" aria-hidden />
          <span>Share</span>
        </>
      )}
    </button>
  );
}

function SessionBadge({ credits, dojoQuota }: { credits: number; dojoQuota: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-sm">
        <Coins className="h-4 w-4 text-[color:var(--color-ideator)]" aria-hidden />
        <span className="font-semibold">{credits}</span>
        <span className="text-muted">credits</span>
      </div>
      <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-sm">
        <span className="font-semibold">{dojoQuota}</span>
        <span className="text-muted">Dojo left</span>
      </div>
    </div>
  );
}

function CreditRule({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ background: color }}
      />
      <span className="text-muted">{label}:</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function IdeaCard({
  idea,
  active,
  loading,
  onClick,
}: {
  idea: SharedIdea;
  active: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  const [copied, setCopied] = useState(false);

  function handleShare(e: React.MouseEvent) {
    e.stopPropagation();
    const url = `${window.location.origin}/community?idea=${idea.id}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <li>
      <button
        onClick={onClick}
        disabled={loading}
        className={`w-full rounded-2xl border p-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
          active
            ? "border-primary bg-surface"
            : "border-border bg-surface hover:bg-surface-2"
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-display text-sm font-semibold leading-snug">
              {idea.title}
            </p>
            <p className="mt-1 line-clamp-2 text-xs text-muted">
              {idea.statement}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
              <span className="rounded-md border border-border px-2 py-0.5">
                {idea.angle}
              </span>
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" aria-hidden />
                {idea.contribution_count} contribution
                {idea.contribution_count !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button
              onClick={handleShare}
              title="Copy shareable link"
              className="rounded-lg p-1.5 text-muted hover:bg-surface-2 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label="Copy shareable link"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-green-500" aria-hidden />
              ) : (
                <Link2 className="h-3.5 w-3.5" aria-hidden />
              )}
            </button>
            <ChevronRight
              className={`h-4 w-4 transition-colors ${active ? "text-primary" : "text-muted"}`}
              aria-hidden
            />
          </div>
        </div>
      </button>
    </li>
  );
}

function TypePill({ type }: { type: ContributionType }) {
  const meta = CONTRIBUTION_TYPES.find((t) => t.id === type)!;
  const Icon = meta.icon;
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-xs font-medium text-muted">
      <Icon className="h-3 w-3" aria-hidden />
      {meta.label}
    </span>
  );
}

function ContributionFeedback({
  result,
  onReset,
}: {
  result: ContributionResult;
  onReset: () => void;
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        result.quality_ok
          ? "border-green-500/30 bg-green-500/10"
          : "border-border bg-surface-2"
      }`}
    >
      <div className="flex items-start gap-3">
        {result.quality_ok ? (
          <CheckCircle className="h-5 w-5 shrink-0 text-green-500" aria-hidden />
        ) : (
          <XCircle className="h-5 w-5 shrink-0 text-muted" aria-hidden />
        )}
        <div className="flex-1">
          {result.quality_ok ? (
            <>
              <p className="text-sm font-semibold text-green-600 dark:text-green-400">
                +{result.credits_awarded} credits earned
              </p>
              <p className="mt-0.5 text-xs text-muted">
                You now have <strong>{result.new_credits}</strong> credits total.
                Each credit unlocks one extra Dojo section.
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold">No credits this time</p>
              <p className="mt-0.5 text-xs text-muted">{result.quality_reason}</p>
            </>
          )}
        </div>
      </div>
      <button
        onClick={onReset}
        className="mt-3 text-xs font-medium text-primary hover:underline focus:outline-none"
      >
        Contribute again
      </button>
    </div>
  );
}
