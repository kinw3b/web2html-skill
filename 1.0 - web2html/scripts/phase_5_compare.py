#!/usr/bin/env python3
"""5.3 / 5.4 — disk-gold clip compare for every interior page.

The ship is the BUILT page: astro/dist/{slug}/index.html (build-astro-dist.py).
Shots come from paper_23_rebuild_shots.py --page {slug} --ship <that file>.

  python3 phase_5_compare.py /path/to/project --mode desktop
  python3 phase_5_compare.py /path/to/project --mode responsive

desktop → 1600 only → qa/phase-5-clip-compare.json
responsive → 768,390 → qa/phase-5-responsive.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_clip_compare as compare
import paper_23_disk_gold as gold
from astro_build import dist_page_rel

RECEIPTS = {
    "desktop": (Path("qa/phase-5-clip-compare.json"), (1600,)),
    "responsive": (Path("qa/phase-5-responsive.json"), (768, 390)),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def pages(root: Path) -> list[dict]:
    src = root / "qa" / "phase-4-pages.json"
    if not src.is_file():
        raise FileNotFoundError("need qa/phase-4-pages.json")
    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload.get("pages") if isinstance(payload, dict) else []
    return [row for row in rows or [] if isinstance(row, dict) and row.get("slug") not in {None, "", "home"}]


def run(root: Path, mode: str) -> dict:
    dest_rel, widths = RECEIPTS[mode]
    rows = []
    missing: list[str] = []
    for row in pages(root):
        slug = str(row["slug"])
        for width in widths:
            folder = gold.lander_dir(slug, width)
            if not (root / folder).is_dir():
                missing.append(f"{slug} missing {folder.as_posix()}")
        ship = Path(dist_page_rel(slug))
        if not (root / ship).is_file():
            missing.append(f"missing {ship.as_posix()} — run build-astro-dist.py first")
            continue
        payload = compare.compare_project(root, page=slug, widths=widths)
        rows.append({"slug": slug, "ok": payload.get("ok"), "missing": payload.get("missing") or []})
        missing.extend(f"{slug}:{item}" for item in payload.get("missing") or [])
    receipt = {
        "generatedFrom": "web2html/phase-5-compare",
        "ok": bool(rows) and not missing,
        "mode": mode,
        "widths": list(widths),
        "pages": rows,
        "missing": missing,
        "updated": _now_iso(),
    }
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--mode", choices=sorted(RECEIPTS), required=True)
    args = ap.parse_args(argv)
    try:
        receipt = run(args.root.resolve(), args.mode)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        print(f"FAIL: {receipt['missing']}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "mode": args.mode, "pages": len(receipt["pages"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
