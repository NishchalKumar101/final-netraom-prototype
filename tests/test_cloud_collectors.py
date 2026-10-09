from __future__ import annotations

import json
from uuid import UUID

import pytest

from app.config import CLOUD_TENANT_ID, DEMO_TENANT_ID
from app.cloud_collectors.aws import collect_aws_inventory
from app.cloud_collectors.gcp import collect_gcp_inventory
from app.ingest import asset_id_for, parse_graph

TENANT_ID = CLOUD_TENANT_ID


class Paginator:
    def __init__(self, records: list[dict], key: str) -> None:
        self.records = records
        self.key = key

    def paginate(self, **_kwargs: object) -> list[dict]:
        return [{self.key: self.records}]


class AwsApiError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class AwsClient:
    def __init__(self, paginated: dict[str, tuple[str, list[dict]]], **responses: object) -> None:
        self.paginated = paginated
        self.responses = responses
        self.calls: list[str] = []

    def get_paginator(self, operation: str) -> Paginator:
        self.calls.append(operation)
        key, records = self.paginated[operation]
        return Paginator(records, key)

    def __getattr__(self, name: str):
        response = self.responses.get(name)
        if response is None:
            raise AttributeError(name)

        def call(**_kwargs: object) -> object:
            self.calls.append(name)
            if isinstance(response, Exception):
                raise response
            return response

        return call


class AwsSession:
    region_name = "us-east-1"

    def __init__(self) -> None:
        self.sts = AwsClient({}, get_caller_identity={"Account": "123456789012"})
        self.s3 = AwsClient(
            {"list_buckets": ("Buckets", [{"Name": "public-bucket"}])},
            get_bucket_location={"LocationConstraint": None},
            get_bucket_policy={
                "Policy": json.dumps(
                    {
                        "Statement": {
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:Get*",
                            "Resource": "arn:aws:s3:::public-bucket/*",
                        }
                    }
                )
            },
            get_bucket_policy_status={"PolicyStatus": {"IsPublic": True}},
            get_public_access_block={
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": False,
                    "RestrictPublicBuckets": False,
                }
            },
            get_bucket_acl={"Grants": []},
            get_bucket_encryption={"ServerSideEncryptionConfiguration": {"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}},
        )
        self.ec2 = AwsClient(
            {
                "describe_security_groups": (
                    "SecurityGroups",
                    [
                        {
                            "GroupId": "sg-web",
                            "GroupName": "web",
                            "IpPermissions": [
                                {
                                    "IpProtocol": "tcp",
                                    "FromPort": 443,
                                    "ToPort": 443,
                                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                                    "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
                                }
                            ],
                        }
                    ],
                ),
                "describe_instances": (
                    "Reservations",
                    [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-web",
                                    "PublicIpAddress": "203.0.113.12",
                                    "SecurityGroups": [{"GroupId": "sg-web"}],
                                    "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:instance-profile/web"},
                                }
                            ]
                        }
                    ],
                ),
            }
        )
        self.iam = AwsClient(
            {
                "list_roles": ("Roles", [{"RoleName": "web-role", "Arn": "arn:aws:iam::123456789012:role/web-role"}]),
                "list_attached_role_policies": ("AttachedPolicies", []),
            },
            get_instance_profile={
                "InstanceProfile": {
                    "Roles": [{"RoleName": "web-role", "Arn": "arn:aws:iam::123456789012:role/web-role"}]
                }
            },
            simulate_principal_policy={
                "EvaluationResults": [
                    {
                        "ResourceName": "arn:aws:s3:::public-bucket/*",
                        "EvalActionName": "s3:GetObject",
                        "EvalDecision": "allowed",
                    }
                ]
            },
        )

    def client(self, name: str, **_kwargs: object) -> AwsClient:
        return {"sts": self.sts, "s3": self.s3, "ec2": self.ec2, "iam": self.iam}[name]


