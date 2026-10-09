# Student guide — CSPM Trust Graph demo

Local lab only. No AWS account required. Goal: see how **inventory + misconfigs (SQL)** and **attack paths (graph)** work together in a modern CNAPP-style workflow.

---

## 1. Prerequisites

- Docker Desktop (or Docker + Compose v2), ~4 GB free RAM
- Browser (Chrome/Firefox)

```bash
git clone <your-repo-url>
cd netraom-cspm-graph-demo
docker compose up -d --build
```

Wait ~1 minute, then load data:

```bash
curl -X POST http://localhost:8000/demo/load \
  -H 'Content-Type: application/json' \
  -d '{"fixture":"enterprise"}'
```

**Smaller lab** (easier to follow): Dashboard → **Small AWS lab**, or  
`curl -X POST http://localhost:8000/demo/load -d '{"fixture":"aws"}'`

---

## 2. URLs you will use

| Tool | URL | Notes |
|------|-----|--------|
| **Main UI** | http://localhost:5173 | Dashboard, Inventory, Findings, Learn |
| **API Swagger** | http://localhost:8000/docs | Customer-style read API only (no Learn/SQL/Cypher labs) |
| **Postgres (Adminer)** | http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo | Password `student`. [Login help](../docker/adminer/README.md) |
| **Neo4j Browser** | http://localhost:7474 | `neo4j` / `changeme` |

Demo tenant id (for Cypher): `11111111-1111-4111-8111-111111111111`

---

## 3. Recommended walkthrough (~60 min)

Do these in order once data is loaded.

### A. Portal story (UI)

1. **Dashboard** — confirm asset/finding counts after enterprise load.
2. **Inventory** — filter **Internet exposed**; open an API Gateway, load balancer, or bastion.
3. **Asset detail** — read **Portal** vs **Normalized (trust graph)** panels; open **View raw JSON** (raw → normalized → portal).
4. **Findings** — tab **toxic-combo**; filter **Critical**; open a row and study the **path graph**.
5. **Learn → Raw → normalized** — compare collector JSON to trust graph bundle (AWS/GCP fixtures).

### B. Postgres (facts)

1. **Learn → Postgres lab** — run template **B2** (findings by source), then **M5** (T2 combos).
2. **Adminer** — `SELECT title, rule_id, trust_graph_node_ids FROM findings WHERE source = 'toxic-combo' LIMIT 5;`

Ask yourself: *What lives in SQL that the UI lists and filters?*

### C. Graph (paths)

1. **Learn → Graph lab** — run **B4** (world SSH), then **M6** (T2 path).
2. **Neo4j Browser** — paste a `graph_node_id` from SQL and expand neighbors.

Ask yourself: *Why is a toxic combo not just one SQL join?*

### D. API (optional)

1. Open http://localhost:8000/docs
2. Execute **GET /assets** (`limit=10`, `internet_exposed=true`)
3. Execute **GET /findings** (`source=toxic-combo`, `severity=critical`)
4. Copy a `fingerprint` → **GET /findings/{fingerprint}/path**

---

## 4. Core concepts (remember these)

| Idea | Where in demo |
|------|----------------|
| **Inventory asset** | Postgres `assets` → Inventory UI |
| **Misconfiguration (CSPM)** | Postgres `findings` where `source=cspm` — one row per rule/asset |
| **Toxic combination** | Postgres `findings` where `source=toxic-combo` + `trust_graph_node_ids` / `path_edges` |
| **Trust graph** | Neo4j `TrustGraphNode` + `TRUST_EDGE` (edge `kind`: `allows_ingress`, `can_write`, …) |
| **Pipeline** | Raw collector JSON → normalized bundle → graph + Postgres → detection |

Details: [schema.md](./schema.md) · [scenarios.md](./scenarios.md)

---

## 5. Hands-on labs (copy-paste)

| Topic | Doc |
|-------|-----|
| SQL exercises | [teaching-sql.md](./teaching-sql.md) |
| Cypher exercises | [teaching-cypher.md](./teaching-cypher.md) |
| In-app query buttons | **Learn → Postgres lab** / **Graph lab** (Beginner → Advanced) |

Instructor-led timing: [teaching-session-runbook.md](./teaching-session-runbook.md)

---

## 6. After you finish the demo

You should be able to explain:

1. Why products use **two stores** (tables for lists/RBAC; graph for multi-hop paths).
2. The difference between a **CSPM finding** and a **toxic-combo finding**.
3. How `graph_node_id` links Inventory to Neo4j.

**Go deeper (optional, still in repo):**

- [portal-integration.md](./portal-integration.md) — conceptual production mapping (optional)
- [customer-api-plan.md](./customer-api-plan.md) — future public read API + Swagger at `/v1`
- Run tests: `pytest tests/` (see root README)

**Try on your own:**

- Reset and load **AWS + GCP** lab: `{"fixture":"both"}`
- Find one **T2** combo in UI, same row in Adminer, same nodes in Graph lab **M6**

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| Empty Inventory/Findings | Dashboard → Load enterprise, or curl `/demo/load` above |
| Graph empty on asset page | Reload demo data; hard-refresh browser |
| Adminer “Connection refused” | Use `?pgsql=postgres` URL; clear cookies for localhost:8081; see [adminer README](../docker/adminer/README.md) |
| API errors | `docker compose logs api --tail 50` |
| `student` login fails | DB created before read-only user: `docker compose down -v` then `up` again (wipes data) |

---

## 8. Doc map

| Audience | File |
|----------|------|
| **Students (start here)** | **This guide** |
| SQL / Cypher cookbooks | [teaching-sql.md](./teaching-sql.md), [teaching-cypher.md](./teaching-cypher.md) |
| Graph & table schema | [schema.md](./schema.md) |
| Expected lab outcomes | [scenarios.md](./scenarios.md) |
| Instructors | [teaching-session-runbook.md](./teaching-session-runbook.md) |
| Postgres login | [docker/adminer/README.md](../docker/adminer/README.md) |
| Vendored deps | [vendor/README.md](../vendor/README.md) |
