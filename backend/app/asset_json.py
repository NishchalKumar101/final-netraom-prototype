from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from app.config import FIXTURES_DIR
from app.db.models import AssetRow
from app.learn_inventory import RAW_FIXTURES_DIR
from app.neo4j_client import Neo4jClient

RUN_ID = "44444444-4444-4444-8444-444444444444"


def _normalized_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.json"))


def _raw_files() -> list[Path]:
    return sorted(RAW_FIXTURES_DIR.glob("*.json"))


def _fixture_asset_and_node(
    graph_node_id: str,
    canonical_key: str,
) -> dict[str, Any] | None:
    for path in _normalized_files():
        with path.open(encoding="utf-8") as f:
            fx = json.load(f)
        asset_row = next(
            (a for a in fx.get("assets", []) if a.get("graph_node_id") == graph_node_id),
            None,
        )
        node_row = next(
            (n for n in fx.get("nodes", []) if n.get("node_id") == graph_node_id),
            None,
        )
        if asset_row or node_row:
            edges = [
                e
                for e in fx.get("edges", [])
                if e.get("src_id") == graph_node_id or e.get("dst_id") == graph_node_id
            ]
            return {
                "fixture_file": path.name,
                "source": "fixture",
                "asset_row": asset_row,
                "trust_graph_node": node_row,
                "trust_graph_edges": edges[:25],
            }
        if canonical_key:
            asset_row = next(
                (a for a in fx.get("assets", []) if a.get("canonical_key") == canonical_key),
                None,
            )
            if asset_row:
                nid = asset_row.get("graph_node_id")
                node_row = next((n for n in fx.get("nodes", []) if n.get("node_id") == nid), None)
                edges = [
                    e
                    for e in fx.get("edges", [])
                    if e.get("src_id") == nid or e.get("dst_id") == nid
                ]
                return {
                    "fixture_file": path.name,
                    "source": "fixture",
                    "asset_row": asset_row,
                    "trust_graph_node": node_row,
                    "trust_graph_edges": edges[:25],
                }
    return None


def _record_matches(record: dict[str, Any], row: AssetRow) -> bool:
    blob = json.dumps(record, default=str).lower()
    for token in (
        (row.display_name or "").lower(),
        row.canonical_key.lower(),
        row.graph_node_id.lower(),
        (row.graph_node_id.split("/")[-1] if row.graph_node_id else ""),
        (row.display_name or "").replace("-", "").lower(),
    ):
        if token and len(token) >= 3 and token in blob:
            return True
    return False


def find_raw_collector_record(row: AssetRow) -> dict[str, Any] | None:
    cloud = (row.cloud or "").lower()
    for path in _raw_files():
        with path.open(encoding="utf-8") as f:
            bundle = json.load(f)
        if cloud and bundle.get("cloud") and bundle.get("cloud") != cloud:
            continue
        for shard in bundle.get("shards", []):
            for record in shard.get("records", []):
                if _record_matches(record, row):
                    return {
                        "source": "raw_fixture",
                        "synthetic": False,
                        "raw_fixture_file": path.name,
                        "module": shard.get("module"),
                        "api": shard.get("api"),
                        "record": record,
                    }
    return None


def _trust_graph_node_v1(row: AssetRow, neo_node: dict[str, Any] | None) -> dict[str, Any]:
    props = dict(row.props or {})
    if neo_node and neo_node.get("props"):
        props = {**props, **neo_node["props"]}
    kind = "resource"
    if neo_node and neo_node.get("kind"):
        kind = neo_node["kind"]
    elif row.resource_type in {"iam_role", "iam.service_account"}:
        kind = "identity"
    return {
        "schema_version": "trust_graph_node.v1",
        "tenant_id": str(row.tenant_id),
        "node_id": row.graph_node_id,
        "kind": kind,
        "labels": ["TrustGraphNode", kind.title()],
        "cloud": row.cloud,
        "resource_type": row.resource_type,
        "name": row.display_name or neo_node.get("name") if neo_node else row.display_name,
        "region": row.region,
        "props": props,
        "status": "active",
        "last_scan_run_id": RUN_ID,
        "source_modules": ["demo_enterprise_gen"],
    }


