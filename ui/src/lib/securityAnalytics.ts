import type { Finding, FindingFacets } from "@/lib/api";
import type { AnalystStatus, WorkflowEntry } from "@/lib/analystWorkflow";

export type GeoSite = {
  id: string;
  name: string;
  region: string;
  lat: number;
  lon: number;
};

export const GEO_SITES: GeoSite[] = [
  { id: "iad", name: "N. Virginia", region: "us-east-1", lat: 39.04, lon: -77.49 },
  { id: "pdx", name: "Oregon", region: "us-west-2", lat: 45.52, lon: -122.67 },
  { id: "dub", name: "Ireland", region: "eu-west-1", lat: 53.35, lon: -6.26 },
  { id: "lhr", name: "London", region: "eu-west-2", lat: 51.51, lon: -0.13 },
  { id: "fra", name: "Frankfurt", region: "eu-central-1", lat: 50.11, lon: 8.68 },
  { id: "bom", name: "Mumbai", region: "ap-south-1", lat: 19.08, lon: 72.88 },
  { id: "sin", name: "Singapore", region: "ap-southeast-1", lat: 1.35, lon: 103.82 },
  { id: "nrt", name: "Tokyo", region: "ap-northeast-1", lat: 35.68, lon: 139.69 },
  { id: "syd", name: "Sydney", region: "ap-southeast-2", lat: -33.87, lon: 151.21 },
  { id: "gru", name: "São Paulo", region: "sa-east-1", lat: -23.55, lon: -46.63 },
];

export type MapEvent = {
  id: string;
  simulated: true;
  title: string;
  severity: string;
  category: string;
  sourceSite: GeoSite;
  destSite: GeoSite;
  asset: string;
  timestamp: string;
  fingerprint?: string;
  findingSource?: string;
};

export type RiskItem = {
  id: string;
  fingerprint?: string;
  title: string;
  severity: string;
  entity: string;
  time: string;
  impact: string;
  mitigation: string;
  status: AnalystStatus;
  /** Analyst status is stored in this browser. The API has no resolve workflow. */
  simulatedStatus: true;
  source: string;
  category: string;
  read: boolean;
  dismissed: boolean;
};

export type AnalyticsModel = {
  generatedAtIso: string;
  dataState: "ready" | "empty" | "unavailable";
  history: { sufficient: false; note: string };
  kpis: {
    totalFindings: number | null;
    criticalHigh: number | null;
    attackPaths: number | null;
    vulnerabilities: number | null;
    assets: number | null;
    mitigated: number;
    resolved: number;
    mitigatedNote: string;
  };
  severityBars: { severity: string; label: string; count: number }[];
  categoryDonut: { id: string; label: string; count: number }[];
  trend: { date: string; findings: number; criticalHigh: number; simulated: true }[];
  risks: RiskItem[];
  mapEvents: MapEvent[];
  mapUsesFallback: boolean;
  sampleNote: string | null;
};

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;

let sessionClock: number | null = null;

export function sessionClockMs() {
  if (sessionClock == null) sessionClock = Math.floor(Date.now() / 3_600_000) * 3_600_000;
  return sessionClock;
}

