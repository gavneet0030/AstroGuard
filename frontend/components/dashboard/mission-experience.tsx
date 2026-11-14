"use client";

import dynamic from "next/dynamic";
import MissionControl from "@/components/astroguard/mission-control";
import MissionCommand from "./mission-command";
import MissionEvents from "./mission-events";
import MissionStatus from "./mission-status";

const EarthVisualization = dynamic(
  () => import("./earth-visualization"),
  {
    ssr: false,
    loading: () => (
      <div className="ag-earth-loading" role="status">
        Preparing conceptual visualization...
      </div>
    )
  }
);

export default function MissionExperience() {
  return (
    <>
      <div className="ag-experience-visualization">
        <EarthVisualization />
      </div>

      <MissionControl section="overview" />

      <section className="ag-dashboard-support-grid" aria-label="Mission support workspaces">
        <MissionCommand />
        <MissionStatus />
        <MissionEvents />
      </section>
    </>
  );
}