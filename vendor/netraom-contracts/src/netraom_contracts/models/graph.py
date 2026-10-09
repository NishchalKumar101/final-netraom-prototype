from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from netraom_contracts.models.enums import CloudProvider, GraphEdgeKind, GraphNodeKind

GraphEntityStatus = Literal["active", "deleted"]
GraphConfidence = Literal["exact", "inferred", "heuristic"]

TRUST_GRAPH_LABEL = "TrustGraphNode"


class TrustGraphNode(BaseModel):
    """Node in the Netraom Trust Graph — cross-cloud property graph interchange."""

    schema_version: str = Field(default="trust_graph_node.v1")
    tenant_id: UUID
    node_id: str = Field(min_length=1, max_length=512)
    kind: GraphNodeKind
    labels: list[str] = Field(min_length=1, max_length=16)
    cloud: CloudProvider | None = None
    cloud_account_id: UUID | None = None
    region: str | None = Field(default=None, max_length=64)
    resource_type: str | None = Field(default=None, max_length=64)
    native_id: str | None = Field(default=None, max_length=512)
    name: str | None = Field(default=None, max_length=256)
    props: dict[str, Any] = Field(default_factory=dict)
    status: GraphEntityStatus = "active"
    last_seen: datetime
    last_scan_run_id: UUID
    source_modules: list[str] = Field(default_factory=list, max_length=16)

    model_config = {"extra": "forbid"}


class TrustGraphEdge(BaseModel):
    """Directed edge in the Trust Graph."""

    schema_version: str = Field(default="trust_graph_edge.v1")
    tenant_id: UUID
    edge_id: str = Field(min_length=8, max_length=64)
    kind: GraphEdgeKind
    src_id: str = Field(min_length=1, max_length=512)
    dst_id: str = Field(min_length=1, max_length=512)
    props: dict[str, Any] = Field(default_factory=dict)
    status: GraphEntityStatus = "active"
    last_seen: datetime
    last_scan_run_id: UUID
    source_modules: list[str] = Field(default_factory=list, max_length=16)

    model_config = {"extra": "forbid"}


class TrustGraphSnapshot(BaseModel):
    """Immutable Trust Graph snapshot manifest (S3)."""

    schema_version: str = Field(default="trust_graph_snapshot.v1")
    tenant_id: UUID
    run_id: UUID
    created_at: datetime
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes_ref: str = Field(pattern=r"^s3://")
    edges_ref: str = Field(pattern=r"^s3://")
    source_runs: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class TrustGraphPointer(BaseModel):
    """Points readers at the current Trust Graph snapshot for a tenant."""

    schema_version: str = Field(default="1")
    tenant_id: UUID
    manifest_ref: str = Field(pattern=r"^s3://")
    as_of: datetime
    run_id: UUID
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)

    model_config = {"extra": "forbid"}
