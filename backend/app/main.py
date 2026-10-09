from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.combos import evaluate_and_persist_combos
from app.asset_json import build_asset_json_package, build_normalized_preview
from app.asset_filters import (
    ASSET_CATEGORIES,
    CATEGORY_LABELS,
    apply_asset_filters,
    asset_sort_column,
)
from app.config import DEMO_TENANT_ID, FIXTURES_DIR
from app.db.models import AssetRow, FindingRow
from app.db.session import get_db
from app.fixture_gen import generate_enterprise_fixture
from app.ingest import ingest_fixture, ingest_fixture_dict
from app.misconfig import evaluate_misconfigs
from app.db.session import engine
from app.learn_cypher import CYPHER_TEMPLATES, graph_stats, run_cypher_lab
from app.learn_inventory import get_both_payload, get_inventory_payload, list_inventory_fixtures
from app.learn_postgres import postgres_sample, postgres_schema, run_select_sql, validate_select_only
from app.learn_sql_templates import SQL_TEMPLATES
from app.neo4j_client import Neo4jClient
from app.graph_utils import ordered_route_node_ids

app = FastAPI(title="CSPM Trust Graph Demo", version="0.1.0")

# Teaching labs (UI + markdown docs); omitted from /docs and /openapi.json.
learn_router = APIRouter(prefix="/learn", include_in_schema=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_neo4j: Neo4jClient | None = None


def neo4j_client() -> Neo4jClient:
    global _neo4j
    if _neo4j is None:
        _neo4j = Neo4jClient()
    return _neo4j


@app.on_event("startup")
def _startup() -> None:
    neo = neo4j_client()
    with neo._driver.session() as session:  # noqa: SLF001
        session.run(
            "CREATE CONSTRAINT trust_graph_node_id IF NOT EXISTS "
            "FOR (n:TrustGraphNode) REQUIRE (n.tenant_id, n.node_id) IS UNIQUE"
        )


class LoadRequest(BaseModel):
    fixture: str = "aws"


FIXTURE_MAP = {
    "aws": "aws_toxic_ssh_bucket.json",
    "gcp": "gcp_toxic_ssh_bucket.json",
    "both": "both",
    "enterprise": "enterprise",
}


def _run_detection(
    db: Session,
    neo: Neo4jClient,
    *,
    tenant_id: UUID = DEMO_TENANT_ID,
    nodes: list,
    edges: list,
    run_id: UUID,
    all_patterns: bool,
    demo_patterns: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cspm = evaluate_misconfigs(db, tenant_id=tenant_id, nodes=nodes, edges=edges)
    assets = [
        {
            "asset_id": str(r.asset_id),
            "canonical_key": r.canonical_key,
            "graph_node_id": r.graph_node_id,
        }
        for r in db.query(AssetRow).filter(AssetRow.tenant_id == tenant_id).all()
    ]
    combos = evaluate_and_persist_combos(
        db,
        neo,
        tenant_id=tenant_id,
        run_id=run_id,
        nodes=nodes,
        edges=edges,
        cspm_findings=cspm,
        assets=assets,
        all_patterns=all_patterns,
        include_demo_patterns=demo_patterns,
    )
    return cspm, combos


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)) -> dict[str, str]:
    neo = neo4j_client()
    neo.clear_tenant(DEMO_TENANT_ID)
    db.query(FindingRow).filter(FindingRow.tenant_id == DEMO_TENANT_ID).delete()
    db.query(AssetRow).filter(AssetRow.tenant_id == DEMO_TENANT_ID).delete()
    db.commit()
    return {"status": "reset", "tenant_id": str(DEMO_TENANT_ID)}


