import {
  createContext,
  useContext,
  type ReactNode,
} from "react";
import type { Tier } from "@/lib/types";

interface TierContextValue {
  tier: Tier;
  setTier: (t: Tier) => void;
  /** Tier-aware copy so screens re-tune tone, not just theme. */
  copy: TierCopy;
}

export interface TierCopy {
  /** Label for the root idea framing. */
  statementLabel: string;
  /** Landing framing question. */
  framingQuestion: string;
  /** How the crew's job is described. */
  toneWord: string;
  /** Landing hero sub-line. */
  heroSub: string;
  /** Mind-map counter-arg framing. */
  counterLabel: string;
}

const COPY: Record<Tier, TierCopy> = {
  university: {
    statementLabel: "Thesis statement",
    framingQuestion: "What gap are you addressing?",
    toneWord: "rigorous supervisor",
    heroSub:
      "From empty page to a defensible research angle — a critical-thinking map, formal references with DOIs, and a scholarly video summary.",
    counterLabel: "Counter-argument",
  },
};

const TierContext = createContext<TierContextValue | null>(null);

export function TierProvider({ children }: { children: ReactNode }) {
  const tier: Tier = "university";

  const value: TierContextValue = {
    tier,
    setTier: () => {},
    copy: COPY[tier],
  };
  return <TierContext.Provider value={value}>{children}</TierContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTier(): TierContextValue {
  const ctx = useContext(TierContext);
  if (!ctx) throw new Error("useTier must be used within TierProvider");
  return ctx;
}
