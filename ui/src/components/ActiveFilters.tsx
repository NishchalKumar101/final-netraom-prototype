import { FilterChip } from "@/components/FilterChip";

export function ActiveFilters({
  chips,
  onClear,
}: {
  chips: { id: string; label: string; onRemove: () => void }[];
  onClear: () => void;
}) {
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">Active</span>
      {chips.map((chip) => (
        <FilterChip key={chip.id} label={chip.label} active dismissible onClick={chip.onRemove} />
      ))}
      <button
        type="button"
        onClick={onClear}
        className="rounded-md px-2 py-1 text-xs font-medium text-[var(--muted)] transition-colors hover:bg-[var(--hover)] hover:text-[var(--foreground)]"
      >
        Clear all
      </button>
    </div>
  );
}
