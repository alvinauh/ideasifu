import {
  Compass,
  Lightbulb,
  Network,
  BookMarked,
  Clapperboard,
  type LucideIcon,
} from "lucide-react";

export type AgentId =
  | "scout"
  | "ideator"
  | "cartographer"
  | "librarian"
  | "director";

export interface Agent {
  id: AgentId;
  name: string;
  icon: LucideIcon;
  /** CSS var name for this agent's signature hue. */
  colorVar: string;
  tagline: string;
  /** Student-facing present-continuous status shown while it works. */
  statusVerb: string;
}

export const AGENTS: Agent[] = [
  {
    id: "scout",
    name: "Scout",
    icon: Compass,
    colorVar: "var(--color-scout)",
    tagline: "Crawls the web for context, debates, and real-world hooks.",
    statusVerb: "Scouting the field",
  },
  {
    id: "ideator",
    name: "Ideator",
    icon: Lightbulb,
    colorVar: "var(--color-ideator)",
    tagline: "Turns raw context into distinct, calibrated idea candidates.",
    statusVerb: "Shaping ideas",
  },
  {
    id: "cartographer",
    name: "Cartographer",
    icon: Network,
    colorVar: "var(--color-cartographer)",
    tagline: "Builds the critical-thinking mind map of your idea.",
    statusVerb: "Mapping the thinking",
  },
  {
    id: "librarian",
    name: "Librarian",
    icon: BookMarked,
    colorVar: "var(--color-librarian)",
    tagline: "Attaches sources and books, and grades their credibility.",
    statusVerb: "Gathering sources",
  },
  {
    id: "director",
    name: "Director",
    icon: Clapperboard,
    colorVar: "var(--color-director)",
    tagline: "Writes a short narrated video summary of the idea.",
    statusVerb: "Filming the summary",
  },
];

export const AGENT_BY_ID: Record<AgentId, Agent> = AGENTS.reduce(
  (acc, a) => {
    acc[a.id] = a;
    return acc;
  },
  {} as Record<AgentId, Agent>,
);
