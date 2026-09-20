#!/usr/bin/env python3
"""
capture-build.py — Capture the rebuilt site as a full-page screenshot
at the same viewport as the reference (default 1440 wide).

Usage:
  python3 capture-build.py <output_dir> <output_png>
  python3 capture-build.py v4 v4-build.png --viewport 1440
"""
from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path

async def capture(site_dir: Path, out_png: Path, viewport_w: int = 1440, viewport_h: int = 900):
    """Capture fullpage screenshot using Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("✗ playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    # Find index.html in site_dir
    index = site_dir / "index.html"
    if not index.exists():
        print(f"✗ {index} not found", file=sys.stderr)
        sys.exit(1)

    url = f"file://{index.absolute()}"
    print(f"[capture] url: {url}")
    print(f"[capture] viewport: {viewport_w}x{viewport_h}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": viewport_w, "height": viewport_h},
                                          device_scale_factor=1)
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Wait for fonts and any web-fonts
        await page.wait_for_timeout(2000)
        # Make sure all data-reveal elements are visible (for capture)
        await page.evaluate("""() => {
            document.querySelectorAll('[data-reveal]').forEach(el => {
                el.classList.add('is-visible');
                el.classList.remove('is-prep');
            });
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(out_png), full_page=True)
        await browser.close()

    print(f"[capture] saved: {out_png} ({out_png.stat().st_size} bytes)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir", help="v1/, v2/, etc.")
    ap.add_argument("out_png", help="output PNG path")
    ap.add_argument("--viewport", type=int, default=1440, help="viewport width (default 1440)")
    args = ap.parse_args()

    out_png = Path(args.out_png)
    asyncio.run(capture(Path(args.output_dir), out_png, viewport_w=args.viewport))

if __name__ == "__main__":
    main()
