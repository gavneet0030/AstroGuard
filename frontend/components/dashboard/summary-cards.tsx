import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Database
} from "lucide-react";

const cards = [
  {
    label: "Telemetry events",
    value: "—",
    note: "Awaiting telemetry API",
    icon: Activity,
    color: "blue"
  },
  {
    label: "Active anomalies",
    value: "—",
    note: "Awaiting anomaly API",
    icon: AlertTriangle,
    color: "amber"
  },
  {
    label: "Models deployed",
    value: "—",
    note: "Awaiting model inventory",
    icon: BrainCircuit,
    color: "violet"
  },
  {
    label: "Data records",
    value: "—",
    note: "Awaiting data metrics API",
    icon: Database,
    color: "green"
  }
];

export function SummaryCards() {
  return (
    <div className="summary-grid">
      {cards.map((card) => {
        const Icon = card.icon;

        return (
          <article className="metric-card" key={card.label}>
            <div className="metric-top">
              <span>{card.label}</span>
              <div className={`metric-icon ${card.color}`}>
                <Icon size={18} />
              </div>
            </div>
            <div className="metric-value">{card.value}</div>
            <div className="metric-note">{card.note}</div>
          </article>
        );
      })}
    </div>
  );
}