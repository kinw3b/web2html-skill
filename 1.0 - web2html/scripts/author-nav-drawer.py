#!/usr/bin/env python3
"""3.2 — author a burger open drawer on rebuild/index-polish.html.

If the polish file paints a hamburger, open = the same desktop links stacked.
Do not wait for Capture Tool. Do not invent a burger that was never painted.

  python3 author-nav-drawer.py .

Writes rebuild/css/nav-drawer.css + rebuild/js/nav-drawer.js, links both
from index-polish.html, and records qa/nav-drawer.json.
Does not mutate rebuild/index.html.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from html import unescape
from pathlib import Path

WRITER = "author-nav-drawer.py"
CSS_HREF = "css/nav-drawer.css"
JS_SRC = "js/nav-drawer.js"
PANEL_ID = "nav-panel"
HERE = Path(__file__).resolve().parent
JS_TEMPLATE = HERE.parent / "templates" / "nav-drawer.js"

TOGGLE_CLASS = re.compile(
    r"\b(burger|hamburger|nav-toggle|menu-toggle|nav-burger)\b", re.I
)
TOGGLE_LABEL = re.compile(
    r"\b(open menu|menu|toggle menu|open navigation|toggle navigation)\b", re.I
)
LOGO_HINT = re.compile(r"\b(logo|brand|wordmark|site-logo)\b", re.I)
BUTTON_RE = re.compile(r"<button\b[^>]*>.*?</button>", re.I | re.S)
LINK_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
HEADER_RE = re.compile(r"<header\b[^>]*>.*?</header>", re.I | re.S)
PANEL_RE = re.compile(
    r"<(nav|div)\b([^>]*(?:id=[\"']nav-panel[\"']|data-nav-panel)[^>]*)>(.*?)</\1>",
    re.I | re.S,
)
BANNED_SKIP = re.compile(
    r"capture tool open-nav|inventing a sheet|new chrome", re.I
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def text_of(inner: str) -> str:
    stripped = re.sub(r"<script[\s\S]*?</script>", " ", inner, flags=re.I)
    stripped = re.sub(r"<style[\s\S]*?</style>", " ", stripped, flags=re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return re.sub(r"\s+", " ", unescape(stripped)).strip()


def attr(attrs: str, name: str) -> str:
    match = re.search(rf"""\b{name}\s*=\s*(['"])(.*?)\1""", attrs or "", re.I)
    return match.group(2) if match else ""


def opening_of(tag: str) -> str:
    end = tag.find(">")
    return tag if end < 0 else tag[: end + 1]


def header_slice(html: str) -> tuple[str, int] | None:
    match = HEADER_RE.search(html)
    if match:
        return match.group(0), match.start()
    return None


def strip_existing_panel(chunk: str) -> str:
    return PANEL_RE.sub("", chunk)


def is_logo(attrs: str, inner: str) -> bool:
    return bool(LOGO_HINT.search(f"{attrs} {inner}"))


def looks_like_toggle(tag: str) -> bool:
    opening = opening_of(tag)
    if "data-nav-toggle" in opening:
        return True
    if TOGGLE_CLASS.search(attr(opening, "class")):
        return True
    if TOGGLE_LABEL.search(attr(opening, "aria-label")):
        return True
    spans = len(re.findall(r"<span\b", tag, flags=re.I))
    return spans >= 2 and not text_of(tag)


def toggle_span(html: str) -> tuple[int, int, str] | None:
    scoped = header_slice(html)
    search_in = scoped[0] if scoped else html
    offset = scoped[1] if scoped else 0
    ranked: list[tuple[int, re.Match[str]]] = []
    for match in BUTTON_RE.finditer(search_in):
        if not looks_like_toggle(match.group(0)):
            continue
        opening = opening_of(match.group(0))
        rank = 3 if "data-nav-toggle" in opening else 2 if TOGGLE_CLASS.search(
            attr(opening, "class")
        ) else 1
        ranked.append((rank, match))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], item[1].start()))
    best = ranked[0][1]
    return offset + best.start(), offset + best.end(), best.group(0)


def painted_hamburger(html: str) -> bool:
    return toggle_span(html) is not None


