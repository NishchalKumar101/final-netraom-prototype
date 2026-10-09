from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from netraom_contracts.models.enums import Exposure, FindingSeverity, FindingSource, SsvcAction

from netraom_graph_writer.backends.networkx_mem import NetworkXTrustGraph

WORLD_CIDR = "0.0.0.0/0"


@dataclass(frozen=True)
class ComboMatch:
    pattern_id: str
    node_ids: list[str]
    title: str
    description: str
    severity: FindingSeverity
    ssvc_action: SsvcAction
    exposure: Exposure


def _is_public_resource(g: NetworkXTrustGraph, node_id: str) -> bool:
    props = g.node_props(node_id)
    return bool(props.get("is_public") or props.get("is_internet_exposed"))


def _is_critical_data(g: NetworkXTrustGraph, node_id: str) -> bool:
    props = g.node_props(node_id)
    return bool(props.get("is_critical_data"))


def _roles_for_vm(g: NetworkXTrustGraph, vm_id: str) -> list[str]:
    roles: list[str] = []
    for src, _dst, _ in g.in_edges(vm_id, kind="attached_to"):
        if ":role/" in src:
            roles.append(src)
        elif "instance-profile" in src:
            for role_id, _prof, _ in g.in_edges(src, kind="attached_to"):
                if ":role/" in role_id:
                    roles.append(role_id)
    return roles


def _vm_internet_exposed(g: NetworkXTrustGraph, vm_id: str) -> bool:
    if _is_public_resource(g, vm_id):
        return True
    for _vm, subnet_id, _ in g.out_edges(vm_id, kind="in_subnet"):
        if g.node_props(subnet_id).get("is_public"):
            return True
    return False


def pattern_t1_public_writable_storage(g: NetworkXTrustGraph) -> list[ComboMatch]:
    """Public storage that an identity can write."""
    matches: list[ComboMatch] = []
    for node_id in g.graph.nodes:
        if g.node_props(node_id).get("kind") != "resource":
            continue
        if not _is_public_resource(g, node_id):
            continue
        writers: list[str] = []
        for src, _dst, data in g.in_edges(node_id, kind="can_write"):
            if g.node_props(src).get("kind") == "identity":
                writers.append(src)
        if not writers:
            continue
        matches.append(
            ComboMatch(
                pattern_id="T1_public_writable_storage",
                node_ids=sorted([node_id, *writers]),
                title="Public storage writable by privileged identity",
                description=(
                    f"Resource `{node_id}` is public and reachable for write by "
                    f"{', '.join(writers)}."
                ),
                severity=FindingSeverity.CRITICAL,
                ssvc_action=SsvcAction.IMMEDIATE,
                exposure=Exposure.INTERNET,
            )
        )
    return matches


def pattern_t2_internet_ssh_admin_path(g: NetworkXTrustGraph) -> list[ComboMatch]:
    """Internet ingress to compute that can reach admin-capable identity and sensitive storage."""
    matches: list[ComboMatch] = []
    world = f"net:{WORLD_CIDR}"
    for sg_id in g.graph.nodes:
        for _src, dst, data in g.out_edges(sg_id, kind="allows_ingress"):
            if dst != world and data.get("props", {}).get("cidr") != WORLD_CIDR:
                continue
            port = (data.get("props") or {}).get("port_from") or (data.get("props") or {}).get("port")
            if port not in (22, "22", None):
                continue
            for vm_id, _sg, _ in g.in_edges(sg_id, kind="has_sg"):
                vm_props = g.node_props(vm_id)
                if vm_props.get("kind") != "resource":
                    continue
                roles = _roles_for_vm(g, vm_id)
                buckets: list[str] = []
                for role_id in roles:
                    for _r, bucket_id, _ in g.out_edges(role_id, kind="can_write"):
                        if _is_public_resource(g, bucket_id) or _is_critical_data(g, bucket_id):
                            buckets.append(bucket_id)
                if roles and buckets:
                    matches.append(
                        ComboMatch(
                            pattern_id="T2_internet_ssh_admin_path",
                            node_ids=sorted([sg_id, vm_id, *roles, *buckets, world]),
                            title="Internet SSH path to role with public writable storage",
                            description=(
                                f"Security group `{sg_id}` allows SSH from the internet to `{vm_id}`, "
                                f"which attaches to {', '.join(roles)} with write access to "
                                f"{', '.join(buckets)}."
                            ),
                            severity=FindingSeverity.CRITICAL,
                            ssvc_action=SsvcAction.IMMEDIATE,
                            exposure=Exposure.INTERNET,
                        )
                    )
    return matches


