import { Activity, AlertTriangle, ArrowRight, ArrowUpRight, AudioWaveform, Clock3, Crosshair, Database, Globe2, Layers3, Radio, Satellite, ShieldCheck, Signal, Sparkles, Waves, Workflow, Zap } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { HealthPanel } from "@/components/health-panel";
import { EmptyState } from "@/components/empty-state";

function SectionLabel({
  children,
  right
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="ag-section-label">
      <span>{children}</span>
      {right ? <span className="ag-section-right">{right}</span> : null}
    </div>
  );
}

function InstrumentFrame({
  children,
  className = ""
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`ag-instrument ${className}`}>
      {children}
    </section>
  );
}

function EarthVisualization() {
  return (
    <div className="ag-earth-stage">
      <div className="ag-earth-stars" />
      <div className="ag-earth-grid" />

      <div className="ag-earth-orbit ag-orbit-a" />
      <div className="ag-earth-orbit ag-orbit-b" />
      <div className="ag-earth-orbit ag-orbit-c" />

      <div className="ag-earth">
        <div className="ag-earth-texture" />
        <div className="ag-earth-clouds" />
        <div className="ag-earth-atmosphere" />
      </div>

      <div className="ag-orbit-satellite ag-satellite-one">
        <Satellite size={18} />
      </div>

      <div className="ag-orbit-satellite ag-satellite-two">
        <Radio size={15} />
      </div>

      <div className="ag-orbit-satellite ag-satellite-three">
        <Crosshair size={13} />
      </div>

      <div className="ag-earth-coordinate ag-coordinate-one">
        <span>ORBITAL VIEW</span>
        <strong>CONCEPTUAL RENDER</strong>
      </div>

      <div className="ag-earth-coordinate ag-coordinate-two">
        <span>VISUALIZATION MODE</span>
        <strong>NOT LIVE TRACKING</strong>
      </div>

      <div className="ag-earth-crosshair">
        <span />
        <i />
      </div>

      <div className="ag-earth-side-label">
        <span>AG / EARTH SYSTEM</span>
        <span>ILLUSTRATIVE SCENE</span>
      </div>
    </div>
  );
}

function MissionIdentity() {
  return (
    <div className="ag-mission-identity">
      <div className="ag-mission-emblem">
        <ShieldCheck size={23} />
      </div>

      <div className="ag-mission-identity-copy">
        <span>ASTROGUARD</span>
        <strong>MISSION INTELLIGENCE SYSTEM</strong>
      </div>

      <div className="ag-mission-id">
        <span>PLATFORM</span>
        <strong>AG-01</strong>
      </div>
    </div>
  );
}

function MissionHero() {
  return (
    <section className="ag-mission-hero">
      <div className="ag-hero-background" />
      <div className="ag-hero-grid" />

      <div className="ag-hero-content">
        <div className="ag-hero-pretitle">
          <span className="ag-live-indicator" />
          SPACE SYSTEMS INTELLIGENCE
        </div>

        <div className="ag-hero-title">
          <span>BEYOND</span>
          <span className="ag-title-accent">THE SIGNAL.</span>
        </div>

        <p>
          A unified command environment for telemetry,
          anomaly intelligence, mission investigation
          and spacecraft systems research.
        </p>

        <div className="ag-hero-actions">
          <a href="/telemetry" className="ag-primary-action">
            <AudioWaveform size={16} />
            ENTER TELEMETRY LAB
            <ArrowUpRight size={15} />
          </a>

          <a href="/anomalies" className="ag-secondary-action">
            EXPLORE INTELLIGENCE
            <ArrowRight size={14} />
          </a>
        </div>

        <div className="ag-hero-bottom">
          <span>
            <ShieldCheck size={13} />
            CONTROL PLANE
          </span>

          <span>
            <Activity size={13} />
            BACKEND HEALTH CHECKS
          </span>

          <span>
            <Globe2 size={13} />
            SPACE SYSTEMS RESEARCH
          </span>
        </div>
      </div>

      <div className="ag-hero-art">
        <EarthVisualization />
      </div>

      <div className="ag-hero-index">
        <span>01</span>
        <i />
        <span>MISSION CONTROL</span>
      </div>
    </section>
  );
}

