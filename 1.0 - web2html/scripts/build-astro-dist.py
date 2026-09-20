#!/usr/bin/env python3
"""5.3 / 5.4 — `astro build`, then make astro/dist open on file://.

The clip loops (5.3 desktop, 5.4 live 768/390) screenshot the BUILT pages,
not the .astro source. This runs the build and rewrites root-absolute URLs in
astro/dist so `paper_23_rebuild_shots.py --ship astro/dist/{slug}/index.html`
works on file://. Never starts a server.

  python3 build-astro-dist.py /path/to/project

Receipt qa/phase-5-build.json (+ qa/phase-5-build.log).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from astro_build import build, dist_page_rel, relativize_dist, write_build_log
from html_to_astro import now_pages


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(root: Path, *, skip_build: bool = False) -> dict:
    root = root.resolve()
    if skip_build:
        result = {"built": False, "errors": [], "log": "", "relativized": relativize_dist(root / "astro" / "dist")}
    else:
        result = build(root)
    pages = []
    missing: list[str] = []
    for row in now_pages(root):
        rel = dist_page_rel(row["slug"])
        path = root / rel
        ok = path.is_file()
        if not ok:
            missing.append(rel)
        pages.append(
            {
                "slug": row["slug"],
                "route": row["route"],
                "astro": row.get("astro"),
                "dist": rel,
                "fileUrl": path.as_uri() if ok else None,
            }
        )
    errors = list(result["errors"])
    if missing and not errors:
        errors.append(f"missing built pages: {missing[:6]}")
    receipt = {
        "generatedFrom": "web2html/phase-5-build",
        "ok": bool(pages) and not errors,
        "built": result["built"],
        "skipBuild": skip_build,
        "pages": pages,
        "missing": missing,
        "relativized": result["relativized"],
        "errors": errors,
        "updated": _now_iso(),
    }
    log_rel = write_build_log(root, result["log"])
    if log_rel:
        receipt["buildLog"] = log_rel
    dest = root / "qa" / "phase-5-build.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--skip-build", action="store_true", help="only check + relativize an existing dist")
    args = ap.parse_args(argv)
    try:
        receipt = run(args.root.resolve(), skip_build=args.skip_build)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "built": receipt["built"], "pages": [row["dist"] for row in receipt["pages"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
