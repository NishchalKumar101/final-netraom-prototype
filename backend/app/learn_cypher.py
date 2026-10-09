from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.config import DEMO_TENANT_ID
from app.neo4j_client import Neo4jClient

FORBIDDEN_CYPHER = re.compile(
    r"\b(create|merge|delete|detach|set|remove|drop|call\s+\{?\s*dbms)\b",
    re.IGNORECASE,
)

TENANT = str(DEMO_TENANT_ID)

CYPHER_TEMPLATES: list[dict[str, str]] = [
    # --- Beginner ---
    {
        "id": "cy_b1_counts_by_kind",
        "title": "B1 — Node counts by kind",
        "description": "Graph inventory shape after load.",
        "level": "beginner",
        "category": "analytics",
        "query": f"""
MATCH (n:TrustGraphNode {{tenant_id: '{TENANT}'}})
RETURN n.kind AS kind, count(*) AS c
ORDER BY c DESC
LIMIT 20
""".strip(),
    },
    {
        "id": "cy_b2_edge_counts",
        "title": "B2 — Edge counts by kind",
        "description": "Trust relationships (can_write, allows_ingress, …).",
        "level": "beginner",
        "category": "analytics",
        "query": f"""
MATCH (:TrustGraphNode {{tenant_id: '{TENANT}'}})-[r:TRUST_EDGE]->()
RETURN r.kind AS edge_kind, count(*) AS c
ORDER BY c DESC
LIMIT 20
""".strip(),
    },
    {
        "id": "lab1_public_resources",
        "title": "B3 — Public resources",
        "description": "Resources with is_public / exposure in props.",
        "level": "beginner",
        "category": "cspm",
        "query": f"""
MATCH (n:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'resource'}})
WHERE n.props CONTAINS 'is_public' OR n.props CONTAINS 'is_internet_exposed'
RETURN n.name AS name, n.resource_type AS type, n.props AS props
LIMIT 25
""".strip(),
    },
    {
        "id": "lab2_world_ssh",
        "title": "B4 — World SSH ingress",
        "description": "Security groups / firewalls allowing port 22 from the internet.",
        "level": "beginner",
        "category": "cspm",
        "query": f"""
MATCH (sg:TrustGraphNode {{tenant_id: '{TENANT}'}})-[r:TRUST_EDGE]->(w)
WHERE r.kind = 'allows_ingress' AND r.props CONTAINS '22'
RETURN sg.name AS control, w.name AS destination, r.props AS ingress
LIMIT 25
""".strip(),
    },
    # --- Medium CSPM ---
    {
        "id": "lab4_apigw",
        "title": "M1 — Public API Gateway (no auth)",
        "description": "APIs with authorization NONE in props.",
        "level": "medium",
        "category": "cspm",
        "query": f"""
MATCH (api:TrustGraphNode {{tenant_id: '{TENANT}', resource_type: 'apigateway_rest_api'}})
WHERE api.props CONTAINS 'NONE'
RETURN api.name AS api, api.props AS props
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_m2_public_rds",
        "title": "M2 — Public RDS nodes",
        "description": "Database resources flagged publicly accessible.",
        "level": "medium",
        "category": "cspm",
        "query": f"""
MATCH (db:TrustGraphNode {{tenant_id: '{TENANT}'}})
WHERE db.resource_type CONTAINS 'rds' AND db.props CONTAINS 'public'
RETURN db.name AS db, db.region AS region, db.props AS props
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_m3_internet_lb",
        "title": "M3 — Internet-facing load balancers",
        "description": "ALB/NLB-style resources with public exposure props.",
        "level": "medium",
        "category": "cspm",
        "query": f"""
MATCH (lb:TrustGraphNode {{tenant_id: '{TENANT}'}})
WHERE (lb.resource_type CONTAINS 'load_balancer' OR lb.resource_type CONTAINS 'elb')
  AND (lb.props CONTAINS 'internet' OR lb.props CONTAINS 'is_public')
RETURN lb.name AS lb, lb.resource_type AS type, lb.props AS props
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_m4_can_write_public",
        "title": "M4 — Identities that can_write storage",
        "description": "IAM/SA paths toward buckets (precursor to T1/T2).",
        "level": "medium",
        "category": "cspm",
        "query": f"""
MATCH (id:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'identity'}})
      -[w:TRUST_EDGE {{kind: 'can_write'}}]->(b:TrustGraphNode {{kind: 'resource'}})
WHERE b.resource_type IN ['s3_bucket', 'gcs_bucket']
RETURN id.name AS identity, b.name AS bucket, w.props AS edge_props
LIMIT 20
""".strip(),
    },
    {
        "id": "cy_m5_world_rdp",
        "title": "M5 — World RDP (3389)",
        "description": "Remote desktop exposure from 0.0.0.0/0.",
        "level": "medium",
        "category": "cspm",
        "query": f"""
