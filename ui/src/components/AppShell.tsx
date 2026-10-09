import { Bot, Database, GraduationCap, LayoutDashboard, Shield, ShieldAlert } from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import clsx from "clsx";

import { NotificationBell } from "@/components/soc/NotificationCenter";
import { ThemeToggle } from "@/components/soc/ThemeToggle";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assets", label: "Inventory", icon: Database },
  { to: "/findings", label: "Findings", icon: ShieldAlert },
  { to: "/learn", label: "Learn", icon: GraduationCap },
  { to: "/assistant", label: "Assistant", icon: Bot },
];

function pageTitle(pathname: string) {
  if (pathname.startsWith("/assets/")) return "Asset detail";
  if (pathname.startsWith("/assets")) return "Inventory";
  if (pathname.startsWith("/findings")) return "Findings";
  if (pathname.startsWith("/learn/inventory")) return "Inventory pipeline";
  if (pathname.startsWith("/learn/postgres")) return "Postgres lab";
  if (pathname.startsWith("/learn/graph")) return "Graph & Cypher lab";
  if (pathname.startsWith("/learn/cookbook")) return "Query cookbook";
  if (pathname.startsWith("/learn/attack-path")) return "Attack path analysis";
  if (pathname.startsWith("/learn")) return "Learn";
  if (pathname.startsWith("/assistant")) return "Security assistant";
  return "Dashboard";
}

function SideNav({ layout }: { layout: "row" | "col" }) {
  return (
    <nav className={layout === "row" ? "flex gap-1 overflow-x-auto" : "flex flex-col gap-1"} aria-label="Primary">
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors duration-150",
              layout === "row" && "shrink-0",
              isActive
                ? layout === "col"
                  ? "bg-[var(--accent)]/15 text-white shadow-[inset_2px_0_0_var(--accent)]"
                  : "bg-[var(--accent)]/15 text-white ring-1 ring-[var(--accent)]/40"
                : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell() {
  const { pathname } = useLocation();
  const title = pageTitle(pathname);

  useEffect(() => {
    document.title = `${title} · CSPM Trust Graph`;
  }, [title]);

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--sidebar)] px-3 py-4 md:flex">
        <div className="mb-6 flex items-center gap-3 px-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--accent)] text-[var(--on-accent)]">
            <Shield className="h-4 w-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <div className="text-[10px] font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">netraom</div>
            <div className="truncate text-sm font-semibold leading-tight">CSPM Trust Graph</div>
          </div>
        </div>
        <div className="mb-2 px-2.5 text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Workspace</div>
        <SideNav layout="col" />
        <div className="mt-auto rounded-lg border border-[var(--border)] bg-[var(--wash)] px-3 py-2.5">
          <div className="text-[10px] font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">Environment</div>
          <div className="mt-1 text-xs text-[var(--foreground)]">Local demo data</div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--background)]/90 backdrop-blur-md">
          <div className="flex h-14 items-center gap-3 px-4 md:px-6">
            <span className="text-sm font-semibold md:hidden">netraom</span>
            <h1 className="min-w-0 flex-1 truncate text-[15px] font-semibold tracking-tight">{title}</h1>
            <div className="ml-auto flex items-center gap-2">
              <ThemeToggle />
              <NotificationBell />
            </div>
          </div>
          <div className="px-3 pb-3 md:hidden">
            <SideNav layout="row" />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-4 py-5 md:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1440px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
