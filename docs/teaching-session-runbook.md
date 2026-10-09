# Teaching session & demo runbook

**Students** should follow [student-guide.md](./student-guide.md) first. This runbook is for **instructors** (50–90 min). Local Docker only — no AWS.

---

## Before the session (15 min)

1. Clone the demo repo (standalone — includes `vendor/` dependencies):

   ```bash
   cd netraom-cspm-graph-demo
   docker compose up -d --build
   ```

2. Wait for health, then load data:

   ```bash
   curl -s -X POST http://localhost:8000/demo/load \
     -H 'Content-Type: application/json' \
     -d '{"fixture":"enterprise"}' | jq .
   ```

3. Open tabs (in order you will use them):

   | Tab | URL | Login |
   |-----|-----|-------|
   | Portal UI | http://localhost:5173 | — |
   | Learn overview | http://localhost:5173/learn | — |
   | Adminer | http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo | **System: PostgreSQL**, Server **`postgres`**, DB `cspm_demo`, password **student** (not MySQL; not `localhost:5433` in Server) |
   | Neo4j Browser | http://localhost:7474 | `neo4j` / `changeme` |

4. Optional reset between cohorts:

   ```bash
   curl -X POST http://localhost:8000/demo/reset
   curl -X POST http://localhost:8000/demo/load -H 'Content-Type: application/json' -d '{"fixture":"enterprise"}'
   ```

---

## Session agenda

### 1. Hook — why CSPM needs a graph (5 min)

- Show **Dashboard** counts after enterprise load (~500 assets, many findings).
- One sentence: CNAPP products combine **inventory + misconfig rules + multi-hop toxic combinations**.
- This demo splits **lists** (Postgres) and **paths** (Neo4j) like production Netraom (Neptune).

### 2. Raw → normalized (8 min)

- **Learn → Raw → normalized** — pick **AWS** lab; compare S3/SG/IAM shards to `assets` + `nodes` + `edges`.
- **Enterprise** — sample raw shard + truncated normalized preview; then Dashboard **Load enterprise**.

### 3. Portal UX — Inventory & Findings (10 min)

- **Inventory:** filter **Internet exposed**, sort by exposure; open any public load balancer or API Gateway asset.
- **Asset graph:** click neighbors — `allows_ingress`, `has_sg`, `can_write` edges.
- **Findings:** filter **Critical**; open a **toxic-combo** row; show path overlay vs a single-asset CSPM row.

**Talking point:** UI never asks students to write Cypher — it calls the API, which reads Postgres + Neo4j.

### 4. Postgres deep dive (15 min)

- **Adminer:** run Lab 4 from [teaching-sql.md](./teaching-sql.md) — toxic-combo rows with `trust_graph_node_ids` and `path_edges`.
- **Learn → Postgres lab:** run the default inventory SELECT; show API SELECT-only guard (try `DELETE` — rejected).
- Compare **demo** vs **student** login: student cannot mutate tables.

**Talking point:** Findings are the product’s “alert objects”; graph ids are denormalized for fast portal linking.

### 5. Neo4j deep dive (15 min)

- **Graph lab:** load **Lab 3 — T2-style path** template; run; compare columns to Postgres path JSON.
- **Neo4j Browser:** run Lab 0 counts; visualize Lab 5 neighborhood from a copied node id.

**Talking point:** Same tenant id everywhere; patterns are bounded (LIMIT) like production graph queries.

### 6. End-to-end story (10 min)

Walk one toxic combo:

1. Findings UI → pick fingerprint.
2. Postgres → same row in Adminer.
3. Cypher → path as edges.
4. Back to UI path view — same nodes.

### 7. Small labs (optional, 10 min)

- Dashboard → **Small AWS lab** for a minimal SSH→bucket story (easier whiteboard).
- Map to [docs/scenarios.md](./scenarios.md) expected fingerprints.

### 8. Q&A / production mapping (5–15 min)

- [docs/portal-integration.md](./portal-integration.md) — API shapes vs future portal.
- Graph writer + Neptune; Postgres remains system of record for findings list.

---

## Demo tips

- **Projector:** zoom browser 125%; use dark UI theme if room is bright.
- **If API is down:** `docker compose logs api --tail 50`; rebuild with `docker compose up -d --build api`.
- **If Postgres empty:** reload enterprise fixture; `student` role only exists on fresh volume — recreate with `docker compose down -v` (wipes data) if Adminer login fails.
- **Pacing:** 50 min = sections 1–5 only; 90 min = add small labs + Q&A.

---

## One-page cheat sheet (printable)

```text
Load:     POST localhost:8000/demo/load  {"fixture":"enterprise"}
UI:       localhost:5173
Learn:    localhost:5173/learn
Adminer:  localhost:8081/?pgsql=postgres&username=student&db=cspm_demo  (PostgreSQL, server postgres, pwd student)
Neo4j:    localhost:7474  neo4j/changeme
Tenant:   11111111-1111-4111-8111-111111111111

SQL:      findings WHERE source='toxic-combo' LIMIT 5
Cypher:   Graph lab → Lab 3 template
Portal:   Findings → Critical → toxic-combo → path graph
```

---

## Related docs

- [teaching-console-plan.md](./teaching-console-plan.md) — architecture and phases
- [teaching-sql.md](./teaching-sql.md) — Postgres labs
- [teaching-cypher.md](./teaching-cypher.md) — Cypher labs
- [schema.md](./schema.md) — table and graph model