def header_links(html: str) -> list[dict[str, str]]:
    scoped = header_slice(html)
    chunk = strip_existing_panel(scoped[0] if scoped else html)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in LINK_RE.finditer(chunk):
        attrs, inner = match.group(1), match.group(2)
        if is_logo(attrs, inner):
            continue
        label = text_of(inner)
        if not label:
            continue
        href = attr(attrs, "href") or "#"
        key = f"{label.casefold()}|{href.casefold()}"
        if key in seen:
            continue
        seen.add(key)
        cls = attr(attrs, "class")
        rows.append({"label": label, "href": href, "className": cls})
    return rows


def find_panel(html: str) -> re.Match[str] | None:
    scoped = header_slice(html)
    search_in = scoped[0] if scoped else html
    match = PANEL_RE.search(search_in)
    if match is None:
        return PANEL_RE.search(html)
    return match


def burger_max_width(css: str) -> int:
    found: list[int] = []
    for match in re.finditer(r"@media\s*\(([^)]+)\)\s*\{", css or "", re.I):
        query = match.group(1)
        chunk = (css or "")[match.end() : match.end() + 5000]
        shows = re.search(
            r"\.(burger|nav-toggle|hamburger|menu-toggle)[^{]*\{[^}]*display\s*:\s*(flex|block)",
            chunk,
            re.I | re.S,
        )
        hides = re.search(
            r"\.(burger|nav-toggle|hamburger|menu-toggle)[^{]*\{[^}]*display\s*:\s*none",
            chunk,
            re.I | re.S,
        )
        max_m = re.search(r"max-width\s*:\s*(\d+)px", query, re.I)
        min_m = re.search(r"min-width\s*:\s*(\d+)px", query, re.I)
        if max_m and shows:
            found.append(int(max_m.group(1)))
        if min_m and hides:
            found.append(max(int(min_m.group(1)) - 1, 1))
    return max(found) if found else 768


def stamp_toggle(tag: str) -> str:
    end = tag.find(">")
    if end < 0:
        return tag
    opening, rest = tag[:end], tag[end:]
    if "data-nav-toggle" not in opening:
        opening = re.sub(r"<button\b", '<button data-nav-toggle=""', opening, count=1, flags=re.I)
    if "type=" not in opening:
        opening += ' type="button"'
    if "aria-controls=" in opening:
        opening = re.sub(
            r"""aria-controls\s*=\s*(['"]).*?\1""",
            f'aria-controls="{PANEL_ID}"',
            opening,
            count=1,
            flags=re.I,
        )
    else:
        opening += f' aria-controls="{PANEL_ID}"'
    if "aria-expanded=" not in opening:
        opening += ' aria-expanded="false"'
    if "aria-label=" not in opening:
        opening += ' aria-label="Open menu"'
    return opening + rest


def stamp_panel_open(opening: str) -> str:
    if "data-nav-panel" not in opening:
        opening = re.sub(
            r"<(nav|div)\b",
            r'<\1 data-nav-panel=""',
            opening,
            count=1,
            flags=re.I,
        )
    if re.search(r"""\bid\s*=""", opening, re.I) is None:
        opening = re.sub(
            r"<(nav|div)\b",
            rf'<\1 id="{PANEL_ID}"',
            opening,
            count=1,
            flags=re.I,
        )
    if "aria-hidden=" not in opening:
        opening += ' aria-hidden="true"'
    if "aria-label=" not in opening:
        opening += ' aria-label="Menu"'
    if "class=" in opening:
        if not re.search(r"\bnav-panel\b", attr(opening, "class")):
            opening = re.sub(
                r"""(\bclass\s*=\s*(['"]))""",
                r"\1nav-panel ",
                opening,
                count=1,
                flags=re.I,
            )
    else:
        opening += ' class="nav-panel"'
    if not opening.endswith(">"):
        opening += ">"
    return opening


def panel_html(links: list[dict[str, str]]) -> str:
    items = []
    for row in links:
        cls = f' class="{row["className"]}"' if row.get("className") else ""
        items.append(f'<a href="{row["href"]}"{cls}>{row["label"]}</a>')
    inner = "\n".join(items)
    return (
        f'<nav id="{PANEL_ID}" class="nav-panel" data-nav-panel="" '
        f'aria-label="Menu" aria-hidden="true">\n{inner}\n</nav>'
    )


