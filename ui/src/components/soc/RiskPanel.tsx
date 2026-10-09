import { Link } from "react-router-dom";

import { Button } from "@/components/Button";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ANALYST_STATUSES, setAnalystStatus, type AnalystStatus } from "@/lib/analystWorkflow";
import { categoryLabel, findingHref, type RiskItem } from "@/lib/securityAnalytics";

export function RiskPanel({ risks, empty }: { risks: RiskItem[]; empty: string }) {
  if (!risks.length) {
    return <p className="text-sm text-[var(--muted)]">{empty}</p>;
  }

  return (
    <ul className="space-y-3">
      {risks.map((risk) => (
        <li key={risk.id} className="rounded-xl border border-[var(--border)] bg-[var(--inset)] p-3">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={risk.severity} />
            <span className="text-sm font-medium">{risk.title}</span>
            <span className="text-[10px] font-semibold tracking-[0.12em] text-[var(--muted)] uppercase">Analyst workflow</span>
          </div>
          <dl className="mt-2 grid gap-1 text-xs text-[var(--muted)] sm:grid-cols-2">
            <div>Entity: {risk.entity}</div>
            <div>Time: {risk.time.replace("T", " ").slice(0, 16)} UTC · simulated</div>
            <div>Category: {categoryLabel(risk.category)}</div>
            <div>Status: {risk.status} · this browser, not server-verified</div>
          </dl>
          <p className="mt-2 text-sm text-[var(--foreground)]">{risk.impact}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">{risk.mitigation}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {ANALYST_STATUSES.map((status) => (
              <Button
                key={status}
                variant={risk.status === status ? "primary" : "secondary"}
                className="px-2.5 py-1 text-xs"
                aria-pressed={risk.status === status}
                onClick={() => setAnalystStatus(risk.id, status as AnalystStatus)}
              >
                {status}
              </Button>
            ))}
            {risk.fingerprint ? (
              <Link
                to={findingHref(risk)}
                className="inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium text-[var(--link)] hover:underline"
              >
                Open finding
              </Link>
            ) : (
              <span className="text-xs text-[var(--muted)]">No loaded finding — simulated row</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
