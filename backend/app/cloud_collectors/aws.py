from __future__ import annotations

import fnmatch
from typing import Any
from uuid import UUID

from netraom_contracts.models.enums import CloudProvider, GraphEdgeKind, GraphNodeKind

from app.cloud_collectors.common import InventoryBundle, aws_resource_arn, stable_key

_S3_ACTIONS = ("s3:GetObject", "s3:PutObject", "s3:DeleteObject")


def _pages(client: Any, operation: str, result_key: str, **kwargs: Any) -> list[dict[str, Any]]:
    paginator = client.get_paginator(operation)
    return [item for page in paginator.paginate(**kwargs) for item in page.get(result_key, [])]


def _error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return (response.get("Error") or {}).get("Code")
    return None


def _optional_call(client: Any, method: str, *, missing_codes: set[str], **kwargs: Any) -> dict[str, Any]:
    try:
        return getattr(client, method)(**kwargs)
    except Exception as exc:
        if _error_code(exc) in missing_codes:
            return {}
        raise


def _policy_access(policy: dict[str, Any]) -> tuple[bool, bool]:
    can_read = False
    can_write = False
    statements = policy.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    for statement in statements:
        if statement.get("Effect") != "Allow":
            continue
        principal = statement.get("Principal")
        is_public = principal == "*" or (
            isinstance(principal, dict)
            and any(value == "*" or (isinstance(value, list) and "*" in value) for value in principal.values())
        )
        if not is_public:
            continue
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        can_read |= any(fnmatch.fnmatchcase("s3:getobject", action.lower()) for action in actions)
        can_write |= any(
            fnmatch.fnmatchcase(target.lower(), action.lower())
            for action in actions
            for target in ("s3:putobject", "s3:deleteobject")
        )
    return can_read, can_write


def _public_acl(grants: list[dict[str, Any]]) -> tuple[bool, bool]:
    read = False
    write = False
    for grant in grants:
        grantee = grant.get("Grantee") or {}
        if grantee.get("URI", "").endswith("/AllUsers"):
            permission = grant.get("Permission")
            read |= permission in {"READ", "FULL_CONTROL"}
            write |= permission in {"WRITE", "FULL_CONTROL"}
    return read, write