def drawer_css(max_width: int) -> str:
    desktop = max_width + 1
    return f"""/* 3.2 authored burger drawer — same desktop links stacked. Not Capture Tool. */

@media (min-width: {desktop}px) {{
  [data-nav-panel] {{
    display: none !important;
  }}
}}

@media (max-width: {max_width}px) {{
  [data-nav-panel] {{
    position: fixed;
    left: 0;
    right: 0;
    top: var(--nav-drawer-top, 72px);
    z-index: 80;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-5, 20px);
    padding: var(--spacing-6, 24px) var(--spacing-8, 32px);
    background: var(--color-surface, #fff);
    color: var(--color-ink, inherit);
    box-shadow: var(--shadow-md, 0 16px 40px rgb(0 0 0 / 0.12));
    transform: translateY(-8px);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition:
      transform 280ms cubic-bezier(0.32, 0.72, 0, 1),
      opacity 280ms cubic-bezier(0.32, 0.72, 0, 1),
      visibility 280ms;
  }}

  .is-nav-open [data-nav-panel],
  body.nav-open [data-nav-panel] {{
    transform: none;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
  }}

  html.is-nav-open,
  html.is-nav-open body {{
    overflow: hidden;
  }}
}}

@media (prefers-reduced-motion: reduce) {{
  [data-nav-panel] {{
    transition: none;
  }}
}}
"""


def ensure_css_link(html: str) -> str:
    if CSS_HREF in html:
        return html
    tag = f'<link rel="stylesheet" href="{CSS_HREF}" />'
    for needle in (
        'href="css/hover.css" />',
        'href="css/hover.css"/>',
        'href="css/site.css" />',
        'href="css/site.css"/>',
        'href="css/tokens.css" />',
        'href="css/tokens.css"/>',
    ):
        if needle in html:
            return html.replace(needle, f"{needle}\n  {tag}", 1)
    if "</head>" in html:
        return html.replace("</head>", f"  {tag}\n</head>", 1)
    return tag + "\n" + html


def existing_nav_script(html: str) -> bool:
    if JS_SRC in html:
        return True
    for match in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.I | re.S):
        attrs, body = match.group(1), match.group(2)
        src = attr(attrs, "src")
        if src:
            if "nav-drawer.js" in src:
                return True
            continue
        if re.search(r"nav-open|is-nav-open|nav-panel|data-nav-toggle", body, re.I):
            return True
    return False


def drawer_wired(html: str) -> bool:
    if not painted_hamburger(html) or PANEL_RE.search(html) is None:
        return False
    return JS_SRC in html or existing_nav_script(html)


def ensure_js_link(html: str) -> str:
    if JS_SRC in html:
        return html
    tag = f'<script src="{JS_SRC}"></script>'
    if "js/gsap-reveal.js" in html:
        return html.replace(
            '<script src="js/gsap-reveal.js"></script>',
            f"{tag}\n" + '<script src="js/gsap-reveal.js"></script>',
            1,
        )
    if "</body>" in html:
        return html.replace("</body>", f"{tag}\n</body>", 1)
    return html + "\n" + tag + "\n"


def fill_empty_panel(html: str, links: list[dict[str, str]]) -> str:
    match = PANEL_RE.search(html)
    if match is None:
        return html
    inner = match.group(3)
    if LINK_RE.search(inner):
        opening = stamp_panel_open(f"<{match.group(1)}{match.group(2)}>")
        return html[: match.start()] + f"{opening}{inner}</{match.group(1)}>" + html[match.end() :]
    panel = panel_html(links)
    return html[: match.start()] + panel + html[match.end() :]


def drawer_receipt_ok(payload: dict) -> bool:
    if payload.get("ok") is not True or payload.get("writer") != WRITER:
        return False
    if not isinstance(payload.get("applied"), list) or not isinstance(payload.get("skipped"), list):
        return False
    for row in payload.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if BANNED_SKIP.search(reason) and "burger" in finding.casefold():
            return False
    return True


