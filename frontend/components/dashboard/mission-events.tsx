const events = [
  {
    id: "EVT-001",
    title: "Telemetry provider integration",
    status: "PENDING",
    detail: "Awaiting a configured and verified telemetry provider."
  },
  {
    id: "EVT-002",
    title: "Data validation pipeline",
    status: "PENDING",
    detail: "Awaiting a configured and verified telemetry provider."
  },
  {
    id: "EVT-003",
    title: "Anomaly model evaluation",
    status: "PENDING",
    detail: "Awaiting validated observation datasets."
  }
];

export default function MissionEvents() {
  return (
    <section className="ag-dashboard-widget" aria-labelledby="mission-events-title">
      <div className="ag-dashboard-widget-heading">
        <span>OPERATIONAL TIMELINE</span>
        <h2 id="mission-events-title">Mission events</h2>
      </div>

      <div className="ag-events-list">
        {events.map((event) => (
          <article className="ag-event-item" key={event.id}>
            <div className="ag-event-marker" aria-hidden="true" />
            <div>
              <span className="ag-event-id">{event.id}</span>
              <h3>{event.title}</h3>
              <p>{event.detail}</p>
            </div>
            <span className="ag-demo-tag">{event.status}</span>
          </article>
        ))}
      </div>
    </section>
  );
}