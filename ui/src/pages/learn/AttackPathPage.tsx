import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { Panel } from "@/components/Panel";
import { LearnNav } from "@/pages/learn/LearnNav";

type Stage = {
  id: string;
  title: string;
  kind: "stage" | "decision";
  x: number;
  y: number;
  w: number;
  explanation: string;
  inputs: string;
  outputs: string;
  role: string;
  runtime: string;
};

const STAGES: Stage[] = [
  {
    id: "collect",
    title: "Data Collection",
    kind: "stage",
    x: 40,
    y: 40,
    w: 180,
    explanation: "Gather cloud inventory: accounts, networks, workloads, identities, and storage.",
    inputs: "Collector output or, in this demo, a chosen fixture (enterprise, AWS, GCP).",
    outputs: "Raw resource documents.",
    role: "Start of the pipeline. Nothing is scored yet.",
    runtime:
      "The Dashboard load buttons post bundled synthetic fixtures. They do not call live AWS or GCP APIs. Collector modules exist in the backend tree, but this UI path does not run them.",
  },
  {
    id: "preprocess",
    title: "Data Preprocessing",
    kind: "stage",
    x: 280,
    y: 40,
    w: 190,
    explanation: "Turn raw collector JSON into the normalized trust-graph bundle the loaders expect.",
    inputs: "Raw documents.",
    outputs: "Normalized assets and relationships, or a rejection when the shape is invalid.",
    role: "Drops records that cannot become nodes.",
    runtime: "Learn → Raw to normalized shows this step on the fixture files. The load API consumes the normalized bundle.",
  },
  {
    id: "invalid",
    title: "Invalid data",
    kind: "decision",
    x: 280,
    y: 190,
    w: 190,
    explanation: "If a record is missing identity or fails the bundle shape, it is not inserted as a graph node.",
    inputs: "A raw or half-normalized document.",
    outputs: "No asset row and no edge. The pipeline stops for that record and collection has to be fixed.",
    role: "Decision branch. It does not invent a path.",
    runtime: "The fixtures shipped with this demo are already valid. This branch is the educational stop for bad input, not a second detector.",
  },
  {
    id: "extract",
    title: "Entity Extraction",
    kind: "stage",
    x: 530,
    y: 40,
    w: 190,
    explanation: "Each asset becomes an entity: compute, storage, database, network, or identity, with a stable graph node id.",
    inputs: "Normalized assets.",
    outputs: "Node identities, display names, cloud, region, and exposure flags.",
    role: "These are the vertices later traversal can walk.",
    runtime: "Load writes Postgres asset rows and graph nodes that share graph_node_id.",
  },
  {
    id: "relate",
    title: "Relationship Mapping",
    kind: "stage",
    x: 780,
    y: 40,
    w: 200,
    explanation: "Edges record how entities relate: ingress, attachment, assume-role, read, write, and similar trust edges.",
    inputs: "Normalized relationships.",
    outputs: "Directed edges. Storage direction is canonical; attacker direction is derived later.",
    role: "Without edges, entities stay isolated.",
    runtime:
      "Edge kinds follow ATTACK_TRAVERSAL_POLICY in attack_path_engine.py (forward or reverse). The stored edge is not rewritten.",
  },
  {
    id: "missing",
    title: "Missing relationships",
    kind: "decision",
    x: 780,
    y: 190,
    w: 200,
    explanation: "If the nodes for a finding are not connected under the traversal policy, there is no attacker route.",
    inputs: "Nodes with no allowed hop between them.",
    outputs: "An empty route. Scoring can still run on the nodes themselves.",
    role: "Decision branch. A finding is kept; a path is not invented.",
    runtime:
      "assess_finding_path returns no attack path and still computes exposure, privilege, exploitability, and impact. Findings then says there is no valid attacker route.",
  },
  {
    id: "graph",
    title: "Graph Construction",
    kind: "stage",
    x: 400,
    y: 320,
    w: 200,
    explanation: "Nodes and edges are loaded into the graph store used for neighborhood and path queries.",
    inputs: "Extracted entities and mapped relationships.",
    outputs: "A traversable graph for the demo tenant.",
    role: "This is the structure both labs and finding detail read.",
    runtime: "The demo graph is Neo4j. Tests can use the NetworkX backend. Construction is the fixture load, not a separate UI step.",
  },
  {
    id: "analyze",
    title: "Attack-Path Analysis",
    kind: "stage",
    x: 400,
    y: 460,
    w: 220,
    explanation:
      "Search the graph for simple attacker routes, then rank them. BFS expands hop by hop and finds whether a route exists within a hop limit. DFS follows one branch to the end before backtracking; it is useful for enumerating a branch, and it is not what this app runs. Dijkstra (and the bounded heap search here) orders routes by traversal cost so cheaper routes surface first. A* adds a heuristic toward the target; this ranker does not.",
    inputs: "Entry nodes (internet or public) and other finding nodes, plus edge costs.",
    outputs: "Zero or more simple routes, each with a traversal cost.",
    role: "Chooses candidate routes. It does not by itself decide critical versus low.",
    runtime:
      "Finding scoring calls assess_finding_path → find_rank_paths_dijkstra (max 8 hops, up to 10 routes), then sorts by risk score, then cost. find_candidate_paths_bfs is implemented and unit-tested, and finding scoring does not call it. There is no DFS function. Comments mention A*; the heap key is traversal cost only, so this is not A*.",
  },
  {
    id: "nopath",
    title: "No meaningful path",
    kind: "decision",
    x: 680,
    y: 460,
    w: 200,
    explanation: "The search returns no route that reaches another finding node within the hop limit.",
    inputs: "A graph search with an empty result.",
    outputs: "attack_path_nodes stays empty. The factor score still exists.",
    role: "Decision branch into alert generation without a highlighted route.",
    runtime: "Same outcome as missing relationships: the finding remains, the graph view shows context only.",
  },
  {
    id: "found",
    title: "Meaningful path found",
    kind: "decision",
    x: 160,
    y: 460,
    w: 200,
    explanation: "At least one simple route connects an entry to another finding node.",
    inputs: "The best ranked route.",
    outputs: "Ordered node ids and edge ids handed to risk scoring and the UI highlight.",
    role: "Decision branch into scoring and visualization.",
    runtime: "The winning route is stored on the finding as path edges, attack_path_nodes, and attack_path_edge_ids.",
  },
  {
    id: "score",
    title: "Risk Scoring",
    kind: "stage",
    x: 160,
    y: 620,
    w: 200,
    explanation:
      "Four factors, each 0–25: exposure, privilege, exploitability, and impact. The final score is the sum, capped at 100. Critical is 90+, high is 70+, medium is 40+, otherwise low.",
    inputs: "A route when one exists, otherwise the finding nodes alone.",
    outputs: "risk_score and score_breakdown.",
    role: "Explains why a finding is critical or low. Independent of the traversal-cost sort.",
    runtime: "evaluate_path_risk_breakdown in attack_path_engine.py. Both path and non-path findings receive it.",
  },
  {
    id: "visualize",
    title: "Attack Path Visualization",
    kind: "stage",
    x: 420,
    y: 620,
    w: 210,
    explanation: "Draw the neighborhood and emphasize the stored route.",
    inputs: "Graph nodes, edges, and the stored attack-path ids.",
    outputs: "The Findings detail canvas.",
    role: "Lets a person inspect the route. This Learn diagram is not that canvas.",
    runtime: "Findings uses React Flow (GraphCanvas). Highlighted nodes and edges come from the stored route. This page is an educational flowchart only.",
  },
  {
    id: "alert",
    title: "Alert Generation and Mitigation",
    kind: "stage",
    x: 690,
    y: 620,
    w: 230,
    explanation: "Persist the finding and describe what a person might change. Mitigation in the new dashboard is guidance plus a browser-local status.",
    inputs: "Misconfiguration or toxic-combination result, score, and optional route.",
    outputs: "A findings row. Optional analyst status in this browser.",
    role: "Closes the teaching loop. It does not open a ticket or change a cloud account.",
    runtime:
      "misconfig.py and combos.py write findings. The API has no resolve workflow. Dashboard statuses are labeled analyst workflow and stay in localStorage.",
  },
];

