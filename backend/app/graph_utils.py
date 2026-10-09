from __future__ import annotations

from typing import Any

from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph


def path_edges_for_nodes(graph: NetworkXTrustGraph, node_ids: list[str]) -> list[dict[str, Any]]:
    """Return edges in a node-set neighborhood (not an ordered attack route)."""
    allowed = set(node_ids)
    edges: list[dict[str, Any]] = []
    for src, dst, data in graph.all_edges():
        if src in allowed and dst in allowed:
            eid = data.get("edge_id") or f"{src}->{dst}"
            edges.append(
                {
                    "edge_id": eid,
                    "kind": data.get("kind"),
                    "src_id": src,
                    "dst_id": dst,
                    "props": data.get("props") or {},
                }
            )
    return edges


def path_edges_for_route(
    graph: NetworkXTrustGraph,
    path_nodes: list[str],
    path_edge_ids: list[str],
) -> list[dict[str, Any]]:
    """Resolve an ordered route to its exact canonical edges and traversal directions."""
    if len(path_nodes) != len(path_edge_ids) + 1:
        raise ValueError("A route must have exactly one fewer edge than nodes.")

    edges_by_id = {
        str(data.get("edge_id")): (src, dst, data)
        for src, dst, data in graph.all_edges()
        if data.get("edge_id") is not None
    }
    route_edges: list[dict[str, Any]] = []
    for index, edge_id in enumerate(path_edge_ids):
        data = edges_by_id.get(edge_id)
        if data is None:
            raise ValueError(f"Route edge {edge_id!r} is not present in the graph.")
        src, dst, attrs = data
        traversal_src, traversal_dst = path_nodes[index : index + 2]
        if (src, dst) not in {
            (traversal_src, traversal_dst),
            (traversal_dst, traversal_src),
        }:
            raise ValueError(f"Route edge {edge_id!r} does not connect its adjacent nodes.")
        route_edges.append(
            {
                "edge_id": edge_id,
                "kind": attrs.get("kind"),
                "src_id": src,
                "dst_id": dst,
                "traversal_src_id": traversal_src,
                "traversal_dst_id": traversal_dst,
                "props": attrs.get("props") or {},
            }
        )
    return route_edges


def ordered_route_node_ids(path_edges: list[dict[str, Any]]) -> list[str]:
    """Recover route nodes only from a complete, explicitly ordered edge sequence."""
    if not path_edges:
        return []
    first_src = path_edges[0].get("traversal_src_id")
    if not first_src:
        return []
    node_ids = [str(first_src)]
    for edge in path_edges:
        src = edge.get("traversal_src_id")
        dst = edge.get("traversal_dst_id")
        if not src or not dst or str(src) != node_ids[-1]:
            return []
        node_ids.append(str(dst))
    return node_ids


def assess_finding_graph_path(
    graph: NetworkXTrustGraph,
    node_ids: list[str],
) -> dict[str, Any]:
    """Return shared path/risk metadata without treating finding context as a route."""
    from app.attack_path_engine import assess_finding_path

    assessment = assess_finding_path(graph, node_ids)
    path = assessment.attack_path
    return {
        "risk_score": assessment.risk.final_score,
        "score_breakdown": assessment.risk.to_dict(),
        "path_edges": path.path_edges if path else [],
        "attack_path_nodes": path.path_nodes if path else [],
        "attack_path_edge_ids": path.path_edge_ids if path else [],
    }
