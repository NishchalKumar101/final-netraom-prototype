from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from netraom_contracts.models.enums import Exposure, FindingSeverity, FindingSource, SsvcAction
from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from sqlalchemy.orm import Session

from app.db.models import FindingRow
from app.graph_utils import assess_finding_graph_path


def _fp(pattern_id: str, node_ids: list[str]) -> str:
    material = f"{pattern_id}:{','.join(sorted(node_ids))}"
    return f"toxic-combo:{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def evaluate_extra_demo_patterns(
    graph: NetworkXTrustGraph,
    db: Session,
    *,
    tenant_id: UUID,
) -> list[dict[str, Any]]:
    """Demo-only toxic combos not in core T1–T9 catalog (APIGW, ALB, etc.)."""
    now = datetime.now(tz=UTC)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for node_id in graph.graph.nodes:
        props = graph.node_props(node_id)
        rt = props.get("resource_type") or ""

        if rt == "apigateway_rest_api" and props.get("auth_type") == "NONE":
            for _api, fn_id, _ in graph.out_edges(node_id, kind="deploys"):
                fn_props = graph.node_props(fn_id)
                if fn_props.get("resource_type") != "lambda_function":
                    continue
                for role_id in _roles_for_compute(graph, fn_id):
                    for _r, dst, _ in graph.out_edges(role_id, kind="can_write"):
                        dst_props = graph.node_props(dst)
                        if dst_props.get("is_critical_data") or dst_props.get("resource_type") == "dynamodb_table":
                            nids = sorted([node_id, fn_id, role_id, dst])
                            fp = _fp("D1_apigw_no_auth_to_sensitive_data", nids)
                            if fp in seen:
                                continue
                            seen.add(fp)
                            rows.append(_persist_demo_combo(
                                db,
                                tenant_id=tenant_id,
                                pattern_id="D1_apigw_no_auth_to_sensitive_data",
                                node_ids=nids,
                                title="Public API without auth can modify sensitive data",
                                description=(
                                    f"API `{node_id}` has no authorizer and reaches `{dst}` via `{fn_id}`."
                                ),
                                graph=graph,
                                now=now,
                            ))

        if rt in {"elbv2_load_balancer", "alb", "nlb"} and (
            props.get("is_public") or props.get("scheme") == "internet-facing"
        ):
            for _lb, vm_id, _ in graph.out_edges(node_id, kind="serves"):
                if not graph.node_props(vm_id).get("is_internet_exposed"):
                    continue
                for role_id in _roles_for_compute(graph, vm_id):
                    for kind in ("can_write", "can_read"):
                        for _r, bucket_id, _ in graph.out_edges(role_id, kind=kind):
                            bprops = graph.node_props(bucket_id)
                            if bprops.get("is_public") or bprops.get("is_critical_data"):
                                nids = sorted([node_id, vm_id, role_id, bucket_id])
                                fp = _fp("D2_public_lb_to_exposed_data", nids)
                                if fp in seen:
                                    continue
                                seen.add(fp)
                                rows.append(_persist_demo_combo(
                                    db,
                                    tenant_id=tenant_id,
                                    pattern_id="D2_public_lb_to_exposed_data",
                                    node_ids=nids,
                                    title="Internet-facing load balancer path to exposed data",
                                    description=(
                                        f"Load balancer `{node_id}` serves `{vm_id}` with access to `{bucket_id}`."
                                    ),
                                    graph=graph,
                                    now=now,
                                ))

    db.commit()
    return rows


def _roles_for_compute(g: NetworkXTrustGraph, compute_id: str) -> list[str]:
    roles: list[str] = []
    for src, _dst, _ in g.in_edges(compute_id, kind="attached_to"):
        if g.node_props(src).get("kind") == "identity" or ":role/" in src or "serviceaccount" in src.lower():
            roles.append(src)
    return roles


def _persist_demo_combo(
    db: Session,
    *,
    tenant_id: UUID,
    pattern_id: str,
    node_ids: list[str],
    title: str,
    description: str,
    graph: NetworkXTrustGraph,
    now: datetime,
) -> dict[str, Any]:
    fingerprint = _fp(pattern_id, node_ids)
    path_data = assess_finding_graph_path(graph, node_ids)
    row = {
        "fingerprint": fingerprint,
        "source": FindingSource.TOXIC_COMBO.value,
        "rule_id": pattern_id,
        "title": title,
        "description": description,
        "severity": FindingSeverity.CRITICAL.value,
        "ssvc_action": SsvcAction.IMMEDIATE.value,
        "exposure": Exposure.INTERNET.value,
        "trust_graph_node_ids": node_ids,
        **path_data,
    }
    db.merge(
        FindingRow(
            fingerprint=fingerprint,
            tenant_id=tenant_id,
            source=FindingSource.TOXIC_COMBO.value,
            rule_id=pattern_id,
            title=title,
            description=description,
            severity=FindingSeverity.CRITICAL.value,
            ssvc_action=SsvcAction.IMMEDIATE.value,
            exposure=Exposure.INTERNET.value,
            canonical_key=node_ids[0],
            trust_graph_node_ids=node_ids,
            path_edges=path_data["path_edges"],
            risk_score=path_data["risk_score"],
            score_breakdown=path_data["score_breakdown"],
            last_seen=now,
        )
    )
    return row
