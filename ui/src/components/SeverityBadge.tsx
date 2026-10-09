import { cn } from "@/lib/cn";

const styles: Record<string, string> = {
  critical: "bg-[#e5484d]/15 text-[var(--sev-critical-fg)] ring-1 ring-[#e5484d]/35",
  high: "bg-[#e08a2c]/15 text-[var(--sev-high-fg)] ring-1 ring-[#e08a2c]/35",
  medium: "bg-[#e0a106]/15 text-[var(--warn-fg)] ring-1 ring-[#e0a106]/35",
  low: "bg-[var(--wash-strong)] text-[var(--sev-low-fg)] ring-1 ring-[var(--ring-soft)]",
  info: "bg-[#3b82f6]/15 text-[var(--sev-info-fg)] ring-1 ring-[#3b82f6]/30",
};

const dots: Record<string, string> = {
  critical: "bg-[#e5484d]",
  high: "bg-[#e08a2c]",
  medium: "bg-[#e0a106]",
  low: "bg-[#8ea0bb]",
  info: "bg-[#3b82f6]",
};

export function severityBarClass(severity: string) {
  return dots[severity] ?? "bg-[#8ea0bb]";
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        styles[severity] ?? styles.low,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dots[severity] ?? dots.low)} aria-hidden />
      {severity}
    </span>
  );
}

export function ExposureBadge({ exposed }: { exposed?: boolean | null }) {
  if (exposed === true) {
    return (
      <span className="inline-flex items-center rounded-full bg-[#e5484d]/15 px-2 py-0.5 text-xs font-medium text-[var(--sev-critical-fg)] ring-1 ring-[#e5484d]/30">
        Internet
      </span>
    );
  }
  if (exposed === false) {
    return (
      <span className="inline-flex items-center rounded-full bg-[#34b27b]/15 px-2 py-0.5 text-xs font-medium text-[var(--ok-fg)] ring-1 ring-[#34b27b]/30">
        Internal
      </span>
    );
  }
  return <span className="text-xs text-[var(--muted)]">—</span>;
}

export function CloudBadge({ cloud }: { cloud?: string | null }) {
  if (!cloud) return <span className="text-xs text-[var(--muted)]">—</span>;
  return (
    <span className="inline-flex items-center rounded-md bg-[var(--wash-strong)] px-1.5 py-0.5 text-[11px] font-semibold tracking-wide text-[var(--foreground)] uppercase ring-1 ring-[var(--ring-soft)]">
      {cloud}
    </span>
  );
}

export function RiskScore({ score }: { score?: number | null }) {
  const value = score ?? 0;
  const tone =
    value >= 90 ? styles.critical : value >= 70 ? styles.high : value >= 40 ? styles.medium : styles.info;
  return (
    <span className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums", tone)}>
      {value}/100
    </span>
  );
}
