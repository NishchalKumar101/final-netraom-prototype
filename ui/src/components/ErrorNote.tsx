import type { ReactNode } from "react";

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-[var(--critical)]/30 bg-[var(--critical)]/10 px-3 py-2 text-sm text-[var(--danger-fg)]"
    >
      {children}
    </div>
  );
}
