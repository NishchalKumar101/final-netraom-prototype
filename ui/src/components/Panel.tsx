import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { surfaceClass } from "@/lib/styles";

export function Panel({
  title,
  eyebrow,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn(surfaceClass, "min-w-0", className)}>
      {title || eyebrow || action ? (
        <header className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
          <div className="min-w-0">
            {eyebrow ? (
              <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">{eyebrow}</div>
            ) : null}
            {title ? <h2 className="text-sm font-semibold break-words text-[var(--foreground)]">{title}</h2> : null}
          </div>
          {action}
        </header>
      ) : null}
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
