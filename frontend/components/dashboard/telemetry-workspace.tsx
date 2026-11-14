import { Activity, Filter, Radio, Waves } from "lucide-react";
import { SectionHeading } from "@/components/ui/section-heading";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";

export function TelemetryWorkspace() {
  return (
    <>
      <SectionHeading
        eyebrow="OBSERVABILITY / STREAMING"
        title="Telemetry Explorer"
        description="Inspect telemetry streams, event volume, and ingestion health."
        action={
          <button className="secondary-button" type="button" disabled>
            <Filter size={15} />
            Filters unavailable
          </button>
        }
      />

      <div className="summary-grid">
        <div className="metric-card">
          <div className="metric-top">
            <span>Events ingested</span>
            <Activity size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">No verified metrics endpoint</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Stream throughput</span>
            <Waves size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">No verified throughput endpoint</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Consumer lag</span>
            <Radio size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">No verified lag endpoint</div>
        </div>
      </div>

      <Panel
        title="Telemetry stream"
        subtitle="Raw and validated event inspection"
      >
        <EmptyState
          kind="telemetry"
          title="Telemetry API contract required"
          description="The audited API inventory does not expose a confirmed telemetry query endpoint. This panel will connect to the real stream after the backend route and response schema are verified."
        />
      </Panel>
    </>
  );
}