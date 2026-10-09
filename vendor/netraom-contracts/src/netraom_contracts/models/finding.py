from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from netraom_contracts.models.enums import (
    CloudProvider,
    Disposition,
    Exposure,
    FindingCoverage,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    SsvcAction,
    TriageState,
)


class Finding(BaseModel):
    """Unified finding object — all modules write this shape."""

    tenant_id: UUID
    fingerprint: str = Field(min_length=8, max_length=128)
    source: FindingSource
    rule_id: str = Field(min_length=1, max_length=128)
    control_ids: list[str] = Field(default_factory=list)
    asset_id: UUID | None = None
    canonical_key: str | None = Field(default=None, max_length=512)
    cloud: CloudProvider | None = None
    cloud_account_id: UUID | None = None
    region: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=8192)
    severity: FindingSeverity
    ssvc_action: SsvcAction
    exposure: Exposure
    cvss_score: float | None = Field(default=None, ge=0, le=10)
    cve_ids: list[str] = Field(default_factory=list)
    status: FindingStatus = FindingStatus.OPEN
    disposition: Disposition | None = None
    triage_state: TriageState = TriageState.NEW
    priority: str | None = Field(default=None, pattern=r"^p[1-4]$")
    why_it_matters: str | None = Field(default=None, max_length=4096)
    remediation_guidance: str | None = Field(default=None, max_length=8192)
    evidence_ref: str | None = Field(default=None, pattern=r"^s3://")
    related_finding_ids: list[UUID] = Field(default_factory=list)
    related_asset_ids: list[UUID] = Field(default_factory=list)
    trust_graph_node_ids: list[str] = Field(default_factory=list, max_length=64)
    coverage: FindingCoverage | None = None
    first_seen: datetime
    last_seen: datetime
    last_verified: datetime | None = None
    occurrence_count: int = Field(default=1, ge=1)

    model_config = {"extra": "forbid"}
