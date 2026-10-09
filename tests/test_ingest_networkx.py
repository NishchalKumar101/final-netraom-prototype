from __future__ import annotations

import json
from pathlib import Path

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from netraom_graph_writer.combo.patterns import run_all_patterns

ROOT = Path(__file__).resolve().parents[1] / "fixtures/normalized"


def test_gcp_fixture_loads_and_matches_t1() -> None:
    data = json.loads((ROOT / "gcp_toxic_ssh_bucket.json").read_text())
    nodes = [TrustGraphNode.model_validate(n) for n in data["nodes"]]
    edges = [TrustGraphEdge.model_validate(e) for e in data["edges"]]
    g = NetworkXTrustGraph()
    g.load(nodes, edges)
    ids = {m.pattern_id for m in run_all_patterns(g)}
    assert "T1_public_writable_storage" in ids
