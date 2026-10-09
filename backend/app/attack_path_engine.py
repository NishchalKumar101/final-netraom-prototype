"""
Attack Path Engine for NetraOM CSPM.
Handles:
1. Candidate attack path discovery (BFS/DFS traversals).
2. Traversal cost calculation and Dijkstra/A* ranking.
3. Independent 4-factor risk scoring (Exposure, Privilege, Exploitability, Impact: 0-25 each).
4. Final Risk Score calculation (0-100 max) and explainable score breakdowns.
"""
from __future__ import annotations

import math
import heapq
from collections import deque
from typing import Any, Sequence
from dataclasses import dataclass, field

from app.risk_config import (
    get_edge_weight,
    get_node_criticality_weight,
    get_node_exposure_weight,
    get_node_privilege_weight,
    get_node_sensitivity_weight,
    get_node_vuln_weight,
)


@dataclass
class RiskBreakdown:
    exposure: int          # 0 - 25
    privilege: int         # 0 - 25
    exploitability: int    # 0 - 25
    impact: int            # 0 - 25
    final_score: int       # 0 - 100
    severity: str          # CRITICAL / HIGH / MEDIUM / LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "exposure": self.exposure,
            "privilege": self.privilege,
            "exploitability": self.exploitability,
            "impact": self.impact,
            "final_score": self.final_score,
            "severity": self.severity,
        }


@dataclass
class ScoredAttackPath:
    path_nodes: list[str]
    path_edges: list[dict[str, Any]]
    path_edge_ids: list[str]
    traversal_cost: float
    risk: RiskBreakdown


@dataclass
class AttackPath:
    path_nodes: list[str]
    path_edges: list[dict[str, Any]]
    path_edge_ids: list[str]


@dataclass
class FindingPathAssessment:
    attack_path: ScoredAttackPath | None
    risk: RiskBreakdown


# Canonical graph storage keeps the protecting asset on the source side
# (for example security group -> world, VM -> security group, role -> VM).
# Attacker traversal is derived separately so the route follows the
# exploitable movement direction instead of the graph's storage convention.
ATTACK_TRAVERSAL_POLICY: dict[str, str] = {
    "owns": "forward",
    "contains": "forward",
    "in_vpc": "reverse",
    "in_subnet": "reverse",
    "attached_to": "reverse",
    "has_sg": "reverse",
    "uses": "forward",
    "can_assume": "forward",
    "can_read": "forward",
    "can_write": "forward",
    "can_admin": "forward",
    "grants": "forward",
    "trusts": "forward",
    "federates_to": "forward",
    "allows_ingress": "forward",
    "allows_egress": "forward",
    "resolves_to": "forward",
    "serves": "forward",
    "exposes": "reverse",
    "redirects_to": "forward",
    "runs_image": "forward",
    "deploys": "forward",
}


def _policy_for_edge(graph: Any, src: str, dst: str, edge_kind: str) -> str | None:
    """Return the traversal direction for an edge while keeping canonical storage intact.

    For world-facing relationships (for example security group -> 0.0.0.0/0), the attacker
    moves from the internet entry point into the protected resource. For generic direct edges,
    the canonical direction is kept unless the endpoint metadata clearly marks the target as the
    world representation.
    """
    base = ATTACK_TRAVERSAL_POLICY.get(edge_kind)
    if base is None:
        return None
    if edge_kind == "allows_ingress":
        dst_props = _get_node_props(graph, dst)
        src_props = _get_node_props(graph, src)
        if dst_props.get("is_internet_exposed") or dst_props.get("is_public") or str(dst).startswith("net:") or str(dst).startswith("0.0.0.0"):
            return "reverse"
        if src_props.get("is_internet_exposed") or src_props.get("is_public") or str(src).startswith("net:") or str(src).startswith("0.0.0.0"):
            return "forward"
    return base


