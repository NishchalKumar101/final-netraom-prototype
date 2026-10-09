import { useSyncExternalStore } from "react";

export const ANALYST_STATUSES = ["New", "Investigating", "Mitigated", "Resolved"] as const;
export type AnalystStatus = (typeof ANALYST_STATUSES)[number];

export type WorkflowEntry = {
  status: AnalystStatus;
  read: boolean;
  dismissed: boolean;
};

const STORAGE_KEY = "netraom-analyst-workflow-v1";

let state: Record<string, WorkflowEntry> = load();
const listeners = new Set<() => void>();

function load(): Record<string, WorkflowEntry> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, WorkflowEntry>;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed;
  } catch {
    return {};
  }
}

function emit() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return state;
}

function update(id: string, patch: Partial<WorkflowEntry>) {
  const current = state[id] ?? { status: "New" as AnalystStatus, read: false, dismissed: false };
  state = { ...state, [id]: { ...current, ...patch } };
  emit();
}

export function setAnalystStatus(id: string, status: AnalystStatus) {
  update(id, { status, read: true });
}

export function markAnalystRead(id: string) {
  update(id, { read: true });
}

export function dismissAnalystItem(id: string) {
  update(id, { dismissed: true, read: true });
}

export function markAllAnalystRead(ids: string[]) {
  const next = { ...state };
  for (const id of ids) {
    const current = next[id] ?? { status: "New" as AnalystStatus, read: false, dismissed: false };
    next[id] = { ...current, read: true };
  }
  state = next;
  emit();
}

export function useAnalystWorkflow() {
  const workflow = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return { workflow, setAnalystStatus, markAnalystRead, dismissAnalystItem, markAllAnalystRead };
}
