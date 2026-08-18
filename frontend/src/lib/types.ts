// TS mirror of backend/schemas.py. Keep in sync.

export type Tier = "university";
export type AssignmentType =
  | "essay"
  | "research_proposal"
  | "project"
  | "presentation";

export interface Brief {
  subject: string;
  tier: Tier;
  level: string;
  interests: string;
  assignment_type: AssignmentType;
}

export interface ScoutFinding {
  title: string;
  summary: string;
  url?: string | null;
  hook: string;
}

export interface ScoutReport {
  context: string;
  findings: ScoutFinding[];
  debates: string[];
}

export type Difficulty = "approachable" | "moderate" | "ambitious";

export interface IdeaCandidate {
  id: string;
  title: string;
  statement: string;
  why_it_matters: string;
  angle: string;
  scope: string;
  difficulty: Difficulty;
}

export type MindMapNodeType =
  | "thesis"
  | "question"
  | "argument"
  | "evidence"
  | "counter";

export interface MindMapNode {
  id: string;
  label: string;
  type: MindMapNodeType;
  parent?: string | null;
  prompt: string;
  source_id?: string | null;
}

export interface MindMap {
  nodes: MindMapNode[];
}

export type SourceKind = "article" | "book" | "paper" | "web";
export type Credibility = "high" | "medium" | "unverified";

export interface Source {
  id: string;
  kind: SourceKind;
  title: string;
  authors: string;
  year: string;
  citation: string;
  url?: string | null;
  credibility: Credibility;
  why: string;
}

export interface VideoScene {
  n: number;
  visual: string;
  narration: string;
  seconds: number;
}

export interface VideoSummary {
  title: string;
  hook: string;
  scenes: VideoScene[];
  total_seconds: number;
}

export interface IdeaResult {
  idea: IdeaCandidate;
  mind_map: MindMap;
  sources: Source[];
  video: VideoSummary;
}

// --- API envelopes ---

export interface GenerateIdeasResponse {
  scout: ScoutReport;
  candidates: IdeaCandidate[];
}

export interface BuildRequest {
  brief: Brief;
  scout: ScoutReport;
  idea: IdeaCandidate;
}

export interface RefineRequest {
  brief: Brief;
  idea: IdeaCandidate;
  nudge: string;
}

// --- Corpus search (the "Corpus" tab) ---

export interface CorpusHit {
  title: string;
  openalex_id?: string | null;
  score: number;
}

export interface CorpusSearchResponse {
  status: string;
  count: number;
  results: CorpusHit[];
  message?: string | null;
}

// --- The Dojo: a written-up sample thesis, one chapter at a time. ---

export type DojoDegree = "undergraduate" | "masters" | "phd";
export type DojoLang = "en" | "bm";
export type DojoSection =
  | "title"
  | "research_questions"
  | "introduction"
  | "literature_review"
  | "methodology"
  | "results"
  | "discussion";

export interface DojoGenerateRequest {
  section: DojoSection;
  degree: DojoDegree;
  language: DojoLang;
  topic: string;
  research_questions: string;
  notes: string;
  pro?: boolean;
  session_token?: string | null;
}

export interface DojoCorpusExample {
  title: string;
  openalex_id?: string | null;
  score: number;
  authors?: string;
  year?: number | null;
  venue?: string;
  doi?: string | null;
  reference?: string;
}

export interface DojoSectionResult {
  section: DojoSection;
  heading: string;
  content: string;
  corpus_examples: DojoCorpusExample[];
  language: DojoLang;
  word_count: number;
}

// --- Community / social feature ---

export type ContributionType = "challenge" | "extend" | "source";

export interface SessionInfo {
  token: string;
  credits: number;
  dojo_quota: number;
}

export interface SharedIdea {
  id: string;
  title: string;
  statement: string;
  angle: string;
  shared_at: string;
  contribution_count: number;
}

export interface ContributionItem {
  id: string;
  type: ContributionType;
  text: string;
  quality_ok: boolean;
  credits_awarded: number;
  created_at: string;
}

export interface SharedIdeaDetail extends SharedIdea {
  contributions: ContributionItem[];
}

export interface ContributionRequest {
  idea_id: string;
  contributor_token: string;
  type: ContributionType;
  text: string;
}

export interface ContributionResult {
  id: string;
  credits_awarded: number;
  quality_ok: boolean;
  quality_reason: string;
  new_credits: number;
}

export interface CommunityFeedResponse {
  ideas: SharedIdea[];
  total: number;
}
