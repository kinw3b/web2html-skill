#!/usr/bin/env python3
"""3.4 done — one homepage entry for the Vercel / GitHub ship.

`rebuild/index-polish.html` becomes `rebuild/index.html`. The 2.4 lock,
`index-raw.html`, and `index-semantic.html` move to `rebuild/archive/`.
Outlines are off on that ship (`data-qa-ship="final"`). `?qa-outlines=tags`
(or `on` / `mono` / `off`) turns them back on. Idempotent.

  python3 promote_ship.py /path/to/project
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
ARCHIVE_NAMES = ("index-raw.html", "index-semantic.html", "polish-report.html")
RECEIPT = Path("qa/ship-promote.json")
SHIP_ATTR = 'data-qa-ship="final"'
OUTLINES_OFF = 'data-qa-outlines="off"'
VERCELIGNORE_LINE = "archive"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ship_path(root: Path) -> Path:
    return root / "rebuild" / "index.html"


def polish_path(root: Path) -> Path:
    return root / "rebuild" / "index-polish.html"


def ship_is_final(root: Path) -> bool:
    path = ship_path(root)
    if not path.is_file():
        return False
    try:
        return SHIP_ATTR in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def ship_ready(root: Path) -> bool:
    """3.4 may finish when polish still exists, or when promote already ran."""
    return polish_path(root).is_file() or ship_is_final(root)


def stamp_ship(html: str) -> str:
    """Outlines off, ship flag on. Overlay assets stay so a query param can toggle."""
    if SHIP_ATTR not in html:
        if "<html" in html:
            html = html.replace("<html", f"<html {SHIP_ATTR}", 1)
        else:
            html = f'<html {SHIP_ATTR}>{html}'
    if re.search(r'data-qa-outlines="[^"]*"', html):
        html = re.sub(r'data-qa-outlines="[^"]*"', OUTLINES_OFF, html, count=1)
    elif "<html" in html:
        html = html.replace("<html", f"<html {OUTLINES_OFF}", 1)
    return html


def _archive_file(src: Path, archive: Path) -> str | None:
    if not src.is_file():
        return None
    dest = archive / src.name
    if dest.exists():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    return src.name


def _ensure_vercelignore(rebuild: Path) -> None:
    """A Vercel project rooted at rebuild/ must not upload the old entry points."""
    path = rebuild / ".vercelignore"
    try:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        return
    lines = [line.strip() for line in text.splitlines()]
    if VERCELIGNORE_LINE in lines:
        return
    path.write_text((text.rstrip() + "\n" if text.strip() else "") + VERCELIGNORE_LINE + "\n", encoding="utf-8")


def _refresh_overlay(rebuild: Path) -> None:
    """Ship must load the JS that honors data-qa-ship, not a 2.4 copy that defaults to tags."""
    for name, dest_dir in (("qa-overlay.css", "css"), ("qa-overlay.js", "js")):
        src = TEMPLATES / name
        if not src.is_file():
            continue
        dest = rebuild / dest_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _write_note(archive: Path) -> None:
    note = archive / "README.txt"
    if note.exists():
        return
    note.write_text(
        "Pre-3.4 homepage variants. Do not deploy these as the site root.\n"
        "rebuild/index.html is the ship (promoted index-polish.html).\n"
        "Outlines are off. ?qa-outlines=tags (or on / mono / off) toggles them.\n",
        encoding="utf-8",
    )


def promote(root: Path) -> dict:
    root = root.resolve()
    rebuild = root / "rebuild"
    polish = polish_path(root)
    ship = ship_path(root)
    if not polish.is_file() and ship_is_final(root):
        return {"ok": True, "already": True, "ship": "rebuild/index.html", "archived": []}
    if not polish.is_file():
        raise FileNotFoundError(
            "need rebuild/index-polish.html — 3.1 seeds it; 3.4 promote makes it index.html"
        )
    archive = rebuild / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    if ship.is_file() and not ship_is_final(root):
        moved = _archive_file(ship, archive)
        if moved:
            archived.append(moved)
    for name in ARCHIVE_NAMES:
        moved = _archive_file(rebuild / name, archive)
        if moved:
            archived.append(moved)
    html = stamp_ship(polish.read_text(encoding="utf-8", errors="replace"))
    ship.write_text(html, encoding="utf-8")
    polish.unlink()
    _refresh_overlay(rebuild)
    _ensure_vercelignore(rebuild)
    _write_note(archive)
    receipt = {
        "ok": True,
        "already": False,
        "writer": "promote_ship.py",
        "at": _now(),
        "ship": "rebuild/index.html",
        "outlines": "off",
        "toggle": "?qa-outlines=tags|on|mono|off",
        "archived": archived,
        "archive": "rebuild/archive",
    }
    receipt_path = root / RECEIPT
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = promote(args.root)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if receipt.get("already"):
        print("ship promote → already rebuild/index.html")
    else:
        archived = ", ".join(receipt.get("archived") or []) or "none"
        print(f"ship promote → rebuild/index.html  outlines off  archived {archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
