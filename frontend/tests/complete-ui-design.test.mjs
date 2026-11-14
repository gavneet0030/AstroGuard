import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

function read(file) {
  return fs.readFileSync(path.join(root, file), "utf8");
}

test("AstroGuard root route composes MissionExperience with mission control", () => {
  const home = read("app/page.tsx");
  const experience = read("components/dashboard/mission-experience.tsx");

  assert.match(home, /MissionExperience/);
  assert.match(experience, /import MissionControl from "@\/components\/astroguard\/mission-control"/);
  assert.match(experience, /<MissionControl\s+section="overview"\s*\/>/);
});

test("all six application sections have route integrations", () => {
  for (const route of [
    "app/telemetry/page.tsx",
    "app/anomalies/page.tsx",
    "app/investigations/page.tsx",
    "app/models/page.tsx",
    "app/settings/page.tsx",
    "app/login/page.tsx"
  ]) {
    assert.match(read(route), /MissionControl/);
  }
});

test("mission control contains the approved sidebar navigation", () => {
  const source = read("components/astroguard/mission-control.tsx");
  for (const label of [
    "Mission Control",
    "Telemetry",
    "Anomalies",
    "Investigations",
    "AI Models",
    "Space Explorer",
    "Satellite Registry",
    "Mission Planner",
    "Reports",
    "Settings"
  ]) {
    assert.ok(source.includes(label), `Missing navigation item: ${label}`);
  }
});

test("mission control contains the main Earth visualization", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /function EarthPanel/);
  assert.match(source, /ag-earth-globe/);
  assert.match(source, /ag-orbit-lines/);
  assert.match(source, /satellite-one/);
});

test("mission summary and four KPI cards are present", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /function MissionSummary/);
  assert.match(source, /function MetricCards/);
  assert.match(source, /Orbital Objects/);
  assert.match(source, /Telemetry Channels/);
  assert.match(source, /Anomaly Queue/);
  assert.match(source, /Model Confidence/);
});

test("mission activity has interactive filtering", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /function ActivityPanel/);
  assert.match(source, /setFilter/);
  assert.match(source, /All Activity/);
});

test("anomaly intelligence panel exists", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /function AnomalyIntelligence/);
  assert.match(source, /Severity Distribution/);
  assert.match(source, /Orbital Risk/);
});

test("mission pipeline includes all four stages", () => {
  const source = read("components/astroguard/mission-control.tsx");
  for (const stage of ["Observe", "Detect", "Investigate", "Report"]) {
    assert.ok(source.includes(stage));
  }
});

test("telemetry workspace has a data integrity disclaimer", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /Sample telemetry values are illustrative/);
});

test("anomaly records are marked as demonstration candidates", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /Candidate events are demonstration records/);
});

test("authentication does not claim to be operational", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /Authentication is not configured/);
  assert.match(source, /No credentials were transmitted/);
});

test("NASA affiliation disclaimer exists", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /not affiliated with NASA/);
});

test("global search and notification interaction exist", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /Search missions, objects, or analyses/);
  assert.match(source, /setNotificationsOpen/);
});

test("settings toggles are controlled", () => {
  const source = read("components/astroguard/mission-control.tsx");
  assert.match(source, /aria-checked/);
  assert.match(source, /setCompact/);
  assert.match(source, /setMotion/);
});

test("responsive design has tablet and mobile breakpoints", () => {
  const css = read("app/globals.css");
  assert.match(css, /max-width:\s*1250px/);
  assert.match(css, /max-width:\s*1050px/);
  assert.match(css, /max-width:\s*820px/);
  assert.match(css, /max-width:\s*560px/);
});

test("reduced motion support exists", () => {
  assert.match(read("app/globals.css"), /prefers-reduced-motion:\s*reduce/);
});

test("approved cyan palette is defined", () => {
  const css = read("app/globals.css");
  assert.match(css, /--ag-cyan:\s*#31d9f5/);
  assert.match(css, /--ag-bg:\s*#050a10/);
});

test("all application pages use the shared mission shell directly or through the experience composition", () => {
  const routes = [
    "app/page.tsx",
    "app/telemetry/page.tsx",
    "app/anomalies/page.tsx",
    "app/investigations/page.tsx",
    "app/models/page.tsx",
    "app/settings/page.tsx",
    "app/login/page.tsx"
  ];

  const experience = read("components/dashboard/mission-experience.tsx");

  assert.match(experience, /import MissionControl from "@\/components\/astroguard\/mission-control"/);
  assert.match(experience, /<MissionControl\s+section="overview"\s*\/>/);

  for (const route of routes) {
    const source = read(route);

    if (route === "app/page.tsx") {
      assert.match(source, /MissionExperience/);
    } else {
      assert.match(source, /@\/components\/astroguard\/mission-control/);
      assert.match(source, /MissionControl/);
    }
  }
});;