import test from "node:test";
import assert from "node:assert/strict";
import { censusKey, sidecarKeys, compareCensus } from "../scripts/layer-ids-census.mjs";

test("quote marks normalize so live and sidecar join", () => {
  assert.equal(
    censusKey("h3", "“One of a kind restaurant”"),
    censusKey("h3", '"One of a kind restaurant"'),
  );
});

test("imgs collapse to one key so count is the join", () => {
  assert.equal(censusKey("img", "hero.png"), "img|img");
  assert.equal(censusKey("img", ""), "img|img");
});

test("missing live heading fails the census", () => {
  const side = sidecarKeys({
    "pc-06-0.0": { tag: "h2", text: "What Our Customers Say" },
  });
  const live = [
    censusKey("h2", "What Our Customers Say"),
    censusKey("h3", "Simply delicious"),
  ];
  const report = compareCensus(live, side);
  assert.equal(report.ok, false);
  assert.equal(report.missing[0].key, censusKey("h3", "Simply delicious"));
});

test("empty icon anchors join as <A>", () => {
  const side = sidecarKeys({
    "pc-00-0.2": { tag: "a", text: "" },
    b: { tag: "a", href: "https://twitter.com/" },
  });
  const live = [censusKey("a", "<A>"), censusKey("a", "<A>")];
  assert.equal(side[0], censusKey("a", "<A>"));
  assert.equal(compareCensus(live, side).ok, true);
});

test("card <a> uses textContent concat, not innerText spaces", () => {
  const side = sidecarKeys({
    a: { tag: "a", text: "Apr 8, 2022How to prepare a delicious gluten free sushi" },
  });
  const live = [censusKey("a", "Apr 8, 2022How to prepare a delicious gluten free sushi")];
  assert.equal(compareCensus(live, side).ok, true);
});

test("sidecar covering every live key is green", () => {
  const side = sidecarKeys({
    a: { tag: "h3", text: "“The best restaurant”" },
    b: { tag: "h3", text: "“Simply delicious”" },
    c: { tag: "p", text: "Los Angeles, CA" },
    d: { tag: "p", text: "Los Angeles, CA" },
    e: { tag: "img", src: "x.png" },
  });
  const live = [
    censusKey("h3", '"The best restaurant"'),
    censusKey("h3", '"Simply delicious"'),
    censusKey("p", "Los Angeles, CA"),
    censusKey("p", "Los Angeles, CA"),
    censusKey("img", "photo"),
  ];
  assert.equal(compareCensus(live, side).ok, true);
});
