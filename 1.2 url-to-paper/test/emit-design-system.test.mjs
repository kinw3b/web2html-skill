import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { emitDesignSystem, tokensCss } from "../scripts/emit-design-system.mjs";

const css = tokensCss([
  { type: "color", name: "--color-ink", value: "#111" },
  { type: "fontWeight", name: "--font-weight-medium", value: 500 },
  { name: "--skip-me" },
]);
assert.match(css, /--color-ink: #111;/);
assert.match(css, /--font-weight-medium: 500;/);
assert.doesNotMatch(css, /skip-me/);

const root = mkdtempSync(join(tmpdir(), "emit-ds-"));
mkdirSync(join(root, "design-library"), { recursive: true });
writeFileSync(
  join(root, "design-library", "library.json"),
  JSON.stringify({
    file: "TEST",
    proposedTokens: [
      { type: "color", name: "--color-ink", value: "#111111", source: "mined" },
      { type: "color", name: "--color-surface", value: "#FFFFFF", source: "mined" },
      { type: "color", name: "--color-accent", value: "#2051FF", source: "mined" },
      { type: "fontFamily", name: "--font-sans", value: "Inter, sans-serif", family: "Inter", source: "mined" },
      { type: "fontSize", name: "--text-base", value: "16px", source: "tailwind-default" },
    ],
  }),
);
const receipt = emitDesignSystem(root);
assert.equal(receipt.ok, true);
assert.equal(receipt.generatedFrom, "url-to-paper/emit-design-system");
const page = readFileSync(join(root, "rebuild", "design-system.html"), "utf8");
const tokens = readFileSync(join(root, "rebuild", "css", "tokens.css"), "utf8");
assert.match(page, /css\/tokens.css/);
assert.match(page, /css\/fonts.css/);
assert.match(page, /data-page="design-system"/);
assert.match(page, /Foundations|DESIGN SYSTEM/i);
assert.match(page, /var\(--color-ink\)/);
assert.match(page, /var\(--color-surface\)/);
assert.match(tokens, /--color-accent: #2051FF;/);
assert.match(tokens, /--font-sans:/);
console.log("ok");