MATCH (sg:TrustGraphNode {{tenant_id: '{TENANT}'}})-[r:TRUST_EDGE]->()
WHERE r.kind = 'allows_ingress' AND r.props CONTAINS '3389'
RETURN sg.name AS control, r.props AS ingress
LIMIT 15
""".strip(),
    },
    # --- Medium toxic ---
    {
        "id": "lab3_t2_path",
        "title": "M6 — T2 SSH → writable bucket",
        "description": "Toxic combo T2_internet_ssh_admin_path shape.",
        "level": "medium",
        "category": "toxic-combo",
        "query": f"""
MATCH (sg:TrustGraphNode {{tenant_id: '{TENANT}'}})-[i:TRUST_EDGE]->()
WHERE i.kind = 'allows_ingress' AND i.props CONTAINS '22'
MATCH (vm:TrustGraphNode {{tenant_id: '{TENANT}'}})-[:TRUST_EDGE {{kind: 'has_sg'}}]->(sg)
MATCH (role:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'identity'}})
      -[:TRUST_EDGE {{kind: 'attached_to'}}]->(vm)
MATCH (role)-[:TRUST_EDGE {{kind: 'can_write'}}]->(bucket:TrustGraphNode {{kind: 'resource'}})
WHERE bucket.props CONTAINS 'is_public' OR bucket.props CONTAINS 'is_critical_data'
RETURN vm.name AS vm, role.name AS role, bucket.name AS bucket
LIMIT 10
""".strip(),
    },
    {
        "id": "cy_m7_t1_public_writable",
        "title": "M7 — T1 public writable storage",
        "description": "Public bucket/object store with write-capable identity.",
        "level": "medium",
        "category": "toxic-combo",
        "query": f"""
MATCH (b:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'resource'}})
WHERE (b.props CONTAINS 'is_public' OR b.props CONTAINS 'anonymous')
MATCH (id:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'identity'}})
      -[:TRUST_EDGE {{kind: 'can_write'}}]->(b)
RETURN b.name AS storage, id.name AS identity, b.resource_type AS type
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_m8_t9_admin_internet",
        "title": "M8 — T9 admin on internet compute",
        "description": "Admin-privilege identity on internet-exposed VM.",
        "level": "medium",
        "category": "toxic-combo",
        "query": f"""
MATCH (vm:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'resource'}})
WHERE vm.props CONTAINS 'is_internet_exposed' OR vm.props CONTAINS 'is_public'
MATCH (id:TrustGraphNode {{tenant_id: '{TENANT}', kind: 'identity'}})
      -[:TRUST_EDGE {{kind: 'attached_to'}}]->(vm)
WHERE id.props CONTAINS 'admin'
RETURN vm.name AS compute, id.name AS identity, id.props AS identity_props
LIMIT 15
""".strip(),
    },
    # --- Advanced ---
    {
        "id": "cy_a1_t5_compute_critical",
        "title": "A1 — T5 public compute → critical data",
        "description": "Internet VM with read/write path to sensitive data store.",
        "level": "advanced",
        "category": "toxic-combo",
        "query": f"""
MATCH (vm:TrustGraphNode {{tenant_id: '{TENANT}'}})
WHERE vm.props CONTAINS 'is_internet_exposed'
MATCH (vm)<-[:TRUST_EDGE {{kind: 'attached_to'}}]-(id:TrustGraphNode {{kind: 'identity'}})
MATCH (id)-[acc:TRUST_EDGE]->(data:TrustGraphNode {{kind: 'resource'}})
WHERE acc.kind IN ['can_read', 'can_write', 'can_admin']
  AND data.props CONTAINS 'is_critical_data'
RETURN vm.name AS vm, id.name AS identity, acc.kind AS access, data.name AS data_store
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_a2_t7_db_path",
        "title": "A2 — T7 public database path",
        "description": "Exposure chain toward publicly reachable database.",
        "level": "advanced",
        "category": "toxic-combo",
        "query": f"""
MATCH (db:TrustGraphNode {{tenant_id: '{TENANT}'}})
WHERE db.resource_type CONTAINS 'rds' AND db.props CONTAINS 'public'
OPTIONAL MATCH (db)<-[:TRUST_EDGE]-(hop:TrustGraphNode {{tenant_id: '{TENANT}'}})
RETURN db.name AS database, db.props AS db_props, collect(DISTINCT hop.name)[0..5] AS related_hops
LIMIT 10
""".strip(),
    },
    {
        "id": "cy_a3_apigw_deploys_lambda",
        "title": "A3 — API Gateway → Lambda deploys",
        "description": "Unauthenticated API wired to serverless (enterprise pattern).",
        "level": "advanced",
        "category": "toxic-combo",
        "query": f"""
MATCH (api:TrustGraphNode {{tenant_id: '{TENANT}'}})-[d:TRUST_EDGE]->(fn:TrustGraphNode)
WHERE d.kind = 'deploys' AND api.props CONTAINS 'NONE'
RETURN api.name AS api, fn.name AS target, fn.resource_type AS target_type
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_a4_lb_serves_compute",
        "title": "A4 — Public LB serves backend",
        "description": "Internet LB serves edge to compute (lateral movement setup).",
        "level": "advanced",
        "category": "toxic-combo",
        "query": f"""
MATCH (lb:TrustGraphNode {{tenant_id: '{TENANT}'}})-[s:TRUST_EDGE {{kind: 'serves'}}]->(vm:TrustGraphNode)
WHERE lb.props CONTAINS 'internet' OR lb.props CONTAINS 'is_public'
RETURN lb.name AS load_balancer, vm.name AS backend, vm.resource_type AS backend_type
LIMIT 15
""".strip(),
    },
    {
        "id": "cy_a5_shortest_ssh_bucket",
        "title": "A5 — SSH SG to bucket (3-hop)",
        "description": "Manual path audit: ingress → compute → identity → bucket.",
        "level": "advanced",
        "category": "toxic-combo",
        "query": f"""
MATCH (sg:TrustGraphNode {{tenant_id: '{TENANT}'}})-[ing:TRUST_EDGE]->()
WHERE ing.kind = 'allows_ingress' AND ing.props CONTAINS '22'
MATCH (vm:TrustGraphNode {{tenant_id: '{TENANT}'}})-[:TRUST_EDGE {{kind: 'has_sg'}}]->(sg)
MATCH (vm)<-[:TRUST_EDGE {{kind: 'attached_to'}}]-(role:TrustGraphNode {{kind: 'identity'}})
MATCH (role)-[:TRUST_EDGE {{kind: 'can_write'}}]->(b:TrustGraphNode)
WHERE b.resource_type IN ['s3_bucket', 'gcs_bucket']
RETURN sg.name AS sg, vm.name AS vm, role.name AS role, b.name AS bucket
LIMIT 10
""".strip(),
    },
    {
        "id": "cy_a6_exposes_external",
        "title": "A6 — exposes → external principal",
        "description": "Resources explicitly linked to allUsers / world principals.",
        "level": "advanced",
        "category": "cspm",
        "query": f"""
MATCH (r:TrustGraphNode {{tenant_id: '{TENANT}'}})-[e:TRUST_EDGE {{kind: 'exposes'}}]->(x:TrustGraphNode {{kind: 'external'}})
RETURN r.name AS resource, r.resource_type AS type, x.name AS principal, e.props AS props
LIMIT 20
""".strip(),
    },
]


