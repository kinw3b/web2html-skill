import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const src = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../scripts/serializer.js"),
  "utf8",
);
const start = src.indexOf("function svgHrefId");
const end = src.indexOf("async function fe");
const { svgHrefId, elementId } = vm.runInNewContext(
  `${src.slice(start, end)}; ({ svgHrefId, elementId })`,
);

test("svgHrefId matches Paper Snapshot 0.3.8+ / Paper-Bridge fragments (unchanged in 0.3.12)", () => {
  assert.equal(svgHrefId("#svg-1984002905_559"), "svg-1984002905_559");
  assert.equal(
    svgHrefId("https://kp-dover.framer.website/home-4?x=1#svg-1984002905_559"),
    "svg-1984002905_559",
  );
  assert.equal(svgHrefId("/icons.svg#arrow"), "arrow");
  assert.equal(svgHrefId("https://example.com/icon.svg"), "");
  assert.equal(svgHrefId("url(#icon-plus)"), "icon-plus");
  assert.equal(svgHrefId(""), "");
});

test("elementId does not call startsWith on an SVGAnimatedString-like id", () => {
  assert.equal(elementId({ id: "icon-plus" }), "icon-plus");
  assert.equal(
    elementId({
      id: { baseVal: "x-paper-toast", animVal: "x-paper-toast" },
      getAttribute(name) { return name === "id" ? "icon-plus" : ""; },
    }),
    "icon-plus",
  );
  assert.ok(!elementId({
    id: { baseVal: "x-paper-toast" },
    getAttribute() { return ""; },
  }).startsWith("x-paper-"));
});
