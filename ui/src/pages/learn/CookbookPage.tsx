import { Panel } from "@/components/Panel";
import { LearnNav } from "@/pages/learn/LearnNav";

const docs = [
  {
    path: "docs/teaching-sql.md",
    detail: "Inventory slices, CSPM findings, toxic-combo bridge columns",
  },
  {
    path: "docs/teaching-cypher.md",
    detail: "Public resources, SSH ingress, T2-shaped paths, API Gateway",
  },
  {
    path: "docs/teaching-session-runbook.md",
    detail: "Full session agenda and demo script",
  },
  {
    path: "fixtures/raw/*.json",
    detail: "Synthetic collector bundles; normalized in fixtures/normalized/",
  },
];

export function CookbookPage() {
  return (
    <div className="space-y-5">
      <LearnNav />
      <p className="text-sm leading-relaxed text-[var(--muted)]">
        Start with <code>docs/student-guide.md</code> in the repo (full walkthrough + after-demo). Labs below:
      </p>
      <ul className="grid gap-3 md:grid-cols-2">
        {docs.map((doc) => (
          <li key={doc.path} className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
            <code className="text-xs text-[var(--link)]">{doc.path}</code>
            <p className="mt-1 text-sm text-[var(--muted)]">{doc.detail}</p>
          </li>
        ))}
      </ul>

      <Panel title="Bridge query (Postgres → Neo4j)">
        <p className="mb-3 text-sm text-[var(--muted)]">
          Pick a toxic-combo row in SQL, copy a node id from <code>trust_graph_node_ids</code>, then in Neo4j:
        </p>
        <pre className="overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--inset)] p-3 text-xs text-[var(--code-fg)]">{`MATCH (n:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111', node_id: '<paste>' })
RETURN n
MATCH (n)-[r:TRUST_EDGE]-(m)
RETURN n, r, m LIMIT 50`}</pre>
      </Panel>
    </div>
  );
}
