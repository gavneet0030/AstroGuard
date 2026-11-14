import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

function read(relative) {
  return fs.readFileSync(path.join(root, relative), "utf8");
}

test("command palette component exists", () => {
  assert.ok(fs.existsSync(path.join(root, "components/command-palette.tsx")));
});

test("command palette supports keyboard navigation", () => {
  const source = read("components/command-palette.tsx");
  assert.match(source, /ArrowDown/);
  assert.match(source, /ArrowUp/);
  assert.match(source, /Escape/);
  assert.match(source, /Enter/);
});

test("command palette has accessible dialog semantics", () => {
  const source = read("components/command-palette.tsx");
  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /aria-labelledby=/);
});

test("command palette includes verified frontend routes only", () => {
  const source = read("components/command-palette.tsx");
  for (const route of [
    'href: "/"',
    'href: "/telemetry"',
    'href: "/anomalies"',
    'href: "/investigations"',
    'href: "/models"',
    'href: "/settings"'
  ]) {
    assert.ok(source.includes(route), `Missing route ${route}`);
  }
});

test("application shell uses command palette", () => {
  const source = read("components/app-shell.tsx");
  assert.match(source, /CommandPalette/);
  assert.match(source, /setPaletteOpen/);
  assert.match(source, /ctrlKey/);
});

test("application shell uses inline vector brand mark", () => {
  const source = read("components/app-shell.tsx");
  assert.match(source, /<svg/);
  assert.doesNotMatch(source, /<img\s/);
});

test("application icon exists", () => {
  assert.ok(fs.existsSync(path.join(root, "app/icon.svg")));
});

test("command palette does not invent backend endpoints", () => {
  const source = read("components/command-palette.tsx");
  assert.doesNotMatch(source, /fetch\s*\(/);
  assert.doesNotMatch(source, /axios/);
});

test("no destructive git command is present in source", () => {
  const source = read("components/app-shell.tsx");
  assert.doesNotMatch(source, /git reset --hard/);
  assert.doesNotMatch(source, /git clean -fd/);
});
