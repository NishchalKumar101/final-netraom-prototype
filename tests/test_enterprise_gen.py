from __future__ import annotations

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from netraom_graph_writer.combo.patterns import run_all_patterns

from app.fixture_gen import generate_enterprise_fixture


def test_enterprise_fixture_has_500_assets() -> None:
    fx = generate_enterprise_fixture(target_assets=500)
    assert len(fx["assets"]) == 500
    assert len(fx["nodes"]) > 500
    assert len(fx["edges"]) > 200


def test_enterprise_has_apigw_and_lb_types() -> None:
    fx = generate_enterprise_fixture(target_assets=500)
    types = {a["resource_type"] for a in fx["assets"]}
    assert "apigateway_rest_api" in types
    assert "elbv2_load_balancer" in types
    assert "rds_instance" in types


def test_enterprise_repeated_toxic_patterns() -> None:
    fx = generate_enterprise_fixture(target_assets=500)
    nodes = [TrustGraphNode.model_validate(n) for n in fx["nodes"]]
    edges = [TrustGraphEdge.model_validate(e) for e in fx["edges"]]
    g = NetworkXTrustGraph()
    g.load(nodes, edges)
    t2 = [m for m in run_all_patterns(g) if m.pattern_id == "T2_internet_ssh_admin_path"]
    assert len(t2) >= 10
