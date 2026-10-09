"""Read-only AWS and GCP inventory collectors for the demo Trust Graph."""

from app.cloud_collectors.aws import collect_aws_inventory
from app.cloud_collectors.gcp import collect_gcp_inventory

__all__ = ["collect_aws_inventory", "collect_gcp_inventory"]
