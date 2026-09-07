import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Sparkles, Library as LibraryIcon, Database, FileText, GraduationCap, Users, Coins } from "lucide-react";
import TierToggle from "@/components/TierToggle";
import { USING_MOCK } from "@/lib/api";
import { store, useStore, getOrCreateToken } from "@/lib/store";
import * as api from "@/lib/api";

export default function SiteHeader() {
  const { pathname } = useLocation();
  const onLanding = pathname === "/" || pathname === "/start";
  const session = useStore((s) => s.session);

  // Init session once on mount so credits are available everywhere
  useEffect(() => {
    const token = getOrCreateToken();
    api.initSession(token).then((s) => store.setSession(s)).catch(() => {});
  }, []);

  const credits = session?.credits ?? 0;
  const dojoQuota = session?.dojo_quota ?? 0;
  const showQuota = session !== null;

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2 focus:outline-none">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-idea glow">
            <Sparkles className="h-5 w-5 text-white" aria-hidden />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">
            Idea<span className="text-gradient">Sifu</span>
          </span>
          {USING_MOCK && (
            <span
              title="No backend configured — using built-in demo data"
              className="ml-1 rounded-full border border-border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted"
            >
              Demo
            </span>
          )}
        </Link>

        <div className="flex items-center gap-3">
          {showQuota && (
            <Link
              to="/community"
              title={`${credits} credits · ${dojoQuota} Dojo sections remaining`}
              className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1.5 text-xs font-medium transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary text-muted"
            >
              <Coins className="h-3.5 w-3.5 text-[color:var(--color-ideator)]" aria-hidden />
              {credits}
            </Link>
          )}
          {!onLanding && <TierToggle size="sm" />}
          <Link
            to="/format"
            className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              pathname === "/format" ? "text-foreground" : "text-muted"
            }`}
          >
            <FileText className="h-4 w-4" aria-hidden />
            Format
          </Link>
          <Link
            to="/community"
            className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              pathname === "/community" ? "text-foreground" : "text-muted"
            }`}
          >
            <Users className="h-4 w-4" aria-hidden />
            Community
          </Link>
          <Link
            to="/dojo"
            className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              pathname === "/dojo" ? "text-foreground" : "text-muted"
            }`}
          >
            <GraduationCap className="h-4 w-4" aria-hidden />
            Dojo
          </Link>
          <Link
            to="/corpus"
            className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              pathname === "/corpus" ? "text-foreground" : "text-muted"
            }`}
          >
            <Database className="h-4 w-4" aria-hidden />
            Corpus
          </Link>
          <Link
            to="/library"
            className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              pathname === "/library" ? "text-foreground" : "text-muted"
            }`}
          >
            <LibraryIcon className="h-4 w-4" aria-hidden />
            Library
          </Link>
        </div>
      </div>
    </header>
  );
}