def _trust_graph_edges_v1(neo: Neo4jClient, tenant_id: UUID, node_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
    hood = neo.get_neighborhood(tenant_id, node_id, depth=1)
    out: list[dict[str, Any]] = []
    for e in hood.get("edges", [])[:limit]:
        out.append(
            {
                "schema_version": "trust_graph_edge.v1",
                "tenant_id": str(tenant_id),
                "edge_id": e.get("edge_id") or f"{e.get('src_id')}->{e.get('dst_id')}",
                "kind": e.get("kind"),
                "src_id": e.get("src_id"),
                "dst_id": e.get("dst_id"),
                "props": e.get("props") or {},
                "status": "active",
                "last_scan_run_id": RUN_ID,
                "source_modules": ["demo_enterprise_gen"],
            }
        )
    return out


def _extract_idx(name: str | None) -> str | None:
    if not name:
        return None
    m = re.search(r"-(\d{3,5})$", name)
    return m.group(1) if m else None


def synthesize_raw_collector_record(row: AssetRow) -> dict[str, Any]:
    """API-shaped collector JSON for enterprise-generated assets (teaching)."""
    name = row.display_name or row.graph_node_id.split("/")[-1]
    idx = _extract_idx(name) or "000"
    rt = row.resource_type or ""
    cloud = (row.cloud or "aws").lower()
    exposed = bool(row.is_internet_exposed)
    props = row.props or {}

    if cloud == "gcp" and rt == "gce_instance":
        record: dict[str, Any] = {
            "name": name,
            "selfLink": row.graph_node_id,
            "networkInterfaces": [
                {
                    "networkIP": "10.0.0.5",
                    "accessConfigs": [{"type": "ONE_TO_ONE_NAT", "natIP": "203.0.113.20"}] if exposed else [],
                }
            ],
            "tags": {"items": ["ssh-bastion"]},
            "serviceAccounts": [
                {
                    "email": f"writer-{idx}@demo-gcp-project.iam.gserviceaccount.com",
                    "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
                }
            ],
        }
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "gcp.compute",
            "api": "compute.instances.get",
            "record": record,
            "normalizer_mapping": [
                "NAT + tags → is_internet_exposed on trust graph node",
                "Service account attachment → attached_to edge",
                "Firewall shard (separate API) → allows_ingress on port 22",
            ],
        }

    if cloud == "gcp" and rt == "gcs_bucket":
        bname = name or f"customer-data-{idx}"
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "gcp.storage",
            "api": "storage.buckets.get + getIamPolicy",
            "record": {
                "name": bname,
                "id": row.graph_node_id,
                "iamPolicy": {
                    "bindings": [{"role": "roles/storage.objectViewer", "members": ["allUsers"]}]
                },
            },
            "normalizer_mapping": ["allUsers binding → is_public / exposes edge"],
        }

    if cloud == "aws" and rt == "ec2_instance":
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "aws.ec2",
            "api": "DescribeInstances",
            "record": {
                "InstanceId": f"i-{name}",
                "InstanceArn": row.graph_node_id,
                "Tags": [{"Key": "Name", "Value": name}],
                "PublicIpAddress": "203.0.113.10" if exposed else None,
                "SecurityGroups": [{"GroupId": f"sg-upload-{idx}", "GroupName": f"sg-upload-{idx}"}],
                "IamInstanceProfile": {
                    "Arn": f"arn:aws:iam::123456789012:instance-profile/{name}-profile"
                },
            },
            "normalizer_mapping": [
                "PublicIpAddress → is_internet_exposed",
                "SecurityGroups → has_sg edges",
                "Instance profile → attached_to role",
            ],
        }

    if cloud == "aws" and rt == "s3_bucket":
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "aws.s3",
            "api": "GetBucketPolicy + GetPublicAccessBlock",
            "record": {
                "Name": name,
                "BucketArn": row.canonical_key,
                "Policy": {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"{row.canonical_key}/*",
                        }
                    ]
                }
                if exposed
                else None,
                "PublicAccessBlockConfiguration": {"BlockPublicPolicy": not exposed},
            },
            "normalizer_mapping": ["Public policy → anonymous_access / is_public props"],
        }

    if rt == "apigateway_rest_api":
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "aws.apigateway",
            "api": "GetRestApis + GetResources",
            "record": {
                "name": name,
                "endpointConfiguration": {"types": ["REGIONAL"]},
                "methods": [{"httpMethod": "ANY", "authorizationType": "NONE"}],
            },
            "normalizer_mapping": ["authorizationType NONE → CSPM aws_apigw_public_no_auth"],
        }

    if "rds" in rt:
        return {
            "source": "synthetic",
            "synthetic": True,
            "module": "aws.rds",
            "api": "DescribeDBInstances",
            "record": {
                "DBInstanceIdentifier": name,
                "PubliclyAccessible": exposed,
                "StorageEncrypted": props.get("is_encrypted", False),
            },
            "normalizer_mapping": ["PubliclyAccessible → aws_rds_public_exposure finding"],
        }

    return {
        "source": "synthetic",
        "synthetic": True,
        "module": f"{cloud}.inventory",
        "api": "DescribeResource (generic)",
        "record": {
            "id": row.graph_node_id,
            "name": name,
            "resource_type": rt,
            "region": row.region,
            "internet_exposed": exposed,
            "tags": props,
        },
        "normalizer_mapping": [
            "Enterprise filler assets map 1:1 to trust_graph_node.v1 + assets table row",
            "See fixtures/raw/enterprise_scan_sample.json for shard layout",
        ],
    }


