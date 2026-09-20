import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rewriteFramerAssetReferences } from "../scripts/localize-html-images.mjs";

test("rewrites data:framer/asset-reference to a local paper-asset", () => {
  const dir = mkdtempSync(join(tmpdir(), "framer-ref-"));
  const file = "RnBz9ly9edvJiRIoFNBDnvuBOP8.png";
  writeFileSync(join(dir, file), "png");
  const html = `<img src="data:framer/asset-reference,${file}?originalFilename=feature-img8.png&amp;preferredSize=auto" />`;
  const mapped = [];
  const missing = [];
  const seen = new Map();
  const out = rewriteFramerAssetReferences(html, [dir], { mapped, missing, seen });
  assert.equal(missing.length, 0);
  assert.equal(mapped.length, 1);
  assert.match(out, /paper-asset:\/\//);
  assert.doesNotMatch(out, /data:framer\/asset-reference/);
});

test("leaves an unresolved asset-reference and records missing", () => {
  const html = `<img src="data:framer/asset-reference,missing-hash.png" />`;
  const missing = [];
  const out = rewriteFramerAssetReferences(html, ["/tmp/does-not-exist-assets"], { mapped: [], missing, seen: new Map() });
  assert.match(out, /data:framer\/asset-reference/);
  assert.equal(missing.length, 1);
});
