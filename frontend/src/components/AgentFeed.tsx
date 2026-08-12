import { Check, Loader2 } from "lucide-react";
import type { Agent, AgentId } from "@/data/agents";

export type AgentStatus = "pending" | "active" | "done";

interface AgentFeedProps {
  agents: Agent[];
  status: Record<AgentId, AgentStatus>;
}

/** Live activity feed: each Sifu lights up (pulse-glow in its hue), streams its
 * statusVerb, then marks done. Color + icon + label together. */
export default function AgentFeed({ agents, status }: AgentFeedProps) {
  return (
    <ol className="space-y-3">
      {agents.map((a) => {
        const st = status[a.id];
        const Icon = a.icon;
        const isActive = st === "active";
        const isDone = st === "done";
        return (
          <li
            key={a.id}
            className={`card-shadow flex items-center gap-4 rounded-xl border bg-surface p-4 transition-all ${
              isActive ? "border-transparent" : "border-border"
            } ${st === "pending" ? "opacity-50" : "opacity-100"}`}
            style={
              isActive
                ? { boxShadow: `0 0 0 1px ${a.colorVar}, 0 0 28px -6px ${a.colorVar}` }
                : undefined
            }
          >
            <span
              className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${
                isActive ? "animate-pulse-glow" : ""
              }`}
              style={{
                color: a.colorVar,
                backgroundColor: "color-mix(in oklab, currentColor 16%, transparent)",
              }}
            >
              <Icon className="h-5 w-5" aria-hidden />
            </span>

            <div className="min-w-0 flex-1">
              <p className="font-display text-sm font-semibold" style={{ color: a.colorVar }}>
                {a.name}
              </p>
              <p className="truncate text-sm text-muted">
                {isDone ? "Done" : isActive ? `${a.statusVerb}…` : a.tagline}
              </p>
            </div>

            <span className="shrink-0">
              {isDone ? (
                <span className="flex items-center gap-1 text-xs font-medium text-[color:var(--color-success)]">
                  <Check className="h-4 w-4" aria-hidden />
                  <span className="sr-only sm:not-sr-only">Done</span>
                </span>
              ) : isActive ? (
                <Loader2
                  className="h-5 w-5 animate-spin"
                  style={{ color: a.colorVar }}
                  aria-label="Working"
                />
              ) : (
                <span className="text-xs text-muted">Waiting</span>
              )}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