export function fingerprintHash(input: string) {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function siteForRegion(region: string | undefined, salt: number): GeoSite {
  if (region) {
    const normalized = region.toLowerCase();
    const hit = GEO_SITES.find((site) => normalized === site.region || normalized.includes(site.region));
    if (hit) return hit;
  }
  return GEO_SITES[salt % GEO_SITES.length];
}

function otherSite(site: GeoSite, salt: number): GeoSite {
  const index = GEO_SITES.findIndex((item) => item.id === site.id);
  const step = 1 + (salt % (GEO_SITES.length - 1));
  return GEO_SITES[(Math.max(index, 0) + step) % GEO_SITES.length];
}

export function categoryOf(finding: Pick<Finding, "source" | "rule_id">) {
  if (finding.source === "cspm") return "cspm";
  if (finding.source === "toxic-combo") return "toxic-combo";
  const family = finding.rule_id.split(/[_:]/)[0];
  return family || finding.source || "other";
}

export function categoryLabel(id: string) {
  if (id === "cspm") return "CSPM misconfiguration";
  if (id === "toxic-combo") return "Toxic combination";
  return id;
}

function entityOf(finding: Finding) {
  return (
    finding.related_assets?.[0]?.display_name ||
    finding.related_assets?.[0]?.canonical_key ||
    finding.canonical_key ||
    finding.rule_id
  );
}

function impactOf(finding: Finding) {
  if (finding.description) return finding.description;
  const score = finding.score_breakdown;
  if (score) {
    return `Factor score — exposure ${score.exposure}/25, privilege ${score.privilege}/25, exploitability ${score.exploitability}/25, impact ${score.impact}/25.`;
  }
  return "Severity recorded by the demo detection engines. No separate impact narrative is stored.";
}

function mitigationOf(finding: Finding) {
  const blob = `${finding.rule_id} ${finding.title}`.toLowerCase();
  if (blob.includes("ssh")) {
    return "Restrict SSH ingress to known administration networks and review the role on this path. Local guidance only — nothing is changed on a server.";
  }
  if (blob.includes("public") || blob.includes("exposed") || blob.includes("internet")) {
    return "Remove unintended public exposure on the related asset, then reload detections. Local guidance only.";
  }
  if (finding.source === "toxic-combo") {
    return "Break one hop of the combination (exposure, identity grant, or data access) and review the stored path. Local guidance only.";
  }
  return "Review the misconfiguration on the Findings page and tighten the related asset. Local guidance only — this prototype does not apply controls.";
}

function isoFromOffset(clock: number, offsetMs: number) {
  return new Date(clock - offsetMs).toISOString();
}

const FALLBACK_BLUEPRINTS: {
  id: string;
  title: string;
  severity: string;
  category: string;
  sourceRegion: string;
  destRegion: string;
  asset: string;
  impact: string;
  mitigation: string;
}[] = [
  {
    id: "fb-ssh-bucket",
    title: "SSH path to a writable bucket",
    severity: "critical",
    category: "toxic-combo",
    sourceRegion: "us-east-1",
    destRegion: "eu-west-1",
    asset: "upload-bastion",
    impact: "Illustrative internet entry toward writable storage.",
    mitigation: "Close public SSH and drop the write grant. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-public-api",
    title: "Public API without authentication",
    severity: "high",
    category: "cspm",
    sourceRegion: "eu-central-1",
    destRegion: "ap-southeast-1",
    asset: "public-api",
    impact: "Illustrative unauthenticated API edge.",
    mitigation: "Require authentication on the API stage. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-open-rds",
    title: "Internet-facing database",
    severity: "critical",
    category: "cspm",
    sourceRegion: "ap-south-1",
    destRegion: "us-west-2",
    asset: "prod-db",
    impact: "Illustrative datastore reachable from the internet.",
    mitigation: "Remove public ingress to the database. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-admin-role",
    title: "Compute can assume an admin role",
    severity: "high",
    category: "toxic-combo",
    sourceRegion: "eu-west-2",
    destRegion: "us-east-1",
    asset: "platform-admin",
    impact: "Illustrative privilege hop from a workload to an admin role.",
    mitigation: "Remove the assume-role grant. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-open-lb",
    title: "Internet-facing load balancer",
    severity: "medium",
    category: "cspm",
    sourceRegion: "ap-northeast-1",
    destRegion: "sa-east-1",
    asset: "edge-lb",
    impact: "Illustrative public listener.",
    mitigation: "Restrict the listener to intended clients. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-bucket-read",
    title: "Public read on object storage",
    severity: "medium",
    category: "cspm",
    sourceRegion: "ap-southeast-2",
    destRegion: "eu-central-1",
    asset: "public-bucket",
    impact: "Illustrative anonymous read.",
    mitigation: "Block public access on the bucket. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-egress",
    title: "Broad egress from a workload",
    severity: "low",
    category: "cspm",
    sourceRegion: "us-west-2",
    destRegion: "ap-south-1",
    asset: "worker",
    impact: "Illustrative unrestricted egress.",
    mitigation: "Narrow egress to required destinations. Simulated fallback — no finding is loaded.",
  },
  {
    id: "fb-combo-write",
    title: "Exposed host with a write path",
    severity: "high",
    category: "toxic-combo",
    sourceRegion: "sa-east-1",
    destRegion: "ap-southeast-1",
    asset: "internal-worker",
    impact: "Illustrative multi-hop write path.",
    mitigation: "Remove either the exposure or the write edge. Simulated fallback — no finding is loaded.",
  },
];

function fallbackMap(clock: number): MapEvent[] {
  return FALLBACK_BLUEPRINTS.map((item, index) => {
    const sourceSite = siteForRegion(item.sourceRegion, index);
    const destSite = siteForRegion(item.destRegion, index + 3);
    return {
      id: item.id,
      simulated: true,
      title: item.title,
      severity: item.severity,
      category: item.category,
      sourceSite,
      destSite: destSite.id === sourceSite.id ? otherSite(sourceSite, index + 1) : destSite,
      asset: item.asset,
      timestamp: isoFromOffset(clock, (index + 1) * 45 * 60 * 1000),
      findingSource: item.category,
    };
  });
}

function fallbackRisks(clock: number, workflow: Record<string, WorkflowEntry>): RiskItem[] {
  return FALLBACK_BLUEPRINTS.map((item, index) => {
    const stored = workflow[item.id];
    return {
      id: item.id,
      title: item.title,
      severity: item.severity,
      entity: item.asset,
      time: isoFromOffset(clock, (index + 1) * 45 * 60 * 1000),
      impact: item.impact,
      mitigation: item.mitigation,
      status: stored?.status ?? "New",
      simulatedStatus: true,
      source: item.category,
      category: item.category,
      read: stored?.read ?? false,
      dismissed: stored?.dismissed ?? false,
    };
  });
}

function distribute(total: number, days: number, salt: string) {
  if (total <= 0) return Array.from({ length: days }, () => 0);
  const weights = Array.from({ length: days }, (_, index) => 1 + (fingerprintHash(`${salt}:${index}`) % 7));
  const weightSum = weights.reduce((sum, weight) => sum + weight, 0);
  const counts = weights.map((weight) => Math.floor((total * weight) / weightSum));
  let remainder = total - counts.reduce((sum, count) => sum + count, 0);
  for (let index = days - 1; remainder > 0; index -= 1) {
    counts[index] += 1;
    remainder -= 1;
  }
  return counts;
}

function trendSeries(clock: number, findings: number, criticalHigh: number) {
  const dates = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(clock - (6 - index) * 86_400_000);
    return day.toISOString().slice(0, 10);
  });
  const findingCounts = distribute(findings, 7, `findings:${findings}`);
  const criticalCounts = distribute(criticalHigh, 7, `critical:${criticalHigh}`);
  return dates.map((date, index) => ({
    date,
    findings: findingCounts[index] ?? 0,
    criticalHigh: Math.min(findingCounts[index] ?? 0, criticalCounts[index] ?? 0),
    simulated: true as const,
  }));
}

