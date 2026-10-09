export const ASSET_CATEGORIES = [
  { id: "all", label: "All assets" },
  { id: "compute", label: "VMs / compute" },
  { id: "storage", label: "Buckets" },
  { id: "serverless", label: "Functions" },
  { id: "database", label: "Databases" },
  { id: "network", label: "Network & LB" },
  { id: "api", label: "API Gateway" },
  { id: "identity", label: "Identity" },
  { id: "secrets", label: "Secrets" },
] as const;

export type AssetCategory = (typeof ASSET_CATEGORIES)[number]["id"];

export const SEVERITY_FILTERS = [
  { id: "all", label: "All severities" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
] as const;
