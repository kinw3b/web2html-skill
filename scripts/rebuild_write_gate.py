#!/usr/bin/env python3
"""HARD GATE — rebuild HTML is not a first-pass scrape.

Agents keep skipping capture / Paper / 1.4 and shipping a page. This module
is what `start`, `mark`, and the 2.x preflight call so that file cannot stay
in `rebuild/` before 2.1. 2.1 may write rebuild/design-system.html (token
contract, not the ship). The first allowed authored write is 2.2
rebuild/index-semantic.html. 2.3 seeds rebuild/index.html from that file.
Pitfall #148.

  python3 rebuild_write_gate.py /path/to/project
  python3 rebuild_write_gate.py /path/to/project --allow design-system   # 2.1
  python3 rebuild_write_gate.py /path/to/project --allow index           # 2.2 Author
  python3 rebuild_write_gate.py /path/to/project --allow polish          # 3.x QA
  python3 rebuild_write_gate.py /path/to/project --allow pages           # 5.2 raw dumps only (pages live in astro/)
  python3 rebuild_write_gate.py /path/to/project --quarantine

Exit 0 ok · 2 no board / predecessors open / freehand ship / unauthorized HTML
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

GENERATED_FROM = "web2html/rebuild-write-gate"
QA = Path("qa/rebuild-write-gate.json")
PROGRESS = Path("qa/pipeline-progress.json")
REVIEW = Path("qa/paper-human-review.md")
INDEX = Path("rebuild/index.html")
INDEX_SEMANTIC = Path("rebuild/index-semantic.html")
DESIGN_SYSTEM = Path("rebuild/design-system.html")
INDEX_POLISH = Path("rebuild/index-polish.html")
ALLOW_NONE = "none"
ALLOW_DESIGN_SYSTEM = "design-system"
ALLOW_INDEX = "index"
ALLOW_POLISH = "polish"
ALLOW_PAGES = "pages"
ALLOWS = (ALLOW_NONE, ALLOW_DESIGN_SYSTEM, ALLOW_INDEX, ALLOW_POLISH, ALLOW_PAGES)
LIVE_ALLOWS = ALLOWS
BEFORE_INDEX = ("1.1", "1.2", "1.3", "1.4")
BEFORE_POLISH = ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4")
BEFORE_PAGES = (
    "1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "3.1", "3.2", "3.3", "3.4",
    "4.1", "4.2", "4.3", "4.4",
)
SHIP_NAMES = (
    "index.html",
    "index-semantic.html",
    "design-system.html",
    "index-raw.html",
    "index-polish.html",
    "polish-report.html",
)
HOMEPAGE_KEEP = frozenset(SHIP_NAMES)


def interior_keep_names(root: Path) -> frozenset[str]:
    """rebuild/{slug}-raw.html from the Phase 4 page receipt. Interiors are .astro, never rebuild/{slug}.html."""
    names = set(HOMEPAGE_KEEP)
    pages = _read_json(root / "qa/phase-4-pages.json") if root else None
    rows = []
    if isinstance(pages, dict):
        raw = pages.get("pages")
        if isinstance(raw, list):
            rows = raw
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        if not slug or slug == "home":
            continue
        names.add(f"{slug}-raw.html")
    return frozenset(names)


KEEP_WITH_ALLOW = {
    ALLOW_NONE: frozenset(),
    ALLOW_DESIGN_SYSTEM: frozenset({"design-system.html"}),
    ALLOW_INDEX: frozenset(
        {
            "index.html",
            "index-semantic.html",
            "design-system.html",
            "index-raw.html",
        }
    ),
    ALLOW_POLISH: frozenset(
        {
            "index.html",
            "index-semantic.html",
            "design-system.html",
            "index-raw.html",
            "index-polish.html",
            "polish-report.html",
        }
    ),
    ALLOW_PAGES: HOMEPAGE_KEEP,
}
FREEHAND_MARKERS = (
    "cdn.tailwindcss.com",
    "unpkg.com/react",
    "unpkg.com/react-dom",
    "cdn.jsdelivr.net/npm/react",
    "/react.development",
    "/react.production",
    "@vite/client",
    "cdn.jsdelivr.net/npm/tailwindcss",
)
RAW_PAPER_EXPORT_RE = re.compile(
    r"data-export\s*=\s*[\"']get_jsx-inline-styles[\"']", re.I
)
BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "div", "footer", "form",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "nav",
        "ol", "p", "pre", "section", "table", "ul",
    }
)


class _ParagraphNestingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[str] = []
        self.violations: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCK_TAGS and "p" in self.stack:
            marker = f"<{tag}> inside <p>"
            if marker not in self.violations:
                self.violations.append(marker)
        self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1] == tag.lower():
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break


def ship_markup_errors(html: str) -> list[str]:
    """Reject converter metadata and HTML that browsers silently reparent."""
    errors: list[str] = []
    if RAW_PAPER_EXPORT_RE.search(html):
        errors.append(
            "raw Paper get_jsx export metadata remains in the authored page; "
            "2.2 authors index-semantic.html, it does not ship a dump"
        )
    parser = _ParagraphNestingParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        errors.append(f"could not validate paragraph nesting: {exc}")
    for violation in parser.violations[:5]:
        errors.append(
            f"invalid HTML nesting: {violation}; browser parsing changes the Paper layout"
        )
    return errors


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_steps(root: Path) -> dict[str, str] | None:
    data = _read_json(root / PROGRESS)
    if not data:
        return None
    raw = data.get("steps")
    if not isinstance(raw, dict):
        return None
    out: dict[str, str] = {}
    for sid, row in raw.items():
        if isinstance(row, dict):
            out[str(sid)] = str(row.get("status") or "pending")
        else:
            out[str(sid)] = "pending"
    return out


def missing_required(steps: dict[str, str] | None, required: tuple[str, ...]) -> list[str]:
    if steps is None:
        return list(required)
    return [sid for sid in required if steps.get(sid) != "done"]


def ship_pages(root: Path) -> list[Path]:
    rebuild = root / "rebuild"
    if not rebuild.is_dir():
        return []
    found: list[Path] = []
    for path in sorted(rebuild.glob("*.html")):
        if path.name in SHIP_NAMES or path.suffix == ".html":
            found.append(path)
    return found


def unauthorized_ship_pages(root: Path, allow: str) -> list[Path]:
    pages = ship_pages(root)
    keep = set(KEEP_WITH_ALLOW.get(allow, frozenset()))
    if allow == ALLOW_PAGES:
        keep = set(interior_keep_names(root))
    try:
        import run_config

        keep.update(run_config.adopt_keep_html_names(root))
    except Exception:  # noqa: BLE001
        pass
    return [path for path in pages if path.name not in keep]


def freehand_reasons(html: str, root: Path | None = None) -> list[str]:
    reasons: list[str] = []
    lowered = html.lower()
    for marker in FREEHAND_MARKERS:
        if marker in lowered:
            reasons.append(f"freehand runtime marker: {marker}")
    reasons.extend(ship_markup_errors(html))
    return reasons


def gate_errors(root: Path, allow: str = ALLOW_NONE) -> list[str]:
    root = root.resolve()
    if allow not in ALLOWS:
        return [f"unknown allow {allow!r}. Use: {' | '.join(LIVE_ALLOWS)}"]
    errors: list[str] = []
    steps = load_steps(root)
    if steps is None:
        errors.append(
            "no live board (qa/pipeline-progress.json). First tool is "
            "pipeline-progress.py start. Do not write HTML (Pitfall #148)."
        )
        if ship_pages(root):
            errors.append(
                "unauthorized rebuild HTML exists without a board. "
                "Quarantine it and start from 1.1."
            )
        return errors
    if allow in (ALLOW_INDEX, ALLOW_DESIGN_SYSTEM):
        missing = missing_required(steps, BEFORE_INDEX)
        if missing:
            target = (
                "rebuild/design-system.html"
                if allow == ALLOW_DESIGN_SYSTEM
                else "rebuild/index-semantic.html"
            )
            errors.append(
                f"cannot write {target} until 1.1–1.4 are done "
                f"({', '.join(missing)} still open). 2.1 is the Design System "
                "page; 2.2 authors the first-pass homepage (Pitfall #148)."
            )
    if allow == ALLOW_POLISH:
        missing = missing_required(steps, BEFORE_POLISH)
        if missing:
            errors.append(
                "cannot write rebuild/index-polish.html until 2.4 is done "
                f"({', '.join(missing)} still open). 3.x copies the 2.4 lock "
                "(Pitfall #203)."
            )
    if allow == ALLOW_PAGES:
        missing = missing_required(steps, BEFORE_PAGES)
        opted = (root / "qa" / "phase-5-opted.json").is_file()
        if missing or not opted:
            errors.append(
                "cannot write rebuild/{slug}-raw.html until 4.4 is done and "
                "qa/phase-5-opted.json exists. Phase 5 authors interiors as "
                "astro/src/pages/{slug}.astro on the 5.1 shared chrome; rebuild/ "
                "only takes the raw dumps."
            )
    leaked = unauthorized_ship_pages(root, allow)
    if leaked:
        rel = ", ".join(path.relative_to(root).as_posix() for path in leaked)
        errors.append(
            f"unauthorized ship HTML ({rel}). Delete or --quarantine it. "
            "Do not polish a freehand page (Pitfall #148)."
        )
    if allow == ALLOW_INDEX:
        for rel, label in (
            (INDEX_SEMANTIC, "rebuild/index-semantic.html"),
            (INDEX, "rebuild/index.html"),
        ):
            path = root / rel
            if not path.is_file():
                continue
            try:
                html = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append(f"cannot read {label}: {exc}")
            else:
                errors.extend(freehand_reasons(html, root))
    polish = root / INDEX_POLISH
    if allow == ALLOW_POLISH and polish.is_file():
        try:
            html = polish.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"cannot read rebuild/index-polish.html: {exc}")
        else:
            errors.extend(freehand_reasons(html, root))
    # index-raw.html is the Paper get_jsx reference. It may carry dump
    # metadata. Never run ship_markup_errors on it.
    return errors


def quarantine_unauthorized_ship(root: Path, allow: str = ALLOW_NONE) -> list[Path]:
    root = root.resolve()
    pages = unauthorized_ship_pages(root, allow)
    if not pages:
        return []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = root / "qa" / "quarantine" / f"bypass-{stamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []
    for src in pages:
        dest = dest_dir / src.name
        shutil.move(str(src), str(dest))
        moved.append(dest)
    return moved


def write_receipt(root: Path, allow: str, errors: list[str], quarantined: list[Path]) -> Path:
    dest = root / QA
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedFrom": GENERATED_FROM,
        "allow": allow,
        "ok": not errors,
        "errors": errors,
        "quarantined": [path.as_posix() for path in quarantined],
        "updated": _now_iso(),
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--allow", choices=ALLOWS, default=ALLOW_NONE)
    ap.add_argument(
        "--quarantine",
        action="store_true",
        help="Move unauthorized rebuild/*.html into qa/quarantine/bypass-*",
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    quarantined: list[Path] = []
    if args.quarantine:
        quarantined = quarantine_unauthorized_ship(root, args.allow)
        for path in quarantined:
            print(f"quarantine → {path}", file=sys.stderr)
    errors = gate_errors(root, args.allow)
    write_receipt(root, args.allow, errors, quarantined)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print("rebuild-write-gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