function eventFromFinding(finding: Finding, clock: number): MapEvent {
  const hash = fingerprintHash(finding.fingerprint);
  const region = finding.related_assets?.find((asset) => asset.region)?.region;
  const sourceSite = siteForRegion(region, hash);
  const destSite = otherSite(sourceSite, hash >>> 3);
  return {
    id: finding.fingerprint,
    simulated: true,
    title: finding.title,
    severity: finding.severity,
    category: categoryOf(finding),
    sourceSite,
    destSite,
    asset: entityOf(finding),
    timestamp: isoFromOffset(clock, (hash % (6 * 60)) * 60 * 1000),
    fingerprint: finding.fingerprint,
    findingSource: finding.source,
  };
}

function riskFromFinding(finding: Finding, clock: number, workflow: Record<string, WorkflowEntry>): RiskItem {
  const stored = workflow[finding.fingerprint];
  const hash = fingerprintHash(finding.fingerprint);
  return {
    id: finding.fingerprint,
    fingerprint: finding.fingerprint,
    title: finding.title,
    severity: finding.severity,
    entity: entityOf(finding),
    time: isoFromOffset(clock, (hash % (6 * 60)) * 60 * 1000),
    impact: impactOf(finding),
    mitigation: mitigationOf(finding),
    status: stored?.status ?? "New",
    simulatedStatus: true,
    source: finding.source,
    category: categoryOf(finding),
    read: stored?.read ?? false,
    dismissed: stored?.dismissed ?? false,
  };
}

const HISTORY_NOTE =
  "Findings in this prototype have no detection timestamps, so there is insufficient history for a real 7-day trend. The series below is a deterministic simulation whose daily counts sum to the current totals. It does not drift randomly and it is not live telemetry.";