def _find_node(bundle: dict, node_id: str) -> dict:
    return next(node for node in bundle["nodes"] if node["node_id"] == node_id)


def test_aws_collection_flattens_reservations_and_emits_stable_graph() -> None:
    first = collect_aws_inventory(TENANT_ID, session=AwsSession())
    second = collect_aws_inventory(TENANT_ID, session=AwsSession())

    nodes, edges = parse_graph(first)
    assert nodes and edges
    assert first["scope"] == "aws:us-east-1"
    assert {asset["resource_type"] for asset in first["assets"]} == {"s3_bucket", "ec2_instance"}

    instance = _find_node(first, "arn:aws:ec2:us-east-1:123456789012:instance/i-web")
    assert instance["props"]["is_internet_exposed"] is True
    bucket = _find_node(first, "arn:aws:s3:::public-bucket")
    assert bucket["props"]["anonymous_access"] == "read"

    ingress_edges = [
        edge for edge in first["edges"]
        if edge["kind"] == "allows_ingress"
    ]
    assert {edge["dst_id"] for edge in ingress_edges} == {"net:0.0.0.0/0", "net:::/0"}
    assert len({edge["edge_id"] for edge in ingress_edges}) == len(ingress_edges)
    assert any(edge["kind"] == "attached_to" and edge["src_id"].endswith(":role/web-role") for edge in first["edges"])
    assert any(edge["kind"] == "can_read" for edge in first["edges"])
    assert {edge["edge_id"] for edge in first["edges"]} == {edge["edge_id"] for edge in second["edges"]}
    assert [asset["asset_id"] for asset in first["assets"]] == [asset["asset_id"] for asset in second["assets"]]
    assert all(asset["asset_id"] != str(asset_id_for(asset["canonical_key"])) for asset in first["assets"])
    assert TENANT_ID != DEMO_TENANT_ID


def test_aws_missing_encryption_configuration_is_unknown_not_false() -> None:
    session = AwsSession()
    session.s3.responses["get_bucket_encryption"] = {}
    bundle = collect_aws_inventory(TENANT_ID, session=session)
    bucket = _find_node(bundle, "arn:aws:s3:::public-bucket")
    assert bucket["props"]["is_encrypted"] is None
    assert bucket["props"]["bucket_encryption_configuration_present"] is False


def test_aws_swallows_only_expected_missing_configuration_errors() -> None:
    missing_configuration = AwsSession()
    missing_configuration.s3.responses["get_public_access_block"] = AwsApiError(
        "NoSuchPublicAccessBlockConfiguration"
    )
    collect_aws_inventory(TENANT_ID, session=missing_configuration)

    denied = AwsSession()
    denied.s3.responses["get_bucket_acl"] = AwsApiError("AccessDenied")
    with pytest.raises(AwsApiError, match="AccessDenied"):
        collect_aws_inventory(TENANT_ID, session=denied)


class GcpBucket:
    def __init__(self, name: str, policy: dict, prevention: str | None = None) -> None:
        self.name = name
        self.iam_configuration = {"public_access_prevention": prevention}
        self.default_kms_key_name = None
        self.policy = policy

    def reload(self) -> None:
        return None

    def get_iam_policy(self, requested_policy_version: int) -> dict:
        assert requested_policy_version == 3
        return self.policy


class GcpClient:
    def __init__(self, response: list | dict) -> None:
        self.response = response
        self.calls: list[object] = []

    def list_buckets(self, **kwargs: object) -> list:
        self.calls.append(("list_buckets", kwargs))
        return self.response

    def list(self, **kwargs: object) -> list:
        self.calls.append(kwargs)
        return self.response

    def list_service_accounts(self, **kwargs: object) -> list:
        self.calls.append(kwargs)
        return self.response

    def get_iam_policy(self, **kwargs: object) -> dict:
        self.calls.append(kwargs)
        return self.response


