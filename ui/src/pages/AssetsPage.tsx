import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Cloud,
  Database,
  Fingerprint,
  Globe,
  HardDrive,
  KeyRound,
  Network,
  Server,
  Shield,
  Waypoints,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ActiveFilters } from "@/components/ActiveFilters";
import { DataTable, type Column } from "@/components/DataTable";
import { ErrorNote } from "@/components/ErrorNote";
import { FilterGroup, FilterRow } from "@/components/FilterRow";
import { Pager } from "@/components/Pager";
import { SearchField } from "@/components/SearchField";
import { SortSelect } from "@/components/SortSelect";
import { TableSkeleton } from "@/components/Skeleton";
import { CloudBadge, ExposureBadge } from "@/components/SeverityBadge";
import { assetRouteId, getAssetFacets, getAssets, type Asset, type AssetSort } from "@/lib/api";
import { plainError } from "@/lib/errors";
import { ASSET_CATEGORIES, type AssetCategory } from "@/lib/filters";
import { surfaceClass } from "@/lib/styles";

const PAGE = 50;

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  all: Boxes,
  compute: Server,
  storage: HardDrive,
  serverless: Zap,
  database: Database,
  network: Network,
  api: Waypoints,
  identity: Fingerprint,
  secrets: KeyRound,
};