def collect_aws_inventory(
    tenant_id: UUID,
    *,
    region: str | None = None,
    session: Any | None = None,
) -> dict[str, Any]:
    """Collect the AWS resources represented by the checked-in raw AWS lab fixture.

    boto3.Session() is intentionally used without explicit credentials so boto3's standard
    environment/profile/role credential chain remains authoritative.
    """
    if session is None:
        import boto3

        session = boto3.Session()
    selected_region = region or session.region_name
    if not selected_region:
        raise ValueError("AWS region is required; set AWS_DEFAULT_REGION or pass region.")

    sts = session.client("sts", region_name=selected_region)
    account_id = str(sts.get_caller_identity()["Account"])
    s3 = session.client("s3", region_name=selected_region)
    ec2 = session.client("ec2", region_name=selected_region)
    iam = session.client("iam", region_name=selected_region)
    bundle = InventoryBundle(
        tenant_id=tenant_id,
        cloud=CloudProvider.AWS,
        account_id=account_id,
        account_name=account_id,
    )

    bucket_records: list[dict[str, Any]] = []
    buckets = _pages(s3, "list_buckets", "Buckets")
    for bucket in buckets:
        name = str(bucket["Name"])
        location = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
        if location == "EU":
            location = "eu-west-1"
        bucket_arn = f"arn:aws:s3:::{name}"
        policy_response = _optional_call(
            s3, "get_bucket_policy", missing_codes={"NoSuchBucketPolicy", "NoSuchBucketPolicyStatus"}, Bucket=name
        )
        policy: dict[str, Any] = {}
        if policy_response.get("Policy"):
            import json

            policy = json.loads(policy_response["Policy"])
        public_status = _optional_call(
            s3,
            "get_bucket_policy_status",
            missing_codes={"NoSuchBucketPolicy", "NoSuchBucketPolicyStatus"},
            Bucket=name,
        ).get("PolicyStatus", {})
        pab = _optional_call(
            s3,
            "get_public_access_block",
            missing_codes={"NoSuchPublicAccessBlockConfiguration"},
            Bucket=name,
        ).get("PublicAccessBlockConfiguration", {})
        acl_response = s3.get_bucket_acl(Bucket=name)
        acl_read, acl_write = _public_acl(acl_response.get("Grants", []))
        policy_read, policy_write = _policy_access(policy)
        policy_is_public = bool(public_status.get("IsPublic"))
        acl_blocked = bool(pab.get("IgnorePublicAcls"))
        policy_blocked = bool(pab.get("RestrictPublicBuckets"))
        anonymous_read = policy_read and policy_is_public and not policy_blocked
        anonymous_write = policy_write and policy_is_public and not policy_blocked
        if not acl_blocked:
            anonymous_read |= acl_read
            anonymous_write |= acl_write
        encryption = _optional_call(
            s3,
            "get_bucket_encryption",
            missing_codes={"ServerSideEncryptionConfigurationNotFoundError", "NoSuchServerSideEncryptionConfiguration"},
            Bucket=name,
        )
        encryption_rules = (encryption.get("ServerSideEncryptionConfiguration") or {}).get("Rules")
        encrypted = bool(encryption_rules) if encryption_rules is not None else None
        props = {
            "is_public": bool(anonymous_read or anonymous_write),
            "is_internet_exposed": bool(anonymous_read or anonymous_write),
            "is_encrypted": encrypted,
            "bucket_encryption_configuration_present": bool(encryption_rules),
            "anonymous_access": "write" if anonymous_write else "read" if anonymous_read else "none",
            "public_access_block": pab,
        }
        bundle.add_asset(
            bucket_arn,
            kind=GraphNodeKind.RESOURCE,
            resource_type="s3_bucket",
            name=name,
            region=str(location),
            props=props,
            native_id=name,
        )
        if anonymous_read or anonymous_write:
            external_id = "ext:allUsers"
            bundle.add_node(
                external_id,
                GraphNodeKind.EXTERNAL,
                resource_type="public_principal",
                name="allUsers",
                props={"principal": "allUsers", "is_internet_exposed": True},
            )
            bundle.add_edge(
                GraphEdgeKind.EXPOSES,
                bucket_arn,
                external_id,
                props={"anonymous_access": props["anonymous_access"]},
                edge_key="public-bucket-access",
            )
        bucket_records.append({"name": name, "arn": bucket_arn})

    security_groups = _pages(ec2, "describe_security_groups", "SecurityGroups")
    group_ids: dict[str, str] = {}
    group_public_ingress: dict[str, tuple[bool, bool]] = {}
    for group in security_groups:
        group_id = str(group["GroupId"])
        group_arn = aws_resource_arn("ec2", selected_region, account_id, f"security-group/{group_id}")
        group_ids[group_id] = group_arn
        bundle.add_node(
            group_arn,
            GraphNodeKind.NETWORK,
            resource_type="security_group",
            name=group.get("GroupName") or group_id,
            native_id=group_id,
            region=selected_region,
            props={"vpc_id": group.get("VpcId")},
        )
        group_public_ingress[group_id] = (False, False)
        for permission in group.get("IpPermissions", []):
            cidr_ranges = [
                (cidr_range.get("CidrIp"), "ipv4")
                for cidr_range in permission.get("IpRanges", [])
            ] + [
                (cidr_range.get("CidrIpv6"), "ipv6")
                for cidr_range in permission.get("Ipv6Ranges", [])
            ]
            for cidr_value, ip_version in cidr_ranges:
                cidr = str(cidr_value or "")
                if not cidr:
                    continue
                external_id = f"net:{cidr}"
                bundle.add_node(
                    external_id,
                    GraphNodeKind.EXTERNAL,
                    resource_type="cidr",
                    name=cidr,
                    props={"cidr": cidr, "is_internet_exposed": cidr in {"0.0.0.0/0", "::/0"}},
                )
                is_world_v4 = ip_version == "ipv4" and cidr == "0.0.0.0/0"
                is_world_v6 = ip_version == "ipv6" and cidr == "::/0"
                ingress_v4, ingress_v6 = group_public_ingress[group_id]
                group_public_ingress[group_id] = (ingress_v4 or is_world_v4, ingress_v6 or is_world_v6)
                bundle.add_edge(
                    GraphEdgeKind.ALLOWS_INGRESS,
                    group_arn,
                    external_id,
                    props={
                        "cidr": cidr,
                        "protocol": permission.get("IpProtocol"),
                        "port_from": permission.get("FromPort"),
                        "port_to": permission.get("ToPort"),
                    },
                    edge_key=f"{ip_version}:{cidr}:{stable_key(permission)}",
                )

    roles = _pages(iam, "list_roles", "Roles")
    role_arns: dict[str, str] = {}
    for role in roles:
        role_name = str(role["RoleName"])
        role_arn = str(role["Arn"])
        role_arns[role_name] = role_arn
        attached = _pages(iam, "list_attached_role_policies", "AttachedPolicies", RoleName=role_name)
        bundle.add_node(
            role_arn,
            GraphNodeKind.IDENTITY,
            resource_type="iam_role",
            name=role_name,
            native_id=role_name,
            props={
                "path": role.get("Path"),
                "max_session_duration": role.get("MaxSessionDuration"),
                "attached_policy_arns": sorted(policy["PolicyArn"] for policy in attached),
            },
        )

    reservations = _pages(ec2, "describe_instances", "Reservations")
    instances = [
        instance
        for reservation in reservations
        for instance in reservation.get("Instances", [])
    ]
    for instance in instances:
        instance_id = str(instance["InstanceId"])
        arn = instance.get("InstanceArn") or aws_resource_arn(
            "ec2", selected_region, account_id, f"instance/{instance_id}"
        )
        name = next(
            (tag.get("Value") for tag in instance.get("Tags", []) if tag.get("Key") == "Name"),
            instance_id,
        )
        attached_groups = [group_ids[group["GroupId"]] for group in instance.get("SecurityGroups", []) if group.get("GroupId") in group_ids]
        network_interfaces = instance.get("NetworkInterfaces", [])
        public_ipv4 = bool(instance.get("PublicIpAddress")) or any(
            (interface.get("Association") or {}).get("PublicIp")
            for interface in network_interfaces
        )
        public_ipv6 = any(
            address.get("Ipv6Address")
            for interface in network_interfaces
            for address in interface.get("Ipv6Addresses", [])
        )
        ingress_v4 = any(
            group_public_ingress.get(group["GroupId"], (False, False))[0]
            for group in instance.get("SecurityGroups", [])
        )
        ingress_v6 = any(
            group_public_ingress.get(group["GroupId"], (False, False))[1]
            for group in instance.get("SecurityGroups", [])
        )
        is_exposed = (public_ipv4 and ingress_v4) or (public_ipv6 and ingress_v6)
        bundle.add_asset(
            str(arn),
            kind=GraphNodeKind.RESOURCE,
            resource_type="ec2_instance",
            name=str(name),
            region=selected_region,
            native_id=instance_id,
            props={
                "is_internet_exposed": is_exposed,
                "has_public_ip": bool(public_ipv4 or public_ipv6),
                "public_ip": instance.get("PublicIpAddress"),
                "public_ipv6_addresses": sorted(
                    address["Ipv6Address"]
                    for interface in network_interfaces
                    for address in interface.get("Ipv6Addresses", [])
                    if address.get("Ipv6Address")
                ),
                "instance_state": (instance.get("State") or {}).get("Name"),
                "vpc_id": instance.get("VpcId"),
                "subnet_id": instance.get("SubnetId"),
                "security_group_ids": sorted(group["GroupId"] for group in instance.get("SecurityGroups", [])),
            },
        )
        for group_arn in attached_groups:
            bundle.add_edge(GraphEdgeKind.HAS_SG, str(arn), group_arn, edge_key=group_arn)

        subnet_id = instance.get("SubnetId")
        if subnet_id:
            subnet_arn = aws_resource_arn("ec2", selected_region, account_id, f"subnet/{subnet_id}")
            bundle.add_node(
                subnet_arn,
                GraphNodeKind.NETWORK,
                resource_type="subnet",
                name=str(subnet_id),
                native_id=str(subnet_id),
                region=selected_region,
            )
            bundle.add_edge(GraphEdgeKind.IN_SUBNET, str(arn), subnet_arn, edge_key=str(subnet_id))

        profile_arn = (instance.get("IamInstanceProfile") or {}).get("Arn")
        if profile_arn:
            profile_name = str(profile_arn).rsplit("/", 1)[-1]
            profile = iam.get_instance_profile(InstanceProfileName=profile_name)["InstanceProfile"]
            for role in profile.get("Roles", []):
                role_arn = str(role["Arn"])
                if role_arn not in bundle.nodes:
                    bundle.add_node(
                        role_arn,
                        GraphNodeKind.IDENTITY,
                        resource_type="iam_role",
                        name=role.get("RoleName"),
                        native_id=role.get("RoleName"),
                    )
                bundle.add_edge(
                    GraphEdgeKind.ATTACHED_TO,
                    role_arn,
                    str(arn),
                    edge_key=profile_name,
                    props={"instance_profile_arn": profile_arn},
                )

    # IAM policy simulation materializes only effective S3 read/write relationships.
    # It does not attempt to infer permissions from policy names or policy documents.
    bucket_arns = [record["arn"] for record in bucket_records]
    for role_name, role_arn in sorted(role_arns.items()):
        for offset in range(0, len(bucket_arns), 20):
            batch = bucket_arns[offset : offset + 20]
            if not batch:
                continue
            resources = [f"{bucket_arn}/*" for bucket_arn in batch]
            result = iam.simulate_principal_policy(
                PolicySourceArn=role_arn,
                ActionNames=list(_S3_ACTIONS),
                ResourceArns=resources,
            )
            decisions: dict[tuple[str, str], bool] = {}
            for evaluation in result.get("EvaluationResults", []):
                decisions[(str(evaluation.get("ResourceName")), str(evaluation.get("EvalActionName")))] = (
                    evaluation.get("EvalDecision") == "allowed"
                )
            for bucket_arn in batch:
                resource_arn = f"{bucket_arn}/*"
                can_read = decisions.get((resource_arn, "s3:GetObject"), False)
                can_write = decisions.get((resource_arn, "s3:PutObject"), False) or decisions.get(
                    (resource_arn, "s3:DeleteObject"), False
                )
                if can_read:
                    bundle.add_edge(GraphEdgeKind.CAN_READ, role_arn, bucket_arn, edge_key="s3:GetObject")
                if can_write:
                    bundle.add_edge(GraphEdgeKind.CAN_WRITE, role_arn, bucket_arn, edge_key="s3:write")

    return bundle.to_dict(scope=f"aws:{selected_region}")