def _attacker_adjacency(graph: Any) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    nx_graph = graph.graph if hasattr(graph, "graph") else graph
    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {node_id: [] for node_id in nx_graph.nodes}

    edges: list[tuple[str, str, dict[str, Any]]] = []
    if hasattr(nx_graph, "edges"):
        if nx_graph.is_multigraph():
            for src, dst, _key, data in nx_graph.edges(keys=True, data=True):
                edges.append((src, dst, data))
        else:
            for src, dst, data in nx_graph.edges(data=True):
                edges.append((src, dst, data))

    for src, dst, data in edges:
        kind = str(data.get("kind") or "")
        direction = _policy_for_edge(graph, src, dst, kind)
        if direction not in {"forward", "reverse"}:
            continue
        traversal_src, traversal_dst = (src, dst) if direction == "forward" else (dst, src)
        edge = {
            "edge_id": data.get("edge_id") or f"{src}->{dst}",
            "kind": kind,
            "src_id": src,
            "dst_id": dst,
            "traversal_src_id": traversal_src,
            "traversal_dst_id": traversal_dst,
            "props": data.get("props") or {},
        }
        adjacency.setdefault(traversal_src, []).append((traversal_dst, edge))

    for neighbors in adjacency.values():
        neighbors.sort(
            key=lambda item: (
                item[0],
                str(item[1].get("kind") or ""),
                str(item[1].get("edge_id") or ""),
            )
        )
    return adjacency


def _get_node_props(graph: Any, node_id: str) -> dict[str, Any]:
    """Helper to get props from NetworkXTrustGraph or raw networkx graph or dict."""
    if hasattr(graph, "node_props"):
        return graph.node_props(node_id) or {}
    if hasattr(graph, "nodes") and node_id in graph.nodes:
        return graph.nodes[node_id].get("props") or graph.nodes[node_id] or {}
    return {}


def _get_node_kind(graph: Any, node_id: str) -> str | None:
    props = _get_node_props(graph, node_id)
    if "kind" in props:
        return str(props["kind"])
    if hasattr(graph, "node_props"):
        p = graph.node_props(node_id)
        return p.get("kind")
    return None


def calculate_edge_cost(edge_kind: str, dst_props: dict[str, Any]) -> float:
    """
    Computes logarithmic inverse traversal cost for Dijkstra / A*.
    High-risk / easy traversals yield low cost, so Dijkstra prioritizes high-risk paths.
    """
    rel_weight = get_edge_weight(edge_kind)
    vuln_weight = max(0.1, get_node_vuln_weight(dst_props))
    # Risk factor per hop (0.01 to 1.0)
    risk_factor = max(0.01, rel_weight * vuln_weight)
    # Inverse log cost for Dijkstra (lower cost = higher risk)
    return -math.log(risk_factor) + 0.05


def evaluate_path_risk_breakdown(
    graph: Any,
    node_ids: Sequence[str],
    edges: Sequence[dict[str, Any]] | None = None,
) -> RiskBreakdown:
    """
    Calculates four independent risk subscores (0-25 each) and final risk score (0-100 max).
    1. Exposure Score (0-25)
    2. Privilege Score (0-25)
    3. Exploitability Score (0-25)
    4. Impact Score (0-25)
    """
    if not node_ids:
        return RiskBreakdown(0, 0, 0, 0, 0, "LOW")

    path_nodes = list(node_ids)
    node_props_list = [_get_node_props(graph, nid) for nid in path_nodes]

    # --- 1. EXPOSURE SCORE (0 - 25) ---
    # Evaluates direct internet exposure and public reachability along entry/path nodes
    max_exposure_factor = max(get_node_exposure_weight(props) for props in node_props_list)
    # Check if entry point is world net or internet exposed
    entry_props = node_props_list[0]
    entry_is_internet = (
        path_nodes[0].startswith("net:")
        or entry_props.get("is_internet_exposed")
        or entry_props.get("is_public")
    )
    exposure_multiplier = 1.0 if entry_is_internet else 0.7
    exposure_raw = max_exposure_factor * exposure_multiplier * 25.0
    exposure_score = min(25, max(0, round(exposure_raw)))

    # --- 2. PRIVILEGE SCORE (0 - 25) ---
    # Evaluates highest IAM privilege or admin capacity reached along the path
    max_priv_factor = max(
        get_node_privilege_weight(props, _get_node_kind(graph, nid))
        for props, nid in zip(node_props_list, path_nodes)
    )
    # Check if edge contains admin/write privileges
    edge_priv_bonus = 0.0
    if edges:
        for e in edges:
            kind = e.get("kind", "")
            if kind in ("can_admin", "can_write", "can_assume"):
                edge_priv_bonus = max(edge_priv_bonus, get_edge_weight(kind))
    privilege_raw = (max_priv_factor * 0.7 + edge_priv_bonus * 0.3) * 25.0
    privilege_score = min(25, max(0, round(privilege_raw)))

    # --- 3. EXPLOITABILITY SCORE (0 - 25) ---
    # Evaluates technical ease of traversal and vulnerability severity
    max_vuln_factor = max(get_node_vuln_weight(props) for props in node_props_list)
    avg_rel_weight = 0.8
    if edges:
        avg_rel_weight = sum(get_edge_weight(e.get("kind", "")) for e in edges) / max(1, len(edges))
    exploitability_raw = (max_vuln_factor * 0.5 + avg_rel_weight * 0.5) * 25.0
    exploitability_score = min(25, max(0, round(exploitability_raw)))

    # --- 4. IMPACT SCORE (0 - 25) ---
    # Evaluates target asset criticality, crown jewel status, and data sensitivity
    target_props = node_props_list[-1]
    crit_w = get_node_criticality_weight(target_props)
    sens_w = get_node_sensitivity_weight(target_props)
    impact_raw = (crit_w * 0.6 + sens_w * 0.4) * 25.0
    impact_score = min(25, max(0, round(impact_raw)))

    # --- FINAL RISK SCORE (Sum of 4 factors, capped at 100) ---
    final_score = min(100, max(0, exposure_score + privilege_score + exploitability_score + impact_score))

    if final_score >= 90:
        severity = "CRITICAL"
    elif final_score >= 70:
        severity = "HIGH"
    elif final_score >= 40:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return RiskBreakdown(
        exposure=exposure_score,
        privilege=privilege_score,
        exploitability=exploitability_score,
        impact=impact_score,
        final_score=final_score,
        severity=severity,
    )


