// Live-DOM inventory + inspect helpers for pre-pesticide.
//
// Used by the CLI (via a document adapter), the injected HUD, and unit tests.
// Keep this file free of Playwright / Node fs so the same functions can run
// inside page.evaluate after a thin adapter is built.

export const HUD_TAG = "x-paper-prepesticide";
export const HUD_ID = "x-paper-prepesticide";
export const HUD_STYLE_ID = "x-paper-prepesticide-css";
export const HUD_OUTLINE_ID = "x-paper-prepesticide-outline";

export const LANDMARK_TAGS = [
  "header",
  "nav",
  "main",
  "section",
  "footer",
  "form",
  "img",
  "a",
  "button",
  "h1",
  "h2",
  "h3",
];

export const SECTION_ROOT_TAGS = ["header", "section", "footer", "nav", "main"];

const VOID = new Set([
  "area",
  "base",
  "br",
  "col",
  "embed",
  "hr",
  "img",
  "input",
  "link",
  "meta",
  "param",
  "source",
  "track",
  "wbr",
]);

/** Same skip the Paper serializer uses (serializer.js: tag or id). */
export function isSerializerSkip(tagName, id) {
  const tag = String(tagName || "").toLowerCase();
  const ident = String(id || "");
  return tag.startsWith("x-paper-") || ident.startsWith("x-paper-");
}

export function isHudSkipEl(el) {
  if (!el) return true;
  const tag = tagOf(el);
  if (isSerializerSkip(tag, el.id)) return true;
  if (typeof el.closest === "function") {
    try {
      if (el.closest(HUD_TAG) || el.closest("x-paper-hud")) return true;
    } catch {
      /* custom-element closest is fine; ignore selector errors */
    }
  }
  return false;
}

export function tagOf(el) {
  return String(el?.tagName || "").toLowerCase();
}

