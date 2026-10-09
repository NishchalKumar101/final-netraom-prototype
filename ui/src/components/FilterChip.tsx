import { X } from "lucide-react";

import { cn } from "@/lib/cn";

export function FilterChip({
  label,
  count,
  active,
  dismissible,
  onClick,
}: {
  label: string;
  count?: number;
  active?: boolean;
  dismissible?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-150",
        active
          ? "border-[var(--accent)]/50 bg-[var(--accent)]/18 text-white"
          : "border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)]",
      )}
    >
      <span className="max-w-[220px] truncate">{label}</span>
      {count != null ? <span className="ml-1 tabular-nums opacity-70">({count})</span> : null}
      {dismissible ? <X className="ml-1 h-3 w-3" aria-hidden /> : null}
    </button>
  );
}