function MetricInstrument({
  index,
  label,
  value,
  note,
  icon,
  tone
}: {
  index: string;
  label: string;
  value: string;
  note: string;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <article className={`ag-metric-instrument ${tone}`}>
      <div className="ag-metric-top">
        <span className="ag-metric-index">{index}</span>
        <span className="ag-metric-icon">{icon}</span>
      </div>

      <div className="ag-metric-label">{label}</div>

      <div className="ag-metric-value">{value}</div>

      <div className="ag-metric-note">
        <span className="ag-metric-dash" />
        {note}
      </div>

      <div className="ag-metric-bottom-line" />
    </article>
  );
}

function MissionMetrics() {
  return (
    <section className="ag-metrics-section">
      <SectionLabel
        right="DATA CONTRACT STATUS"
      >
        PLATFORM INSTRUMENTS
      </SectionLabel>

      <div className="ag-metrics-grid">
        <MetricInstrument
          index="01"
          label="TELEMETRY EVENTS"
          value="â€”"
          note="EVENT API NOT CONNECTED"
          icon={<Waves size={18} />}
          tone="ag-tone-cyan"
        />

        <MetricInstrument
          index="02"
          label="OPEN ANOMALIES"
          value="â€”"
          note="ANOMALY API NOT CONNECTED"
          icon={<AlertTriangle size={18} />}
          tone="ag-tone-amber"
        />

        <MetricInstrument
          index="03"
          label="INVESTIGATIONS"
          value="â€”"
          note="INVESTIGATION API PENDING"
          icon={<Crosshair size={18} />}
          tone="ag-tone-violet"
        />

        <MetricInstrument
          index="04"
          label="REGISTERED MODELS"
          value="â€”"
          note="MODEL REGISTRY PENDING"
          icon={<Layers3 size={18} />}
          tone="ag-tone-green"
        />
      </div>
    </section>
  );
}

function OrbitalInformation() {
  return (
    <InstrumentFrame className="ag-orbital-information">
      <div className="ag-instrument-header">
        <div>
          <span className="ag-instrument-eyebrow">
            <Globe2 size={13} />
            SPACE ENVIRONMENT
          </span>

          <h3>Orbital visualization</h3>
        </div>

        <span className="ag-instrument-tag">
          CONCEPTUAL
        </span>
      </div>

      <div className="ag-orbit-info-body">
        <div className="ag-orbit-info-visual">
          <div className="ag-mini-orbit ag-mini-orbit-one" />
          <div className="ag-mini-orbit ag-mini-orbit-two" />
          <div className="ag-mini-orbit ag-mini-orbit-three" />

          <div className="ag-mini-earth">
            <Globe2 size={30} />
          </div>

          <div className="ag-mini-satellite">
            <Satellite size={16} />
          </div>
        </div>

        <div className="ag-orbit-info-copy">
          <div className="ag-orbit-info-title">
            Earth system research
          </div>

          <p>
            This scene is an illustrative visualization.
            No real satellite position, orbital altitude
            or spacecraft trajectory is being reported.
          </p>

          <div className="ag-orbit-info-footer">
            <span>
              <ShieldCheck size={13} />
              DATA INTEGRITY
            </span>

            <span>NO LIVE ORBIT FEED</span>
          </div>
        </div>
      </div>
    </InstrumentFrame>
  );
}

