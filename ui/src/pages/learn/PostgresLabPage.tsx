import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/Button";
import { ErrorNote } from "@/components/ErrorNote";
import { LabTemplatePicker } from "@/components/LabTemplatePicker";
import { Panel } from "@/components/Panel";
import { Skeleton } from "@/components/Skeleton";
import { getPostgresSample, getPostgresSchema, getSqlTemplates, runSqlLab, type SqlLabResult } from "@/lib/api";
import { plainError } from "@/lib/errors";
import { fieldClass } from "@/lib/styles";
import { LearnNav } from "@/pages/learn/LearnNav";

const DEFAULT_SQL = `SELECT display_name, resource_type, cloud, is_internet_exposed
FROM assets
ORDER BY is_internet_exposed DESC NULLS LAST
LIMIT 20`;

export function PostgresLabPage() {
  const [table, setTable] = useState<"assets" | "findings">("findings");
  const [sql, setSql] = useState(DEFAULT_SQL);
  const [result, setResult] = useState<SqlLabResult | null>(null);

  const schema = useQuery({ queryKey: ["learn-pg-schema"], queryFn: getPostgresSchema });
  const sqlTemplates = useQuery({ queryKey: ["learn-sql-templates"], queryFn: getSqlTemplates });
  const sample = useQuery({
    queryKey: ["learn-pg-sample", table],
    queryFn: () => getPostgresSample(table, 10),
  });

  const run = useMutation({
    mutationFn: () => runSqlLab(sql),
    onSuccess: (data) => setResult(data),
  });

  const columns = result?.columns ?? [];

  return (
    <div className="space-y-5">
      <LearnNav />
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        SELECT-only queries (same guard as the API). For a full SQL IDE use{" "}
        <a
          className="text-[var(--link)] underline"
          href="http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo"
          target="_blank"
          rel="noreferrer"
        >
          Adminer (PostgreSQL)
        </a>{" "}
        — System <strong className="font-medium text-[var(--foreground)]">PostgreSQL</strong>, Server{" "}
        <code>postgres</code>, password <code>student</code>. Use <code>localhost:5433</code> only for psql on your
        Mac, not in Adminer. Load <strong className="font-medium text-[var(--foreground)]">enterprise</strong> on
        Dashboard for medium/advanced findings.
      </p>

      {sqlTemplates.isPending ? <Skeleton className="h-16 w-full" /> : null}
      {sqlTemplates.isError ? (
        <ErrorNote>{plainError(sqlTemplates.error, "Couldn't load SQL templates. You can still type a query.")}</ErrorNote>
      ) : null}
      {sqlTemplates.data?.templates ? (
        <LabTemplatePicker
          templates={sqlTemplates.data.templates}
          onPick={(t) => {
            setSql(t.query);
            setResult(null);
          }}
        />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          {schema.isPending ? <Skeleton className="h-40 w-full" /> : null}
          {schema.isError ? (
            <ErrorNote>{plainError(schema.error, "Couldn't load the Postgres schema.")}</ErrorNote>
          ) : null}
          {schema.data?.tables.map((t) => (
            <Panel key={t.name} title={t.name} eyebrow="Table">
              <p className="text-xs text-[var(--muted)]">{t.purpose}</p>
              <ul className="mt-3 space-y-1 font-mono text-xs text-[var(--muted)]">
                {t.columns.map((c) => (
                  <li key={c.name} className="flex flex-wrap items-center gap-2">
                    <span className="text-[var(--foreground)]">{c.name}</span>
                    <span className="opacity-70">({c.type})</span>
                    {c.primary_key ? (
                      <span className="rounded bg-[var(--accent)]/15 px-1.5 py-0.5 text-[10px] font-sans font-semibold tracking-wide text-[var(--sev-info-fg)] uppercase">
                        PK
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </Panel>
          ))}
        </div>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-sm text-[var(--muted)]" htmlFor="sample-table">
              Sample rows
            </label>
            <select
              id="sample-table"
              className={fieldClass}
              value={table}
              onChange={(e) => setTable(e.target.value as "assets" | "findings")}
            >
              <option value="assets">assets</option>
              <option value="findings">findings</option>
            </select>
          </div>
          {sample.isPending ? <Skeleton className="h-32 w-full" /> : null}
          {sample.isError ? (
            <ErrorNote>{plainError(sample.error, "Couldn't load sample rows.")}</ErrorNote>
          ) : null}
          {sample.data ? (
            <pre className="max-h-48 overflow-auto rounded-xl border border-[var(--border)] bg-[var(--inset)] p-3 text-xs text-[var(--code-fg)]">
              {JSON.stringify(sample.data.rows, null, 2)}
            </pre>
          ) : null}

          <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)]">
            <div className="border-b border-[var(--border)] px-3 py-2 text-xs font-medium text-[var(--muted)]">
              SQL (SELECT only)
            </div>
            <textarea
              className="h-40 w-full bg-transparent p-3 font-mono text-xs text-[var(--foreground)] outline-none"
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              aria-label="SQL (SELECT only)"
            />
          </div>
          <Button disabled={run.isPending} onClick={() => run.mutate()}>
            {run.isPending ? "Running…" : "Run query"}
          </Button>
          {run.isError ? (
            <ErrorNote>{plainError(run.error, "Query failed.")}</ErrorNote>
          ) : null}
        </div>
      </div>

      {result ? (
        <div className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]">
          <p className="border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--muted)]">
            {result.row_count} row(s)
          </p>
          {result.rows.length === 0 ? (
            <p className="px-4 py-6 text-sm text-[var(--muted)]">Query returned no rows.</p>
          ) : (
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-[var(--muted)]">
                  {columns.map((c) => (
                    <th key={c} className="px-3 py-2 font-medium">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i} className="border-t border-[var(--border)]">
                    {columns.map((c) => (
                      <td key={c} className="max-w-xs truncate px-3 py-2 font-mono">
                        {formatCell(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : null}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
