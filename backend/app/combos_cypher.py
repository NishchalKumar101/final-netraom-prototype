from __future__ import annotations

from uuid import UUID

from app.neo4j_client import Neo4jClient

WORLD = "net:0.0.0.0/0"

T1_CYPHER = """
MATCH (b:TrustGraphNode {tenant_id: $tenant_id, kind: 'resource'})
WHERE b.props CONTAINS 'is_public'
MATCH (i:TrustGraphNode {tenant_id: $tenant_id, kind: 'identity'})
      -[:TRUST_EDGE {kind: 'can_write'}]->(b)
RETURN b.node_id AS bucket, i.node_id AS identity
LIMIT 100
"""

T2_CYPHER = """
MATCH (sg:TrustGraphNode {tenant_id: $tenant_id})
      -[ing:TRUST_EDGE {kind: 'allows_ingress'}]->(world:TrustGraphNode {node_id: $world})
WHERE ing.props CONTAINS '22'
MATCH (vm:TrustGraphNode {tenant_id: $tenant_id})
      -[:TRUST_EDGE {kind: 'has_sg'}]->(sg)
MATCH (role:TrustGraphNode {tenant_id: $tenant_id, kind: 'identity'})
      -[:TRUST_EDGE {kind: 'attached_to'}]->(vm)
MATCH (role)-[:TRUST_EDGE {kind: 'can_write'}]->(bucket:TrustGraphNode {kind: 'resource'})
WHERE bucket.props CONTAINS 'is_public' OR bucket.props CONTAINS 'is_critical_data'
RETURN vm.node_id AS vm, role.node_id AS role, bucket.node_id AS bucket, sg.node_id AS sg
LIMIT 100
"""


def run_cypher_combo_audit(neo4j: Neo4jClient, tenant_id: UUID) -> dict[str, int]:
    """Bounded Cypher audit (runtime sanity check alongside NetworkX engine)."""
    tid = str(tenant_id)
    counts: dict[str, int] = {}
    with neo4j._driver.session() as session:  # noqa: SLF001 — demo helper
        t1 = session.run(T1_CYPHER, tenant_id=tid).data()
        t2 = session.run(T2_CYPHER, tenant_id=tid, world=WORLD).data()
        counts["T1_cypher_matches"] = len(t1)
        counts["T2_cypher_matches"] = len(t2)
    return counts
