import test from "node:test";
import assert from "node:assert/strict";

function normalizeState(value) {
  if (typeof value !== "string") {
    return "unknown";
  }

  const normalized = value.trim().toLowerCase();

  // Failure states must be evaluated before healthy states.
  // Otherwise "unhealthy" contains the substring "healthy".
  if (
    normalized === "unhealthy" ||
    normalized.includes("error") ||
    normalized.includes("failed") ||
    normalized.includes("unavailable")
  ) {
    return "unavailable";
  }

  if (
    normalized.includes("degraded") ||
    normalized.includes("warning")
  ) {
    return "degraded";
  }

  if (
    normalized === "ok" ||
    normalized === "healthy" ||
    normalized === "ready" ||
    normalized === "operational"
  ) {
    return "operational";
  }

  return "unknown";
}

test("healthy status is operational", () => {
  assert.equal(normalizeState("healthy"), "operational");
});

test("ready status is operational", () => {
  assert.equal(normalizeState("ready"), "operational");
});

test("degraded status is degraded", () => {
  assert.equal(normalizeState("degraded"), "degraded");
});

test("warning status is degraded", () => {
  assert.equal(normalizeState("warning"), "degraded");
});

test("unhealthy status is unavailable", () => {
  assert.equal(normalizeState("unhealthy"), "unavailable");
});

test("failed status is unavailable", () => {
  assert.equal(normalizeState("failed"), "unavailable");
});

test("error status is unavailable", () => {
  assert.equal(normalizeState("error"), "unavailable");
});

test("unavailable status is unavailable", () => {
  assert.equal(normalizeState("unavailable"), "unavailable");
});

test("unknown values remain unknown", () => {
  assert.equal(normalizeState("pending"), "unknown");
});

test("empty values remain unknown", () => {
  assert.equal(normalizeState(""), "unknown");
});

test("non-string values remain unknown", () => {
  assert.equal(normalizeState(null), "unknown");
});

test("numeric values remain unknown", () => {
  assert.equal(normalizeState(200), "unknown");
});

test("whitespace is normalized", () => {
  assert.equal(normalizeState("  healthy  "), "operational");
});
