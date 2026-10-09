from __future__ import annotations

from uuid import UUID

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph

from app.attack_path_engine import find_candidate_paths_bfs, find_rank_paths_dijkstra
from app.graph_utils import path_edges_for_route

TENANT = UUID("11111111-1111-4111-8111-111111111111")
RUN = UUID("22222222-2222-4222-8222-222222222222")


def _node(node_id: str, kind: str, **props):
    return TrustGraphNode(
        tenant_id=TENANT,
        node_id=node_id,
        kind=kind,
        labels=[kind],
        props=props,
        status="active",
        last_seen="2024-01-01T00:00:00Z",
        last_scan_run_id=RUN,
        source_modules=["test"],
    )


def _edge(edge_id: str, kind: str, src_id: str, dst_id: str, **props):
    return TrustGraphEdge(
        tenant_id=TENANT,
        edge_id=edge_id,
        kind=kind,
        src_id=src_id,
        dst_id=dst_id,
        props=props,
        status="active",
        last_seen="2024-01-01T00:00:00Z",
        last_scan_run_id=RUN,
        source_modules=["test"],
    )


def test_attacker_traversal_preserves_canonical_directions() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("net:0.0.0.0/0", "external", is_internet_exposed=True),
            _node("sg:public", "network"),
            _node("vm:app", "resource"),
            _node("role:admin", "identity", can_admin=True),
            _node("db:prod", "resource", is_critical_data=True),
        ],
        [
            _edge("edge-0001", "allows_ingress", "sg:public", "net:0.0.0.0/0", cidr="0.0.0.0/0", port_from=22),
            _edge("edge-0002", "has_sg", "vm:app", "sg:public"),
            _edge("edge-0003", "attached_to", "role:admin", "vm:app"),
            _edge("edge-0004", "can_admin", "role:admin", "db:prod"),
        ],
    )

    routes = find_candidate_paths_bfs(graph, "net:0.0.0.0/0", "db:prod", max_hops=4, candidate_limit=10)
    assert len(routes) == 1
    route = routes[0]
    assert route.path_nodes == ["net:0.0.0.0/0", "sg:public", "vm:app", "role:admin", "db:prod"]
    assert route.path_edge_ids == ["edge-0001", "edge-0002", "edge-0003", "edge-0004"]
    route_edges = path_edges_for_route(graph, route.path_nodes, route.path_edge_ids)
    assert [(e["src_id"], e["dst_id"]) for e in route_edges] == [
        ("sg:public", "net:0.0.0.0/0"),
        ("vm:app", "sg:public"),
        ("role:admin", "vm:app"),
        ("role:admin", "db:prod"),
    ]
    assert [e["traversal_src_id"] for e in route_edges] == ["net:0.0.0.0/0", "sg:public", "vm:app", "role:admin"]
    assert [e["traversal_dst_id"] for e in route_edges] == ["sg:public", "vm:app", "role:admin", "db:prod"]


def test_direct_ingress_already_in_traversal_direction() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("net:0.0.0.0/0", "external", is_internet_exposed=True),
            _node("sg:public", "network"),
        ],
        [_edge("edge-direct-ingress", "allows_ingress", "net:0.0.0.0/0", "sg:public")],
    )

    routes = find_candidate_paths_bfs(graph, "net:0.0.0.0/0", "sg:public", max_hops=1)
    assert len(routes) == 1
    assert routes[0].path_nodes == ["net:0.0.0.0/0", "sg:public"]
    assert routes[0].path_edge_ids == ["edge-direct-ingress"]


def test_cycle_and_hop_limits_stop_expansion() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("net:0.0.0.0/0", "external", is_internet_exposed=True),
            _node("sg:public", "network"),
            _node("vm:app", "resource"),
            _node("role:admin", "identity"),
            _node("db:prod", "resource"),
        ],
        [
            _edge("edge-0001", "allows_ingress", "sg:public", "net:0.0.0.0/0"),
            _edge("edge-0002", "has_sg", "vm:app", "sg:public"),
            _edge("edge-0003", "attached_to", "role:admin", "vm:app"),
            _edge("edge-0004", "can_admin", "role:admin", "db:prod"),
            _edge("edge-0005", "attached_to", "vm:app", "role:admin"),
        ],
    )

    routes = find_candidate_paths_bfs(graph, "net:0.0.0.0/0", "db:prod", max_hops=2, candidate_limit=20)
    assert routes == []
    routes = find_candidate_paths_bfs(graph, "net:0.0.0.0/0", "db:prod", max_hops=4, candidate_limit=20)
    assert routes
    assert all(len(route.path_nodes) == len(set(route.path_nodes)) for route in routes)
    ranked = find_rank_paths_dijkstra(graph, "net:0.0.0.0/0", "db:prod", max_hops=4, candidate_limit=20)
    assert ranked
    assert all(len(route.path_nodes) == len(set(route.path_nodes)) for route in ranked)