export function buildSecurityAnalytics(input: {
  dataState: "ready" | "empty" | "unavailable";
  findings: Finding[];
  findingsTotal: number;
  facets: FindingFacets | null;
  cspmTotal: number | null;
  comboTotal: number | null;
  assetTotal: number | null;
  workflow: Record<string, WorkflowEntry>;
}): AnalyticsModel {
  const clock = sessionClockMs();
  const generatedAtIso = new Date(clock).toISOString();

  if (input.dataState !== "ready") {
    const risks = input.dataState === "empty" ? [] : fallbackRisks(clock, input.workflow);
    const mitigated = risks.filter((risk) => risk.status === "Mitigated").length;
    const resolved = risks.filter((risk) => risk.status === "Resolved").length;
    return {
      generatedAtIso,
      dataState: input.dataState,
      history: {
        sufficient: false,
        note:
          input.dataState === "unavailable"
            ? "The demo API is unavailable, so KPI counts cannot be read. The map and risk list below are the shared simulated fallback, not loaded findings."
            : "No findings are loaded. Charts stay at zero. The map can show the shared simulated fallback.",
      },
      kpis: {
        totalFindings: input.dataState === "empty" ? 0 : null,
        criticalHigh: input.dataState === "empty" ? 0 : null,
        attackPaths: input.dataState === "empty" ? 0 : null,
        vulnerabilities: input.dataState === "empty" ? 0 : null,
        assets: input.dataState === "empty" ? input.assetTotal ?? 0 : input.assetTotal,
        mitigated,
        resolved,
        mitigatedNote:
          "Mitigated and resolved counts are an analyst workflow in this browser. The API does not store finding status.",
      },
      severityBars: SEVERITY_ORDER.map((severity) => ({
        severity,
        label: severity,
        count: 0,
      })),
      categoryDonut: [
        { id: "cspm", label: categoryLabel("cspm"), count: input.dataState === "empty" ? 0 : 0 },
        { id: "toxic-combo", label: categoryLabel("toxic-combo"), count: 0 },
      ],
      trend: trendSeries(clock, 0, 0),
      risks,
      mapEvents: fallbackMap(clock),
      mapUsesFallback: true,
      sampleNote: null,
    };
  }

  const bySeverity = input.facets?.by_severity ?? {};
  const criticalHigh = (bySeverity.critical ?? 0) + (bySeverity.high ?? 0);
  const totalFindings = input.facets?.total ?? input.findingsTotal;
  const ranked = [...input.findings].sort((a, b) => {
    const sa = SEVERITY_ORDER.indexOf(a.severity as (typeof SEVERITY_ORDER)[number]);
    const sb = SEVERITY_ORDER.indexOf(b.severity as (typeof SEVERITY_ORDER)[number]);
    return (sa === -1 ? 99 : sa) - (sb === -1 ? 99 : sb);
  });
  const risks = ranked.slice(0, 24).map((finding) => riskFromFinding(finding, clock, input.workflow));
  const known = new Set<string>(SEVERITY_ORDER);
  const extras = Object.keys(bySeverity).filter((key) => !known.has(key) && (bySeverity[key] ?? 0) > 0);

  return {
    generatedAtIso,
    dataState: "ready",
    history: { sufficient: false, note: HISTORY_NOTE },
    kpis: {
      totalFindings,
      criticalHigh,
      attackPaths: input.comboTotal,
      vulnerabilities: input.cspmTotal,
      assets: input.assetTotal,
      mitigated: risks.filter((risk) => risk.status === "Mitigated").length,
      resolved: risks.filter((risk) => risk.status === "Resolved").length,
      mitigatedNote:
        "Mitigated and resolved counts only include the risk list on this page (top findings by severity). Status is an analyst workflow in this browser, not a server-verified state.",
    },
    severityBars: [
      ...SEVERITY_ORDER.map((severity) => ({
        severity,
        label: severity,
        count: bySeverity[severity] ?? 0,
      })),
      ...extras.map((severity) => ({ severity, label: severity, count: bySeverity[severity] ?? 0 })),
    ],
    categoryDonut: [
      { id: "cspm", label: categoryLabel("cspm"), count: input.cspmTotal ?? 0 },
      { id: "toxic-combo", label: categoryLabel("toxic-combo"), count: input.comboTotal ?? 0 },
    ],
    trend: trendSeries(clock, totalFindings, criticalHigh),
    risks,
    mapEvents: ranked.slice(0, 12).map((finding) => eventFromFinding(finding, clock)),
    mapUsesFallback: false,
    sampleNote:
      input.findingsTotal > input.findings.length
        ? `Risk list and map use the first ${Math.min(24, input.findings.length)} findings by severity (${input.findings.length} loaded of ${input.findingsTotal}). KPI totals use facet counts.`
        : null,
  };
}

export function findingHref(item: { fingerprint?: string; source?: string; category?: string }) {
  const source = item.source === "cspm" || item.source === "toxic-combo" ? item.source : item.category;
  const tab = source === "cspm" || source === "toxic-combo" ? source : "toxic-combo";
  const params = new URLSearchParams({ tab });
  if (item.fingerprint) params.set("fp", item.fingerprint);
  return `/findings?${params.toString()}`;
}
