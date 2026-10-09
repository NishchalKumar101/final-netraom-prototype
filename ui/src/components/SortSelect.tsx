import { fieldClass } from "@/lib/styles";
import { cn } from "@/lib/cn";

export function SortSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
      <span className="shrink-0">{label}</span>
      <select
        className={cn(fieldClass, "max-w-full py-1.5")}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
