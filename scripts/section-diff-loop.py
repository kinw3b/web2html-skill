#!/usr/bin/env python3
"""
section-diff-loop.py — Capture the live build section-by-section (reveal-aware)
and pair each section with the matching per-section SOURCE screenshot, so an
agent can loop one section at a time until it visually matches.

This does NOT decide pass/fail itself (that needs a vision-capable read of each
pair) — it produces, per section: the source reference, a freshly captured build
shot, and a side-by-side composite, plus a manifest. Re-run after every fix.

Why per-section capture (not full-page crop): a full-page screenshot grabs
reveal-on-scroll content mid-animation or before it fires (Pitfall #1). Each
build section is instead scrolled into view and allowed to FULLY reveal
(animations settled) before its shot — mirroring how the scrape captures the
source (scrape-web.sh Phase 3). Both sides are therefore settled, so the
comparison is apples-to-apples.

Usage:
  python3 section-diff-loop.py <build_url> <source_shots_dir> <out_dir> \
      [--pair BUILD_ID:SOURCE_INDEX ...] [--build-section ID] [--viewport 1440]

  <source_shots_dir>  dir with section-NN.png + sections.json (from the scrape)
  --pair hero:1       map build section id `hero` to source section-01.png
                      (repeatable). If omitted, pairs by document order:
                      build[i] ↔ source section-(i+1), warning on count mismatch.
  --build-section ID  only process this one build section (e.g. hero)

Output (per section):
  <out_dir>/ref_<id>.png            — the source reference shot
  <out_dir>/build_<id>.png          — fresh reveal-settled build capture
  <out_dir>/side_by_side_<id>.png   — source (left) vs build (right)
  <out_dir>/manifest.json
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path


# ── Build-side section discovery (semantic ids from the Step 2 scaffold) ──────
DETECT_JS = """
() => {
  // Section-level ids live as siblings under <body>: <header id>, each
  // <main> > <section id>, and <footer id>. Collect all three in order.
  const main = document.querySelector('main');
  const header = document.querySelector('body > header');
  const footer = document.querySelector('body > footer');
  const kids = [
    ...(header ? [header] : []),
    ...(main ? Array.from(main.children) : []),
    ...(footer ? [footer] : []),
  ].filter(el => el.id);
  kids.forEach(el => el.setAttribute('data-diff-section', el.id));
  return kids.map((el, i) => ({ order: i, id: el.id }));
}
"""


OBSERVE_JS = """
(el) => {
  const r = el.getBoundingClientRect();
  const imgs = [...el.querySelectorAll('img')];
  const imagesComplete = imgs.every(img => img.complete && img.naturalWidth > 0);
  const textSample = (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
  return {
    scrollY: Math.round(window.scrollY),
    top: Math.round(r.top),
    left: Math.round(r.left),
    width: Math.round(r.width),
    height: Math.round(r.height),
    imagesComplete,
    textSample,
    id: el.id || el.getAttribute('data-diff-section') || '',
  };
}
"""


async def settle(page, handle):
    """Scroll into view, wait for animations, then require two matching observations."""
    try:
        await handle.scroll_into_view_if_needed(timeout=6000)
    except Exception:
        pass
    try:
        await page.wait_for_function(
            "(el) => el.getAnimations({subtree:true}).every(a => a.playState !== 'running')",
            arg=handle, timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(400)

    last = None
    for _ in range(8):
        obs = await handle.evaluate(OBSERVE_JS)
        if (
            last is not None
            and last["scrollY"] == obs["scrollY"]
            and last["top"] == obs["top"]
            and last["left"] == obs["left"]
            and last["width"] == obs["width"]
            and last["height"] == obs["height"]
            and obs["imagesComplete"]
        ):
            return obs
        last = obs
        await page.wait_for_timeout(250)
    return last


async def capture_build_sections(url: str, viewport_w: int, out_dir: Path,
                                 wanted_id: str | None):
    from playwright.async_api import async_playwright

    captured = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": viewport_w, "height": 900}, device_scale_factor=1)
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)

        # Pre-pass: trigger every reveal observer + lazy load, then back to top.
        height = await page.evaluate("document.body.scrollHeight")
        for y in range(0, min(height, 20000), 700):
            await page.evaluate(f"window.scrollTo(0,{y})")
            await page.wait_for_timeout(200)
        await page.evaluate("window.scrollTo(0,0)")
        await page.wait_for_timeout(500)

        sections = await page.evaluate(DETECT_JS)
        if wanted_id:
            sections = [s for s in sections if s["id"] == wanted_id]

        for s in sections:
            handle = await page.query_selector(f'[data-diff-section="{s["id"]}"]')
            if handle is None:
                continue
            verified = await settle(page, handle)
            # Identity check in the same observation used for capture.
            if verified and verified.get("id") and verified["id"] != s["id"]:
                print(
                    f"  ! build section {s['id']}: identity mismatch "
                    f"(observed id={verified['id']!r}) — discarding",
                    file=sys.stderr,
                )
                continue
            build_path = out_dir / f"build_{s['id']}.png"
            try:
                await handle.screenshot(path=str(build_path))
            except Exception as e:
                print(f"  ! build section {s['id']} shot failed: {e}", file=sys.stderr)
                continue
            # Re-observe immediately after shot; discard if layout shifted mid-capture.
            post = await handle.evaluate(OBSERVE_JS)
            if verified and post and (
                post["scrollY"] != verified["scrollY"]
                or post["top"] != verified["top"]
                or post["width"] != verified["width"]
                or post["height"] != verified["height"]
            ):
                print(
                    f"  ! build section {s['id']}: shifted during capture — discarding",
                    file=sys.stderr,
                )
                build_path.unlink(missing_ok=True)
                continue
            captured.append({
                "order": s["order"],
                "id": s["id"],
                "build": build_path,
                "verified": verified,
            })

        await browser.close()
    return captured


# ── Side-by-side composite ───────────────────────────────────────────────────
def side_by_side(ref_path: Path, build_path: Path, out_path: Path, col_w: int = 620):
    from PIL import Image
    ref = Image.open(ref_path).convert("RGB")
    build = Image.open(build_path).convert("RGB")

    def scale(im):
        h = max(1, int(im.size[1] * col_w / im.size[0]))
        return im.resize((col_w, h), Image.LANCZOS)

    r, b = scale(ref), scale(build)
    gutter, pad, label_h = 28, 20, 34
    H = max(r.size[1], b.size[1]) + label_h + pad * 2
    canvas = Image.new("RGB", (col_w * 2 + gutter + pad * 2, H), (18, 18, 22))
    canvas.paste(r, (pad, pad + label_h))
    canvas.paste(b, (pad + col_w + gutter, pad + label_h))
    try:
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        d.text((pad, pad + 8), "SOURCE (reference)", fill=(150, 150, 160))
        d.text((pad + col_w + gutter, pad + 8), "BUILD (your rebuild)", fill=(150, 150, 160))
    except Exception:
        pass
    canvas.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_url", help="e.g. file:///…/build/index.html or http://localhost:PORT/")
    ap.add_argument("source_shots_dir", help="dir with section-NN.png + sections.json")
    ap.add_argument("out_dir")
    ap.add_argument("--pair", action="append", default=[],
                    help="BUILD_ID:SOURCE_INDEX, e.g. hero:1 (repeatable)")
    ap.add_argument("--build-section", default=None, help="only this build section id")
    ap.add_argument("--viewport", type=int, default=1440)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src_dir = Path(args.source_shots_dir)
    # explicit build_id -> source section index map
    pair_map = {}
    for pr in args.pair:
        bid, _, idx = pr.partition(":")
        pair_map[bid] = int(idx)

    captured = asyncio.run(
        capture_build_sections(args.build_url, args.viewport, out_dir, args.build_section))
    if not captured:
        print("✗ No id'd build sections found (header/main>section/footer with an id).",
              file=sys.stderr)
        sys.exit(1)

    def source_shot(build_id: str, order: int) -> Path | None:
        idx = pair_map.get(build_id, order + 1)  # default: pair by order (1-based)
        cand = src_dir / f"section-{idx:02d}.png"
        return cand if cand.exists() else None

    manifest = []
    for c in captured:
        ref_src = source_shot(c["id"], c["order"])
        entry = {
            "id": c["id"],
            "order": c["order"],
            "build": str(c["build"]),
            "verified": c.get("verified"),
            "stable_capture": True,
        }
        if ref_src is None:
            entry["ref"] = None
            entry["note"] = "no matching source section shot — pair explicitly with --pair"
            print(f"  - {c['id']}: build captured, NO source match (use --pair {c['id']}:N)")
        else:
            ref_path = out_dir / f"ref_{c['id']}.png"
            ref_path.write_bytes(ref_src.read_bytes())
            sbs = out_dir / f"side_by_side_{c['id']}.png"
            side_by_side(ref_path, c["build"], sbs)
            entry.update(ref=str(ref_path), source_file=ref_src.name,
                         side_by_side=str(sbs))
            print(f"  - {c['id']}: {ref_src.name}  vs  build_{c['id']}.png  →  {sbs.name}")
        manifest.append(entry)

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[section-diff-loop] {len(manifest)} section(s) → {out_dir}/")


if __name__ == "__main__":
    main()
