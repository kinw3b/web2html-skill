import assert from "node:assert/strict";
import { paperFileName } from "../scripts/create-paper-file.mjs";

const now = new Date("2026-08-30T12:05:00");
assert.equal(
  paperFileName({ projectRoot: "/tmp/templates/kp-thrive", now }),
  "kp-thrive 2026-08-30 1205",
);
assert.equal(
  paperFileName({ url: "https://kp-thrive.framer.website/home-01", now }),
  "kp-thrive.framer.website 2026-08-30 1205",
);
const a = paperFileName({ projectRoot: "/tmp/kp-thrive", now: new Date("2026-08-30T12:05:00") });
const b = paperFileName({ projectRoot: "/tmp/kp-thrive", now: new Date("2026-08-30T12:06:00") });
assert.notEqual(a, b, "two runs must not share a Paper file name");
console.log("ok");