def pattern_t3_public_exposure(g: NetworkXTrustGraph) -> list[ComboMatch]:
    """In-account resource exposes an external URL (ASM join precursor)."""
    matches: list[ComboMatch] = []
    for src, dst, data in g.all_edges():
        if data.get("kind") != "exposes":
            continue
        if g.node_props(dst).get("kind") != "external":
            continue
        matches.append(
            ComboMatch(
                pattern_id="T3_public_exposure",
                node_ids=sorted([src, dst]),
                title="Resource exposes external surface",
                description=f"Resource `{src}` is linked to external asset `{dst}`.",
                severity=FindingSeverity.MEDIUM,
                ssvc_action=SsvcAction.SCHEDULED,
                exposure=Exposure.INTERNET,
            )
        )
    return matches


def pattern_t4_cross_cloud_federation(g: NetworkXTrustGraph) -> list[ComboMatch]:
    """Shallow cross-cloud identity federation edge."""
    matches: list[ComboMatch] = []
    for src, dst, data in g.all_edges():
        if data.get("kind") not in {"federates_to", "can_assume"}:
            continue
        src_cloud = g.node_props(src).get("cloud") or _cloud_from_node_id(src)
        dst_cloud = g.node_props(dst).get("cloud") or _cloud_from_node_id(dst)
        if src_cloud and dst_cloud and src_cloud != dst_cloud:
            matches.append(
                ComboMatch(
                    pattern_id="T4_cross_cloud_federation",
                    node_ids=sorted([src, dst]),
                    title="Cross-cloud identity federation path",
                    description=f"Identity `{src}` can reach `{dst}` across clouds.",
                    severity=FindingSeverity.HIGH,
                    ssvc_action=SsvcAction.OUT_OF_CYCLE,
                    exposure=Exposure.PARTNER,
                )
            )
    return matches


def pattern_t5_public_compute_to_critical_data(g: NetworkXTrustGraph) -> list[ComboMatch]:
    matches: list[ComboMatch] = []
    for vm_id in g.graph.nodes:
        if g.node_props(vm_id).get("kind") != "resource":
            continue
        if not _vm_internet_exposed(g, vm_id):
            continue
        roles = _roles_for_vm(g, vm_id)
        targets: list[str] = []
        for role_id in roles:
            for kind in ("can_read", "can_write", "can_admin"):
                for _r, dst, _ in g.out_edges(role_id, kind=kind):
                    if _is_critical_data(g, dst):
                        targets.append(dst)
        if roles and targets:
            matches.append(
                ComboMatch(
                    pattern_id="T5_public_compute_to_critical_data",
                    node_ids=sorted([vm_id, *roles, *targets]),
                    title="Internet-reachable compute can access critical data",
                    description=(
                        f"Compute `{vm_id}` is internet-reachable and roles "
                        f"{', '.join(roles)} can reach critical data "
                        f"{', '.join(sorted(set(targets)))}."
                    ),
                    severity=FindingSeverity.CRITICAL,
                    ssvc_action=SsvcAction.IMMEDIATE,
                    exposure=Exposure.INTERNET,
                )
            )
    return matches


def pattern_t6_public_unencrypted_storage(g: NetworkXTrustGraph) -> list[ComboMatch]:
    matches: list[ComboMatch] = []
    for node_id in g.graph.nodes:
        props = g.node_props(node_id)
        if props.get("kind") != "resource":
            continue
        if not _is_public_resource(g, node_id):
            continue
        if props.get("is_encrypted") is True:
            continue
        matches.append(
            ComboMatch(
                pattern_id="T6_public_unencrypted_storage",
                node_ids=[node_id],
                title="Public storage without encryption",
                description=f"Resource `{node_id}` is public and not encrypted.",
                severity=FindingSeverity.HIGH,
                ssvc_action=SsvcAction.IMMEDIATE,
                exposure=Exposure.INTERNET,
            )
        )
    return matches


def pattern_t7_public_database_path(g: NetworkXTrustGraph) -> list[ComboMatch]:
    matches: list[ComboMatch] = []
    world = f"net:{WORLD_CIDR}"
    for node_id in g.graph.nodes:
        props = g.node_props(node_id)
        if props.get("resource_type") not in {"rds_instance", "rds_cluster", "redshift_cluster"}:
            continue
        if not props.get("is_internet_exposed") and not _is_public_resource(g, node_id):
            continue
        matches.append(
            ComboMatch(
                pattern_id="T7_public_database_path",
                node_ids=[node_id],
                title="Database exposed to the internet",
                description=f"Data store `{node_id}` is internet-accessible.",
                severity=FindingSeverity.CRITICAL,
                ssvc_action=SsvcAction.IMMEDIATE,
                exposure=Exposure.INTERNET,
            )
        )
    return matches


