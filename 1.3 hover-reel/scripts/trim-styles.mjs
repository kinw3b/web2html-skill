// Clean url-to-paper serializer output before handing it to Paper's write_html.
//
// Three classes of removal, all lossless for rendering:
//
// 1. Logical-property duplicates (border-block-*, inline-size, block-size…) —
//    the physical twin (border-*, width, height) is already in the same rule.
// 2. Paint-only properties Paper does not render (caret-color, outline-color,
//    column-rule-color, text-emphasis-color, appearance, unicode-bidi…).
// 3. THE IMPORTANT ONE: invisible Framer borders that Paper paints.
//    (a) border-<side>-width / -color with no border-<side>-style — CSS paints
//        nothing (initial style is `none`); Paper reads width+color as a 3px box.
//    (b) `border: 1px solid rgba(42, 42, 42, 0)` — CSS is still invisible; Paper
//        drops the alpha and strokes #2A2A2A around nav/footer text links.
//    Stage P now runs the same rules via url-to-paper `trimPaperStyles`.
//
// Plus one ADDITION, same species as (3) — a default that differs between the
// two renderers, so silence means two different pictures. See TRANSFORM_ORIGIN.
//
// Typically cuts the payload to ~25-35% of the raw serialization.
//
//   import { trim } from './trim-styles.mjs'
//   node trim-styles.mjs <inDir> <outDir>

import fs from 'node:fs';
import path from 'node:path';

const DROP = new RegExp('^(' + [
  'border-(block|inline)-', 'border-(start|end)-(start|end)-radius',
  'inset-(block|inline)', 'margin-(block|inline)', 'padding-(block|inline)',
  'overflow-(block|inline)', 'contain-intrinsic', 'scroll-(margin|padding)',
  'block-size', 'inline-size',
  'caret-color', 'column-rule-color', 'row-rule-color', 'outline-color',
  'text-emphasis-color', '-webkit-text-stroke-color', 'appearance',
  'unicode-bidi', 'perspective-origin', 'overflow-clip-margin', 'user-select',
  'scrollbar-width', 'animation-', 'transition-', '-moz-', 'text-decoration-color'
].join('|') + ')');

// A fixed px line-height breaks vertical alignment once Paper re-measures the
// text node: a 16px font carrying `line-height: 32px` inside a 20px-tall box
// pushes the glyphs off centre and the text no longer sits in its field. A
// relative line-height is computed from the font size, so the box always hugs
// the text. 120% is the house value.
//
// Cost, stated plainly: a paragraph whose source leading was 150% comes in
// tighter. Screenshot multi-line text after import and raise it locally if it
// reads cramped — alignment correctness is the thing being protected here.
const LINE_HEIGHT_PCT = '120%';

// ROTATION ORIGIN. A browser rotates about an element's centre (`transform-origin`
// defaults to `50% 50%`); Paper rotates about its top-left corner and pins
// `transform-origin: 0% 0%` — it is not settable through write_html or
// update_styles, both of which report success and change nothing.
//
// So a rotated element lands somewhere else after import. Storm's FAQ close mark
// is a `+` glyph rotated 45°: its centre swung 12px left and 5px down, half out
// of its circle and clipped by the row. Icons built as rotated glyphs — carets,
// chevrons, arrows, close marks — are everywhere, so this is not a one-off.
//
// Compensate geometrically instead. For a w×h box rotated by θ about its
// top-left, the centre moves from c to R(θ)·c, so shifting the element by
// c − R(θ)·c lands it exactly where the browser put it. CSS `translate` is an
// independent longhand, which Paper does honour, and it composes with whatever
// `left`/`top` the source used — including `calc()` — so nothing needs parsing.
//
// The trade-off, stated plainly: the emitted HTML is now Paper-targeted. Opened
// in a browser, which already rotates about the centre, the extra translate
// shifts the glyph. That is the same bargain this file already makes for
// line-height, and these captures exist to be imported, not re-rendered.
const ROT = /rotate\(\s*(-?[\d.]+)deg\s*\)|^\s*(-?[\d.]+)deg\s*$/;
const PX = /^\s*(-?[\d.]+)px\s*$/;

