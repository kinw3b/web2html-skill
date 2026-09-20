#!/usr/bin/env python3
"""
spec-shot.py — Redline/spec overlay for a page section, measured from the
LOCAL scraped HTML (no live network fetch) or a live build.

For a given section (CSS selector), captures a plain screenshot AND an
annotated "spec" version, pesticide-style: every element gets a thin outline
in ONE uniform color, padding regions are shaded, and red dimension lines with
arrowheads mark the gap between adjacent elements — the goal is spacing,
layout, and geometry clarity, not a text-heavy dump per element.

Measures from the scraped file, not the live site: pass a `file://` URL to a
scraped source-site/index.html (or a build's index.html) and all *remote*
requests (http/https) are blocked during the run — this proves (and enforces)
that no live re-fetch happens on every spec pass. Only pass a live http(s) URL
if you explicitly want to measure the live source instead.

Usage:
  Single section:
    python3 spec-shot.py <url> <out_prefix> <section_selector> [--viewport 1440]
  Every top-level section in one pass (same section-detection heuristic as
  scrape-web.sh's Phase 3 — no need to know selectors up front):
    python3 spec-shot.py <url> <out_dir> --all-sections [--viewport 1440]

Output (single):
  <out_prefix>.png        plain screenshot of the section
  <out_prefix>.spec.png   annotated: outlines + padding + gap redlines
  <out_prefix>.spec.json  raw measurements (box model, computed styles)

Output (--all-sections), matching scrape-web.sh's section-NN.png naming:
  <out_dir>/section-01.png / .spec.png / .spec.json
  <out_dir>/section-02.png / .spec.png / .spec.json  ...
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path

DETECT_JS = r"""() => {
  const vw = innerWidth;
  const fwTall = (parent) => [...parent.children].filter(el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width >= vw * 0.85 && el.scrollHeight >= 200
        && s.position !== 'fixed' && s.position !== 'sticky' && s.display !== 'none';
  });
  let best = null;
  const queue = [document.body];
  while (queue.length) {
    const n = queue.shift();
    const fw = fwTall(n);
    if (fw.length >= 3) { best = n; break; }
    for (const c of [...n.children]) {
      const r = c.getBoundingClientRect();
      if (r.width >= vw * 0.85 && c.scrollHeight >= 400) queue.push(c);
    }
  }
  if (!best) best = document.body;
  const secs = fwTall(best);
  secs.forEach((el, i) => el.setAttribute('data-scrape-section', i));
  return secs.map((el, i) => {
    const name = el.getAttribute('data-framer-name') || el.id || ('section-' + (i + 1));
    return { i, name };
  });
}"""

MEASURE_JS = r"""
(sectionSel) => {
  const section = document.querySelector(sectionSel);
  if (!section) return null;
  const sRect = section.getBoundingClientRect();

  const interesting = [];
  const seen = new Set();
  let nextId = 0;

  function pushEl(el, role, parentId) {
    if (seen.has(el)) return null;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return null;
    const s = getComputedStyle(el);
    const directText = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim()).join('').trim();
    const id = nextId++;
    interesting.push({
      id, parentId, role,
      tag: el.tagName.toLowerCase(),
      cls: (el.className || '').toString().split(' ').filter(Boolean).slice(0, 2).join('.'),
      text: directText.slice(0, 40),
      x: r.left - sRect.left, y: r.top - sRect.top,
      width: r.width, height: r.height,
      fontSize: s.fontSize, fontWeight: s.fontWeight,
      color: s.color,
      borderRadius: s.borderRadius,
      paddingTop: parseFloat(s.paddingTop) || 0,
      paddingRight: parseFloat(s.paddingRight) || 0,
      paddingBottom: parseFloat(s.paddingBottom) || 0,
      paddingLeft: parseFloat(s.paddingLeft) || 0,
    });
    return id;
  }

  // Recursive descent that finds the MEANINGFUL layout units — the things a
  // designer would actually measure spacing between — instead of every DOM
  // node. Rules:
  //  - <a>/<button> is always its own "container" unit (a clickable row is
  //    ONE thing to measure against, even though it internally wraps an icon
  //    + text span) — we do NOT recurse into it as further containers, we
  //    only pull its icon/text out as label-only detail (role 'leaf-detail',
  //    excluded from gap-line eligibility) so button-vs-button gaps are real.
  //  - A wrapper with exactly ONE significant child is a pass-through (pure
  //    layout div) — skip boxing it, recurse straight into the child so we
  //    don't stack 3 identical-looking outlines on the same rect.
  //  - A wrapper with 2+ significant children is a real row/stack — box it
  //    as a container and recurse into each child.
  //  - A leaf with no significant children (h1/h2/h3/h4/p/span/li) or a
  //    media tag (img/svg) gets boxed as 'leaf'/'media' for detail only.
  const MAX_DEPTH = 20;
  const LEAFY = new Set(['H1','H2','H3','H4','P','SPAN','LI']);

  function expandContents(el) {
    // display:contents wrappers (Framer's "ssr-variant hidden-XXXX"
    // responsive-breakpoint pattern is the common case) generate NO box of
    // their own — getBoundingClientRect() on one is always 0x0 — so a naive
    // size filter kills the entire real subtree underneath it. Flatten them
    // away and use their children directly, recursively (can nest).
    let out = [];
    for (const c of el.children) {
      const cs = getComputedStyle(c);
      if (cs.display === 'none') continue;
      if (cs.display === 'contents') { out = out.concat(expandContents(c)); continue; }
      out.push(c);
    }
    return out;
  }

  function significantChildren(el) {
    return expandContents(el).filter(c => {
      const cs = getComputedStyle(c);
      const r = c.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return false;
      // <img>/<svg> default to display:inline in the UA stylesheet unless
      // CSS overrides it — exclude that inline check for them specifically,
      // or a real, visible, large image gets silently dropped from its
      // parent's child count (parent then wrongly looks "leaf-empty" and
      // the image never gets walked into at all).
      if (cs.display === 'inline' && c.tagName !== 'IMG' && c.tagName !== 'SVG') return false;
      return true;
    });
  }

  function walk(el, parentId, depth) {
    // Safety net: never silently drop real content on depth overflow — box
    // whatever we've got instead of returning nothing (Framer markup nests
    // deep; a hard "return" here previously made a whole branch vanish).
    if (depth > MAX_DEPTH) { pushEl(el, 'container', parentId); return; }

    if (el.tagName === 'A' || el.tagName === 'BUTTON') {
      const id = pushEl(el, 'container', parentId);
      el.querySelectorAll('p,span,img,svg').forEach(child => pushEl(child, 'leaf-detail', id));
      return;
    }

    const kids = significantChildren(el);

    if (kids.length === 0) {
      if (LEAFY.has(el.tagName)) pushEl(el, 'leaf', parentId);
      else if (el.tagName === 'IMG' || el.tagName === 'SVG') pushEl(el, 'media', parentId);
      return;
    }

    if (kids.length === 1) {
      walk(kids[0], parentId, depth); // pass-through wrapper, same depth/parent
      return;
    }

    const id = pushEl(el, 'container', parentId);
    kids.forEach(c => walk(c, id, depth + 1));
  }

  // Don't box the root selected element itself (redundant with the
  // SECTION-level footer stat) — recurse straight into its real substructure.
  significantChildren(section).forEach(c => walk(c, null, 0));

  return {
    section: { width: sRect.width, height: sRect.height },
    elements: interesting,
  };
}
"""


# Framer entrance animations ("appear effects") start below-the-fold elements
# at opacity:0 and reveal them via IntersectionObserver when they scroll into
# view. They're driven by Framer Motion's own requestAnimationFrame loop, not
# the Web Animations API, so getAnimations() can't see them and a wait on it
# passes instantly while the element is still invisible — which is why only the
# first (in-viewport-on-load) section used to capture correctly and everything
# below the fold came out blank. Scroll the whole page once (top→bottom→top) to
# fire every reveal (Framer appear effects are once-only, so revealed elements
# stay visible) and to trigger any lazy-loaded images, then settle back at top.
REVEAL_JS = r"""async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const maxY = () => Math.max(
    document.body.scrollHeight, document.documentElement.scrollHeight);
  const step = Math.max(200, Math.floor(innerHeight * 0.8));
  for (let y = 0; y <= maxY(); y += step) {
    window.scrollTo(0, y);
    await wait(120);
  }
  window.scrollTo(0, maxY());
  await wait(250);
  window.scrollTo(0, 0);
  await wait(250);
}"""


async def _settle_before_shot(page, handle):
    """Bring the section into view and give its reveal a beat to finish before
    capturing. REVEAL_JS already fired every once-only appear effect; this also
    covers effects configured to replay each time they re-enter the viewport."""
    try:
        await handle.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    try:
        await page.wait_for_function(
            "(el) => el.getAnimations({subtree:true}).every(a => a.playState !== 'running')",
            arg=handle, timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(350)


async def measure(url: str, selector: str, viewport: int):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": viewport, "height": 1200})

        if url.startswith("file://"):
            # Prove + enforce: no live network fetch during a spec pass against
            # a scraped/local file. Only the local file itself is allowed.
            await page.route("http://**", lambda route: route.abort())
            await page.route("https://**", lambda route: route.abort())

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(500)
        await page.evaluate(REVEAL_JS)

        handle = await page.query_selector(selector)
        if handle is None:
            print(f"✗ selector {selector!r} not found", file=sys.stderr)
            await browser.close()
            sys.exit(1)

        await _settle_before_shot(page, handle)

        data = await page.evaluate(MEASURE_JS, selector)
        screenshot_bytes = await handle.screenshot()
        await browser.close()
        return data, screenshot_bytes


async def measure_all(url: str, viewport: int):
    """Same detection heuristic as scrape-web.sh Phase 3 (DETECT_JS), so no
    selector needs to be known ahead of time — one browser session measures
    every top-level section in turn. Returns [(index, name, data, screenshot_bytes), ...]."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": viewport, "height": 1200})

        if url.startswith("file://"):
            await page.route("http://**", lambda route: route.abort())
            await page.route("https://**", lambda route: route.abort())

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(500)

        sections = await page.evaluate(DETECT_JS)
        # Fire every scroll-reveal / lazy image once, up front, so sections
        # below the initial viewport are already painted when we capture them.
        await page.evaluate(REVEAL_JS)
        results = []
        for s in sections:
            selector = f'[data-scrape-section="{s["i"]}"]'
            handle = await page.query_selector(selector)
            if handle is None:
                continue
            await _settle_before_shot(page, handle)
            data = await page.evaluate(MEASURE_JS, selector)
            screenshot_bytes = await handle.screenshot()
            results.append((s["i"], s["name"], data, screenshot_bytes))

        await browser.close()
        return results


