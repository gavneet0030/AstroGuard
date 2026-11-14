const configuredBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000";

export const API_BASE_URL = configuredBaseUrl.replace(/\/+$/, "");

export const HEALTH_ENDPOINTS = {
  health: "/health",
  readiness: "/ready",
  database: "/api/v1/system/database/health"
} as const;

export const HEALTH_POLL_INTERVAL = Math.max(
  5000,
  Number(process.env.NEXT_PUBLIC_HEALTH_POLL_INTERVAL ?? 30000)
);