"use client";

import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Database,
  RefreshCw,
  Server
} from "lucide-react";

import { useSystemHealth } from "@/hooks/use-system-health";
import { formatTime } from "@/lib/utils/format";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { Panel } from "@/components/ui/panel";

function ServiceIcon({ id }: { id: string }) {
  if (id === "database") {
    return <Database size={18} />;
  }

  if (id === "readiness") {
    return <CheckCircle2 size={18} />;
  }

  return <Server size={18} />;
}

export function SystemHealth() {
  const {
    snapshot,
    loading,
    refreshing,
    lastError,
    refresh
  } = useSystemHealth();

  return (
    <Panel
      title="Infrastructure health"
      subtitle="Live checks against verified backend endpoints"
      action={
        <button
          className="text-button"
          type="button"
          onClick={() => void refresh()}
          disabled={refreshing}
        >
          <RefreshCw
            size={14}
            className={refreshing ? "spin" : ""}
          />
          Refresh
        </button>
      }
    >
      {loading && !snapshot ? (
        <div className="health-loading">
          <div className="loading-spinner" />
          <span>Connecting to AstroGuard backend...</span>
        </div>
      ) : (
        <div className="health-list">
          {(snapshot?.services ?? []).map((service) => (
            <div className="health-row" key={service.id}>
              <div className="health-service-icon">
                <ServiceIcon id={service.id} />
              </div>

              <div className="health-service-copy">
                <strong>{service.name}</strong>
                <span>{service.endpoint}</span>
              </div>

              <div className="health-service-meta">
                <StatusIndicator state={service.state} />
                <span className="latency">
                  {service.latencyMs !== null
                    ? `${service.latencyMs} ms`
                    : "—"}
                </span>
              </div>
            </div>
          ))}

          {snapshot?.services.length === 0 ? (
            <div className="empty-inline">
              No health checks are available.
            </div>
          ) : null}
        </div>
      )}

      {lastError ? (
        <div className="inline-warning">
          <AlertCircle size={15} />
          {lastError}
        </div>
      ) : null}

      <div className="health-footer">
        <span>
          <Clock3 size={13} />
          Last checked: {formatTime(snapshot?.checkedAt ?? null)}
        </span>
        <span>
          <Activity size={13} />
          Automatic polling enabled
        </span>
      </div>
    </Panel>
  );
}