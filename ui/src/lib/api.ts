const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type NormalizedAssetPreview = {
  schema_version?: string;
  kind?: string;
  node_id?: string;
  name?: string;
  source_modules?: string[];
  graph_props?: Record<string, unknown>;
  highlights?: Record<string, unknown>;
  edge_count?: number;
  sample_edges?: { kind?: string; src_id?: string; dst_id?: string; props?: Record<string, unknown> }[];
};

export type Asset = {
  asset_id: string;
  graph_node_id: string;
  canonical_key: string;
  display_name?: string;
  cloud?: string;
  resource_type?: string;
  region?: string;
  is_internet_exposed?: boolean | null;
  props?: Record<string, unknown>;
  normalized?: NormalizedAssetPreview;
};

export type AssetFacets = {
  total: number;
  internet_exposed: number;
  by_cloud: Record<string, number>;
  by_resource_type: Record<string, number>;
  by_category: Record<string, number>;
  categories: { id: string; label: string }[];
};

export type Finding = {
  fingerprint: string;
  source: string;
  rule_id: string;
  title: string;
  description?: string;
  severity: string;
  risk_score?: number;
  score_breakdown?: {
    exposure: number;
    privilege: number;
    exploitability: number;
    impact: number;
    final_score: number;
    severity: string;
  };
  canonical_key?: string;
  trust_graph_node_ids?: string[];
  path_edges?: GraphEdge[];
  attack_path_nodes?: string[];
  attack_path_edge_ids?: string[];
  related_assets?: Asset[];
};

export type FindingFacets = {
  total: number;
  by_severity: Record<string, number>;
  top_rules: { rule_id: string; count: number }[];
};

export type GraphNode = {
  node_id: string;
  kind?: string;
  name?: string;
  cloud?: string;
  resource_type?: string;
  props?: Record<string, unknown>;
};

export type GraphEdge = {
  edge_id: string;
  kind?: string;
  src_id: string;
  dst_id: string;
  props?: Record<string, unknown>;
};

export type LoadResult = {
  assets: number;
  misconfig_findings: number;
  combo_findings: number;
  nodes: number;
  edges: number;
};

export type DemoFixture = "aws" | "gcp" | "both" | "enterprise";

export type AssetSort = "name" | "type" | "cloud" | "region" | "exposed";
export type FindingSort = "severity" | "title" | "rule" | "risk_score";
export type SortOrder = "asc" | "desc";

export function loadDemo(fixture: DemoFixture) {
  return request<LoadResult>("/demo/load", {
    method: "POST",
    body: JSON.stringify({ fixture }),
  });
}

export function resetDemo() {
  return request("/demo/reset", { method: "POST" });
}

export function getAssetFacets() {
  return request<AssetFacets>("/assets/facets");
}

export function getAssets(params?: {
  limit?: number;
  offset?: number;
  q?: string;
  cloud?: string;
  category?: string;
  resource_type?: string;
  internet_exposed?: boolean;
  sort?: AssetSort;
  order?: SortOrder;
}) {
  return request<Paginated<Asset>>(
    `/assets${qs({
      limit: params?.limit,
      offset: params?.offset,
      q: params?.q,
      cloud: params?.cloud,
      category: params?.category && params.category !== "all" ? params.category : undefined,
      resource_type: params?.resource_type,
      internet_exposed: params?.internet_exposed,
      sort: params?.sort,
      order: params?.order,
    })}`,
  );
}

export function getAsset(id: string) {
  return request<Asset>(`/assets/${id}`);
}

export type AssetJsonPackage = {
  portal_asset: Record<string, unknown>;
  normalized: Record<string, unknown> | null;
  neo4j_node: Record<string, unknown> | null;
  raw_collector: Record<string, unknown> | null;
  note: string | null;
};

export function getAssetJson(assetId: string) {
  return request<AssetJsonPackage>(`/assets/${encodeURIComponent(assetId)}/json`);
}

export function getAssetByGraphNode(graphNodeId: string) {
  return request<Asset>(`/assets/by-node/${encodeURIComponent(graphNodeId)}`);
}

export function getNeighborhood(nodeId: string, depth = 2) {
  return request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
    `/graph/nodes/${encodeURIComponent(nodeId)}/neighborhood?depth=${depth}`,
  );
}

export function getFindingFacets(source?: string) {
  return request<FindingFacets>(`/findings/facets${qs({ source })}`);
}

