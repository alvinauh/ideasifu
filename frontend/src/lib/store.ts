// Lightweight module store: holds the in-flight brief/scout/candidates and the
// current IdeaResult, and persists built ideas to localStorage for the Library.
// Subscribers (via useStore) re-render on change. No external dependency.

import { useSyncExternalStore } from "react";
import type {
  Brief,
  IdeaCandidate,
  IdeaResult,
  ScoutReport,
  SessionInfo,
} from "@/lib/types";

export interface SavedIdea {
  /** Stable id for the library entry. */
  key: string;
  savedAt: number;
  brief: Brief;
  result: IdeaResult;
}

interface StoreState {
  brief: Brief | null;
  scout: ScoutReport | null;
  candidates: IdeaCandidate[];
  current: IdeaResult | null;
  library: SavedIdea[];
  session: SessionInfo | null;
  sharedIdeaIds: Set<string>;
}

const LIB_KEY = "ideasifu.library";
const SESSION_KEY = "ideasifu.session_token";

function generateToken(): string {
  // RFC-4122-ish UUID v4 without depending on crypto.randomUUID (broader compat)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function getOrCreateToken(): string {
  let token = localStorage.getItem(SESSION_KEY);
  if (!token) {
    token = generateToken();
    localStorage.setItem(SESSION_KEY, token);
  }
  return token;
}

function loadSharedIdeaIds(): Set<string> {
  try {
    const raw = localStorage.getItem("ideasifu.shared_ideas");
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

function loadLibrary(): SavedIdea[] {
  try {
    const raw = localStorage.getItem(LIB_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedIdea[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

let state: StoreState = {
  brief: null,
  scout: null,
  candidates: [],
  current: null,
  library: loadLibrary(),
  session: null,
  sharedIdeaIds: loadSharedIdeaIds(),
};

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function set(patch: Partial<StoreState>) {
  state = { ...state, ...patch };
  emit();
}

export const store = {
  getState: () => state,
  subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  setBrief(brief: Brief) {
    set({ brief });
  },
  setGeneration(scout: ScoutReport, candidates: IdeaCandidate[]) {
    set({ scout, candidates });
  },
  appendCandidates(more: IdeaCandidate[]) {
    set({ candidates: [...state.candidates, ...more] });
  },
  setCurrent(current: IdeaResult) {
    set({ current });
  },

  saveCurrentToLibrary(): void {
    if (!state.current || !state.brief) return;
    const key = `${state.current.idea.id}-${Date.now()}`;
    const entry: SavedIdea = {
      key,
      savedAt: Date.now(),
      brief: state.brief,
      result: state.current,
    };
    const library = [entry, ...state.library];
    persist(library);
    set({ library });
  },

  removeFromLibrary(key: string) {
    const library = state.library.filter((e) => e.key !== key);
    persist(library);
    set({ library });
  },

  openFromLibrary(key: string): SavedIdea | undefined {
    const entry = state.library.find((e) => e.key === key);
    if (entry) set({ brief: entry.brief, current: entry.result });
    return entry;
  },

  setSession(session: SessionInfo) {
    set({ session });
  },

  markIdeaShared(ideaId: string) {
    const next = new Set(state.sharedIdeaIds);
    next.add(ideaId);
    try {
      localStorage.setItem("ideasifu.shared_ideas", JSON.stringify([...next]));
    } catch {
      // non-fatal
    }
    set({ sharedIdeaIds: next });
  },

  isIdeaShared(ideaId: string): boolean {
    return state.sharedIdeaIds.has(ideaId);
  },
};

function persist(library: SavedIdea[]) {
  try {
    localStorage.setItem(LIB_KEY, JSON.stringify(library));
  } catch {
    // storage full / unavailable — non-fatal for a demo
  }
}

export function useStore<T>(selector: (s: StoreState) => T): T {
  return useSyncExternalStore(
    store.subscribe,
    () => selector(state),
    () => selector(state),
  );
}
