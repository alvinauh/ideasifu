import {
  createContext,
  useContext,
  useEffect,
  useState,
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
  highschool: {
    statementLabel: "Guiding question",
    framingQuestion: "What are you curious about?",
    toneWord: "warm coach",
    heroSub:
      "Go from a blank page to a real idea you can defend — with a thinking map, sources to read, and a short video that explains it.",
    counterLabel: "But wait...",
  },
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
const STORAGE_KEY = "ideasifu.tier";

export function TierProvider({ children }: { children: ReactNode }) {
  const [tier, setTierState] = useState<Tier>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "university" ? "university" : "highschool";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, tier);
  }, [tier]);

  const value: TierContextValue = {
    tier,
    setTier: setTierState,
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
