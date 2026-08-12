import { useTier } from "@/lib/tier";
import type { Tier } from "@/lib/types";

const OPTIONS: { value: Tier; emoji: string; label: string }[] = [
  { value: "highschool", emoji: "\u{1F392}", label: "High School" },
  { value: "university", emoji: "\u{1F393}", label: "University" },
];

/**
 * The most important control in the product: re-tunes vocabulary and rigor.
 * Segmented control, keyboard-navigable, color + emoji + label (never color
 * alone).
 */
export default function TierToggle({ size = "md" }: { size?: "md" | "sm" }) {
  const { tier, setTier } = useTier();
  const pad = size === "sm" ? "px-3 py-1.5 text-sm" : "px-5 py-2.5";

  return (
    <div
      role="radiogroup"
      aria-label="Learning level"
      className="inline-flex items-center gap-1 rounded-full border border-border bg-surface p-1"
    >
      {OPTIONS.map((opt) => {
        const active = tier === opt.value;
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            onClick={() => setTier(opt.value)}
            className={`${pad} flex items-center gap-2 rounded-full font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              active
                ? "bg-gradient-idea text-white glow"
                : "text-muted hover:text-foreground"
            }`}
          >
            <span aria-hidden>{opt.emoji}</span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
