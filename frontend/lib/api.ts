import type { ApiResult, HealthCheck, HealthSnapshot, HealthState } from "./types";

const DEFAULT_BASE = "http://127.0.0.1:8000";
const BASE_URL = (process.env.NEXT_PUBLIC_ASTROGUARD_API_BASE_URL || DEFAULT_BASE).replace(/\/+$/, "");

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function readText(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function normalizeState(value: unknown): HealthState {
  if (typeof value !== "string") return "unknown";
  const normalized = value.toLowerCase();
  if (["ok", "healthy", "ready", "operational", "up", "success"].includes(normalized)) {
    return "operational";
  }
  if (["degraded", "partial", "warning"].includes(normalized)) return "degraded";
  if (["offline", "down", "unhealthy", "failed", "error"].includes(normalized)) {
    return "offline";
  }
  return "unknown";
}

async function request(path: string, timeoutMs = 4500): Promise<ApiResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const started = performance.now();

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal
    });
    const latencyMs = Math.round(performance.now() - started);
    const raw = await response.text();
    let payload: unknown = null;

    if (raw) {
      try {
        payload = JSON.parse(raw) as unknown;
      } catch {
        payload = { raw };
      }
    }

    return {
      ok: response.ok,
      status: response.status,
      payload,
      error: response.ok ? null : `HTTP ${response.status}`,
      latencyMs
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    return {
      ok: false,
      status: null,
      payload: null,
      error: message,
      latencyMs: Math.round(performance.now() - started)
    };
  } finally {
    clearTimeout(timeout);
  }
}

function makeCheck(
  id: string,
  name: string,
  endpoint: string,
  result: ApiResult,
  readinessStrict: boolean
): HealthCheck {
  const payload = asRecord(result.payload);
  const declared = normalizeState(
    payload.status ?? payload.state ?? payload.health ?? payload.detail
  );
  let state: HealthState = "unknown";

  if (!result.ok) {
    state = result.status === null ? "offline" : "degraded";
  } else if (declared !== "unknown") {
    state = declared;
  } else if (!readinessStrict) {
    // HTTP success is evidence that the endpoint responded, not proof of
    // every underlying dependency. Keep detail explicit.
    state = "operational";
  }

  const detail =
    readText(payload, ["message", "detail", "status", "state"]) ||
    (result.ok ? "HTTP endpoint responded; payload has no recognized health field." : result.error || "Request failed.");

  return {
    id,
    name,
    endpoint,
    state,
    latencyMs: result.latencyMs,
    detail,
    checkedAt: new Date().toISOString()
  };
}

export async function getHealthSnapshot(): Promise<HealthSnapshot> {
  const definitions = [
    { id: "api", name: "API service", path: "/health", strict: false },
    { id: "readiness", name: "Application readiness", path: "/ready", strict: true },
    { id: "database", name: "Database endpoint", path: "/api/v1/system/database/health", strict: false }
  ];

  const results = await Promise.all(
    definitions.map(async (item) => {
      const response = await request(item.path);
      return makeCheck(item.id, item.name, item.path, response, item.strict);
    })
  );

  const states = results.map((item) => item.state);
  let overall: HealthState = "unknown";
  if (states.some((state) => state === "offline")) overall = "degraded";
  else if (states.every((state) => state === "operational")) overall = "operational";
  else if (states.some((state) => state === "degraded")) overall = "degraded";

  return { checks: results, overall, checkedAt: new Date().toISOString() };
}
