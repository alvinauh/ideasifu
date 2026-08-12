import { useMemo, useState } from "react";
import {
  Network,
  List,
  X,
  Lightbulb,
  ExternalLink,
  BookMarked,
} from "lucide-react";
import type {
  MindMap as MindMapData,
  MindMapNode,
  MindMapNodeType,
  Source,
} from "@/lib/types";

const NODE_META: Record<
  MindMapNodeType,
  { label: string; colorVar: string; glyph: string }
> = {
  thesis: { label: "Thesis / Question", colorVar: "var(--color-node-thesis)", glyph: "◆" },
  argument: { label: "Argument / Reason", colorVar: "var(--color-node-argument)", glyph: "▲" },
  evidence: { label: "Evidence", colorVar: "var(--color-node-evidence)", glyph: "●" },
  counter: { label: "Counter-argument", colorVar: "var(--color-node-counter)", glyph: "✕" },
  question: { label: "Open question / Gap", colorVar: "var(--color-node-question)", glyph: "?" },
};

interface Positioned {
  node: MindMapNode;
  x: number;
  y: number;
}

const WIDTH = 900;
const HEIGHT = 640;

/** Compute a radial layout: root at center, children fanned on rings by depth. */
function layout(nodes: MindMapNode[]): {
  positioned: Positioned[];
  byId: Map<string, Positioned>;
} {
  const byId = new Map<string, Positioned>();
  const root = nodes.find((n) => !n.parent) ?? nodes[0];
  const cx = WIDTH / 2;
  const cy = HEIGHT / 2;

  const positioned: Positioned[] = [];
  if (!root) return { positioned, byId };

  const rootPos = { node: root, x: cx, y: cy };
  positioned.push(rootPos);
  byId.set(root.id, rootPos);

  // First ring: direct children of root spread around a full circle.
  const firstRing = nodes.filter((n) => n.parent === root.id);
  const ring1Radius = 210;
  firstRing.forEach((child, i) => {
    const angle = (i / firstRing.length) * Math.PI * 2 - Math.PI / 2;
    const p = {
      node: child,
      x: cx + Math.cos(angle) * ring1Radius,
      y: cy + Math.sin(angle) * ring1Radius,
    };
    positioned.push(p);
    byId.set(child.id, p);

    // Second ring: children of this child, clustered near the parent's angle.
    const grandChildren = nodes.filter((n) => n.parent === child.id);
    const spread = Math.PI / 3.2;
    grandChildren.forEach((gc, j) => {
      const base =
        grandChildren.length === 1
          ? angle
          : angle - spread / 2 + (j / (grandChildren.length - 1)) * spread;
      const gp = {
        node: gc,
        x: cx + Math.cos(base) * (ring1Radius + 150),
        y: cy + Math.sin(base) * (ring1Radius + 150),
      };
      positioned.push(gp);
      byId.set(gc.id, gp);
    });
  });

  return { positioned, byId };
}

interface Props {
  data: MindMapData;
  sources: Source[];
  onGoToSource?: (sourceId: string) => void;
}

