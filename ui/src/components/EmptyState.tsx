import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-1.5 rounded-xl border border-dashed border-[var(--border)] bg-[var(--wash)] px-4 py-8">
      {Icon ? <Icon className="mb-1 h-5 w-5 text-[var(--muted)]" aria-hidden /> : null}
      <p className="text-sm font-medium text-[var(--foreground)]">{title}</p>
      {body ? <p className="max-w-lg text-sm leading-relaxed text-[var(--muted)]">{body}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
