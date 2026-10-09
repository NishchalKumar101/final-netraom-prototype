import { Button } from "@/components/Button";

export function Pager({
  offset,
  pageSize,
  total,
  onOffset,
}: {
  offset: number;
  pageSize: number;
  total: number;
  onOffset: (next: number) => void;
}) {
  if (total <= pageSize) return null;
  const page = Math.floor(offset / pageSize) + 1;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = offset + 1;
  const to = Math.min(offset + pageSize, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <span className="text-[var(--muted)]">
        {from}–{to} of {total}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" className="px-2.5 py-1" disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - pageSize))}>
          Previous
        </Button>
        <span className="text-[var(--muted)]">
          Page {page} / {pages}
        </span>
        <Button
          variant="secondary"
          className="px-2.5 py-1"
          disabled={offset + pageSize >= total}
          onClick={() => onOffset(offset + pageSize)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
