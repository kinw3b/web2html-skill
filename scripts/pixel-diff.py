#!/usr/bin/env python3
"""
pixel-diff.py — Compare a reference screenshot to a build screenshot.

Produces:
  - diff-heatmap.png   (3-panel: reference | build | heatmap, red = differs)
  - diff-report.md     (per-band match score, top divergences)

Usage:
  python3 pixel-diff.py reference.png build.png
  python3 pixel-diff.py reference.png build.png --out-dir v4/verification
  python3 pixel-diff.py reference.png build.png --band-height 1000 --threshold 0.10
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

def load_resize(path: Path, target_w: int) -> Image.Image:
    """Load image and resize to target width (preserving aspect ratio)."""
    im = Image.open(path).convert("RGB")
    if im.width != target_w:
        ratio = target_w / im.width
        im = im.resize((target_w, int(im.height * ratio)), Image.LANCZOS)
    return im

def pixel_diff(ref: Image.Image, build: Image.Image, threshold: float = 0.05) -> Image.Image:
    """Per-pixel diff, scaled by threshold. Returns grayscale heatmap where
    white = match, red = diff > threshold."""
    # Same size required
    if ref.size != build.size:
        # Resize build to match ref
        build = build.resize(ref.size, Image.LANCZOS)

    diff = ImageChops.difference(ref, build)
    # Convert to grayscale (perceptual luminance)
    gray = diff.convert("L")
    # Threshold: pixels with any channel > threshold*255 are "different"
    # We use the per-pixel max channel difference
    w, h = gray.size
    px = gray.load()
    threshold_byte = int(threshold * 255)
    for y in range(h):
        for x in range(w):
            if px[x, y] < threshold_byte:
                px[x, y] = 0
            else:
                # Normalize the diff to 0-255 range (max channel)
                px[x, y] = min(255, int(px[x, y] * 2))  # amplify

    # Color: red for diff, light gray for match
    heatmap = Image.new("RGB", ref.size, (245, 245, 245))
    draw = ImageDraw.Draw(heatmap)
    # Use gray as alpha mask
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            if v > 0:
                # Red intensity scales with diff magnitude
                draw.point((x, y), fill=(255, 80, 80, int(v)))
    return heatmap

def overall_score(ref: Image.Image, build: Image.Image, threshold: float = 0.05) -> float:
    """Match score: % of pixels where all RGB channels are within threshold."""
    if ref.size != build.size:
        build = build.resize(ref.size, Image.LANCZOS)
    diff = ImageChops.difference(ref, build)
    w, h = diff.size
    px = diff.load()
    threshold_byte = int(threshold * 255)
    matching = 0
    total = w * h
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if max(r, g, b) <= threshold_byte:
                matching += 1
    return matching / total

def band_score(ref: Image.Image, build: Image.Image, y0: int, y1: int, threshold: float = 0.05) -> float:
    """Match score for a horizontal band [y0, y1)."""
    if ref.size != build.size:
        build = build.resize(ref.size, Image.LANCZOS)
    diff = ImageChops.difference(ref, build)
    w = diff.width
    px = diff.load()
    threshold_byte = int(threshold * 255)
    matching = 0
    total = w * (y1 - y0)
    for y in range(y0, min(y1, diff.height)):
        for x in range(w):
            r, g, b = px[x, y]
            if max(r, g, b) <= threshold_byte:
                matching += 1
    return matching / total if total else 0

def color_delta_per_band(ref: Image.Image, build: Image.Image, y0: int, y1: int) -> dict:
    """Find the dominant color difference in a band — useful for diagnosis."""
    if ref.size != build.size:
        build = build.resize(ref.size, Image.LANCZOS)
    diff = ImageChops.difference(ref, build)
    # Quantize diff to find dominant delta color
    from collections import Counter
    counter = Counter()
    px = diff.load()
    for y in range(y0, min(y1, diff.height)):
        for x in range(0, diff.width, 4):  # subsample
            r, g, b = px[x, y]
            if max(r, g, b) > 12:  # non-trivial diff
                # Round to nearest 16
                rk = (r // 16) * 16
                gk = (g // 16) * 16
                bk = (b // 16) * 16
                counter[(rk, gk, bk)] += 1
    return dict(counter.most_common(3))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference", help="reference screenshot (source of truth)")
    ap.add_argument("build", help="build screenshot (the rebuild)")
    ap.add_argument("--out-dir", default="verification", help="output directory")
    ap.add_argument("--target-width", type=int, default=1440,
                    help="resize both images to this width for fair comparison")
    ap.add_argument("--band-height", type=int, default=1000, help="band size in px")
    ap.add_argument("--threshold", type=float, default=0.05,
                    help="per-channel diff threshold (0.05 = 5 percent)")
    args = ap.parse_args()

    ref_path = Path(args.reference)
    build_path = Path(args.build)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ref_path.exists():
        print(f"✗ reference not found: {ref_path}", file=sys.stderr)
        sys.exit(1)
    if not build_path.exists():
        print(f"✗ build not found: {build_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[diff] reference: {ref_path} ({ref_path.stat().st_size // 1024} KB)")
    print(f"[diff] build:     {build_path} ({build_path.stat().st_size // 1024} KB)")

    ref = load_resize(ref_path, args.target_width)
    build = load_resize(build_path, args.target_width)
    print(f"[diff] normalized to: {ref.size}")

    # Save 3-panel comparison: reference | build | heatmap
    heatmap = pixel_diff(ref, build, threshold=args.threshold)

    # Composite 3-panel image side by side
    w, h = ref.size
    panel_w = w // 2  # scale down for output
    panel_h = int(h * panel_w / w)
    ref_small = ref.resize((panel_w, panel_h), Image.LANCZOS)
    build_small = build.resize((panel_w, panel_h), Image.LANCZOS)
    heatmap_small = heatmap.resize((panel_w, panel_h), Image.LANCZOS)

    combined_w = panel_w * 3 + 20
    combined_h = panel_h + 30
    combined = Image.new("RGB", (combined_w, combined_h), (255, 255, 255))
    combined.paste(ref_small, (0, 30))
    combined.paste(build_small, (panel_w + 10, 30))
    combined.paste(heatmap_small, (panel_w * 2 + 20, 30))
    draw = ImageDraw.Draw(combined)
    draw.text((10, 5), "REFERENCE", fill=(0, 0, 0))
    draw.text((panel_w + 20, 5), "BUILD", fill=(0, 0, 0))
    draw.text((panel_w * 2 + 30, 5), "HEATMAP (red = differs)", fill=(0, 0, 0))
    combined.save(out_dir / "diff-heatmap.png", optimize=True)
    print(f"[diff] saved: {out_dir/'diff-heatmap.png'}")

    # Overall + per-band scores
    overall = overall_score(ref, build, threshold=args.threshold)
    print(f"[diff] overall match: {overall*100:.1f}%")

    bands = []
    h_total = ref.height
    for y0 in range(0, h_total, args.band_height):
        y1 = min(y0 + args.band_height, h_total)
        score = band_score(ref, build, y0, y1, threshold=args.threshold)
        deltas = color_delta_per_band(ref, build, y0, y1)
        bands.append((y0, y1, score, deltas))

    # Markdown report
    lines = [
        "# Pixel-Diff Report",
        "",
        f"**Reference:** `{ref_path}` ({ref.size[0]}×{ref.size[1]})",
        f"**Build:**     `{build_path}` ({build.size[0]}×{build.size[1]})",
        f"**Threshold:** {args.threshold*100:.1f}% per channel",
        f"**Match score:** {overall*100:.1f}%",
        "",
        "## Per-band match scores",
        "",
        "| Band (px) | Score | Dominant color delta |",
        "|---|---|---|",
    ]
    for y0, y1, score, deltas in bands:
        if deltas:
            top = max(deltas, key=deltas.get)
            hex_color = f"#{top[0]:02x}{top[1]:02x}{top[2]:02x}"
            count = sum(deltas.values())
            delta_str = f"`{hex_color}` ×{count}"
        else:
            delta_str = "—"
        verdict = "✅" if score > 0.95 else ("⚠️ " if score > 0.85 else "❌")
        lines.append(f"| {y0}–{y1} | {verdict} {score*100:.1f}% | {delta_str} |")

    lines += [
        "",
        "## Top divergences to fix",
        "",
    ]
    # Identify the worst bands
    worst = sorted(bands, key=lambda b: b[2])[:5]
    for y0, y1, score, deltas in worst:
        lines.append(f"### Band {y0}–{y1}px (score {score*100:.1f}%)")
        if deltas:
            lines.append("")
            lines.append("Dominant color differences (compared to reference):")
            for color, count in list(deltas.items())[:3]:
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                lines.append(f"- `{hex_color}` (count: {count})")
        lines.append("")
        lines.append("**Likely causes:**")
        lines.append("- Background color mismatch (check `--c-*` tokens)")
        lines.append("- Missing image or wrong image src")
        lines.append("- Padding/spacing off (check `--s-*` and section padding)")
        lines.append("- Text color or font-size mismatch")
        lines.append("")

    lines += [
        "## How to iterate",
        "",
        "1. Open the build in a browser",
        "2. Compare visually with `diff-heatmap.png`",
        "3. For each red band, identify the divergence in CSS",
        "4. Fix the specific token value, padding, or font-size",
        "5. Re-run `capture-build.py` then `pixel-diff.py`",
        "6. Loop until overall score ≥ 95%",
    ]

    (out_dir / "diff-report.md").write_text("\n".join(lines) + "\n")
    print(f"[diff] saved: {out_dir/'diff-report.md'}")
    print(f"[diff] overall match: {overall*100:.1f}% — "
          f"{'✅ accept' if overall > 0.95 else '⚠️  iterate' if overall > 0.85 else '❌ major fixes needed'}")

if __name__ == "__main__":
    main()