def author_nav_drawer(root: Path) -> dict:
    root = root.resolve()
    polish = root / "rebuild" / "index-polish.html"
    if not polish.is_file():
        raise FileNotFoundError("need rebuild/index-polish.html — 3.1 seeds it")

    html = polish.read_text(encoding="utf-8")
    site_css = ""
    site_path = root / "rebuild" / "css" / "site.css"
    if site_path.is_file():
        site_css = site_path.read_text(encoding="utf-8")
    max_width = burger_max_width(site_css)
    files: list[str] = []
    applied: list[dict] = []
    skipped: list[dict] = []

    toggle = toggle_span(html)
    if toggle is None:
        skipped.append(
            {
                "finding": "burger open drawer",
                "reason": (
                    "No painted hamburger on index-polish.html. "
                    "Do not invent a burger (Pitfall #145)."
                ),
            }
        )
        receipt = {
            "ok": True,
            "writer": WRITER,
            "painted": False,
            "maxWidth": max_width,
            "applied": applied,
            "skipped": skipped,
            "files": files,
            "links": [],
            "captureTool": False,
        }
        dest = root / "qa" / "nav-drawer.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt

    links = header_links(html)
    if not links:
        skipped.append(
            {
                "finding": "burger open drawer",
                "reason": "Hamburger is painted but no desktop nav links to stack.",
            }
        )
        receipt = {
            "ok": False,
            "writer": WRITER,
            "painted": True,
            "maxWidth": max_width,
            "applied": applied,
            "skipped": skipped,
            "files": files,
            "links": [],
            "captureTool": False,
        }
        dest = root / "qa" / "nav-drawer.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt

    start, end, tag = toggle
    stamped = stamp_toggle(tag)
    html_out = html[:start] + stamped + html[end:]
    if stamped != tag:
        applied.append({
            "finding": "burger toggle",
            "fix": "stamped data-nav-toggle + aria-controls=nav-panel",
            "file": "rebuild/index-polish.html",
            "change": "data-nav-toggle",
            "why": "Painted hamburger is a click control (Pitfall #43).",
        })

    if find_panel(html_out):
        before = html_out
        html_out = fill_empty_panel(html_out, links)
        if html_out != before:
            applied.append(
                {
                    "finding": "burger open drawer",
                    "fix": "filled #nav-panel with the same desktop links stacked",
                    "file": "rebuild/index-polish.html",
                    "change": "#nav-panel",
                    "why": "Same desktop links stacked. Capture Tool not required.",
                }
            )
        elif not any(row.get("finding") == "burger open drawer" for row in applied):
            applied.append(
                {
                    "finding": "burger open drawer",
                    "fix": "kept existing #nav-panel; Capture Tool was not required",
                    "file": "rebuild/css/nav-drawer.css",
                    "change": "burger open drawer",
                    "why": "Existing panel kept. Capture Tool not required.",
                }
            )
    else:
        insert_at = start + len(stamped)
        html_out = html_out[:insert_at] + "\n" + panel_html(links) + html_out[insert_at:]
        applied.append(
            {
                "finding": "burger open drawer",
                "fix": "authored #nav-panel from desktop nav links (no Capture Tool pair)",
                "file": "rebuild/index-polish.html",
                "change": "#nav-panel",
                "why": "Same desktop links stacked. Capture Tool not required.",
            }
        )

    css_dir = root / "rebuild" / "css"
    js_dir = root / "rebuild" / "js"
    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    css_path = css_dir / "nav-drawer.css"
    css_path.write_text(drawer_css(max_width), encoding="utf-8")
    files.append("rebuild/css/nav-drawer.css")
    if JS_TEMPLATE.is_file():
        shutil.copyfile(JS_TEMPLATE, js_dir / "nav-drawer.js")
    else:
        raise FileNotFoundError(f"missing {JS_TEMPLATE}")
    files.append("rebuild/js/nav-drawer.js")

    html_out = ensure_css_link(html_out)
    if JS_SRC in html or not existing_nav_script(html):
        html_out = ensure_js_link(html_out)

    if html_out != html:
        polish.write_text(html_out, encoding="utf-8")
        files.append("rebuild/index-polish.html")

    receipt = {
        "ok": True,
        "writer": WRITER,
        "painted": True,
        "maxWidth": max_width,
        "applied": applied,
        "skipped": skipped,
        "files": files,
        "links": [row["label"] for row in links],
        "captureTool": False,
    }
    dest = root / "qa" / "nav-drawer.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    try:
        receipt = author_nav_drawer(args.root)
    except FileNotFoundError as exc:
        fail(str(exc))
        return 2
    print(json.dumps(receipt, indent=2))
    if not drawer_receipt_ok(receipt):
        fail("qa/nav-drawer.json is not a valid 3.2 burger-drawer receipt")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
