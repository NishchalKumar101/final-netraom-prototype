from __future__ import annotations

import networkx as nx

from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph


def neighborhood_node_ids(graph: NetworkXTrustGraph, seeds: list[str], max_hops: int) -> set[str]:
    if not seeds:
        return set(graph.graph.nodes)
    allowed: set[str] = set(seeds)
    frontier = set(seeds)
    for _ in range(max_hops):
        next_frontier: set[str] = set()
        for node_id in frontier:
            if node_id not in graph.graph:
                continue
            for neighbor in graph.graph.predecessors(node_id):
                if neighbor not in allowed:
                    allowed.add(neighbor)
                    next_frontier.add(neighbor)
            for neighbor in graph.graph.successors(node_id):
                if neighbor not in allowed:
                    allowed.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier
        if not frontier:
            break
    return allowed


def match_touches_allowed(match_node_ids: list[str], allowed: set[str] | None) -> bool:
    if allowed is None:
        return True
    if not allowed:
        return True
    return any(node_id in allowed for node_id in match_node_ids)
