import { useEffect, useId, useMemo, useState } from "react";

import { Button } from "@/components/Button";
import { categoryLabel, type MapEvent } from "@/lib/securityAnalytics";

const WIDTH = 960;
const HEIGHT = 480;

const LAND: [number, number][][] = [
  [
    [-168, 66], [-156, 71], [-140, 70], [-128, 70], [-105, 73], [-88, 74], [-70, 68], [-64, 60], [-56, 53],
    [-64, 47], [-70, 42], [-74, 40], [-80, 32], [-82, 25], [-90, 29], [-97, 26], [-106, 22], [-110, 24],
    [-114, 27], [-117, 32], [-124, 40], [-124, 49], [-130, 55], [-136, 57], [-153, 59], [-166, 54], [-168, 66],
  ],
  [
    [-81, 12], [-77, 8], [-71, 12], [-62, 8], [-50, 0], [-35, -6], [-35, -16], [-40, -22], [-48, -28],
    [-62, -40], [-68, -52], [-74, -52], [-72, -40], [-74, -22], [-70, -16], [-78, -2], [-80, 8], [-81, 12],
  ],
  [
    [-10, 36], [-9, 43], [-2, 48], [2, 51], [8, 54], [12, 56], [16, 69], [24, 71], [28, 70], [30, 60],
    [24, 52], [18, 48], [16, 42], [12, 38], [3, 36], [-5, 36], [-10, 36],
  ],
  [
    [-17, 15], [-16, 21], [-10, 32], [-6, 35], [10, 37], [11, 32], [25, 32], [32, 31], [43, 12], [51, 12],
    [51, 0], [42, -2], [40, -15], [35, -26], [32, -29], [19, -35], [18, -32], [12, -18], [13, -8], [9, 4],
    [-5, 5], [-10, 6], [-17, 15],
  ],
  [
    [26, 40], [28, 42], [36, 45], [40, 47], [48, 42], [60, 45], [72, 45], [80, 50], [90, 50], [110, 55],
    [130, 55], [140, 60], [160, 66], [180, 66], [180, 60], [160, 55], [142, 45], [140, 35], [128, 34],
    [122, 30], [120, 22], [108, 14], [104, 2], [98, 8], [80, 6], [78, 16], [72, 20], [70, 24], [60, 25],
    [56, 27], [44, 12], [43, 16], [36, 22], [32, 30], [34, 36], [26, 40],
  ],
  [
    [114, -22], [122, -18], [128, -14], [136, -12], [146, -18], [153, -26], [150, -36], [140, -38],
    [128, -32], [116, -35], [114, -28], [114, -22],
  ],
];

function project(lon: number, lat: number) {
  return { x: ((lon + 180) / 360) * WIDTH, y: ((90 - lat) / 180) * HEIGHT };
}

