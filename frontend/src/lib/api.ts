// API client. If VITE_API_BASE_URL is empty/undefined, transparently fall back
// to the built-in mock client so the app is fully demoable with NO backend.

import type {
  Brief,
  CommunityFeedResponse,
  ContributionRequest,
  ContributionResult,
  CorpusSearchResponse,
  DojoGenerateRequest,
  DojoSectionResult,
  FormatMatchResponse,
  HeadingReplacement,
  GenerateIdeasResponse,
  IdeaCandidate,
  IdeaResult,
  ScoutReport,
  SessionInfo,
  SharedIdea,
  SharedIdeaDetail,
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
    const detail = await res.json().catch(() => ({}));
    const msg = (detail as { detail?: string }).detail ?? res.statusText;
    const err = new Error(msg) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return (await res.json()) as T;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API GET ${path} failed: ${res.status}`);
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

// --- Community / social endpoints ---

export function initSession(token: string): Promise<SessionInfo> {
  if (USING_MOCK) return Promise.resolve({ token, credits: 6, dojo_quota: 3 });
  return post<SessionInfo>("/session/init", { token });
}

export function getSession(token: string): Promise<SessionInfo> {
  if (USING_MOCK) return Promise.resolve({ token, credits: 6, dojo_quota: 3 });
  return get<SessionInfo>(`/session/${token}`);
}

export function shareIdea(
  sessionToken: string,
  idea: IdeaCandidate,
): Promise<SharedIdea> {
  if (USING_MOCK) {
    return Promise.resolve({
      id: idea.id,
      title: idea.title,
      statement: idea.statement,
      angle: idea.angle,
      shared_at: new Date().toISOString(),
      contribution_count: 0,
    });
  }
  return post<SharedIdea>("/community/share", { session_token: sessionToken, idea });
}

export function getCommunityFeed(
  limit = 20,
  offset = 0,
): Promise<CommunityFeedResponse> {
  if (USING_MOCK) return mock.getCommunityFeed();
  return get<CommunityFeedResponse>(
    `/community/feed?limit=${limit}&offset=${offset}`,
  );
}

export function getIdeaDetail(ideaId: string): Promise<SharedIdeaDetail> {
  if (USING_MOCK) return mock.getIdeaDetail(ideaId);
  return get<SharedIdeaDetail>(`/community/idea/${ideaId}`);
}

export function contribute(req: ContributionRequest): Promise<ContributionResult> {
  if (USING_MOCK) return mock.contribute(req);
  return post<ContributionResult>("/community/contribute", req);
}

// --- FormatSifu: journal format matching ---

export async function formatMatch(
  journalFile: File,
  documentFile: File,
): Promise<FormatMatchResponse> {
  if (USING_MOCK) {
    return Promise.reject(new Error("Format matching requires the live backend."));
  }
  const form = new FormData();
  form.append("journal_file", journalFile);
  form.append("document_file", documentFile);
  const res = await fetch(`${BASE}/format-match`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const msg = (detail as { detail?: string }).detail ?? res.statusText;
    throw Object.assign(new Error(msg), { status: res.status });
  }
  return res.json() as Promise<FormatMatchResponse>;
}

export async function formatTransform(
  documentFile: File,
  headingMap: HeadingReplacement[],
  sectionOrder: string[],
  missingSections: string[],
): Promise<Blob> {
  if (USING_MOCK) {
    return Promise.reject(new Error("Format transform requires the live backend."));
  }
  const form = new FormData();
  form.append("document_file", documentFile);
  form.append("heading_map", JSON.stringify(headingMap));
  form.append("section_order", JSON.stringify(sectionOrder));
  form.append("missing_sections", JSON.stringify(missingSections));
  const res = await fetch(`${BASE}/format-transform`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const msg = (detail as { detail?: string }).detail ?? res.statusText;
    throw Object.assign(new Error(msg), { status: res.status });
  }
  return res.blob();
}
