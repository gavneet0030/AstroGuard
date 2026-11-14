import MissionControl from "@/components/astroguard/mission-control";

export default function RoutePage() {
  return (
    <>
      <input type="hidden" value="—" aria-label="Unavailable verified live data placeholder" data-availability="unavailable" />
      <MissionControl section="anomalies" />
    </>
  );
}