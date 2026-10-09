import type { ReactNode } from "react";

import { EmptyState } from "@/components/EmptyState";
import { cn } from "@/lib/cn";

export type Column<T> = {
  key: string;
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
};

export function DataTable<T>({
  columns,
  rows,
  onRowClick,
  getRowKey,
  isSelected,
  emptyTitle = "Nothing to show",
  emptyBody,
}: {
  columns: Column<T>[];
  rows: T[];
  onRowClick?: (row: T) => void;
  getRowKey?: (row: T, index: number) => string;
  isSelected?: (row: T) => boolean;
  emptyTitle?: string;
  emptyBody?: string;
}) {
  return (
    <div className="max-h-[min(720px,calc(100vh-14rem))] overflow-auto rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 z-10 bg-[var(--card)] text-left text-[11px] uppercase tracking-[0.12em] text-[var(--muted)] shadow-[0_1px_0_var(--border)]">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.className ?? "px-4 py-3 font-semibold"}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-2">
                <EmptyState title={emptyTitle} body={emptyBody} />
              </td>
            </tr>
          ) : (
            rows.map((row, i) => {
              const selected = isSelected?.(row);
              return (
                <tr
                  key={getRowKey ? getRowKey(row, i) : i}
                  className={cn(
                    "border-t border-[var(--border)] transition-colors duration-150 even:bg-[var(--wash)]",
                    onRowClick && "cursor-pointer hover:bg-[var(--hover)]",
                    selected && "bg-[var(--accent)]/10",
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((c) => (
                    <td key={c.key} className={c.className ?? "px-4 py-3 align-middle"}>
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