def validate_cypher(query: str) -> str:
    q = query.strip()
    if not q:
        raise ValueError("Cypher is empty")
    if FORBIDDEN_CYPHER.search(q):
        raise ValueError("Write operations are not allowed in the teaching lab")
    if TENANT not in q:
        raise ValueError(f"Include tenant filter tenant_id: '{TENANT}' for lab safety")
    if not re.search(r"\blimit\s+\d+", q, re.IGNORECASE):
        q = f"{q.rstrip(';')}\nLIMIT 100"
    return q


def run_cypher_lab(neo: Neo4jClient, query: str) -> dict[str, Any]:
    safe = validate_cypher(query)
    with neo._driver.session() as session:  # noqa: SLF001
        result = session.run(safe)
        columns = result.keys()
        rows: list[dict[str, Any]] = []
        for record in result:
            row: dict[str, Any] = {}
            for key in columns:
                val = record[key]
                if hasattr(val, "items"):
                    row[key] = dict(val)
                elif isinstance(val, (dict, list, str, int, float, bool)) or val is None:
                    row[key] = val
                else:
                    row[key] = str(val)
            rows.append(row)
            if len(rows) >= 100:
                break
    return {"columns": list(columns), "rows": rows, "row_count": len(rows), "cypher_executed": safe}


def graph_stats(neo: Neo4jClient, tenant_id: UUID) -> dict[str, Any]:
    tid = str(tenant_id)
    with neo._driver.session() as session:  # noqa: SLF001
        nodes = session.run(
            """
            MATCH (n:TrustGraphNode {tenant_id: $tid})
            RETURN n.kind AS kind, count(*) AS c
            """,
            tid=tid,
        ).data()
        edges = session.run(
            """
            MATCH (:TrustGraphNode {tenant_id: $tid})-[r:TRUST_EDGE]->()
            RETURN r.kind AS kind, count(*) AS c
            """,
            tid=tid,
        ).data()
        total_n = session.run(
            "MATCH (n:TrustGraphNode {tenant_id: $tid}) RETURN count(n) AS c",
            tid=tid,
        ).single()["c"]
        total_e = session.run(
            """
            MATCH (:TrustGraphNode {tenant_id: $tid})-[r:TRUST_EDGE]->()
            RETURN count(r) AS c
            """,
            tid=tid,
        ).single()["c"]
    return {
        "node_count": total_n,
        "edge_count": total_e,
        "nodes_by_kind": {r["kind"]: r["c"] for r in nodes},
        "edges_by_kind": {r["kind"]: r["c"] for r in edges},
    }
