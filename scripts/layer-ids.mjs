// Optional invisible 1.2 QA sidecar. Never written onto Paper frames.
//
// Paper layer-name stays the scrape name (or omitted). This module may still
// collect the serializer's internal `ids` arrays into `layer-ids.json` next to
// manifest.json. That file is not required to finish 1.2 and is not a 2.0 input.
// Do not stamp, join, or retag Paper from these keys.

import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { paperSectionName, sectionId } from "./section-ids.mjs";

/** Section-scoped prefix. Keeps `0.2.1` unique across ten sections. */
export function idPrefixFor(section, index) {
  return `${section?.id || sectionId(index)}-`;
}

/** Keep the serializer census intact; only add the Paper section label. */
export function sectionRows(rows = [], { section, index, desktop = false } = {}) {
  const label = paperSectionName(
    { id: section?.id || sectionId(index), slug: section?.slug || section?.name },
    { desktop },
  );
  return (rows || []).map((row) => persistCensusRow(row, label));
}

export function persistCensusRow(row = {}, section = null) {
  return {
    ...row,
    pcId: row.pcId,
    path: row.path,
    tag: row.tag ?? null,
    class: row.class ?? "",
    classes: Array.isArray(row.classes) ? row.classes : [],
    role: row.role ?? "",
    "data-framer-name": row["data-framer-name"] ?? row.framerName ?? "",
    section: section ?? row.section ?? null,
  };
}

export function buildLayerIds(sections = [], { url, width, desktop = false } = {}) {
  const rows = [];
  const bySection = [];
  sections.forEach((entry, index) => {
    const scoped = sectionRows(entry.ids, { section: entry.section, index, desktop });
    rows.push(...scoped);
    bySection.push({
      id: entry.section?.id || sectionId(index),
      slug: entry.section?.slug || entry.section?.name || null,
      section: scoped[0]?.section || null,
      ids: scoped.length,
    });
  });
  const seen = new Set();
  const duplicates = [];
  for (const row of rows) {
    if (seen.has(row.pcId)) duplicates.push(row.pcId);
    seen.add(row.pcId);
  }
  return {
    generatedFrom: "url-to-paper/serializer",
    url: url || null,
    width: width || null,
    writtenAt: new Date().toISOString(),
    total: rows.length,
    duplicates,
    sections: bySection,
    // pc-id → identity. Object form so a lookup is O(1) and diffs read cleanly.
    ids: Object.fromEntries(rows.map((row) => [row.pcId, row])),
  };
}

export function writeLayerIds(outDir, sections, meta = {}) {
  const payload = buildLayerIds(sections, meta);
  const file = join(outDir, "layer-ids.json");
  writeFileSync(file, JSON.stringify(payload, null, 2));
  return { file, total: payload.total, duplicates: payload.duplicates };
}
