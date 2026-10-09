# Demo scenarios

## Enterprise — `POST /demo/load {"fixture":"enterprise"}`

**~500 inventory assets** generated in-memory (not a static JSON file). Patterns repeat so you see **many** similar critical alerts.

| Pattern | What it models |
|---|---|
| Toxic SSH + narrow role + public/critical bucket | Core T1/T2/T5 combo (×12) |
| API Gateway `auth_type=NONE` → Lambda → DynamoDB | Public API, no auth (×12) |
| Internet ALB → EC2 → public/critical S3 | Public load balancer path (×12) |
| Internet NLB → EC2 + world SSH | Network LB exposure (×12) |
| Public RDS + world 5432 | T7-style database path (×12) |
| Public Lambda → Secrets Manager | T8-style (×12) |
| Anonymous-write S3 | Data poisoning / T1 input (×12) |
| GCP GCS + SSH + SA | Cross-cloud slice (×4) |
| Private EC2 + encrypted S3 | Safe filler to reach 500 assets |

**Demo-only toxic combos:** `D1_apigw_no_auth_to_sensitive_data`, `D2_public_lb_to_exposed_data`.

**Top misconfig rule IDs:** `aws_apigw_public_no_auth`, `aws_alb_public_internet`, `aws_nlb_public_internet`, `aws_rds_public_exposure`, `aws_lambda_public_invoke`, `aws_sg_world_ssh`, `storage_public_anonymous_write`, …

## Small labs

- `aws` — original hero SSH + bucket
- `gcp` — parallel GCS story
- `both` — aws + gcp files

## UI

- **Inventory:** search + pagination; click row → asset detail → graph neighbors (click-through).
- **Findings:** paginated alerts; click row → path graph; **Related assets** chips and graph nodes link to inventory when mapped.
