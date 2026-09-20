import test from "node:test";
import assert from "node:assert/strict";
import { trim } from "../scripts/trim-styles.mjs";

test("trim drops transparent text-link outlines Paper would paint", () => {
  const html = `<a style="display: flex; border: 1px solid rgba(42, 42, 42, 0); color: rgb(9, 12, 28)">Pricing</a>`;
  const out = trim(html);
  assert.doesNotMatch(out, /border:/);
  assert.match(out, /color: rgb\(9, 12, 28\)/);
});

test("trim keeps a real CTA stroke", () => {
  const html = `<a style="border: 1px solid #090C1C; line-height: 32px">Book a demo</a>`;
  const out = trim(html);
  assert.match(out, /border: 1px solid #090C1C/);
  assert.match(out, /line-height: 120%/);
});
