import test from "node:test";
import assert from "node:assert/strict";
import { isEntrancePaint, restEntranceStyles } from "../scripts/settle-page.mjs";

test("Framer appear leftover is rest-painted (opacity 0 + translateY 28)", () => {
  const style = {
    opacity: "0",
    transform: "translate(0px, 28px)",
    position: "relative",
    display: "block",
    visibility: "visible",
  };
  assert.equal(isEntrancePaint(style), true);
  const rest = restEntranceStyles(style);
  assert.equal(rest.opacity, "1");
  assert.equal(rest.transform, "none");
});

test("mid-fade FAQ wrapper with translate is rest-painted", () => {
  const rest = restEntranceStyles({
    opacity: "0.18",
    transform: "translate(0px, 28px)",
    position: "static",
    display: "flex",
  });
  assert.equal(rest.opacity, "1");
  assert.equal(rest.transform, "none");
});

test("designed muted opacity without a translate is kept", () => {
  const style = { opacity: "0.6", transform: "none", position: "static", display: "block" };
  assert.equal(isEntrancePaint(style), false);
  assert.equal(restEntranceStyles(style).opacity, "0.6");
});

test("absolute overlay at opacity 0 is not rest-painted (serializer still drops it)", () => {
  const style = {
    opacity: "0",
    transform: "translate(0px, 8px)",
    position: "absolute",
    display: "block",
  };
  assert.equal(isEntrancePaint(style), false);
  assert.equal(restEntranceStyles(style).opacity, "0");
});

test("in-flow opacity 0 without transform is still rest-painted", () => {
  assert.equal(isEntrancePaint({ opacity: "0", position: "static", display: "block" }), true);
  assert.equal(restEntranceStyles({ opacity: "0", position: "relative" }).opacity, "1");
});
