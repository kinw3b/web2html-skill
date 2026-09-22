#!/usr/bin/env python3
"""2.3 — pull numbered 1.2 source-section clips and pair them with rebuild shots.

1.2 already stored each band as NN-slug.png at 1600 / 768 / 390:
  capture/home-{desktop,768,390}/source-sections/01-hero.png
This script copies those into qa/paper-measure/compare/ and writes a
side-by-side (1.2 left, rebuild right) so 2.3 reads the clips — it does
not re-query Paper MCP.

  python3 paper_23_clip_compare.py /path/to/project

Exit 0 every ship band has a pulled 1.2 clip at all three widths (and a
rebuild pair unless shots were skipped). Exit 2 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_disk_gold as gold
import paper_23_rebuild_shots as shots

GENERATED_FROM = "web2html/section-23-clip-compare"
OUT = Path("qa/paper-measure/clip-compare.json")
COMPARE_DIR = Path("qa/paper-measure/compare")
SKIP = Path("qa/paper-measure/rebuild-shots-skip.json")
WIDTHS = (1600, 768, 390)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def safe_stem(nn: str | None, slug: str, width: int) -> str:
    number = nn if nn and re.fullmatch(r"\d{2}", nn) else "00"
    name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", slug).strip("-") or "section"
    return f"{number}-{name}-{width}"


def side_by_side(source: Path, rebuild: Path, dest: Path) -> bool:
    """1.2 clip left, rebuild right. Returns False if Pillow is missing."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    try:
        left = Image.open(source).convert("RGB")
        right = Image.open(rebuild).convert("RGB")
    except (OSError, ValueError):
        return False
    col_w = 620

    def scale(image: Image.Image) -> Image.Image:
        height = max(1, int(image.size[1] * col_w / max(image.size[0], 1)))
        return image.resize((col_w, height), Image.LANCZOS)

    left_s, right_s = scale(left), scale(right)
    gutter, pad, label_h = 28, 20, 34
    canvas_h = max(left_s.size[1], right_s.size[1]) + label_h + pad * 2
    canvas = Image.new("RGB", (col_w * 2 + gutter + pad * 2, canvas_h), (18, 18, 22))
    canvas.paste(left_s, (pad, pad + label_h))
    canvas.paste(right_s, (pad + col_w + gutter, pad + label_h))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, pad + 8), f"1.2 {source.name}", fill=(150, 150, 160))
    draw.text((pad + col_w + gutter, pad + 8), f"rebuild {rebuild.name}", fill=(150, 150, 160))
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)
    return True


def pull(root: Path, src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest.resolve().relative_to(root).as_posix()


def compare_project(
    root: Path,
    *,
    page: str = "home",
    widths: tuple[int, ...] | None = None,
) -> dict:
    root = root.resolve()
    widths = tuple(widths) if widths else gold.run_widths(root)
    mapped = gold.build_index(root, page=page, widths=widths)
    gold_rel = gold.OUT if page == "home" else Path(f"qa/paper-measure/disk-gold-{page}.json")
    gold.write_index(root, mapped, gold_rel)
    skip = _read_json(root / SKIP)
    shots_skipped = bool(skip and skip.get("skipped") is True)
    out_dir = root / COMPARE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs: list[dict] = []
    missing: list[str] = []
    sides = 0
    for row in mapped.get("sections") or []:
        sid = str(row.get("id") or "")
        nn = row.get("nn")
        slug = str(row.get("slug") or sid)
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        rebuild = row.get("rebuild") if isinstance(row.get("rebuild"), dict) else {}
        for width in widths:
            key = str(width)
            stem = safe_stem(nn if isinstance(nn, str) else None, slug, width)
            src_rel = source.get(key)
            src_abs = root / str(src_rel) if src_rel else None
            reb_rel = rebuild.get(key)
            reb_abs = root / str(reb_rel) if reb_rel else shots.shot_path(root, sid, width, page)
            pair = {
                "id": sid,
                "nn": nn,
                "slug": slug,
                "width": width,
                "source": src_rel,
                "rebuild": reb_rel if reb_abs.is_file() else None,
                "pulledSource": None,
                "pulledRebuild": None,
                "side": None,
            }
            if src_abs is None or not src_abs.is_file():
                missing.append(f"{sid}@{width} source")
                pairs.append(pair)
                continue
            pair["pulledSource"] = pull(root, src_abs, out_dir / f"{stem}-source.png")
            if reb_abs.is_file():
                pair["rebuild"] = reb_abs.relative_to(root).as_posix()
                pair["pulledRebuild"] = pull(root, reb_abs, out_dir / f"{stem}-rebuild.png")
                side_abs = out_dir / f"{stem}-side.png"
                if side_by_side(src_abs, reb_abs, side_abs):
                    pair["side"] = side_abs.relative_to(root).as_posix()
                    sides += 1
            elif not shots_skipped:
                missing.append(f"{sid}@{width} rebuild")
            pairs.append(pair)
    return {
        "generatedFrom": GENERATED_FROM,
        "ok": bool(mapped.get("sections")) and not missing,
        "page": page,
        "widths": list(widths),
        "shotsSkipped": shots_skipped,
        "sides": sides,
        "pairs": pairs,
        "missing": missing,
        "updated": _now_iso(),
    }


def write_index(root: Path, payload: dict, dest_rel: Path = OUT) -> Path:
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--page", default="home")
    ap.add_argument("--widths", default="")
    ap.add_argument("--receipt", default=str(OUT))
    args = ap.parse_args(argv)
    root = args.root.resolve()
    widths = gold.parse_widths(args.widths or None, root)
    ship = gold.ship_rel_for(args.page)
    if not (root / ship).is_file():
        print(f"FAIL: missing {ship.as_posix()}", file=sys.stderr)
        return 2
    payload = compare_project(root, page=args.page, widths=widths)
    dest = write_index(root, payload, Path(args.receipt))
    if not payload["ok"]:
        print(f"FAIL: {dest.relative_to(root)} missing {payload['missing']}", file=sys.stderr)
        return 2
    print(
        f"paper-23-clip-compare: ok {len(payload['pairs'])} pairs "
        f"({payload['sides']} side-by-sides)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