function landPath(ring: [number, number][]) {
  return ring
    .map((point, index) => {
      const { x, y } = project(point[0], point[1]);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ") + " Z";
}

function control(a: { x: number; y: number }, b: { x: number; y: number }) {
  const midX = (a.x + b.x) / 2;
  const midY = (a.y + b.y) / 2;
  const lift = Math.min(90, Math.hypot(b.x - a.x, b.y - a.y) * 0.28);
  return { x: midX, y: Math.max(24, midY - lift) };
}

function quadPoint(
  a: { x: number; y: number },
  c: { x: number; y: number },
  b: { x: number; y: number },
  t: number,
) {
  const u = 1 - t;
  return {
    x: u * u * a.x + 2 * u * t * c.x + t * t * b.x,
    y: u * u * a.y + 2 * u * t * c.y + t * t * b.y,
  };
}

function severityStroke(severity: string) {
  if (severity === "critical") return "var(--critical)";
  if (severity === "high") return "var(--high)";
  if (severity === "medium") return "var(--warning)";
  return "var(--live)";
}

export function ThreatMap({
  events,
  fallback,
}: {
  events: MapEvent[];
  fallback: boolean;
}) {
  const markerId = useId().replace(/:/g, "");
  const [paused, setPaused] = useState(false);
  const [severity, setSeverity] = useState("all");
  const [category, setCategory] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (paused || reduced) return;
    const id = window.setInterval(() => setTick((value) => (value + 1) % 120), 90);
    return () => window.clearInterval(id);
  }, [paused, reduced]);

  const severities = useMemo(() => ["all", ...new Set(events.map((event) => event.severity))], [events]);
  const categories = useMemo(() => ["all", ...new Set(events.map((event) => event.category))], [events]);
  const visible = events.filter(
    (event) => (severity === "all" || event.severity === severity) && (category === "all" || event.category === category),
  );
  const selected = visible.find((event) => event.id === selectedId) ?? null;

  const geometry = visible.map((event, index) => {
    const source = project(event.sourceSite.lon, event.sourceSite.lat);
    const dest = project(event.destSite.lon, event.destSite.lat);
    const bend = control(source, dest);
    const t = ((tick + index * 11) % 120) / 120;
    return { event, source, dest, bend, marker: quadPoint(source, bend, dest, reduced || paused ? 0.45 : t) };
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>
          {paused ? "Resume" : "Pause"}
        </Button>
        <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
          Severity
          <select
            className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm text-[var(--foreground)]"
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          >
            {severities.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
          Category
          <select
            className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm text-[var(--foreground)]"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "all" : categoryLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-[var(--muted)]">
          {fallback ? "Simulated fallback dataset — no findings loaded." : "Simulated telemetry derived from loaded findings."}
        </p>
      </div>

      <div className="flex flex-wrap gap-2 text-[11px] text-[var(--muted)]" aria-hidden>
        {[
          ["critical", "var(--critical)"],
          ["high", "var(--high)"],
          ["medium", "var(--warning)"],
          ["low", "var(--live)"],
        ].map(([label, color]) => (
          <span key={label} className="inline-flex items-center gap-1.5 rounded-md bg-[var(--inset)] px-2 py-1 ring-1 ring-[var(--ring-soft)]">
            <span className="h-2 w-2 rounded-full" style={{ background: color }} />
            {label}
          </span>
        ))}
        <span className="rounded-md bg-[var(--inset)] px-2 py-1 ring-1 ring-[var(--ring-soft)]">Arc = simulated path · left to right is not flow direction</span>
      </div>

      <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--canvas)]">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full" role="img" aria-label="Simulated global threat map">
          <defs>
            <pattern id={`${markerId}-grid`} width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M40 0 H0 V40" fill="none" stroke="var(--grid-line)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="var(--canvas)" />
          <rect width={WIDTH} height={HEIGHT} fill={`url(#${markerId}-grid)`} />
          {LAND.map((ring, index) => (
            <path key={index} d={landPath(ring)} fill="color-mix(in srgb, var(--accent) 18%, var(--inset))" stroke="var(--border-strong)" strokeWidth="1" />
          ))}
          {geometry.map(({ event, source, dest, bend }) => {
            const active = event.id === selectedId;
            return (
              <path
                key={`${event.id}-path`}
                d={`M${source.x} ${source.y} Q${bend.x} ${bend.y} ${dest.x} ${dest.y}`}
                fill="none"
                stroke={severityStroke(event.severity)}
                strokeWidth={active ? 2.6 : 1.4}
                className={paused || reduced ? undefined : "threat-dash"}
                opacity={active ? 1 : 0.75}
                onClick={() => setSelectedId(event.id)}
                style={{ cursor: "pointer" }}
              >
                <title>
                  {event.title}: {event.sourceSite.name} to {event.destSite.name}
                </title>
              </path>
            );
          })}
          {geometry.map(({ event, source, dest, marker }) => (
            <g key={`${event.id}-nodes`}>
              <circle cx={source.x} cy={source.y} r="7" fill="none" stroke={severityStroke(event.severity)} className={paused || reduced ? undefined : "threat-pulse"} />
              <circle
                cx={source.x}
                cy={source.y}
                r="3.5"
                fill={severityStroke(event.severity)}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(event.id)}
              >
                <title>{event.sourceSite.name}</title>
              </circle>
              <circle
                cx={dest.x}
                cy={dest.y}
                r="3.5"
                fill={severityStroke(event.severity)}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(event.id)}
              >
                <title>{event.destSite.name}</title>
              </circle>
              <circle cx={marker.x} cy={marker.y} r="3" fill="var(--foreground)" opacity="0.9" />
            </g>
          ))}
        </svg>
      </div>

      {visible.length === 0 ? <p className="text-sm text-[var(--muted)]">No simulated paths match these filters.</p> : null}

      {selected ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--inset)] p-3 text-sm" role="status">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{selected.title}</span>
            <span className="rounded-full bg-[var(--wash-strong)] px-2 py-0.5 text-xs capitalize">{selected.severity}</span>
            <span className="text-xs text-[var(--muted)]">Simulated</span>
          </div>
          <dl className="mt-2 grid gap-1 text-xs text-[var(--muted)] sm:grid-cols-2">
            <div>Source: {selected.sourceSite.name} ({selected.sourceSite.region})</div>
            <div>Destination: {selected.destSite.name} ({selected.destSite.region})</div>
            <div>Category: {categoryLabel(selected.category)}</div>
            <div>Asset: {selected.asset}</div>
            <div className="sm:col-span-2">Timestamp: {selected.timestamp} (simulated)</div>
          </dl>
        </div>
      ) : (
        <p className="text-xs text-[var(--muted)]">Select a path or endpoint for source, destination, category, severity, and time.</p>
      )}
    </div>
  );
}