def test_parallel_edges_are_preserved_and_route_exact() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("source", "external"),
            _node("target", "resource"),
        ],
        [
            _edge("edge-read", "can_read", "source", "target"),
            _edge("edge-admin", "can_admin", "source", "target"),
        ],
    )

    out = graph.out_edges("source")
    assert len(out) == 2
    assert {data["edge_id"] for _src, _dst, data in out} == {"edge-read", "edge-admin"}
    routes = find_candidate_paths_bfs(graph, "source", "target", max_hops=1, candidate_limit=10)
    assert len(routes) == 2
    seen_edge_ids = {tuple(route.path_edge_ids) for route in routes}
    assert seen_edge_ids == {("edge-read",), ("edge-admin",)}
    ranked = find_rank_paths_dijkstra(graph, "source", "target", max_hops=1, candidate_limit=10)
    assert {tuple(route.path_edge_ids) for route in ranked} == {("edge-read",), ("edge-admin",)}


def test_unreachable_and_missing_targets_return_empty() -> None:
    graph = NetworkXTrustGraph()
    graph.load([_node("a", "external"), _node("b", "resource")], [])
    assert find_candidate_paths_bfs(graph, "a", "missing", max_hops=5, candidate_limit=10) == []
    assert find_rank_paths_dijkstra(graph, "a", "missing", max_hops=5, candidate_limit=10) == []
    assert find_rank_paths_dijkstra(graph, "missing", "b", max_hops=5, candidate_limit=10) == []


def test_max_hops_and_candidate_limits_are_enforced() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("start", "external"),
            _node("mid1", "network"),
            _node("mid2", "network"),
            _node("finish", "resource"),
        ],
        [
            _edge("edge-0001", "allows_ingress", "start", "mid1"),
            _edge("edge-0002", "allows_ingress", "mid1", "mid2"),
            _edge("edge-0003", "allows_ingress", "mid2", "finish"),
        ],
    )

    assert len(find_candidate_paths_bfs(graph, "start", "finish", max_hops=1, candidate_limit=10)) == 0
    assert find_candidate_paths_bfs(graph, "start", "finish", max_hops=3, candidate_limit=0) == []
    assert len(find_candidate_paths_bfs(graph, "start", "finish", max_hops=3, candidate_limit=1)) == 1
    assert find_rank_paths_dijkstra(graph, "start", "finish", max_hops=1, candidate_limit=10) == []
    assert len(find_rank_paths_dijkstra(graph, "start", "finish", max_hops=3, candidate_limit=1)) == 1


def test_unrecognized_relationship_is_not_traversed() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [_node("source", "external"), _node("target", "resource")],
        [_edge("edge-related", "related_to", "source", "target")],
    )

    assert find_candidate_paths_bfs(graph, "source", "target", max_hops=1) == []


def test_dijkstra_is_deterministic_for_equal_cost_routes() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("start", "external"),
            _node("left", "network"),
            _node("right", "network"),
            _node("finish", "resource"),
        ],
        [
            _edge("edge-left", "allows_ingress", "start", "left"),
            _edge("edge-right", "allows_ingress", "start", "right"),
            _edge("edge-left-2", "allows_ingress", "left", "finish"),
            _edge("edge-right-2", "allows_ingress", "right", "finish"),
        ],
    )

    first = find_rank_paths_dijkstra(graph, "start", "finish", max_hops=2, candidate_limit=10)
    second = find_rank_paths_dijkstra(graph, "start", "finish", max_hops=2, candidate_limit=10)
    assert first == second
    assert [p.path_nodes for p in first] == [["start", "left", "finish"], ["start", "right", "finish"]]
