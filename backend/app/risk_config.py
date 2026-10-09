"""
Centralized Risk Configuration Matrix for NetraOM CSPM Attack Path Engine.
All factor weights are normalized between 0.0 and 1.0.
"""
from typing import Any

# Node Attribute Risk Factor Weights (0.0 to 1.0)
NODE_EXPOSURE_WEIGHTS: dict[str, float] = {
    "is_internet_exposed": 1.0,
    "is_public": 0.9,
    "in_public_subnet": 0.7,
    "internal_only": 0.2,
    "isolated": 0.0,
}

NODE_VULN_SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 1.0,
    "HIGH": 0.75,
    "MEDIUM": 0.5,
    "LOW": 0.25,
    "NONE": 0.0,
}

NODE_PRIVILEGE_WEIGHTS: dict[str, float] = {
    "admin": 1.0,
    "can_admin": 1.0,
    "can_write": 0.75,
    "can_read": 0.4,
    "attached_role": 0.5,
    "user": 0.2,
    "none": 0.0,
}

NODE_CRITICALITY_WEIGHTS: dict[str, float] = {
    "crown_jewel": 1.0,
    "production": 0.85,
    "staging": 0.5,
    "development": 0.2,
    "default": 0.3,
}

NODE_DATA_SENSITIVITY_WEIGHTS: dict[str, float] = {
    "pii_phi_pci": 1.0,
    "is_critical_data": 1.0,
    "confidential": 0.7,
    "internal": 0.3,
    "public": 0.0,
}

# Relationship / Edge Traversability Weights (0.0 to 1.0)
# Used to calculate edge traversal difficulty / probability for path discovery
RELATIONSHIP_WEIGHTS: dict[str, float] = {
    "allows_ingress": 0.95,      # Direct open network ingress (e.g. port 22/3389)
    "exposes": 0.90,             # External URL exposure
    "can_admin": 0.95,           # Full administrative control
    "can_write": 0.85,           # Data modification permission
    "can_assume": 0.80,           # IAM role assumption across trust boundary
    "attached_to": 0.85,         # EC2 / Instance profile role attachment
    "can_read": 0.60,            # Read-only permission
    "in_subnet": 0.70,           # Subnet membership / network reachability
    "federates_to": 0.75,        # Cross-cloud identity federation
    "default": 0.50,
}


def get_node_exposure_weight(props: dict[str, Any]) -> float:
    if props.get("is_internet_exposed") or props.get("is_public"):
        return NODE_EXPOSURE_WEIGHTS["is_internet_exposed"]
    if props.get("in_public_subnet"):
        return NODE_EXPOSURE_WEIGHTS["in_public_subnet"]
    return NODE_EXPOSURE_WEIGHTS["internal_only"]


def get_node_vuln_weight(props: dict[str, Any]) -> float:
    severity = str(props.get("vuln_severity", props.get("severity", "NONE"))).upper()
    return NODE_VULN_SEVERITY_WEIGHTS.get(severity, 0.2)


def get_node_privilege_weight(props: dict[str, Any], node_kind: str | None = None) -> float:
    if props.get("is_admin") or props.get("has_admin_policy"):
        return NODE_PRIVILEGE_WEIGHTS["admin"]
    if props.get("can_write"):
        return NODE_PRIVILEGE_WEIGHTS["can_write"]
    if props.get("can_read"):
        return NODE_PRIVILEGE_WEIGHTS["can_read"]
    if node_kind == "identity":
        return NODE_PRIVILEGE_WEIGHTS["attached_role"]
    return NODE_PRIVILEGE_WEIGHTS["user"]


def get_node_criticality_weight(props: dict[str, Any]) -> float:
    if props.get("is_crown_jewel"):
        return NODE_CRITICALITY_WEIGHTS["crown_jewel"]
    env = str(props.get("environment", "")).lower()
    if env in ("prod", "production"):
        return NODE_CRITICALITY_WEIGHTS["production"]
    if env in ("stage", "staging"):
        return NODE_CRITICALITY_WEIGHTS["staging"]
    if env in ("dev", "development"):
        return NODE_CRITICALITY_WEIGHTS["development"]
    return NODE_CRITICALITY_WEIGHTS["default"]


def get_node_sensitivity_weight(props: dict[str, Any]) -> float:
    if props.get("is_critical_data") or props.get("has_pii"):
        return NODE_DATA_SENSITIVITY_WEIGHTS["is_critical_data"]
    sens = str(props.get("data_classification", "")).lower()
    if sens == "confidential":
        return NODE_DATA_SENSITIVITY_WEIGHTS["confidential"]
    if sens == "internal":
        return NODE_DATA_SENSITIVITY_WEIGHTS["internal"]
    return NODE_DATA_SENSITIVITY_WEIGHTS["public"]


def get_edge_weight(edge_kind: str) -> float:
    return RELATIONSHIP_WEIGHTS.get(edge_kind, RELATIONSHIP_WEIGHTS["default"])
