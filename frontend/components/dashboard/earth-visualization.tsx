"use client";

import dynamic from "next/dynamic";

const EarthScene = dynamic(
  () => import("./earth-scene"),
  {
    ssr: false,
    loading: () => (
      <div className="ag-earth-fallback">
        <span className="ag-earth-orbit" aria-hidden="true" />
        <strong>CONCEPTUAL RENDER</strong>
        <span>NOT LIVE ORBITAL TELEMETRY</span>
      </div>
    )
  }
);

export default function EarthVisualization() {
  return (
    <section
      className="ag-earth-visualization"
      aria-label="Conceptual Earth visualization"
    >
      <div className="ag-earth-visualization-heading">
        <span>MISSION ENVIRONMENT</span>
        <span className="ag-demo-tag">INDEPENDENT PROJECT</span>
      </div>

      <EarthScene />

      <div className="ag-earth-visualization-caption">
        <strong>CONCEPTUAL RENDER</strong>
        <span>NOT LIVE ORBITAL TELEMETRY</span>
      </div>
    </section>
  );
}