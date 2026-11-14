import { apiGet } from "./client";
import { HEALTH_ENDPOINTS } from "./config";
import type {
  HealthResponse,
  HealthSnapshot,
  ServiceHealth,
  ServiceState
} from "@/types/system";

function normalizeState(value: unknown): ServiceState {
  if (typeof value !== "string") {
    return "unknown";
  }

  const normalized = value.toLowerCase();

  if (
    normalized.includes("ok") ||
    normalized.includes("healthy") ||
    normalized.includes("ready") ||
    normalized.includes("operational")
  ) {
    return "operational";
  }

  if (
    normalized.includes("degraded") ||
    normalized.includes("warning")
  ) {
    return "degraded";
  }

  if (
    normalized.includes("unhealthy") ||
    normalized.includes("error") ||
    normalized.includes("failed")
  ) {
    return "unavailable";
  }

  return "unknown";
}

async function checkEndpoint(
  id: string,
  name: string,
  endpoint: string
): Promise<ServiceHealth> {
  const startedAt = performance.now();

  try {
    const response = await apiGet<HealthResponse>(endpoint, {
      timeoutMs: 8000
    });

    const latency = Math.round(performance.now() - startedAt);
    const rawStatus =
      response.status ??
      response.detail ??
      response.message ??
      "unknown";

    const state =
      id === "readiness"
        ? normalizeState(rawStatus)
        : normalizeState(rawStatus) === "unknown"
          ? "operational"
          : normalizeState(rawStatus);

    return {
      id,
      name,
      endpoint,
      state,
      detail:
        typeof rawStatus === "string"
          ? rawStatus
          : "Endpoint responded successfully",
      checkedAt: new Date().toISOString(),
      latencyMs: latency
    };
  } catch (error) {
    return {
      id,
      name,
      endpoint,
      state: "unavailable",
      detail:
        error instanceof Error
          ? error.message
          : "Endpoint unavailable",
      checkedAt: new Date().toISOString(),
      latencyMs: null
    };
  }
}

export async function fetchHealthSnapshot(): Promise<HealthSnapshot> {
  const services = await Promise.all([
    checkEndpoint(
      "health",
      "API Health",
      HEALTH_ENDPOINTS.health
    ),
    checkEndpoint(
      "readiness",
      "API Readiness",
      HEALTH_ENDPOINTS.readiness
    ),
    checkEndpoint(
      "database",
      "Database",
      HEALTH_ENDPOINTS.database
    )
  ]);

  const backendReachable = services.some(
    (service) =>
      service.id !== "database" &&
      service.state !== "unavailable"
  );

  const states = services.map((service) => service.state);

  let overall: ServiceState = "unknown";

  if (states.every((state) => state === "operational")) {
    overall = "operational";
  } else if (states.some((state) => state === "unavailable")) {
    overall = backendReachable ? "degraded" : "unavailable";
  } else if (states.some((state) => state === "degraded")) {
    overall = "degraded";
  }

  return {
    overall,
    services,
    checkedAt: new Date().toISOString(),
    backendReachable
  };
}