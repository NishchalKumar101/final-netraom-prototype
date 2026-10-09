from __future__ import annotations

from sqlalchemy.orm import Query

from app.db.models import AssetRow

ASSET_CATEGORIES: dict[str, list[str]] = {
    "compute": ["ec2_instance", "gce_instance"],
    "storage": ["s3_bucket", "gcs_bucket"],
    "serverless": ["lambda_function", "cloud_function", "cloud_run_service"],
    "database": ["rds_instance", "rds_cluster", "dynamodb_table", "redshift_cluster"],
    "network": [
        "elbv2_load_balancer",
        "security_group",
        "compute.firewall",
        "subnet",
        "vpc",
    ],
    "identity": ["iam_role", "iam.service_account"],
    "api": ["apigateway_rest_api"],
    "secrets": ["secretsmanager_secret"],
}

CATEGORY_LABELS = {
    "compute": "VMs / compute",
    "storage": "Buckets / storage",
    "serverless": "Functions",
    "database": "Databases",
    "network": "Network & LB",
    "identity": "Identity",
    "api": "API Gateway",
    "secrets": "Secrets",
}


def resource_types_for_category(category: str | None) -> list[str] | None:
    if not category or category == "all":
        return None
    return ASSET_CATEGORIES.get(category)


def apply_asset_filters(
    query: Query,
    *,
    q: str | None,
    cloud: str | None,
    category: str | None,
    resource_type: str | None,
    internet_exposed: bool | None,
) -> Query:
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            AssetRow.display_name.ilike(like)
            | AssetRow.canonical_key.ilike(like)
            | AssetRow.resource_type.ilike(like)
        )
    if cloud:
        query = query.filter(AssetRow.cloud == cloud.lower())
    if resource_type:
        query = query.filter(AssetRow.resource_type == resource_type)
    elif category:
        types = resource_types_for_category(category)
        if types:
            query = query.filter(AssetRow.resource_type.in_(types))
    if internet_exposed is True:
        query = query.filter(AssetRow.is_internet_exposed.is_(True))
    elif internet_exposed is False:
        query = query.filter(AssetRow.is_internet_exposed.is_(False))
    return query


def asset_sort_column(sort: str):
    mapping = {
        "name": AssetRow.display_name,
        "type": AssetRow.resource_type,
        "cloud": AssetRow.cloud,
        "region": AssetRow.region,
        "exposed": AssetRow.is_internet_exposed,
    }
    return mapping.get(sort, AssetRow.display_name)