def _gcp_clients() -> dict[str, GcpClient]:
    public_policy = {"bindings": [{"role": "roles/storage.objectViewer", "members": ["allUsers"]}]}
    clients = {
        "storage": GcpClient(
            [
                GcpBucket("public-bucket", public_policy),
                GcpBucket("blocked-bucket", public_policy, prevention="enforced"),
            ]
        ),
        "firewalls": GcpClient(
            [
                {
                    "name": "web-ingress",
                    "direction": "INGRESS",
                    "network": "https://compute.googleapis.com/compute/v1/projects/demo/global/networks/default",
                    "source_ranges": ["0.0.0.0/0"],
                    "target_tags": ["web"],
                    "allowed": [{"I_p_protocol": "tcp", "ports": ["443"]}],
                },
                {
                    "name": "disabled-ingress",
                    "direction": "INGRESS",
                    "disabled": True,
                    "network": "https://compute.googleapis.com/compute/v1/projects/demo/global/networks/default",
                    "source_ranges": ["0.0.0.0/0"],
                    "allowed": [{"I_p_protocol": "tcp", "ports": ["22"]}],
                },
                {
                    "name": "different-network",
                    "direction": "INGRESS",
                    "network": "https://compute.googleapis.com/compute/v1/projects/demo/global/networks/other",
                    "source_ranges": ["0.0.0.0/0"],
                    "allowed": [{"I_p_protocol": "tcp", "ports": ["22"]}],
                },
            ]
        ),
        "zones": GcpClient([{"name": "us-central1-a"}]),
        "instances": GcpClient(
            [
                {
                    "name": "web-vm",
                    "id": "12345",
                    "zone": "https://compute.googleapis.com/compute/v1/projects/demo/zones/us-central1-a",
                    "tags": {"items": ["web"]},
                    "network_interfaces": [
                        {
                            "network": "https://compute.googleapis.com/compute/v1/projects/demo/global/networks/default",
                            "access_configs": [{"nat_i_p": "203.0.113.20"}],
                        }
                    ],
                    "service_accounts": [
                        {
                            "email": "web@demo.iam.gserviceaccount.com",
                            "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
                        }
                    ],
                }
            ]
        ),
        "service_accounts": GcpClient(
            [{"email": "web@demo.iam.gserviceaccount.com", "display_name": "web"}]
        ),
        "projects": GcpClient(
            {
                "bindings": [
                    {
                        "role": "roles/storage.admin",
                        "members": ["serviceAccount:web@demo.iam.gserviceaccount.com"],
                    }
                ]
            }
        ),
    }
    return clients


def test_gcp_collection_honors_firewall_target_network_and_public_access_prevention() -> None:
    clients = _gcp_clients()
    first = collect_gcp_inventory(TENANT_ID, project_id="demo", clients=clients)
    second = collect_gcp_inventory(TENANT_ID, project_id="demo", clients=_gcp_clients())

    nodes, edges = parse_graph(first)
    assert nodes and edges
    assert first["scope"] == "gcp:demo"
    instance_id = "gcp://compute/demo/zones/us-central1-a/instances/web-vm"
    instance = _find_node(first, instance_id)
    assert instance["props"]["is_internet_exposed"] is True
    assert _find_node(first, "gcp://storage/demo/blocked-bucket")["props"]["is_public"] is False
    assert _find_node(first, "gcp://storage/demo/public-bucket")["props"]["is_encrypted"] is True
    assert _find_node(first, "gcp://compute/demo/global/firewalls/disabled-ingress")["props"]["disabled"] is True
    matching_sg_edges = [
        edge for edge in first["edges"]
        if edge["kind"] == "has_sg" and edge["src_id"] == instance_id
    ]
    assert [edge["dst_id"] for edge in matching_sg_edges] == [
        "gcp://compute/demo/global/firewalls/web-ingress"
    ]
    attached_edge = next(edge for edge in first["edges"] if edge["kind"] == "attached_to")
    assert attached_edge["props"]["oauth_scopes"] == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    assert any(edge["kind"] == "can_read" for edge in first["edges"])
    assert {edge["edge_id"] for edge in first["edges"]} == {edge["edge_id"] for edge in second["edges"]}
    assert [asset["asset_id"] for asset in first["assets"]] == [asset["asset_id"] for asset in second["assets"]]


