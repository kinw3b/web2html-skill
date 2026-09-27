#!/usr/bin/env python3
"""3.4 done — one homepage entry for the Vercel / GitHub ship.

`rebuild/index-polish.html` becomes `rebuild/index.html`. The 2.4 lock,
`index-raw.html`, and `index-semantic.html` move to `rebuild/archive/`.
The promoted document has no QA overlay: no boot script, no qa-overlay
link or script, no data-qa-outlines, no data-qa-ship. The review toggle
stays on index-polish.html until this promote. Idempotent.

  python3 promote_ship.py /path/to/project
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
ARCHIVE_NAMES = ("index-raw.html", "index-semantic.html", "polish-report.html")
RECEIPT = Path("qa/ship-promote.json")
SHIP_ATTR = 'data-qa-ship="final"'
VERCELIGNORE_LINE = "archive"
BOOT_RE = re.compile(
    r"""<script\b[^>]*\bid=["']qa-outlines-boot["'][^>]*>.*?</script>\s*""",
    re.I | re.S,
)
OVERLAY_LINK_RE = re.compile(
    r"""<link\b[^>]*href=["'][^"']*qa-overlay[^"']*["'][^>]*/?>\s*""",
    re.I,
)
OVERLAY_SCRIPT_RE = re.compile(
    r"""<script\b[^>]*src=["'][^"']*qa-overlay[^"']*["'][^>]*>\s*</script>\s*""",
    re.I,
)
QA_ATTR_RE = re.compile(
    r'\s(?:data-qa-outlines|data-qa-ship|data-qa-review)="[^"]*"'
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ship_path(root: Path) -> Path:
    return root / "rebuild" / "index.html"


def polish_path(root: Path) -> Path:
    return root / "rebuild" / "index-polish.html"


def ship_is_final(root: Path) -> bool:
    """True after promote. The receipt is the signal — the ship HTML no longer carries a QA attribute."""
    receipt = root / RECEIPT
    if receipt.is_file():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and data.get("ok") and data.get("ship") == "rebuild/index.html":
            return True
    path = ship_path(root)
    if not path.is_file():
        return False
    try:
        return SHIP_ATTR in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def ship_ready(root: Path) -> bool:
    """3.4 may finish when polish still exists, when promote already ran, or when an adopted export is the ship."""
    try:
        import run_config

        if run_config.adopt_mode(root):
            import source_fidelity

            ship = root / "source-html" / "index.html"
            return ship.is_file() and source_fidelity.load_snapshot(root) is not None and not source_fidelity.verify(root)
    except Exception:  # noqa: BLE001
        pass
    return polish_path(root).is_file() or ship_is_final(root)


def strip_overlay(html: str) -> str:
    """Drop every QA overlay hook from the promoted document."""
    html = BOOT_RE.sub("", html)
    html = OVERLAY_LINK_RE.sub("", html)
    html = OVERLAY_SCRIPT_RE.sub("", html)
    html = QA_ATTR_RE.sub("", html)
    return html


def stamp_ship(html: str) -> str:
    """Final source of truth: no overlay, no outlines, no QA attributes."""
    return strip_overlay(html)


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


def _drop_overlay_assets(rebuild: Path) -> None:
    """The polished ship must not still serve the overlay files."""
    for rel in ("css/qa-overlay.css", "js/qa-overlay.js"):
        path = rebuild / rel
        if path.is_file():
            path.unlink()


def _write_note(archive: Path) -> None:
    note = archive / "README.txt"
    if note.exists():
        return
    note.write_text(
        "Pre-3.4 homepage variants. Do not deploy these as the site root.\n"
        "rebuild/index.html is the ship (promoted index-polish.html).\n"
        "The overlay and outlines are removed from that file. They are not a query toggle.\n",
        encoding="utf-8",
    )


def _promote_adopted(root: Path) -> dict:
    """Leave source-html/ as the ship. Do not copy it into rebuild/ or stamp the markup."""
    import source_fidelity

    ship = root / "source-html" / "index.html"
    if not ship.is_file():
        raise FileNotFoundError("need source-html/index.html — the provided folder is the ship")
    errors = source_fidelity.verify(root)
    if errors:
        raise FileNotFoundError(errors[0])
    if (root / "rebuild" / "index.html").is_file() or (root / "rebuild" / "index-polish.html").is_file():
        raise FileNotFoundError("adopted run must not have rebuild/index.html — source-html/ is the ship")
    return {"ok": True, "already": False, "ship": "source-html/index.html", "archived": [], "adopted": True}


def promote(root: Path) -> dict:
    root = root.resolve()
    try:
        import run_config
    except ImportError:
        run_config = None  # type: ignore[assignment]
    if run_config is not None and run_config.adopt_mode(root):
        return _promote_adopted(root)
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
    _drop_overlay_assets(rebuild)
    _ensure_vercelignore(rebuild)
    _write_note(archive)
    receipt = {
        "ok": True,
        "already": False,
        "writer": "promote_ship.py",
        "at": _now(),
        "ship": "rebuild/index.html",
        "outlines": "removed",
        "overlay": "removed",
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
        print(f"ship promote → rebuild/index.html  overlay removed  archived {archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
