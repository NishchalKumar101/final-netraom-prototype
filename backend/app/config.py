from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

DEMO_TENANT_ID = UUID(os.environ.get("DEMO_TENANT_ID", "11111111-1111-4111-8111-111111111111"))
CLOUD_TENANT_ID = UUID(os.environ.get("CLOUD_TENANT_ID", "22222222-2222-4222-8222-222222222222"))
if CLOUD_TENANT_ID == DEMO_TENANT_ID:
    raise ValueError("CLOUD_TENANT_ID must differ from DEMO_TENANT_ID to protect cloud inventory from demo resets.")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://demo:demo@localhost:5433/cspm_demo",
)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "changeme")
FIXTURES_DIR = Path(os.environ.get("FIXTURES_DIR", Path(__file__).resolve().parents[2] / "fixtures" / "normalized"))
