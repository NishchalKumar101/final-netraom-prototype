import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorNote } from "@/components/ErrorNote";
import { Panel } from "@/components/Panel";
import { Skeleton } from "@/components/Skeleton";
import { getLearnStats } from "@/lib/api";
import { plainError } from "@/lib/errors";
import { LearnNav } from "@/pages/learn/LearnNav";

const ADMINER = "http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo";
const NEO4J = "http://localhost:7474";

export function OverviewPage() {
  const stats = useQuery({ queryKey: ["learn-stats"], queryFn: getLearnStats });

  const pg = stats.data?.postgres;
  const neo = stats.data?.neo4j;

  return (
    <div className="space-y-5">
      <LearnNav />
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        Netraom keeps <strong className="font-medium text-[var(--foreground)]">portal facts</strong> in Postgres
        (inventory rows, finding fingerprints, filters) and{" "}
        <strong className="font-medium text-[var(--foreground)]">trust paths</strong> in a graph (Neo4j here; Neptune
        in production). Misconfigs are mostly one SQL row per asset; toxic combinations add{" "}
        <code className="text-xs">trust_graph_node_ids</code> and <code className="text-xs">path_edges</code> from a
        graph walk.
      </p>

      {stats.isError ? (
        <ErrorNote>{plainError(stats.error, "Couldn't load store counts. The rest of this page still applies.")}</ErrorNote>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Postgres (RDBMS)" eyebrow="Portal facts">
          <ul className="space-y-1.5 text-sm text-[var(--muted)]">
            <li>
              Tables: <code>assets</code>, <code>findings</code>
            </li>
            <li>Inventory / Findings UI → SELECT + facets</li>
            <li>
              Adminer:{" "}
              <a className="text-[var(--link)] underline" href={ADMINER} target="_blank" rel="noreferrer">
                {ADMINER}
              </a>{" "}
              (password <code>student</code>; if login fails, clear cookies for localhost:8081 and retry)
            </li>
          </ul>
          {stats.isPending ? (
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : null}
          {pg ? (
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <Stat label="Assets" value={pg.assets} />
              <Stat label="Findings" value={pg.findings} />
              <Stat label="CSPM" value={pg.findings_cspm} />
              <Stat label="Toxic combos" value={pg.findings_toxic_combo} />
            </div>
          ) : null}
        </Panel>

        <Panel title="Neo4j (graph)" eyebrow="Trust paths">
          <ul className="space-y-1.5 text-sm text-[var(--muted)]">
            <li>
              Labels: <code>TrustGraphNode</code>, rel <code>TRUST_EDGE</code>
            </li>
            <li>Asset graph / combo paths → neighborhood + Cypher</li>
            <li>
              Browser:{" "}
              <a className="text-[var(--link)] underline" href={NEO4J} target="_blank" rel="noreferrer">
                {NEO4J}
              </a>{" "}
              (neo4j / changeme)
            </li>
          </ul>
          {stats.isPending ? (
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : null}
          {neo ? (
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <Stat label="Nodes" value={neo.node_count} />
              <Stat label="Edges" value={neo.edge_count} />
            </div>
          ) : null}
        </Panel>
      </div>

      <Panel title="Load path (after Dashboard → Load enterprise)">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-[var(--muted)]">
          <li>Normalized JSON → API upserts Neo4j nodes/edges and Postgres asset rows.</li>
          <li>
            Misconfig engine writes CSPM rows to <code>findings</code>.
          </li>
          <li>Combo engine runs graph patterns → toxic-combo rows with path metadata.</li>
          <li>Portal UI reads Postgres for lists; Neo4j for paths when you open a finding or asset graph.</li>
        </ol>
        <p className="mt-3 text-sm">
          <Link className="text-[var(--link)] underline" to="/learn/inventory">
            Raw → normalized
          </Link>{" "}
          shows collector JSON vs trust graph bundle before load.
        </p>
        {stats.isSuccess && !pg?.assets ? (
          <p className="mt-3 text-sm text-[var(--warn-fg)]">
            No data yet — go to Dashboard and load enterprise or a small lab first.
          </p>
        ) : null}
      </Panel>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--inset)] px-3 py-2">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}
