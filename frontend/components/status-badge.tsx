import type { HealthState } from "@/lib/types";

export function StatusBadge({ state }: { state: HealthState }) {
  const label = state === "operational" ? "Operational" :
    state === "degraded" ? "Degraded" :
    state === "offline" ? "Offline" : "Unknown";
  return <span className={`status-badge status-${state}`}><i />{label}</span>;
}
