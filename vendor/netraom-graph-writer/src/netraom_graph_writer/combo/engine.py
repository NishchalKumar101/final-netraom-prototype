from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from netraom_contracts.models.enums import FindingCoverage, FindingSource, FindingStatus, TriageState
from netraom_contracts.models.finding import Finding
from netraom_contracts.models.graph import TrustGraphEdge, TrustGraphNode

from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph
from netraom_graph_writer.combo.patterns import ComboMatch, run_all_patterns
from netraom_graph_writer.combo.subgraph import neighborhood_node_ids


def _combo_fingerprint(pattern_id: str, node_ids: list[str]) -> str:
    material = f"{pattern_id}:{','.join(sorted(node_ids))}"
    return f"toxic-combo:{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def _coverage_for_match(g: NetworkXTrustGraph, node_ids: list[str]) -> FindingCoverage:
    for node_id in node_ids:
        props = g.node_props(node_id)
        if props.get("coverage") in {"unscanned", "external_to_tenant"}:
            return FindingCoverage.PARTIAL_MISSING_ACCOUNTS
    return FindingCoverage.COMPLETE


def _related_asset_ids(
    node_ids: list[str],
    assets: list[dict[str, Any]],
) -> list[str]:
    keys = set(node_ids)
    related: list[str] = []
    for row in assets:
        ck = row.get("canonical_key") or row.get("graph_node_id")
        if ck and ck in keys:
            asset_id = row.get("asset_id")
            if asset_id:
                related.append(str(asset_id))
    return related


def _related_cspm_finding_ids(
    node_ids: list[str],
    cspm_findings: list[dict[str, Any]],
) -> list[str]:
    keys = set(node_ids)
    related: list[str] = []
    for row in cspm_findings:
        if row.get("source") != "cspm":
            continue
        ck = row.get("canonical_key")
        if ck and ck in keys:
            fp = row.get("fingerprint")
            if fp:
                related.append(str(fp))
    return related


def combo_findings_from_matches(
    matches: list[ComboMatch],
    *,
    tenant_id: UUID,
    run_id: UUID,
    graph: NetworkXTrustGraph,
    cspm_findings: list[dict[str, Any]] | None = None,
    assets: list[dict[str, Any]] | None = None,
    evidence_ref: str | None = None,
) -> list[dict[str, Any]]:
    now = datetime.now(tz=UTC)
    rows: list[dict[str, Any]] = []
    cspm = cspm_findings or []
    asset_rows = assets or []
    for match in matches:
        coverage = _coverage_for_match(graph, match.node_ids)
        related = _related_cspm_finding_ids(match.node_ids, cspm)
        related_assets = _related_asset_ids(match.node_ids, asset_rows)
        finding = Finding(
            tenant_id=tenant_id,
            fingerprint=_combo_fingerprint(match.pattern_id, match.node_ids),
            source=FindingSource.TOXIC_COMBO,
            rule_id=match.pattern_id,
            title=match.title,
            description=match.description,
            severity=match.severity,
            ssvc_action=match.ssvc_action,
            exposure=match.exposure,
            status=FindingStatus.OPEN,
            triage_state=TriageState.NEW,
            evidence_ref=evidence_ref,
            trust_graph_node_ids=match.node_ids,
            coverage=coverage,
            first_seen=now,
            last_seen=now,
        )
        row = finding.model_dump(mode="json")
        if related:
            row["related_finding_ids"] = related
        if related_assets:
            row["related_asset_ids"] = related_assets
        row["why_it_matters"] = match.description
        row["last_scan_run_id"] = str(run_id)
        rows.append(row)
    return rows


def evaluate_combos(
    nodes: list[TrustGraphNode],
    edges: list[TrustGraphEdge],
    *,
    tenant_id: UUID,
    run_id: UUID,
    evidence_ref: str | None = None,
    cspm_findings: list[dict[str, Any]] | None = None,
    assets: list[dict[str, Any]] | None = None,
    pattern_ids: list[str] | None = None,
    dirty_node_ids: list[str] | None = None,
    max_hops: int = 4,
    trigger: str = "sweep",
) -> list[dict[str, Any]]:
    graph = NetworkXTrustGraph()
    graph.load(nodes, edges)
    allowed: set[str] | None = None
    if trigger == "incremental" and dirty_node_ids:
        allowed = neighborhood_node_ids(graph, dirty_node_ids, max_hops)
    elif trigger == "ondemand" and dirty_node_ids:
        allowed = neighborhood_node_ids(graph, dirty_node_ids, max_hops)
    matches = run_all_patterns(
        graph,
        pattern_ids=pattern_ids,
        allowed_node_ids=allowed,
    )
    return combo_findings_from_matches(
        matches,
        tenant_id=tenant_id,
        run_id=run_id,
        graph=graph,
        cspm_findings=cspm_findings,
        assets=assets,
        evidence_ref=evidence_ref,
    )
