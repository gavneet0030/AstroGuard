import test from "node:test";
import assert from "node:assert/strict";

test("frontend package exposes required validation scripts", async () => {
  const fs = await import("node:fs");

  const packageJson = JSON.parse(
    fs.readFileSync(
      new URL("../package.json", import.meta.url),
      "utf8"
    )
  );

  assert.equal(typeof packageJson.scripts.typecheck, "string");
  assert.equal(typeof packageJson.scripts.test, "string");
  assert.equal(typeof packageJson.scripts.build, "string");
});

test("verified API paths are explicitly declared in the API client", async () => {
  const fs = await import("node:fs");

  const source = fs.readFileSync(
    new URL("../lib/api.ts", import.meta.url),
    "utf8"
  );

  assert.ok(source.includes('"/health"'));
  assert.ok(source.includes('"/ready"'));
  assert.ok(
    source.includes('"/api/v1/system/database/health"')
  );
});

test("unverified business screens do not contain fabricated metric values", async () => {
  const fs = await import("node:fs");

  const pages = [
    "../app/telemetry/page.tsx",
    "../app/anomalies/page.tsx",
    "../app/investigations/page.tsx",
    "../app/models/page.tsx"
  ];

  for (const page of pages) {
    const source = fs.readFileSync(
      new URL(page, import.meta.url),
      "utf8"
    );

    assert.ok(
      source.includes('value="—"'),
      `${page} should use an unavailable placeholder`
    );
  }
});

test("login page does not render credential inputs", async () => {
  const fs = await import("node:fs");

  const source = fs.readFileSync(
    new URL("../app/login/page.tsx", import.meta.url),
    "utf8"
  );

  assert.doesNotMatch(source, /type=["']password["']/i);
  assert.doesNotMatch(source, /type=["']email["']/i);
});

test("API client does not embed a secret-looking API key", async () => {
  const fs = await import("node:fs");

  const source = fs.readFileSync(
    new URL("../lib/api.ts", import.meta.url),
    "utf8"
  );

  assert.doesNotMatch(source, /sk-[A-Za-z0-9]{20,}/);
});
