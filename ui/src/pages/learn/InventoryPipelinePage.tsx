import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ErrorNote } from "@/components/ErrorNote";
import { Panel } from "@/components/Panel";
import { Skeleton } from "@/components/Skeleton";
import { getInventoryFixtures, getInventoryPayload, type InventoryFixtureId } from "@/lib/api";
import { plainError } from "@/lib/errors";
import { fieldClass } from "@/lib/styles";
import { cn } from "@/lib/cn";
import { LearnNav } from "@/pages/learn/LearnNav";

export function InventoryPipelinePage() {
  const fixtures = useQuery({ queryKey: ["learn-inventory-fixtures"], queryFn: getInventoryFixtures });
  const [fixtureId, setFixtureId] = useState<InventoryFixtureId>("aws");
  const [previewLimit, setPreviewLimit] = useState(25);

  const payload = useQuery({
    queryKey: ["learn-inventory", fixtureId, previewLimit],
    queryFn: () => getInventoryPayload(fixtureId, previewLimit),
  });

  const pipeline = payload.data?.pipeline ?? fixtures.data?.pipeline ?? [];
  const bothPayload = payload.data?.fixture_id === "both" ? payload.data : undefined;

  const rawJson = useMemo(() => formatRaw(payload.data), [payload.data]);
  const normalizedJson = useMemo(() => formatNormalized(payload.data), [payload.data]);

  return (
    <div className="space-y-5">
      <LearnNav />
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        End-to-end teaching view: what collectors return from the cloud vs what the normalizer produces before{" "}
        <code className="text-xs">POST /demo/load</code> writes Neo4j + Postgres. Load the same fixture from Dashboard
        to see findings.
      </p>

      {fixtures.isError ? (
        <ErrorNote>{plainError(fixtures.error, "Couldn't load the fixture list.")}</ErrorNote>
      ) : null}
      {payload.isError ? (
        <ErrorNote>{plainError(payload.error, "Couldn't load this fixture payload.")}</ErrorNote>
      ) : null}

      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Fixture</span>
          <select
            className={fieldClass}
            value={fixtureId}
            onChange={(e) => setFixtureId(e.target.value as InventoryFixtureId)}
          >
            {(fixtures.data?.fixtures ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Normalized preview limit</span>
          <input
            type="number"
            min={5}
            max={100}
            className={cn(fieldClass, "w-24")}
            value={previewLimit}
            onChange={(e) => setPreviewLimit(Number(e.target.value) || 25)}
          />
        </label>
        {payload.data?.load_fixture_key ? (
          <p className="text-xs text-[var(--muted)]">
            Dashboard load key: <code>{payload.data.load_fixture_key}</code>
          </p>
        ) : null}
      </div>

      {pipeline.length > 0 ? (
        <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {pipeline.map((s, i) => (
            <li key={s.stage} className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-3">
              <div className="text-[10px] font-semibold tracking-[0.14em] text-[var(--live)] uppercase">
                {i + 1}. {s.stage}
              </div>
              <div className="mt-1 text-sm font-medium">{s.title}</div>
              <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">{s.detail}</p>
            </li>
          ))}
        </ol>
      ) : null}

      {fixtureId === "both" && payload.isPending ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      ) : null}

      {fixtureId === "both" && bothPayload ? (
        <div className="space-y-8">
          {bothPayload.clouds.map((cloud) => (
            <div key={cloud.fixture_id} className="space-y-3">
              <h2 className="text-base font-semibold">{cloud.label}</h2>
              <div className="grid gap-4 lg:grid-cols-2">
                <JsonPanel title="Raw cloud inventory" json={JSON.stringify(cloud.raw, null, 2)} />
                <JsonPanel
                  title="Normalized trust graph bundle"
                  subtitle={previewSubtitle(cloud.normalized)}
                  json={JSON.stringify(cloud.normalized, null, 2)}
                />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {fixtureId !== "both" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <JsonPanel title="Raw cloud inventory" json={rawJson} loading={payload.isPending} />
          <JsonPanel
            title="Normalized trust graph bundle"
            subtitle={previewSubtitle(payload.data && "normalized" in payload.data ? payload.data.normalized : undefined)}
            json={normalizedJson}
            loading={payload.isPending}
          />
        </div>
      ) : null}

      {payload.data && "raw" in payload.data && payload.data.raw && "normalizer_notes" in payload.data.raw && Array.isArray(payload.data.raw.normalizer_notes) ? (
        <Panel title="How raw maps to graph (this lab)">
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {(payload.data.raw.normalizer_notes as string[]).map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}

function JsonPanel({
  title,
  subtitle,
  json,
  loading,
}: {
  title: string;
  subtitle?: string;
  json: string;
  loading?: boolean;
}) {
  return (
    <div className="flex min-h-[320px] min-w-0 flex-col rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-2">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">{title}</h2>
          {subtitle ? <p className="text-xs text-[var(--muted)]">{subtitle}</p> : null}
        </div>
        <button
          type="button"
          className="shrink-0 text-xs font-medium text-[var(--link)] hover:underline disabled:opacity-40"
          disabled={loading || !json}
          onClick={() => navigator.clipboard.writeText(json)}
        >
          Copy
        </button>
      </div>
      {loading ? (
        <div className="space-y-2 p-3">
          <p className="text-xs text-[var(--muted)]">Loading…</p>
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <pre className="max-h-[480px] flex-1 overflow-auto p-3 font-mono text-[11px] leading-relaxed text-[var(--muted)]">
          {json || "—"}
        </pre>
      )}
    </div>
  );
}

function previewSubtitle(normalized: Record<string, unknown> | undefined): string | undefined {
  const preview = normalized?._preview as { truncated?: boolean; totals?: Record<string, number> } | undefined;
  if (!preview?.totals) return undefined;
  const t = preview.totals;
  const parts = [`${t.assets ?? 0} assets`, `${t.nodes ?? 0} nodes`, `${t.edges ?? 0} edges`];
  return preview.truncated ? `Preview (totals: ${parts.join(", ")})` : parts.join(", ");
}

function formatRaw(data: Awaited<ReturnType<typeof getInventoryPayload>> | undefined): string {
  if (!data || "clouds" in data) return "";
  if (!data.raw) return "";
  return JSON.stringify(data.raw, null, 2);
}

function formatNormalized(data: Awaited<ReturnType<typeof getInventoryPayload>> | undefined): string {
  if (!data || "clouds" in data) return "";
  if (!data.normalized) return "";
  return JSON.stringify(data.normalized, null, 2);
}
