from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode
from sqlalchemy.orm import Session

from app.db.models import AssetRow
from app.neo4j_client import Neo4jClient


def asset_id_for(canonical_key: str) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"netraom-demo:{canonical_key}")


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_graph(fixture: dict[str, Any]) -> tuple[list[TrustGraphNode], list[TrustGraphEdge]]:
    nodes = [TrustGraphNode.model_validate(n) for n in fixture.get("nodes", [])]
    edges = [TrustGraphEdge.model_validate(e) for e in fixture.get("edges", [])]
    return nodes, edges


def upsert_assets(db: Session, fixture: dict[str, Any]) -> None:
    tenant_id = UUID(str(fixture["tenant_id"]))
    now = datetime.now(tz=UTC)
    for row in fixture.get("assets", []):
        ck = str(row["canonical_key"])
        aid = UUID(str(row.get("asset_id"))) if row.get("asset_id") else asset_id_for(ck)
        graph_node_id = str(row.get("graph_node_id") or ck)
        existing = (
            db.query(AssetRow)
            .filter(AssetRow.tenant_id == tenant_id, AssetRow.graph_node_id == graph_node_id)
            .one_or_none()
        )
        payload = AssetRow(
            asset_id=aid,
            tenant_id=tenant_id,
            graph_node_id=graph_node_id,
            canonical_key=ck,
            display_name=row.get("display_name") or row.get("name"),
            cloud=row.get("cloud"),
            resource_type=row.get("resource_type"),
            region=row.get("region"),
            is_internet_exposed=row.get("is_internet_exposed"),
            props=row.get("props") or {},
            last_seen=now,
        )
        if existing:
            existing.display_name = payload.display_name
            existing.cloud = payload.cloud
            existing.resource_type = payload.resource_type
            existing.region = payload.region
            existing.is_internet_exposed = payload.is_internet_exposed
            existing.props = payload.props
            existing.last_seen = now
        else:
            db.add(payload)


def ingest_fixture_dict(
    db: Session,
    neo4j: Neo4jClient,
    fixture: dict[str, Any],
) -> tuple[list[TrustGraphNode], list[TrustGraphEdge], dict[str, Any]]:
    nodes, edges = parse_graph(fixture)
    neo4j.upsert_graph(nodes, edges)
    upsert_assets(db, fixture)
    db.commit()
    return nodes, edges, fixture


def ingest_fixture(
    db: Session,
    neo4j: Neo4jClient,
    path: Path,
) -> tuple[list[TrustGraphNode], list[TrustGraphEdge], dict[str, Any]]:
    return ingest_fixture_dict(db, neo4j, load_fixture(path))
