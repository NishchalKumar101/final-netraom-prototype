# CSPM Graph Demo API

FastAPI service: ingest fixtures → Neo4j + Postgres, misconfig rules, toxic-combo evaluation.

Python deps are vendored in `../vendor/` (see `vendor/README.md`).

Local run (monorepo siblings required):

```bash
cd backend
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://demo:demo@localhost:5433/cspm_demo
export NEO4J_URI=bolt://localhost:7687 NEO4J_PASSWORD=changeme
uvicorn app.main:app --reload
```

## Read-only cloud inventory

The optional collectors read these resource sets:

| Cloud | Resources |
|---|---|
| AWS | S3 buckets and bucket policy/public-access-block/ACL/encryption configuration; EC2 instances and security groups; IAM roles, attached policies, and instance profiles |
| GCP | Cloud Storage buckets and IAM; Compute Engine instances, zones, and ingress firewall rules; service accounts and project IAM policy |

Cloud calls are read-only and use the standard provider credential chain. Collection is scoped to one AWS account and EC2 region or one GCP project. AWS S3 buckets and IAM roles are account-level inventory, while EC2 instances and security groups are region-scoped. Collected assets and graph data are then **written** to this application's PostgreSQL and Neo4j stores and detection runs for the selected tenant. Re-running collection upserts stable resource and edge IDs; it does not delete resources that disappeared from the cloud scope.

### Required cloud permissions

Grant only read permissions for the selected account/project:

- **AWS**: `sts:GetCallerIdentity`; `s3:ListAllMyBuckets`, `s3:GetBucketLocation`, `s3:GetBucketPolicy`, `s3:GetBucketPolicyStatus`, `s3:GetPublicAccessBlock`, `s3:GetBucketAcl`, `s3:GetEncryptionConfiguration`; `ec2:DescribeInstances`, `ec2:DescribeSecurityGroups`; `iam:ListRoles`, `iam:ListAttachedRolePolicies`, `iam:GetInstanceProfile`, `iam:SimulatePrincipalPolicy`.
- **GCP**: `storage.buckets.list`, `storage.buckets.get`, `storage.buckets.getIamPolicy`; `compute.zones.list`, `compute.instances.list`, `compute.firewalls.list`; `iam.serviceAccounts.list`; `resourcemanager.projects.getIamPolicy`.

The AWS collector uses `boto3.Session()` and its normal environment/profile/role credential chain. Set `AWS_DEFAULT_REGION` or pass `--region`. The GCP collector uses Application Default Credentials (ADC), with a read-only Cloud Platform OAuth scope. Neither collector accepts credentials as command-line arguments or writes to cloud resources.

### Run

Install the backend with its optional cloud SDKs and make sure local PostgreSQL and Neo4j are available with the existing `DATABASE_URL`, `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` settings. From `backend/`, run:

```bash
pip install -e ".[dev,cloud]"

python -m app.cloud_collectors.cli aws --region us-east-1

python -m app.cloud_collectors.cli gcp --project-id my-gcp-project
```

Cloud collection uses the separate `CLOUD_TENANT_ID` setting (default `22222222-2222-4222-8222-222222222222`), which must differ from `DEMO_TENANT_ID`. This prevents `/demo/reset` and `/demo/load` from clearing or replacing cloud inventory. Existing demo endpoints remain scoped to `DEMO_TENANT_ID`; configure your tenant-aware consumers to use `CLOUD_TENANT_ID` to access the collected records. Asset IDs and non-demo finding fingerprints are tenant-scoped to prevent primary-key collisions across tenants. The AWS IAM policy simulation only materializes object read/write decisions for the S3 buckets collected in the selected scope. AWS bucket-level encryption configuration is reported; existing object-level encryption is not enumerated, and an absent bucket setting is left unknown rather than marked unencrypted. AWS account-level S3 Block Public Access settings and bucket-policy conditions are not evaluated. GCP instance exposure is approximated from public IPs and enabled, matching-network ingress rules with public source ranges; firewall deny rules and priority interactions, inherited Public Access Prevention, and IAM binding conditions are not evaluated. Attached GCP service-account OAuth scopes are recorded but are not used to constrain the generated IAM permission edges. Project and bucket IAM grants are mapped only for `roles/storage.objectViewer`, `roles/storage.legacyBucketReader`, `roles/storage.objectAdmin`, `roles/storage.admin`, `roles/storage.objectCreator`, and `roles/storage.legacyBucketWriter`.

These commands do not call or change `/demo/load`; synthetic fixture workflows remain available as before. `/demo/reset` and `/demo/load` only operate on `DEMO_TENANT_ID` and therefore leave the separately configured cloud inventory tenant untouched.