function SignalSpectrum() {
  const bars = [
    15, 24, 19, 31, 43, 27, 18, 36, 51, 34,
    22, 40, 29, 55, 39, 25, 47, 33, 21, 43,
    58, 31, 19, 36, 48, 27, 17, 40, 29, 51,
    35, 23, 45, 30, 19, 39, 55, 32, 21, 42,
    27, 48, 34, 18, 39, 52, 31, 23
  ];

  return (
    <InstrumentFrame className="ag-spectrum-panel">
      <div className="ag-instrument-header">
        <div>
          <span className="ag-instrument-eyebrow">
            <AudioWaveform size={13} />
            SIGNAL LABORATORY
          </span>

          <h3>Signal visualization</h3>
        </div>

        <span className="ag-instrument-tag">
          DECORATIVE
        </span>
      </div>

      <div className="ag-spectrum">
        {bars.map((height, index) => (
          <span
            key={index}
            style={{ height: `${height}%` }}
          />
        ))}
      </div>

      <div className="ag-spectrum-axis">
        <span>ILLUSTRATIVE WAVEFORM</span>
        <span>NO LIVE SIGNAL INPUT</span>
      </div>

      <div className="ag-spectrum-legend">
        <span><i /> SIGNAL SHAPE</span>
        <span><i /> SAMPLE GRAPHIC</span>
      </div>
    </InstrumentFrame>
  );
}

