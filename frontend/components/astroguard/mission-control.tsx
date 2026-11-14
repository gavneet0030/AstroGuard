"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Section =
  | "overview"
  | "telemetry"
  | "anomalies"
  | "investigations"
  | "models"
  | "settings"
  | "login";

type IconName =
  | "grid"
  | "activity"
  | "alert"
  | "target"
  | "cpu"
  | "planet"
  | "satellite"
  | "calendar"
  | "chart"
  | "settings"
  | "search"
  | "bell"
  | "user"
  | "home"
  | "rocket"
  | "chevron"
  | "menu"
  | "close"
  | "filter"
  | "download"
  | "arrow"
  | "clock"
  | "database"
  | "shield"
  | "layers"
  | "radio"
  | "file"
  | "check"
  | "globe"
  | "external";

function Icon({
  name,
  size = 19,
  className = ""
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  const paths: Record<IconName, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4"/></>,
    alert: <><path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></>,
    target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/></>,
    cpu: <><rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4"/></>,
    planet: <><circle cx="12" cy="12" r="6"/><ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(-25 12 12)"/></>,
    satellite: <><path d="m8 8 8 8M5 3l4 4-3 3-4-4zM19 21l-4-4 3-3 4 4z"/><path d="m13 5 6 6M5 13l6 6"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.8 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.8-1l-1.7.7-1.4-2.4 1.4-1.1a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.8-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.8 1l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1 0 2Z"/></>,
    search: <><circle cx="10.8" cy="10.8" r="7"/><path d="m16 16 5 5"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></>,
    rocket: <><path d="M5 15c-2 1-3 4-3 6 3 0 5-1 6-3"/><path d="M12 15 9 12c1-5 5-9 12-10-1 7-5 11-9 13Z"/><path d="m14 7 3 3"/><circle cx="15" cy="8" r="1"/></>,
    chevron: <><path d="m7 10 5 5 5-5"/></>,
    menu: <><path d="M3 6h18M3 12h18M3 18h18"/></>,
    close: <><path d="m18 6-12 12M6 6l12 12"/></>,
    filter: <><path d="M4 5h16M7 12h10M10 19h4"/></>,
    download: <><path d="M12 3v12m-5-5 5 5 5-5"/><path d="M4 20h16"/></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 2 16 2 16 0V5M4 12c0 2 16 2 16 0"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    radio: <><circle cx="12" cy="12" r="2"/><path d="M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14M8 8a6 6 0 0 0 0 8M16 8a6 6 0 0 1 0 8"/></>,
    file: <><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M13 2v7h7M8 14h8M8 18h8"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></>,
    external: <><path d="M14 3h7v7M10 14 21 3"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/></>
  };

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

const navigation: {
  label: string;
  href: string;
  icon: IconName;
  section: Section;
}[] = [
  { label: "Mission Control", href: "/", icon: "grid", section: "overview" },
  { label: "Telemetry", href: "/telemetry", icon: "activity", section: "telemetry" },
  { label: "Anomalies", href: "/anomalies", icon: "alert", section: "anomalies" },
  { label: "Investigations", href: "/investigations", icon: "target", section: "investigations" },
  { label: "AI Models", href: "/models", icon: "cpu", section: "models" },
  { label: "Space Explorer", href: "/?view=explorer", icon: "planet", section: "overview" },
  { label: "Satellite Registry", href: "/?view=satellites", icon: "satellite", section: "overview" },
  { label: "Mission Planner", href: "/?view=planner", icon: "calendar", section: "overview" },
  { label: "Reports", href: "/?view=reports", icon: "chart", section: "overview" },
  { label: "Settings", href: "/settings", icon: "settings", section: "settings" }
];

const sectionMeta: Record<Section, { title: string; subtitle: string; eyebrow: string }> = {
  overview: {
    title: "Mission Control",
    subtitle: "Space systems intelligence and mission observability.",
    eyebrow: "MISSION CONTROL / OVERVIEW"
  },
  telemetry: {
    title: "Telemetry Laboratory",
    subtitle: "Inspect telemetry channels, measurements and data quality.",
    eyebrow: "MISSION CONTROL / TELEMETRY"
  },
  anomalies: {
    title: "Anomaly Intelligence",
    subtitle: "Review unusual observations and prioritize investigation.",
    eyebrow: "MISSION CONTROL / ANOMALIES"
  },
  investigations: {
    title: "Mission Investigations",
    subtitle: "Organize evidence, review events and document findings.",
    eyebrow: "MISSION CONTROL / INVESTIGATIONS"
  },
  models: {
    title: "AI Model Observatory",
    subtitle: "Monitor model versions, evaluation and inference readiness.",
    eyebrow: "MISSION CONTROL / AI MODELS"
  },
  settings: {
    title: "Mission Configuration",
    subtitle: "Configure interface preferences and operational settings.",
    eyebrow: "MISSION CONTROL / SETTINGS"
  },
  login: {
    title: "Access AstroGuard",
    subtitle: "Independent space-systems intelligence platform.",
    eyebrow: "SECURE ACCESS"
  }
};

const metrics = [
  {
    label: "Orbital Objects",
    value: "1,284",
    change: "+2.6%",
    icon: "satellite" as IconName,
    tone: "cyan",
    points: "0,30 16,22 30,27 44,17 58,19 72,8 87,14 100,4"
  },
  {
    label: "Telemetry Channels",
    value: "256",
    change: "+4.1%",
    icon: "radio" as IconName,
    tone: "blue",
    points: "0,25 13,18 25,22 39,11 52,15 65,6 78,12 90,3 100,8"
  },
  {
    label: "Anomaly Queue",
    value: "03",
    change: "+1",
    icon: "alert" as IconName,
    tone: "amber",
    points: "0,27 12,21 24,25 36,10 49,15 61,7 73,16 86,6 100,13"
  },
  {
    label: "Model Confidence",
    value: "96.4%",
    change: "+0.7 pp",
    icon: "cpu" as IconName,
    tone: "cyan",
    points: "0,23 14,20 27,14 40,19 53,9 66,12 79,5 91,9 100,3"
  }
];

const activities = [
  {
    time: "23:42:17",
    type: "INFO",
    title: "Interface initialized",
    description: "Mission Control services are operational. (Demo)",
    tone: "info"
  },
  {
    time: "23:39:02",
    type: "WARN",
    title: "Telemetry source pending",
    description: "No live telemetry provider is configured. (Demo)",
    tone: "warning"
  },
  {
    time: "23:27:31",
    type: "ALERT",
    title: "Anomaly candidate detected",
    description: "Candidate observation queued for investigation. (Demo)",
    tone: "danger"
  },
  {
    time: "23:15:06",
    type: "INFO",
    title: "AI model ready",
    description: "Demonstration model metadata loaded. (Demo)",
    tone: "info"
  }
];

function Sparkline({ points, tone }: { points: string; tone: string }) {
  return (
    <svg className={`sparkline ${tone}`} viewBox="0 0 100 36" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.1" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function Brand() {
  return (
    <Link href="/" className="ag-brand" aria-label="AstroGuard home">
      <span className="ag-brand-mark">
        <span className="ag-brand-orbit ag-brand-orbit-one" />
        <span className="ag-brand-orbit ag-brand-orbit-two" />
        <span className="ag-brand-core" />
        <span className="ag-brand-star" />
      </span>
      <span className="ag-brand-copy">
        <strong>ASTROGUARD</strong>
        <small>SPACE SYSTEMS INTELLIGENCE</small>
      </span>
    </Link>
  );
}

function Sidebar({
  section,
  open,
  onClose
}: {
  section: Section;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {open && <button className="ag-sidebar-scrim" onClick={onClose} aria-label="Close navigation" />}
      <aside className={`ag-sidebar ${open ? "is-open" : ""}`}>
        <div className="ag-sidebar-brand">
          <Brand />
          <button className="ag-mobile-close" onClick={onClose} aria-label="Close navigation">
            <Icon name="close" />
          </button>
        </div>

        <nav className="ag-navigation" aria-label="Main navigation">
          <span className="ag-nav-label">OPERATIONS</span>

          {navigation.slice(0, 5).map((item) => {
            const active = item.section === section;

            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={onClose}
                className={`ag-nav-item ${active ? "active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <Icon name={item.icon} size={20} />
                <span>{item.label}</span>
                {active && <span className="ag-nav-active-dot" />}
              </Link>
            );
          })}

          <span className="ag-nav-label ag-nav-label-secondary">MISSION TOOLS</span>

          {navigation.slice(5).map((item) => (
            <Link
              key={item.label}
              href={item.href}
              onClick={onClose}
              className="ag-nav-item"
            >
              <Icon name={item.icon} size={20} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="ag-sidebar-bottom">
          <div className="ag-sidebar-promo">
            <div className="ag-promo-orb" />
            <span className="ag-promo-eyebrow">ASTROGUARD</span>
            <strong>Explore the orbital environment.</strong>
            <small>Independent space-systems intelligence platform.</small>
            <span className="ag-demo-chip">INTERFACE / DEMO</span>
          </div>
          <div className="ag-sidebar-footer">
            <span className="ag-footer-dot" />
            <span>LOCAL INTERFACE</span>
            <span>v0.7.5</span>
          </div>
        </div>
      </aside>
    </>
  );
}

function Topbar({ onMenu }: { onMenu: () => void }) {
  const [search, setSearch] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="ag-topbar">
      <div className="ag-topbar-left">
        <button className="ag-menu-button" onClick={onMenu} aria-label="Open navigation">
          <Icon name="menu" />
        </button>
        <div className="ag-breadcrumb">
          <Link href="/" aria-label="Home"><Icon name="home" size={18} /></Link>
          <span>/</span>
          <span>MISSION CONTROL</span>
          <span>/</span>
          <strong>OVERVIEW</strong>
        </div>
      </div>

      <div className="ag-topbar-right">
        <div className="ag-system-pill">
          <span className="ag-system-dot" />
          <strong>SYSTEMS NOMINAL</strong>
          <span className="ag-system-demo">(INTERFACE / DEMO)</span>
        </div>

        <label className="ag-global-search">
          <Icon name="search" size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search missions, objects, or analyses..."
            aria-label="Search missions, objects, or analyses"
          />
          <kbd>Ctrl + K</kbd>
        </label>

        <div className="ag-topbar-action-wrap">
          <button
            className="ag-icon-button"
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            aria-label="Notifications"
            aria-expanded={notificationsOpen}
          >
            <Icon name="bell" />
            <span className="ag-notification-dot" />
          </button>

          {notificationsOpen && (
            <div className="ag-popover">
              <strong>Notifications</strong>
              <p>No live notification provider is connected.</p>
              <span className="ag-demo-chip">DEMO INTERFACE</span>
            </div>
          )}
        </div>

        <div className="ag-topbar-action-wrap">
          <button
            className="ag-avatar"
            onClick={() => setProfileOpen(!profileOpen)}
            aria-label="User profile"
            aria-expanded={profileOpen}
          >
            <Icon name="user" />
          </button>

          {profileOpen && (
            <div className="ag-popover ag-profile-popover">
              <strong>Mission Operator</strong>
              <span>Local interface session</span>
              <Link href="/settings">Configuration</Link>
              <Link href="/login">Access screen</Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function PageHeading({ section }: { section: Section }) {
  const meta = sectionMeta[section];
  const [range, setRange] = useState("24H");

  return (
    <div className="ag-page-heading">
      <div className="ag-page-heading-copy">
        <div className="ag-heading-accent" />
        <div>
          <div className="ag-eyebrow">{meta.eyebrow}</div>
          <h1>{meta.title}</h1>
          <p>{meta.subtitle}</p>
        </div>
      </div>

      {section === "overview" && (
        <div className="ag-heading-controls">
          <span className="ag-control-caption">TIME RANGE</span>
          <div className="ag-range-selector" role="group" aria-label="Time range">
            {["24H", "7D", "30D", "90D"].map((value) => (
              <button
                key={value}
                onClick={() => setRange(value)}
                className={range === value ? "selected" : ""}
                aria-pressed={range === value}
              >
                {value}
              </button>
            ))}
          </div>
          <div className="ag-date-control">
            <Icon name="calendar" size={16} />
            <span>MISSION PERIOD</span>
            <Icon name="chevron" size={14} />
          </div>
        </div>
      )}
    </div>
  );
}

function EarthPanel() {
  return (
    <section className="ag-earth-panel ag-panel">
      <div className="ag-earth-image">
        <div className="ag-earth-stars" />
        <div className="ag-earth-horizon" />
        <div className="ag-earth-globe">
          <div className="ag-earth-texture" />
          <div className="ag-earth-atmosphere" />
        </div>

        <svg className="ag-orbit-lines" viewBox="0 0 900 340" preserveAspectRatio="none" aria-hidden="true">
          <ellipse cx="450" cy="225" rx="390" ry="85" transform="rotate(-9 450 225)" />
          <ellipse cx="450" cy="225" rx="320" ry="125" transform="rotate(13 450 225)" />
          <path d="M80 280 Q450 -30 825 150" />
        </svg>

        <div className="ag-satellite-marker satellite-one"><Icon name="satellite" size={17} /></div>
        <div className="ag-satellite-marker satellite-two"><Icon name="satellite" size={16} /></div>
        <div className="ag-satellite-marker satellite-three"><Icon name="satellite" size={15} /></div>

        <div className="ag-earth-overlay">
          <span className="ag-earth-label">EARTH OVERVIEW</span>
          <div><span>VIEW</span><strong>Orbit (Conceptual)</strong></div>
          <div><span>LAYER</span><strong>Tracked Objects</strong></div>
          <div><span>STATUS</span><strong className="ag-nominal"><i /> Nominal</strong></div>
          <span className="ag-demo-chip">VISUALIZATION / DEMO</span>
        </div>

        <div className="ag-earth-corner corner-one" />
        <div className="ag-earth-corner corner-two" />
        <div className="ag-earth-corner corner-three" />
        <div className="ag-earth-corner corner-four" />

        <div className="ag-earth-watermark">ASTROGUARD / PLANETARY VIEW</div>
      </div>
    </section>
  );
}

function MissionSummary() {
  const items = [
    { icon: "satellite" as IconName, label: "Tracked objects", value: "1,284", tone: "cyan" },
    { icon: "rocket" as IconName, label: "Active missions", value: "08", tone: "cyan" },
    { icon: "alert" as IconName, label: "Alerts", value: "03", tone: "amber" }
  ];

  return (
    <section className="ag-summary ag-panel">
      <div className="ag-panel-heading">
        <h2>MISSION SUMMARY</h2>
        <span className="ag-heading-indicator" />
      </div>

      {items.map((item) => (
        <div className="ag-summary-row" key={item.label}>
          <div className={`ag-summary-icon ${item.tone}`}>
            <Icon name={item.icon} size={25} />
          </div>
          <div className="ag-summary-copy">
            <span>{item.label}</span>
            <small>DEMO DATA</small>
          </div>
          <strong className={item.tone}>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}

function MetricCards() {
  return (
    <div className="ag-metrics-grid">
      {metrics.map((metric) => (
        <article className={`ag-metric-card ag-panel ${metric.tone}`} key={metric.label}>
          <div className="ag-metric-top">
            <div className="ag-metric-icon"><Icon name={metric.icon} size={23} /></div>
            <span className="ag-metric-label">{metric.label}</span>
            <span className="ag-demo-tag">DEMO</span>
          </div>
          <div className="ag-metric-bottom">
            <div>
              <strong>{metric.value}</strong>
              <span className="ag-metric-change">▲ {metric.change} <small>(24h)</small></span>
            </div>
            <Sparkline points={metric.points} tone={metric.tone} />
          </div>
        </article>
      ))}
    </div>
  );
}

function ActivityPanel() {
  const [filter, setFilter] = useState("All Activity");

  const filtered = useMemo(() => {
    if (filter === "All Activity") return activities;
    return activities.filter((item) => item.type === filter.toUpperCase());
  }, [filter]);

  return (
    <section className="ag-activity-panel ag-panel">
      <div className="ag-panel-heading">
        <div className="ag-panel-title">
          <Icon name="layers" size={22} />
          <h2>MISSION ACTIVITY</h2>
        </div>

        <select
          className="ag-select"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          aria-label="Filter mission activity"
        >
          <option>All Activity</option>
          <option>INFO</option>
          <option>WARN</option>
          <option>ALERT</option>
        </select>
      </div>

      <div className="ag-activity-list">
        {filtered.map((item, index) => (
          <article className={`ag-activity-row ${item.tone}`} key={`${item.time}-${item.title}`}>
            <div className="ag-activity-track">
              <span className="ag-activity-dot" />
              {index !== filtered.length - 1 && <span className="ag-activity-line" />}
            </div>
            <time>{item.time}</time>
            <span className={`ag-activity-type ${item.tone}`}>{item.type}</span>
            <div className="ag-activity-copy">
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </div>
          </article>
        ))}

        {filtered.length === 0 && (
          <div className="ag-empty-state">No activities match this filter.</div>
        )}
      </div>
    </section>
  );
}

function AnomalyIntelligence() {
  const severity = [
    { label: "Critical", value: 0, color: "critical" },
    { label: "High", value: 1, color: "high" },
    { label: "Medium", value: 1, color: "medium" },
    { label: "Low", value: 1, color: "low" }
  ];

  return (
    <section className="ag-anomaly-panel ag-panel">
      <div className="ag-panel-heading">
        <div className="ag-panel-title">
          <Icon name="target" size={22} />
          <h2>ANOMALY INTELLIGENCE</h2>
        </div>
        <span className="ag-demo-tag">DEMO DATA</span>
      </div>

      <div className="ag-anomaly-content">
        <div className="ag-severity">
          <h3>Severity Distribution <span>(24h)</span></h3>
          {severity.map((item) => (
            <div className="ag-severity-row" key={item.label}>
              <span>{item.label}</span>
              <div className="ag-severity-track">
                <i className={item.color} style={{ width: `${item.value * 33}%` }} />
              </div>
              <strong>{item.value} <small>({item.value === 0 ? "0" : "33"}%)</small></strong>
            </div>
          ))}
        </div>

        <div className="ag-risk">
          <h3>Orbital Risk <span>(Demo)</span></h3>
          <svg viewBox="0 0 330 150" preserveAspectRatio="none" role="img" aria-label="Illustrative orbital risk trend">
            <defs>
              <linearGradient id="ag-risk-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity=".35" />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity=".01" />
              </linearGradient>
            </defs>
            {[15,45,75,105,135].map((y) => (
              <line key={y} x1="30" y1={y} x2="320" y2={y} stroke="rgba(133,178,209,.17)" />
            ))}
            <path d="M30 112 L95 92 L160 80 L230 53 L320 76 L320 135 L30 135Z" fill="url(#ag-risk-fill)" />
            <polyline points="30,112 95,92 160,80 230,53 320,76" fill="none" stroke="#38d9f3" strokeWidth="2.5" />
            {[[30,112],[95,92],[160,80],[230,53],[320,76]].map(([x,y]) => (
              <circle key={`${x}-${y}`} cx={x} cy={y} r="4" fill="#e9fbff" stroke="#38d9f3" strokeWidth="2" />
            ))}
            <g fill="#8ca3b9" fontSize="9">
              <text x="25" y="148">-24h</text>
              <text x="88" y="148">-18h</text>
              <text x="153" y="148">-12h</text>
              <text x="225" y="148">-6h</text>
              <text x="301" y="148">Now</text>
            </g>
          </svg>
        </div>
      </div>
      <p className="ag-chart-disclaimer">Illustrative demonstration values — not a live risk calculation.</p>
    </section>
  );
}

function MissionPipeline() {
  const stages = [
    { number: "01", title: "Observe", description: "Ingest and monitor space data.", icon: "target" as IconName, state: "complete" },
    { number: "02", title: "Detect", description: "Identify events and anomalies.", icon: "activity" as IconName, state: "active" },
    { number: "03", title: "Investigate", description: "Analyze and validate findings.", icon: "search" as IconName, state: "pending" },
    { number: "04", title: "Report", description: "Generate mission insights.", icon: "file" as IconName, state: "pending" }
  ];

  return (
    <section className="ag-pipeline ag-panel">
      <div className="ag-panel-heading">
        <div className="ag-panel-title">
          <Icon name="rocket" size={22} />
          <h2>MISSION PIPELINE</h2>
        </div>
        <span className="ag-demo-tag">DEMO WORKFLOW</span>
      </div>

      <div className="ag-pipeline-track">
        {stages.map((stage) => (
          <article className={`ag-pipeline-stage ${stage.state}`} key={stage.number}>
            <div className="ag-pipeline-icon"><Icon name={stage.icon} size={25} /></div>
            <div className="ag-pipeline-copy">
              <span>{stage.number}</span>
              <strong>{stage.title}</strong>
              <p>{stage.description}</p>
            </div>
            <span className={`ag-pipeline-state ${stage.state}`}>
              {stage.state === "complete" ? <Icon name="check" size={15} /> : ""}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function Overview() {
  return (
    <>
      <div className="ag-hero-grid">
        <EarthPanel />
        <MissionSummary />
      </div>
      <MetricCards />
      <div className="ag-analytics-grid">
        <ActivityPanel />
        <AnomalyIntelligence />
      </div>
      <MissionPipeline />
    </>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
  action
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: string;
}) {
  return (
    <div className="ag-section-header">
      <div>
        <span className="ag-eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action && <button className="ag-outline-button"><Icon name="download" size={15} /> {action}</button>}
    </div>
  );
}

function DataTable({
  headers,
  rows
}: {
  headers: string[];
  rows: string[][];
}) {
  return (
    <div className="ag-table-wrap">
      <table className="ag-table">
        <thead>
          <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row[0]}-${index}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${cell}-${cellIndex}`}>
                  {cellIndex === row.length - 1 && ["NOMINAL","PENDING","HIGH","MEDIUM","LOW","READY"].includes(cell)
                    ? <span className={`ag-table-status ${cell.toLowerCase()}`}>{cell}</span>
                    : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TelemetryPage() {
  const [channel, setChannel] = useState("All Channels");

  const rows = [
    ["TM-001", "Orbital velocity", "7.66 km/s", "Nominal"],
    ["TM-002", "Altitude", "408.2 km", "Nominal"],
    ["TM-003", "Temperature", "21.4 °C", "Nominal"],
    ["TM-004", "Signal strength", "-72 dBm", "Pending"],
    ["TM-005", "Power subsystem", "86.2%", "Nominal"],
    ["TM-006", "Attitude deviation", "0.04°", "Nominal"]
  ];

  return (
    <div className="ag-workspace">
      <SectionHeader
        eyebrow="TELEMETRY / OBSERVATION"
        title="Telemetry channels"
        description="Explore structured telemetry records and channel-level measurements."
        action="EXPORT VIEW"
      />

      <div className="ag-workspace-cards">
        <div className="ag-workspace-card"><span>REGISTERED CHANNELS</span><strong>256</strong><small>Demonstration value</small></div>
        <div className="ag-workspace-card"><span>ACTIVE STREAMS</span><strong>0</strong><small>No live provider connected</small></div>
        <div className="ag-workspace-card"><span>DATA QUALITY</span><strong>—</strong><small>Awaiting provider validation</small></div>
      </div>

      <section className="ag-panel ag-workspace-panel">
        <div className="ag-panel-heading">
          <div className="ag-panel-title"><Icon name="radio" /><h2>CHANNEL REGISTRY</h2></div>
          <select className="ag-select" value={channel} onChange={(event) => setChannel(event.target.value)}>
            <option>All Channels</option>
            <option>Orbital</option>
            <option>Power</option>
          </select>
        </div>
        <DataTable headers={["CHANNEL ID","MEASUREMENT","SAMPLE VALUE","STATUS"]} rows={rows} />
        <div className="ag-data-notice"><Icon name="shield" size={15} /> Sample telemetry values are illustrative and are not live spacecraft measurements.</div>
      </section>
    </div>
  );
}

function AnomaliesPage() {
  const [severity, setSeverity] = useState("All severity");
  const rows = [
    ["AN-2026-001", "Orbital deviation candidate", "High", "23:27:31", "Pending"],
    ["AN-2026-002", "Signal fluctuation candidate", "Medium", "22:14:09", "Pending"],
    ["AN-2026-003", "Thermal variance candidate", "Low", "20:05:42", "Pending"]
  ];

  const filtered = rows.filter((row) => severity === "All severity" || row[2] === severity);

  return (
    <div className="ag-workspace">
      <SectionHeader
        eyebrow="ANOMALY INTELLIGENCE"
        title="Anomaly queue"
        description="Review candidate events, severity and investigation status."
      />

      <div className="ag-workspace-cards">
        <div className="ag-workspace-card"><span>OPEN CANDIDATES</span><strong>03</strong><small>Demonstration records</small></div>
        <div className="ag-workspace-card"><span>CRITICAL</span><strong>00</strong><small>No critical demo records</small></div>
        <div className="ag-workspace-card"><span>AWAITING REVIEW</span><strong>03</strong><small>Requires analyst verification</small></div>
      </div>

      <section className="ag-panel ag-workspace-panel">
        <div className="ag-panel-heading">
          <div className="ag-panel-title"><Icon name="alert" /><h2>ANOMALY CANDIDATES</h2></div>
          <select className="ag-select" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option>All severity</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
          </select>
        </div>
        <DataTable headers={["EVENT ID","OBSERVATION","SEVERITY","DETECTED","STATUS"]} rows={filtered} />
        <div className="ag-data-notice"><Icon name="shield" size={15} /> Candidate events are demonstration records, not confirmed real-world anomalies.</div>
      </section>
    </div>
  );
}

function InvestigationsPage() {
  const [selected, setSelected] = useState("INV-001");

  const cases = [
    { id: "INV-001", title: "Orbital deviation review", status: "OPEN", description: "Review a demonstration orbital deviation candidate and its supporting evidence." },
    { id: "INV-002", title: "Signal variance assessment", status: "OPEN", description: "Review a demonstration signal fluctuation candidate." },
    { id: "INV-003", title: "Thermal variance review", status: "DRAFT", description: "Review a demonstration thermal variance candidate." }
  ];

  const active = cases.find((item) => item.id === selected) ?? cases[0];

  return (
    <div className="ag-workspace">
      <SectionHeader
        eyebrow="MISSION INVESTIGATIONS"
        title="Investigation workspace"
        description="Organize evidence and document the review of candidate events."
      />

      <div className="ag-investigation-layout">
        <section className="ag-panel ag-case-list">
          <div className="ag-panel-heading"><h2>INVESTIGATION CASES</h2><span className="ag-demo-tag">03 DEMO</span></div>
          {cases.map((item) => (
            <button
              key={item.id}
              className={`ag-case-item ${selected === item.id ? "active" : ""}`}
              onClick={() => setSelected(item.id)}
            >
              <span>{item.id}</span>
              <strong>{item.title}</strong>
              <small>{item.status}</small>
            </button>
          ))}
        </section>

        <section className="ag-panel ag-case-detail">
          <span className="ag-eyebrow">CASE DETAILS / {active.id}</span>
          <h2>{active.title}</h2>
          <p>{active.description}</p>
          <div className="ag-case-metadata">
            <div><span>CASE STATUS</span><strong>{active.status}</strong></div>
            <div><span>DATA SOURCE</span><strong>DEMO RECORD</strong></div>
            <div><span>EVIDENCE</span><strong>NOT VERIFIED</strong></div>
          </div>
          <div className="ag-case-callout">
            <Icon name="shield" />
            <div><strong>Evidence verification required</strong><p>Do not treat this demonstration case as a verified operational incident.</p></div>
          </div>
          <button className="ag-primary-button" onClick={() => alert("Investigation editing will be enabled when the backend workflow is configured.")}>
            OPEN INVESTIGATION <Icon name="arrow" size={16} />
          </button>
        </section>
      </div>
    </div>
  );
}

function ModelsPage() {
  const models = [
    ["ASTRO-ANOMALY-01", "Anomaly candidate classifier", "v0.3.2", "Ready"],
    ["ORBIT-RISK-02", "Orbital risk research model", "v0.1.0", "Pending"],
    ["SIGNAL-INTEL-03", "Signal pattern research model", "v0.2.1", "Pending"]
  ];

  return (
    <div className="ag-workspace">
      <SectionHeader
        eyebrow="AI MODEL OBSERVATORY"
        title="Model registry"
        description="Review model metadata, versions and evaluation readiness."
      />

      <div className="ag-workspace-cards">
        <div className="ag-workspace-card"><span>REGISTERED MODELS</span><strong>03</strong><small>Illustrative registry</small></div>
        <div className="ag-workspace-card"><span>PRODUCTION DEPLOYMENTS</span><strong>0</strong><small>No production inference configured</small></div>
        <div className="ag-workspace-card"><span>MODEL EVALUATION</span><strong>—</strong><small>Awaiting evaluation datasets</small></div>
      </div>

      <section className="ag-panel ag-workspace-panel">
        <div className="ag-panel-heading"><div className="ag-panel-title"><Icon name="cpu" /><h2>MODEL REGISTRY</h2></div><span className="ag-demo-tag">DEMO METADATA</span></div>
        <DataTable headers={["MODEL ID","DESCRIPTION","VERSION","STATUS"]} rows={models} />
        <div className="ag-data-notice"><Icon name="shield" size={15} /> Registry entries do not imply a deployed or validated production model.</div>
      </section>
    </div>
  );
}

function SettingsPage() {
  const [compact, setCompact] = useState(false);
  const [motion, setMotion] = useState(true);
  const [notifications, setNotifications] = useState(false);

  return (
    <div className="ag-workspace">
      <SectionHeader
        eyebrow="MISSION CONFIGURATION"
        title="Interface settings"
        description="Manage local interface preferences and display behavior."
      />

      <section className="ag-panel ag-settings-panel">
        <div className="ag-panel-heading"><div className="ag-panel-title"><Icon name="settings" /><h2>DISPLAY PREFERENCES</h2></div></div>

        {[
          { label: "Compact interface", detail: "Reduce spacing across interface panels.", value: compact, set: setCompact },
          { label: "Interface animations", detail: "Enable decorative interface motion where supported.", value: motion, set: setMotion },
          { label: "Local notification preview", detail: "Show demonstration notification previews.", value: notifications, set: setNotifications }
        ].map((item) => (
          <div className="ag-setting-row" key={item.label}>
            <div><strong>{item.label}</strong><p>{item.detail}</p></div>
            <button
              className={`ag-toggle ${item.value ? "on" : ""}`}
              role="switch"
              aria-checked={item.value}
              onClick={() => item.set(!item.value)}
            ><span /></button>
          </div>
        ))}
      </section>

      <section className="ag-panel ag-settings-panel">
        <div className="ag-panel-heading"><div className="ag-panel-title"><Icon name="database" /><h2>DATA SOURCE CONFIGURATION</h2></div></div>
        <div className="ag-data-notice"><Icon name="shield" size={15} /> No live telemetry provider is configured by this interface. Backend configuration is managed separately.</div>
        <div className="ag-setting-row"><div><strong>Application mode</strong><p>Independent project / demonstration interface</p></div><span className="ag-demo-tag">LOCAL</span></div>
        <div className="ag-setting-row"><div><strong>NASA affiliation</strong><p>AstroGuard is an independent project and is not affiliated with NASA.</p></div><span className="ag-demo-tag">INDEPENDENT</span></div>
      </section>
    </div>
  );
}

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="ag-login-screen">
      <div className="ag-login-card ag-panel">
        <Brand />
        <span className="ag-eyebrow">MISSION ACCESS</span>
        <h1>Welcome back.</h1>
        <p>Sign-in interface preview. Authentication must be connected to a verified identity provider before use.</p>
        <form onSubmit={(event) => {
          event.preventDefault();
          alert("Authentication is not configured. No credentials were transmitted.");
        }}>
          <label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="operator@example.com" required /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter password" required /></label>
          <button className="ag-primary-button" type="submit">CONTINUE <Icon name="arrow" size={16} /></button>
        </form>
        <div className="ag-data-notice"><Icon name="shield" size={15} /> Authentication is not connected. This form does not validate or transmit credentials.</div>
        <Link href="/" className="ag-login-back">Return to Mission Control</Link>
      </div>
    </div>
  );
}

export default function MissionControl({ section }: { section: Section }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (section === "login") {
    return <LoginPage />;
  }

  const activeSection: Section =
    pathname === "/telemetry" ? "telemetry" :
    pathname === "/anomalies" ? "anomalies" :
    pathname === "/investigations" ? "investigations" :
    pathname === "/models" ? "models" :
    pathname === "/settings" ? "settings" : section;

  return (
    <div className="ag-app">
      <Sidebar section={activeSection} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="ag-main">
        <Topbar onMenu={() => setSidebarOpen(true)} />

        <main className="ag-content">
          <PageHeading section={activeSection} />

          {activeSection === "overview" && <Overview />}
          {activeSection === "telemetry" && <TelemetryPage />}
          {activeSection === "anomalies" && <AnomaliesPage />}
          {activeSection === "investigations" && <InvestigationsPage />}
          {activeSection === "models" && <ModelsPage />}
          {activeSection === "settings" && <SettingsPage />}

          <footer className="ag-page-footer">
            <span>ASTROGUARD / SPACE SYSTEMS INTELLIGENCE</span>
            <span>INDEPENDENT PROJECT · INTERFACE / DEMO</span>
          </footer>
        </main>
      </div>
    </div>
  );
}