export type ServiceState =
  | "operational"
  | "degraded"
  | "unavailable"
  | "unknown";

export interface HealthResponse {
  status?: string;
  service?: string;
  version?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface ServiceHealth {
  id: string;
  name: string;
  endpoint: string;
  state: ServiceState;
  detail: string;
  checkedAt: string | null;
  latencyMs: number | null;
}

export interface HealthSnapshot {
  overall: ServiceState;
  services: ServiceHealth[];
  checkedAt: string | null;
  backendReachable: boolean;
}

export interface NavigationItem {
  label: string;
  href: string;
  icon: string;
  description?: string;
}

export interface Metric {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
  description: string;
}

export interface ActivityItem {
  id: string;
  title: string;
  description: string;
  time: string;
  severity: "info" | "warning" | "critical";
}