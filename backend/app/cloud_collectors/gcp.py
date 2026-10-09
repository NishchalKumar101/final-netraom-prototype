from __future__ import annotations

import ipaddress
from typing import Any
from uuid import UUID

from netraom_contracts.models.enums import CloudProvider, GraphEdgeKind, GraphNodeKind

from app.cloud_collectors.common import InventoryBundle, stable_key

_ROLE_PERMISSIONS = {
    "roles/storage.objectviewer": (True, False),
    "roles/storage.legacybucketreader": (True, False),
    "roles/storage.objectadmin": (True, True),
    "roles/storage.admin": (True, True),
    "roles/storage.objectcreator": (False, True),
    "roles/storage.legacybucketwriter": (False, True),
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _is_world_range(cidr: str) -> bool:
    try:
        return ipaddress.ip_network(cidr, strict=False).prefixlen == 0
    except ValueError:
        return False


def _resource_name(value: Any) -> str:
    return str(value or "").rstrip("/").rsplit("/", 1)[-1]


def _members_for_permissions(policy: Any) -> list[tuple[str, bool, bool, str]]:
    out: list[tuple[str, bool, bool, str]] = []
    for binding in _get(policy, "bindings", []) or []:
        role = str(_get(binding, "role", "")).lower()
        can_read, can_write = _ROLE_PERMISSIONS.get(role, (False, False))
        if not (can_read or can_write):
            continue
        members = _get(binding, "members", []) or []
        for member in members:
            out.append((str(member), can_read, can_write, role))
    return out


def collect_gcp_inventory(
    tenant_id: UUID,
    *,
    project_id: str,
    clients: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect GCS, GCE, firewall, and service-account inventory using ADC by default."""
    if not project_id.strip():
        raise ValueError("GCP project_id is required.")
    if clients is None:
        import google.auth
        from google.cloud import compute_v1, storage
        from google.cloud.iam_admin_v1 import IAMClient
        from google.cloud.resourcemanager_v3 import ProjectsClient

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]
        )
        clients = {
            "storage": storage.Client(project=project_id, credentials=credentials),
            "instances": compute_v1.InstancesClient(credentials=credentials),
            "zones": compute_v1.ZonesClient(credentials=credentials),
            "firewalls": compute_v1.FirewallsClient(credentials=credentials),
            "service_accounts": IAMClient(credentials=credentials),
            "projects": ProjectsClient(credentials=credentials),
        }

    bundle = InventoryBundle(
        tenant_id=tenant_id,
        cloud=CloudProvider.GCP,
        account_id=project_id,
        account_name=project_id,
    )

    bucket_records: list[dict[str, Any]] = []
    bucket_policies: dict[str, list[tuple[str, bool, bool, str]]] = {}
    storage_client = clients["storage"]
    for bucket in storage_client.list_buckets(project=project_id):
        name = str(_get(bucket, "name"))
        bucket.reload()
        policy = bucket.get_iam_policy(requested_policy_version=3)
        bindings = _members_for_permissions(policy)
        bucket_policies[name] = bindings
        public_bindings = [row for row in bindings if row[0] in {"allUsers", "allAuthenticatedUsers"}]
        public_access_prevention = _get(_get(bucket, "iam_configuration", {}), "public_access_prevention")
        public_prevention_enforced = str(public_access_prevention or "").lower() == "enforced"
        public_read = not public_prevention_enforced and any(row[1] for row in public_bindings)
        public_write = not public_prevention_enforced and any(row[2] for row in public_bindings)
        bucket_id = f"gcp://storage/{project_id}/{name}"
        props = {
            "is_public": bool(public_read or public_write),
            "is_internet_exposed": bool(public_read or public_write),
            "is_encrypted": True,
            "uses_customer_managed_encryption": bool(_get(bucket, "default_kms_key_name")),
            "anonymous_access": "write" if public_write else "read" if public_read else "none",
            "public_access_prevention": public_access_prevention,
        }
        bundle.add_asset(
            bucket_id,
            kind=GraphNodeKind.RESOURCE,
            resource_type="gcs_bucket",
            name=name,
            native_id=name,
            region=_get(bucket, "location"),
            props=props,
        )
        if public_read or public_write:
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
                bucket_id,
                external_id,
                props={"anonymous_access": props["anonymous_access"]},
                edge_key="public-bucket-access",
            )
        bucket_records.append({"name": name, "node_id": bucket_id})

    firewall_records = list(clients["firewalls"].list(project=project_id))
    firewall_nodes: dict[str, dict[str, Any]] = {}
    for firewall in firewall_records:
        firewall_name = str(_get(firewall, "name"))
        firewall_id = f"gcp://compute/{project_id}/global/firewalls/{firewall_name}"
        direction = str(_get(firewall, "direction", "INGRESS")).upper()
        disabled = bool(_get(firewall, "disabled", False))
        bundle.add_node(
            firewall_id,
            GraphNodeKind.NETWORK,
            resource_type="compute.firewall",
            name=firewall_name,
            native_id=firewall_name,
            props={
                "network": _get(firewall, "network"),
                "direction": direction,
                "disabled": disabled,
                "priority": _get(firewall, "priority"),
                "target_tags": sorted(_get(firewall, "target_tags", []) or []),
            },
        )
        if direction != "INGRESS" or disabled:
            continue
        firewall_nodes[firewall_name] = {
            "node_id": firewall_id,
            "target_tags": set(_get(firewall, "target_tags", []) or []),
            "target_service_accounts": set(_get(firewall, "target_service_accounts", []) or []),
            "network": _resource_name(_get(firewall, "network")),
            "record": firewall,
        }
        allowed_rules = _get(firewall, "allowed", []) or []
        for cidr in (_get(firewall, "source_ranges", []) or []):
            if not allowed_rules:
                continue
            cidr = str(cidr)
            external_id = f"net:{cidr}"
            bundle.add_node(
                external_id,
                GraphNodeKind.EXTERNAL,
                resource_type="cidr",
                name=cidr,
                props={"cidr": cidr, "is_internet_exposed": _is_world_range(cidr)},
            )
            allowed = [
                {
                    "protocol": _get(rule, "I_p_protocol", _get(rule, "IPProtocol", "all")),
                    "ports": list(_get(rule, "ports", []) or []),
                }
                for rule in allowed_rules
            ]
            bundle.add_edge(
                GraphEdgeKind.ALLOWS_INGRESS,
                firewall_id,
                external_id,
                props={"source_ranges": cidr, "allowed": allowed, "priority": _get(firewall, "priority")},
                edge_key=f"{cidr}:{stable_key(allowed)}",
            )

    zones = list(clients["zones"].list(project=project_id))
    instances: list[Any] = []
    for zone in zones:
        zone_name = str(_get(zone, "name"))
        instances.extend(clients["instances"].list(project=project_id, zone=zone_name))

    service_account_emails: set[str] = set()
    for instance in instances:
        for service_account in _get(instance, "service_accounts", []) or []:
            email = _get(service_account, "email")
            if email:
                service_account_emails.add(str(email))

    service_accounts = list(
        clients["service_accounts"].list_service_accounts(
            request={"name": f"projects/{project_id}"}
        )
    )
    account_by_email = {str(_get(account, "email")): account for account in service_accounts}
    service_account_emails.update(account_by_email)

    def add_service_account(email: str) -> str:
        account = account_by_email.get(email)
        identity_id = f"gcp://iam/{project_id}/serviceAccounts/{email}"
        bundle.add_node(
            identity_id,
            GraphNodeKind.IDENTITY,
            resource_type="iam.service_account",
            name=_get(account, "display_name") or email.split("@", 1)[0],
            native_id=email,
            props={
                "email": email,
                "disabled": bool(_get(account, "disabled", False)),
            },
        )
        return identity_id

    for email in sorted(service_account_emails):
        add_service_account(email)

    project_policy = clients["projects"].get_iam_policy(
        request={"resource": f"projects/{project_id}"}
    )
    project_grants: list[tuple[str, bool, bool, str]] = []
    for member, can_read, can_write, role in _members_for_permissions(project_policy):
        if member.startswith("serviceAccount:"):
            email = member.split(":", 1)[1]
            service_account_emails.add(email)
            add_service_account(email)
            project_grants.append((email, can_read, can_write, role))

    for instance in instances:
        name = str(_get(instance, "name"))
        zone = str(_get(instance, "zone", "")).rsplit("/", 1)[-1]
        instance_id = f"gcp://compute/{project_id}/zones/{zone}/instances/{name}"
        tags = set(_get(_get(instance, "tags", {}), "items", []) or [])
        attached_accounts = {
            str(_get(service_account, "email")): sorted(_get(service_account, "scopes", []) or [])
            for service_account in (_get(instance, "service_accounts", []) or [])
            if _get(service_account, "email")
        }
        attached_emails = set(attached_accounts)
        interfaces = _get(instance, "network_interfaces", []) or []
        instance_networks = {
            _resource_name(_get(interface, "network"))
            for interface in interfaces
            if _get(interface, "network")
        }
        public_ips = [
            str(_get(access_config, "nat_i_p", _get(access_config, "natIP")))
            for interface in interfaces
            for access_config in (_get(interface, "access_configs", []) or [])
            if _get(access_config, "nat_i_p", _get(access_config, "natIP"))
        ]
        matching_firewalls = []
        for firewall_name, info in firewall_nodes.items():
            if not info["network"] or info["network"] not in instance_networks:
                continue
            targeted_tags = info["target_tags"]
            targeted_accounts = info["target_service_accounts"]
            if (not targeted_tags and not targeted_accounts) or tags.intersection(targeted_tags) or attached_emails.intersection(targeted_accounts):
                matching_firewalls.append((firewall_name, info))

        public_ingress = any(
            _is_world_range(str(cidr))
            and bool(_get(info["record"], "allowed", []) or [])
            for _firewall_name, info in matching_firewalls
            for cidr in (_get(info["record"], "source_ranges", []) or [])
        )
        is_exposed = bool(public_ips and public_ingress)
        bundle.add_asset(
            instance_id,
            kind=GraphNodeKind.RESOURCE,
            resource_type="gce_instance",
            name=name,
            native_id=str(_get(instance, "id") or name),
            region=zone,
            props={
                "is_internet_exposed": is_exposed,
                "has_public_ip": bool(public_ips),
                "public_ips": public_ips,
                "machine_type": _get(instance, "machine_type"),
                "tags": sorted(tags),
                "service_account_scopes": attached_accounts,
            },
        )
        for email in sorted(attached_emails):
            identity_id = add_service_account(email)
            bundle.add_edge(
                GraphEdgeKind.ATTACHED_TO,
                identity_id,
                instance_id,
                edge_key=email,
                props={"oauth_scopes": attached_accounts[email]},
            )
        for firewall_name, info in matching_firewalls:
            bundle.add_edge(
                GraphEdgeKind.HAS_SG,
                instance_id,
                info["node_id"],
                edge_key=firewall_name,
            )
        for interface_index, interface in enumerate(interfaces):
            subnetwork = _get(interface, "subnetwork")
            if not subnetwork:
                continue
            subnet_name = str(subnetwork).rstrip("/").rsplit("/", 1)[-1]
            subnet_region = str(subnetwork).split("/regions/")[-1].split("/")[0] if "/regions/" in str(subnetwork) else zone.rsplit("-", 1)[0]
            subnet_id = f"gcp://compute/{project_id}/regions/{subnet_region}/subnetworks/{subnet_name}"
            bundle.add_node(
                subnet_id,
                GraphNodeKind.NETWORK,
                resource_type="subnet",
                name=subnet_name,
                native_id=subnet_name,
                region=subnet_region,
            )
            bundle.add_edge(GraphEdgeKind.IN_SUBNET, instance_id, subnet_id, edge_key=str(interface_index))

    for email, can_read, can_write, role in project_grants:
        identity_id = add_service_account(email)
        for bucket in bucket_records:
            if can_read:
                bundle.add_edge(
                    GraphEdgeKind.CAN_READ,
                    identity_id,
                    bucket["node_id"],
                    edge_key=f"project:{role}:read",
                    props={"iam_role": role, "grant_scope": "project"},
                )
            if can_write:
                bundle.add_edge(
                    GraphEdgeKind.CAN_WRITE,
                    identity_id,
                    bucket["node_id"],
                    edge_key=f"project:{role}:write",
                    props={"iam_role": role, "grant_scope": "project"},
                )

    for bucket in bucket_records:
        for member, can_read, can_write, role in bucket_policies.get(bucket["name"], []):
            if not member.startswith("serviceAccount:"):
                continue
            email = member.split(":", 1)[1]
            identity_id = add_service_account(email)
            if can_read:
                bundle.add_edge(
                    GraphEdgeKind.CAN_READ,
                    identity_id,
                    bucket["node_id"],
                    edge_key=f"bucket:{bucket['name']}:{role}:read",
                    props={"iam_role": role, "grant_scope": "bucket"},
                )
            if can_write:
                bundle.add_edge(
                    GraphEdgeKind.CAN_WRITE,
                    identity_id,
                    bucket["node_id"],
                    edge_key=f"bucket:{bucket['name']}:{role}:write",
                    props={"iam_role": role, "grant_scope": "bucket"},
                )

    return bundle.to_dict(scope=f"gcp:{project_id}")
