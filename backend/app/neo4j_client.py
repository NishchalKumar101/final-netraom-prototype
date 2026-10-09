from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from neo4j import GraphDatabase
from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode

from app.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


class Neo4jClient:
    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self) -> None:
        self._driver.close()

    def clear_tenant(self, tenant_id: UUID) -> None:
        tid = str(tenant_id)
        with self._driver.session() as session:
            session.run(
                """
                MATCH (n:TrustGraphNode {tenant_id: $tenant_id})
                DETACH DELETE n
                """,
                tenant_id=tid,
            )

    def upsert_graph(self, nodes: list[TrustGraphNode], edges: list[TrustGraphEdge]) -> None:
        with self._driver.session() as session:
            for node in nodes:
                session.run(
                    """
                    MERGE (n:TrustGraphNode {node_id: $node_id, tenant_id: $tenant_id})
                    SET n.kind = $kind,
                        n.name = $name,
                        n.labels = $labels,
                        n.props = $props,
                        n.cloud = $cloud,
                        n.resource_type = $resource_type,
                        n.region = $region
                    """,
                    node_id=node.node_id,
                    tenant_id=str(node.tenant_id),
                    kind=node.kind.value,
                    name=node.name,
                    labels=node.labels,
                    props=json.dumps(node.props),
                    cloud=node.cloud.value if node.cloud else None,
                    resource_type=node.resource_type,
                    region=node.region,
                )
            for edge in edges:
                session.run(
                    """
                    MATCH (s:TrustGraphNode {node_id: $src_id, tenant_id: $tenant_id})
                    MATCH (d:TrustGraphNode {node_id: $dst_id, tenant_id: $tenant_id})
                    MERGE (s)-[r:TRUST_EDGE {edge_id: $edge_id}]->(d)
                    SET r.kind = $kind, r.props = $props
                    """,
                    src_id=edge.src_id,
                    dst_id=edge.dst_id,
                    tenant_id=str(edge.tenant_id),
                    edge_id=edge.edge_id,
                    kind=edge.kind.value,
                    props=json.dumps(edge.props),
                )

    def neighborhood(self, tenant_id: UUID, node_id: str, depth: int = 2) -> dict[str, Any]:
        tid = str(tenant_id)
        depth = max(1, min(depth, 3))
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (start:TrustGraphNode {tenant_id: $tenant_id, node_id: $node_id})
                CALL apoc.path.subgraphAll(start, {
                  relationshipFilter: 'TRUST_EDGE>',
                  minLevel: 0,
                  maxLevel: $depth
                })
                YIELD nodes, relationships
                RETURN nodes, relationships
                """,
                tenant_id=tid,
                node_id=node_id,
                depth=depth,
            )
            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}
            nodes_out = []
            for n in record["nodes"]:
                props_raw = n.get("props")
                if isinstance(props_raw, str):
                    props = json.loads(props_raw) if props_raw else {}
                else:
                    props = props_raw or {}
                nodes_out.append(
                    {
                        "node_id": n["node_id"],
                        "kind": n.get("kind"),
                        "name": n.get("name"),
                        "cloud": n.get("cloud"),
                        "resource_type": n.get("resource_type"),
                        "region": n.get("region"),
                        "props": props,
                    }
                )
            edges_out = []
            for r in record["relationships"]:
                props_raw = r.get("props")
                if isinstance(props_raw, str):
                    props = json.loads(props_raw) if props_raw else {}
                else:
                    props = props_raw or {}
                edges_out.append(
                    {
                        "edge_id": r.get("edge_id"),
                        "kind": r.get("kind"),
                        "src_id": r.start_node["node_id"],
                        "dst_id": r.end_node["node_id"],
                        "props": props,
                    }
                )
            return {"nodes": nodes_out, "edges": edges_out}

    def neighborhood_fallback(self, tenant_id: UUID, node_id: str, depth: int = 2) -> dict[str, Any]:
        """BFS without APOC when apoc is unavailable."""
        tid = str(tenant_id)
        depth = max(1, min(depth, 3))
        visited_nodes: dict[str, dict[str, Any]] = {}
        visited_edges: dict[str, dict[str, Any]] = {}
        frontier = [node_id]
        for _level in range(depth + 1):
            if not frontier:
                break
            next_frontier: list[str] = []
            with self._driver.session() as session:
                for nid in frontier:
                    rec = session.run(
                        """
                        MATCH (n:TrustGraphNode {tenant_id: $tenant_id, node_id: $node_id})
                        RETURN n
                        """,
                        tenant_id=tid,
                        node_id=nid,
                    ).single()
                    if rec:
                        n = rec["n"]
                        props_raw = n.get("props")
                        props = json.loads(props_raw) if isinstance(props_raw, str) and props_raw else {}
                        visited_nodes[nid] = {
                            "node_id": nid,
                            "kind": n.get("kind"),
                            "name": n.get("name"),
                            "cloud": n.get("cloud"),
                            "resource_type": n.get("resource_type"),
                            "region": n.get("region"),
                            "props": props,
                        }
                    out = session.run(
                        """
                        MATCH (s:TrustGraphNode {tenant_id: $tenant_id, node_id: $node_id})
                              -[r:TRUST_EDGE]->(d:TrustGraphNode)
                        RETURN s.node_id AS src_id, d.node_id AS dst_id, r
                        """,
                        tenant_id=tid,
                        node_id=nid,
                    )
                    for row in out:
                        src_id = row["src_id"]
                        dst_id = row["dst_id"]
                        rel = row["r"]
                        eid = rel.get("edge_id") or f"{src_id}->{dst_id}"
                        props_raw = rel.get("props")
                        props = json.loads(props_raw) if isinstance(props_raw, str) and props_raw else {}
                        visited_edges[eid] = {
                            "edge_id": eid,
                            "kind": rel.get("kind"),
                            "src_id": src_id,
                            "dst_id": dst_id,
                            "props": props,
                        }
                        if dst_id not in visited_nodes and _level < depth:
                            next_frontier.append(dst_id)
                    inc = session.run(
                        """
                        MATCH (s:TrustGraphNode)-[r:TRUST_EDGE]->(d:TrustGraphNode {tenant_id: $tenant_id, node_id: $node_id})
                        RETURN s.node_id AS src_id, d.node_id AS dst_id, r
                        """,
                        tenant_id=tid,
                        node_id=nid,
                    )
                    for row in inc:
                        src_id = row["src_id"]
                        dst_id = row["dst_id"]
                        rel = row["r"]
                        eid = rel.get("edge_id") or f"{src_id}->{dst_id}"
                        props_raw = rel.get("props")
                        props = json.loads(props_raw) if isinstance(props_raw, str) and props_raw else {}
                        visited_edges[eid] = {
                            "edge_id": eid,
                            "kind": rel.get("kind"),
                            "src_id": src_id,
                            "dst_id": dst_id,
                            "props": props,
                        }
                        if src_id not in visited_nodes and _level < depth:
                            next_frontier.append(src_id)
            frontier = list(dict.fromkeys(next_frontier))
        return {"nodes": list(visited_nodes.values()), "edges": list(visited_edges.values())}

    def get_node(self, tenant_id: UUID, node_id: str) -> dict[str, Any] | None:
        tid = str(tenant_id)
        with self._driver.session() as session:
            rec = session.run(
                """
                MATCH (n:TrustGraphNode {tenant_id: $tenant_id, node_id: $node_id})
                RETURN n
                """,
                tenant_id=tid,
                node_id=node_id,
            ).single()
            if not rec:
                return None
            n = rec["n"]
            props_raw = n.get("props")
            if isinstance(props_raw, str):
                props = json.loads(props_raw) if props_raw else {}
            else:
                props = props_raw or {}
            return {
                "node_id": n["node_id"],
                "kind": n.get("kind"),
                "name": n.get("name"),
                "cloud": n.get("cloud"),
                "resource_type": n.get("resource_type"),
                "region": n.get("region"),
                "props": props,
            }

    def get_neighborhood(self, tenant_id: UUID, node_id: str, depth: int = 2) -> dict[str, Any]:
        try:
            return self.neighborhood(tenant_id, node_id, depth)
        except Exception:
            return self.neighborhood_fallback(tenant_id, node_id, depth)
