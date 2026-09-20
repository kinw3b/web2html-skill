// Strip borders that CSS does not paint but Paper does.
//
// Two Framer leftovers become visible boxes after write_html:
//
// 1. `border-*-width` + `border-*-color` with no `border-*-style`.
//    CSS initial style is `none`, so the browser shows nothing. Paper reads
//    width+color and strokes a 3px black box on nav/footer links.
// 2. A real shorthand whose color is fully transparent —
//    `border: 1px solid rgba(42, 42, 42, 0)`. CSS is still invisible. Paper
//    drops the alpha and paints `#2A2A2A`.
//
// Real strokes (`border: 1px solid #090C1C`) are kept.
//
// Stage P (`assemble-lander` / `import-sections`) must run this before every
// write_html. Hover-reel `trim()` applies the same rules plus line-height /
// transform-origin fixes.

const SIDES = "top|right|bottom|left";
const ORPHAN_SIDE = new RegExp(`^border-(${SIDES})-(width|color)$`);
const COLOR_PROP = new RegExp(`^border(-(${SIDES}))?-color$`);

function valueOf(raw) {
  const i = raw.indexOf(":");
  return i < 0 ? "" : raw.slice(i + 1).trim();
}

export function isTransparentColor(value) {
  const v = String(value || "").trim().toLowerCase();
  if (!v || v === "transparent") return true;

  if (/^#(?:[0-9a-f]{4}|[0-9a-f]{8})$/.test(v)) {
    const a = v.length === 5 ? v[4] + v[4] : v.slice(7);
    return parseInt(a, 16) === 0;
  }

  const fn = /^(?:rgba?|hsla?)\((.+)\)$/.exec(v);
  if (!fn) return false;
  const body = fn[1].trim();
  const slash = body.split("/");
  if (slash.length === 2) {
    return parseAlpha(slash[1]) === 0;
  }
  if (!/^rgba|^hsla/.test(v)) return false;
  const parts = body.split(/[,\s]+/).filter(Boolean);
  return parts.length >= 4 && parseAlpha(parts[3]) === 0;
}

function parseAlpha(raw) {
  const s = String(raw).trim();
  if (s.endsWith("%")) return Number.parseFloat(s) / 100;
  return Number.parseFloat(s);
}

export function shorthandHasTransparentColor(value) {
  const v = String(value || "").trim();
  if (!v) return false;
  const colors = v.match(/(?:rgba?|hsla?)\([^)]+\)|#[0-9a-f]{3,8}|transparent/gi) || [];
  return colors.length > 0 && colors.every(isTransparentColor);
}

export function shouldDropBorderDecl(prop, value, present) {
  if (prop === "border" && shorthandHasTransparentColor(value)) return true;
  if (COLOR_PROP.test(prop) && isTransparentColor(value)) return true;
  const m = ORPHAN_SIDE.exec(prop);
  if (m && !present.has("border-style") && !present.has(`border-${m[1]}-style`)) {
    return true;
  }
  return false;
}

export function trimPaperStyles(html) {
  return String(html).replace(/style="([^"]*)"/g, (_m, css) => {
    const decls = css.split(";").map((s) => s.trim()).filter(Boolean).map((d) => {
      const i = d.indexOf(":");
      return { prop: d.slice(0, i).trim(), raw: d };
    });
    const present = new Set(decls.map((d) => d.prop));
    const kept = decls.filter((d) => !shouldDropBorderDecl(d.prop, valueOf(d.raw), present));
    return `style="${kept.map((d) => d.raw).join("; ")}"`;
  });
}