function MissionPipeline() {
  const stages = [
    {
      number: "01",
      name: "INGESTION",
      description: "Source integration",
      icon: <Radio size={17} />,
      status: "API PENDING"
    },
    {
      number: "02",
      name: "PROCESSING",
      description: "Signal processing",
      icon: <Workflow size={17} />,
      status: "API PENDING"
    },
    {
      number: "03",
      name: "INTELLIGENCE",
      description: "Anomaly analysis",
      icon: <Sparkles size={17} />,
      status: "API PENDING"
    },
    {
      number: "04",
      name: "INVESTIGATION",
      description: "Analyst workflow",
      icon: <ShieldCheck size={17} />,
      status: "API PENDING"
    }
  ];

  return (
    <InstrumentFrame className="ag-pipeline-panel">
      <div className="ag-instrument-header">
        <div>
          <span className="ag-instrument-eyebrow">
            <Workflow size={13} />
            SYSTEM ARCHITECTURE
          </span>

          <h3>Intelligence pipeline</h3>
        </div>

        <span className="ag-instrument-tag">
          INTEGRATION MAP
        </span>
      </div>

      <div className="ag-pipeline">
        {stages.map((stage, index) => (
          <div className="ag-pipeline-stage" key={stage.number}>
            <div className="ag-pipeline-icon">
              {stage.icon}
            </div>

            <div className="ag-pipeline-number">
              STAGE {stage.number}
            </div>

            <strong>{stage.name}</strong>

            <span>{stage.description}</span>

            <small>{stage.status}</small>

            {index !== stages.length - 1 ? (
              <div className="ag-pipeline-connector">
                <ArrowRight size={14} />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </InstrumentFrame>
  );
}

function MissionTimeline() {
  const entries = [
    {
      time: "SYSTEM",
      title: "Backend health integration",
      description: "Verified health endpoints are available.",
      icon: <Activity size={15} />,
      type: "verified"
    },
    {
      time: "RESEARCH",
      title: "Telemetry interface",
      description: "Waiting for confirmed telemetry contract.",
      icon: <Waves size={15} />,
      type: "pending"
    },
    {
      time: "RESEARCH",
      title: "Anomaly intelligence",
      description: "Waiting for confirmed anomaly contract.",
      icon: <AlertTriangle size={15} />,
      type: "pending"
    },
    {
      time: "RESEARCH",
      title: "Model observatory",
      description: "Waiting for model registry integration.",
      icon: <Sparkles size={15} />,
      type: "pending"
    }
  ];

  return (
    <InstrumentFrame className="ag-timeline-panel">
      <div className="ag-instrument-header">
        <div>
          <span className="ag-instrument-eyebrow">
            <Clock3 size={13} />
            PLATFORM ACTIVITY
          </span>

          <h3>Mission timeline</h3>
        </div>

        <span className="ag-instrument-tag">
          INTEGRATION STATUS
        </span>
      </div>

      <div className="ag-timeline">
        {entries.map((entry, index) => (
          <div className="ag-timeline-entry" key={index}>
            <div className={`ag-timeline-node ${entry.type}`}>
              {entry.icon}
            </div>

            <div className="ag-timeline-content">
              <div className="ag-timeline-top">
                <span>{entry.time}</span>
                <small>{entry.type === "verified" ? "VERIFIED" : "PENDING"}</small>
              </div>

              <strong>{entry.title}</strong>
              <p>{entry.description}</p>
            </div>
          </div>
        ))}
      </div>
    </InstrumentFrame>
  );
}

function SystemStatusStrip() {
  return (
    <div className="ag-status-strip">
      <div className="ag-status-strip-title">
        <span className="ag-status-led" />
        PLATFORM STATUS
      </div>

      <div className="ag-status-strip-item">
        <Database size={14} />
        DATABASE
        <span>CHECKED VIA API</span>
      </div>

      <div className="ag-status-strip-item">
        <Signal size={14} />
        TELEMETRY
        <span>CONTRACT PENDING</span>
      </div>

      <div className="ag-status-strip-item">
        <Zap size={14} />
        INTELLIGENCE
        <span>INTEGRATION PENDING</span>
      </div>
    </div>
  );
}

function ResearchNotice() {
  return (
    <div className="ag-research-notice">
      <div className="ag-notice-icon">
        <ShieldCheck size={18} />
      </div>

      <div className="ag-notice-copy">
        <strong>Research prototype Â· Data integrity notice</strong>

        <p>
          AstroGuard is an independent research project and is not
          affiliated with NASA. Orbital artwork and signal graphics
          are illustrative. Live operational information is displayed
          only when a verified backend integration supplies it.
        </p>
      </div>

      <span className="ag-notice-reference">
        AG / 7.3
      </span>
    </div>
  );
}

export function Dashboard() {
  return (
    <div className="ag-dashboard">
      <div className="ag-dashboard-topline">
        <MissionIdentity />

        <div className="ag-dashboard-clock">
          <span>MISSION ENVIRONMENT</span>
          <strong>RESEARCH MODE</strong>
        </div>
      </div>

      <PageHeader
        eyebrow="COMMAND CENTER / 01"
        title="Mission control"
        description="Space systems intelligence, operational health and research environment."
      />

      <MissionHero />

      <SystemStatusStrip />

      <MissionMetrics />

      <div className="ag-dashboard-section-heading">
        <div>
          <span>02 / MISSION ENVIRONMENT</span>
          <h2>Explore the system</h2>
        </div>

        <span>VISUALIZATION + SIGNAL ANALYSIS</span>
      </div>

      <div className="ag-feature-grid">
        <OrbitalInformation />
        <SignalSpectrum />
      </div>

      <div className="ag-dashboard-section-heading">
        <div>
          <span>03 / OPERATIONAL ARCHITECTURE</span>
          <h2>Intelligence operations</h2>
        </div>

        <span>INTEGRATION STATUS</span>
      </div>

      <MissionPipeline />

      <div className="ag-dashboard-section-heading">
        <div>
          <span>04 / SYSTEM MONITORING</span>
          <h2>Platform health</h2>
        </div>

        <span>VERIFIED BACKEND CHECKS</span>
      </div>

      <div className="ag-real-health">
        <HealthPanel />
      </div>

      <div className="ag-lower-grid">
        <MissionTimeline />

        <InstrumentFrame className="ag-activity-panel">
          <div className="ag-instrument-header">
            <div>
              <span className="ag-instrument-eyebrow">
                <Activity size={13} />
                EVENT INTELLIGENCE
              </span>

              <h3>Operational activity</h3>
            </div>

            <span className="ag-instrument-tag">
              API PENDING
            </span>
          </div>

          <EmptyState
            title="No verified event feed"
            description="An operational event endpoint has not been established in the backend audit. No synthetic events are displayed."
          />
        </InstrumentFrame>
      </div>

      <ResearchNotice />

      <div className="ag-dashboard-footer">
        <span>ASTROGUARD MISSION INTELLIGENCE</span>
        <span>INDEPENDENT RESEARCH PROTOTYPE</span>
        <span>PHASE 7.3</span>
      </div>
    </div>
  );
}