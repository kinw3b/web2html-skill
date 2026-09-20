#!/usr/bin/env python3
"""5.1 — convert the signed 3.4 homepage into astro/src/pages/index.astro.

Homepage body comes from rebuild/index-polish.html (falls back to index.html).
Chrome is the 5.1 Header/Footer. In-page Paper / comment components replace
matching markup. Remaining <main> stays as signed HTML. Interiors are NOT
converted here — 5.2 authors them as .astro bodies on the same chrome.

  python3 convert-astro-home.py /path/to/project

Receipt qa/phase-5-home.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from html_to_astro import (
    apply_component_replacements,
    extract_regions,
    main_parts,
    page_file,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def convert(root: Path) -> dict:
    root = root.resolve()
    astro = root / "astro"
    pages_dir = astro / "src" / "pages"
    header = astro / "src" / "components" / "Header.astro"
    footer = astro / "src" / "components" / "Footer.astro"
    if not header.is_file() or not footer.is_file():
        raise FileNotFoundError("need Header.astro and Footer.astro from 5.1 extract-astro-components.py")
    polish = root / "rebuild" / "index-polish.html"
    home = polish if polish.is_file() else root / "rebuild" / "index.html"
    if not home.is_file():
        raise FileNotFoundError("need rebuild/index-polish.html or rebuild/index.html from 3.4")
    pages_dir.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    receipt_path = root / "qa" / "phase-5-components.json"
    if receipt_path.is_file():
        try:
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        catalog = [row for row in (payload.get("replacements") or []) if isinstance(row, dict)]
    errors: list[str] = []
    html = home.read_text(encoding="utf-8", errors="replace")
    regions = extract_regions(html)
    page = None
    if not regions["main"]:
        errors.append("homepage is missing <main>")
    else:
        main_html = apply_component_replacements(regions["main"], catalog)
        used = {
            part["name"]
            for part in main_parts(main_html)
            if part.get("type") == "component"
        }
        extras = [item for item in catalog if item.get("name") in used]
        dest = pages_dir / "index.astro"
        dest.write_text(
            page_file(
                title=regions["title"] or "Home",
                description=regions["description"],
                lang=regions["lang"],
                main_html=main_html,
                extras=extras,
            ),
            encoding="utf-8",
        )
        page = {
            "slug": "index",
            "route": "/",
            "source": str(home.relative_to(root)),
            "astro": str(dest.relative_to(root)),
            "components": sorted(used),
        }
    receipt = {
        "generatedFrom": "web2html/phase-5-home",
        "ok": page is not None and not errors,
        "page": page,
        "errors": errors,
        "updated": _now_iso(),
    }
    dest = root / "qa" / "phase-5-home.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = convert(args.root.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "page": receipt["page"]["astro"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
