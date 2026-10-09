"""
Test Suite for NetraOM CSPM Weighted Attack Path Risk Engine.
Validates:
1. Multi-hop high-impact path ranking over single-hop low-impact path.
2. Four-factor subscores remain strictly within 0-25.
3. Final score remains capped within 0-100.
4. Determinism of score calculations.
5. Integration with database findings and API endpoints.
"""
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.attack_path_engine import (
    evaluate_path_risk_breakdown,
    calculate_edge_cost,
    RiskBreakdown,
)


class MockGraph:
    """Mock Trust Graph for testing risk scoring without third-party dependencies."""

    def __init__(self, node_props_map: dict):
        self._node_props_map = node_props_map

    def node_props(self, node_id: str) -> dict:
        return self._node_props_map.get(node_id, {})


def create_mock_attack_graph():
    """
    Constructs a test graph map with two competing paths:
    Path A (1-hop): Internet -> Low Risk Public Log Bucket (Low Sensitivity)
    Path B (3-hop): Internet -> Vulnerable EC2 -> SecOps IAM Role -> Prod Crown Jewel Database
    """
    node_props = {
        "net:0.0.0.0/0": {"is_internet_exposed": True, "kind": "external"},
        "s3:public-log-bucket": {
            "kind": "resource",
            "is_public": True,
            "is_critical_data": False,
            "environment": "dev",
        },
        "ec2:web-server-01": {
            "kind": "resource",
            "is_internet_exposed": True,
            "vuln_severity": "CRITICAL",
            "environment": "prod",
        },
        "iam:role/ProdSecOpsRole": {
            "kind": "identity",
            "is_admin": True,
            "can_admin": True,
        },
        "rds:prod-customer-db": {
            "kind": "resource",
            "is_crown_jewel": True,
            "is_critical_data": True,
            "environment": "prod",
            "data_classification": "pii_phi_pci",
        },
    }
    return MockGraph(node_props)


def test_subscore_bounds_and_capping():
    g = create_mock_attack_graph()
    path_b = ["net:0.0.0.0/0", "ec2:web-server-01", "iam:role/ProdSecOpsRole", "rds:prod-customer-db"]
    edges_b = [
        {"kind": "allows_ingress"},
        {"kind": "attached_to"},
        {"kind": "can_admin"},
    ]

    rb = evaluate_path_risk_breakdown(g, path_b, edges_b)

    assert 0 <= rb.exposure <= 25, f"Exposure {rb.exposure} out of 0-25 bounds"
    assert 0 <= rb.privilege <= 25, f"Privilege {rb.privilege} out of 0-25 bounds"
    assert 0 <= rb.exploitability <= 25, f"Exploitability {rb.exploitability} out of 0-25 bounds"
    assert 0 <= rb.impact <= 25, f"Impact {rb.impact} out of 0-25 bounds"
    assert 0 <= rb.final_score <= 100, f"Final score {rb.final_score} out of 0-100 bounds"
    assert rb.final_score == (rb.exposure + rb.privilege + rb.exploitability + rb.impact)
    print("✅ Subscore bounds & 0-100 capping test passed.")


def test_multi_hop_outranks_single_hop():
    """
    Verifies that a 3-hop path to a production crown jewel database receives a HIGHER
    Final Risk Score than a 1-hop path to a low-risk public bucket.
    """
    g = create_mock_attack_graph()

    path_a = ["net:0.0.0.0/0", "s3:public-log-bucket"]
    edges_a = [{"kind": "exposes"}]

    path_b = ["net:0.0.0.0/0", "ec2:web-server-01", "iam:role/ProdSecOpsRole", "rds:prod-customer-db"]
    edges_b = [
        {"kind": "allows_ingress"},
        {"kind": "attached_to"},
        {"kind": "can_admin"},
    ]

    rb_a = evaluate_path_risk_breakdown(g, path_a, edges_a)
    rb_b = evaluate_path_risk_breakdown(g, path_b, edges_b)

    print(f"\nPath A (1-hop) Risk Score: {rb_a.final_score} -> {rb_a.to_dict()}")
    print(f"Path B (3-hop) Risk Score: {rb_b.final_score} -> {rb_b.to_dict()}")

    assert rb_b.final_score > rb_a.final_score, (
        f"Multi-hop high-impact path ({rb_b.final_score}) failed to outrank single-hop low-impact path ({rb_a.final_score})"
    )
    assert rb_b.severity in ("CRITICAL", "HIGH")
    print("✅ Multi-hop high-impact outranking single-hop low-impact test passed.")


def test_score_determinism():
    g = create_mock_attack_graph()
    path = ["net:0.0.0.0/0", "ec2:web-server-01", "iam:role/ProdSecOpsRole", "rds:prod-customer-db"]
    edges = [{"kind": "allows_ingress"}, {"kind": "attached_to"}, {"kind": "can_admin"}]

    score1 = evaluate_path_risk_breakdown(g, path, edges)
    score2 = evaluate_path_risk_breakdown(g, path, edges)

    assert score1.to_dict() == score2.to_dict()
    print("✅ Risk score calculation determinism test passed.")


def test_api_risk_fields():
    import urllib.request
    import json

    res = urllib.request.urlopen("http://localhost:8000/findings")
    assert res.status == 200
    data = json.loads(res.read())
    items = data.get("items", [])
    if items:
        first = items[0]
        assert "risk_score" in first, "risk_score missing from /findings API"
        assert "score_breakdown" in first, "score_breakdown missing from /findings API"
        print(f"✅ API verification passed. Sample finding risk_score: {first['risk_score']}")


if __name__ == "__main__":
    print("--- Running NetraOM CSPM Weighted Risk Engine Test Suite ---")
    test_subscore_bounds_and_capping()
    test_multi_hop_outranks_single_hop()
    test_score_determinism()
    test_api_risk_fields()
    print("\n✅ ALL WEIGHTED ATTACK PATH RISK ENGINE TESTS PASSED PERFECTLY!")
