import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ActiveFilters } from "@/components/ActiveFilters";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { FilterChip } from "@/components/FilterChip";
import { FilterGroup, FilterRow } from "@/components/FilterRow";
import { GraphCanvas } from "@/components/GraphCanvas";
import { Pager } from "@/components/Pager";
import { Panel } from "@/components/Panel";
import { SearchField } from "@/components/SearchField";
import { SeverityBadge, RiskScore, severityBarClass } from "@/components/SeverityBadge";
import { Skeleton } from "@/components/Skeleton";
import { SortSelect } from "@/components/SortSelect";
import {
  assetRouteId,
  getAssetByGraphNode,
  getFindingFacets,
  getFindingPath,
  getFindings,
  type FindingSort,
} from "@/lib/api";
import { plainError } from "@/lib/errors";
import { SEVERITY_FILTERS } from "@/lib/filters";
import { cn } from "@/lib/cn";
import { surfaceClass } from "@/lib/styles";
import { ShieldAlert, Shield, AlertTriangle, Info, ListFilter } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const PAGE = 50;

const SEVERITY_ICONS: Record<string, LucideIcon> = {
  all: ListFilter,
  critical: ShieldAlert,
  high: AlertTriangle,
  medium: AlertTriangle,
  low: Info,
};

export function FindingsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<string | null>(searchParams.get("fp"));
  const fingerprintParam = searchParams.get("fp");

  useEffect(() => {
    if (fingerprintParam) setSelected(fingerprintParam);
  }, [fingerprintParam]);

  const tab = (searchParams.get("tab") ?? "toxic-combo") as "cspm" | "toxic-combo";
  const severity = searchParams.get("severity") ?? "all";
  const ruleId = searchParams.get("rule") ?? "";
  const q = searchParams.get("q") ?? "";
  const sort = (searchParams.get("sort") ?? "severity") as FindingSort;
  const order = (searchParams.get("order") ?? "asc") as "asc" | "desc";
  const offset = Number(searchParams.get("offset") ?? "0");

  const facets = useQuery({
    queryKey: ["finding-facets", tab],
    queryFn: () => getFindingFacets(tab),
  });

  const listQuery = useQuery({
    queryKey: ["findings", tab, severity, ruleId, q, sort, order, offset],
    queryFn: () =>
      getFindings({
        source: tab,
        limit: PAGE,
        offset,
        q: q || undefined,
        severity,
        rule_id: ruleId || undefined,
        sort,
        order,
      }),
  });

  const pathQ = useQuery({
    queryKey: ["finding-path", selected],
    queryFn: () => getFindingPath(selected!),
    enabled: Boolean(selected),
  });

  const patchParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === "") next.delete(k);
      else next.set(k, v);
    }
    if (!("offset" in patch)) next.set("offset", "0");
    setSearchParams(next);
  };

  const highlightNodes = useMemo(
    () => new Set(pathQ.data?.attack_path_nodes ?? []),
    [pathQ.data?.attack_path_nodes],
  );
  const highlightEdges = useMemo(
    () => new Set(pathQ.data?.attack_path_edge_ids ?? []),
    [pathQ.data?.attack_path_edge_ids],
  );

  const onGraphNodeClick = async (nodeId: string) => {
    try {
      const asset = await getAssetByGraphNode(nodeId);
      navigate(`/assets/${assetRouteId(asset)}`);
    } catch {
      /* external / network-only nodes */
    }
  };

  const total = listQuery.data?.total ?? 0;
  const sevCounts = facets.data?.by_severity ?? {};
  const severityLabel = SEVERITY_FILTERS.find((s) => s.id === severity)?.label;

  const chips = [
    severity !== "all" && severityLabel
      ? { id: "severity", label: severityLabel, onRemove: () => patchParams({ severity: null }) }
      : null,
    ruleId
      ? { id: "rule", label: ruleId.replace(/_/g, " "), onRemove: () => patchParams({ rule: null }) }
      : null,
    q ? { id: "q", label: `Search: ${q}`, onRemove: () => patchParams({ q: null }) } : null,
  ].filter((chip): chip is { id: string; label: string; onRemove: () => void } => Boolean(chip));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="max-w-2xl text-sm leading-relaxed text-[var(--muted)]">
          Filter by severity and rule; review weighted risk attack paths.
        </p>
        <SortSelect
          label="Sort"
          value={`${sort}:${order}`}
          options={[
            { value: "risk_score:desc", label: "Risk Score (highest first)" },
            { value: "severity:asc", label: "Severity (critical first)" },
            { value: "severity:desc", label: "Severity (low first)" },
            { value: "title:asc", label: "Title A→Z" },
            { value: "rule:asc", label: "Rule ID A→Z" },
          ]}
          onChange={(v) => {
            const [s, o] = v.split(":");
            patchParams({ sort: s, order: o });
          }}
        />
      </div>

      <div className="inline-flex max-w-full flex-wrap gap-1 rounded-lg border border-[var(--border)] bg-[var(--card)] p-1" role="tablist">
        {(["cspm", "toxic-combo"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150",
              tab === t ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
            )}
            onClick={() => {
              setSelected(null);
              patchParams({ tab: t, rule: null, severity: null, offset: "0" });
            }}
          >
            {t === "cspm" ? "Misconfigurations" : "Toxic combinations"}
          </button>
        ))}
      </div>

      <div className={`${surfaceClass} space-y-4 p-4`}>
        <FilterGroup title="Severity">
          <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-5">
            {SEVERITY_FILTERS.map((s) => (
              <FilterRow
                key={s.id}
                icon={SEVERITY_ICONS[s.id] ?? Shield}
                label={s.label}
                count={s.id === "all" ? facets.data?.total : sevCounts[s.id]}
                active={severity === s.id}
                onClick={() => patchParams({ severity: s.id === "all" ? null : s.id })}
              />
            ))}
          </div>
        </FilterGroup>
        {facets.isError ? (
          <ErrorNote>{plainError(facets.error, "Couldn't load severity and rule counts.")}</ErrorNote>
        ) : null}
        {facets.data?.top_rules?.length ? (
          <div className="space-y-2">
            <div className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Top rules</div>
            <div className="flex flex-wrap gap-2">
              <FilterChip label="All rules" active={!ruleId} onClick={() => patchParams({ rule: null })} />
              {facets.data.top_rules.map((r) => (
                <FilterChip
                  key={r.rule_id}
                  label={r.rule_id.replace(/_/g, " ")}
                  count={r.count}
                  active={ruleId === r.rule_id}
                  onClick={() => patchParams({ rule: ruleId === r.rule_id ? null : r.rule_id })}
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={q}
          placeholder="Search alert title or rule…"
          onChange={(value) => patchParams({ q: value || null })}
        />
      </div>
      <ActiveFilters
        chips={chips}
        onClear={() => patchParams({ severity: null, rule: null, q: null })}
      />

      <div className="grid items-start gap-4 xl:grid-cols-2">
        <div className="min-w-0 space-y-3">
          <p className="text-sm text-[var(--muted)]">{listQuery.isPending ? "Loading alerts…" : `${total} alerts`}</p>
          {listQuery.isPending ? <Skeleton className="h-64 w-full" /> : null}
          {listQuery.isError ? (
            <ErrorNote>{plainError(listQuery.error, "Couldn't load findings. Check that the API is running.")}</ErrorNote>
          ) : null}
          {listQuery.data && listQuery.data.items.length === 0 ? (
            <EmptyState title="No alerts match" body="Try another severity, rule, or source tab." />
          ) : null}
          {listQuery.data && listQuery.data.items.length > 0 ? (
            <ul className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)]">
              {listQuery.data.items.map((finding) => {
                const active = selected === finding.fingerprint;
                return (
                  <li key={finding.fingerprint} className="border-t border-[var(--border)] first:border-t-0">
                    <button
                      type="button"
                      onClick={() => setSelected(finding.fingerprint)}
                      className={cn(
                        "flex w-full items-stretch gap-3 px-3 py-3 text-left transition-colors duration-150 hover:bg-[var(--hover)]",
                        active && "bg-[var(--accent)]/10",
                      )}
                    >
                      <span className={cn("w-1 shrink-0 rounded-full", severityBarClass(finding.severity))} />
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <SeverityBadge severity={finding.severity} />
                          <RiskScore score={finding.risk_score} />
                        </span>
                        <span className="mt-1 block text-sm font-medium break-words">{finding.title}</span>
                        <span className="mt-0.5 block truncate text-xs text-[var(--muted)]">
                          {finding.related_assets?.[0]?.display_name ? `${finding.related_assets[0].display_name} · ` : ""}
                          <code>{finding.rule_id}</code>
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {listQuery.data ? (
            <Pager offset={offset} pageSize={PAGE} total={total} onOffset={(next) => patchParams({ offset: String(next) })} />
          ) : null}
        </div>

        <Panel
          eyebrow="Attack path"
          title={pathQ.data?.title ?? "Alert detail"}
          className="xl:sticky xl:top-[4.5rem]"
          bodyClassName="space-y-3"
        >
          {!selected ? (
            <EmptyState title="Select an alert" body="The attack path graph and score breakdown open here." />
          ) : null}
          {selected && pathQ.isPending ? (
            <div className="space-y-2">
              <p className="text-sm text-[var(--muted)]">Loading attack path…</p>
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-[320px] w-full" />
            </div>
          ) : null}
          {selected && pathQ.isError ? (
            <ErrorNote>{plainError(pathQ.error, "Couldn't load this attack path.")}</ErrorNote>
          ) : null}
          {selected && pathQ.data ? (
            <>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge
                    severity={pathQ.data.severity || (pathQ.data.source === "toxic-combo" ? "critical" : "high")}
                  />
                  <RiskScore score={pathQ.data.risk_score} />
                  {pathQ.data.rule_id ? <code className="text-xs text-[var(--muted)]">{pathQ.data.rule_id}</code> : null}
                </div>
                {pathQ.data.description ? (
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{pathQ.data.description}</p>
                ) : null}
              </div>

              {pathQ.data.score_breakdown ? (
                <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--inset)] p-3">
                  <div className="flex justify-between text-[10px] font-semibold tracking-[0.12em] text-[var(--muted)] uppercase">
                    <span>Attack path risk breakdown</span>
                    <span>Max 25 pts each</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
                    <ScoreCell label="Exposure" value={pathQ.data.score_breakdown.exposure} tone="text-[var(--sev-info-fg)]" />
                    <ScoreCell label="Privilege" value={pathQ.data.score_breakdown.privilege} tone="text-[var(--sev-info-fg)]" />
                    <ScoreCell label="Exploitability" value={pathQ.data.score_breakdown.exploitability} tone="text-[var(--warn-fg)]" />
                    <ScoreCell label="Impact" value={pathQ.data.score_breakdown.impact} tone="text-[var(--sev-critical-fg)]" />
                  </div>
                </div>
              ) : null}

              {pathQ.data.related_assets?.length ? (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-[var(--muted)]">Related assets:</span>
                  {pathQ.data.related_assets.map((a) => (
                    <Link
                      key={a.asset_id}
                      to={`/assets/${assetRouteId(a)}`}
                      className="rounded-full bg-[var(--wash-strong)] px-2 py-0.5 text-[var(--link)] ring-1 ring-[var(--ring-soft)] hover:underline"
                    >
                      {a.display_name ?? a.graph_node_id}
                    </Link>
                  ))}
                </div>
              ) : null}

              <p className="text-xs text-[var(--muted)]">
                {pathQ.data.attack_path_nodes.length
                  ? `Attack route: ${pathQ.data.attack_path_nodes.length} nodes · ${pathQ.data.attack_path_edge_ids.length} edges`
                  : `No valid attacker route; showing graph context (${pathQ.data.nodes.length} nodes · ${pathQ.data.edges.length} edges)`}
              </p>
              {pathQ.data.nodes.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">This alert has no graph nodes.</p>
              ) : (
                <GraphCanvas
                  nodes={pathQ.data.nodes}
                  edges={pathQ.data.edges}
                  highlightNodeIds={highlightNodes}
                  highlightEdgeIds={highlightEdges}
                  onNodeClick={onGraphNodeClick}
                />
              )}
            </>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

function ScoreCell({ label, value, tone }: { label: string; value?: number; tone: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--wash)] p-1.5">
      <div className="text-[var(--muted)]">{label}</div>
      <div className={cn("font-semibold tabular-nums", tone)}>{value ?? 0}/25</div>
    </div>
  );
}
