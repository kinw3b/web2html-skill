// Live source-tag census for HUD Semantics mode.
// img, h1–h6, p, ul, ol, a, button, form — assigned to Paper 01, 02, 03…
// Writes JSON + markdown. Paper layers rename to `h1 · …` so 2.2.b wrap matches.

import fs from "node:fs";
import path from "node:path";

export const SEMANTIC_TAGS = [
  "h1", "h2", "h3", "h4", "h5", "h6",
  "p", "ul", "ol", "img", "a", "button", "form",
];

export const SEMANTIC_SEL = SEMANTIC_TAGS.join(",");

export function normalizeSemText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

export function paperSemanticsName(tag, label) {
  const t = String(tag || "div").toLowerCase();
  const text = normalizeSemText(label).slice(0, 48) || t;
  return `${t} · ${text}`;
}

export function sectionForY(y, sections = []) {
  let best = null;
  let bestTop = -Infinity;
  for (const s of sections) {
    const top = Number(s.top ?? s.y ?? 0);
    const height = Number(s.height ?? s.h ?? 0);
    const bot = height > 0 ? top + height : Infinity;
    if (y >= top - 8 && y < bot + 8 && top >= bestTop) {
      best = s;
      bestTop = top;
    }
  }
  return best;
}

export function assignSemanticsNodes(nodes = [], sections = []) {
  return (nodes || []).map((node) => {
    const y = Number(node.y ?? node.cy ?? 0);
    const section = node.sectionId
      ? sections.find((s) => s.id === node.sectionId)
      : sectionForY(y, sections);
    const tag = String(node.tag || "").toLowerCase();
    const text = normalizeSemText(node.text || node.alt || "");
    return {
      tag,
      text,
      href: node.href || "",
      alt: node.alt || "",
      src: node.src || "",
      x: Math.round(Number(node.x) || 0),
      y: Math.round(y),
      w: Math.round(Number(node.w) || 0),
      h: Math.round(Number(node.h) || 0),
      sectionId: section?.id || node.sectionId || null,
      sectionLabel: section?.slug || node.sectionLabel || null,
      paperName: paperSemanticsName(tag, text || node.alt || tag),
    };
  }).filter((row) => SEMANTIC_TAGS.includes(row.tag));
}

export function groupSemanticsBySection(nodes = [], sections = []) {
  const groups = (sections || []).map((s) => ({
    id: s.id,
    slug: s.slug,
    nodes: [],
  }));
  const extra = { id: "00", slug: "unassigned", nodes: [] };
  const byId = new Map(groups.map((g) => [g.id, g]));
  for (const node of nodes) {
    const bucket = byId.get(node.sectionId) || extra;
    bucket.nodes.push(node);
  }
  return extra.nodes.length ? [...groups, extra] : groups;
}

export function buildSemanticWrapMap(nodes = []) {
  const map = {
    generatedFrom: "source-semantics",
    h1: [],
    h2: [],
    h3: [],
    faq: [],
    links: {},
    ctaComponents: [],
  };
  for (const node of nodes) {
    if (node.tag === "h1" && node.text && !map.h1.includes(node.text)) map.h1.push(node.text);
    if (node.tag === "h2" && node.text && !map.h2.includes(node.text)) map.h2.push(node.text);
    if (node.tag === "h3" && node.text && !map.h3.includes(node.text)) map.h3.push(node.text);
    if ((node.tag === "a" || node.tag === "button") && node.text) {
      map.links[node.text] = {
        href: node.href || "#",
        component: node.tag === "button" ? "button" : "a",
      };
    }
  }
  return map;
}

export function semanticsMarkdown(doc = {}) {
  const page = doc.page || "home";
  const lines = [
    `# Source semantics · ${page}`,
    "",
    "Live tags from the HUD **Semantics** mode. Paper desktop layers should",
    "be named `h1 · …` / `p · …` so 2.2.b wrap matches this census.",
    "",
  ];
  if (doc.url) lines.push(`Source: ${doc.url}`, "");
  for (const section of doc.sections || []) {
    lines.push(`## ${section.id} · ${section.slug}`, "");
    if (!section.nodes?.length) {
      lines.push("_No semantic tags in this band._", "");
      continue;
    }
    for (const node of section.nodes) {
      const extra = node.href ? ` → ${node.href}` : "";
      lines.push(`- \`<${node.tag}>\` ${node.text || node.alt || node.paperName}${extra}`);
    }
    lines.push("");
  }
  return `${lines.join("\n").trim()}\n`;
}

export function buildSemanticsDoc({ url, page, width, nodes, sections }) {
  const assigned = assignSemanticsNodes(nodes, sections);
  const grouped = groupSemanticsBySection(assigned, sections);
  return {
    generatedFrom: "source-semantics",
    capturedAt: new Date().toISOString(),
    url: url || "",
    page: page || "home",
    width: Number(width) || 1600,
    nodeCount: assigned.length,
    sections: grouped,
    wrapMap: buildSemanticWrapMap(assigned),
  };
}

export function semanticsOutputPaths({ captureDir, projectRoot, page } = {}) {
  const slug = page || "home";
  return {
    captureJson: captureDir ? path.join(captureDir, "source-semantics.json") : "",
    qaJson: projectRoot ? path.join(projectRoot, "qa", "source-semantics.json") : "",
    qaMd: projectRoot ? path.join(projectRoot, "qa", "source-semantics.md") : "",
    wrapMap: projectRoot ? path.join(projectRoot, "qa", "source-semantics-map.json") : "",
    siteJson: projectRoot ? path.join(projectRoot, "source-site", "semantics", `${slug}.json`) : "",
  };
}

export function inferSemanticsRoots({ sectionManifest, outDir } = {}) {
  let captureDir = "";
  let projectRoot = "";
  if (sectionManifest) {
    const dir = path.dirname(path.resolve(sectionManifest));
    captureDir = dir;
    if (path.basename(path.dirname(dir)) === "capture") {
      projectRoot = path.dirname(path.dirname(dir));
    }
  }
  if (!projectRoot && outDir) {
    const abs = path.resolve(outDir);
    const parent = path.dirname(abs);
    if (/^components/.test(path.basename(abs)) && path.basename(parent) === "source-site") {
      projectRoot = path.dirname(parent);
    }
  }
  return { captureDir, projectRoot };
}

export function writeSemanticsFiles(doc, paths = {}) {
  const md = semanticsMarkdown(doc);
  const written = [];
  for (const file of [paths.captureJson, paths.qaJson, paths.siteJson]) {
    if (!file) continue;
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`);
    written.push(file);
  }
  if (paths.qaMd) {
    fs.mkdirSync(path.dirname(paths.qaMd), { recursive: true });
    fs.writeFileSync(paths.qaMd, md);
    written.push(paths.qaMd);
  }
  if (paths.wrapMap) {
    fs.mkdirSync(path.dirname(paths.wrapMap), { recursive: true });
    fs.writeFileSync(paths.wrapMap, `${JSON.stringify(doc.wrapMap || {}, null, 2)}\n`);
    written.push(paths.wrapMap);
  }
  return written;
}