def find_candidate_paths_bfs(
    graph: Any,
    source_node: str,
    target_node: str | None = None,
    max_hops: int = 5,
    candidate_limit: int = 100,
) -> list[AttackPath]:
    """Discover deterministic, simple attacker routes with explicit hop/candidate bounds."""
    nx_graph = graph.graph if hasattr(graph, "graph") else graph
    if (
        source_node not in nx_graph
        or (target_node is not None and target_node not in nx_graph)
        or max_hops < 0
        or candidate_limit < 0
        or candidate_limit == 0
    ):
        return []

    adjacency = _attacker_adjacency(graph)
    candidate_paths: list[AttackPath] = []
    queue = deque([([source_node], [], [])])
    canonical_seen: set[tuple[str, ...]] = set()

    while queue and len(candidate_paths) < candidate_limit:
        path_nodes, path_edges, path_edge_ids = queue.popleft()
        current = path_nodes[-1]

        if target_node is not None and current == target_node:
            candidate_paths.append(AttackPath(path_nodes, path_edges, path_edge_ids))
            continue

        if target_node is None and path_edges:
            candidate_paths.append(AttackPath(path_nodes, path_edges, path_edge_ids))
            if len(candidate_paths) >= candidate_limit:
                break

        if len(path_edges) >= max_hops:
            continue

        for neighbor, edge in adjacency.get(current, []):
            if neighbor in path_nodes:
                continue
            next_nodes = [*path_nodes, neighbor]
            next_edge_ids = [*path_edge_ids, str(edge["edge_id"])]
            key = (tuple(next_nodes), tuple(next_edge_ids))
            if key in canonical_seen:
                continue
            canonical_seen.add(key)
            queue.append((next_nodes, [*path_edges, edge], next_edge_ids))

    if target_node is not None:
        return [p for p in candidate_paths if p.path_nodes and p.path_nodes[-1] == target_node]
    return candidate_paths


