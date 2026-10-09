from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from netraom_contracts.models.enums import CloudProvider, GraphEdgeKind, GraphNodeKind
from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode


class InventoryBundle:
    def __init__(
        self,
        *,
        tenant_id: UUID,
        cloud: CloudProvider,
        account_id: str,
        account_name: str,
    ) -> None:
        self.tenant_id = tenant_id
        self.cloud = cloud
        self.account_id = account_id
        self.run_id = uuid4()
        self.collected_at = datetime.now(tz=UTC)
        self.account_node_id = f"acct:{cloud.value}:{account_id}"
        self.nodes: dict[str, TrustGraphNode] = {}
        self.edges: dict[str, TrustGraphEdge] = {}
        self.assets: dict[str, dict[str, Any]] = {}
        self.add_node(
            self.account_node_id,
            GraphNodeKind.ACCOUNT,
            resource_type=f"{cloud.value}_account" if cloud == CloudProvider.AWS else "gcp_project",
            name=account_name,
            native_id=account_id,
            region="global",
        )

    def add_node(
        self,
        node_id: str,
        kind: GraphNodeKind,
        *,
        resource_type: str,
        name: str | None = None,
        native_id: str | None = None,
        region: str | None = None,
        props: dict[str, Any] | None = None,
    ) -> TrustGraphNode:
        existing = self.nodes.get(node_id)
        if existing:
            if props:
                existing.props.update(props)
            if name and not existing.name:
                existing.name = name
            return existing
        node = TrustGraphNode(
            tenant_id=self.tenant_id,
            node_id=node_id,
            kind=kind,
            labels=[kind.value.title(), "TrustGraphNode"],
            cloud=self.cloud,
            resource_type=resource_type,
            name=name,
            native_id=native_id,
            region=region,
            props=props or {},
            last_seen=self.collected_at,
            last_scan_run_id=self.run_id,
            source_modules=["aws_read_only_collector" if self.cloud == CloudProvider.AWS else "gcp_read_only_collector"],
        )
        self.nodes[node_id] = node
        return node

    def add_asset(
        self,
        node_id: str,
        *,
        kind: GraphNodeKind,
        resource_type: str,
        name: str,
        region: str | None,
        props: dict[str, Any],
        native_id: str | None = None,
    ) -> None:
        self.add_node(
            node_id,
            kind,
            resource_type=resource_type,
            name=name,
            native_id=native_id,
            region=region,
            props=props,
        )
        self.assets[node_id] = {
            "asset_id": str(uuid5(NAMESPACE_URL, f"netraom-cloud:{self.tenant_id}:{node_id}")),
            "canonical_key": node_id,
            "graph_node_id": node_id,
            "display_name": name,
            "cloud": self.cloud.value,
            "resource_type": resource_type,
            "region": region,
            "is_internet_exposed": bool(props.get("is_internet_exposed")),
            "props": props,
        }
        self.add_edge(
            GraphEdgeKind.OWNS,
            self.account_node_id,
            node_id,
            edge_key="account-ownership",
        )

    def add_edge(
        self,
        kind: GraphEdgeKind,
        src_id: str,
        dst_id: str,
        *,
        props: dict[str, Any] | None = None,
        edge_key: str = "",
    ) -> None:
        if src_id not in self.nodes or dst_id not in self.nodes:
            raise ValueError(f"Cannot add {kind.value} edge with a missing endpoint: {src_id} -> {dst_id}")
        identity = f"{self.tenant_id}:{kind.value}:{src_id}:{dst_id}:{edge_key}"
        edge_id = uuid5(UUID("b12e9cf1-4da8-4c14-9eeb-52b1d41c8514"), identity).hex
        if edge_id in self.edges:
            return
        self.edges[edge_id] = TrustGraphEdge(
            tenant_id=self.tenant_id,
            edge_id=edge_id,
            kind=kind,
            src_id=src_id,
            dst_id=dst_id,
            props=props or {},
            last_seen=self.collected_at,
            last_scan_run_id=self.run_id,
            source_modules=["aws_read_only_collector" if self.cloud == CloudProvider.AWS else "gcp_read_only_collector"],
        )

    def to_dict(self, *, scope: str) -> dict[str, Any]:
        return {
            "schema_version": "cloud_inventory_bundle.v1",
            "tenant_id": str(self.tenant_id),
            "run_id": str(self.run_id),
            "cloud": self.cloud.value,
            "account_id" if self.cloud == CloudProvider.AWS else "project_id": self.account_id,
            "scope": scope,
            "collected_at": self.collected_at.isoformat(),
            "assets": list(self.assets.values()),
            "nodes": [node.model_dump(mode="json") for node in self.nodes.values()],
            "edges": [edge.model_dump(mode="json") for edge in self.edges.values()],
        }


def stable_key(value: Any) -> str:
    """Build a stable suffix for distinct rules with otherwise identical endpoints."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()[:20]


def aws_resource_arn(service: str, region: str, account_id: str, resource: str) -> str:
    return f"arn:aws:{service}:{region}:{account_id}:{resource}"
