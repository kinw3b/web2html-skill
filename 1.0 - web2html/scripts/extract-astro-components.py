#!/usr/bin/env python3
"""5.1 — extract the shared chrome + components from the 3.4 polish homepage.

Lifts Header + Footer ONCE (every later page reuses them), then every
Paper-backed button / data-component / comment-nominated block that can
stay lean across routes. Runs after scaffold-astro.py.

  python3 extract-astro-components.py /path/to/project
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from html_to_astro import (
    control_component_file,
    extract_regions,
    fragment_file,
    inventory_components,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def extract(root: Path) -> dict:
    root = root.resolve()
    polish = root / "rebuild" / "index-polish.html"
    home = polish if polish.is_file() else root / "rebuild" / "index.html"
    if not home.is_file():
        raise FileNotFoundError("need rebuild/index-polish.html or rebuild/index.html")
    astro = root / "astro"
    if not (astro / "src" / "layouts" / "BaseLayout.astro").is_file():
        raise FileNotFoundError("need astro/ from 5.1 scaffold-astro.py")
    regions = extract_regions(home.read_text(encoding="utf-8", errors="replace"))
    errors: list[str] = []
    if not regions["header"]:
        errors.append("homepage is missing <header>")
    if not regions["footer"]:
        errors.append("homepage is missing <footer>")
    components = astro / "src" / "components"
    components.mkdir(parents=True, exist_ok=True)
    written = []
    catalog = []
    if regions["header"]:
        (components / "Header.astro").write_text(fragment_file(regions["header"]), encoding="utf-8")
        written.append("src/components/Header.astro")
        catalog.append({
            "name": "Header",
            "kind": "chrome",
            "mode": "fragment",
            "file": "src/components/Header.astro",
            "import": "../components/Header.astro",
            "html": regions["header"],
            "sources": ["html:header"],
        })
    if regions["footer"]:
        (components / "Footer.astro").write_text(fragment_file(regions["footer"]), encoding="utf-8")
        written.append("src/components/Footer.astro")
        catalog.append({
            "name": "Footer",
            "kind": "chrome",
            "mode": "fragment",
            "file": "src/components/Footer.astro",
            "import": "../components/Footer.astro",
            "html": regions["footer"],
            "sources": ["html:footer"],
        })
    found = inventory_components(root)
    for item in found["inventory"]:
        name = item["name"]
        if name in {"Header", "Footer"}:
            continue
        dest = components / f"{name}.astro"
        body = control_component_file(item["html"]) if item.get("mode") == "props" else fragment_file(item["html"])
        dest.write_text(body, encoding="utf-8")
        rel = f"src/components/{name}.astro"
        written.append(rel)
        catalog.append({
            "name": name,
            "kind": item.get("kind") or "component",
            "mode": item.get("mode") or "fragment",
            "file": rel,
            "import": f"../components/{name}.astro",
            "html": item.get("html") or "",
            "sources": item.get("sources") or [],
            "uses": item.get("uses") or 0,
            "pages": item.get("pages") or [],
            "reason": item.get("reason") or "",
        })
    receipt = {
        "generatedFrom": "web2html/phase-5-components",
        "ok": bool(written) and not errors,
        "source": str(home.relative_to(root)),
        "components": written,
        "inventory": catalog,
        "skipped": found["skipped"],
        "paper": found["paper"],
        "nominated": found["nominated"],
        "replacements": [
            row for row in catalog if row["name"] not in {"Header", "Footer"}
        ],
        "errors": errors,
        "updated": _now_iso(),
    }
    dest = root / "qa" / "phase-5-components.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = extract(args.root.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(json.dumps({
        "ok": True,
        "components": receipt["components"],
        "extracted": [row["name"] for row in receipt["inventory"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
