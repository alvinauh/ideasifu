// API client. If VITE_API_BASE_URL is empty/undefined, transparently fall back
// to the built-in mock client so the app is fully demoable with NO backend.

import type {
  Brief,
  CorpusSearchResponse,
  DojoGenerateRequest,
  DojoSectionResult,
  GenerateIdeasResponse,
  IdeaCandidate,
  IdeaResult,
  ScoutReport,
} from "@/lib/types";
import * as mock from "@/lib/mockApi";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
export const USING_MOCK = BASE.length === 0;

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function generateIdeas(brief: Brief): Promise<GenerateIdeasResponse> {
  if (USING_MOCK) return mock.generateIdeas(brief);
  return post<GenerateIdeasResponse>("/generate-ideas", brief);
}

export function moreIdeas(
  brief: Brief,
  scout: ScoutReport,
): Promise<IdeaCandidate[]> {
  if (USING_MOCK) return mock.moreIdeas(brief);
  return post<IdeaCandidate[]>("/more-ideas", { brief, scout });
}

export function buildIdea(
  brief: Brief,
  scout: ScoutReport,
  idea: IdeaCandidate,
): Promise<IdeaResult> {
  if (USING_MOCK) return mock.buildIdea(brief, scout, idea);
  return post<IdeaResult>("/build", { brief, scout, idea });
}

export function refineIdea(
  brief: Brief,
  idea: IdeaCandidate,
  nudge: string,
): Promise<IdeaCandidate> {
  if (USING_MOCK) return mock.refineIdea(brief, idea, nudge);
  return post<IdeaCandidate>("/refine", { brief, idea, nudge });
}

export function searchCorpus(
  query: string,
  topK = 20,
): Promise<CorpusSearchResponse> {
  if (USING_MOCK) return mock.searchCorpus(query);
  return post<CorpusSearchResponse>("/search-corpus", {
    query,
    top_k: topK,
  });
}

export function generateDojoSection(
  req: DojoGenerateRequest,
): Promise<DojoSectionResult> {
  if (USING_MOCK) return mock.generateDojoSection(req);
  return post<DojoSectionResult>("/dojo/generate", req);
}
