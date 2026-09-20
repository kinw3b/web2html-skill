import test from "node:test";
import assert from "node:assert/strict";
import { collapseAnimatedLabelStacks, flattenDecorativeAbs, isDecorativeAbs, stripAbsolutePaintFill } from "../scripts/flatten-decorative-abs.mjs";

const card = `<div style="position: relative; overflow: clip; width: 310px; height: 295px; border-radius: 16px; background-color: #FFFFFF"><div style="position: absolute; top: 0; right: 0; bottom: 0; left: 0; width: 310.078px; height: 295.023px; border-width: 1px; border-style: solid; border-color: rgb(234, 237, 240); border-radius: 16px"></div><p style="margin: 0">Sally Robson</p></div>`;

test("hoists a frozen 1px stroke overlay onto the card", () => {
  const out = flattenDecorativeAbs(card);
  assert.equal(out.removed.length, 1);
  assert.equal(out.removed[0].paint, "box-border");
  assert.match(out.html, /border: 1px solid #EAEDF0/);
  assert.match(out.html, /overflow: visible/);
  assert.doesNotMatch(out.html, /position: absolute/);
  assert.match(out.html, /Sally Robson/);
});

test("hoists a hairline row divider as border-bottom", () => {
  const row = `<div style="position: relative; width: 523px; height: 57px"><div style="position: absolute; inset: 0; width: 523.594px; height: 57px; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: rgb(234, 237, 240)"></div><span>Cashless Payment</span></div>`;
  const out = flattenDecorativeAbs(row);
  assert.equal(out.removed.length, 1);
  assert.match(out.html, /border-bottom: 1px solid #EAEDF0/);
  assert.doesNotMatch(out.html, /position: absolute/);
});

test("leaves a real absolute image / badge alone", () => {
  const hero = `<div style="position: relative; width: 400px; height: 400px"><img src="x.jpg" style="position: absolute; top: 20px; left: 20px; width: 120px; height: 160px" alt="" /><p>Copy</p></div>`;
  const out = flattenDecorativeAbs(hero);
  assert.equal(out.removed.length, 0);
  assert.match(out.html, /position: absolute/);
});

test("skips 2px hamburger / 3px capture hairlines", () => {
  const bar = `<div style="position: relative; width: 24px; height: 16px"><div style="position: absolute; inset: 0; height: 2px; background-color: rgb(8, 14, 19); border-width: 3px"></div></div>`;
  const out = flattenDecorativeAbs(bar);
  assert.equal(out.removed.length, 0);
});

test("hoists a 1.5px pill stroke overlay used on hover buttons", () => {
  const pill = `<a style="position: relative; width: 222px; height: 54px; background-image: linear-gradient(rgb(7, 8, 15) 0%, rgb(76, 80, 100) 100%)"><p>Try 14 Days Free Trial</p><div style="position: absolute; top: 0px; right: 0px; bottom: 0px; left: 0px; width: 221.766px; height: 54px; pointer-events: none; border-top-width: 1.5px; border-right-width: 1.5px; border-bottom-width: 1.5px; border-left-width: 1.5px; border-style: solid; border-color: rgb(9, 12, 28); border-radius: 28px"></div></a>`;
  const out = flattenDecorativeAbs(pill);
  assert.equal(out.removed.length, 1);
  assert.match(out.html, /border: 1\.5px solid #090C1C/);
  assert.doesNotMatch(out.html, /position: absolute/);
  assert.match(out.html, /linear-gradient/);
});

test("hoists a CSS gradient overlay onto the parent", () => {
  const pill = `<button style="position: relative; width: 200px; height: 48px; background-color: rgb(9, 12, 28)"><span>Demo</span><div style="position: absolute; inset: 0; background-image: linear-gradient(rgb(7, 8, 15) 0%, rgb(76, 80, 100) 100%); border-radius: 28px"></div></button>`;
  const out = flattenDecorativeAbs(pill);
  assert.equal(out.removed.length, 1);
  assert.match(out.html, /background-image: linear-gradient/);
  assert.doesNotMatch(out.html, /position: absolute/);
});

test("collapses Framer text-swap duplicate labels", () => {
  const stacked = `<a style="display: flex"><div style="display: flex; flex-direction: column; height: 30px; overflow-y: hidden"><div><p>Try 14 Days Free Trial</p></div><div><p>Try 14 Days Free Trial</p></div></div></a>`;
  const out = collapseAnimatedLabelStacks(stacked);
  assert.equal(out.collapsed.length, 1);
  assert.equal((out.html.match(/Try 14 Days Free Trial/g) || []).length, 1);
  assert.match(out.html, /justify-content: center/);
  assert.doesNotMatch(out.html, /height: 30px/);
});

test("isDecorativeAbs rejects media and text", () => {
  assert.equal(
    isDecorativeAbs({
      childStyle: { position: "absolute", top: "0", left: "0", right: "0", bottom: "0", "border-width": "1px" },
      parentStyle: { width: "100px", height: "100px" },
      hasMedia: true,
    }),
    false,
  );
});

test("hoists a Frame+Rectangle hover fill onto background-color (Pitfall #95)", () => {
  const pill = `<a style="position: relative; width: 220px; height: 54px; border-radius: 999px"><p>Get Started Now</p><div style="position: absolute; inset: 0; width: 220px; height: 54px"><div style="width: 220px; height: 54px; background-color: rgb(255, 255, 255); border-radius: 999px"></div></div></a>`;
  const out = flattenDecorativeAbs(pill);
  assert.equal(out.removed.length, 1);
  assert.match(out.html, /background-color: rgb\(255, 255, 255\)|background-color: #FFFFFF/);
  assert.doesNotMatch(out.html, /position: absolute/);
  assert.match(out.html, /Get Started Now/);
});

test("stripAbsolutePaintFill keeps background-color and drops abs geometry", () => {
  const pill = `<a style="position: relative; width: 220px; height: 54px"><div style="position: absolute; inset: 0; background-color: #C4A574"></div><p>Book A Room</p></a>`;
  const out = stripAbsolutePaintFill(pill);
  assert.ok(out.removed.length >= 1);
  assert.match(out.html, /background-color: #C4A574/);
  assert.doesNotMatch(out.html, /position: absolute/);
  assert.match(out.html, /Book A Room/);
});

