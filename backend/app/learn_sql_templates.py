from __future__ import annotations

from typing import Literal

Level = Literal["beginner", "medium", "advanced"]
Category = Literal["inventory", "cspm", "toxic-combo", "analytics"]

SQL_TEMPLATES: list[dict[str, str]] = [
    {
        "id": "sql_b1_inventory_exposed",
        "title": "B1 — Exposed inventory",
        "description": "Portal-style slice: what Inventory filters on.",
        "level": "beginner",
        "category": "inventory",
        "query": """SELECT display_name, resource_type, cloud, is_internet_exposed, graph_node_id
FROM assets
ORDER BY is_internet_exposed DESC NULLS LAST, display_name
LIMIT 25""",
    },
    {
        "id": "sql_b2_findings_by_source",
        "title": "B2 — Findings by source",
        "description": "CSPM (single-asset rules) vs toxic-combo (graph paths).",
        "level": "beginner",
        "category": "analytics",
        "query": """SELECT source, count(*) AS findings, count(DISTINCT rule_id) AS distinct_rules
FROM findings
GROUP BY source
ORDER BY findings DESC""",
    },
    {
        "id": "sql_b3_critical_cspm",
        "title": "B3 — Critical CSPM",
        "description": "High-severity misconfigurations stored as flat rows.",
        "level": "beginner",
        "category": "cspm",
        "query": """SELECT severity, rule_id, title, canonical_key
FROM findings
WHERE source = 'cspm' AND severity = 'critical'
ORDER BY rule_id
LIMIT 30""",
    },
    {
        "id": "sql_m1_top_cspm_rules",
        "title": "M1 — Top CSPM rules",
        "description": "Which misconfiguration rules fire most after enterprise load.",
        "level": "medium",
        "category": "cspm",
        "query": """SELECT rule_id, count(*) AS cnt, max(severity) AS max_severity
FROM findings
WHERE source = 'cspm'
GROUP BY rule_id
ORDER BY cnt DESC
LIMIT 20""",
    },
    {
        "id": "sql_m2_exposed_by_type",
        "title": "M2 — Exposed assets by type",
        "description": "Attack surface breakdown (API GW, LB, RDS, buckets, compute).",
        "level": "medium",
        "category": "inventory",
        "query": """SELECT resource_type, cloud,
       count(*) AS total,
       sum(CASE WHEN is_internet_exposed THEN 1 ELSE 0 END) AS exposed
FROM assets
GROUP BY resource_type, cloud
HAVING sum(CASE WHEN is_internet_exposed THEN 1 ELSE 0 END) > 0
ORDER BY exposed DESC
LIMIT 25""",
    },
    {
        "id": "sql_m3_apigw_findings",
        "title": "M3 — Public API Gateway (CSPM)",
        "description": "Public API Gateway without auth — rule aws_apigw_public_no_auth.",
        "level": "medium",
        "category": "cspm",
        "query": """SELECT title, severity, canonical_key, exposure
FROM findings
WHERE source = 'cspm' AND rule_id = 'aws_apigw_public_no_auth'
ORDER BY title
LIMIT 20""",
    },
    {
        "id": "sql_m4_toxic_by_severity",
        "title": "M4 — Toxic combos by severity",
        "description": "Graph-derived findings ranked by severity.",
        "level": "medium",
        "category": "toxic-combo",
        "query": """SELECT severity, rule_id, title, canonical_key
FROM findings
WHERE source = 'toxic-combo'
ORDER BY CASE severity
  WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, rule_id
LIMIT 25""",
    },
    {
        "id": "sql_m5_t2_combos",
        "title": "M5 — T2 SSH path combos",
        "description": "Toxic combination pattern T2_internet_ssh_admin_path.",
        "level": "medium",
        "category": "toxic-combo",
        "query": """SELECT fingerprint, title, trust_graph_node_ids, jsonb_array_length(path_edges) AS edge_count
FROM findings
WHERE source = 'toxic-combo' AND rule_id = 'T2_internet_ssh_admin_path'
LIMIT 15""",
    },
    {
        "id": "sql_a1_cspm_on_exposed_assets",
        "title": "A1 — CSPM on internet-exposed assets",
        "description": "Join findings to inventory via canonical_key = graph_node_id.",
        "level": "advanced",
        "category": "cspm",
        "query": """SELECT a.display_name, a.resource_type, a.cloud, f.rule_id, f.severity, f.title
FROM findings f
JOIN assets a ON a.graph_node_id = f.canonical_key AND a.tenant_id = f.tenant_id
WHERE f.source = 'cspm' AND a.is_internet_exposed = true
ORDER BY f.severity, a.resource_type
LIMIT 30""",
    },
    {
        "id": "sql_a2_toxic_path_size",
        "title": "A2 — Largest toxic paths",
        "description": "Combo complexity via JSONB path metadata (bridge to Cypher).",
        "level": "advanced",
        "category": "toxic-combo",
        "query": """SELECT rule_id, title,
       jsonb_array_length(trust_graph_node_ids) AS nodes,
       jsonb_array_length(path_edges) AS edges
FROM findings
WHERE source = 'toxic-combo'
ORDER BY nodes DESC, edges DESC
LIMIT 20""",
    },
    {
        "id": "sql_a3_toxic_rule_rollup",
        "title": "A3 — Toxic pattern rollup",
        "description": "Count matches per T1–T9 pattern id.",
        "level": "advanced",
        "category": "toxic-combo",
        "query": """SELECT rule_id, count(*) AS matches,
       sum(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical
FROM findings
WHERE source = 'toxic-combo'
GROUP BY rule_id
ORDER BY matches DESC""",
    },
    {
        "id": "sql_a4_rds_public",
        "title": "A4 — Public RDS misconfigs",
        "description": "CSPM + inventory correlation for databases.",
        "level": "advanced",
        "category": "cspm",
        "query": """SELECT a.display_name, a.region, f.title, f.severity
FROM findings f
JOIN assets a ON a.graph_node_id = f.canonical_key
WHERE f.source = 'cspm'
  AND f.rule_id = 'aws_rds_public_exposure'
ORDER BY a.region
LIMIT 20""",
    },
    {
        "id": "sql_a5_world_ssh_cspm",
        "title": "A5 — World SSH / RDP (CSPM)",
        "description": "Network misconfigs that enable graph walks to toxic combos.",
        "level": "advanced",
        "category": "cspm",
        "query": """SELECT rule_id, count(*) AS cnt, max(title) AS example_title
FROM findings
WHERE source = 'cspm'
  AND rule_id IN ('aws_sg_world_ssh', 'aws_sg_world_rdp', 'gcp_firewall_world_ssh')
GROUP BY rule_id
ORDER BY cnt DESC""",
    },
    {
        "id": "sql_a6_combo_with_path_edges",
        "title": "A6 — Combos with stored path_edges",
        "description": "Rows ready for UI path overlay (same data Neo4j computed).",
        "level": "advanced",
        "category": "toxic-combo",
        "query": """SELECT fingerprint, rule_id, title,
       trust_graph_node_ids->0 AS first_node,
       path_edges->0 AS first_edge
FROM findings
WHERE source = 'toxic-combo' AND jsonb_array_length(path_edges) > 0
LIMIT 15""",
    },
]
