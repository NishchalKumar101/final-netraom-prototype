import { cn } from "@/lib/cn";

export type LabTemplate = {
  id: string;
  title: string;
  description: string;
  level?: string;
  category?: string;
  query: string;
};

const LEVEL_ORDER = ["beginner", "medium", "advanced"] as const;
const LEVEL_LABEL: Record<string, string> = {
  beginner: "Beginner",
  medium: "Medium",
  advanced: "Advanced",
};

const levelTone: Record<string, string> = {
  beginner: "text-[var(--ok-fg)]",
  medium: "text-[var(--warn-fg)]",
  advanced: "text-[var(--sev-info-fg)]",
};

export function LabTemplatePicker({
  templates,
  onPick,
}: {
  templates: LabTemplate[];
  onPick: (t: LabTemplate) => void;
}) {
  const byLevel = LEVEL_ORDER.map((level) => ({
    level,
    label: LEVEL_LABEL[level],
    items: templates.filter((t) => (t.level ?? "beginner") === level),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-4">
      {byLevel.map((group) => (
        <div key={group.level}>
          <h3 className={cn("mb-2 text-[10px] font-semibold uppercase tracking-[0.14em]", levelTone[group.level])}>
            {group.label}
          </h3>
          <div className="flex flex-wrap gap-2">
            {group.items.map((t) => (
              <button
                key={t.id}
                type="button"
                title={t.description}
                className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-left text-xs transition-colors duration-150 hover:border-[var(--border-strong)] hover:bg-[var(--hover)]"
                onClick={() => onPick(t)}
              >
                <span className="font-medium text-[var(--foreground)]">{t.title}</span>
                {t.category ? (
                  <span className="mt-0.5 block text-[10px] tracking-wide text-[var(--muted)] uppercase">{t.category}</span>
                ) : null}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
