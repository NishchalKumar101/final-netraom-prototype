from __future__ import annotations

from typing import Any

import networkx as nx

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode


class NetworkXTrustGraph:
    """In-memory Trust Graph for toxic-combo evaluation."""

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

    def load(self, nodes: list[TrustGraphNode], edges: list[TrustGraphEdge]) -> None:
        self.graph.clear()
        for node in nodes:
            self.graph.add_node(
                node.node_id,
                kind=node.kind.value,
                labels=node.labels,
                props=node.props,
                tenant_id=str(node.tenant_id),
                cloud=node.cloud.value if node.cloud else None,
                resource_type=node.resource_type,
            )
        for edge in edges:
            self.graph.add_edge(
                edge.src_id,
                edge.dst_id,
                key=edge.edge_id,
                kind=edge.kind.value,
                props=edge.props,
                edge_id=edge.edge_id,
            )

    def node_props(self, node_id: str) -> dict[str, Any]:
        data = self.graph.nodes.get(node_id, {})
        props = dict(data.get("props") or {})
        if data.get("kind"):
            props.setdefault("kind", data["kind"])
        if data.get("resource_type"):
            props.setdefault("resource_type", data["resource_type"])
        return props

    def out_edges(self, node_id: str, *, kind: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        results: list[tuple[str, str, dict[str, Any]]] = []
        for src, dst, _key, data in self.graph.out_edges(node_id, keys=True, data=True):
            if kind and data.get("kind") != kind:
                continue
            results.append((src, dst, data))
        return sorted(results, key=_edge_sort_key)

    def in_edges(self, node_id: str, *, kind: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        results: list[tuple[str, str, dict[str, Any]]] = []
        for src, dst, _key, data in self.graph.in_edges(node_id, keys=True, data=True):
            if kind and data.get("kind") != kind:
                continue
            results.append((src, dst, data))
        return sorted(results, key=_edge_sort_key)

    def all_edges(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Return every canonical directed edge, including parallel relationships."""
        edges = [
            (src, dst, data)
            for src, dst, _key, data in self.graph.edges(keys=True, data=True)
        ]
        return sorted(edges, key=_edge_sort_key)


def _edge_sort_key(edge: tuple[str, str, dict[str, Any]]) -> tuple[str, str, str, str]:
    src, dst, data = edge
    return src, dst, str(data.get("kind") or ""), str(data.get("edge_id") or "")
