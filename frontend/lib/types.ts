export type HealthState = "operational" | "degraded" | "offline" | "unknown";

export interface HealthCheck {
  id: string;
  name: string;
  endpoint: string;
  state: HealthState;
  latencyMs: number | null;
  detail: string;
  checkedAt: string;
}

export interface HealthSnapshot {
  checks: HealthCheck[];
  overall: HealthState;
  checkedAt: string;
}

export interface ApiResult {
  ok: boolean;
  status: number | null;
  payload: unknown;
  error: string | null;
  latencyMs: number | null;
}
