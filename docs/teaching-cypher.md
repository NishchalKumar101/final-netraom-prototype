# Neo4j Cypher teaching labs

**Browser:** http://localhost:7474 — user `neo4j`, password `changeme`.

**Demo tenant id** (always filter in class):

```text
11111111-1111-4111-8111-111111111111
```

In-app: **Learn → Graph lab** runs the same queries with write-blocking guards.

---

## Lab 0 — Counts by kind

```cypher
MATCH (n:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111' })
RETURN n.kind AS kind, count(*) AS c
ORDER BY c DESC;
```

---

## Lab 1 — Public resources

```cypher
MATCH (n:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111', kind: 'resource' })
WHERE n.props CONTAINS 'is_public'
RETURN n.name AS name, n.resource_type AS type, n.props AS props
LIMIT 25;
```

---

## Lab 2 — World SSH ingress

```cypher
MATCH (sg:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111' })
      -[r:TRUST_EDGE { kind: 'allows_ingress' }]->(w)
WHERE r.props CONTAINS '22'
RETURN sg.name AS control, w.name AS destination, r.props AS ingress
LIMIT 25;
```

---

## Lab 3 — T2-shaped path (SSH → role → writable bucket)

```cypher
MATCH (sg:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111' })
      -[i:TRUST_EDGE { kind: 'allows_ingress' }]->()
WHERE i.props CONTAINS '22'
MATCH (vm:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111' })
      -[:TRUST_EDGE { kind: 'has_sg' }]->(sg)
MATCH (role:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111', kind: 'identity' })
      -[:TRUST_EDGE { kind: 'attached_to' }]->(vm)
MATCH (role)-[:TRUST_EDGE { kind: 'can_write' }]->(bucket:TrustGraphNode { kind: 'resource' })
WHERE bucket.props CONTAINS 'is_public' OR bucket.props CONTAINS 'is_critical_data'
RETURN vm.name AS vm, role.name AS role, bucket.name AS bucket
LIMIT 10;
```

**Talking point:** This is why SQL joins break down — the path length and edge kinds vary.

---

## Lab 4 — Public API Gateway (auth NONE)

```cypher
MATCH (api:TrustGraphNode {
  tenant_id: '11111111-1111-4111-8111-111111111111',
  resource_type: 'apigateway_rest_api'
})
WHERE api.props CONTAINS 'NONE'
RETURN api.name AS api, api.props AS props
LIMIT 15;
```

---

## Lab 5 — Neighborhood from a node id (from Postgres)

Replace `<node_id>` with `graph_node_id` or an entry from `trust_graph_node_ids`:

```cypher
MATCH (n:TrustGraphNode {
  tenant_id: '11111111-1111-4111-8111-111111111111',
  node_id: '<node_id>'
})
MATCH (n)-[r:TRUST_EDGE]-(m)
RETURN n, r, m
LIMIT 50;
```

---

## Production bridge

Bounded patterns align with **netraom-graph-writer** toxic combo templates (T1–T9). Production uses Neptune openCypher with the same node/edge semantics written by the graph writer.

---

## In-app query cookbook (beginner → advanced)

**Learn → Graph lab** includes clickable templates (`GET /learn/cypher/templates`):

| Level | Focus | Examples |
|-------|--------|----------|
| **Beginner** | Graph shape | B1 node counts, B2 edge kinds, B3 public resources, B4 world SSH |
| **Medium** | CSPM + combo shapes | M1 API Gateway NONE, M2 public RDS, M4 can_write→bucket, M6 T2 path, M7 T1, M8 T9 |
| **Advanced** | Multi-hop toxic paths | A1 T5 compute→critical data, A3 APIGW→Lambda deploys, A4 LB serves backend, A5 SSH→bucket audit |

Use `r.kind = 'allows_ingress'` (and similar) on `TRUST_EDGE` relationships — edge semantics live in the `kind` property.

### Advanced — T5-style compute to critical data

```cypher
MATCH (vm:TrustGraphNode { tenant_id: '11111111-1111-4111-8111-111111111111' })
WHERE vm.props CONTAINS 'is_internet_exposed'
MATCH (vm)<-[:TRUST_EDGE { kind: 'attached_to' }]-(id:TrustGraphNode { kind: 'identity' })
MATCH (id)-[acc:TRUST_EDGE]->(data:TrustGraphNode { kind: 'resource' })
WHERE acc.kind IN ['can_read', 'can_write', 'can_admin']
  AND data.props CONTAINS 'is_critical_data'
RETURN vm.name, id.name, acc.kind, data.name
LIMIT 15;
```
