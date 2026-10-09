from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AssetRow(Base):
    __tablename__ = "assets"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    graph_node_id: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    cloud: Mapped[str | None] = mapped_column(String(16))
    resource_type: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    is_internet_exposed: Mapped[bool | None] = mapped_column(Boolean)
    props: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=UTC))


class FindingRow(Base):
    __tablename__ = "findings"

    fingerprint: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    ssvc_action: Mapped[str] = mapped_column(String(32), nullable=False)
    exposure: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_key: Mapped[str | None] = mapped_column(Text)
    trust_graph_node_ids: Mapped[list] = mapped_column(JSONB, default=list)
    path_edges: Mapped[list] = mapped_column(JSONB, default=list)
    risk_score: Mapped[int] = mapped_column(default=0)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="open")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=UTC))
