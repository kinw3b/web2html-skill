// Compare homepage landers (desktop / 768 / 390) for missing feature photos.
// Image QA also matches icon box metrics (size, container, gap) from the
// live/pre-pesticide inventory at that width — not flex-wrap / 2+1 from
// another breakpoint (Pitfall #75).
//
// Framer's tablet/mobile serializer often emits
// `data:framer/asset-reference,<hash>.png` instead of an https URL. Paper
// cannot fetch that scheme, so the slot becomes a large empty Rectangle.
// Desktop still has a real Image. qa-paper flags both the hollow slot and
// the cross-breakpoint count gap (Pitfall #58).

export function sectionSlug(name) {
  return String(name || "")
    .replace(/^\d+\s*·\s*/u, "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

export function landerFamily(name) {
  const n = String(name || "").trim();
  const m = n.match(/^(.*)-(desktop|768|390|tablet|mobile)$/i);
  if (!m) return null;
  const hint = m[2].toLowerCase();
  const widthRank = { desktop: 3, tablet: 2, 768: 2, mobile: 1, 390: 1 };
  return { family: m[1].toLowerCase(), hint, rank: widthRank[hint] || 0 };
}

export function isPaintedFill(bg) {
  if (!bg) return false;
  const v = String(bg).trim().toLowerCase();
  if (!v || v === "transparent" || v === "none") return false;
  return !/rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0/.test(v);
}

export function isEmptyImageSlot(n) {
  const w = Number(n.w) || 0;
  const h = Number(n.h) || 0;
  if (w < 80 || h < 80) return false;
  if (n.textContent) return false;
  if (isPaintedFill(n.bg)) return false;
  if (n.component === "Image" && n.hasImageFill === false) return true;
  if (n.component === "Rectangle" && (n.childCount || 0) === 0) return true;
  return false;
}

const DEFERRED_IMAGE = /deferred-image/i;
const FILE_LAYER = /^file$/i;
const CIRCLE_MIN = 40;
const CIRCLE_MAX = 120;

export function isSmallCircleSlot(n) {
  const w = Number(n?.w) || 0;
  const h = Number(n?.h) || 0;
  if (w < CIRCLE_MIN || h < CIRCLE_MIN || w > CIRCLE_MAX || h > CIRCLE_MAX) return false;
  return Math.abs(w - h) <= 16;
}

export function isDeferredImageHole(n) {
  if (!DEFERRED_IMAGE.test(n?.name || "")) return false;
  if (n.textContent) return false;
  if (isPaintedFill(n.bg)) return false;
  const w = Number(n.w) || 0;
  const h = Number(n.h) || 0;
  if (w < 8 || h < 8) return false;
  if (n.component === "Image" && n.hasImageFill !== false) return false;
  return (n.childCount || 0) === 0 || n.hasImageFill === false;
}

export function isEmptyAvatarOverlay(n, parent) {
  if (!n) return false;
  const c = String(n.component || "");
  const name = String(n.name || "");
  const isSvg = c === "SVG";
  const isFile = FILE_LAYER.test(name) && (c === "Rectangle" || c === "Frame" || c === "");
  if (!isSvg && !isFile) return false;
  if (n.textContent && !isSvg) return false;
  if (isPaintedFill(n.bg) || n.hasImageFill) return false;
  const slot = parent && isSmallCircleSlot(parent) ? parent : n;
  return isSmallCircleSlot(slot);
}

/** Pitfall #68 — hollow slots, deferred-image holes, avatar SVG/file overlays. */
export function emptyImageKind(n, parent) {
  if (isEmptyImageSlot(n)) return "hollow-slot";
  if (isDeferredImageHole(n)) return "deferred-image";
  if (isEmptyAvatarOverlay(n, parent)) return "avatar-overlay";
  return null;
}

export function emptyImageDetail(n, kind) {
  const w = Math.round(Number(n?.w) || 0);
  const h = Math.round(Number(n?.h) || 0);
  if (kind === "deferred-image") {
    return `${w}×${h} Frame named deferred-image has no bitmap. Inventory vs live (Pitfall #68).`;
  }
  if (kind === "avatar-overlay") {
    return `empty ${n.component || "layer"} "${n.name || ""}" covers a circular avatar slot (Pitfall #68).`;
  }
  return `${w}×${h} ${n.component} has no bitmap. Pull the desktop file into this breakpoint (Pitfall #58).`;
}

export function findBreakpointImageGaps(boards) {
  const findings = [];
  const groups = new Map();
  for (const board of boards) {
    const fam = landerFamily(board.name);
    if (!fam) continue;
    if (!groups.has(fam.family)) groups.set(fam.family, []);
    groups.get(fam.family).push({ ...board, ...fam });
  }

  for (const [family, members] of groups) {
    if (members.length < 2) continue;
    members.sort((a, b) => b.rank - a.rank || (b.width || 0) - (a.width || 0));
    const reference = members[0];
    const refBySlug = new Map((reference.sections || []).map((s) => [s.slug, s]));

    for (const other of members.slice(1)) {
      for (const section of other.sections || []) {
        const ref = refBySlug.get(section.slug);
        if (!ref) continue;
        const refFilled = ref.filledImages || 0;
        const otherFilled = section.filledImages || 0;
        const holes = section.emptyImageSlots || 0;
        if (refFilled > 0 && otherFilled < refFilled) {
          findings.push({
            artboard: other.name,
            type: "breakpoint-image-gap",
            severity: "high",
            name: section.slug,
            detail:
              `${other.name} section "${section.slug}" has ${otherFilled} image(s)` +
              (holes ? ` and ${holes} empty photo slot(s)` : "") +
              `; ${reference.name} has ${refFilled}. ` +
              `Framer asset-reference srcs do not load in Paper — localize to the desktop file (Pitfall #58).`,
            family,
            reference: reference.name,
          });
        }
      }
    }
  }
  return findings;
}
