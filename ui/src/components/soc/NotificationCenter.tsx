import { Bell, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/Button";
import { SeverityBadge } from "@/components/SeverityBadge";
import {
  dismissAnalystItem,
  markAllAnalystRead,
  markAnalystRead,
  useAnalystWorkflow,
} from "@/lib/analystWorkflow";
import { findingHref, type RiskItem } from "@/lib/securityAnalytics";
import { useSecurityAnalytics } from "@/lib/useSecurityAnalytics";

type Toast = { id: string; title: string; detail: string; href?: string };

export function NotificationBell() {
  const { model } = useSecurityAnalytics();
  const { workflow } = useAnalystWorkflow();
  const [open, setOpen] = useState(false);
  const [severity, setSeverity] = useState("all");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const risks = (model?.risks ?? []).map((risk) => {
    const stored = workflow[risk.id];
    return stored ? { ...risk, status: stored.status, read: stored.read, dismissed: stored.dismissed } : risk;
  });
  const visible = risks.filter((risk) => {
    if (risk.dismissed) return false;
    if (severity !== "all" && risk.severity !== severity) return false;
    if (unreadOnly && risk.read) return false;
    return true;
  });
  const unread = risks.filter((risk) => !risk.read && !risk.dismissed).length;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    panelRef.current?.querySelector<HTMLElement>("button, a, select")?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="relative">
      <Button
        ref={buttonRef}
        variant="secondary"
        className="relative h-9 px-2.5"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        onClick={() => setOpen((value) => !value)}
      >
        <Bell className="h-4 w-4" aria-hidden />
        {unread > 0 ? (
          <span className="absolute -top-1 -right-1 grid min-w-5 place-items-center rounded-full bg-[var(--critical)] px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </Button>
      {open ? (
        <div
          id={panelId}
          ref={panelRef}
          role="dialog"
          aria-label="Notification center"
          className="fixed inset-x-3 top-16 z-40 max-h-[70vh] overflow-auto rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 shadow-[var(--shadow)] md:absolute md:inset-x-auto md:right-0 md:top-full md:mt-2 md:w-[380px]"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">Notification center</h2>
            <button type="button" className="rounded-md p-1 text-[var(--muted)] hover:bg-[var(--hover)]" aria-label="Close notifications" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Seeded from the analytics model. Read and dismiss stay in this browser.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="text-xs text-[var(--muted)]">
              Severity
              <select
                className="ml-1 rounded-md border border-[var(--border)] bg-[var(--inset)] px-2 py-1 text-xs text-[var(--foreground)]"
                value={severity}
                onChange={(event) => setSeverity(event.target.value)}
              >
                {["all", "critical", "high", "medium", "low"].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label className="inline-flex items-center gap-1 text-xs text-[var(--muted)]">
              <input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} />
              Unread only
            </label>
            <Button
              variant="ghost"
              className="px-2 py-1 text-xs"
              onClick={() => markAllAnalystRead(visible.map((risk) => risk.id))}
            >
              Mark visible read
            </Button>
          </div>
          {visible.length === 0 ? <p className="mt-3 text-sm text-[var(--muted)]">No notifications in this filter.</p> : null}
          <ul className="mt-3 space-y-2">
            {visible.map((risk) => (
              <NotificationRow key={risk.id} risk={risk} onOpen={() => setOpen(false)} />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function NotificationRow({ risk, onOpen }: { risk: RiskItem; onOpen: () => void }) {
  return (
    <li className="rounded-lg border border-[var(--border)] bg-[var(--inset)] p-2">
      <div className="flex items-start gap-2">
        <SeverityBadge severity={risk.severity} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{risk.title}</div>
          <div className="text-xs text-[var(--muted)]">
            {risk.entity} · {risk.status}
            {risk.read ? "" : " · unread"}
          </div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => markAnalystRead(risk.id)}>
          Mark read
        </Button>
        <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => dismissAnalystItem(risk.id)}>
          Dismiss
        </Button>
        {risk.fingerprint ? (
          <Link to={findingHref(risk)} className="inline-flex items-center px-2 py-1 text-xs font-medium text-[var(--link)] hover:underline" onClick={onOpen}>
            Open finding
          </Link>
        ) : null}
      </div>
    </li>
  );
}

export function NotificationToasts() {
  const { model } = useSecurityAnalytics();
  const seen = useRef<Set<string> | null>(null);
  const queue = useRef<RiskItem[]>([]);
  const lastAt = useRef(0);
  const timers = useRef<number[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    if (!model || model.dataState !== "ready") return;
    const hot = model.risks.filter(
      (risk) => (risk.severity === "critical" || risk.severity === "high") && !risk.dismissed,
    );
    if (seen.current == null) {
      seen.current = new Set(hot.map((risk) => risk.id));
      return;
    }
    for (const risk of hot) {
      if (!seen.current.has(risk.id)) {
        seen.current.add(risk.id);
        queue.current.push(risk);
      }
    }
  }, [model]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (!queue.current.length) return;
      const now = Date.now();
      if (now - lastAt.current < 8000) return;
      lastAt.current = now;
      let toast: Toast;
      if (queue.current.length > 3) {
        const count = queue.current.length;
        queue.current = [];
        toast = {
          id: `burst-${now}`,
          title: `${count} new critical or high findings`,
          detail: "Opened in the notification center so this toast stays quiet.",
        };
      } else {
        const risk = queue.current.shift();
        if (!risk) return;
        toast = {
          id: `${risk.id}-${now}`,
          title: risk.title,
          detail: `${risk.severity} · ${risk.entity} · simulated notice`,
          href: risk.fingerprint ? findingHref(risk) : undefined,
        };
      }
      setToasts((current) => [...current, toast].slice(-3));
      const timeout = window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== toast.id));
      }, 6000);
      timers.current.push(timeout);
    }, 1000);
    return () => {
      window.clearInterval(interval);
      timers.current.forEach((timeout) => window.clearTimeout(timeout));
      timers.current = [];
    };
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="pointer-events-none fixed right-3 bottom-3 z-50 flex w-[min(100%-1.5rem,320px)] flex-col gap-2" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 shadow-[var(--shadow)]">
          <div className="text-sm font-medium">{toast.title}</div>
          <p className="mt-1 text-xs text-[var(--muted)]">{toast.detail}</p>
          {toast.href ? (
            <Link to={toast.href} className="mt-2 inline-block text-xs font-medium text-[var(--link)] hover:underline">
              Open finding
            </Link>
          ) : null}
        </div>
      ))}
    </div>
  );
}