export default function MindMap({ data, sources, onGoToSource }: Props) {
  const [view, setView] = useState<"map" | "list">("map");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { positioned, byId } = useMemo(() => layout(data.nodes), [data.nodes]);
  const selected = selectedId
    ? data.nodes.find((n) => n.id === selectedId) ?? null
    : null;
  const selectedSource = selected?.source_id
    ? sources.find((s) => s.id === selected.source_id)
    : undefined;

  return (
    <div>
      {/* Controls + legend */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div
          role="radiogroup"
          aria-label="Mind map view"
          className="inline-flex items-center gap-1 rounded-full border border-border bg-surface p-1"
        >
          <ViewBtn active={view === "map"} onClick={() => setView("map")} icon={<Network className="h-4 w-4" />} label="Map" />
          <ViewBtn active={view === "list"} onClick={() => setView("list")} icon={<List className="h-4 w-4" />} label="Outline" />
        </div>
        <Legend />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div className="card-shadow overflow-hidden rounded-2xl border border-border bg-surface">
          {view === "map" ? (
            <MapView
              positioned={positioned}
              byId={byId}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          ) : (
            <ListView
              nodes={data.nodes}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>

        {/* Detail side panel */}
        <aside className="card-shadow rounded-2xl border border-border bg-surface p-4">
          {selected ? (
            <NodeDetail
              node={selected}
              source={selectedSource}
              onClose={() => setSelectedId(null)}
              onGoToSource={onGoToSource}
            />
          ) : (
            <div className="grid h-full min-h-[200px] place-items-center text-center">
              <p className="text-sm text-muted">
                Click any node to see its{" "}
                <span className="text-foreground">"keep thinking"</span> prompt.
                Every branch ends in a question, not a period.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function MapView({
  positioned,
  byId,
  selectedId,
  onSelect,
}: {
  positioned: Positioned[];
  byId: Map<string, Positioned>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="h-[560px] w-full"
      role="img"
      aria-label="Critical-thinking mind map"
    >
      {/* connectors */}
      {positioned.map((p) => {
        if (!p.node.parent) return null;
        const parent = byId.get(p.node.parent);
        if (!parent) return null;
        const midX = (parent.x + p.x) / 2;
        const path = `M ${parent.x} ${parent.y} C ${midX} ${parent.y}, ${midX} ${p.y}, ${p.x} ${p.y}`;
        return (
          <path
            key={`edge-${p.node.id}`}
            d={path}
            fill="none"
            stroke={NODE_META[p.node.type].colorVar}
            strokeWidth={1.5}
            strokeOpacity={0.45}
          />
        );
      })}

      {/* nodes */}
      {positioned.map((p, i) => {
        const meta = NODE_META[p.node.type];
        const isRoot = !p.node.parent;
        const isSel = selectedId === p.node.id;
        const w = isRoot ? 260 : 190;
        const label =
          p.node.label.length > 68
            ? p.node.label.slice(0, 66) + "…"
            : p.node.label;
        return (
          <g
            key={p.node.id}
            transform={`translate(${p.x - w / 2}, ${p.y - 24})`}
            className="animate-rise-in cursor-pointer"
            style={{ animationDelay: `${i * 60}ms` }}
            onClick={() => onSelect(p.node.id)}
            role="button"
            tabIndex={0}
            aria-label={`${meta.label}: ${p.node.label}`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(p.node.id);
              }
            }}
          >
            <rect
              width={w}
              height={48}
              rx={12}
              fill="var(--color-surface-2)"
              stroke={meta.colorVar}
              strokeWidth={isSel ? 2.5 : 1.5}
              style={
                isSel
                  ? { filter: `drop-shadow(0 0 10px ${meta.colorVar})` }
                  : undefined
              }
            />
            <text
              x={16}
              y={20}
              fill={meta.colorVar}
              fontSize={11}
              fontWeight={600}
              style={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
            >
              {meta.glyph} {p.node.type}
            </text>
            <text x={16} y={38} fill="var(--color-foreground)" fontSize={12}>
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function ListView({
  nodes,
  selectedId,
  onSelect,
}: {
  nodes: MindMapNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const root = nodes.find((n) => !n.parent) ?? nodes[0];
  if (!root) return null;

  const renderChildren = (parentId: string, depth: number) =>
    nodes
      .filter((n) => n.parent === parentId)
      .map((n) => (
        <li key={n.id} style={{ paddingLeft: depth * 18 }}>
          <button
            onClick={() => onSelect(n.id)}
            className={`flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              selectedId === n.id ? "bg-surface-2" : ""
            }`}
          >
            <span aria-hidden style={{ color: NODE_META[n.type].colorVar }}>
              {NODE_META[n.type].glyph}
            </span>
            <span>
              <span className="text-xs uppercase tracking-wide" style={{ color: NODE_META[n.type].colorVar }}>
                {n.type}
              </span>
              <br />
              {n.label}
            </span>
          </button>
          <ul>{renderChildren(n.id, depth + 1)}</ul>
        </li>
      ));

  return (
    <div className="max-h-[560px] overflow-auto p-3">
      <ul>
        <li>
          <button
            onClick={() => onSelect(root.id)}
            className={`flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left font-medium transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              selectedId === root.id ? "bg-surface-2" : ""
            }`}
          >
            <span aria-hidden style={{ color: NODE_META[root.type].colorVar }}>
              {NODE_META[root.type].glyph}
            </span>
            {root.label}
          </button>
          <ul>{renderChildren(root.id, 1)}</ul>
        </li>
      </ul>
    </div>
  );
}

function NodeDetail({
  node,
  source,
  onClose,
  onGoToSource,
}: {
  node: MindMapNode;
  source?: Source;
  onClose: () => void;
  onGoToSource?: (id: string) => void;
}) {
  const meta = NODE_META[node.type];
  return (
    <div className="animate-rise-in">
      <div className="flex items-start justify-between gap-2">
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide"
          style={{
            color: meta.colorVar,
            backgroundColor: "color-mix(in oklab, currentColor 16%, transparent)",
          }}
        >
          {meta.glyph} {meta.label}
        </span>
        <button
          onClick={onClose}
          aria-label="Close node detail"
          className="rounded-md p-1 text-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className="mt-3 text-sm font-medium leading-relaxed">{node.label}</p>

      {node.prompt && (
        <div
          className="mt-4 rounded-xl border p-3"
          style={{ borderColor: "var(--color-librarian)" }}
        >
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[color:var(--color-librarian)]">
            <Lightbulb className="h-3.5 w-3.5" aria-hidden />
            Keep thinking
          </p>
          <p className="mt-1.5 text-sm text-foreground/90">{node.prompt}</p>
        </div>
      )}

      {source && (
        <button
          onClick={() => onGoToSource?.(source.id)}
          className="mt-4 flex w-full items-start gap-2 rounded-xl border border-border p-3 text-left transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <BookMarked className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--color-librarian)]" aria-hidden />
          <span className="text-sm">
            <span className="font-medium">{source.title}</span>
            <span className="mt-0.5 flex items-center gap-1 text-xs text-muted">
              Jump to source <ExternalLink className="h-3 w-3" aria-hidden />
            </span>
          </span>
        </button>
      )}
    </div>
  );
}

function Legend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted">
      {(Object.keys(NODE_META) as MindMapNodeType[]).map((t) => (
        <li key={t} className="flex items-center gap-1.5">
          <span aria-hidden style={{ color: NODE_META[t].colorVar }}>
            {NODE_META[t].glyph}
          </span>
          {NODE_META[t].label}
        </li>
      ))}
    </ul>
  );
}

function ViewBtn({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        active ? "bg-gradient-idea text-white" : "text-muted hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
