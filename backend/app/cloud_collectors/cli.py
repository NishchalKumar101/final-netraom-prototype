from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.cloud_collectors import collect_aws_inventory, collect_gcp_inventory
from app.config import CLOUD_TENANT_ID
from app.db.session import SessionLocal
from app.ingest import ingest_fixture_dict
from app.main import _run_detection
from app.neo4j_client import Neo4jClient


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect read-only AWS/GCP inventory and ingest it into the local CSPM graph."
    )
    subparsers = parser.add_subparsers(dest="cloud", required=True)
    aws = subparsers.add_parser("aws", help="Collect S3, EC2, security groups, and IAM roles.")
    aws.add_argument("--region", help="AWS region (defaults to the standard AWS session region).")
    gcp = subparsers.add_parser("gcp", help="Collect GCS, GCE, firewall, and service-account inventory.")
    gcp.add_argument("--project-id", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.cloud == "aws":
        bundle = collect_aws_inventory(CLOUD_TENANT_ID, region=args.region)
    else:
        bundle = collect_gcp_inventory(CLOUD_TENANT_ID, project_id=args.project_id)

    db = SessionLocal()
    neo4j: Neo4jClient | None = None
    try:
        neo4j = Neo4jClient()
        nodes, edges, _ = ingest_fixture_dict(db, neo4j, bundle)
        cspm, combos = _run_detection(
            db,
            neo4j,
            tenant_id=CLOUD_TENANT_ID,
            nodes=nodes,
            edges=edges,
            run_id=UUID(bundle["run_id"]),
            all_patterns=True,
            demo_patterns=True,
        )
        print(
            json.dumps(
                {
                    "cloud": bundle["cloud"],
                    "scope": bundle["scope"],
                    "assets_collected": len(bundle["assets"]),
                    "nodes_collected": len(nodes),
                    "edges_collected": len(edges),
                    "cspm_findings": len(cspm),
                    "toxic_combo_findings": len(combos),
                    "run_id": bundle["run_id"],
                },
                sort_keys=True,
            )
        )
    finally:
        db.close()
        if neo4j is not None:
            neo4j.close()


if __name__ == "__main__":
    main()
