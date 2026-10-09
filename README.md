# netraom-cspm-graph-demo

Local CSPM **Trust Graph** lab: synthetic cloud inventory → Neo4j → misconfiguration rules + toxic-combination paths → portal-style UI.

**Students:** read **[docs/student-guide.md](docs/student-guide.md)** (setup, URLs, walkthrough, after-demo).  
**Doc index:** [docs/README.md](docs/README.md)

Not deployed to AWS. **Synthetic inventory only** — demo tenant and account IDs are placeholders; compose passwords are for local lab use ([public-release-notes](docs/public-release-notes.md)). Standalone repo ([vendor/](vendor/README.md) includes trust-graph + combo code).

## Quick start

```bash
git clone <your-repo-url>
cd netraom-cspm-graph-demo
docker compose up -d --build
curl -X POST http://localhost:8000/demo/load -H 'Content-Type: application/json' -d '{"fixture":"enterprise"}'
open http://localhost:5173
```

| Service | URL |
|---------|-----|
| UI | http://localhost:5173 |
| API / Swagger | http://localhost:8000/docs |
| Adminer (Postgres) | http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo |
| Neo4j | http://localhost:7474 (`neo4j` / `changeme`) |

## What you will do in the UI

1. **Dashboard** — load enterprise (~500 assets) or a small AWS/GCP lab.
2. **Inventory** — exposed assets; asset detail shows portal + **normalized** graph fields.
3. **Findings** — CSPM vs **toxic-combo**; path overlay on combos.
4. **Learn** — raw → normalized JSON, Postgres lab, Cypher lab.

Concepts: [docs/schema.md](docs/schema.md) · Labs: [docs/teaching-sql.md](docs/teaching-sql.md), [docs/teaching-cypher.md](docs/teaching-cypher.md)

## Developers

```bash
pip install -e vendor/netraom-contracts
pip install -e vendor/netraom-graph-writer --no-deps
pip install -e "backend/.[dev]"
pytest tests/
```

Local API (Postgres + Neo4j via compose): see [backend/README.md](backend/README.md).

## Requirements

- Docker Desktop or Docker + Compose v2
- ~4 GB RAM for Neo4j + Postgres + API + UI
