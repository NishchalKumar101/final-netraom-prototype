from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from netraom_graph_writer.combo.engine import evaluate_combos
from sqlalchemy.orm import Session

from app.combos_cypher import run_cypher_combo_audit
from app.combos_demo import evaluate_extra_demo_patterns
from app.config import DEMO_TENANT_ID
from app.db.models import FindingRow
from app.graph_utils import assess_finding_graph_path
from app.neo4j_client import Neo4jClient


def _tenant_scoped_fingerprint(fingerprint: str, tenant_id: UUID) -> str:
    if tenant_id == DEMO_TENANT_ID:
        return fingerprint
    prefix, _, _ = fingerprint.partition(":")
    material = f"{tenant_id}:{fingerprint}"
    return f"{prefix}:{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def evaluate_and_persist_combos(
    db: Session,
    neo4j: Neo4jClient,
    *,
    tenant_id: UUID,
    run_id: UUID,
    nodes: list[TrustGraphNode],
    edges: list[TrustGraphEdge],
    cspm_findings: list[dict[str, Any]] | None = None,
    assets: list[dict[str, Any]] | None = None,
    all_patterns: bool = False,
    include_demo_patterns: bool = False,
) -> list[dict[str, Any]]:
    graph = NetworkXTrustGraph()
    graph.load(nodes, edges)

    core_patterns = None
    if not all_patterns:
        core_patterns = [
            "T1_public_writable_storage",
            "T2_internet_ssh_admin_path",
            "T5_public_compute_to_critical_data",
            "T6_public_unencrypted_storage",
            "T9_admin_on_internet_compute",
        ]

    rows = evaluate_combos(
        nodes,
        edges,
        tenant_id=tenant_id,
        run_id=run_id,
        cspm_findings=cspm_findings,
        assets=assets,
        pattern_ids=core_patterns,
    )

    if include_demo_patterns:
        rows.extend(evaluate_extra_demo_patterns(graph, db, tenant_id=tenant_id))

    run_cypher_combo_audit(neo4j, tenant_id)

    now = datetime.now(tz=UTC)
    for row in rows:
        row["fingerprint"] = _tenant_scoped_fingerprint(row["fingerprint"], tenant_id)
        node_ids = row.get("trust_graph_node_ids") or []
        path_data = assess_finding_graph_path(graph, node_ids)
        row.update(path_data)
        db.merge(
            FindingRow(
                fingerprint=row["fingerprint"],
                tenant_id=tenant_id,
                source=str(row["source"]),
                rule_id=row["rule_id"],
                title=row["title"],
                description=row.get("description"),
                severity=str(row.get("severity", path_data["score_breakdown"]["severity"].lower())),
                ssvc_action=str(row.get("ssvc_action", "immediate")),
                exposure=str(row.get("exposure", "internet")),
                canonical_key=node_ids[0] if node_ids else None,
                trust_graph_node_ids=node_ids,
                path_edges=path_data["path_edges"],
                risk_score=path_data["risk_score"],
                score_breakdown=path_data["score_breakdown"],
                last_seen=now,
            )
        )
    db.commit()
    return rows
