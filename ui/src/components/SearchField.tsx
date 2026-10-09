import { Search } from "lucide-react";

import { cn } from "@/lib/cn";
import { fieldClass } from "@/lib/styles";

export function SearchField({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  label?: string;
}) {
  return (
    <div className="relative min-w-0 flex-1">
      <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" aria-hidden />
      <input
        aria-label={label ?? placeholder}
        className={cn(fieldClass, "w-full pl-9")}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
