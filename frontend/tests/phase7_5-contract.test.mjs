import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("dashboard home renders mission experience", () => {
  const page = read("app/page.tsx");
  assert.match(page, /MissionExperience/);
});

test("mission experience includes major workspaces", () => {
  const source = read("components/dashboard/mission-experience.tsx");
  assert.match(source, /MissionCommand/);
  assert.match(source, /MissionEvents/);
  assert.match(source, /MissionStatus/);
  assert.match(source, /EarthVisualization/);
});

test("Earth visualization is lazy loaded", () => {
  const source = read("components/dashboard/mission-experience.tsx");
  assert.match(source, /dynamic\(/);
  assert.match(source, /ssr:\s*false/);
});

test("Three.js import is deferred", () => {
  const source = read("components/dashboard/earth-scene.tsx");
  assert.match(source, /await import\("three"\)/);
});

test("Three.js renderer uses low power preference", () => {
  const source = read("components/dashboard/earth-scene.tsx");
  assert.match(source, /powerPreference:\s*"low-power"/);
});

test("visualization has reduced motion fallback", () => {
  const source = read("components/dashboard/earth-scene.tsx");
  assert.match(source, /prefers-reduced-motion/);
  assert.match(source, /setStatus\("fallback"\)/);
});

test("visualization cleans up renderer and animation", () => {
  const source = read("components/dashboard/earth-scene.tsx");
  assert.match(source, /cancelAnimationFrame/);
  assert.match(source, /renderer\?\.dispose/);
  assert.match(source, /resizeObserver\?\.disconnect/);
});

test("visualization labels conceptual render honestly", () => {
  const source = read("components/dashboard/earth-visualization.tsx");
  assert.match(source, /CONCEPTUAL RENDER/);
  assert.match(source, /NOT LIVE ORBITAL TELEMETRY/);
});

test("mission command has accessible tabs", () => {
  const source = read("components/dashboard/mission-command.tsx");
  assert.match(source, /role="tablist"/);
  assert.match(source, /aria-selected/);
  assert.match(source, /aria-live="polite"/);
});

test("mission status does not claim live telemetry", () => {
  const source = read("components/dashboard/mission-status.tsx");
  assert.match(source, /NOT CONNECTED/);
  assert.match(source, /VERIFY/);
});

test("mission events clearly mark pending integrations", () => {
  const source = read("components/dashboard/mission-events.tsx");
  assert.match(source, /PENDING/);
  assert.match(source, /awaiting a configured and verified telemetry provider/i);
});

test("responsive design breakpoints exist", () => {
  const css = read("app/globals.css");
  assert.match(css, /max-width:\s*1100px/);
  assert.match(css, /max-width:\s*820px/);
  assert.match(css, /max-width:\s*560px/);
});

test("reduced motion stylesheet exists", () => {
  const css = read("app/globals.css");
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test("NASA affiliation is not claimed", () => {
  const files = [
    "components/dashboard/mission-experience.tsx",
    "components/dashboard/earth-visualization.tsx"
  ];
  const combined = files.map(read).join("\n");
  assert.match(combined, /INDEPENDENT PROJECT/);
});