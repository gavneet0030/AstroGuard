import { cn } from "@/lib/utils/cn";
import type { ServiceState } from "@/types/system";

const labels: Record<ServiceState, string> = {
  operational: "Operational",
  degraded: "Degraded",
  unavailable: "Unavailable",
  unknown: "Unknown"
};

export function StatusIndicator({
  state,
  showLabel = true
}: {
  state: ServiceState;
  showLabel?: boolean;
}) {
  return (
    <span className="status-wrap">
      <span className={cn("status-dot", `status-${state}`)} />
      {showLabel ? (
        <span className="status-label">{labels[state]}</span>
      ) : null}
    </span>
  );
}