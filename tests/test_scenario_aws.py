from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from netraom_graph_writer.combo.engine import evaluate_combos
from netraom_graph_writer.combo.patterns import run_all_patterns
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/normalized/aws_toxic_ssh_bucket.json"
TENANT = UUID("11111111-1111-4111-8111-111111111111")
RUN = UUID("44444444-4444-4444-8444-444444444444")
VM_BASTION = "arn:aws:ec2:ap-south-1:123456789012:instance/upload-bastion"


def _load():
    data = json.loads(FIXTURE.read_text())
    nodes = [TrustGraphNode.model_validate(n) for n in data["nodes"]]
    edges = [TrustGraphEdge.model_validate(e) for e in data["edges"]]
    return nodes, edges


def test_aws_fixture_produces_t2_and_not_t9_on_bastion() -> None:
    nodes, edges = _load()
    graph = NetworkXTrustGraph()
    graph.load(nodes, edges)
    matches = run_all_patterns(graph)
    by_id = {m.pattern_id: m for m in matches}
    assert "T2_internet_ssh_admin_path" in by_id
    assert "T1_public_writable_storage" in by_id
    t9 = [m for m in matches if m.pattern_id == "T9_admin_on_internet_compute"]
    assert all(VM_BASTION not in m.node_ids for m in t9)


def test_evaluate_combos_fingerprints() -> None:
    nodes, edges = _load()
    rows = evaluate_combos(nodes, edges, tenant_id=TENANT, run_id=RUN)
    assert any(r["rule_id"] == "T2_internet_ssh_admin_path" for r in rows)
    assert all(r["source"] == "toxic-combo" for r in rows)
