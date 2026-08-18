import { Link } from "react-router-dom";
import {
  ArrowRight,
  Lightbulb,
  GraduationCap,
  Database,
  Users,
  Coins,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { useStore } from "@/lib/store";

const TOOLS = [
  {
    id: "generate",
    href: "/dojo",
    icon: Lightbulb,
    colorVar: "var(--color-ideator)",
    label: "Generate Ideas",
    tagline: "From blank page to defensible idea",
    description:
      "Tell us your subject and level and jump straight into the Dojo — where Sensei writes up sample thesis chapters grounded in real papers, directly answering your research questions.",
    cta: "Start generating",
    badge: null,
  },
  {
    id: "dojo",
    href: "/dojo",
    icon: GraduationCap,
    colorVar: "var(--color-cartographer)",
    label: "Dojo",
    tagline: "Sample thesis sections, grounded in real papers",
    description:
      "Enter your research questions and get a capped sample write-up — introduction, literature review, methodology, and more — grounded in real papers from a 7.1-million-paper corpus.",
    cta: "Open Dojo",
    badge: "3 free sections",
  },
  {
    id: "community",
    href: "/community",
    icon: Users,
    colorVar: "var(--color-scout)",
    label: "Community",
    tagline: "Contribute anonymously, earn credits",
    description:
      "Share your idea with the community, then contribute to others'. Challenge an assumption, suggest an angle, or recommend a source. Every quality contribution earns 3 credits — each credit unlocks one more Dojo section.",
    cta: "Contribute & earn",
    badge: null,
    creditHint: true,
  },
  {
    id: "corpus",
    href: "/corpus",
    icon: Database,
    colorVar: "var(--color-librarian)",
    label: "Corpus",
    tagline: "7.1 million academic papers, searchable in seconds",
    description:
      "Semantic search over the full OpenAlex corpus, embedded with a multilingual model. Find real sources for your research in any language — Malay, English, or otherwise.",
    cta: "Search papers",
    badge: null,
  },
] as const;

export default function Landing() {
  const session = useStore((s) => s.session);

  return (
    <main className="relative overflow-hidden">
      {/* Glow backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[600px]"
        style={{ background: "var(--gradient-glow)" }}
      />

      <div className="relative mx-auto max-w-5xl px-4 pb-24 pt-14">
        {/* Hero */}
        <div className="mb-12 text-center">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
            <Sparkles className="h-3.5 w-3.5 text-[color:var(--color-librarian)]" aria-hidden />
            Your AI research crew — from idea to write-up
          </p>
          <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            What would you like to
            <br />
            <span className="text-gradient">work on today?</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted">
            IdeaSifu is a suite of AI tools for students — pick a tool below to
            get started.
          </p>
        </div>

        {/* Tool grid */}
        <div className="grid gap-4 sm:grid-cols-2">
          {TOOLS.map((tool) => {
            const Icon = tool.icon;
            return (
              <Link
                key={tool.id}
                to={tool.href}
                className="group card-shadow flex flex-col rounded-2xl border border-border bg-surface p-6 transition-colors hover:border-[color:var(--tool-color)] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                style={{ "--tool-color": tool.colorVar } as React.CSSProperties}
              >
                {/* Icon + badge row */}
                <div className="flex items-start justify-between gap-3">
                  <span
                    className="grid h-12 w-12 place-items-center rounded-xl transition-colors"
                    style={{
                      color: tool.colorVar,
                      backgroundColor: "color-mix(in oklab, currentColor 14%, transparent)",
                    }}
                  >
                    <Icon className="h-6 w-6" aria-hidden />
                  </span>
                  <div className="flex items-center gap-2">
                    {tool.badge && (
                      <span
                        className="rounded-full border px-2.5 py-0.5 text-xs font-medium"
                        style={{
                          color: tool.colorVar,
                          borderColor: "color-mix(in oklab, currentColor 30%, transparent)",
                          backgroundColor: "color-mix(in oklab, currentColor 10%, transparent)",
                        }}
                      >
                        {tool.badge}
                      </span>
                    )}
                    {"creditHint" in tool && tool.creditHint && session && (
                      <span className="flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-xs font-medium text-muted">
                        <Coins className="h-3 w-3 text-[color:var(--color-ideator)]" aria-hidden />
                        {session.credits} credits
                      </span>
                    )}
                  </div>
                </div>

                {/* Text */}
                <div className="mt-4 flex-1">
                  <p
                    className="text-xs font-medium uppercase tracking-wide"
                    style={{ color: tool.colorVar }}
                  >
                    {tool.tagline}
                  </p>
                  <h2 className="mt-1 font-display text-xl font-semibold">
                    {tool.label}
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    {tool.description}
                  </p>
                </div>

                {/* CTA */}
                <div
                  className="mt-5 flex items-center gap-1.5 text-sm font-semibold transition-colors"
                  style={{ color: tool.colorVar }}
                >
                  {tool.cta}
                  <ArrowRight
                    className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </div>
              </Link>
            );
          })}
        </div>

        {/* Library + sibling link */}
        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6">
          <Link
            to="/library"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            View your saved ideas →
          </Link>
          <a
            href="https://thesissifu.com"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-muted underline-offset-4 transition-colors hover:text-foreground hover:underline"
          >
            Already have a draft? Audit it at ThesisSifu
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          </a>
        </div>
      </div>
    </main>
  );
}