export function AssetsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const category = (searchParams.get("category") ?? "all") as AssetCategory;
  const cloud = searchParams.get("cloud") ?? "";
  const exposed = searchParams.get("exposed") ?? "";
  const sort = (searchParams.get("sort") ?? "name") as AssetSort;
  const order = (searchParams.get("order") ?? "asc") as "asc" | "desc";
  const q = searchParams.get("q") ?? "";
  const offset = Number(searchParams.get("offset") ?? "0");

  const facets = useQuery({ queryKey: ["asset-facets"], queryFn: getAssetFacets });

  const query = useQuery({
    queryKey: ["assets", category, cloud, exposed, sort, order, q, offset],
    queryFn: () =>
      getAssets({
        limit: PAGE,
        offset,
        q: q || undefined,
        cloud: cloud || undefined,
        category,
        internet_exposed: exposed === "true" ? true : exposed === "false" ? false : undefined,
        sort,
        order,
      }),
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

  const columns = useMemo<Column<Asset>[]>(
    () => [
      {
        key: "name",
        header: "Name",
        render: (r) => (
          <span className="font-medium text-[var(--link)]">{r.display_name ?? r.canonical_key}</span>
        ),
      },
      { key: "type", header: "Type", render: (r) => r.resource_type ?? "—" },
      { key: "cloud", header: "Cloud", render: (r) => <CloudBadge cloud={r.cloud} /> },
      { key: "region", header: "Region", className: "px-4 py-3 whitespace-nowrap", render: (r) => r.region ?? "—" },
      {
        key: "exposed",
        header: "Exposure",
        render: (r) => <ExposureBadge exposed={r.is_internet_exposed} />,
      },
    ],
    [],
  );

  const total = query.data?.total ?? 0;
  const catCounts = facets.data?.by_category ?? {};
  const categoryLabel = ASSET_CATEGORIES.find((c) => c.id === category)?.label;

  const chips = [
    category !== "all" && categoryLabel
      ? { id: "category", label: categoryLabel, onRemove: () => patchParams({ category: null }) }
      : null,
    cloud ? { id: "cloud", label: cloud.toUpperCase(), onRemove: () => patchParams({ cloud: null }) } : null,
    exposed === "true"
      ? { id: "exposed", label: "Internet exposed", onRemove: () => patchParams({ exposed: null }) }
      : null,
    exposed === "false"
      ? { id: "exposed", label: "Internal only", onRemove: () => patchParams({ exposed: null }) }
      : null,
    q ? { id: "q", label: `Search: ${q}`, onRemove: () => patchParams({ q: null }) } : null,
  ].filter((chip): chip is { id: string; label: string; onRemove: () => void } => Boolean(chip));

  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        Filter by asset class — VMs, buckets, functions, load balancers, and more.
      </p>

      {facets.isError ? (
        <ErrorNote>{plainError(facets.error, "Couldn't load filter counts. You can still filter the inventory.")}</ErrorNote>
      ) : null}

      <div className="grid items-start gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className={`${surfaceClass} space-y-4 p-3 lg:sticky lg:top-[4.5rem] lg:max-h-[calc(100vh-6.5rem)] lg:overflow-auto`}>
          <FilterGroup title="Asset type">
            {ASSET_CATEGORIES.map((c) => {
              const Icon = CATEGORY_ICONS[c.id] ?? Boxes;
              return (
                <FilterRow
                  key={c.id}
                  icon={Icon}
                  label={c.label}
                  count={c.id === "all" ? facets.data?.total : catCounts[c.id]}
                  active={category === c.id}
                  onClick={() => patchParams({ category: c.id === "all" ? null : c.id })}
                />
              );
            })}
          </FilterGroup>
          <FilterGroup title="Cloud">
            <FilterRow icon={Cloud} label="All clouds" active={!cloud} onClick={() => patchParams({ cloud: null })} />
            <FilterRow
              icon={Cloud}
              label="AWS"
              count={facets.data?.by_cloud.aws}
              active={cloud === "aws"}
              onClick={() => patchParams({ cloud: cloud === "aws" ? null : "aws" })}
            />
            <FilterRow
              icon={Cloud}
              label="GCP"
              count={facets.data?.by_cloud.gcp}
              active={cloud === "gcp"}
              onClick={() => patchParams({ cloud: cloud === "gcp" ? null : "gcp" })}
            />
          </FilterGroup>
          <FilterGroup title="Exposure">
            <FilterRow icon={Globe} label="Any exposure" active={!exposed} onClick={() => patchParams({ exposed: null })} />
            <FilterRow
              icon={Globe}
              label="Internet exposed"
              count={facets.data?.internet_exposed}
              active={exposed === "true"}
              onClick={() => patchParams({ exposed: exposed === "true" ? null : "true" })}
            />
            <FilterRow
              icon={Shield}
              label="Internal only"
              active={exposed === "false"}
              onClick={() => patchParams({ exposed: exposed === "false" ? null : "false" })}
            />
          </FilterGroup>
        </aside>

        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <SearchField
              value={q}
              placeholder="Search name, ARN, resource type…"
              onChange={(value) => patchParams({ q: value || null })}
            />
            <SortSelect
              label="Sort"
              value={`${sort}:${order}`}
              options={[
                { value: "name:asc", label: "Name A→Z" },
                { value: "name:desc", label: "Name Z→A" },
                { value: "type:asc", label: "Type A→Z" },
                { value: "region:asc", label: "Region A→Z" },
                { value: "exposed:desc", label: "Exposure (internet first)" },
              ]}
              onChange={(v) => {
                const [s, o] = v.split(":");
                patchParams({ sort: s, order: o });
              }}
            />
          </div>

          <ActiveFilters
            chips={chips}
            onClear={() => patchParams({ category: null, cloud: null, exposed: null, q: null })}
          />

          <p className="text-sm text-[var(--muted)]">
            {query.isPending ? "Loading inventory…" : `${total} matching ${total === 1 ? "asset" : "assets"}`}
          </p>

          {query.isPending ? <TableSkeleton /> : null}
          {query.isError ? (
            <ErrorNote>{plainError(query.error, "Couldn't load inventory. Check that the API is running.")}</ErrorNote>
          ) : null}
          {query.data ? (
            <DataTable
              columns={columns}
              rows={query.data.items}
              getRowKey={(row) => row.asset_id}
              onRowClick={(row) => navigate(`/assets/${assetRouteId(row)}`)}
              emptyTitle="No assets match"
              emptyBody="Clear a filter or load a scenario from the dashboard."
            />
          ) : null}

          {query.data ? (
            <Pager offset={offset} pageSize={PAGE} total={total} onOffset={(next) => patchParams({ offset: String(next) })} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
