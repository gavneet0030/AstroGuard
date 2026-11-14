"use client";

import { useState } from "react";

const commands = [
  {
    id: "overview",
    label: "Overview",
    description: "Mission environment overview. No live provider is connected."
  },
  {
    id: "telemetry",
    label: "Telemetry",
    description: "Telemetry integration is pending provider configuration."
  },
  {
    id: "analysis",
    label: "Analysis",
    description: "Analytical workflows are awaiting validated source data."
  }
];

export default function MissionCommand() {
  const [active, setActive] = useState("overview");

  const selected = commands.find((item) => item.id === active) ?? commands[0];

  return (
    <section className="ag-dashboard-widget" aria-labelledby="mission-command-title">
      <div className="ag-dashboard-widget-heading">
        <span>COMMAND INTERFACE</span>
        <h2 id="mission-command-title">Mission command</h2>
      </div>

      <div className="ag-command-tabs" role="tablist" aria-label="Mission command views">
        {commands.map((command) => (
          <button
            key={command.id}
            type="button"
            role="tab"
            id={`mission-tab-${command.id}`}
            aria-controls="mission-command-panel"
            aria-selected={active === command.id}
            tabIndex={active === command.id ? 0 : -1}
            onClick={() => setActive(command.id)}
          >
            {command.label}
          </button>
        ))}
      </div>

      <div
        id="mission-command-panel"
        role="tabpanel"
        aria-labelledby={`mission-tab-${active}`}
        aria-live="polite"
        className="ag-command-panel"
      >
        <strong>{selected.label.toUpperCase()}</strong>
        <p>{selected.description}</p>
        <span className="ag-demo-tag">DEMONSTRATION INTERFACE</span>
      </div>
    </section>
  );
}