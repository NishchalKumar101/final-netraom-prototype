import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { ErrorNote } from "@/components/ErrorNote";
import { GraphCanvas } from "@/components/GraphCanvas";
import { JsonPanelModal } from "@/components/JsonPanelModal";
import { Panel } from "@/components/Panel";
import { Skeleton } from "@/components/Skeleton";
import { CloudBadge, ExposureBadge } from "@/components/SeverityBadge";
import { getAsset, getAssetJson, getAssets, getNeighborhood } from "@/lib/api";
import { plainError } from "@/lib/errors";

export function AssetDetailPage() {
  const { assetId = "" } = useParams();
  const navigate = useNavigate();
  const [jsonOpen, setJsonOpen] = useState(false);

  const assetQ = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId),
    enabled: Boolean(assetId),
  });

  const assetJsonQ = useQuery({
    queryKey: ["asset-json", assetId],
    queryFn: () => getAssetJson(assetId),
    enabled: jsonOpen && Boolean(assetId),
  });

  const nodeId = assetQ.data?.graph_node_id;
  const hoodQ = useQuery({
    queryKey: ["hood", nodeId],
    queryFn: () => getNeighborhood(nodeId!, 2),
    enabled: Boolean(nodeId),
  });

  const assetsQ = useQuery({
    queryKey: ["assets", "all-for-graph-nav"],
    queryFn: () => getAssets({ limit: 200, offset: 0 }),
  });

  const onNodeClick = (clickedNodeId: string) => {
    const match = assetsQ.data?.items.find((a) => a.graph_node_id === clickedNodeId);
    if (match) {
      navigate(`/assets/${match.asset_id}`);
    }
  };

  const asset = assetQ.data;
  const norm = asset?.normalized;
  const pkg = assetJsonQ.data;

  const rawPayload = pkg?.raw_collector;
  const rawSynthetic =
    rawPayload && typeof rawPayload === "object" && "synthetic" in rawPayload && rawPayload.synthetic;

  const jsonSections = pkg
    ? [
        {
          id: "raw",
          label: rawSynthetic ? "Raw cloud inventory (synthetic collector)" : "Raw cloud inventory (collector)",
          data: rawPayload ?? { message: "No raw shard available." },
          note:
            pkg.note ??
            (rawSynthetic
              ? "Representative API response for this resource type (enterprise load)."
              : undefined),
        },
        {
          id: "normalized",
          label: "Normalized (trust graph bundle)",
          data:
            pkg.normalized ??
            (pkg.neo4j_node
              ? { trust_graph_node: pkg.neo4j_node, message: "Edges loaded from Neo4j neighborhood." }
              : { message: "Load demo data from Dashboard first." }),
        },
        {
          id: "portal",
          label: "Portal asset (Postgres / API)",
          data: pkg.portal_asset,
        },
      ]
    : [];

  const graphPropsDisplay =
    norm?.graph_props && Object.keys(norm.graph_props).length > 0
      ? norm.graph_props
      : norm?.highlights && Object.keys(norm.highlights).length > 0
        ? norm.highlights
        : null;

  return (
    <div className="space-y-5">
      <Link
        to="/assets"
        className="inline-flex items-center gap-2 text-sm text-[var(--muted)] transition-colors hover:text-[var(--foreground)]"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to inventory
      </Link>

      {assetQ.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-8 w-72" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : null}

      {assetQ.isError ? (
        <ErrorNote>{plainError(assetQ.error, "Couldn't load this asset.")}</ErrorNote>
      ) : null}

      {asset ? (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
                Inventory / {asset.cloud ?? "asset"} / {asset.resource_type ?? "resource"}
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight break-words">{asset.display_name ?? asset.canonical_key}</h2>
              <p className="mt-1 break-all font-mono text-xs text-[var(--muted)]">{asset.graph_node_id}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <CloudBadge cloud={asset.cloud} />
                {asset.resource_type ? (
                  <span className="rounded-md bg-[var(--wash)] px-2 py-0.5 text-xs text-[var(--foreground)] ring-1 ring-[var(--ring-soft)]">
                    {asset.resource_type}
                  </span>
                ) : null}
                {asset.region ? <span className="text-xs text-[var(--muted)]">{asset.region}</span> : null}
                <ExposureBadge exposed={asset.is_internet_exposed} />
              </div>
            </div>
            <Button variant="secondary" onClick={() => setJsonOpen(true)}>
              View raw JSON
            </Button>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel eyebrow="Portal" title="Postgres record">
              <dl className="space-y-2 text-sm">
                <Row label="Cloud" value={asset.cloud} />
                <Row label="Type" value={asset.resource_type} />
                <Row label="Region" value={asset.region} />
                <div className="flex items-start justify-between gap-4 border-t border-[var(--border)] pt-2">
                  <dt className="text-[var(--muted)]">Internet exposed</dt>
                  <dd>
                    <ExposureBadge exposed={asset.is_internet_exposed} />
                  </dd>
                </div>
                <Row label="Canonical key" value={asset.canonical_key} mono />
              </dl>
              {Object.keys(asset.props ?? {}).length > 0 ? (
                <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--inset)] p-3 text-xs text-[var(--code-fg)]">
                  {JSON.stringify(asset.props, null, 2)}
                </pre>
              ) : null}
            </Panel>

            <Panel eyebrow="Normalized" title="Trust graph node">
              {norm ? (
                <div className="space-y-2 text-sm">
                  <Row label="Schema" value={norm.schema_version} />
                  <Row label="Kind" value={norm.kind} />
                  <Row label="Graph edges (1-hop)" value={String(norm.edge_count ?? 0)} />
                  <Row label="Source" value={norm.source_modules?.join(", ") ?? "—"} />
                  {norm.highlights && Object.keys(norm.highlights).length > 0 ? (
                    <div className="mt-2 space-y-1 border-t border-[var(--border)] pt-2">
                      <p className="text-xs text-[var(--muted)]">Algorithm props (CSPM / combos)</p>
                      {Object.entries(norm.highlights).map(([k, v]) => (
                        <Row key={k} label={k} value={String(v)} />
                      ))}
                    </div>
                  ) : null}
                  {graphPropsDisplay ? (
                    <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--inset)] p-3 text-xs text-[var(--code-fg)]">
                      {JSON.stringify(graphPropsDisplay, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-xs text-[var(--muted)]">
                      No extra graph props on this node (isolated filler asset is common in enterprise load).
                    </p>
                  )}
                  {norm.sample_edges && norm.sample_edges.length > 0 ? (
                    <div className="mt-2 border-t border-[var(--border)] pt-2">
                      <p className="mb-1 text-xs text-[var(--muted)]">Sample TRUST_EDGE (1-hop)</p>
                      <ul className="space-y-1 font-mono text-xs text-[var(--muted)]">
                        {norm.sample_edges.map((e, i) => (
                          <li key={i} className="break-all">
                            <span className="text-[var(--live)]">{e.kind}</span>: {shortId(e.src_id)} → {shortId(e.dst_id)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted)]">No normalized preview on this asset.</p>
              )}
            </Panel>
          </div>

          <Panel
            eyebrow="Graph"
            title="Neighborhood"
            bodyClassName="space-y-3"
          >
            <p className="text-sm text-[var(--muted)]">Click a node to jump if it is an inventory asset.</p>
            {hoodQ.isError ? (
              <ErrorNote>{plainError(hoodQ.error, "The neighborhood graph didn't load.")}</ErrorNote>
            ) : null}
            {hoodQ.isPending ? (
              <div className="space-y-2">
                <p className="text-sm text-[var(--muted)]">Loading graph…</p>
                <Skeleton className="h-[320px] w-full" />
              </div>
            ) : null}
            {hoodQ.data && hoodQ.data.nodes.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                No graph nodes found in Neo4j for this asset. Try Dashboard → Load enterprise (or a lab) again.
              </p>
            ) : null}
            {hoodQ.data && hoodQ.data.nodes.length > 0 ? (
              <>
                {hoodQ.data.edges.length === 0 ? (
                  <p className="text-xs text-[var(--muted)]">
                    Single-node neighborhood — no trust edges within 2 hops (typical for internal filler buckets).
                  </p>
                ) : null}
                <GraphCanvas
                  nodes={hoodQ.data.nodes}
                  edges={hoodQ.data.edges}
                  centerId={nodeId}
                  onNodeClick={onNodeClick}
                />
              </>
            ) : null}
          </Panel>
        </>
      ) : null}

      <JsonPanelModal
        open={jsonOpen}
        onClose={() => setJsonOpen(false)}
        title="Asset JSON (raw → normalized → portal)"
        sections={jsonSections}
        loading={jsonOpen && assetJsonQ.isPending}
        error={jsonOpen && assetJsonQ.isError ? plainError(assetJsonQ.error, "Couldn't load the JSON package.") : null}
      />
    </div>
  );
}

function shortId(id?: string) {
  if (!id) return "—";
  const parts = id.split(/[/:]/);
  return parts[parts.length - 1] || id;
}

function Row({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 border-t border-[var(--border)] pt-2 first:border-t-0 first:pt-0">
      <span className="text-[var(--muted)]">{label}</span>
      <span className={mono ? "max-w-[65%] text-right font-mono text-xs break-all" : "max-w-[65%] text-right break-words"}>
        {value ?? "—"}
      </span>
    </div>
  );
}
