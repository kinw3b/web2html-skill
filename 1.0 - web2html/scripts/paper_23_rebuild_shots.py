#!/usr/bin/env python3
"""2.3 — file:// rebuild shots at Paper widths.

Pairs with references/section-23-paper-loop.md. Does not talk to Paper MCP.
Gold is the 1.2 source-section clips already on disk.

  python3 paper_23_rebuild_shots.py /path/to/project --id hero
  python3 paper_23_rebuild_shots.py /path/to/project --all

Exit 0 ok (or Playwright skipped) · 2 missing ship / unknown id
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WIDTHS = (1600, 768, 390)


def run_widths(root: Path) -> tuple[int, ...]:
    """Configured widths from qa/run-config.json (fast run = 1600 + 390)."""
    try:
        import run_config

        return tuple(run_config.widths(root))
    except Exception:  # noqa: BLE001
        return WIDTHS
SHIP = Path("rebuild/index.html")
OUT_DIR = Path("qa/paper-measure/rebuild")
SKIP = Path("qa/paper-measure/rebuild-shots-skip.json")
INDEX = Path("qa/paper-measure/_index.json")
GENERATED_FROM = "web2html/section-23-paper-loop"
SECTION_ID_RE = re.compile(r'<section\b[^>]*\bid=["\']([^"\']+)["\']', re.I)
FOOTER_RE = re.compile(r"<footer\b([^>]*)>", re.I)
FOOTER_ID_RE = re.compile(r"""\bid=["']([^"']+)["']""", re.I)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ship_section_ids(html: str) -> list[str]:
    seen: list[str] = []
    for match in SECTION_ID_RE.finditer(html):
        sid = match.group(1).strip()
        if sid and sid not in seen:
            seen.append(sid)
    footer = FOOTER_RE.search(html)
    if footer:
        attrs = footer.group(1) or ""
        found = FOOTER_ID_RE.search(attrs)
        fid = (found.group(1).strip() if found else "footer") or "footer"
        if fid not in seen:
            seen.append(fid)
    return seen


def locator_selector(section_id: str) -> str:
    if section_id == "footer":
        return "footer"
    return f"#{section_id}"


def shot_path(root: Path, section_id: str, width: int, page: str = "home") -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", section_id).strip("-") or "section"
    if page and page != "home":
        return root / OUT_DIR / page / f"{safe}-{width}.png"
    return root / OUT_DIR / f"{safe}-{width}.png"


def file_url(root: Path, ship: Path = SHIP) -> str:
    return (root / ship).resolve().as_uri()


def write_skip(root: Path, reason: str) -> Path:
    dest = root / SKIP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": True,
                "skipped": True,
                "reason": reason,
                "updated": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def capture(
    root: Path,
    section_ids: list[str],
    *,
    ship: Path = SHIP,
    page: str = "home",
    widths: tuple[int, ...] | None = None,
) -> dict:
    """Screenshot each section at the requested widths. Requires Playwright."""
    widths = tuple(widths) if widths else run_widths(root)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        write_skip(root, "Playwright not installed — measure Paper MCP + DevTools instead")
        return {"ok": True, "skipped": True, "shots": []}

    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []
    url = file_url(root, ship)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in widths:
                page_view = browser.new_page(viewport={"width": width, "height": 1200})
                page_view.goto(url, wait_until="load")
                page_view.evaluate("window.scrollTo(0, 0)")
                for sid in section_ids:
                    locator = page_view.locator(locator_selector(sid)).first
                    dest = shot_path(root, sid, width, page)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if locator.count() == 0:
                        shots.append(
                            {
                                "id": sid,
                                "width": width,
                                "path": None,
                                "error": f"missing #{sid}",
                            }
                        )
                        continue
                    locator.scroll_into_view_if_needed()
                    locator.screenshot(path=str(dest))
                    shots.append(
                        {
                            "id": sid,
                            "width": width,
                            "path": dest.relative_to(root).as_posix(),
                        }
                    )
                page_view.close()
        finally:
            browser.close()
    skip = root / SKIP
    if skip.is_file():
        skip.unlink()
    return {"ok": all("error" not in row for row in shots), "skipped": False, "shots": shots}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--id", action="append", dest="ids", help="section id (repeatable)")
    ap.add_argument("--all", action="store_true", help="every <section id> in the ship page")
    ap.add_argument("--page", default="home")
    ap.add_argument("--ship", default="")
    ap.add_argument("--widths", default="")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    ship_rel = Path(args.ship) if args.ship else (
        SHIP if args.page == "home" else Path(f"rebuild/{args.page}.html")
    )
    widths = tuple(int(part.strip()) for part in args.widths.split(",") if part.strip()) or run_widths(root)
    ship = root / ship_rel
    if not ship.is_file():
        print(f"FAIL: missing {ship_rel.as_posix()}", file=sys.stderr)
        return 2
    html = ship.read_text(encoding="utf-8")
    available = ship_section_ids(html)
    if args.all:
        ids = available
    elif args.ids:
        ids = args.ids
        missing = [sid for sid in ids if sid not in available]
        if missing:
            print(f"FAIL: unknown section id(s) {missing} — ship has {available}", file=sys.stderr)
            return 2
    else:
        print("FAIL: pass --id <section> or --all", file=sys.stderr)
        return 2
    if not ids:
        print(f"FAIL: no <section id> in {ship_rel.as_posix()}", file=sys.stderr)
        return 2
    result = capture(root, ids, ship=ship_rel, page=args.page, widths=widths)
    receipt = root / OUT_DIR / "shots.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({**result, "updated": _now_iso()}, indent=2) + "\n")
    if result.get("skipped"):
        print("paper-23-shots: skipped (no Playwright)")
        return 0
    errors = [row for row in result["shots"] if "error" in row]
    if errors:
        for row in errors:
            print(f"FAIL: {row['id']}@{row['width']} {row['error']}", file=sys.stderr)
        return 2
    print(f"paper-23-shots: ok {len(result['shots'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