@app.post("/demo/load")
def demo_load(body: LoadRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    neo = neo4j_client()
    demo_reset(db)
    key = body.fixture.lower()
    if key not in FIXTURE_MAP:
        raise HTTPException(400, f"fixture must be one of {list(FIXTURE_MAP)}")

    all_nodes: list = []
    all_edges: list = []
    run_id: UUID | None = None
    all_patterns = key in {"enterprise", "both"}
    demo_patterns = key == "enterprise"

    if key == "enterprise":
        fixture = generate_enterprise_fixture(target_assets=500)
        nodes, edges, fixture = ingest_fixture_dict(db, neo, fixture)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        run_id = UUID(str(fixture["run_id"]))
    else:
        files = (
            ["aws_toxic_ssh_bucket.json", "gcp_toxic_ssh_bucket.json"]
            if key == "both"
            else [FIXTURE_MAP[key]]
        )
        for name in files:
            path = FIXTURES_DIR / name
            if not path.is_file():
                raise HTTPException(404, f"fixture not found: {path}")
            nodes, edges, fixture = ingest_fixture(db, neo, path)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
            run_id = UUID(str(fixture["run_id"]))

    assert run_id is not None
    cspm, combos = _run_detection(
        db,
        neo,
        nodes=all_nodes,
        edges=all_edges,
        run_id=run_id,
        all_patterns=all_patterns,
        demo_patterns=demo_patterns,
    )
    asset_count = db.query(AssetRow).filter(AssetRow.tenant_id == DEMO_TENANT_ID).count()
    return {
        "tenant_id": str(DEMO_TENANT_ID),
        "nodes": len(all_nodes),
        "edges": len(all_edges),
        "assets": asset_count,
        "misconfig_findings": len(cspm),
        "combo_findings": len(combos),
    }


@app.get("/assets/facets")
def asset_facets(db: Session = Depends(get_db)) -> dict[str, Any]:
    base = db.query(AssetRow).filter(AssetRow.tenant_id == DEMO_TENANT_ID)
    rows = base.all()
    by_cloud: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_category: dict[str, int] = {k: 0 for k in ASSET_CATEGORIES}
    exposed = 0
    for r in rows:
        if r.cloud:
            by_cloud[r.cloud] = by_cloud.get(r.cloud, 0) + 1
        if r.resource_type:
            by_type[r.resource_type] = by_type.get(r.resource_type, 0) + 1
            for cat, types in ASSET_CATEGORIES.items():
                if r.resource_type in types:
                    by_category[cat] += 1
        if r.is_internet_exposed:
            exposed += 1
    return {
        "total": len(rows),
        "internet_exposed": exposed,
        "by_cloud": by_cloud,
        "by_resource_type": dict(sorted(by_type.items(), key=lambda x: (-x[1], x[0]))),
        "by_category": by_category,
        "categories": [{"id": k, "label": CATEGORY_LABELS[k]} for k in ASSET_CATEGORIES],
    }


@app.get("/assets")
def list_assets(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    cloud: str | None = Query(None),
    category: str | None = Query(None, description="compute|storage|serverless|database|network|identity|api|secrets"),
    resource_type: str | None = Query(None),
    internet_exposed: bool | None = Query(None),
    sort: str = Query("name", pattern="^(name|type|cloud|region|exposed)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    base = db.query(AssetRow).filter(AssetRow.tenant_id == DEMO_TENANT_ID)
    base = apply_asset_filters(
        base,
        q=q,
        cloud=cloud,
        category=category,
        resource_type=resource_type,
        internet_exposed=internet_exposed,
    )
    total = base.count()
    col = asset_sort_column(sort)
    ordering = col.asc() if order == "asc" else col.desc()
    rows = base.order_by(ordering, AssetRow.display_name).offset(offset).limit(limit).all()
    return {"items": [_asset_dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/assets/by-node/{graph_node_id:path}")
def asset_by_graph_node(graph_node_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = (
        db.query(AssetRow)
        .filter(AssetRow.tenant_id == DEMO_TENANT_ID, AssetRow.graph_node_id == graph_node_id)
        .one_or_none()
    )
    if not row:
        raise HTTPException(404, "no inventory asset for this graph node")
    return _asset_dict(row)


@app.get("/assets/{asset_id}")
def get_asset(asset_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = (
        db.query(AssetRow)
        .filter(AssetRow.tenant_id == DEMO_TENANT_ID, AssetRow.asset_id == asset_id)
        .one_or_none()
    )
    if not row:
        raise HTTPException(404, "asset not found")
    neo = neo4j_client()
    payload = _asset_dict(row)
    payload["normalized"] = build_normalized_preview(row, neo)
    return payload


@app.get("/assets/{asset_id}/json")
def get_asset_json(asset_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = (
        db.query(AssetRow)
        .filter(AssetRow.tenant_id == DEMO_TENANT_ID, AssetRow.asset_id == asset_id)
        .one_or_none()
    )
    if not row:
        raise HTTPException(404, "asset not found")
    neo = neo4j_client()
    return build_asset_json_package(row, neo)


@app.get("/graph/nodes/{node_id:path}/neighborhood")
def graph_neighborhood(
    node_id: str,
    depth: int = Query(2, ge=1, le=3),
) -> dict[str, Any]:
    neo = neo4j_client()
    return neo.get_neighborhood(DEMO_TENANT_ID, node_id, depth)


@app.get("/graph/schema")
def graph_schema() -> dict[str, Any]:
    return {
        "node_kinds": ["account", "identity", "resource", "network", "external"],
        "edge_kinds": [
            "owns",
            "in_subnet",
            "has_sg",
            "attached_to",
            "allows_ingress",
            "exposes",
            "can_read",
            "can_write",
            "can_admin",
            "deploys",
            "serves",
        ],
    }


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@app.get("/findings/facets")
def findings_facets(
    source: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    base = db.query(FindingRow).filter(FindingRow.tenant_id == DEMO_TENANT_ID)
    if source:
        base = base.filter(FindingRow.source == source)
    rows = base.all()
    by_severity: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for r in rows:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_rule[r.rule_id] = by_rule.get(r.rule_id, 0) + 1
    top_rules = sorted(by_rule.items(), key=lambda x: (-x[1], x[0]))[:15]
    return {
        "total": len(rows),
        "by_severity": by_severity,
        "top_rules": [{"rule_id": rid, "count": c} for rid, c in top_rules],
    }


@app.get("/findings")
def list_findings(
    source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    severity: str | None = Query(None),
    rule_id: str | None = Query(None),
    sort: str = Query("severity", pattern="^(severity|title|rule|risk_score)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    base = db.query(FindingRow).filter(FindingRow.tenant_id == DEMO_TENANT_ID)
    if source:
        base = base.filter(FindingRow.source == source)
    if severity:
        base = base.filter(FindingRow.severity == severity.lower())
    if rule_id:
        base = base.filter(FindingRow.rule_id == rule_id)
    if q:
        like = f"%{q.strip()}%"
        base = base.filter(FindingRow.title.ilike(like) | FindingRow.rule_id.ilike(like))
    total = base.count()
    if sort == "severity":
        all_rows = base.all()
        all_rows.sort(
            key=lambda r: (SEVERITY_ORDER.get(r.severity, 99), (r.title or "").lower()),
            reverse=order == "desc",
        )
        rows = all_rows[offset : offset + limit]
    elif sort == "risk_score":
        all_rows = base.all()
        all_rows.sort(
            key=lambda r: getattr(r, "risk_score", 0) or 0,
            reverse=order != "asc", # Default highest risk first
        )
        rows = all_rows[offset : offset + limit]
    else:
        col = FindingRow.title if sort == "title" else FindingRow.rule_id
        ordering = col.asc() if order == "asc" else col.desc()
        rows = base.order_by(ordering, FindingRow.title).offset(offset).limit(limit).all()
    node_map = _asset_lookup_by_nodes(
        db,
        [nid for r in rows for nid in (r.trust_graph_node_ids or [])],
    )
    items = [_finding_dict(r, node_map) for r in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/findings/{fingerprint}/path")
def finding_path(fingerprint: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.query(FindingRow).filter(FindingRow.fingerprint == fingerprint).one_or_none()
    if not row:
        raise HTTPException(404, "finding not found")
    neo = neo4j_client()
    node_ids = [str(n) for n in (row.trust_graph_node_ids or [])]
    if not node_ids and row.canonical_key:
        node_ids = [row.canonical_key]

    path_edges = row.path_edges or []
    attack_path_nodes = ordered_route_node_ids(path_edges)
    attack_path_edge_ids = (
        [str(edge["edge_id"]) for edge in path_edges]
        if attack_path_nodes and all(edge.get("edge_id") for edge in path_edges)
        else []
    )
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    for nid in node_ids:
        hood = neo.get_neighborhood(DEMO_TENANT_ID, nid, depth=2)
        for n in hood["nodes"]:
            nodes[n["node_id"]] = n
        for e in hood["edges"]:
            edges[e["edge_id"]] = e

    for nid in attack_path_nodes:
        if nid in nodes:
            continue
        hood = neo.get_neighborhood(DEMO_TENANT_ID, nid, depth=1)
        for n in hood["nodes"]:
            nodes[n["node_id"]] = n
        for e in hood["edges"]:
            edges[e["edge_id"]] = e

    for e in path_edges:
        edges[e.get("edge_id", f"{e.get('src_id')}->{e.get('dst_id')}")] = e

    related = _asset_lookup_by_nodes(db, list(nodes.keys()))
    return {
        "fingerprint": row.fingerprint,
        "title": row.title,
        "description": row.description,
        "source": row.source,
        "rule_id": row.rule_id,
        "severity": row.severity,
        "risk_score": getattr(row, "risk_score", 0) or 0,
        "score_breakdown": getattr(row, "score_breakdown", {}) or {},
        "node_ids": node_ids,
        "edges": list(edges.values()),
        "nodes": list(nodes.values()),
        "related_assets": list(related.values()),
        "attack_path_nodes": attack_path_nodes,
        "attack_path_edge_ids": attack_path_edge_ids,
        "attack_path_edges": path_edges if attack_path_edge_ids else [],
    }


def _asset_lookup_by_nodes(db: Session, node_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not node_ids:
        return {}
    rows = (
        db.query(AssetRow)
        .filter(AssetRow.tenant_id == DEMO_TENANT_ID, AssetRow.graph_node_id.in_(node_ids))
        .all()
    )
    return {r.graph_node_id: _asset_dict(r) for r in rows}


def _asset_dict(row: AssetRow) -> dict[str, Any]:
    return {
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


class SqlLabRequest(BaseModel):
    sql: str


class CypherLabRequest(BaseModel):
    cypher: str


@learn_router.get("/inventory/fixtures")
def learn_inventory_fixture_list() -> dict[str, Any]:
    data = list_inventory_fixtures()
    data["fixtures"] = [
        *data["fixtures"],
        {
            "id": "both",
            "label": "AWS + GCP small labs",
            "normalized_file": None,
            "raw_file": None,
            "load_fixture_key": "both",
        },
    ]
    return data


@learn_router.get("/inventory")
def learn_inventory(
    fixture: str = Query("aws", pattern="^(aws|gcp|both|enterprise)$"),
    preview_limit: int = Query(25, ge=5, le=100),
) -> dict[str, Any]:
    try:
        if fixture == "both":
            return get_both_payload(normalized_preview_limit=preview_limit)
        return get_inventory_payload(fixture, normalized_preview_limit=preview_limit)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@learn_router.get("/stats")
def learn_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    neo = neo4j_client()
    asset_total = db.query(AssetRow).filter(AssetRow.tenant_id == DEMO_TENANT_ID).count()
    finding_total = db.query(FindingRow).filter(FindingRow.tenant_id == DEMO_TENANT_ID).count()
    cspm = (
        db.query(FindingRow)
        .filter(FindingRow.tenant_id == DEMO_TENANT_ID, FindingRow.source == "cspm")
        .count()
    )
    combo = (
        db.query(FindingRow)
        .filter(FindingRow.tenant_id == DEMO_TENANT_ID, FindingRow.source == "toxic-combo")
        .count()
    )
    graph = graph_stats(neo, DEMO_TENANT_ID)
    return {
        "tenant_id": str(DEMO_TENANT_ID),
        "postgres": {
            "assets": asset_total,
            "findings": finding_total,
            "findings_cspm": cspm,
            "findings_toxic_combo": combo,
        },
        "neo4j": graph,
    }


@learn_router.get("/postgres/schema")
def learn_postgres_schema(db: Session = Depends(get_db)) -> dict[str, Any]:
    return postgres_schema(db)


@learn_router.get("/postgres/sample")
def learn_postgres_sample(
    table: str = Query(..., pattern="^(assets|findings)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return postgres_sample(db, table, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@learn_router.get("/sql/templates")
def learn_sql_templates() -> dict[str, Any]:
    return {"templates": SQL_TEMPLATES}


@learn_router.post("/sql")
def learn_sql(body: SqlLabRequest) -> dict[str, Any]:
    try:
        validate_select_only(body.sql)
        return run_select_sql(engine, body.sql, max_rows=100)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@learn_router.get("/cypher/templates")
def learn_cypher_templates() -> dict[str, Any]:
    return {"templates": CYPHER_TEMPLATES, "tenant_id": str(DEMO_TENANT_ID)}


@learn_router.post("/cypher")
def learn_cypher(body: CypherLabRequest) -> dict[str, Any]:
    neo = neo4j_client()
    try:
        return run_cypher_lab(neo, body.cypher)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


app.include_router(learn_router)


def _finding_dict(row: FindingRow, node_assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    path_edges = row.path_edges or []
    attack_path_nodes = ordered_route_node_ids(path_edges)
    attack_path_edge_ids = (
        [str(edge["edge_id"]) for edge in path_edges]
        if attack_path_nodes and all(edge.get("edge_id") for edge in path_edges)
        else []
    )
    related: list[dict[str, Any]] = []
    for nid in row.trust_graph_node_ids or []:
        if nid in node_assets:
            related.append(node_assets[nid])
    if not related and row.canonical_key and row.canonical_key in node_assets:
        related.append(node_assets[row.canonical_key])
    return {
        "fingerprint": row.fingerprint,
        "source": row.source,
        "rule_id": row.rule_id,
        "title": row.title,
        "description": row.description,
        "severity": row.severity,
        "ssvc_action": row.ssvc_action,
        "exposure": row.exposure,
        "canonical_key": row.canonical_key,
        "trust_graph_node_ids": row.trust_graph_node_ids,
        "path_edges": path_edges,
        "attack_path_nodes": attack_path_nodes,
        "attack_path_edge_ids": attack_path_edge_ids,
        "risk_score": getattr(row, "risk_score", 0) or 0,
        "score_breakdown": getattr(row, "score_breakdown", {}) or {},
        "related_assets": related,
    }
