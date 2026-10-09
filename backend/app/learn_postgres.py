from __future__ import annotations

import re
from typing import Any

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.models import AssetRow, FindingRow

ALLOWED_TABLES = frozenset({"assets", "findings"})

FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy)\b",
    re.IGNORECASE,
)


def postgres_schema(db: Session) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    for model, name in ((AssetRow, "assets"), (FindingRow, "findings")):
        columns = []
        for col in model.__table__.columns:
            columns.append(
                {
                    "name": col.name,
                    "type": str(col.type),
                    "nullable": col.nullable,
                    "primary_key": col.primary_key,
                }
            )
        tables.append(
            {
                "name": name,
                "purpose": _table_purpose(name),
                "columns": columns,
            }
        )
    return {"tables": tables}


def _table_purpose(name: str) -> str:
    if name == "assets":
        return "Portal-style inventory rows (one row per demo asset; graph_node_id links to Neo4j)."
    return "Misconfiguration and toxic-combo findings; trust_graph_node_ids and path_edges bridge to the graph."


def _cell(value: Any) -> Any:
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    if isinstance(value, dict):
        return value
    return value


def postgres_sample(db: Session, table: str, limit: int = 10) -> dict[str, Any]:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"table must be one of {sorted(ALLOWED_TABLES)}")
    limit = max(1, min(limit, 50))
    if table == "assets":
        rows = db.query(AssetRow).limit(limit).all()
        items = [
            {
                "asset_id": str(r.asset_id),
                "display_name": r.display_name,
                "resource_type": r.resource_type,
                "cloud": r.cloud,
                "is_internet_exposed": r.is_internet_exposed,
                "graph_node_id": r.graph_node_id,
            }
            for r in rows
        ]
    else:
        rows = db.query(FindingRow).limit(limit).all()
        items = [
            {
                "fingerprint": r.fingerprint,
                "source": r.source,
                "severity": r.severity,
                "rule_id": r.rule_id,
                "title": r.title,
                "trust_graph_node_ids": r.trust_graph_node_ids,
            }
            for r in rows
        ]
    return {"table": table, "limit": limit, "rows": items}


def validate_select_only(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL is empty")
    if FORBIDDEN_SQL.search(cleaned):
        raise ValueError("Only SELECT queries are allowed in the teaching lab")
    if not re.match(r"^\s*select\b", cleaned, re.IGNORECASE):
        raise ValueError("Query must start with SELECT")
    if ";" in cleaned:
        raise ValueError("Only a single statement is allowed")
    return cleaned


def run_select_sql(engine: Engine, sql: str, *, max_rows: int = 100) -> dict[str, Any]:
    safe = validate_select_only(sql)
    wrapped = f"SELECT * FROM ({safe}) AS _lab_sub LIMIT {max_rows}"
    with engine.connect() as conn:
        result = conn.execute(text(wrapped))
        columns = list(result.keys())
        rows = [
            {k: _cell(v) for k, v in dict(zip(columns, row, strict=True)).items()}
            for row in result.fetchall()
        ]
    return {"columns": columns, "rows": rows, "row_count": len(rows), "sql_executed": safe}
