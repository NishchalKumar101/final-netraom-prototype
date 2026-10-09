from enum import StrEnum


class CloudProvider(StrEnum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class FindingSource(StrEnum):
    CSPM = "cspm"
    ASM = "asm"
    VULN = "vuln"
    BRAND = "brand"
    SUPPLY = "supply"
    AI_SURFACE = "ai-surface"
    TOXIC_COMBO = "toxic-combo"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SsvcAction(StrEnum):
    IMMEDIATE = "immediate"
    OUT_OF_CYCLE = "out_of_cycle"
    SCHEDULED = "scheduled"
    DEFER = "defer"


class Exposure(StrEnum):
    INTERNET = "internet"
    PARTNER = "partner"
    INTERNAL = "internal"


class FindingCoverage(StrEnum):
    """Whether a toxic-combo path is fully observable in the tenant graph."""

    COMPLETE = "complete"
    PARTIAL_MISSING_ACCOUNTS = "partial_missing_accounts"


class GraphNodeCoverage(StrEnum):
    """Trust Graph node scan coverage (props.coverage)."""

    SCANNED = "scanned"
    UNSCANNED = "unscanned"
    EXTERNAL_TO_TENANT = "external_to_tenant"


class FindingStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Disposition(StrEnum):
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    EXCEPTION = "exception"
    SUPPRESSED = "suppressed"


class TriageState(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    PENDING_VERIFICATION = "pending_verification"


class UserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class ActorType(StrEnum):
    HUMAN = "human"
    API_KEY = "api_key"
    SYSTEM = "system"


class GranteeType(StrEnum):
    USER = "user"
    API_KEY = "api_key"


class ScopeType(StrEnum):
    TENANT = "tenant"
    ORG_NODE = "org_node"
    PROJECT = "project"


class OrgNodeType(StrEnum):
    ROOT = "root"
    DIVISION = "division"
    TEAM = "team"
    PRODUCT = "product"
    ENVIRONMENT = "environment"
    CUSTOM = "custom"


class GraphNodeKind(StrEnum):
    """Canonical Trust Graph node kinds (cross-cloud)."""

    ACCOUNT = "account"
    IDENTITY = "identity"
    RESOURCE = "resource"
    NETWORK = "network"
    EXTERNAL = "external"
    SERVICE = "service"
    IMAGE = "image"


class GraphEdgeKind(StrEnum):
    """Canonical Trust Graph edge kinds."""

    OWNS = "owns"
    CONTAINS = "contains"
    IN_VPC = "in_vpc"
    IN_SUBNET = "in_subnet"
    ATTACHED_TO = "attached_to"
    HAS_SG = "has_sg"
    USES = "uses"
    CAN_ASSUME = "can_assume"
    CAN_READ = "can_read"
    CAN_WRITE = "can_write"
    CAN_ADMIN = "can_admin"
    GRANTS = "grants"
    TRUSTS = "trusts"
    FEDERATES_TO = "federates_to"
    ALLOWS_INGRESS = "allows_ingress"
    ALLOWS_EGRESS = "allows_egress"
    RESOLVES_TO = "resolves_to"
    SERVES = "serves"
    EXPOSES = "exposes"
    ISSUED_FOR = "issued_for"
    REDIRECTS_TO = "redirects_to"
    RUNS_IMAGE = "runs_image"
    DEPLOYS = "deploys"
    SAME_AS = "same_as"
    RELATED_TO = "related_to"
