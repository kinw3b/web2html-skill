#!/usr/bin/env python3
"""3.4 done — finalize the single ship file.

rebuild/index.html is the one homepage HTML from 2.2 onward: authored (2.2),
patched in place (2.3), locked (2.4), polished in place (3.1–3.3). Marking
3.4 done does not promote or archive anything — it strips the QA overlay
from index.html in place: no boot script, no qa-overlay link or script, no
data-qa-outlines, no data-qa-ship. The outlines toggle is review chrome, not
a ship feature (Pitfall #234). Idempotent.

Legacy bridge (2.34.0): a run started under the old three-file model may
still carry rebuild/index-polish.html, index-semantic.html, or index-raw.html.
finalize promotes the polish copy to index.html, moves the variants to
rebuild/archive/, then strips the overlay — the same outcome the old
promote_ship.py produced, so a resumed run cannot ship two entry points
(Pitfall #223). New runs never create those files; the write gate refuses
them.

  python3 finalize_ship.py /path/to/project
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE_NAMES = ("index-raw.html", "index-semantic.html", "polish-report.html")
RECEIPT = Path("qa/ship-promote.json")
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
    """Legacy only (pre-2.34 runs). New writes land on index.html directly."""
    return root / "rebuild" / "index-polish.html"


def ship_is_final(root: Path) -> bool:
    """True after finalize. The receipt is the signal."""
    receipt = root / RECEIPT
    if receipt.is_file():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and data.get("ok") and data.get("ship") == "rebuild/index.html":
            return True
    return False


def ship_ready(root: Path) -> bool:
    """3.4 may finish when the single ship file exists or the adopted export is the ship."""
    try:
        import run_config

        if run_config.adopt_mode(root):
            import source_fidelity

            ship = root / "source-html" / "index.html"
            return ship.is_file() and source_fidelity.load_snapshot(root) is not None and not source_fidelity.verify(root)
    except Exception:  # noqa: BLE001
        pass
    return ship_path(root).is_file() or polish_path(root).is_file()


def strip_overlay(html: str) -> str:
    """Drop every QA overlay hook from the ship document."""
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
    """The finalized ship must not still serve the overlay files."""
    for rel in ("css/qa-overlay.css", "js/qa-overlay.js"):
        path = rebuild / rel
        if path.is_file():
            path.unlink()


def _write_note(archive: Path) -> None:
    note = archive / "README.txt"
    if note.exists():
        return
    note.write_text(
        "Pre-2.34 homepage variants (legacy three-file model). Do not deploy these.\n"
        "rebuild/index.html is the only homepage HTML, polished in place since 2.2.\n"
        "The overlay and outlines are stripped from that file. They are not a query toggle.\n",
        encoding="utf-8",
    )


def _finalize_adopted(root: Path) -> dict:
    """Leave source-html/ as the ship. Do not copy it into rebuild/ or stamp the markup."""
    import source_fidelity

    ship = root / "source-html" / "index.html"
    if not ship.is_file():
        raise FileNotFoundError("need source-html/index.html — the provided folder is the ship")
    errors = source_fidelity.verify(root)
    if errors:
        raise FileNotFoundError(errors[0])
    if (root / "rebuild" / "index.html").is_file():
        raise FileNotFoundError("adopted run must not have rebuild/index.html — source-html/ is the ship")
    return {"ok": True, "already": False, "ship": "source-html/index.html", "archived": [], "adopted": True}


def finalize(root: Path) -> dict:
    root = root.resolve()
    try:
        import run_config
    except ImportError:
        run_config = None  # type: ignore[assignment]
    if run_config is not None and run_config.adopt_mode(root):
        return _finalize_adopted(root)
    rebuild = root / "rebuild"
    ship = ship_path(root)
    polish = polish_path(root)
    archived: list[str] = []
    if polish.is_file():
        # Legacy bridge: a pre-2.34 run polished a copy — that copy is the ship now.
        archive = rebuild / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        html = stamp_ship(polish.read_text(encoding="utf-8", errors="replace"))
        ship.write_text(html, encoding="utf-8")
        polish.unlink()
        for name in ARCHIVE_NAMES:
            moved = _archive_file(rebuild / name, archive)
            if moved:
                archived.append(moved)
        _ensure_vercelignore(rebuild)
        _write_note(archive)
    else:
        if not ship.is_file():
            raise FileNotFoundError(
                "need rebuild/index.html — 2.2 authors it, 3.x polishes it in place"
            )
        html = ship.read_text(encoding="utf-8", errors="replace")
        stamped = stamp_ship(html)
        if stamped == html and ship_is_final(root):
            return {"ok": True, "already": True, "ship": "rebuild/index.html", "archived": []}
        ship.write_text(stamped, encoding="utf-8")
    _drop_overlay_assets(rebuild)
    receipt = {
        "ok": True,
        "already": False,
        "writer": "finalize_ship.py",
        "at": _now(),
        "ship": "rebuild/index.html",
        "outlines": "removed",
        "overlay": "removed",
        "archived": archived,
        "archive": "rebuild/archive" if archived else None,
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
        receipt = finalize(args.root)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if receipt.get("adopted"):
        print("ship stays source-html/index.html — no rebuild/")
        return 0
    if receipt.get("archived"):
        print(f"ship finalize → rebuild/index.html  overlay removed  archived {', '.join(receipt['archived'])} (legacy)")
    else:
        print("ship finalize → rebuild/index.html  overlay removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