const ARROWS: { d: string; label?: string }[] = [
  { d: "M220 80 H280" },
  { d: "M470 80 H530" },
  { d: "M720 80 H780" },
  { d: "M880 120 V190", label: "invalid" },
  { d: "M880 270 V300 H500 V320" },
  { d: "M375 270 V300" },
  { d: "M500 400 V460" },
  { d: "M400 500 H360", label: "path" },
  { d: "M620 500 H680", label: "no path" },
  { d: "M880 270 H980 V735 H920" },
  { d: "M260 540 V620" },
  { d: "M360 660 H420" },
  { d: "M630 700 H690" },
  { d: "M780 540 V620" },
];

export function AttackPathPage() {
  const [selected, setSelected] = useState<string>("analyze");
  const [view, setView] = useState({ x: 20, y: 10, scale: 0.92 });
  const drag = useRef<{ px: number; py: number; x: number; y: number } | null>(null);
  const frame = useRef<HTMLDivElement>(null);
  const stage = STAGES.find((item) => item.id === selected) ?? STAGES[0];

  useEffect(() => {
    const node = frame.current;
    if (!node) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const factor = event.deltaY > 0 ? 0.92 : 1.08;
      setView((current) => ({ ...current, scale: Math.min(2.2, Math.max(0.45, current.scale * factor)) }));
    };
    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  }, []);

  const fit = () => setView({ x: 20, y: 10, scale: 0.92 });

  return (
    <div className="space-y-4">
      <LearnNav />
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        Educational flowchart for how an attack path is produced. BFS, DFS, and Dijkstra are explained on the analysis stage. This prototype&apos;s finding scorer runs a bounded Dijkstra-style search in <code>attack_path_engine.py</code> and scores exposure, privilege, exploitability, and impact. DFS is not implemented. BFS is implemented and tested, and it is not what finding scoring calls.
      </p>
      <div className="flex flex-wrap gap-2 text-[11px] text-[var(--muted)]">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-[var(--inset)] px-2 py-1 ring-1 ring-[var(--ring-soft)]">
          <span className="h-2.5 w-4 rounded-sm bg-[var(--accent)]" /> Stage
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-md bg-[var(--inset)] px-2 py-1 ring-1 ring-[var(--ring-soft)]">
          <span className="h-2.5 w-4 rounded-sm bg-[var(--warning)]" /> Decision
        </span>
        <span className="rounded-md bg-[var(--inset)] px-2 py-1 ring-1 ring-[var(--ring-soft)]">Flow moves from collection across the top, then down into analysis</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => setView((current) => ({ ...current, scale: Math.min(2.2, current.scale * 1.15) }))}>
          Zoom in
        </Button>
        <Button variant="secondary" onClick={() => setView((current) => ({ ...current, scale: Math.max(0.45, current.scale / 1.15) }))}>
          Zoom out
        </Button>
        <Button variant="secondary" onClick={fit}>
          Fit
        </Button>
        <Button variant="secondary" onClick={fit}>
          Reset
        </Button>
      </div>
      <div
        ref={frame}
        className="h-[min(560px,70vh)] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--canvas)]"
        onPointerDown={(event) => {
          drag.current = { px: event.clientX, py: event.clientY, x: view.x, y: view.y };
          (event.currentTarget as HTMLDivElement).setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          setView((current) => ({
            ...current,
            x: drag.current!.x + event.clientX - drag.current!.px,
            y: drag.current!.y + event.clientY - drag.current!.py,
          }));
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
      >
        <svg viewBox="0 0 980 780" className="h-full w-full" role="img" aria-label="Attack path analysis flowchart">
          <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0 0 L6 3 L0 6 Z" fill="var(--muted)" />
              </marker>
            </defs>
            {ARROWS.map((arrow) => (
              <path key={arrow.d} d={arrow.d} fill="none" stroke="var(--muted)" strokeWidth="1.4" markerEnd="url(#arrow)" />
            ))}
            {STAGES.map((item) => {
              const active = item.id === selected;
              const fill = item.kind === "decision" ? "color-mix(in srgb, var(--warning) 22%, var(--card))" : "var(--card)";
              return (
                <g key={item.id} transform={`translate(${item.x} ${item.y})`} onClick={() => setSelected(item.id)} style={{ cursor: "pointer" }}>
                  <rect
                    width={item.w}
                    height="78"
                    rx="12"
                    fill={fill}
                    stroke={active ? "var(--accent)" : "var(--border-strong)"}
                    strokeWidth={active ? 2.5 : 1}
                  />
                  <text x="12" y="32" fill="var(--foreground)" fontSize="13" fontWeight="600">
                    {wrapLabel(item.title).map((line, index) => (
                      <tspan key={line} x="12" dy={index === 0 ? 0 : 16}>
                        {line}
                      </tspan>
                    ))}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>
      <Panel eyebrow={stage.kind === "decision" ? "Decision" : "Stage"} title={stage.title}>
        <p className="text-sm leading-relaxed">{stage.explanation}</p>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Inputs</dt>
            <dd className="text-[var(--foreground)]">{stage.inputs}</dd>
          </div>
          <div>
            <dt className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Outputs</dt>
            <dd className="text-[var(--foreground)]">{stage.outputs}</dd>
          </div>
          <div>
            <dt className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Role</dt>
            <dd className="text-[var(--foreground)]">{stage.role}</dd>
          </div>
          <div>
            <dt className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">What this app runs</dt>
            <dd className="text-[var(--foreground)]">{stage.runtime}</dd>
          </div>
        </dl>
      </Panel>
    </div>
  );
}

function wrapLabel(title: string) {
  const words = title.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > 22 && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines.slice(0, 3);
}
