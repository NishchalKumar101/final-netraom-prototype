import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/Button";
import { ErrorNote } from "@/components/ErrorNote";
import { LabTemplatePicker } from "@/components/LabTemplatePicker";
import { Panel } from "@/components/Panel";
import { Skeleton } from "@/components/Skeleton";
import { getCypherTemplates, runCypherLab, type CypherLabResult } from "@/lib/api";
import { plainError } from "@/lib/errors";
import { LearnNav } from "@/pages/learn/LearnNav";

export function GraphLabPage() {
  const templates = useQuery({ queryKey: ["learn-cypher-templates"], queryFn: getCypherTemplates });
  const [cypher, setCypher] = useState("");
  const [result, setResult] = useState<CypherLabResult | null>(null);

  const run = useMutation({
    mutationFn: () => runCypherLab(cypher),
    onSuccess: (data) => setResult(data),
  });

  const columns = result?.columns ?? [];

  return (
    <div className="space-y-5">
      <LearnNav />
      <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        Read-only Cypher with tenant guard and automatic LIMIT. Load{" "}
        <strong className="font-medium text-[var(--foreground)]">enterprise</strong> first for medium/advanced
        toxic-combo paths. Neo4j Browser:{" "}
        <a className="text-[var(--link)] underline" href="http://localhost:7474" target="_blank" rel="noreferrer">
          localhost:7474
        </a>
        . Tenant: <code className="text-xs">{templates.data?.tenant_id ?? "…"}</code>
      </p>

      {templates.isPending ? <Skeleton className="h-16 w-full" /> : null}
      {templates.isError ? (
        <ErrorNote>{plainError(templates.error, "Couldn't load Cypher templates. You can still type a query.")}</ErrorNote>
      ) : null}
      {templates.data?.templates ? (
        <LabTemplatePicker
          templates={templates.data.templates}
          onPick={(t) => {
            setCypher(t.query);
            setResult(null);
          }}
        />
      ) : null}

      <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)]">
        <div className="border-b border-[var(--border)] px-3 py-2 text-xs font-medium text-[var(--muted)]">Cypher</div>
        <textarea
          className="h-56 w-full bg-transparent p-3 font-mono text-xs text-[var(--foreground)] outline-none"
          placeholder="MATCH (n:TrustGraphNode { tenant_id: '…' }) RETURN n LIMIT 25"
          value={cypher}
          aria-label="Cypher"
          onChange={(e) => setCypher(e.target.value)}
        />
      </div>
      <Button disabled={run.isPending || !cypher.trim()} onClick={() => run.mutate()}>
        {run.isPending ? "Running…" : "Run Cypher"}
      </Button>
      {run.isError ? <ErrorNote>{plainError(run.error, "Query failed.")}</ErrorNote> : null}

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
                      <td key={c} className="max-w-md truncate px-3 py-2 font-mono">
                        {typeof row[c] === "object" ? JSON.stringify(row[c]) : String(row[c] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : null}

      <Panel title="Schema cheat sheet">
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
          <li>
            <code>TrustGraphNode</code>: tenant_id, node_id, kind, name, resource_type, props (JSON string)
          </li>
          <li>
            <code>TRUST_EDGE</code>: property <code>kind</code> — allows_ingress, has_sg, attached_to, can_write,
            deploys, serves, exposes
          </li>
        </ul>
      </Panel>
    </div>
  );
}
