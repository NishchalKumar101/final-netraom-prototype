# Trust Graph schema (demo subset)

Aligned with `platform-contracts` schemas `trust_graph_node.v1` and `trust_graph_edge.v1`.

## Node kinds

| kind | Used for | Algorithm props |
|---|---|---|
| account | AWS account, GCP project | `cloud`, `native_id` |
| identity | IAM role, GCP service account | `privilege`: `narrow` \| `admin` |
| resource | S3, EC2, GCS, GCE | `is_public`, `is_internet_exposed`, `is_encrypted`, `is_critical_data`, `anonymous_access` |
| network | SG, subnet, firewall | `is_public` (subnet) |
| external | `allUsers`, public URL | `cidr`, `principal` |

## Edge kinds

| kind | Direction example |
|---|---|
| owns | account → resource |
| in_subnet | vm → subnet |
| has_sg | vm → security group / firewall |
| allows_ingress | sg → external CIDR |
| attached_to | role → vm |
| can_read / can_write / can_admin | identity → resource |
| exposes | bucket → external principal |

Neo4j labels: `TrustGraphNode`, relationship type `TRUST_EDGE` with property `kind`.
