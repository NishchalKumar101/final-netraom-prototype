# Portal integration (conceptual)

How this demo relates to a **production CNAPP portal** (optional reading after the student guide).

## Contract alignment

| Demo field | Typical production use |
|---|---|
| `Asset.graph_node_id` | Same as `trust_graph_node.v1.node_id` on inventory rows |
| Edge `kind` | Shared graph edge taxonomy (e.g. `allows_ingress`, `can_write`) |
| Finding `source=toxic-combo` | Multi-node finding with `trust_graph_node_ids` |
| Fingerprint | Stable hash over pattern id + sorted graph node ids |

## Suggested portal wiring

1. **Asset detail** — load asset from API; graph panel calls neighborhood BFF (`depth=2`).
2. **Finding detail** — for toxic combos, call attack-path endpoint for React Flow (or equivalent).
3. **Production graph** — Neptune/openCypher read path; same node/edge JSON shape as this demo’s Neo4j layer.

## Local demo vs production

| | This demo | Typical production |
|---|---|---|
| Graph | Neo4j in Docker | Managed graph (e.g. Neptune) |
| Findings | Postgres in Docker | Postgres (+ search index) |
| Ingest | `POST /demo/load` fixtures | Collector → normalizer → graph writer |

Demo UI has no auth; production portals use tenant-scoped API auth.
