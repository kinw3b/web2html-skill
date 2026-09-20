import test from "node:test";
import assert from "node:assert/strict";
import {
  emptyImageKind,
  findBreakpointImageGaps,
  isDeferredImageHole,
  isEmptyAvatarOverlay,
  isEmptyImageSlot,
  landerFamily,
  sectionSlug,
} from "../scripts/qa-breakpoint-images.mjs";

test("sectionSlug strips the desktop index prefix", () => {
  assert.equal(sectionSlug("06 · feature-section-03"), "feature-section-03");
  assert.equal(sectionSlug("feature-section-03"), "feature-section-03");
});

test("landerFamily groups home-desktop / 768 / 390", () => {
  assert.equal(landerFamily("home-desktop").family, "home");
  assert.equal(landerFamily("home-768").rank, 2);
  assert.equal(landerFamily("home-390").rank, 1);
  assert.equal(landerFamily("A/6 · home · states"), null);
});

test("isEmptyImageSlot flags a hollow photo Rectangle", () => {
  assert.equal(isEmptyImageSlot({ component: "Rectangle", w: 485, h: 344, childCount: 0 }), true);
  assert.equal(isEmptyImageSlot({ component: "Rectangle", w: 20, h: 20, childCount: 0 }), false);
  assert.equal(isEmptyImageSlot({ component: "Frame", w: 485, h: 344, childCount: 0, bg: "#fff" }), false);
  assert.equal(isEmptyImageSlot({ component: "Image", w: 485, h: 344, hasImageFill: false }), true);
});

test("findBreakpointImageGaps reports a tablet hole when desktop has the photo", () => {
  const findings = findBreakpointImageGaps([
    {
      name: "home-desktop",
      width: 1600,
      sections: [{ slug: "feature-section-03", filledImages: 4, emptyImageSlots: 0 }],
    },
    {
      name: "home-768",
      width: 768,
      sections: [{ slug: "feature-section-03", filledImages: 0, emptyImageSlots: 4 }],
    },
  ]);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].type, "breakpoint-image-gap");
  assert.equal(findings[0].severity, "high");
  assert.match(findings[0].detail, /Pitfall #58/);
});

test("emptyImageKind flags deferred-image Frames and circular SVG/file overlays", () => {
  const hole = {
    name: "deferred-image",
    component: "Frame",
    w: 50,
    h: 50,
    childCount: 0,
  };
  assert.equal(isDeferredImageHole(hole), true);
  assert.equal(emptyImageKind(hole), "deferred-image");
  assert.equal(isEmptyImageSlot(hole), false, "50×50 is below the hollow-Rectangle floor");

  const parent = { name: "avatar", component: "Frame", w: 56, h: 56 };
  const svg = { name: "placeholder", component: "SVG", w: 56, h: 56, childCount: 1 };
  const file = { name: "file", component: "Rectangle", w: 56, h: 56, childCount: 0 };
  assert.equal(isEmptyAvatarOverlay(svg, parent), true);
  assert.equal(isEmptyAvatarOverlay(file, parent), true);
  assert.equal(emptyImageKind(svg, parent), "avatar-overlay");
  assert.equal(emptyImageKind(file, parent), "avatar-overlay");

  const scribbleParent = { name: "line-2", component: "Frame", w: 420, h: 56 };
  const scribble = { name: "scribble", component: "SVG", w: 120, h: 20, childIds: ["path"] };
  assert.equal(emptyImageKind(scribble, scribbleParent), null);
});

test("findBreakpointImageGaps stays quiet when counts match", () => {
  const findings = findBreakpointImageGaps([
    {
      name: "home-desktop",
      width: 1600,
      sections: [{ slug: "feature-section-03", filledImages: 4, emptyImageSlots: 0 }],
    },
    {
      name: "home-768",
      width: 768,
      sections: [{ slug: "feature-section-03", filledImages: 4, emptyImageSlots: 0 }],
    },
  ]);
  assert.equal(findings.length, 0);
});
