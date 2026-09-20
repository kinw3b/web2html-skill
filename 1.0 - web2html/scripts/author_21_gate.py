#!/usr/bin/env python3
"""HARD GATE — 2.2 authored the first-pass page. Paper + 2.1 tokens are the brief.

The first allowed write of rebuild/index-semantic.html is 2.2. That file is
model-authored semantic HTML+CSS via frontend-design — not a get_jsx dump,
not a pc-id join, not the 2.1 design-system page, not the 2.4 lock.
2.3 seeds rebuild/index.html from this file. Painted <a> keep look;
hrefs stay in-page (# / #id). No live-site or external URLs.

  python3 author_21_gate.py /path/to/project

Exit 0 ok · 2 missing page / dump leftover / no 2.2 receipt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from rebuild_write_gate import RAW_PAPER_EXPORT_RE, ship_markup_errors
from jsx_to_static_html import SELF_CLOSE_DIV_RE, JSX_STYLE_RE, JSON_JSX_RE

GENERATED_FROM = "web2html/author-21"
RECEIPT = Path("qa/frontend-design-21.md")
QA = Path("qa/author-21-qa.json")
SHIP = Path("rebuild/index-semantic.html")
RAW = Path("rebuild/index-raw.html")
TOKENS = Path("rebuild/css/tokens.css")
LIBRARY = Path("design-library/library.json")
SKIP_LINK_RE = re.compile(
    r"""id\s*=\s*["']skip(?:-to)?(?:-content)?["']|class\s*=\s*["'][^"']*skip-link""",
    re.I,
)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
A_TAG_RE = re.compile(r"<a\b([^>]*)>", re.I)
HREF_ATTR_RE = re.compile(
    r"""\bhref\s*=\s*(?:['"]([^'"]*)['"]|([^\s>]+))""",
    re.I,
)


def is_in_page_href(value: str) -> bool:
    """Painted <a> may exist; destinations stay on this file:// homepage."""
    href = unescape((value or "").strip())
    if href == "" or href == "#":
        return True
    if href.startswith("#") and "://" not in href:
        return True
    return False


def off_page_hrefs(html: str, *, limit: int = 8) -> list[str]:
    """Live-site / external <a href> values copied onto the ship."""
    body = COMMENT_RE.sub("", html or "")
    found: list[str] = []
    seen: set[str] = set()
    for tag in A_TAG_RE.finditer(body):
        match = HREF_ATTR_RE.search(tag.group(1) or "")
        if not match:
            continue
        href = (match.group(1) if match.group(1) is not None else match.group(2) or "")
        href = unescape(href).strip()
        if is_in_page_href(href) or href in seen:
            continue
        seen.add(href)
        found.append(href)
        if len(found) >= limit:
            break
    return found


def raw_reference_errors(html: str, *, fonts_css: bool = False) -> list[str]:
    """index-raw.html must be file:// HTML, not a JSON/JSX blob."""
    errors: list[str] = []
    stripped = COMMENT_RE.sub("", html or "").lstrip()
    if not stripped:
        return ["rebuild/index-raw.html is empty"]
    if stripped.startswith("{") or JSON_JSX_RE.search(stripped[:1500]):
        errors.append(
            "rebuild/index-raw.html is a JSON get_jsx payload — run "
            "dump_index_raw.py so 2.3 can open it as HTML (Pitfall #199)"
        )
    if JSX_STYLE_RE.search(html or ""):
        errors.append(
            "rebuild/index-raw.html still has JSX style={{}} — convert with dump_index_raw.py"
        )
    if SELF_CLOSE_DIV_RE.search(html or ""):
        errors.append(
            "rebuild/index-raw.html has self-closing <div /> — browsers treat those "
            "as unclosed tags and the dump paints blank (Pitfall #16 #199)"
        )
    if "tokens.css" not in (html or ""):
        errors.append("rebuild/index-raw.html must link css/tokens.css (2.1 tokens)")
    if fonts_css and "fonts.css" not in (html or ""):
        errors.append(
            "rebuild/index-raw.html must link css/fonts.css — tokens.css names "
            "families, @font-face loads the woff2 (Pitfall #164)"
        )
    if not RAW_PAPER_EXPORT_RE.search(html or ""):
        errors.append(
            'rebuild/index-raw.html must keep data-export="get_jsx-inline-styles"'
        )
    return errors


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def gate_errors(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    ship = root / SHIP
    if not ship.is_file():
        return [
            "missing rebuild/index-semantic.html — 2.2 authors the first-pass "
            "page with frontend-design"
        ]
    try:
        html = ship.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"cannot read rebuild/index-semantic.html: {exc}"]
    if RAW_PAPER_EXPORT_RE.search(html):
        errors.append(
            "raw Paper get_jsx export metadata remains in rebuild/index-semantic.html; "
            "2.2 authors the page, it does not ship a dump"
        )
    errors.extend(ship_markup_errors(html))
    if SKIP_LINK_RE.search(html):
        errors.append("invented skip-link — Paper did not paint that chrome")
    leaked = off_page_hrefs(html)
    if leaked:
        sample = ", ".join(leaked)
        errors.append(
            "source/external <a href> on the ship — 2.2 does not copy live URLs; "
            f"painted links stay in-page (# or #id): {sample}"
        )
    if not (root / RECEIPT).is_file():
        errors.append(f"missing {RECEIPT} — record what frontend-design authored at 2.2")
    if not (root / RAW).is_file():
        errors.append(
            "missing rebuild/index-raw.html — 2.2 writes Paper get_jsx of "
            "home-desktop as the raw reference (not the ship)"
        )
    else:
        try:
            raw_html = (root / RAW).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"cannot read rebuild/index-raw.html: {exc}")
        else:
            errors.extend(
                raw_reference_errors(
                    raw_html,
                    fonts_css=(root / "rebuild" / "css" / "fonts.css").is_file(),
                )
            )
    if not (root / TOKENS).is_file() and not (root / LIBRARY).is_file():
        errors.append(
            "missing 2.1 tokens — 2.2 uses the Design System page, not a new identity"
        )
    return errors


def ready(root: Path) -> bool:
    return not gate_errors(root)


def install_passing_artifacts(root: Path) -> None:
    root = root.resolve()
    from design_system_21_gate import install_passing_artifacts as install_ds

    install_ds(root)
    (root / SHIP).write_text(
        "<!doctype html><html lang=\"en\"><head><title>Home</title>"
        "<link rel=\"stylesheet\" href=\"css/tokens.css\"></head>"
        "<body><header><p>Brand</p></header><main><section>"
        "<h1>Headline</h1><p>Body copy from the source.</p>"
        "</section></main></body></html>\n",
        encoding="utf-8",
    )
    (root / RECEIPT).write_text(
        "# 2.2 frontend-design\n\nAuthored rebuild/index-semantic.html from Paper frames "
        "and the 2.1 Design System tokens. No new identity. No invented copy.\n",
        encoding="utf-8",
    )
    (root / RAW).write_text(
        "<!doctype html>"
        '<html lang="en" data-export="get_jsx-inline-styles">'
        "<head><title>Paper dump</title>"
        '<link rel="stylesheet" href="css/tokens.css"></head>'
        '<body><div data-paper-section="hero">raw paper dump</div>'
        "</body></html>\n",
        encoding="utf-8",
    )


def write_receipt(root: Path, errors: list[str]) -> Path:
    dest = root / QA
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": not errors,
                "errors": errors,
                "updated": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    errors = gate_errors(root)
    write_receipt(root, errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print("author-21: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
