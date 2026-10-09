from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph

from app import combos as combos_module
from app.combos import evaluate_and_persist_combos
from app.graph_utils import assess_finding_graph_path, ordered_route_node_ids
from app.misconfig import evaluate_misconfigs

TENANT = UUID("11111111-1111-4111-8111-111111111111")
RUN = UUID("22222222-2222-4222-8222-222222222222")
AWS_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/normalized/aws_toxic_ssh_bucket.json"


class _MemorySession:
    def __init__(self):
        self.merged = []

    def merge(self, row):
        self.merged.append(row)

    def commit(self):
        pass


def _aws_fixture():
    payload = json.loads(AWS_FIXTURE.read_text())
    nodes = [TrustGraphNode.model_validate(row) for row in payload["nodes"]]
    edges = [TrustGraphEdge.model_validate(row) for row in payload["edges"]]
    return nodes, edges


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


def _edge(edge_id: str, kind: str, src_id: str, dst_id: str):
    return TrustGraphEdge(
        tenant_id=TENANT,
        edge_id=edge_id,
        kind=kind,
        src_id=src_id,
        dst_id=dst_id,
        props={},
        status="active",
        last_seen="2024-01-01T00:00:00Z",
        last_scan_run_id=RUN,
        source_modules=["test"],
    )


def test_finding_score_uses_exact_ordered_attack_route() -> None:
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
            _edge("edge-ingress", "allows_ingress", "sg:public", "net:0.0.0.0/0"),
            _edge("edge-sg-01", "has_sg", "vm:app", "sg:public"),
            _edge("edge-role-01", "attached_to", "role:admin", "vm:app"),
            _edge("edge-admin-01", "can_admin", "role:admin", "db:prod"),
        ],
    )

    result = assess_finding_graph_path(
        graph,
        ["db:prod", "role:admin", "vm:app", "sg:public", "net:0.0.0.0/0"],
    )

    assert result["attack_path_nodes"] == [
        "net:0.0.0.0/0",
        "sg:public",
        "vm:app",
        "role:admin",
        "db:prod",
    ]
    assert result["attack_path_edge_ids"] == [
        "edge-ingress",
        "edge-sg-01",
        "edge-role-01",
        "edge-admin-01",
    ]
    assert [edge["edge_id"] for edge in result["path_edges"]] == result["attack_path_edge_ids"]
    assert result["risk_score"] == result["score_breakdown"]["final_score"]
    assert ordered_route_node_ids(result["path_edges"]) == result["attack_path_nodes"]


def test_finding_without_valid_route_gets_safe_single_node_score_only() -> None:
    graph = NetworkXTrustGraph()
    graph.load(
        [
            _node("bucket:public", "resource", is_public=True),
            _node("role:unrelated", "identity", can_admin=True),
        ],
        [],
    )

    result = assess_finding_graph_path(graph, ["bucket:public", "role:unrelated"])

    assert result["attack_path_nodes"] == []
    assert result["attack_path_edge_ids"] == []
    assert result["path_edges"] == []
    assert result["risk_score"] == result["score_breakdown"]["final_score"]
    assert ordered_route_node_ids(result["path_edges"]) == []


def test_combo_pipeline_persists_exact_ranked_t2_route(monkeypatch) -> None:
    nodes, edges = _aws_fixture()
    db = _MemorySession()
    monkeypatch.setattr(combos_module, "run_cypher_combo_audit", lambda *_args: None)

    rows = evaluate_and_persist_combos(
        db,
        object(),
        tenant_id=TENANT,
        run_id=RUN,
        nodes=nodes,
        edges=edges,
    )

    finding = next(row for row in rows if row["rule_id"] == "T2_internet_ssh_admin_path")
    assert finding["attack_path_nodes"] == [
        "arn:aws:ec2:ap-south-1:123456789012:instance/upload-bastion",
        "arn:aws:iam::123456789012:role/upload-writer",
        "arn:aws:s3:::customer-uploads",
    ]
    assert finding["attack_path_edge_ids"] == [
        "e009e009e009e009e009e009e009e009",
        "e012e012e012e012e012e012e012e012",
    ]
    assert [
        (edge["src_id"], edge["dst_id"])
        for edge in finding["path_edges"]
    ] == [
        (
            "arn:aws:iam::123456789012:role/upload-writer",
            "arn:aws:ec2:ap-south-1:123456789012:instance/upload-bastion",
        ),
        (
            "arn:aws:iam::123456789012:role/upload-writer",
            "arn:aws:s3:::customer-uploads",
        ),
    ]
    assert finding["risk_score"] == finding["score_breakdown"]["final_score"]
    persisted = next(row for row in db.merged if row.fingerprint == finding["fingerprint"])
    assert [edge["edge_id"] for edge in persisted.path_edges] == finding["attack_path_edge_ids"]


def test_misconfiguration_pipeline_uses_path_or_empty_edges_safely() -> None:
    nodes, edges = _aws_fixture()
    db = _MemorySession()

    findings = evaluate_misconfigs(db, tenant_id=TENANT, nodes=nodes, edges=edges)

    ssh = next(row for row in findings if row["rule_id"] == "aws_sg_world_ssh")
    assert ssh["attack_path_nodes"] == [
        "net:0.0.0.0/0",
        "arn:aws:ec2:ap-south-1:123456789012:security-group/sg-upload-ssh",
    ]
    assert ssh["attack_path_edge_ids"] == ["e001e001e001e001e001e001e001e001"]
    assert ssh["risk_score"] == ssh["score_breakdown"]["final_score"]

    standalone = next(row for row in findings if row["rule_id"] == "aws_s3_public_read")
    assert standalone["attack_path_nodes"] == []
    assert standalone["path_edges"] == []
