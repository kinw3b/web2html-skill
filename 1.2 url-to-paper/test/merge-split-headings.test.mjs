import test from "node:test";
import assert from "node:assert/strict";
import {
  applySplitHeadingPlans,
  collectNodes,
  findSplitHeadings,
  headingMergeHtml,
  lineRowFromFrame,
  planSplitHeadingMerges,
  setHeadingText,
} from "../scripts/merge-split-headings.mjs";

/** prior-run hero: three Framer line-box Text siblings + a scribble SVG. */
function kpExpevoHeroNodes() {
  const nodes = new Map();
  const add = (n) => {
    nodes.set(n.id, {
      childCount: n.childIds?.length || 0,
      position: n.position || "relative",
      ...n,
    });
  };
  add({
    id: "2UH-0",
    name: "01 · hero",
    component: "Frame",
    childIds: ["2UP-0", "2UR-0", "2UT-0", "2UW-0"],
    w: 800,
    h: 300,
    worldX: 0,
    worldY: 0,
    alignItems: "center",
    textAlign: "center",
  });
  add({
    id: "2UP-0",
    parentId: "2UH-0",
    name: "Take",
    component: "Text",
    textContent: "Take",
    w: 180,
    h: 72,
    worldX: 310,
    worldY: 20,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  add({
    id: "2UR-0",
    parentId: "2UH-0",
    name: "control",
    component: "Text",
    textContent: "control",
    w: 280,
    h: 72,
    worldX: 260,
    worldY: 100,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  add({
    id: "2UT-0",
    parentId: "2UH-0",
    name: "scribble",
    component: "SVG",
    w: 120,
    h: 24,
    worldX: 480,
    worldY: 140,
    html: '<svg viewBox="0 0 120 24"><path d="M2 18 Q 60 0 118 16"/></svg>',
  });
  add({
    id: "2UW-0",
    parentId: "2UH-0",
    name: "of your personal spending today.",
    component: "Text",
    textContent: "of your personal spending today.",
    w: 720,
    h: 72,
    worldX: 40,
    worldY: 180,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  return nodes;
}

test("detector flags stacked heading line-boxes as split-heading", () => {
  const findings = findSplitHeadings(kpExpevoHeroNodes(), { artboard: "home-desktop" });
  assert.equal(findings.length, 1);
  assert.equal(findings[0].type, "split-heading");
  assert.equal(findings[0].severity, "high");
  assert.match(findings[0].detail, /Take control of your personal spending today/);
  assert.match(findings[0].detail, /Pitfall #69/);
});

test("merge helper emits one centered title and an absolute decorative SVG", () => {
  const nodes = kpExpevoHeroNodes();
  const plans = planSplitHeadingMerges(nodes, { artboard: "home-desktop" });
  assert.equal(plans.length, 1);
  assert.equal(plans[0].text, "Take control of your personal spending today.");
  assert.equal(plans[0].textAlign, "center");
  assert.deepEqual(plans[0].deleteIds, ["2UR-0", "2UW-0"]);
  assert.equal(plans[0].decorations.length, 1);
  assert.equal(plans[0].decorations[0].id, "2UT-0");
  assert.equal(plans[0].decorations[0].position, "absolute");
  assert.equal(plans[0].decorations[0].pointerEvents, "none");
  assert.equal(plans[0].decorations[0].decorative, true);

  const html = headingMergeHtml(plans[0]);
  assert.match(html, /text-align:\s*center/);
  assert.equal((html.match(/Take control of your personal spending today\./g) || []).length, 1);
  assert.doesNotMatch(html, />Take</);
  assert.match(html, /data-decorative/);
  assert.match(html, /position:\s*absolute/);
  assert.match(html, /pointer-events:\s*none/);
  assert.match(html, /<svg/);
});

test("after merge, detector is quiet on the repaired tree", () => {
  const nodes = kpExpevoHeroNodes();
  const plans = planSplitHeadingMerges(nodes, { artboard: "home-desktop" });
  const repaired = applySplitHeadingPlans(nodes, plans);
  const findings = findSplitHeadings(repaired, { artboard: "home-desktop" });
  assert.equal(findings.length, 0);
  const keep = repaired.get("2UP-0");
  assert.equal(keep.textContent, "Take control of your personal spending today.");
  assert.equal(keep.textAlign, "center");
  const svg = repaired.get("2UT-0");
  assert.equal(svg.position, "absolute");
  assert.equal(svg.pointerEvents, "none");
  assert.equal(svg.decorative, true);
  assert.equal(repaired.has("2UR-0"), false);
  assert.equal(repaired.has("2UW-0"), false);
});

/** Real prior-run hero: each line is a Text inside its own row Frame. */
function kpExpevoWrappedRowNodes() {
  const nodes = new Map();
  const add = (n) => {
    nodes.set(n.id, {
      childCount: n.childIds?.length || 0,
      position: n.position || "relative",
      ...n,
    });
  };
  add({
    id: "2UN-0",
    name: "heading",
    component: "Frame",
    childIds: ["2UO-0", "2UQ-0", "2UV-0"],
    w: 800,
    h: 300,
    worldX: 0,
    worldY: 0,
    alignItems: "center",
    textAlign: "center",
  });
  add({
    id: "2UO-0",
    parentId: "2UN-0",
    name: "line-1",
    component: "Frame",
    childIds: ["2UP-0"],
    w: 180,
    h: 72,
    worldX: 310,
    worldY: 20,
  });
  add({
    id: "2UP-0",
    parentId: "2UO-0",
    name: "Take",
    component: "Text",
    textContent: "Take",
    w: 180,
    h: 72,
    worldX: 310,
    worldY: 20,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  add({
    id: "2UQ-0",
    parentId: "2UN-0",
    name: "line-2",
    component: "Frame",
    childIds: ["2UR-0", "2US-0"],
    w: 400,
    h: 72,
    worldX: 200,
    worldY: 100,
  });
  add({
    id: "2UR-0",
    parentId: "2UQ-0",
    name: "control",
    component: "Text",
    textContent: "control",
    w: 280,
    h: 72,
    worldX: 260,
    worldY: 100,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  add({
    id: "2US-0",
    parentId: "2UQ-0",
    name: "scribble wrap",
    component: "Frame",
    childIds: ["2UT-0"],
    w: 120,
    h: 24,
    worldX: 480,
    worldY: 140,
    overflow: "hidden",
  });
  add({
    id: "2UT-0",
    parentId: "2US-0",
    name: "scribble",
    component: "SVG",
    w: 120,
    h: 24,
    worldX: 480,
    worldY: 140,
    html: '<svg viewBox="0 0 120 24"><path d="M2 18 Q 60 0 118 16"/></svg>',
  });
  add({
    id: "2UV-0",
    parentId: "2UN-0",
    name: "line-3",
    component: "Frame",
    childIds: ["2UW-0"],
    w: 720,
    h: 72,
    worldX: 40,
    worldY: 180,
  });
  add({
    id: "2UW-0",
    parentId: "2UV-0",
    name: "of your personal spending today.",
    component: "Text",
    textContent: "of your personal spending today.",
    w: 720,
    h: 72,
    worldX: 40,
    worldY: 180,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    color: "rgb(9, 12, 28)",
    textAlign: "center",
  });
  return nodes;
}

test("detector flags stacked one-Text row Frames as split-heading", () => {
  const findings = findSplitHeadings(kpExpevoWrappedRowNodes(), { artboard: "home-desktop" });
  assert.equal(findings.length, 1);
  assert.equal(findings[0].type, "split-heading");
  assert.equal(findings[0].severity, "high");
  assert.match(findings[0].detail, /Take control of your personal spending today/);
});

test("merge helper collapses wrapped rows into one centered title + absolute SVG", () => {
  const nodes = kpExpevoWrappedRowNodes();
  const plans = planSplitHeadingMerges(nodes, { artboard: "home-desktop" });
  assert.equal(plans.length, 1);
  assert.equal(plans[0].text, "Take control of your personal spending today.");
  assert.equal(plans[0].textAlign, "center");
  assert.equal(plans[0].keepId, "2UP-0");
  assert.ok(plans[0].deleteIds.includes("2UR-0"));
  assert.ok(plans[0].deleteIds.includes("2UW-0"));
  assert.ok(plans[0].deleteIds.includes("2UQ-0"));
  assert.ok(plans[0].deleteIds.includes("2UV-0"));
  assert.equal(plans[0].decorations.length, 1);
  assert.equal(plans[0].decorations[0].id, "2UT-0");
  assert.equal(plans[0].decorations[0].position, "absolute");
  assert.equal(plans[0].decorations[0].parentId, "2UN-0");

  const html = headingMergeHtml(plans[0]);
  assert.match(html, /text-align:\s*center/);
  assert.equal((html.match(/Take control of your personal spending today\./g) || []).length, 1);
  assert.match(html, /data-decorative/);
  assert.match(html, /position:\s*absolute/);

  const repaired = applySplitHeadingPlans(nodes, plans);
  assert.equal(findSplitHeadings(repaired, { artboard: "home-desktop" }).length, 0);
  assert.equal(repaired.get("2UP-0").textContent, "Take control of your personal spending today.");
  const svg = repaired.get("2UT-0");
  assert.equal(svg.position, "absolute");
  assert.equal(svg.parentId, "2UN-0");
  assert.equal(svg.pointerEvents, "none");
  assert.equal(svg.decorative, true);
  assert.equal(repaired.has("2UR-0"), false);
  assert.equal(repaired.has("2UQ-0"), false);
  assert.equal(repaired.has("2UV-0"), false);
});

test("keeps a real eyebrow + display pair that are different type styles", () => {
  const nodes = new Map();
  const add = (n) => nodes.set(n.id, { childCount: n.childIds?.length || 0, position: "relative", ...n });
  add({
    id: "wrap",
    name: "01 · hero",
    component: "Frame",
    childIds: ["eye", "title"],
    w: 800,
    h: 200,
    worldX: 0,
    worldY: 0,
  });
  add({
    id: "eye",
    parentId: "wrap",
    name: "New",
    component: "Text",
    textContent: "New",
    w: 60,
    h: 20,
    worldX: 370,
    worldY: 20,
    fontSize: "14px",
    fontWeight: "600",
    fontFamily: "Satoshi",
  });
  add({
    id: "title",
    parentId: "wrap",
    name: "Take control",
    component: "Text",
    textContent: "Take control",
    w: 400,
    h: 72,
    worldX: 200,
    worldY: 56,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
  });
  assert.equal(findSplitHeadings(nodes, { artboard: "home-desktop" }).length, 0);
  assert.equal(planSplitHeadingMerges(nodes, { artboard: "home-desktop" }).length, 0);
});

test("keeps a split when an explicit max-width is a wrap constraint", () => {
  const nodes = new Map();
  const add = (n) => nodes.set(n.id, { childCount: n.childIds?.length || 0, position: "relative", ...n });
  add({
    id: "wrap",
    name: "01 · hero",
    component: "Frame",
    childIds: ["a", "b"],
    w: 800,
    h: 200,
    worldX: 0,
    worldY: 0,
  });
  add({
    id: "a",
    parentId: "wrap",
    name: "Designed line one",
    component: "Text",
    textContent: "Designed line one that fills a narrow column",
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 20,
    fontSize: "32px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    maxWidth: "240px",
  });
  add({
    id: "b",
    parentId: "wrap",
    name: "Designed line two",
    component: "Text",
    textContent: "Designed line two stays a separate block",
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 80,
    fontSize: "32px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    maxWidth: "240px",
  });
  assert.equal(findSplitHeadings(nodes, { artboard: "home-desktop" }).length, 0);
});

test("keeps wrapped-row eyebrow + display that are different type styles", () => {
  const nodes = new Map();
  const add = (n) => nodes.set(n.id, { childCount: n.childIds?.length || 0, position: "relative", ...n });
  add({
    id: "wrap",
    name: "01 · hero",
    component: "Frame",
    childIds: ["eye-row", "title-row"],
    w: 800,
    h: 200,
    worldX: 0,
    worldY: 0,
  });
  add({
    id: "eye-row",
    parentId: "wrap",
    component: "Frame",
    childIds: ["eye"],
    w: 60,
    h: 20,
    worldX: 370,
    worldY: 20,
  });
  add({
    id: "eye",
    parentId: "eye-row",
    component: "Text",
    textContent: "New",
    w: 60,
    h: 20,
    worldX: 370,
    worldY: 20,
    fontSize: "14px",
    fontWeight: "600",
    fontFamily: "Satoshi",
  });
  add({
    id: "title-row",
    parentId: "wrap",
    component: "Frame",
    childIds: ["title"],
    w: 400,
    h: 72,
    worldX: 200,
    worldY: 56,
  });
  add({
    id: "title",
    parentId: "title-row",
    component: "Text",
    textContent: "Take control",
    w: 400,
    h: 72,
    worldX: 200,
    worldY: 56,
    fontSize: "72px",
    fontWeight: "700",
    fontFamily: "Satoshi",
  });
  assert.equal(findSplitHeadings(nodes, { artboard: "home-desktop" }).length, 0);
});

test("keeps wrapped rows when an explicit max-width is a wrap constraint", () => {
  const nodes = new Map();
  const add = (n) => nodes.set(n.id, { childCount: n.childIds?.length || 0, position: "relative", ...n });
  add({
    id: "wrap",
    name: "01 · hero",
    component: "Frame",
    childIds: ["r1", "r2"],
    w: 800,
    h: 200,
    worldX: 0,
    worldY: 0,
  });
  add({
    id: "r1",
    parentId: "wrap",
    component: "Frame",
    childIds: ["a"],
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 20,
    maxWidth: "240px",
  });
  add({
    id: "a",
    parentId: "r1",
    component: "Text",
    textContent: "Designed line one that fills a narrow column",
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 20,
    fontSize: "32px",
    fontWeight: "700",
    fontFamily: "Satoshi",
  });
  add({
    id: "r2",
    parentId: "wrap",
    component: "Frame",
    childIds: ["b"],
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 80,
    maxWidth: "240px",
  });
  add({
    id: "b",
    parentId: "r2",
    component: "Text",
    textContent: "Designed line two stays a separate block",
    w: 240,
    h: 48,
    worldX: 280,
    worldY: 80,
    fontSize: "32px",
    fontWeight: "700",
    fontFamily: "Satoshi",
  });
  assert.equal(findSplitHeadings(nodes, { artboard: "home-desktop" }).length, 0);
});

/** Expense-tracking heading: three row Frames, middle row is Text + SVG>Path. */
function expenseTrackingNodes() {
  const nodes = new Map();
  const add = (n) => {
    nodes.set(n.id, {
      childCount: n.childIds?.length || 0,
      position: n.position || "relative",
      ...n,
    });
  };
  add({
    id: "2VU-0",
    name: "title stack",
    component: "Frame",
    childIds: ["2VV-0", "2VX-0", "2W2-0"],
    w: 720,
    h: 220,
    worldX: 100,
    worldY: 800,
    alignItems: "center",
    textAlign: "center",
  });
  add({
    id: "2VV-0",
    parentId: "2VU-0",
    name: "line-1",
    component: "Frame",
    childIds: ["2VW-0"],
    w: 640,
    h: 56,
    worldX: 140,
    worldY: 800,
  });
  add({
    id: "2VW-0",
    parentId: "2VV-0",
    name: "Expense tracking…",
    component: "Text",
    textContent: "Expense tracking…",
    w: 640,
    h: 56,
    worldX: 140,
    worldY: 800,
    fontSize: "48px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    textAlign: "center",
  });
  add({
    id: "2VX-0",
    parentId: "2VU-0",
    name: "line-2",
    component: "Frame",
    childIds: ["2VY-0", "2W0-0"],
    w: 420,
    h: 56,
    worldX: 250,
    worldY: 860,
  });
  add({
    id: "2VY-0",
    parentId: "2VX-0",
    name: "precision",
    component: "Text",
    textContent: "precision",
    w: 280,
    h: 56,
    worldX: 260,
    worldY: 860,
    fontSize: "48px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    textAlign: "center",
  });
  add({
    id: "2W0-0",
    parentId: "2VX-0",
    name: "scribble",
    component: "SVG",
    childIds: ["2W1-0"],
    w: 120,
    h: 20,
    worldX: 520,
    worldY: 890,
    html: '<svg viewBox="0 0 120 20"><path d="M2 14 Q 60 0 118 12"/></svg>',
  });
  add({
    id: "2W1-0",
    parentId: "2W0-0",
    name: "Path",
    component: "SVGVisualElement",
    textContent: "M2 14 Q 60 0 118 12",
    w: 120,
    h: 20,
    worldX: 520,
    worldY: 890,
  });
  add({
    id: "2W2-0",
    parentId: "2VU-0",
    name: "line-3",
    component: "Frame",
    childIds: ["2W3-0"],
    w: 220,
    h: 56,
    worldX: 350,
    worldY: 920,
  });
  add({
    id: "2W3-0",
    parentId: "2W2-0",
    name: "control.",
    component: "Text",
    textContent: "control.",
    w: 220,
    h: 56,
    worldX: 350,
    worldY: 920,
    fontSize: "48px",
    fontWeight: "700",
    fontFamily: "Satoshi",
    textAlign: "center",
  });
  return nodes;
}

test("lineRowFromFrame keeps a row whose scribble SVG has a Path child", () => {
  const nodes = expenseTrackingNodes();
  const row = lineRowFromFrame(nodes.get("2VX-0"), nodes);
  assert.ok(row);
  assert.equal(row.text.id, "2VY-0");
  assert.equal(row.decorations.map((d) => d.id).join(","), "2W0-0");
});

test("detector flags the 2VU-0 expense-tracking stack (SVG>Path scribble)", () => {
  const findings = findSplitHeadings(expenseTrackingNodes(), { artboard: "home-desktop" });
  assert.equal(findings.length, 1);
  assert.equal(findings[0].type, "split-heading");
  assert.match(findings[0].detail, /Expense tracking… precision control\./);
  const plans = planSplitHeadingMerges(expenseTrackingNodes(), { artboard: "home-desktop" });
  assert.equal(plans[0].decorations[0].id, "2W0-0");
  const repaired = applySplitHeadingPlans(expenseTrackingNodes(), plans);
  assert.equal(findSplitHeadings(repaired, { artboard: "home-desktop" }).length, 0);
});

function mockPaperCall(tree) {
  return async (name, args) => {
    if (name === "get_children") {
      const n = tree.get(args.nodeId);
      const kids = (n?.childIds || []).map((id) => {
        const c = tree.get(id);
        return {
          id,
          name: c.name,
          component: c.component,
          worldX: c.worldX,
          worldY: c.worldY,
        };
      });
      return { content: [{ type: "text", text: JSON.stringify({ children: kids }) }] };
    }
    if (name === "get_node_info") {
      const n = tree.get(args.nodeId) || {};
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            width: n.w,
            height: n.h,
            worldX: n.worldX,
            worldY: n.worldY,
            textContent: n.textContent,
          }),
        }],
      };
    }
    if (name === "get_computed_styles") {
      const styles = {};
      for (const id of args.nodeIds || []) {
        const n = tree.get(id);
        if (!n) continue;
        styles[id] = {
          fontSize: n.fontSize,
          fontFamily: n.fontFamily,
          fontWeight: n.fontWeight,
          textAlign: n.textAlign,
          alignItems: n.alignItems,
          position: n.position,
        };
      }
      return { content: [{ type: "text", text: JSON.stringify({ styles }) }] };
    }
    throw new Error(`unexpected ${name}`);
  };
}

test("collectNodes walks named sections even when childCount is missing", async () => {
  const leaf = expenseTrackingNodes();
  const tree = new Map(leaf);
  tree.set("home-desktop", {
    id: "home-desktop",
    name: "home-desktop",
    component: "Artboard",
    childIds: ["01-features"],
  });
  tree.set("01-features", {
    id: "01-features",
    name: "01 · features",
    component: "Frame",
    childIds: ["2VU-0"],
    w: 1600,
    h: 900,
    worldX: 0,
    worldY: 0,
  });
  leaf.get("2VU-0").parentId = "01-features";
  const nodes = await collectNodes(mockPaperCall(tree), "home-desktop", {
    name: "home-desktop",
    component: "Artboard",
  }, 4);
  assert.ok(nodes.has("2VU-0"), "must reach the heading wrapper under 01 ·");
  assert.ok(nodes.has("2VW-0"), "must reach the first line Text");
  assert.ok(nodes.has("2W1-0"), "must reach the Path inside the scribble SVG");
  assert.equal(findSplitHeadings(nodes, { artboard: "home-desktop" }).length, 1);
});

test("setHeadingText uses Paper updates [{ nodeId, textContent }]", async () => {
  const calls = [];
  const call = async (name, args) => {
    calls.push({ name, args });
    return { content: [] };
  };
  await setHeadingText(call, "2VW-0", "Expense tracking… precision control.");
  assert.equal(calls[0].name, "set_text_content");
  assert.deepEqual(calls[0].args, {
    updates: [{ nodeId: "2VW-0", textContent: "Expense tracking… precision control." }],
  });
});