_GRAPH_PROP_KEYS = (
    "is_public",
    "is_internet_exposed",
    "is_encrypted",
    "is_critical_data",
    "anonymous_access",
    "privilege",
    "auth_type",
    "coverage",
)


def build_normalized_preview(row: AssetRow, neo: Neo4jClient) -> dict[str, Any]:
    """Lightweight trust-graph fields for asset detail (no raw collector)."""
    neo_node = neo.get_node(row.tenant_id, row.graph_node_id)
    node_v1 = _trust_graph_node_v1(row, neo_node)
    edges = _trust_graph_edges_v1(neo, row.tenant_id, row.graph_node_id, limit=12)
    props = dict(node_v1.get("props") or {})
    highlights = {k: props[k] for k in _GRAPH_PROP_KEYS if k in props}
    return {
        "schema_version": node_v1.get("schema_version"),
        "kind": node_v1.get("kind"),
        "node_id": node_v1.get("node_id"),
        "name": node_v1.get("name"),
        "source_modules": node_v1.get("source_modules"),
        "graph_props": props,
        "highlights": highlights,
        "edge_count": len(edges),
        "sample_edges": [
            {
                "kind": e.get("kind"),
                "src_id": e.get("src_id"),
                "dst_id": e.get("dst_id"),
                "props": e.get("props"),
            }
            for e in edges[:6]
        ],
    }


def build_asset_json_package(row: AssetRow, neo: Neo4jClient) -> dict[str, Any]:
    portal = {
        "asset_id": str(row.asset_id),
        "tenant_id": str(row.tenant_id),
        "graph_node_id": row.graph_node_id,
        "canonical_key": row.canonical_key,
        "display_name": row.display_name,
        "cloud": row.cloud,
        "resource_type": row.resource_type,
        "region": row.region,
        "is_internet_exposed": row.is_internet_exposed,
        "props": row.props,
    }
    neo_node = neo.get_node(row.tenant_id, row.graph_node_id)
    edges_v1 = _trust_graph_edges_v1(neo, row.tenant_id, row.graph_node_id)

    normalized = _fixture_asset_and_node(row.graph_node_id, row.canonical_key)
    if not normalized:
        normalized = {
            "fixture_file": None,
            "source": "neo4j",
            "asset_row": portal,
            "trust_graph_node": _trust_graph_node_v1(row, neo_node),
            "trust_graph_edges": edges_v1,
        }
    elif normalized.get("source") == "fixture" and not normalized.get("trust_graph_edges") and edges_v1:
        normalized["trust_graph_edges"] = edges_v1
        normalized["neo4j_edges_merged"] = True

    raw = find_raw_collector_record(row)
    note = None
    if not raw:
        raw = synthesize_raw_collector_record(row)
        note = (
            "Synthetic collector record for enterprise-generated asset — same API shape as "
            "fixtures/raw/*.json. Matches how normalizer would map this resource type."
        )

    return {
        "portal_asset": portal,
        "normalized": normalized,
        "neo4j_node": neo_node,
        "raw_collector": raw,
        "note": note,
    }
