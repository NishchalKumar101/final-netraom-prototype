# Postgres teaching labs (cspm_demo)

**Connect**

| Tool | How to connect |
|------|----------------|
| **Adminer** (browser) | Open [http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo](http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo) — **System must be PostgreSQL**, Server **`postgres`**, password **`student`**. Do not use MySQL. |
| **psql** (from your Mac) | `postgresql://student:student@localhost:5433/cspm_demo` (port **5433** is host-only; Adminer-in-Docker uses `postgres:5432`). |
| **Full demo user** | Adminer: user `demo` / `demo`; psql: `postgresql://demo:demo@localhost:5433/cspm_demo` |
| In-app lab | Learn → Postgres | via API | — | SELECT-only |

Load data first: Dashboard → **Load enterprise**, or `POST /demo/load` with `{"fixture":"enterprise"}`.

---

## Lab 1 — Inventory slice

```sql
SELECT display_name, resource_type, cloud, is_internet_exposed, graph_node_id
FROM assets
ORDER BY is_internet_exposed DESC NULLS LAST
LIMIT 20;
```

**Talking point:** This is what the Inventory page lists — one row per asset; `graph_node_id` is the join key to Neo4j.

---

## Lab 2 — Internet-exposed count by cloud

```sql
SELECT cloud, count(*) AS assets, sum(CASE WHEN is_internet_exposed THEN 1 ELSE 0 END) AS exposed
FROM assets
GROUP BY cloud
ORDER BY exposed DESC;
```

---

## Lab 3 — Critical CSPM findings

```sql
SELECT severity, rule_id, title, canonical_key
FROM findings
WHERE source = 'cspm' AND severity = 'critical'
ORDER BY rule_id
LIMIT 25;
```

**Talking point:** Misconfigs are evaluated on graph props but **stored** as flat finding rows for filters, RBAC, and ticketing.

---

## Lab 4 — Toxic combos (bridge to graph)

```sql
SELECT fingerprint, rule_id, title, trust_graph_node_ids, path_edges
FROM findings
WHERE source = 'toxic-combo'
ORDER BY severity DESC
LIMIT 5;
```

Copy a value from `trust_graph_node_ids` → use in Neo4j Browser or Graph lab to expand the path.

---

## Lab 5 — Same rule, two sources

```sql
SELECT source, count(*) AS n, count(DISTINCT rule_id) AS rules
FROM findings
GROUP BY source;
```

Compare `cspm` vs `toxic-combo` volumes after enterprise load.

---

## Lab 6 — Find an asset by name

```sql
SELECT asset_id, display_name, graph_node_id, resource_type
FROM assets
WHERE display_name ILIKE '%upload%'
LIMIT 10;
```

Use `graph_node_id` on the Asset detail page URL or `/graph/nodes/{id}/neighborhood`.

---

## In-app query cookbook (beginner → advanced)

**Learn → Postgres lab** includes clickable templates (also via `GET /learn/sql/templates`):

| Level | Focus | Examples |
|-------|--------|----------|
| **Beginner** | Inventory & sources | B1 exposed inventory, B2 findings by source, B3 critical CSPM |
| **Medium** | Misconfigs & combos | M1 top CSPM rules, M3 API Gateway, M4 toxic by severity, M5 T2 paths |
| **Advanced** | Joins & JSONB paths | A1 CSPM on exposed assets, A2 path size, A3 T1–T9 rollup, A6 `path_edges` sample |

### Medium — top misconfiguration rules

```sql
SELECT rule_id, count(*) AS cnt
FROM findings WHERE source = 'cspm'
GROUP BY rule_id ORDER BY cnt DESC LIMIT 20;
```

### Advanced — correlate CSPM with exposed inventory

```sql
SELECT a.display_name, a.resource_type, f.rule_id, f.severity, f.title
FROM findings f
JOIN assets a ON a.graph_node_id = f.canonical_key AND a.tenant_id = f.tenant_id
WHERE f.source = 'cspm' AND a.is_internet_exposed = true
ORDER BY f.severity LIMIT 30;
```

### Advanced — toxic combo path complexity

```sql
SELECT rule_id, title,
       jsonb_array_length(trust_graph_node_ids) AS nodes,
       jsonb_array_length(path_edges) AS edges
FROM findings
WHERE source = 'toxic-combo'
ORDER BY nodes DESC LIMIT 20;
```