export function getFindings(params?: {
  source?: string;
  limit?: number;
  offset?: number;
  q?: string;
  severity?: string;
  rule_id?: string;
  sort?: FindingSort;
  order?: SortOrder;
}) {
  return request<Paginated<Finding>>(
    `/findings${qs({
      source: params?.source,
      limit: params?.limit,
      offset: params?.offset,
      q: params?.q,
      severity: params?.severity && params.severity !== "all" ? params.severity : undefined,
      rule_id: params?.rule_id,
      sort: params?.sort,
      order: params?.order,
    })}`,
  );
}

export type FindingPath = {
  fingerprint: string;
  title?: string;
  description?: string;
  source?: string;
  rule_id?: string;
  severity?: string;
  risk_score?: number;
  score_breakdown?: Finding["score_breakdown"];
  node_ids: string[];
  edges: GraphEdge[];
  nodes: GraphNode[];
  related_assets: Asset[];
  attack_path_nodes: string[];
  attack_path_edge_ids: string[];
  attack_path_edges: GraphEdge[];
};

export function getFindingPath(fingerprint: string) {
  return request<FindingPath>(`/findings/${encodeURIComponent(fingerprint)}/path`);
}

export function assetRouteId(asset: Asset) {
  return asset.asset_id;
}

export type LearnStats = {
  tenant_id: string;
  postgres: {
    assets: number;
    findings: number;
    findings_cspm: number;
    findings_toxic_combo: number;
  };
  neo4j: {
    node_count: number;
    edge_count: number;
    nodes_by_kind: Record<string, number>;
    edges_by_kind: Record<string, number>;
  };
};

export type PostgresSchemaTable = {
  name: string;
  purpose: string;
  columns: { name: string; type: string; nullable: boolean; primary_key: boolean }[];
};

export type SqlLabResult = {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  sql_executed: string;
};

export type LabQueryTemplate = {
  id: string;
  title: string;
  description: string;
  query: string;
  level?: "beginner" | "medium" | "advanced";
  category?: string;
};

export type CypherTemplate = LabQueryTemplate;

export type CypherLabResult = {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  cypher_executed: string;
};

export function getLearnStats() {
  return request<LearnStats>("/learn/stats");
}

export type InventoryFixtureId = "aws" | "gcp" | "both" | "enterprise";

export type PipelineStage = { stage: string; title: string; detail: string };

export type InventoryFixtureMeta = {
  id: string;
  label: string;
  normalized_file: string | null;
  raw_file: string | null;
  load_fixture_key: string;
};

export type InventoryBundle = {
  fixture_id: Exclude<InventoryFixtureId, "both">;
  label: string;
  load_fixture_key: string;
  pipeline: PipelineStage[];
  raw?: Record<string, unknown>;
  normalized?: Record<string, unknown>;
};

export type InventoryBothPayload = {
  fixture_id: "both";
  label: string;
  load_fixture_key: string;
  pipeline: PipelineStage[];
  clouds: InventoryBundle[];
};

export function getInventoryFixtures() {
  return request<{ fixtures: InventoryFixtureMeta[]; pipeline: PipelineStage[] }>(
    "/learn/inventory/fixtures",
  );
}

export function getInventoryPayload(fixture: InventoryFixtureId, previewLimit = 25) {
  return request<InventoryBundle | InventoryBothPayload>(
    `/learn/inventory${qs({ fixture, preview_limit: previewLimit })}`,
  );
}

export function getPostgresSchema() {
  return request<{ tables: PostgresSchemaTable[] }>("/learn/postgres/schema");
}

export function getPostgresSample(table: "assets" | "findings", limit = 10) {
  return request<{ table: string; limit: number; rows: Record<string, unknown>[] }>(
    `/learn/postgres/sample${qs({ table, limit })}`,
  );
}

export function runSqlLab(sql: string) {
  return request<SqlLabResult>("/learn/sql", { method: "POST", body: JSON.stringify({ sql }) });
}

export function getSqlTemplates() {
  return request<{ templates: LabQueryTemplate[] }>("/learn/sql/templates");
}

export function getCypherTemplates() {
  return request<{ templates: CypherTemplate[]; tenant_id: string }>("/learn/cypher/templates");
}

export function runCypherLab(cypher: string) {
  return request<CypherLabResult>("/learn/cypher", { method: "POST", body: JSON.stringify({ cypher }) });
}
