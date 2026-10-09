from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from netraom_contracts.models.enums import Exposure, FindingSeverity, FindingSource, SsvcAction
from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from sqlalchemy.orm import Session

from app.config import DEMO_TENANT_ID
from app.db.models import FindingRow

WORLD = "net:0.0.0.0/0"
GCP_WORLD = "ext:allUsers"


def _fp(rule_id: str, canonical_key: str, tenant_id: UUID) -> str:
    material = f"{rule_id}:{canonical_key}"
    if tenant_id != DEMO_TENANT_ID:
        material = f"{tenant_id}:{material}"
    return f"cspm:{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def evaluate_misconfigs(
    db: Session,
    *,
    tenant_id: UUID,
    nodes: list[TrustGraphNode],
    edges: list[TrustGraphEdge],
) -> list[dict[str, Any]]:
    now = datetime.now(tz=UTC)
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(**kwargs: Any) -> None:
        fp = kwargs["fingerprint"]
        if fp in seen:
            return
        seen.add(fp)
        findings.append(kwargs)

    for node in nodes:
        props = node.props or {}
        rt = node.resource_type or ""
        cloud = node.cloud.value if node.cloud else ""
        anon = props.get("anonymous_access", "none")
        is_public = bool(props.get("is_public") or props.get("is_internet_exposed"))
        encrypted = props.get("is_encrypted")
        name = node.name or node.node_id

        if rt in {"s3_bucket", "gcs_bucket"} and (anon in {"read", "write"} or is_public):
            rule = "gcp_storage_public_read" if cloud == "gcp" else "aws_s3_public_read"
            add(**_row(
                tenant_id=tenant_id,
                rule_id=rule,
                canonical_key=node.node_id,
                title="Object storage allows anonymous or public read",
                description=f"Storage `{name}` is publicly readable.",
                severity=FindingSeverity.HIGH,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt in {"s3_bucket", "gcs_bucket"} and anon == "write":
            add(**_row(
                tenant_id=tenant_id,
                rule_id="storage_public_anonymous_write",
                canonical_key=node.node_id,
                title="Object storage allows anonymous write",
                description=f"Storage `{name}` accepts unauthenticated writes (data poisoning / exfil risk).",
                severity=FindingSeverity.CRITICAL,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt in {"s3_bucket", "gcs_bucket"} and is_public and encrypted is False:
            add(**_row(
                tenant_id=tenant_id,
                rule_id="storage_public_unencrypted",
                canonical_key=node.node_id,
                title="Public storage without encryption",
                description=f"Storage `{name}` is public and not encrypted.",
                severity=FindingSeverity.HIGH,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt == "apigateway_rest_api" and (
            props.get("auth_type") == "NONE" or props.get("authorization") == "NONE"
        ):
            add(**_row(
                tenant_id=tenant_id,
                rule_id="aws_apigw_public_no_auth",
                canonical_key=node.node_id,
                title="API Gateway is public without authentication",
                description=f"API `{name}` is internet-exposed with no authorizer.",
                severity=FindingSeverity.CRITICAL,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt == "elbv2_load_balancer" and (
            props.get("scheme") == "internet-facing"
            or props.get("is_public")
            or props.get("load_balancer_type") in {"application", "network"}
            and is_public
        ):
            lb_type = props.get("load_balancer_type", "application")
            rule = "aws_nlb_public_internet" if lb_type == "network" else "aws_alb_public_internet"
            add(**_row(
                tenant_id=tenant_id,
                rule_id=rule,
                canonical_key=node.node_id,
                title=f"{'Network' if lb_type == 'network' else 'Application'} load balancer is internet-facing",
                description=f"Load balancer `{name}` accepts traffic from the internet.",
                severity=FindingSeverity.HIGH,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt in {"rds_instance", "rds_cluster"} and (is_public or props.get("is_internet_exposed")):
            add(**_row(
                tenant_id=tenant_id,
                rule_id="aws_rds_public_exposure",
                canonical_key=node.node_id,
                title="Database is reachable from the internet",
                description=f"RDS `{name}` is flagged as publicly accessible.",
                severity=FindingSeverity.CRITICAL,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt == "lambda_function" and is_public:
            add(**_row(
                tenant_id=tenant_id,
                rule_id="aws_lambda_public_invoke",
                canonical_key=node.node_id,
                title="Lambda function allows public invocation",
                description=f"Function `{name}` can be invoked without authentication.",
                severity=FindingSeverity.HIGH,
                node_ids=[node.node_id],
                now=now,
            ))

        if rt == "secretsmanager_secret" and props.get("is_critical_data"):
            # Informational tag only when paired with public compute — still useful in UI filters
            pass

    for edge in edges:
        if edge.kind.value != "allows_ingress":
            continue
        props = edge.props or {}
        cidr = str(props.get("cidr") or props.get("source_ranges") or "")
        port = props.get("port_from") or props.get("port")
        internet_open = cidr == "0.0.0.0/0" or (
            edge.dst_id in {WORLD, GCP_WORLD} and cidr in {"", "0.0.0.0/0"}
        )
        if not internet_open:
            continue

        port_num = int(port) if str(port).isdigit() else None
        if port_num == 22:
            rule = "gcp_firewall_world_ssh" if "gcp" in edge.src_id else "aws_sg_world_ssh"
            add(**_row(
                tenant_id=tenant_id,
                rule_id=rule,
                canonical_key=edge.src_id,
                title="Security control allows SSH from the internet",
                description=f"`{edge.src_id}` allows ingress on port 22 from the internet.",
                severity=FindingSeverity.CRITICAL,
                node_ids=[edge.src_id, edge.dst_id],
                now=now,
            ))
        elif port_num == 3389:
            add(**_row(
                tenant_id=tenant_id,
                rule_id="aws_sg_world_rdp",
                canonical_key=edge.src_id,
                title="Security control allows RDP from the internet",
                description=f"`{edge.src_id}` allows RDP (3389) from the internet.",
                severity=FindingSeverity.CRITICAL,
                node_ids=[edge.src_id, edge.dst_id],
                now=now,
            ))
        elif port_num in (443, 80):
            add(**_row(
                tenant_id=tenant_id,
                rule_id="aws_sg_world_web",
                canonical_key=f"{edge.src_id}:web",
                title="Security group allows web traffic from the internet",
                description=f"`{edge.src_id}` allows HTTP/S from 0.0.0.0/0.",
                severity=FindingSeverity.MEDIUM,
                node_ids=[edge.src_id, edge.dst_id],
                now=now,
            ))

    from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
    from app.graph_utils import assess_finding_graph_path

    graph = NetworkXTrustGraph()
    graph.load(nodes, edges)

    for row in findings:
        nids = row.get("trust_graph_node_ids", [])
        path_data = assess_finding_graph_path(graph, nids)
        row.update(path_data)
        db.merge(
            FindingRow(
                fingerprint=row["fingerprint"],
                tenant_id=tenant_id,
                source=FindingSource.CSPM.value,
                rule_id=row["rule_id"],
                title=row["title"],
                description=row["description"],
                severity=row["severity"],
                ssvc_action=row["ssvc_action"],
                exposure=row["exposure"],
                canonical_key=row.get("canonical_key"),
                trust_graph_node_ids=nids,
                path_edges=path_data["path_edges"],
                risk_score=path_data["risk_score"],
                score_breakdown=path_data["score_breakdown"],
                last_seen=now,
            )
        )
    db.commit()
    return findings


def _row(
    *,
    tenant_id: UUID,
    rule_id: str,
    canonical_key: str,
    title: str,
    description: str,
    severity: FindingSeverity,
    node_ids: list[str],
    now: datetime,
) -> dict[str, Any]:
    return {
        "fingerprint": _fp(rule_id, canonical_key, tenant_id),
        "tenant_id": str(tenant_id),
        "source": FindingSource.CSPM.value,
        "rule_id": rule_id,
        "title": title,
        "description": description,
        "severity": severity.value,
        "ssvc_action": SsvcAction.SCHEDULED.value
        if severity in {FindingSeverity.HIGH, FindingSeverity.MEDIUM}
        else SsvcAction.IMMEDIATE.value,
        "exposure": Exposure.INTERNET.value,
        "canonical_key": canonical_key,
        "trust_graph_node_ids": node_ids,
    }
