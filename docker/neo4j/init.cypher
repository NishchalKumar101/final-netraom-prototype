CREATE CONSTRAINT trust_graph_node_id IF NOT EXISTS
FOR (n:TrustGraphNode) REQUIRE (n.tenant_id, n.node_id) IS UNIQUE;

CREATE INDEX trust_graph_node_kind IF NOT EXISTS FOR (n:TrustGraphNode) ON (n.kind);
CREATE INDEX trust_graph_node_cloud IF NOT EXISTS FOR (n:TrustGraphNode) ON (n.cloud);
CREATE INDEX trust_graph_edge_kind IF NOT EXISTS FOR ()-[r:TRUST_EDGE]-() ON (r.kind);
