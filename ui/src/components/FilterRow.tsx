import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function FilterGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="px-2.5 pb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">{title}</div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

export function FilterRow({
  icon: Icon,
  label,
  count,
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  count?: number;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors duration-150",
        active
          ? "bg-[var(--accent)]/15 text-white shadow-[inset_2px_0_0_var(--accent)]"
          : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count != null ? (
        <span className={cn("tabular-nums text-xs", active ? "text-white/75" : "text-[var(--muted)]")}>{count}</span>
      ) : null}
    </button>
  );
}