def find_rank_paths_dijkstra(
    graph: Any,
    source_node: str,
    target_node: str,
    max_hops: int = 8,
    candidate_limit: int = 10,
) -> list[ScoredAttackPath]:
    """
    Enumerate bounded simple routes in nondecreasing traversal cost, then risk-rank them.

    This is a deterministic bounded shortest-path search: each queue entry is keyed by the
    exact current route, stale heap entries are ignored, and candidate discovery stops at the
    explicit route and hop limits.
    """
    nx_graph = graph.graph if hasattr(graph, "graph") else graph
    if (
        source_node not in nx_graph
        or target_node not in nx_graph
        or max_hops < 0
        or candidate_limit < 0
        or candidate_limit == 0
    ):
        return []

    from app.graph_utils import path_edges_for_route

    adjacency = _attacker_adjacency(graph)
    pq: list[tuple[float, int, tuple[str, ...], tuple[str, ...]]] = [(0.0, 0, (source_node,), ())]
    best_cost: dict[tuple[tuple[str, ...], tuple[str, ...]], float] = {((source_node,), ()): 0.0}
    discovered: list[tuple[float, tuple[str, ...], tuple[str, ...]]] = []
    seen_targets: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    counter = 0

    while pq:
        cost, _counter, path_nodes, path_edge_ids = heapq.heappop(pq)
        state = (path_nodes, path_edge_ids)
        if cost > best_cost.get(state, math.inf):
            continue

        current = path_nodes[-1]
        if current == target_node:
            if state not in seen_targets:
                discovered.append((cost, path_nodes, path_edge_ids))
                seen_targets.add(state)
            if len(discovered) >= candidate_limit:
                break
            continue

        if len(path_edge_ids) >= max_hops:
            continue

        for neighbor, edge in adjacency.get(current, []):
            if neighbor in path_nodes:
                continue
            edge_cost = calculate_edge_cost(
                str(edge.get("kind") or "default"),
                _get_node_props(graph, neighbor),
            )
            next_nodes = (*path_nodes, neighbor)
            next_edge_ids = (*path_edge_ids, str(edge["edge_id"]))
            new_cost = cost + edge_cost
            next_state = (next_nodes, next_edge_ids)
            previous_best = best_cost.get(next_state)
            if previous_best is not None and new_cost >= previous_best:
                continue
            best_cost[next_state] = new_cost
            counter += 1
            heapq.heappush(pq, (new_cost, counter, next_nodes, next_edge_ids))

    results: list[ScoredAttackPath] = []
    for cost, path_nodes, path_edge_ids in discovered:
        edges = path_edges_for_route(graph, list(path_nodes), list(path_edge_ids))
        risk_breakdown = evaluate_path_risk_breakdown(graph, path_nodes, edges)
        results.append(
            ScoredAttackPath(
                path_nodes=list(path_nodes),
                path_edges=edges,
                path_edge_ids=list(path_edge_ids),
                traversal_cost=cost,
                risk=risk_breakdown,
            )
        )

    results.sort(
        key=lambda item: (
            -item.risk.final_score,
            item.traversal_cost,
            tuple(item.path_nodes),
            tuple(item.path_edge_ids),
        )
    )
    return results


def assess_finding_path(
    graph: Any,
    finding_node_ids: Sequence[str],
    *,
    max_hops: int = 8,
    candidate_limit: int = 10,
) -> FindingPathAssessment:
    """Score a finding using a valid attacker route when its graph nodes support one."""
    node_ids = sorted({str(node_id) for node_id in finding_node_ids if node_id})
    entry_nodes = [
        node_id
        for node_id in node_ids
        if node_id.startswith(("net:", "ext:"))
        or _get_node_kind(graph, node_id) == "external"
        or _get_node_props(graph, node_id).get("is_internet_exposed")
        or _get_node_props(graph, node_id).get("is_public")
    ]

    paths: list[ScoredAttackPath] = []
    for source in entry_nodes:
        for target in node_ids:
            if target == source:
                continue
            paths.extend(
                find_rank_paths_dijkstra(
                    graph,
                    source,
                    target,
                    max_hops=max_hops,
                    candidate_limit=candidate_limit,
                )
            )

    if paths:
        paths.sort(
            key=lambda item: (
                -item.risk.final_score,
                item.traversal_cost,
                tuple(item.path_nodes),
                tuple(item.path_edge_ids),
            )
        )
        best_path = paths[0]
        return FindingPathAssessment(best_path, best_path.risk)

    # Non-path findings (for example a standalone public bucket) still receive the
    # existing factor score, but an unordered finding-node collection is never scored as a route.
    single_node_risks = [
        evaluate_path_risk_breakdown(graph, [node_id], [])
        for node_id in node_ids
    ]
    if not single_node_risks:
        return FindingPathAssessment(None, RiskBreakdown(0, 0, 0, 0, 0, "LOW"))
    risk = max(single_node_risks, key=lambda item: (item.final_score, item.severity))
    return FindingPathAssessment(None, risk)