export function slugify(text, fallback = "section") {
  const s = String(text || "")
    .trim()
    .toLowerCase()
    .replace(/['’"]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .split("-")
    .slice(0, 5)
    .join("-")
    .slice(0, 40);
  return s || fallback;
}

export function isLandmarkTag(tag) {
  return LANDMARK_TAGS.includes(String(tag || "").toLowerCase());
}

export function paperComponentType(el) {
  const tag = tagOf(el);
  if (tag === "img") return "Image";
  if (tag === "svg" || (typeof el.closest === "function" && el.closest("svg") && tag !== "div")) {
    if (tag === "svg" || tag.startsWith("svg") || ["path", "g", "use", "circle", "rect", "line"].includes(tag)) {
      return "SVG";
    }
  }
  if (tag === "svg") return "SVG";
  const text = String(el.textContent || "").replace(/\s+/g, " ").trim();
  const textTags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "button", "label", "li"];
  if (textTags.includes(tag) && text && tag !== "img") return "Text";
  return "Frame";
}

export function paintRole(el) {
  const tag = tagOf(el);
  const ariaHidden = el.getAttribute?.("aria-hidden") === "true";
  const role = el.getAttribute?.("role") || "";
  if (ariaHidden || role === "presentation" || role === "none") return "decorative";

  if (tag === "img") {
    const alt = el.getAttribute?.("alt");
    const w = num(el.naturalWidth) || num(el.getAttribute?.("width")) || 0;
    const h = num(el.naturalHeight) || num(el.getAttribute?.("height")) || 0;
    if (alt === "" && w > 0 && h > 0 && w * h < 80 * 80) return "decorative";
    return "content";
  }

  if (tag === "svg") {
    const titled = typeof el.querySelector === "function" && el.querySelector("title");
    const box = bboxOf(el);
    if (!titled && box.w * box.h < 80 * 80) return "decorative";
    return titled ? "content" : "decorative";
  }

  const pe = el.getAttribute?.("data-decorative") === "true";
  if (pe) return "decorative";
  return "content";
}

export function textSnippet(el, max = 80) {
  const t = String(el.textContent || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!t) return "";
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

export function bboxOf(el) {
  if (typeof el.getBoundingClientRect === "function") {
    const r = el.getBoundingClientRect();
    const sy = typeof window !== "undefined" ? window.scrollY || 0 : el._scrollY || 0;
    const sx = typeof window !== "undefined" ? window.scrollX || 0 : el._scrollX || 0;
    return {
      x: Math.round((r.left || 0) + sx),
      y: Math.round((r.top || 0) + sy),
      w: Math.round(r.width || 0),
      h: Math.round(r.height || 0),
    };
  }
  const b = el._bbox || {};
  return {
    x: Math.round(b.x || 0),
    y: Math.round(b.y || 0),
    w: Math.round(b.w || num(el.getAttribute?.("width")) || 0),
    h: Math.round(b.h || num(el.getAttribute?.("height")) || 0),
  };
}

export function childCounts(root) {
  const counts = { img: 0, a: 0, button: 0, form: 0, h: 0, svg: 0 };
  walk(root, (el) => {
    if (el === root) return;
    if (isHudSkipEl(el)) return;
    const tag = tagOf(el);
    if (tag === "img") counts.img += 1;
    else if (tag === "a") counts.a += 1;
    else if (tag === "button") counts.button += 1;
    else if (tag === "form") counts.form += 1;
    else if (/^h[1-6]$/.test(tag)) counts.h += 1;
    else if (tag === "svg") counts.svg += 1;
  });
  return counts;
}

export function sectionSlugFor(el, sectionEls) {
  let n = el;
  while (n) {
    const hit = sectionEls.find((s) => s.el === n);
    if (hit) return hit.slug;
    n = n.parentElement || n.parentNode || null;
    if (n && n.nodeType && n.nodeType !== 1) n = n.parentElement || null;
  }
  const framer = el.getAttribute?.("data-framer-name");
  if (framer) return slugify(framer, "section");
  const heading = typeof el.querySelector === "function" ? el.querySelector("h1, h2, h3") : null;
  if (heading && heading.textContent) return slugify(heading.textContent, "section");
  return slugify(tagOf(el), "section");
}

export function inspectRecord(el, sectionEls = [], { twPrefix = "" } = {}) {
  const tag = tagOf(el);
  const classes = classListOf(el);
  const img = tag === "img" ? el : typeof el.querySelector === "function" ? el.querySelector("img") : null;
  const record = {
    tag,
    id: el.id || "",
    classes,
    framerName: el.getAttribute?.("data-framer-name") || "",
    role: el.getAttribute?.("role") || "",
    text: textSnippet(el),
    landmark: isLandmarkTag(tag),
    landmarkKind: isLandmarkTag(tag) ? tag : "",
    paperType: paperComponentType(el),
    paintRole: paintRole(el),
    sectionSlug: sectionSlugFor(el, sectionEls),
    bbox: bboxOf(el),
    tailwind: tailwindFromBox(el, { prefix: twPrefix }),
  };
  if (img) {
    record.img = {
      src: img.currentSrc || img.src || img.getAttribute?.("src") || "",
      alt: img.getAttribute?.("alt") ?? img.alt ?? "",
      w: num(img.naturalWidth) || num(img.getAttribute?.("width")) || 0,
      h: num(img.naturalHeight) || num(img.getAttribute?.("height")) || 0,
    };
  }
  record.paperRow = paperRow(record);
  return record;
}

export function paperRow(record) {
  const bits = [
    `slug=${record.sectionSlug || "—"}`,
    `type=${record.paperType}`,
    `role=${record.paintRole}`,
    `tag=${record.tag}`,
  ];
  if (record.framerName) bits.push(`framer=${record.framerName}`);
  if (record.img?.src) bits.push(`img=${record.img.src}`);
  return bits.join("  ");
}

// Box metrics only (w / h / gap). Do not emit flex-wrap — that is
// breakpoint layout, not something to copy from 768 onto 1600 (Pitfall #75).
export function tailwindFromBox(el, { prefix = "" } = {}) {
  const p = prefix || "";
  const box = bboxOf(el);
  const cs = el._computed || {};
  const cls = [];
  if (box.w) cls.push(`${p}w-[${box.w}px]`);
  if (box.h) cls.push(`${p}h-[${box.h}px]`);
  const display = cs.display || el.getAttribute?.("data-display") || "";
  if (display === "flex") {
    cls.push(`${p}flex`);
    if (cs.flexDirection === "column") cls.push(`${p}flex-col`);
    const items = flexAlign(cs.alignItems);
    const just = flexJustify(cs.justifyContent);
    if (items) cls.push(`${p}${items}`);
    if (just) cls.push(`${p}${just}`);
    const gap = parsePx(cs.gap);
    if (gap != null) cls.push(`${p}gap-[${gap}px]`);
  }
  const radius = parsePx(cs.borderRadius);
  if (radius) cls.push(radius >= 999 ? `${p}rounded-full` : `${p}rounded-[${radius}px]`);
  const bg = cs.backgroundColor;
  if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") {
    cls.push(`${p}bg-[${cssColorToTw(bg)}]`);
  }
  const color = cs.color;
  if (color) cls.push(`${p}text-[${cssColorToTw(color)}]`);
  const fs = parsePx(cs.fontSize);
  if (fs) cls.push(`${p}text-[${fs}px]`);
  const fw = cs.fontWeight;
  if (fw && fw !== "400" && fw !== "normal") cls.push(`${p}font-[${fw}]`);
  return cls.join(" ");
}

export function cssImageUrls(value) {
  if (!value || value === "none") return [];
  const out = [];
  const re = /url\(\s*(['"]?)([^'")]+)\1\s*\)/gi;
  let m;
  while ((m = re.exec(String(value)))) out.push(m[2]);
  return out;
}

export function backgroundSrcOf(el) {
  const style = el.getAttribute?.("style") || "";
  const fromStyle = style.match(/background-image\s*:\s*([^;]+)/i);
  if (fromStyle) {
    const urls = cssImageUrls(fromStyle[1]);
    if (urls[0]) return urls[0];
  }
  const computed = el._computed?.backgroundImage;
  if (computed) {
    const urls = cssImageUrls(computed);
    if (urls[0]) return urls[0];
  }
  return "";
}

export function collectInventory(doc, { sections: detected = [], twPrefix = "" } = {}) {
  const body = doc.body || doc.documentElement;
  const all = queryAll(doc, "*").filter((el) => !isHudSkipEl(el));
  const sectionEls = resolveSectionEls(doc, detected);

  const sections = sectionEls.map((s) => ({
    slug: s.slug,
    tag: tagOf(s.el),
    framerName: s.el.getAttribute?.("data-framer-name") || s.framerName || "",
    bbox: s.bbox || bboxOf(s.el),
    childCounts: childCounts(s.el),
    selector: s.selector || "",
    chrome: !!s.chrome,
  }));

  const images = [];
  for (const el of queryAll(doc, "img").filter((n) => !isHudSkipEl(n))) {
    images.push({
      src: el.currentSrc || el.src || el.getAttribute?.("src") || "",
      alt: el.getAttribute?.("alt") ?? el.alt ?? "",
      w: num(el.naturalWidth) || num(el.getAttribute?.("width")) || 0,
      h: num(el.naturalHeight) || num(el.getAttribute?.("height")) || 0,
      section: sectionSlugFor(el, sectionEls),
      via: "img",
    });
  }
  for (const el of all) {
    if (tagOf(el) === "img") continue;
    const src = backgroundSrcOf(el);
    if (!src) continue;
    const box = bboxOf(el);
    images.push({
      src,
      alt: el.getAttribute?.("aria-label") || el.getAttribute?.("data-framer-name") || "",
      w: box.w,
      h: box.h,
      section: sectionSlugFor(el, sectionEls),
      via: "background",
    });
  }

  const forms = queryAll(doc, "form")
    .filter((el) => !isHudSkipEl(el))
    .map((el) => ({
      id: el.id || "",
      name: el.getAttribute?.("name") || "",
      action: el.getAttribute?.("action") || "",
      method: (el.getAttribute?.("method") || "get").toLowerCase(),
      fields: queryAll(el, "input, textarea, select, button").filter((n) => !isHudSkipEl(n)).length,
      section: sectionSlugFor(el, sectionEls),
      bbox: bboxOf(el),
    }));

  const landmarks = all
    .filter((el) => isLandmarkTag(tagOf(el)) || ["banner", "navigation", "main", "contentinfo"].includes(el.getAttribute?.("role") || ""))
    .map((el) => ({
      tag: tagOf(el),
      id: el.id || "",
      framerName: el.getAttribute?.("data-framer-name") || "",
      role: el.getAttribute?.("role") || "",
      section: sectionSlugFor(el, sectionEls),
      bbox: bboxOf(el),
    }));

  return {
    sections,
    images,
    forms,
    landmarks,
    totals: {
      sections: sections.length,
      images: images.length,
      forms: forms.length,
      landmarks: landmarks.length,
    },
    twPrefix,
  };
}

export function resolveSectionEls(doc, detected) {
  const seen = new Map();
  const out = [];

  const push = (el, hint = {}) => {
    if (!el || isHudSkipEl(el)) return;
    if (out.some((s) => s.el === el)) return;
    let slug = hint.name || hint.slug;
    if (!slug) {
      const framer = el.getAttribute?.("data-framer-name");
      if (framer) slug = slugify(framer, tagOf(el));
      else if (el.id) slug = slugify(el.id, tagOf(el));
      else {
        const heading = typeof el.querySelector === "function" ? el.querySelector("h1, h2, h3") : null;
        slug = heading?.textContent ? slugify(heading.textContent, tagOf(el)) : slugify(tagOf(el), "section");
      }
    }
    if (seen.has(slug)) {
      const n = seen.get(slug) + 1;
      seen.set(slug, n);
      slug = `${slug}-${n}`;
    } else {
      seen.set(slug, 1);
    }
    out.push({
      el,
      slug,
      selector: hint.selector || "",
      framerName: hint.framerName || el.getAttribute?.("data-framer-name") || "",
      chrome: !!hint.chrome,
      bbox: hint.w
        ? { x: 0, y: hint.top || 0, w: hint.w, h: hint.h || 0 }
        : bboxOf(el),
    });
  };

  if (detected.length) {
    for (const s of detected) {
      const el = s.el || (s.selector && typeof doc.querySelector === "function" ? doc.querySelector(s.selector) : null);
      push(el, s);
    }
    return out;
  }

  // Fixture / no detector: semantic bands, outermost only.
  const candidates = queryAll(doc, "header, nav, section, footer, main, [data-framer-name]").filter((el) => {
    if (isHudSkipEl(el)) return false;
    const tag = tagOf(el);
    if (tag === "main") return false;
    if (SECTION_ROOT_TAGS.includes(tag) || el.getAttribute?.("data-framer-name")) return true;
    return false;
  });

  const roots = candidates.filter((el) => !candidates.some((o) => o !== el && contains(o, el)));
  for (const el of roots) push(el);
  return out;
}

export function classListOf(el) {
  if (el.classList && typeof el.classList.length === "number") {
    return Array.from(el.classList).filter((c) => c && !c.startsWith("x-paper-") && !c.startsWith("qa-"));
  }
  const raw = String(el.className || el.getAttribute?.("class") || "");
  if (!raw || raw === "[object SVGAnimatedString]") return [];
  return raw.split(/\s+/).filter((c) => c && !c.startsWith("x-paper-") && !c.startsWith("qa-"));
}

/**
 * Minimal HTML → document-like tree for fixture tests (no jsdom).
 * Handles the tags pre-pesticide inventories; not a general HTML parser.
 */
export function documentFromHtml(html) {
  const stripped = String(html)
    .replace(/<!doctype[^>]*>/i, "")
    .replace(/<!--[\s\S]*?-->/g, "");
  const root = parseFragment(stripped);
  const htmlEl = findTag(root, "html") || root;
  const body = findTag(htmlEl, "body") || htmlEl;

  const doc = {
    body,
    documentElement: htmlEl,
    querySelector(sel) {
      return queryAll(doc, sel)[0] || null;
    },
    querySelectorAll(sel) {
      return queryAll(doc, sel);
    },
  };
  return doc;
}

function parseFragment(html) {
  const root = makeEl("document-fragment");
  const stack = [root];
  const re = /<\/?([a-zA-Z][\w:-]*)([^>]*)\/?>|([^<]+)/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[3] != null) {
      const text = m[3];
      if (text.trim()) stack[stack.length - 1].childNodes.push(makeText(text));
      continue;
    }
    const tag = m[1].toLowerCase();
    const rawAttrs = m[2] || "";
    const closing = m[0].startsWith("</");
    const selfClosing = VOID.has(tag) || /\/\s*$/.test(rawAttrs) || m[0].endsWith("/>");
    if (closing) {
      for (let i = stack.length - 1; i > 0; i--) {
        if (tagOf(stack[i]) === tag) {
          stack.length = i;
          break;
        }
      }
      continue;
    }
    const el = makeEl(tag, parseAttrs(rawAttrs));
    stack[stack.length - 1].childNodes.push(el);
    el.parentElement = stack[stack.length - 1].tagName === "DOCUMENT-FRAGMENT" ? null : stack[stack.length - 1];
    if (el.parentElement && tagOf(el.parentElement) === "document-fragment") el.parentElement = null;
    // Re-parent: if parent is fragment, leave null; else link.
    const parent = stack[stack.length - 1];
    if (parent && tagOf(parent) !== "document-fragment") el.parentElement = parent;
    if (!selfClosing) stack.push(el);
  }
  // Fix parentElement for fragment children (html)
  for (const child of root.childNodes) {
    if (child.nodeType === 1) child.parentElement = null;
    relink(child, null);
  }
  return root;
}

function relink(el, parent) {
  if (!el || el.nodeType !== 1) return;
  el.parentElement = parent;
  for (const c of el.childNodes) relink(c, el);
}

function makeEl(tag, attrs = {}) {
  const el = {
    nodeType: 1,
    tagName: tag.toUpperCase(),
    id: attrs.id || "",
    className: attrs.class || "",
    attrs,
    childNodes: [],
    parentElement: null,
    get children() {
      return this.childNodes.filter((n) => n.nodeType === 1);
    },
    get textContent() {
      return this.childNodes.map((n) => n.textContent || "").join("");
    },
    get src() {
      return this.attrs.src || "";
    },
    get alt() {
      return this.attrs.alt ?? "";
    },
    get naturalWidth() {
      return num(this.attrs.width) || 0;
    },
    get naturalHeight() {
      return num(this.attrs.height) || 0;
    },
    getAttribute(name) {
      if (name === "class") return this.className || null;
      const v = this.attrs[name];
      return v == null ? null : String(v);
    },
    getBoundingClientRect() {
      return {
        left: num(this.attrs["data-x"]) || 0,
        top: num(this.attrs["data-y"]) || 0,
        width: num(this.attrs.width) || (SECTION_ROOT_TAGS.includes(tagOf(this)) ? 1600 : 100),
        height: num(this.attrs.height) || (SECTION_ROOT_TAGS.includes(tagOf(this)) ? 200 : 40),
      };
    },
    querySelector(sel) {
      return queryAll(this, sel)[0] || null;
    },
    querySelectorAll(sel) {
      return queryAll(this, sel);
    },
    closest(sel) {
      let n = this;
      while (n) {
        if (matches(n, sel)) return n;
        n = n.parentElement;
      }
      return null;
    },
  };
  return el;
}

function makeText(text) {
  return { nodeType: 3, textContent: text, childNodes: [], parentElement: null };
}

function parseAttrs(raw) {
  const attrs = {};
  const re = /([:@A-Za-z_][\w:.-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+)))?/g;
  let m;
  while ((m = re.exec(raw))) {
    attrs[m[1]] = m[2] ?? m[3] ?? m[4] ?? "";
  }
  return attrs;
}

function queryAll(root, selector) {
  const sels = String(selector)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const out = [];
  const start = root.body && root.documentElement ? root.documentElement : root;
  walk(start, (el) => {
    if (sels.some((s) => matches(el, s))) out.push(el);
  });
  return out;
}

function matches(el, sel) {
  if (!el || el.nodeType !== 1) return false;
  const tag = tagOf(el);
  if (sel === "*") return true;
  if (sel === HUD_TAG) return tag === HUD_TAG;
  if (sel.startsWith("#")) return el.id === sel.slice(1);
  const attr = sel.match(/^\[([^\]]+)\]$/);
  if (attr) {
    const [name, raw] = attr[1].split("=");
    if (raw == null) return el.getAttribute(name) != null;
    return el.getAttribute(name) === raw.replace(/^["']|["']$/g, "");
  }
  const tagged = sel.match(/^([a-z0-9-]+)(\[([^\]]+)\])?$/i);
  if (tagged) {
    if (tagged[1].toLowerCase() !== tag) return false;
    if (!tagged[3]) return true;
    const [name, raw] = tagged[3].split("=");
    if (raw == null) return el.getAttribute(name) != null;
    return el.getAttribute(name) === raw.replace(/^["']|["']$/g, "");
  }
  // "h1, h2, h3" already split; support "input, textarea"
  return tag === sel.toLowerCase();
}

function walk(el, fn) {
  if (!el || el.nodeType !== 1) return;
  fn(el);
  for (const c of el.children || el.childNodes?.filter?.((n) => n.nodeType === 1) || []) {
    walk(c, fn);
  }
}

function contains(outer, inner) {
  let n = inner?.parentElement;
  while (n) {
    if (n === outer) return true;
    n = n.parentElement;
  }
  return false;
}

function findTag(el, tag) {
  if (!el) return null;
  if (tagOf(el) === tag) return el;
  for (const c of el.children || []) {
    const hit = findTag(c, tag);
    if (hit) return hit;
  }
  return null;
}

function num(v) {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  const n = parseFloat(v);
  return Number.isNaN(n) ? 0 : n;
}

function parsePx(v) {
  if (v == null || v === "" || v === "0px" || v === "normal") return null;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : Math.round(n);
}

function flexAlign(v) {
  if (v === "center") return "items-center";
  if (v === "flex-end") return "items-end";
  if (v === "flex-start") return "items-start";
  return "";
}

function flexJustify(v) {
  if (v === "center") return "justify-center";
  if (v === "space-between") return "justify-between";
  if (v === "flex-end") return "justify-end";
  if (v === "flex-start") return "justify-start";
  return "";
}

function cssColorToTw(v) {
  const s = String(v).trim();
  const hex = rgbToHex(s);
  return hex || s.replace(/\s+/g, "");
}

function rgbToHex(v) {
  const m = String(v).match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  if (!m) return "";
  const h = (n) => Number(n).toString(16).padStart(2, "0");
  return `#${h(m[1])}${h(m[2])}${h(m[3])}`;
}
