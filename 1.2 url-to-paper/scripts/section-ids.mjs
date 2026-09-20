// Desktop section IDs live ON the layer name. "Fix 08" means the eighth
// desktop section. Never create a sibling "Desktop section IDs" legend
// artboard — Paper cannot create comments, so the name is the comment.
// Tablet / phone keep their slugs. A/6 labels always use the desktop id.

import { writeFileSync } from "node:fs";
import { join } from "node:path";

export const sectionId = (index) => String(index + 1).padStart(2, "0");

export function isDesktopCapture({ width, name } = {}) {
  const w = Number(width);
  if (Number.isFinite(w) && w >= 1400) return true;
  return /desktop/i.test(String(name || ""));
}

export function stampSectionIds(sections, { desktop = false } = {}) {
  return (sections || []).map((section, index) => {
    const id = desktop ? (section.id || sectionId(index)) : section.id || null;
    return {
      ...section,
      id,
      slug: section.slug || section.name || null,
    };
  });
}

export const SECTION_ID_LEGEND = "Desktop section IDs";
const NAME_MAX = 50;

/** Paper layer name: desktop = "01 · slug". Other widths keep the slug. */
export function paperSectionName(section, { desktop = false } = {}) {
  const slug = section?.slug || section?.name || "";
  if (desktop && section?.id) {
    const label = slug && slug !== section.id ? `${section.id} · ${slug}` : String(section.id);
    return label.length > NAME_MAX ? label.slice(0, NAME_MAX) : label;
  }
  return section?.name || section?.slug || section?.id || "section";
}

/** Delete leftover legend boards. Layer names are the source of truth. */
export async function retireSectionIdLegend({ call, boards = [], log } = {}) {
  const hits = boards.filter((b) => b.name === SECTION_ID_LEGEND);
  if (!hits.length) return [];
  await call("delete_nodes", { nodeIds: hits.map((b) => b.id) });
  log?.(`retired ${hits.length} "${SECTION_ID_LEGEND}" board(s) — names are the comment`);
  return hits;
}

export function sectionIndexRows(sections) {
  return (sections || []).map((section, index) => ({
    id: section.id || sectionId(index),
    slug: section.slug || section.name || null,
    name: section.name || null,
    top: section.top ?? null,
    h: section.h ?? section.height ?? null,
  }));
}

export function writeSectionIndex(outDir, sections, meta = {}) {
  const rows = sectionIndexRows(sections);
  const payload = {
    ...meta,
    source: "desktop",
    writtenAt: new Date().toISOString(),
    sections: rows,
  };
  const file = join(outDir, "section-ids.json");
  writeFileSync(file, JSON.stringify(payload, null, 2));
  return { file, sections: rows };
}
