// Overlay nav is not a numbered section. After the content walk, the person
// picks the live bar. Fixed / sticky → position:absolute at 0,0 and last
// lander child (Pitfall #97). In-flow nav stays inside 01 · hero.

const OVERLAY = new Set(["fixed", "sticky"]);

export function isOverlayNavPosition(position) {
  return OVERLAY.has(String(position || "").toLowerCase());
}

/** Fixed/sticky, or a top-pinned full-width wrapper (Framer relative header). */
export function isOverlayNav({
  position,
  top,
  width,
  viewportWidth,
  containsOverlay = false,
} = {}) {
  if (isOverlayNavPosition(position) || containsOverlay) return true;
  const t = Number(top);
  const w = Number(width);
  const vw = Number(viewportWidth) || 1600;
  return Number.isFinite(t) && t <= 16 && Number.isFinite(w) && w >= vw * 0.55;
}

function firstTag(html = "") {
  const m = String(html).match(/^(\s*)(<[a-zA-Z][\w-]*)([^>]*)>/);
  if (!m) return null;
  return { lead: m[1], tag: m[2], attrs: m[3], full: m[0], rest: String(html).slice(m[0].length) };
}

function styleOf(attrs = "") {
  const m = attrs.match(/\sstyle=(["'])([\s\S]*?)\1/i);
  return m ? { quote: m[1], value: m[2], raw: m[0] } : null;
}

export function rewriteRootPosition(html = "", next = "") {
  const parsed = firstTag(html);
  if (!parsed || !next) return html;
  const style = styleOf(parsed.attrs);
  if (!style) {
    return `${parsed.lead}${parsed.tag} style="${next}"${parsed.attrs}>${parsed.rest}`;
  }
  let value = style.value
    .replace(/position\s*:\s*[^;]+;?/gi, "")
    .replace(/(?:left|top|right|bottom)\s*:\s*[^;]+;?/gi, "")
    .trim();
  value = `${next} ${value}`.replace(/\s+/g, " ").trim();
  const attrs = parsed.attrs.replace(style.raw, ` style=${style.quote}${value}${style.quote}`);
  return `${parsed.lead}${parsed.tag}${attrs}>${parsed.rest}`;
}

export function ensureAbsoluteOrigin(html = "") {
  return rewriteRootPosition(html, "position: absolute; left: 0px; top: 0px; right: auto; bottom: auto;");
}

/** Navigation frame specimens sit in flow — never Absolute on that board. */
export function ensureRelativeFlow(html = "") {
  return rewriteRootPosition(html, "position: relative; left: auto; top: auto; right: auto; bottom: auto;");
}

export function parkNavHtml(html, livePosition, metrics = {}) {
  if (!html) return { action: "empty", html: "" };
  const overlay = isOverlayNav({
    position: livePosition,
    top: metrics.top,
    width: metrics.width,
    viewportWidth: metrics.viewportWidth,
    containsOverlay: metrics.containsOverlay,
  });
  if (!overlay && !metrics.force) {
    return { action: "skip-inflow", html };
  }
  return { action: "overlay-last", html: ensureAbsoluteOrigin(html) };
}
