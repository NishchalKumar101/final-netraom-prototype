from __future__ import annotations

import copy
import json
from typing import Any

from app.config import FIXTURES_DIR
from app.fixture_gen import generate_enterprise_fixture
from app.ingest import load_fixture

RAW_FIXTURES_DIR = FIXTURES_DIR.parent / "raw"

INVENTORY_FIXTURES: list[dict[str, str]] = [
    {
        "id": "aws",
        "label": "AWS toxic SSH → bucket (small lab)",
        "normalized_file": "aws_toxic_ssh_bucket.json",
        "raw_file": "aws_toxic_ssh_bucket.json",
        "load_fixture_key": "aws",
    },
    {
        "id": "gcp",
        "label": "GCP toxic SSH → bucket (small lab)",
        "normalized_file": "gcp_toxic_ssh_bucket.json",
        "raw_file": "gcp_toxic_ssh_bucket.json",
        "load_fixture_key": "gcp",
    },
    {
        "id": "enterprise",
        "label": "Enterprise (~500 assets, generated)",
        "normalized_file": None,
        "raw_file": "enterprise_scan_sample.json",
        "load_fixture_key": "enterprise",
    },
]

PIPELINE_STAGES = [
    {
        "stage": "raw",
        "title": "Cloud inventory (collector)",
        "detail": "API/CAI-shaped JSON shards in S3 — demo_cloud_scan_bundle.v1.",
    },
    {
        "stage": "normalized",
        "title": "Normalizer → trust graph bundle",
        "detail": "assets[] + trust_graph_node.v1 + trust_graph_edge.v1 (same shape graph-writer ingests).",
    },
    {
        "stage": "graph",
        "title": "Graph writer",
        "detail": "MERGE TrustGraphNode / TRUST_EDGE in Neo4j (Neptune in production).",
    },
    {
        "stage": "postgres",
        "title": "Portal facts",
        "detail": "assets + findings tables for Inventory / Findings UI.",
    },
    {
        "stage": "detection",
        "title": "CSPM + toxic combos",
        "detail": "Rules on props/edges; multi-hop patterns → finding rows with path_edges.",
    },
]


def list_inventory_fixtures() -> dict[str, Any]:
    return {"fixtures": INVENTORY_FIXTURES, "pipeline": PIPELINE_STAGES}


def _load_raw(name: str) -> dict[str, Any]:
    path = RAW_FIXTURES_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"raw fixture not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_normalized(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"normalized fixture not found: {path}")
    return load_fixture(path)


def _truncate_normalized(payload: dict[str, Any], *, max_assets: int, max_nodes: int, max_edges: int) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    assets = out.get("assets") or []
    nodes = out.get("nodes") or []
    edges = out.get("edges") or []
    out["_preview"] = {
        "truncated": True,
        "totals": {
            "assets": len(assets),
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }
    out["assets"] = assets[:max_assets]
    out["nodes"] = nodes[:max_nodes]
    out["edges"] = edges[:max_edges]
    return out


def get_inventory_payload(
    fixture_id: str,
    *,
    include_raw: bool = True,
    include_normalized: bool = True,
    normalized_preview_limit: int = 25,
) -> dict[str, Any]:
    meta = next((f for f in INVENTORY_FIXTURES if f["id"] == fixture_id), None)
    if meta is None:
        raise ValueError(f"unknown fixture id: {fixture_id}")

    limit = max(5, min(normalized_preview_limit, 100))
    result: dict[str, Any] = {
        "fixture_id": fixture_id,
        "label": meta["label"],
        "load_fixture_key": meta["load_fixture_key"],
        "pipeline": PIPELINE_STAGES,
    }

    if include_raw and meta["raw_file"]:
        result["raw"] = _load_raw(meta["raw_file"])

    if include_normalized:
        if fixture_id == "enterprise":
            full = generate_enterprise_fixture(target_assets=500)
            result["normalized"] = _truncate_normalized(
                full,
                max_assets=limit,
                max_nodes=limit,
                max_edges=limit,
            )
        elif meta["normalized_file"]:
            full = _load_normalized(meta["normalized_file"])
            total_assets = len(full.get("assets") or [])
            total_nodes = len(full.get("nodes") or [])
            total_edges = len(full.get("edges") or [])
            if total_assets > limit or total_nodes > limit or total_edges > limit:
                result["normalized"] = _truncate_normalized(
                    full,
                    max_assets=limit,
                    max_nodes=limit,
                    max_edges=limit,
                )
            else:
                result["normalized"] = full
                result["normalized"]["_preview"] = {
                    "truncated": False,
                    "totals": {
                        "assets": total_assets,
                        "nodes": total_nodes,
                        "edges": total_edges,
                    },
                }
        else:
            result["normalized"] = None

    return result


def get_both_payload(*, normalized_preview_limit: int = 25) -> dict[str, Any]:
    return {
        "fixture_id": "both",
        "label": "AWS + GCP small labs",
        "load_fixture_key": "both",
        "pipeline": PIPELINE_STAGES,
        "clouds": [
            get_inventory_payload("aws", normalized_preview_limit=normalized_preview_limit),
            get_inventory_payload("gcp", normalized_preview_limit=normalized_preview_limit),
        ],
    }