# ── geometry helpers ─────────────────────────────────────────────────────────
def contains(a, b) -> bool:
    """True if box a fully contains box b (so a is an ancestor-ish wrapper)."""
    return (a["x"] <= b["x"] + 0.5 and a["y"] <= b["y"] + 0.5 and
            a["x"] + a["width"] >= b["x"] + b["width"] - 0.5 and
            a["y"] + a["height"] >= b["y"] + b["height"] - 0.5)


def x_overlap_frac(a, b) -> float:
    lo = max(a["x"], b["x"])
    hi = min(a["x"] + a["width"], b["x"] + b["width"])
    if hi <= lo:
        return 0.0
    return (hi - lo) / min(a["width"], b["width"])


def y_overlap_frac(a, b) -> float:
    lo = max(a["y"], b["y"])
    hi = min(a["y"] + a["height"], b["y"] + b["height"])
    if hi <= lo:
        return 0.0
    return (hi - lo) / min(a["height"], b["height"])


def find_gaps(elements: list[dict]) -> list[dict]:
    """One nearest-neighbor gap per element per axis (down, right) — skips
    containment pairs (parent/wrapper vs its own content) so gap lines only
    connect elements that are actually adjacent in the flow, not nested.
    Only role='container' (rows/stacks/buttons) and role='media' (real
    images/svg) elements participate — text/icon internals ('leaf' and
    'leaf-detail', e.g. a button's own label/icon) are shown for outline/label
    detail only, never as gap endpoints, so a gap line always means "distance
    between two real elements" — button-to-button, or content-block-to-image —
    not "distance between a button's inner icon and another button's label."
    Near-identical gap lines are deduped to one."""
    gaps = []
    non_contained_pairs_seen = set()
    # containers AND top-level media (real images/svg) are measurable units;
    # 'leaf'/'leaf-detail' (text runs, icons nested inside a button) are not
    eligible = [e for e in elements if e["role"] in ("container", "media")]

    for a in eligible:
        # vertical: nearest element whose top is below a's bottom, same column
        best_v, best_v_gap = None, None
        for b in eligible:
            if b["id"] == a["id"]:
                continue
            if contains(a, b) or contains(b, a):
                continue
            gap = b["y"] - (a["y"] + a["height"])
            if gap < 0:
                continue
            if x_overlap_frac(a, b) < 0.25:
                continue
            if best_v_gap is None or gap < best_v_gap:
                best_v, best_v_gap = b, gap
        if best_v is not None and 1 <= best_v_gap <= 400:
            key = tuple(sorted([a["id"], best_v["id"]])) + ("v",)
            if key not in non_contained_pairs_seen:
                non_contained_pairs_seen.add(key)
                cx_lo = max(a["x"], best_v["x"])
                cx_hi = min(a["x"] + a["width"], best_v["x"] + best_v["width"])
                cx = (cx_lo + cx_hi) / 2
                gaps.append({
                    "axis": "v", "gap": round(best_v_gap),
                    "x0": cx, "y0": a["y"] + a["height"], "x1": cx, "y1": best_v["y"],
                })

        # horizontal: nearest element to the right, same row
        best_h, best_h_gap = None, None
        for b in eligible:
            if b["id"] == a["id"]:
                continue
            if contains(a, b) or contains(b, a):
                continue
            gap = b["x"] - (a["x"] + a["width"])
            if gap < 0:
                continue
            if y_overlap_frac(a, b) < 0.25:
                continue
            if best_h_gap is None or gap < best_h_gap:
                best_h, best_h_gap = b, gap
        if best_h is not None and 1 <= best_h_gap <= 400:
            key = tuple(sorted([a["id"], best_h["id"]])) + ("h",)
            if key not in non_contained_pairs_seen:
                non_contained_pairs_seen.add(key)
                cy_lo = max(a["y"], best_h["y"])
                cy_hi = min(a["y"] + a["height"], best_h["y"] + best_h["height"])
                cy = (cy_lo + cy_hi) / 2
                gaps.append({
                    "axis": "h", "gap": round(best_h_gap),
                    "x0": a["x"] + a["width"], "y0": cy, "x1": best_h["x"], "y1": cy,
                })

    # dedupe near-identical lines: same axis, same rounded distance, endpoints
    # within 15px of an already-kept line (e.g. two sibling elements both
    # measuring "gap to the same row below" a few px apart in x)
    deduped = []
    for g in gaps:
        dup = False
        for k in deduped:
            if g["axis"] != k["axis"] or g["gap"] != k["gap"]:
                continue
            if abs(g["x0"] - k["x0"]) < 15 and abs(g["y0"] - k["y0"]) < 15:
                dup = True
                break
        if not dup:
            deduped.append(g)
    return deduped


