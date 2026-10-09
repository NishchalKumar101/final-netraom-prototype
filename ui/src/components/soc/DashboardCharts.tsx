import { useNavigate } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { AnalyticsModel } from "@/lib/securityAnalytics";

const tooltipStyle = {
  background: "var(--tooltip-bg)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--foreground)",
  fontSize: 12,
};

const SEVERITY_FILL: Record<string, string> = {
  critical: "var(--critical)",
  high: "var(--high)",
  medium: "var(--warning)",
  low: "var(--muted)",
  info: "var(--info)",
};

export function DashboardCharts({ model }: { model: AnalyticsModel }) {
  const navigate = useNavigate();
  const categoryTotal = model.categoryDonut.reduce((sum, row) => sum + row.count, 0);

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <figure className="min-w-0">
        <figcaption className="mb-2 text-xs text-[var(--muted)]">
          Category. Select a slice to open that Findings tab.
        </figcaption>
        <div className="h-64">
          {categoryTotal === 0 ? (
            <p className="text-sm text-[var(--muted)]">No category counts yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={model.categoryDonut}
                  dataKey="count"
                  nameKey="label"
                  innerRadius={52}
                  outerRadius={78}
                  paddingAngle={2}
                  onClick={(slice) => {
                    const id = String((slice as { id?: string }).id ?? "");
                    if (id === "cspm" || id === "toxic-combo") navigate(`/findings?tab=${id}`);
                  }}
                >
                  {model.categoryDonut.map((row) => (
                    <Cell key={row.id} fill={row.id === "cspm" ? "var(--accent)" : "var(--critical)"} cursor="pointer" />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </figure>

      <figure className="min-w-0">
        <figcaption className="mb-2 text-xs text-[var(--muted)]">
          Severity across all findings. A bar opens the toxic-combination tab at that severity.
        </figcaption>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={model.severityBars} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar
                dataKey="count"
                name="Findings"
                radius={[4, 4, 0, 0]}
                onClick={(row) => {
                  const severity = String((row as { severity?: string }).severity ?? "");
                  if (severity) navigate(`/findings?tab=toxic-combo&severity=${encodeURIComponent(severity)}`);
                }}
              >
                {model.severityBars.map((row) => (
                  <Cell key={row.severity} fill={SEVERITY_FILL[row.severity] ?? "var(--info)"} cursor="pointer" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>

      <figure className="min-w-0">
        <figcaption className="mb-2 text-xs text-[var(--muted)]">
          Simulated 7-day series. Findings have no timestamps — daily values sum to current totals.
        </figcaption>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={model.trend} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "var(--muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Area type="monotone" dataKey="findings" name="Findings (simulated)" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.2} />
              <Area type="monotone" dataKey="criticalHigh" name="Critical + high (simulated)" stroke="var(--critical)" fill="var(--critical)" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </div>
  );
}
