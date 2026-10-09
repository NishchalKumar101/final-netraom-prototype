import type { LucideIcon } from "lucide-react";

import { Skeleton } from "@/components/Skeleton";
import { cn } from "@/lib/cn";

export function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  loading,
}: {
  label: string;
  value?: string | number;
  hint?: string;
  icon: LucideIcon;
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--inset-highlight)]">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--muted)]">{label}</div>
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-[var(--accent)]/12 text-[var(--link)]">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      {loading ? (
        <Skeleton className="mt-3 h-8 w-20" />
      ) : (
        <div className="mt-2 text-3xl font-semibold tabular-nums tracking-tight">{value}</div>
      )}
      {hint ? <p className={cn("mt-1 text-xs text-[var(--muted)]")}>{hint}</p> : null}
    </div>
  );
}
