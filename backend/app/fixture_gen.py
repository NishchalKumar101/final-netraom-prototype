from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

TENANT = "11111111-1111-4111-8111-111111111111"
RUN = "44444444-4444-4444-8444-444444444444"
TS = "2026-09-11T12:00:00Z"
ACCT_AWS = "123456789012"
ACCT_GCP = "demo-gcp-project"
WORLD = "net:0.0.0.0/0"
G_ALL = "ext:allUsers"


def _asset_id(key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"netraom-demo:{key}"))


def _node(
    node_id: str,
    kind: str,
    *,
    cloud: str | None = None,
    resource_type: str | None = None,
    name: str | None = None,
    region: str = "ap-south-1",
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = ["TrustGraphNode"]
    if kind == "account":
        labels = ["Account", "TrustGraphNode"]
    elif kind == "identity":
        labels = ["Identity", "TrustGraphNode"]
    elif kind == "resource":
        labels = ["Resource", "TrustGraphNode"]
    elif kind == "network":
        labels = ["Network", "TrustGraphNode"]
    elif kind == "external":
        labels = ["ExternalAsset", "TrustGraphNode"]
    return {
        "schema_version": "trust_graph_node.v1",
        "tenant_id": TENANT,
        "node_id": node_id,
        "kind": kind,
        "labels": labels,
        "cloud": cloud,
        "resource_type": resource_type,
        "name": name,
        "region": region,
        "props": props or {},
        "status": "active",
        "last_seen": TS,
        "last_scan_run_id": RUN,
        "source_modules": ["demo_enterprise_gen"],
    }


def _edge(eid: str, kind: str, src: str, dst: str, props: dict[str, Any] | None = None) -> dict[str, Any]:
    edge_id = eid if len(eid) >= 8 else eid.ljust(8, "0")
    return {
        "schema_version": "trust_graph_edge.v1",
        "tenant_id": TENANT,
        "edge_id": edge_id,
        "kind": kind,
        "src_id": src,
        "dst_id": dst,
        "props": props or {"confidence": "exact"},
        "status": "active",
        "last_seen": TS,
        "last_scan_run_id": RUN,
        "source_modules": ["demo_enterprise_gen"],
    }


def _asset_row(
    node_id: str,
    *,
    name: str,
    cloud: str,
    resource_type: str,
    region: str,
    exposed: bool | None = None,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "asset_id": _asset_id(node_id),
        "canonical_key": node_id,
        "graph_node_id": node_id,
        "display_name": name,
        "cloud": cloud,
        "resource_type": resource_type,
        "region": region,
        "is_internet_exposed": exposed,
        "props": props or {},
    }


def _toxic_ssh_bucket_aws(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "ap-south-1"
    bucket = f"arn:aws:s3:::customer-uploads-{idx:03d}"
    vm = f"arn:aws:ec2:{reg}:{ACCT_AWS}:instance/upload-bastion-{idx:03d}"
    sg = f"arn:aws:ec2:{reg}:{ACCT_AWS}:security-group/sg-upload-{idx:03d}"
    subnet = f"arn:aws:ec2:{reg}:{ACCT_AWS}:subnet/subnet-public-{idx:03d}"
    role = f"arn:aws:iam::{ACCT_AWS}:role/upload-writer-{idx:03d}"
    nodes.extend(
        [
            _node(bucket, "resource", cloud="aws", resource_type="s3_bucket", name=f"customer-uploads-{idx:03d}",
                  props={"is_public": True, "is_internet_exposed": True, "is_encrypted": False,
                         "is_critical_data": True, "anonymous_access": "read"}),
            _node(vm, "resource", cloud="aws", resource_type="ec2_instance", name=f"upload-bastion-{idx:03d}",
                  props={"is_internet_exposed": True}),
            _node(sg, "network", cloud="aws", resource_type="security_group", name=f"sg-upload-{idx:03d}"),
            _node(subnet, "network", cloud="aws", resource_type="subnet", name=f"subnet-public-{idx:03d}",
                  props={"is_public": True}),
            _node(role, "identity", cloud="aws", resource_type="iam_role", name=f"upload-writer-{idx:03d}",
                  props={"privilege": "narrow"}),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"a{e}01", "allows_ingress", sg, WORLD, {"port": 22, "cidr": "0.0.0.0/0"}),
            _edge(f"a{e}02", "has_sg", vm, sg),
            _edge(f"a{e}03", "in_subnet", vm, subnet),
            _edge(f"a{e}04", "attached_to", role, vm),
            _edge(f"a{e}05", "can_write", role, bucket),
        ]
    )
    assets.extend(
        [
            _asset_row(bucket, name=f"customer-uploads-{idx:03d}", cloud="aws", resource_type="s3_bucket", region=reg, exposed=True),
            _asset_row(vm, name=f"upload-bastion-{idx:03d}", cloud="aws", resource_type="ec2_instance", region=reg, exposed=True),
            _asset_row(role, name=f"upload-writer-{idx:03d}", cloud="aws", resource_type="iam_role", region="global"),
        ]
    )


def _public_apigw_no_auth(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "us-east-1"
    api = f"arn:aws:apigateway:{reg}::/restapis/public-api-{idx:03d}"
    fn = f"arn:aws:lambda:{reg}:{ACCT_AWS}:function:orders-handler-{idx:03d}"
    table = f"arn:aws:dynamodb:{reg}:{ACCT_AWS}:table/orders-{idx:03d}"
    role = f"arn:aws:iam::{ACCT_AWS}:role/lambda-orders-{idx:03d}"
    ext = f"ext:https://public-api-{idx:03d}.execute-api.amazonaws.com"
    nodes.extend(
        [
            _node(api, "resource", cloud="aws", resource_type="apigateway_rest_api", name=f"public-api-{idx:03d}",
                  region=reg, props={"is_public": True, "is_internet_exposed": True, "auth_type": "NONE"}),
            _node(fn, "resource", cloud="aws", resource_type="lambda_function", name=f"orders-handler-{idx:03d}",
                  region=reg, props={"is_internet_exposed": True}),
            _node(table, "resource", cloud="aws", resource_type="dynamodb_table", name=f"orders-{idx:03d}",
                  region=reg, props={"is_critical_data": True}),
            _node(role, "identity", cloud="aws", resource_type="iam_role", name=f"lambda-orders-{idx:03d}"),
            _node(ext, "external", name=f"public-api-{idx:03d}.execute-api.amazonaws.com"),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"p{e}01", "exposes", api, ext),
            _edge(f"p{e}02", "deploys", api, fn),
            _edge(f"p{e}03", "attached_to", role, fn),
            _edge(f"p{e}04", "can_write", role, table),
        ]
    )
    assets.extend(
        [
            _asset_row(api, name=f"public-api-{idx:03d}", cloud="aws", resource_type="apigateway_rest_api", region=reg, exposed=True,
                       props={"auth_type": "NONE"}),
            _asset_row(fn, name=f"orders-handler-{idx:03d}", cloud="aws", resource_type="lambda_function", region=reg, exposed=True),
            _asset_row(table, name=f"orders-{idx:03d}", cloud="aws", resource_type="dynamodb_table", region=reg),
        ]
    )


def _public_alb_to_data(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "eu-west-1"
    alb = f"arn:aws:elasticloadbalancing:{reg}:{ACCT_AWS}:loadbalancer/app/web-alb-{idx:03d}"
    vm = f"arn:aws:ec2:{reg}:{ACCT_AWS}:instance/web-{idx:03d}"
    sg = f"arn:aws:ec2:{reg}:{ACCT_AWS}:security-group/sg-web-{idx:03d}"
    bucket = f"arn:aws:s3:::web-assets-public-{idx:03d}"
    role = f"arn:aws:iam::{ACCT_AWS}:role/web-app-{idx:03d}"
    nodes.extend(
        [
            _node(alb, "resource", cloud="aws", resource_type="elbv2_load_balancer", name=f"web-alb-{idx:03d}",
                  region=reg, props={"is_public": True, "is_internet_exposed": True, "scheme": "internet-facing"}),
            _node(vm, "resource", cloud="aws", resource_type="ec2_instance", name=f"web-{idx:03d}",
                  region=reg, props={"is_internet_exposed": True}),
            _node(sg, "network", cloud="aws", resource_type="security_group", name=f"sg-web-{idx:03d}"),
            _node(bucket, "resource", cloud="aws", resource_type="s3_bucket", name=f"web-assets-public-{idx:03d}",
                  region=reg, props={"is_public": True, "is_critical_data": True}),
            _node(role, "identity", cloud="aws", resource_type="iam_role", name=f"web-app-{idx:03d}", props={"privilege": "narrow"}),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"b{e}01", "allows_ingress", sg, WORLD, {"port": 443, "cidr": "0.0.0.0/0"}),
            _edge(f"b{e}02", "has_sg", vm, sg),
            _edge(f"b{e}03", "attached_to", role, vm),
            _edge(f"b{e}04", "can_write", role, bucket),
            _edge(f"b{e}05", "serves", alb, vm),
        ]
    )
    assets.extend(
        [
            _asset_row(alb, name=f"web-alb-{idx:03d}", cloud="aws", resource_type="elbv2_load_balancer", region=reg, exposed=True),
            _asset_row(vm, name=f"web-{idx:03d}", cloud="aws", resource_type="ec2_instance", region=reg, exposed=True),
            _asset_row(bucket, name=f"web-assets-public-{idx:03d}", cloud="aws", resource_type="s3_bucket", region=reg, exposed=True),
        ]
    )


def _public_nlb_ssh(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "ap-southeast-1"
    nlb = f"arn:aws:elasticloadbalancing:{reg}:{ACCT_AWS}:loadbalancer/net/ssh-nlb-{idx:03d}"
    vm = f"arn:aws:ec2:{reg}:{ACCT_AWS}:instance/ssh-target-{idx:03d}"
    sg = f"arn:aws:ec2:{reg}:{ACCT_AWS}:security-group/sg-nlb-{idx:03d}"
    nodes.extend(
        [
            _node(nlb, "resource", cloud="aws", resource_type="elbv2_load_balancer", name=f"ssh-nlb-{idx:03d}",
                  region=reg, props={"is_public": True, "is_internet_exposed": True, "load_balancer_type": "network"}),
            _node(vm, "resource", cloud="aws", resource_type="ec2_instance", name=f"ssh-target-{idx:03d}",
                  region=reg, props={"is_internet_exposed": True}),
            _node(sg, "network", cloud="aws", resource_type="security_group", name=f"sg-nlb-{idx:03d}"),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"n{e}01", "allows_ingress", sg, WORLD, {"port": 22, "cidr": "0.0.0.0/0"}),
            _edge(f"n{e}02", "has_sg", vm, sg),
            _edge(f"n{e}03", "serves", nlb, vm),
        ]
    )
    assets.extend(
        [
            _asset_row(nlb, name=f"ssh-nlb-{idx:03d}", cloud="aws", resource_type="elbv2_load_balancer", region=reg, exposed=True,
                       props={"load_balancer_type": "network"}),
            _asset_row(vm, name=f"ssh-target-{idx:03d}", cloud="aws", resource_type="ec2_instance", region=reg, exposed=True),
        ]
    )


def _public_rds(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "us-west-2"
    rds = f"arn:aws:rds:{reg}:{ACCT_AWS}:db:payments-{idx:03d}"
    sg = f"arn:aws:ec2:{reg}:{ACCT_AWS}:security-group/sg-rds-{idx:03d}"
    nodes.extend(
        [
            _node(rds, "resource", cloud="aws", resource_type="rds_instance", name=f"payments-{idx:03d}",
                  region=reg, props={"is_internet_exposed": True, "is_public": True, "is_critical_data": True}),
            _node(sg, "network", cloud="aws", resource_type="security_group", name=f"sg-rds-{idx:03d}"),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"r{e}01", "allows_ingress", sg, WORLD, {"port": 5432, "cidr": "0.0.0.0/0"}),
            _edge(f"r{e}02", "has_sg", rds, sg),
        ]
    )
    assets.append(
        _asset_row(rds, name=f"payments-{idx:03d}", cloud="aws", resource_type="rds_instance", region=reg, exposed=True)
    )


def _public_lambda_secrets(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "ap-south-2"
    fn = f"arn:aws:lambda:{reg}:{ACCT_AWS}:function:public-fn-{idx:03d}"
    secret = f"arn:aws:secretsmanager:{reg}:{ACCT_AWS}:secret:prod-api-key-{idx:03d}"
    role = f"arn:aws:iam::{ACCT_AWS}:role/public-fn-{idx:03d}"
    nodes.extend(
        [
            _node(fn, "resource", cloud="aws", resource_type="lambda_function", name=f"public-fn-{idx:03d}",
                  region=reg, props={"is_public": True, "is_internet_exposed": True}),
            _node(secret, "resource", cloud="aws", resource_type="secretsmanager_secret", name=f"prod-api-key-{idx:03d}",
                  region=reg, props={"is_critical_data": True}),
            _node(role, "identity", cloud="aws", resource_type="iam_role", name=f"public-fn-{idx:03d}"),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"l{e}01", "attached_to", role, fn),
            _edge(f"l{e}02", "can_read", role, secret),
        ]
    )
    assets.extend(
        [
            _asset_row(fn, name=f"public-fn-{idx:03d}", cloud="aws", resource_type="lambda_function", region=reg, exposed=True),
            _asset_row(secret, name=f"prod-api-key-{idx:03d}", cloud="aws", resource_type="secretsmanager_secret", region=reg),
        ]
    )


def _public_s3_write(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "ap-south-1"
    bucket = f"arn:aws:s3:::public-writable-{idx:03d}"
    role = f"arn:aws:iam::{ACCT_AWS}:role/uploader-{idx:03d}"
    nodes.extend(
        [
            _node(bucket, "resource", cloud="aws", resource_type="s3_bucket", name=f"public-writable-{idx:03d}",
                  region=reg, props={"is_public": True, "anonymous_access": "write", "is_encrypted": False}),
            _node(role, "identity", cloud="aws", resource_type="iam_role", name=f"uploader-{idx:03d}"),
        ]
    )
    e = f"{idx:04d}"
    edges.append(_edge(f"s{e}01", "can_write", role, bucket))
    assets.append(
        _asset_row(bucket, name=f"public-writable-{idx:03d}", cloud="aws", resource_type="s3_bucket", region=reg, exposed=True,
                   props={"anonymous_access": "write"})
    )


def _gcp_public_gcs_ssh(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "asia-south1"
    bucket = f"gcp://storage/{ACCT_GCP}/customer-data-{idx:03d}"
    vm = f"gcp://compute/{ACCT_GCP}/zones/{reg}-a/instances/bastion-{idx:03d}"
    fw = f"gcp://compute/{ACCT_GCP}/global/firewalls/ssh-{idx:03d}"
    sa = f"gcp://iam/{ACCT_GCP}/serviceAccounts/writer-{idx:03d}@{ACCT_GCP}.iam.gserviceaccount.com"
    nodes.extend(
        [
            _node(bucket, "resource", cloud="gcp", resource_type="gcs_bucket", name=f"customer-data-{idx:03d}",
                  region=reg, props={"is_public": True, "anonymous_access": "read", "is_critical_data": True}),
            _node(vm, "resource", cloud="gcp", resource_type="gce_instance", name=f"bastion-{idx:03d}",
                  region=reg, props={"is_internet_exposed": True}),
            _node(fw, "network", cloud="gcp", resource_type="compute.firewall", name=f"ssh-{idx:03d}"),
            _node(sa, "identity", cloud="gcp", resource_type="iam.service_account", name=f"writer-{idx:03d}"),
        ]
    )
    e = f"{idx:04d}"
    edges.extend(
        [
            _edge(f"g{e}01", "allows_ingress", fw, WORLD, {"port": 22, "cidr": "0.0.0.0/0"}),
            _edge(f"g{e}02", "has_sg", vm, fw),
            _edge(f"g{e}03", "attached_to", sa, vm),
            _edge(f"g{e}04", "can_write", sa, bucket),
            _edge(f"g{e}05", "exposes", bucket, G_ALL),
        ]
    )
    assets.extend(
        [
            _asset_row(bucket, name=f"customer-data-{idx:03d}", cloud="gcp", resource_type="gcs_bucket", region=reg, exposed=True),
            _asset_row(vm, name=f"bastion-{idx:03d}", cloud="gcp", resource_type="gce_instance", region=reg, exposed=True),
        ]
    )


def _safe_filler(
    idx: int,
    nodes: list[dict],
    edges: list[dict],
    assets: list[dict],
) -> None:
    reg = "ap-south-1"
    bucket = f"arn:aws:s3:::internal-logs-{idx:05d}"
    vm = f"arn:aws:ec2:{reg}:{ACCT_AWS}:instance/worker-{idx:05d}"
    nodes.extend(
        [
            _node(bucket, "resource", cloud="aws", resource_type="s3_bucket", name=f"internal-logs-{idx:05d}",
                  region=reg, props={"is_public": False, "is_encrypted": True}),
            _node(vm, "resource", cloud="aws", resource_type="ec2_instance", name=f"worker-{idx:05d}",
                  region=reg, props={"is_internet_exposed": False}),
        ]
    )
    assets.extend(
        [
            _asset_row(bucket, name=f"internal-logs-{idx:05d}", cloud="aws", resource_type="s3_bucket", region=reg, exposed=False),
            _asset_row(vm, name=f"worker-{idx:05d}", cloud="aws", resource_type="ec2_instance", region=reg, exposed=False),
        ]
    )


def generate_enterprise_fixture(*, target_assets: int = 500) -> dict[str, Any]:
    nodes: list[dict] = [
        _node(WORLD, "network", resource_type="cidr", name="0.0.0.0/0", props={"cidr": "0.0.0.0/0"}),
        _node(G_ALL, "external", name="allUsers", props={"principal": "allUsers"}),
        _node(f"acct:aws:{ACCT_AWS}", "account", cloud="aws", name="demo-aws", resource_type="aws_account", region="global"),
        _node(f"acct:gcp:{ACCT_GCP}", "account", cloud="gcp", name=ACCT_GCP, resource_type="gcp_project", region="global"),
    ]
    edges: list[dict] = []
    assets: list[dict] = []

    scenario_idx = 0
    # Repeat high-value toxic / misconfig patterns (~120 risky stacks)
    for repeat in range(12):
        _toxic_ssh_bucket_aws(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_apigw_no_auth(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_alb_to_data(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_nlb_ssh(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_rds(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_lambda_secrets(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        _public_s3_write(scenario_idx, nodes, edges, assets)
        scenario_idx += 1
        if repeat % 3 == 0:
            _gcp_public_gcs_ssh(scenario_idx, nodes, edges, assets)
            scenario_idx += 1

    filler_idx = 0
    while len(assets) < target_assets:
        _safe_filler(filler_idx, nodes, edges, assets)
        filler_idx += 1

    assets = assets[:target_assets]

    return {
        "tenant_id": TENANT,
        "run_id": RUN,
        "description": f"Enterprise demo — {len(assets)} inventory assets, repeated critical CSPM patterns",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "assets": assets,
        "nodes": nodes,
        "edges": edges,
    }