def pattern_t8_public_function_to_secrets(g: NetworkXTrustGraph) -> list[ComboMatch]:
    matches: list[ComboMatch] = []
    for fn_id in g.graph.nodes:
        props = g.node_props(fn_id)
        if props.get("resource_type") not in {"lambda_function", "cloud_function", "cloud_run_service"}:
            continue
        if not _is_public_resource(g, fn_id):
            continue
        secrets: list[str] = []
        for role_id in _roles_for_vm(g, fn_id):
            for _r, dst, _ in g.out_edges(role_id, kind="can_read"):
                dst_props = g.node_props(dst)
                if "secretsmanager" in dst or dst_props.get("resource_type") == "secretsmanager_secret":
                    secrets.append(dst)
        if secrets:
            matches.append(
                ComboMatch(
                    pattern_id="T8_public_function_to_secrets",
                    node_ids=sorted([fn_id, *secrets]),
                    title="Public function can read secrets",
                    description=f"Function `{fn_id}` is public and can read {', '.join(secrets)}.",
                    severity=FindingSeverity.CRITICAL,
                    ssvc_action=SsvcAction.IMMEDIATE,
                    exposure=Exposure.INTERNET,
                )
            )
    return matches


def pattern_t9_admin_on_internet_compute(g: NetworkXTrustGraph) -> list[ComboMatch]:
    matches: list[ComboMatch] = []
    for vm_id in g.graph.nodes:
        if g.node_props(vm_id).get("kind") != "resource":
            continue
        if not _vm_internet_exposed(g, vm_id):
            continue
        admin_roles: list[str] = []
        for role_id in _roles_for_vm(g, vm_id):
            for _r, _dst, _ in g.out_edges(role_id, kind="can_admin"):
                admin_roles.append(role_id)
                break
        if admin_roles:
            matches.append(
                ComboMatch(
                    pattern_id="T9_admin_on_internet_compute",
                    node_ids=sorted([vm_id, *admin_roles]),
                    title="Internet-reachable compute with admin-capable role",
                    description=(
                        f"Compute `{vm_id}` is internet-reachable with admin-capable "
                        f"roles {', '.join(sorted(set(admin_roles)))}."
                    ),
                    severity=FindingSeverity.CRITICAL,
                    ssvc_action=SsvcAction.IMMEDIATE,
                    exposure=Exposure.INTERNET,
                )
            )
    return matches


def _cloud_from_node_id(node_id: str) -> str | None:
    if node_id.startswith("arn:aws:"):
        return "aws"
    if node_id.startswith("gcp://"):
        return "gcp"
    if node_id.startswith("acct:"):
        return node_id.split(":", 2)[1]
    return None


PATTERN_REGISTRY: list[tuple[str, Callable[[NetworkXTrustGraph], list[ComboMatch]]]] = [
    ("T1_public_writable_storage", pattern_t1_public_writable_storage),
    ("T2_internet_ssh_admin_path", pattern_t2_internet_ssh_admin_path),
    ("T3_public_exposure", pattern_t3_public_exposure),
    ("T4_cross_cloud_federation", pattern_t4_cross_cloud_federation),
    ("T5_public_compute_to_critical_data", pattern_t5_public_compute_to_critical_data),
    ("T6_public_unencrypted_storage", pattern_t6_public_unencrypted_storage),
    ("T7_public_database_path", pattern_t7_public_database_path),
    ("T8_public_function_to_secrets", pattern_t8_public_function_to_secrets),
    ("T9_admin_on_internet_compute", pattern_t9_admin_on_internet_compute),
]

PATTERN_BY_ID = {pattern_id: fn for pattern_id, fn in PATTERN_REGISTRY}


def run_all_patterns(
    g: NetworkXTrustGraph,
    *,
    pattern_ids: list[str] | None = None,
    allowed_node_ids: set[str] | None = None,
) -> list[ComboMatch]:
    from netraom_graph_writer.combo.subgraph import match_touches_allowed

    selected = PATTERN_REGISTRY
    if pattern_ids:
        selected = [(pid, PATTERN_BY_ID[pid]) for pid in pattern_ids if pid in PATTERN_BY_ID]
    matches: list[ComboMatch] = []
    for _name, fn in selected:
        for match in fn(g):
            if match_touches_allowed(match.node_ids, allowed_node_ids):
                matches.append(match)
    return matches