# ── drawing ───────────────────────────────────────────────────────────────────
OUTLINE = (0, 224, 255, 200)      # uniform cyan — every element, pesticide-style
PADDING_DOT = (110, 220, 120, 28)  # barely-visible green dots — background texture only
PADDING_TEXT = (180, 255, 190, 255)
PADDING_TEXT_BG = (0, 0, 0, 170)  # same backing style as the element outline labels
GAP_COLOR = (255, 40, 40, 235)    # red — distance/gap lines
GAP_TEXT_BG = (40, 0, 0, 220)
DOT_SPACING = 9   # px between dot centers — sparse enough to read as dots, not a texture wash
DOT_RADIUS = 0.6  # px


def draw_dot_grid(draw, box, color, spacing=DOT_SPACING, radius=DOT_RADIUS):
    """Fill a rect with a small low-opacity dot grid instead of a solid wash —
    reads as "this is a spacing zone" (padding) rather than a filled block,
    similar to Figma/Zeplin padding hatching."""
    x0, y0, x1, y1 = box
    if x1 - x0 < 1 or y1 - y0 < 1:
        return
    y = y0 + spacing / 2
    while y < y1:
        x = x0 + spacing / 2
        while x < x1:
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
            x += spacing
        y += spacing


def draw_spec(data: dict, screenshot_path: Path, out_path: Path):
    from PIL import Image, ImageDraw, ImageFont

    im = Image.open(screenshot_path).convert("RGB")

    try:
        font_sm = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 10)
    except Exception:
        font_sm = ImageFont.load_default()

    # dim the base screenshot slightly so redlines/outlines pop
    im = Image.alpha_composite(
        im.convert("RGBA"), Image.new("RGBA", im.size, (10, 10, 14, 70)))
    draw = ImageDraw.Draw(im, "RGBA")

    elements = data["elements"]

    # 1. Padding zones first (under outlines/labels)
    for el in elements:
        pt, pr, pb, pl = el["paddingTop"], el["paddingRight"], el["paddingBottom"], el["paddingLeft"]
        if pt < 1 and pr < 1 and pb < 1 and pl < 1:
            continue
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        for val, tx, ty in [
            (pt, x + w / 2, y + pt / 2), (pb, x + w / 2, y + h - pb / 2),
            (pl, x + pl / 2, y + h / 2), (pr, x + w - pr / 2, y + h / 2),
        ]:
            if val >= 1:
                txt = str(round(val))
                bbox = draw.textbbox((0, 0), txt, font=font_sm)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                cpad = 2
                draw.rectangle(
                    [tx - tw / 2 - cpad, ty - th / 2 - cpad, tx + tw / 2 + cpad, ty + th / 2 + cpad],
                    fill=PADDING_TEXT_BG)
                draw.text((tx - tw / 2, ty - th / 2), txt, fill=PADDING_TEXT, font=font_sm)

    # 2. Uniform outlines, all elements, same color/weight (pesticide-style)
    for el in elements:
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        draw.rectangle([x, y, x + w, y + h], outline=OUTLINE, width=1)

    # 3. Short labels — "tag WxH" only, nothing else, collision-avoided
    placed_boxes = []

    def overlaps(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def label(x, y, text, anchor_bottom):
        bbox = draw.textbbox((0, 0), text, font=font_sm)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 2
        box_h = th + pad * 2
        ly = (y - box_h - 1) if anchor_bottom else (y + 1)
        ly = max(0, ly)
        step = -box_h if anchor_bottom else box_h
        cand = (x, ly, x + tw + pad * 2, ly + box_h)
        guard = 0
        while any(overlaps(cand, pb) for pb in placed_boxes) and guard < 20:
            ly += step
            ly = max(0, ly)
            cand = (x, ly, x + tw + pad * 2, ly + box_h)
            guard += 1
        placed_boxes.append(cand)
        draw.rectangle(cand, fill=(0, 0, 0, 170))
        draw.text((x + pad, ly + pad - 1), text, fill=OUTLINE[:3] + (255,), font=font_sm)

    for el in sorted(elements, key=lambda e: e["width"] * e["height"], reverse=True):
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        text = f"{el['tag']} {round(w)}x{round(h)}"
        label(x + 1, y, text, anchor_bottom=(y > 14))

    # 4. Red gap/distance lines between adjacent (non-nested) elements
    for g in find_gaps(elements):
        x0, y0, x1, y1 = g["x0"], g["y0"], g["x1"], g["y1"]
        draw.line([x0, y0, x1, y1], fill=GAP_COLOR, width=1)
        # arrowheads
        a = 3
        if g["axis"] == "v":
            draw.line([x0 - a, y0 + a, x0, y0], fill=GAP_COLOR, width=1)
            draw.line([x0 + a, y0 + a, x0, y0], fill=GAP_COLOR, width=1)
            draw.line([x1 - a, y1 - a, x1, y1], fill=GAP_COLOR, width=1)
            draw.line([x1 + a, y1 - a, x1, y1], fill=GAP_COLOR, width=1)
        else:
            draw.line([x0 + a, y0 - a, x0, y0], fill=GAP_COLOR, width=1)
            draw.line([x0 + a, y0 + a, x0, y0], fill=GAP_COLOR, width=1)
            draw.line([x1 - a, y1 - a, x1, y1], fill=GAP_COLOR, width=1)
            draw.line([x1 - a, y1 + a, x1, y1], fill=GAP_COLOR, width=1)

        txt = f"{g['gap']}"
        bbox = draw.textbbox((0, 0), txt, font=font_sm)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        draw.rectangle([mx - tw / 2 - 2, my - th / 2 - 2, mx + tw / 2 + 2, my + th / 2 + 2],
                       fill=GAP_TEXT_BG)
        draw.text((mx - tw / 2, my - th / 2 - 1), txt, fill=(255, 120, 120, 255), font=font_sm)

    # 5. section-level footer legend
    sw, sh = data["section"]["width"], data["section"]["height"]
    footer = (f"SECTION {round(sw)} x {round(sh)}px  |  cyan=outline(border-box, incl. padding)  "
              f"green=padding  red=gap(rendered distance, container-to-container only)")
    draw.rectangle([0, im.size[1] - 20, im.size[0], im.size[1]], fill=(0, 0, 0, 210))
    draw.text((8, im.size[1] - 16), footer, fill=(255, 255, 255, 255), font=font_sm)

    im.convert("RGB").save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out_prefix", help="single mode: file prefix. --all-sections: output dir")
    ap.add_argument("section_selector", nargs="?", default=None)
    ap.add_argument("--viewport", type=int, default=1440)
    ap.add_argument("--all-sections", action="store_true",
                     help="auto-detect every top-level section (scrape-web.sh's own "
                          "heuristic) and generate a spec for each, named section-NN.*")
    args = ap.parse_args()

    if args.all_sections:
        out_dir = Path(args.out_prefix)
        out_dir.mkdir(parents=True, exist_ok=True)
        results = asyncio.run(measure_all(args.url, args.viewport))
        for i, name, data, shot in results:
            prefix = out_dir / f"section-{i + 1:02d}"
            plain_path = Path(f"{prefix}.png")
            spec_path = Path(f"{prefix}.spec.png")
            json_path = Path(f"{prefix}.spec.json")
            plain_path.write_bytes(shot)
            json_path.write_text(json.dumps(data, indent=2))
            draw_spec(data, plain_path, spec_path)
            print(f"✓ {spec_path}  ({name}, {len(data['elements'])} elements)")
        return

    if not args.section_selector:
        ap.error("section_selector is required unless --all-sections is passed")

    out_prefix = Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    plain_path = Path(f"{out_prefix}.png")
    spec_path = Path(f"{out_prefix}.spec.png")
    json_path = Path(f"{out_prefix}.spec.json")

    data, shot = asyncio.run(measure(args.url, args.section_selector, args.viewport))
    plain_path.write_bytes(shot)
    json_path.write_text(json.dumps(data, indent=2))
    draw_spec(data, plain_path, spec_path)

    print(f"✓ {plain_path}")
    print(f"✓ {spec_path}  ({len(data['elements'])} elements)")
    print(f"✓ {json_path}")


if __name__ == "__main__":
    main()
