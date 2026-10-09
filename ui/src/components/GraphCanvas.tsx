import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";

import type { GraphEdge, GraphNode } from "@/lib/api";
import { useTheme } from "@/theme/ThemeProvider";

function nodeLabel(n: GraphNode) {
  return n.name ?? n.node_id.split("/").pop() ?? n.node_id;
}

function kindStyle(kind: string | undefined, props: Record<string, unknown> | undefined, theme: "dark" | "light") {
  const pub = props?.is_public || props?.is_internet_exposed;
  if (theme === "light") {
    if (kind === "identity") return { border: "1px solid #6d28d9", background: "#f3e8ff", color: "#1e1b4b" };
    if (kind === "network") return { border: "1px solid #0f766e", background: "#ccfbf1", color: "#134e4a" };
    if (kind === "external") return { border: "1px solid #c2410c", background: "#ffedd5", color: "#7c2d12" };
    if (pub) return { border: "1px solid #be123c", background: "#ffe4e6", color: "#881337" };
    return { border: "1px solid #94a3b8", background: "#f8fafc", color: "#0f172a" };
  }
  if (kind === "identity") return { border: "1px solid #7c6bb5", background: "#241c3d", color: "#e8eef8" };
  if (kind === "network") return { border: "1px solid #2a8ea0", background: "#0e2c38", color: "#e8eef8" };
  if (kind === "external") return { border: "1px solid #c47a3a", background: "#3a2414", color: "#e8eef8" };
  if (pub) return { border: "1px solid #e5484d", background: "#3c1619", color: "#e8eef8" };
  return { border: "1px solid #2c4368", background: "#15243c", color: "#e8eef8" };
}

const legend = [
  { label: "Identity", swatch: "#7c6bb5" },
  { label: "Network", swatch: "#2a8ea0" },
  { label: "External", swatch: "#c47a3a" },
  { label: "Internet exposed", swatch: "#e5484d" },
  { label: "Other", swatch: "#2c4368" },
];

export function GraphCanvas({
  nodes,
  edges,
  centerId,
  highlightNodeIds,
  highlightEdgeIds,
  onNodeClick,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  centerId?: string;
  highlightNodeIds?: Set<string>;
  highlightEdgeIds?: Set<string>;
  onNodeClick?: (nodeId: string) => void;
}) {
  const { theme } = useTheme();
  const signature = nodes.map((n) => n.node_id).join("\0");
  const [focusId, setFocusId] = useState<string | null>(null);
  const [sig, setSig] = useState(signature);
  if (sig !== signature) {
    setSig(signature);
    setFocusId(null);
  }

  const focusLit = useMemo(() => {
    if (!focusId) return null;
    const ids = new Set<string>([focusId]);
    for (const edge of edges) {
      if (edge.src_id === focusId) ids.add(edge.dst_id);
      if (edge.dst_id === focusId) ids.add(edge.src_id);
    }
    return ids;
  }, [focusId, edges]);

  const lit = focusLit ?? (highlightNodeIds && highlightNodeIds.size > 0 ? highlightNodeIds : null);

  const flowNodes: Node[] = useMemo(
    () =>
      nodes.map((n, i) => {
        const col = i % 4;
        const row = Math.floor(i / 4);
        const dimmed = Boolean(lit && !lit.has(n.node_id));
        const ring = n.node_id === focusId || n.node_id === centerId || highlightNodeIds?.has(n.node_id);
        return {
          id: n.node_id,
          data: { label: nodeLabel(n) },
          position: { x: col * 220, y: row * 100 },
          style: {
            ...kindStyle(n.kind, n.props, theme),
            padding: 8,
            borderRadius: 8,
            fontSize: 12,
            width: 180,
            opacity: dimmed ? 0.28 : 1,
            boxShadow: ring ? "0 0 0 2px #2f6fed" : undefined,
            transition: "opacity 150ms ease, box-shadow 150ms ease",
          },
        };
      }),
    [nodes, centerId, highlightNodeIds, lit, focusId, theme],
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((e) => {
        const touchesFocus = Boolean(focusId && (e.src_id === focusId || e.dst_id === focusId));
        const onPath = highlightEdgeIds?.has(e.edge_id) ?? false;
        const emphasized = touchesFocus || onPath;
        const dimEdge = focusId
          ? !touchesFocus
          : Boolean(lit && !(lit.has(e.src_id) && lit.has(e.dst_id)));
        const port = e.props?.port ?? e.props?.port_from;
        const label = [e.kind, port ? `:${port}` : ""].filter(Boolean).join("");
        const color = emphasized ? "#f87171" : "#7f93ad";
        return {
          id: e.edge_id,
          source: e.src_id,
          target: e.dst_id,
          label,
          animated: emphasized,
          style: { stroke: color, strokeWidth: emphasized ? 2.5 : 1.5, opacity: dimEdge ? 0.16 : 1 },
          markerEnd: { type: MarkerType.ArrowClosed, color },
        };
      }),
    [edges, highlightEdgeIds, focusId, lit],
  );

  return (
    <div className="min-w-0">
      <div className="mb-2 flex flex-wrap gap-1.5">
        {legend.map((item) => (
          <span
            key={item.label}
            className="inline-flex items-center gap-1.5 rounded-md bg-[var(--inset)] px-2 py-1 text-[10px] text-[var(--code-fg)] ring-1 ring-[var(--ring-soft)]"
          >
            <span className="h-2 w-2 rounded-sm" style={{ background: item.swatch }} />
            {item.label}
          </span>
        ))}
      </div>
      <div className="relative h-[min(480px,62vh)] min-h-[320px] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--canvas)]">
        <ReactFlowProvider>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            fitView
            colorMode={theme}
            onNodeClick={(_, node) => {
              setFocusId(node.id);
              onNodeClick?.(node.id);
            }}
          >
            <MiniMap pannable zoomable />
            <Controls />
            <Background gap={16} color={theme === "dark" ? "#1c2d48" : "#d5dfec"} />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
    </div>
  );
}
