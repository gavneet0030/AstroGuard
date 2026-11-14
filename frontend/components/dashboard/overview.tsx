import {
  ArrowUpRight,
  Activity,
  ShieldCheck,
  Sparkles
} from "lucide-react";

import { SectionHeading } from "@/components/ui/section-heading";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { SystemHealth } from "@/components/dashboard/system-health";
import { ActivityPanel } from "@/components/dashboard/activity-panel";

export function Overview() {
  return (
    <>
      <SectionHeading
        eyebrow="MISSION CONTROL / OVERVIEW"
        title="Command center"
        description="A consolidated view of AstroGuard platform health and intelligence."
        action={
          <div className="overview-actions">
            <span className="secure-label">
              <ShieldCheck size={14} />
              CONTROL PLANE
            </span>
          </div>
        }
      />

      <section className="welcome-banner">
        <div className="welcome-content">
          <div className="welcome-kicker">
            <Sparkles size={14} />
            ASTROGUARD MISSION CONTROL
          </div>
          <h2>Intelligence begins with visibility.</h2>
          <p>
            Monitor platform health, inspect operational signals, and
            investigate system behavior from one workspace.
          </p>
          <div className="welcome-meta">
            <span>
              <Activity size={14} />
              Backend connectivity checks enabled
            </span>
            <span>
              <ShieldCheck size={14} />
              No fabricated operational metrics
            </span>
          </div>
        </div>
        <div className="welcome-decoration">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit-core">
            <ShieldCheck size={38} />
          </div>
          <div className="orbit-point point-one" />
          <div className="orbit-point point-two" />
          <div className="orbit-point point-three" />
        </div>
      </section>

      <div className="dashboard-section-label">
        <span>PLATFORM INDICATORS</span>
        <span className="section-label-note">LIVE METRICS PENDING API</span>
      </div>

      <SummaryCards />

      <div className="dashboard-grid">
        <div className="dashboard-main">
          <SystemHealth />
        </div>
        <div className="dashboard-side">
          <ActivityPanel />
        </div>
      </div>

      <div className="bottom-insight">
        <div className="insight-icon">
          <ArrowUpRight size={17} />
        </div>
        <div>
          <strong>Integration readiness</strong>
          <p>
            Health endpoints are connected. Telemetry, anomaly, investigation,
            and model data require verified API contracts.
          </p>
        </div>
      </div>
    </>
  );
}