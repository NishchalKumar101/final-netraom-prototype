import { NavLink } from "react-router-dom";
import clsx from "clsx";

const tabs = [
  { to: "/learn", label: "Overview", end: true },
  { to: "/learn/inventory", label: "Raw → normalized", end: false },
  { to: "/learn/postgres", label: "Postgres lab", end: false },
  { to: "/learn/graph", label: "Graph lab", end: false },
  { to: "/learn/cookbook", label: "Cookbook", end: false },
  { to: "/learn/attack-path", label: "Attack paths", end: false },
];

export function LearnNav() {
  return (
    <nav className="flex flex-wrap gap-1 rounded-xl border border-[var(--border)] bg-[var(--card)] p-1" aria-label="Learn">
      {tabs.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150",
              isActive ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
            )
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
