CREATE TABLE IF NOT EXISTS assets (
    asset_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    graph_node_id TEXT NOT NULL,
    canonical_key TEXT NOT NULL,
    display_name TEXT,
    cloud TEXT,
    resource_type TEXT,
    region TEXT,
    is_internet_exposed BOOLEAN,
    props JSONB NOT NULL DEFAULT '{}',
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, graph_node_id)
);

CREATE INDEX IF NOT EXISTS idx_assets_tenant ON assets (tenant_id);

CREATE TABLE IF NOT EXISTS findings (
    fingerprint TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL,
    ssvc_action TEXT NOT NULL,
    exposure TEXT NOT NULL,
    canonical_key TEXT,
    trust_graph_node_ids JSONB NOT NULL DEFAULT '[]',
    path_edges JSONB NOT NULL DEFAULT '[]',
    risk_score INTEGER NOT NULL DEFAULT 0,
    score_breakdown JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open',
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_tenant_source ON findings (tenant_id, source);
CREATE INDEX IF NOT EXISTS idx_findings_risk_score ON findings (tenant_id, risk_score DESC);
