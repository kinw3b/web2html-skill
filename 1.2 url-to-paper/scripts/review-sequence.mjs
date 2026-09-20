// After source-section shots exist, the review sequence is 01, 02, 03…
// Chrome-only clips (nav, overlay bars) are not numbered. 01 is the first
// content band — hero, which already paints the nav. Hover and Source rows
// use this list, not the capture-time 01 · nav / 03 · hero ids.

import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { paperSectionName } from "./section-ids.mjs";

export const REVIEW_SEQUENCE_FILE = "review-sequence.json";

export function parsePaperSectionName(name = "") {
  const raw = String(name || "").trim();
  const m = raw.match(/^(\d{2})\s*·\s*(.+)$/);
  if (m) return { id: m[1], slug: m[2].trim(), paperName: raw };
  return { id: "", slug: raw, paperName: raw };
}

export function isReviewSection(s) {
  if (!s) return false;
  const slug = `${s.slug || ""} ${s.name || ""} ${s.label || ""}`.toLowerCase();
  if (s.chrome) return false;
  if (/(^|[^a-z])(nav|navbar|navigation|header|menubar)([^a-z]|$)/.test(slug) && !/footer/.test(slug)) {
    return false;
  }
  const h = Number(s.height ?? s.h ?? s.bbox?.h ?? 0);
  const top = Number(s.top ?? s.y ?? s.bbox?.y ?? 0);
  if (h > 0 && h <= 96 && top <= 80) return false;
  return true;
}

export function reviewSequenceSections(sections = []) {
  const rows = (sections || []).filter(isReviewSection);
  return rows.map((section, index) => {
    const id = String(index + 1).padStart(2, "0");
    const last = rows.length > 1 && index === rows.length - 1;
    const slug = last ? "footer" : (section.slug || section.name || `section-${index + 1}`);
    const captureId = section.captureId || section.id || null;
    return {
      ...section,
      captureId,
      id,
      slug,
      paperName: paperSectionName({ id, slug }, { desktop: true }),
      includes: index === 0 ? ["nav"] : section.includes || [],
    };
  });
}

export function writeReviewSequence(dir, sections, meta = {}) {
  const rows = reviewSequenceSections(sections);
  const payload = {
    source: "review",
    writtenAt: new Date().toISOString(),
    rule: "01 is the first content band (hero + nav). Chrome-only clips are not numbered.",
    ...meta,
    sections: rows.map((s) => ({
      id: s.id,
      slug: s.slug,
      name: s.name || s.slug,
      captureId: s.captureId || null,
      paperName: s.paperName,
      includes: s.includes || [],
      top: s.top ?? s.bbox?.y ?? null,
      height: s.height ?? s.h ?? s.bbox?.h ?? null,
      selector: s.selector || "",
    })),
  };
  const file = join(dir, REVIEW_SEQUENCE_FILE);
  writeFileSync(file, JSON.stringify(payload, null, 2));
  return { file, sections: payload.sections };
}

/** Match a Paper layer to a review row by slug, then by capture id. */
export function matchReviewRow(layerName, sequence = []) {
  const parsed = parsePaperSectionName(layerName);
  const slug = parsed.slug.toLowerCase();
  return sequence.find((s) => String(s.slug || "").toLowerCase() === slug)
    || sequence.find((s) => s.captureId && s.captureId === parsed.id)
    || null;
}