function isTransparentColor(value) {
  const v = String(value || '').trim().toLowerCase();
  if (!v || v === 'transparent') return true;
  if (/^#(?:[0-9a-f]{4}|[0-9a-f]{8})$/.test(v)) {
    const a = v.length === 5 ? v[4] + v[4] : v.slice(7);
    return parseInt(a, 16) === 0;
  }
  const fn = /^(?:rgba?|hsla?)\((.+)\)$/.exec(v);
  if (!fn) return false;
  const body = fn[1].trim();
  const slash = body.split('/');
  const rawA = slash.length === 2 ? slash[1] : (/^rgba|^hsla/.test(v) ? body.split(/[,\s]+/).filter(Boolean)[3] : null);
  if (rawA == null) return false;
  const s = String(rawA).trim();
  const a = s.endsWith('%') ? Number.parseFloat(s) / 100 : Number.parseFloat(s);
  return a === 0;
}

function isInvisibleBorderShorthand(value) {
  const colors = String(value || '').match(/(?:rgba?|hsla?)\([^)]+\)|#[0-9a-f]{3,8}|transparent/gi) || [];
  return colors.length > 0 && colors.every(isTransparentColor);
}

function originShift(decls) {
  const val = (p) => { const d = decls.find((x) => x.prop === p); return d ? d.raw.slice(d.raw.indexOf(':') + 1) : ''; };
  const rm = ROT.exec(val('transform')) || ROT.exec(val('rotate'));
  if (!rm) return null;
  const deg = parseFloat(rm[1] ?? rm[2]);
  if (!deg || deg % 360 === 0) return null;
  const w = PX.exec(val('width')), h = PX.exec(val('height'));
  if (!w || !h) return null;                      // no explicit box — cannot solve
  const cx = parseFloat(w[1]) / 2, cy = parseFloat(h[1]) / 2;
  const r = (deg * Math.PI) / 180, cos = Math.cos(r), sin = Math.sin(r);
  const dx = cx - (cx * cos - cy * sin);
  const dy = cy - (cx * sin + cy * cos);
  if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) return null;
  return `translate: ${+dx.toFixed(2)}px ${+dy.toFixed(2)}px`;
}

export function trim(html) {
  return html.replace(/style="([^"]*)"/g, (_m, css) => {
    const decls = css.split(';').map((s) => s.trim()).filter(Boolean)
      .map((d) => { const i = d.indexOf(':'); return { prop: d.slice(0, i).trim(), raw: d }; });
    const present = new Set(decls.map((d) => d.prop));
    const shorthandStyle = present.has('border-style');
    const kept = decls.filter((d) => {
      if (DROP.test(d.prop)) return false;
      const v = d.raw.slice(d.raw.indexOf(':') + 1).trim();
      // Paper drops rgba() alpha on `border: 1px solid rgba(42,42,42,0)` and
      // paints #2A2A2A boxes around nav/footer text links.
      if (d.prop === 'border' && isInvisibleBorderShorthand(v)) return false;
      if (/^border(-(top|right|bottom|left))?-color$/.test(d.prop) && isTransparentColor(v)) return false;
      const m = /^border-(top|right|bottom|left)-(width|color)$/.exec(d.prop);
      if (m && !shorthandStyle && !present.has(`border-${m[1]}-style`)) return false;
      return true;
    }).map((d) => {
      if (d.prop !== 'line-height') return d;
      const v = d.raw.slice(d.raw.indexOf(':') + 1).trim();
      if (!/^[\d.]+px$/.test(v)) return d;          // normal / already relative
      return { ...d, raw: `line-height: ${LINE_HEIGHT_PCT}` };
    });

    if (!present.has('translate')) {
      const shift = originShift(kept);
      if (shift) kept.push({ prop: 'translate', raw: shift });
    }

    return `style="${kept.map((d) => d.raw).join('; ')}"`;
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [, , inDir, outDir] = process.argv;
  if (!inDir || !outDir) { console.error('usage: node trim-styles.mjs <inDir> <outDir>'); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });
  let before = 0, after = 0;
  for (const f of fs.readdirSync(inDir).sort()) {
    if (!f.endsWith('.html')) continue;
    const src = fs.readFileSync(path.join(inDir, f), 'utf8');
    const t = trim(src);
    before += src.length; after += t.length;
    fs.writeFileSync(path.join(outDir, f), t);
    console.log(`${f.padEnd(34)} ${String(src.length).padStart(7)} -> ${String(t.length).padStart(6)}`);
  }
  if (before) console.log(`\ntotal ${before} -> ${after} (${(100 * after / before).toFixed(0)}%)`);
}
