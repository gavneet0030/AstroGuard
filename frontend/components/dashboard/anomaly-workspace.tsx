import { AlertTriangle, ShieldAlert, SlidersHorizontal } from "lucide-react";
import { SectionHeading } from "@/components/ui/section-heading";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";

export function AnomalyWorkspace() {
  return (
    <>
      <SectionHeading
        eyebrow="INTELLIGENCE / DETECTION"
        title="Anomaly Center"
        description="Review detected anomalies, severity, and investigation status."
        action={
          <button
            className="secondary-button"
            type="button"
            disabled
          >
            <SlidersHorizontal size={15} />
            Filters unavailable
          </button>
        }
      />

      <div className="summary-grid">
        <div className="metric-card">
          <div className="metric-top">
            <span>Open anomalies</span>
            <AlertTriangle size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">Awaiting anomaly endpoint</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Critical severity</span>
            <ShieldAlert size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">Awaiting severity distribution</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Resolved</span>
            <ShieldAlert size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">Awaiting resolution metrics</div>
        </div>
      </div>

      <Panel
        title="Detection queue"
        subtitle="Anomaly events and triage"
      >
        <EmptyState
          kind="security"
          title="No anomaly feed connected"
          description="No verified anomaly listing endpoint was present in the supplied backend audit. No fabricated anomaly records are displayed."
        />
      </Panel>
    </>
  );
}