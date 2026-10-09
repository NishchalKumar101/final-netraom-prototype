import { useEffect } from "react";

import { ErrorNote } from "@/components/ErrorNote";
import { Skeleton } from "@/components/Skeleton";

export function JsonPanelModal({
  open,
  onClose,
  title,
  sections,
  loading,
  error,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  sections: { id: string; label: string; data: unknown; note?: string }[];
  loading?: boolean;
  error?: string | null;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--overlay)] p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="json-panel-title"
        className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
          <h2 id="json-panel-title" className="text-base font-semibold">
            {title}
          </h2>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-sm text-[var(--muted)] transition-colors hover:bg-[var(--hover)] hover:text-[var(--foreground)]"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="space-y-4 overflow-y-auto p-4">
          {loading ? (
            <div className="space-y-2">
              <p className="text-sm text-[var(--muted)]">Loading JSON…</p>
              <Skeleton className="h-28 w-full" />
            </div>
          ) : null}
          {error ? <ErrorNote>{error}</ErrorNote> : null}
          {sections.map((s) => (
            <div key={s.id}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <h3 className="text-sm font-medium">{s.label}</h3>
                <button
                  type="button"
                  className="text-xs font-medium text-[var(--link)] hover:underline"
                  onClick={() => navigator.clipboard.writeText(JSON.stringify(s.data, null, 2))}
                >
                  Copy
                </button>
              </div>
              {s.note ? <p className="mb-2 text-xs leading-relaxed text-[var(--muted)]">{s.note}</p> : null}
              <pre className="max-h-64 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--inset)] p-3 text-[11px] leading-relaxed text-[var(--code-fg)]">
                {JSON.stringify(s.data, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