def test_gcp_requires_project_scope() -> None:
    with pytest.raises(ValueError, match="project_id is required"):
        collect_gcp_inventory(TENANT_ID, project_id=" ")


def test_non_demo_finding_fingerprints_are_tenant_scoped() -> None:
    from app.combos import _tenant_scoped_fingerprint
    from app.misconfig import _fp

    other_tenant = UUID("33333333-3333-4333-8333-333333333333")
    assert _fp("rule", "resource", DEMO_TENANT_ID) != _fp("rule", "resource", TENANT_ID)
    assert _fp("rule", "resource", TENANT_ID) != _fp("rule", "resource", other_tenant)
    assert _tenant_scoped_fingerprint("toxic-combo:existing", DEMO_TENANT_ID) == "toxic-combo:existing"
    assert _tenant_scoped_fingerprint("toxic-combo:existing", TENANT_ID) != _tenant_scoped_fingerprint(
        "toxic-combo:existing", other_tenant
    )


@pytest.mark.parametrize(
    ("cloud", "cloud_args", "collector_name", "scope"),
    [
        ("aws", ["--region", "us-east-1"], "collect_aws_inventory", "aws:us-east-1"),
        ("gcp", ["--project-id", "demo"], "collect_gcp_inventory", "gcp:demo"),
    ],
)
def test_cli_ingests_collected_bundle_and_runs_existing_detection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cloud: str,
    cloud_args: list[str],
    collector_name: str,
    scope: str,
) -> None:
    from app.cloud_collectors import cli
    from app import main as main_module

    calls: dict[str, object] = {}
    bundle = {
        "cloud": cloud,
        "scope": scope,
        "assets": [{"graph_node_id": "resource"}],
        "run_id": "33333333-3333-4333-8333-333333333333",
    }
    ingested: dict[str, object] = {}

    class Database:
        closed = False

        def close(self) -> None:
            self.closed = True

    class Neo4j:
        closed = False

        def close(self) -> None:
            self.closed = True

    database = Database()
    neo4j = Neo4j()
    monkeypatch.setattr("sys.argv", ["cloud-collector", cloud, *cloud_args])
    monkeypatch.setattr(
        main_module,
        "demo_reset",
        lambda *_args, **_kwargs: pytest.fail("cloud collection must not reset the demo tenant"),
    )
    monkeypatch.setattr(
        cli,
        collector_name,
        lambda tenant, **kwargs: (
            calls.update(tenant=tenant, cloud_args=kwargs)
            or bundle | {"tenant_id": str(tenant)}
        ),
    )
    monkeypatch.setattr(cli, "SessionLocal", lambda: database)
    monkeypatch.setattr(cli, "Neo4jClient", lambda: neo4j)
    monkeypatch.setattr(
        cli,
        "ingest_fixture_dict",
        lambda db, graph, fixture: (ingested.update(tenant_id=fixture["tenant_id"]) or ([], [], fixture)),
    )
    monkeypatch.setattr(
        cli,
        "_run_detection",
        lambda db, graph, **kwargs: (calls.update(detection=kwargs) or ([], [])),
    )

    cli.main()

    assert calls["tenant"] == cli.CLOUD_TENANT_ID
    assert ingested["tenant_id"] == str(cli.CLOUD_TENANT_ID)
    assert calls["cloud_args"] == (
        {"region": "us-east-1"} if cloud == "aws" else {"project_id": "demo"}
    )
    assert calls["detection"]["tenant_id"] == cli.CLOUD_TENANT_ID
    assert calls["detection"]["all_patterns"] is True
    assert database.closed and neo4j.closed
    assert json.loads(capsys.readouterr().out)["assets_collected"] == 1
