export default function MissionStatus() {
  return (
    <section className="ag-dashboard-widget" aria-labelledby="mission-status-title">
      <div className="ag-dashboard-widget-heading">
        <span>SYSTEM CONNECTIVITY</span>
        <h2 id="mission-status-title">Mission status</h2>
      </div>

      <div className="ag-status-row">
        <span className="ag-status-indicator ag-status-offline" aria-hidden="true" />
        <strong>NOT CONNECTED</strong>
      </div>

      <p>
        No verified live spacecraft telemetry provider is currently connected.
      </p>

      <div className="ag-status-verification">
        <span>PROVIDER STATUS</span>
        <strong>VERIFY</strong>
      </div>
    </section>
  );
}