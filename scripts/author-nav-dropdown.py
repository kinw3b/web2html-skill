#!/usr/bin/env python3
"""3.2 — author nav dropdown panels on rebuild/index.html.

If the polish file paints a dropdown trigger, or a nav label whose scrape
submenu exists, wire hover/click. Do not wait for Capture Tool or
--allow-dropdown. Do not invent a nav label.

  python3 author-nav-dropdown.py .
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from html import unescape
from pathlib import Path

WRITER = "author-nav-dropdown.py"
CSS_HREF = "css/nav-dropdown.css"
JS_SRC = "js/nav-dropdown.js"
HERE = Path(__file__).resolve().parent
JS_TEMPLATE = HERE.parent / "templates" / "nav-dropdown.js"
BANNED_SKIP = re.compile(
    r"capture tool|allow-dropdown|do not hunt|no dropdown capture",
    re.I,
)
DROPDOWN_CLASS = re.compile(
    r"\b(dropdown|has-submenu|nav-dropdown|menu-item-has-children|submenu)\b",
    re.I,
)
CHEVRON = re.compile(r"chevron|caret|arrow-down", re.I)
LOGO_HINT = re.compile(r"\b(logo|brand|wordmark|site-logo)\b", re.I)
LABEL_PREFIX = re.compile(r"^(nav|menu|link)\s*[-–—:]\s*", re.I)
# Framer / Webflow builders paint no <header>/<nav>/<ul>: the menu panel is a
# named layer (data-framer-name="Mega Menu") after a href-less trigger
# ("All Pages"). Pitfall #248 — without this the scrape found ZERO submenus,
# the 3.2 panel stayed empty, and the stage-5 audit had nothing to check.
PANEL_NAME = re.compile(r"mega\s*-?\s*menu|drop\s*-?\s*down|sub\s*-?\s*menu|menu\s*panel", re.I)
BUILDER_NAME_ATTRS = ("data-framer-name", "data-w-id-name", "data-name")

DROPDOWN_CSS = """/* 3.2 nav dropdown — authored when a trigger or scrape submenu exists. Pitfall #210 */
[data-nav-dropdown] {
  position: relative;
}
[data-nav-dropdown-panel] {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 40;
  min-width: 12rem;
}
[data-nav-dropdown-panel].is-open,
[data-nav-dropdown-panel][aria-hidden="false"] {
  display: flex;
  flex-direction: column;
}
@media (max-width: 768px) {
  [data-nav-dropdown-panel] {
    display: none !important;
  }
}
"""


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def key(text: str) -> str:
    cleaned = LABEL_PREFIX.sub("", unescape(text or ""))
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned.casefold())
    return cleaned


def text_of(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True) if el is not None else "").strip()


def soup_of(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def dumps(soup, original: str) -> str:
    out = str(soup)
    if re.match(r"(?is)\s*<!doctype", original) and not re.match(r"(?is)\s*<!doctype", out):
        return "<!DOCTYPE html>\n" + out
    return out


def nav_scope(soup):
    return (
        soup.find("header")
        or soup.find("nav")
        or soup.find(attrs={"role": "navigation"})
        or soup.find(id=re.compile(r"nav", re.I))
    )


def is_logo(el) -> bool:
    blob = f"{' '.join(el.get('class') or [])} {el.get('aria-label') or ''} {text_of(el)}"
    return bool(LOGO_HINT.search(blob))


def ship_href(href: str) -> str:
    value = (href or "#").strip()
    if not value or re.match(r"^(https?:|mailto:|tel:|/)", value, re.I):
        return "#"
    return value


def is_submenu_container(el, trigger) -> bool:
    if el is None or el.name in {"script", "style"}:
        return False
    if el.find_parent(id="nav-panel") or el.get("id") == "nav-panel":
        return False
    classes = " ".join(el.get("class") or [])
    links = [a for a in el.find_all("a") if text_of(a) and a is not trigger]
    if DROPDOWN_CLASS.search(classes) or el.name == "ul":
        return len(links) >= 2
    if el.get("data-nav-dropdown-panel") is not None:
        return len(links) >= 1
    return el.name in {"div", "nav"} and len(links) >= 2


def _panel_named(el) -> bool:
    return any(PANEL_NAME.search(str(el.get(attr) or "")) for attr in BUILDER_NAME_ATTRS)


def builder_dropdowns(soup) -> list[dict]:
    """Named builder panels (Framer `Mega Menu`, …) + the nearest href-less
    trigger before them. Items are the panel's labelled links, in order."""
    panels = [
        el for el in soup.find_all(_panel_named)
        if not el.find_parent(_panel_named) and not el.find_parent("footer")
    ]
    out: list[dict] = []
    for panel in panels:
        trigger = None
        for el in panel.find_all_previous(["a", "button"]):
            if el.get("href") or el.find_parent(_panel_named) or is_logo(el):
                continue
            label = text_of(el)
            if label and len(label) <= 40:
                trigger = el
                break
        if trigger is None:
            continue
        items = [
            {"href": a.get("href") or "#", "label": text_of(a)}
            for a in panel.find_all("a")
            if text_of(a) and len(text_of(a)) <= 60
        ]
        out.append({"label": text_of(trigger), "items": items})
    return out


def scrape_dropdowns(html: str) -> list[dict]:
    if not html:
        return []
    soup = soup_of(html)
    scope = nav_scope(soup)
    if scope is None:
        menus: list[dict] = []
        seen_b: set[str] = set()
        for row in builder_dropdowns(soup):
            qk = key(row["label"])
            clean, dupe = [], set()
            for item in row["items"]:
                ik = key(item["label"])
                if not ik or ik == qk or ik in dupe:
                    continue
                dupe.add(ik)
                clean.append({"href": ship_href(item["href"]), "label": item["label"]})
            if qk and qk not in seen_b and len(clean) >= 2:
                seen_b.add(qk)
                menus.append({"label": row["label"], "key": qk, "items": clean})
        return menus
    seen: set[str] = set()
    menus: list[dict] = []

    def add(label: str, items: list[dict]) -> None:
        qk = key(label)
        clean = [
            {"href": ship_href(item.get("href") or "#"), "label": item["label"]}
            for item in items
            if item.get("label") and key(item["label"]) != qk
        ]
        if not qk or qk in seen or len(clean) < 2:
            return
        seen.add(qk)
        menus.append({"label": label, "key": qk, "items": clean})

    for li in scope.find_all("li"):
        trigger = li.find(["a", "button"], recursive=False) or li.find(["a", "button"])
        nested = li.find("ul")
        if trigger is None or nested is None:
            continue
        links = [a for a in nested.find_all("a") if text_of(a)]
        add(text_of(trigger), [{"href": a.get("href") or "#", "label": text_of(a)} for a in links])

    for trigger in scope.find_all(["a", "button"]):
        if trigger.find_parent(id="nav-panel") or is_logo(trigger):
            continue
        label = text_of(trigger)
        if not label:
            continue
        panel = None
        if trigger.parent and trigger.parent.name == "li":
            panel = trigger.parent.find("ul")
        sib = trigger.find_next_sibling()
        if panel is None and is_submenu_container(sib, trigger):
            panel = sib
        if panel is None and (
            trigger.get("aria-haspopup")
            or DROPDOWN_CLASS.search(" ".join(trigger.get("class") or []))
        ):
            host = trigger.find_parent(attrs={"data-nav-dropdown": True}) or trigger.parent
            if host is not None and host.name not in {"header", "nav", "body"}:
                panel = host.find(attrs={"data-nav-dropdown-panel": True}) or host.find("ul")
        if panel is None:
            continue
        links = [a for a in panel.find_all("a") if text_of(a) and a is not trigger]
        add(label, [{"href": a.get("href") or "#", "label": text_of(a)} for a in links])
    return menus


def painted_triggers(soup) -> list:
    from bs4 import Tag

    scope = nav_scope(soup)
    if scope is None:
        return []
    found = []
    for el in scope.find_all(["a", "button"]):
        if not isinstance(el, Tag) or is_logo(el) or el.find_parent(id="nav-panel"):
            continue
        opening = f"{' '.join(el.get('class') or [])} {el.get('aria-label') or ''}"
        svg = el.find("svg")
        svg_blob = " ".join(svg.get("class") or []) if svg is not None else ""
        if (
            el.get("data-nav-dropdown-trigger") is not None
            or el.get("aria-haspopup")
            or DROPDOWN_CLASS.search(opening)
            or CHEVRON.search(opening + " " + svg_blob)
        ):
            found.append(el)
            continue
        parent = el.parent
        if isinstance(parent, Tag) and parent.name == "li" and parent.find("ul"):
            found.append(el)
    return found


def find_trigger(scope, label: str):
    want = key(label)
    if not want or scope is None:
        return None
    for el in scope.find_all(["a", "button"]):
        if el.find_parent(id="nav-panel") or is_logo(el):
            continue
        if key(text_of(el)) == want:
            return el
    return None


def stamp_dropdown(trigger, items: list[dict], soup, index: int) -> dict:
    from bs4 import NavigableString, Tag

    info = {"wired": False, "label": text_of(trigger), "filled": False}
    trigger["data-nav-dropdown-trigger"] = trigger.get("data-nav-dropdown-trigger") or ""
    trigger["aria-haspopup"] = "true"
    trigger["aria-expanded"] = trigger.get("aria-expanded") or "false"
    parent = trigger.parent
    if isinstance(parent, Tag) and parent.name in {"li", "div", "span"}:
        parent["data-nav-dropdown"] = parent.get("data-nav-dropdown") or ""
    panel = None
    nxt = trigger.find_next_sibling()
    if isinstance(nxt, Tag) and (
        nxt.get("data-nav-dropdown-panel") is not None or nxt.name == "ul"
    ):
        panel = nxt
    if panel is None and isinstance(parent, Tag):
        panel = parent.find(attrs={"data-nav-dropdown-panel": True}) or parent.find("ul")
        if panel is not None and panel.find_parent(id="nav-panel"):
            panel = None
    if panel is None:
        panel = soup.new_tag("div")
        panel["data-nav-dropdown-panel"] = ""
        trigger.insert_after(panel)
    panel["data-nav-dropdown-panel"] = panel.get("data-nav-dropdown-panel") or ""
    if not panel.get("id"):
        panel["id"] = f"nav-dropdown-{index}"
    panel["aria-hidden"] = panel.get("aria-hidden") or "true"
    trigger["aria-controls"] = panel["id"]
    existing = [a for a in panel.find_all("a") if text_of(a)]
    if not existing and items:
        for item in items:
            a = soup.new_tag("a")
            a["href"] = ship_href(item.get("href") or "#")
            a.append(NavigableString(item["label"]))
            panel.append(a)
        info["filled"] = True
    info["wired"] = True
    return info


def ensure_link(html: str, href: str, *, css: bool) -> str:
    if href in html:
        return html
    if css:
        tag = f'<link rel="stylesheet" href="{href}" />'
        for needle in (
            'href="css/nav-drawer.css" />',
            'href="css/faq.css" />',
            'href="css/hover.css" />',
            'href="css/tokens.css" />',
            "</head>",
        ):
            if needle in html:
                if needle == "</head>":
                    return html.replace("</head>", f"  {tag}\n</head>", 1)
                return html.replace(needle, f"{needle}\n  {tag}", 1)
        return tag + "\n" + html
    tag = f'<script src="{href}"></script>'
    for needle in ('<script src="js/faq.js"></script>', '<script src="js/nav-drawer.js"></script>', '<script src="js/gsap-reveal.js"></script>'):
        if needle in html:
            return html.replace(needle, f"{tag}\n{needle}", 1)
    if "</body>" in html:
        return html.replace("</body>", f"{tag}\n</body>", 1)
    return html + "\n" + tag + "\n"


def dropdown_receipt_ok(payload: dict) -> bool:
    if payload.get("ok") is not True or payload.get("writer") != WRITER:
        return False
    if not isinstance(payload.get("applied"), list) or not isinstance(payload.get("skipped"), list):
        return False
    painted = payload.get("painted") is True
    for row in payload.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if painted and BANNED_SKIP.search(reason) and "dropdown" in finding.casefold():
            return False
        if BANNED_SKIP.search(reason) and "dropdown" in finding.casefold():
            return False
    return True


def author_nav_dropdown(root: Path) -> dict:
    root = root.resolve()
    polish = root / "rebuild" / "index.html"
    if not polish.is_file():
        raise FileNotFoundError("need rebuild/index.html — 2.2 authors it; 3.x polishes it in place")

    html = polish.read_text(encoding="utf-8")
    scrape = ""
    scrape_path = root / "source-site" / "index.html"
    if scrape_path.is_file():
        scrape = scrape_path.read_text(encoding="utf-8", errors="replace")
    menus = scrape_dropdowns(scrape)
    by_key = {row["key"]: row for row in menus}
    soup = soup_of(html)
    scope = nav_scope(soup)
    applied: list[dict] = []
    skipped: list[dict] = []
    files: list[str] = []
    jobs: list[tuple] = []

    seen_ids = set()
    for trigger in painted_triggers(soup):
        ident = id(trigger)
        if ident in seen_ids:
            continue
        seen_ids.add(ident)
        label = text_of(trigger)
        items = (by_key.get(key(label)) or {}).get("items") or []
        jobs.append((trigger, items, label))

    if scope is not None:
        for menu in menus:
            trigger = find_trigger(scope, menu["label"])
            if trigger is None or id(trigger) in seen_ids:
                continue
            seen_ids.add(id(trigger))
            jobs.append((trigger, menu["items"], menu["label"]))

    painted = bool(jobs)
    if not painted:
        skipped.append({
            "finding": "nav dropdown",
            "reason": "No painted dropdown trigger and no scrape submenu matching a polish nav label. Do not invent a menu.",
        })
        receipt = {
            "ok": True,
            "writer": WRITER,
            "painted": False,
            "applied": applied,
            "skipped": skipped,
            "files": files,
            "captureTool": False,
        }
        dest = root / "qa" / "nav-dropdown.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt

    for index, (trigger, items, label) in enumerate(jobs):
        info = stamp_dropdown(trigger, items, soup, index)
        if info["wired"]:
            applied.append({
                "finding": "nav dropdown",
                "label": label,
                "fix": "wired panel" + (" + scrape items" if info["filled"] else ""),
                "file": "rebuild/index.html",
                "change": "data-nav-dropdown-trigger",
                "why": "Painted or scrape-matched nav dropdowns open on hover/click. Capture Tool is not required (Pitfall #210).",
            })
        if info["wired"] and not items and not trigger.find_next_sibling():
            skipped.append({
                "finding": "nav dropdown items",
                "label": label,
                "reason": "no matching source-site submenu; trigger still wired if a panel already existed",
            })

    html_out = dumps(soup, html)
    css_dir = root / "rebuild" / "css"
    js_dir = root / "rebuild" / "js"
    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    (css_dir / "nav-dropdown.css").write_text(DROPDOWN_CSS, encoding="utf-8")
    files.append("rebuild/css/nav-dropdown.css")
    shutil.copyfile(JS_TEMPLATE, js_dir / "nav-dropdown.js")
    files.append("rebuild/js/nav-dropdown.js")
    linked = ensure_link(html_out, CSS_HREF, css=True)
    linked = ensure_link(linked, JS_SRC, css=False)
    if linked != html:
        polish.write_text(linked, encoding="utf-8")
        files.append("rebuild/index.html")

    receipt = {
        "ok": True,
        "writer": WRITER,
        "painted": True,
        "applied": applied,
        "skipped": skipped,
        "files": files,
        "captureTool": False,
    }
    dest = root / "qa" / "nav-dropdown.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


ASTRO_LITERAL = re.compile(r"(const html = `)(.*?)(`;\s*\n---)", re.S)


def _astro_unescape(value: str) -> str:
    return re.sub(r"\\(\\|`|\$\{)", lambda m: m.group(1), value)


def _astro_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def author_astro_header(root: Path) -> dict:
    """Phase 5 (5.4+ fix lane, Pitfall #247/#248): wire + FILL the dropdown
    panels in astro/src/components/Header.astro from the source scrape, and
    make sure BaseLayout loads nav-dropdown.css/js. Never touches rebuild/."""
    root = root.resolve()
    header = root / "astro" / "src" / "components" / "Header.astro"
    if not header.is_file():
        raise FileNotFoundError("need astro/src/components/Header.astro from 5.1")
    text = header.read_text(encoding="utf-8")
    match = ASTRO_LITERAL.search(text)
    if not match:
        raise FileNotFoundError("Header.astro is not a 5.1 fragment component (const html = `…`)")
    html = _astro_unescape(match.group(2))
    scrape_path = root / "source-site" / "index.html"
    scrape = scrape_path.read_text(encoding="utf-8", errors="replace") if scrape_path.is_file() else ""
    menus = scrape_dropdowns(scrape)
    by_key = {row["key"]: row for row in menus}
    soup = soup_of(html)
    scope = nav_scope(soup) or soup
    jobs, seen = [], set()
    for trigger in painted_triggers(soup):
        if id(trigger) not in seen:
            seen.add(id(trigger))
            jobs.append((trigger, (by_key.get(key(text_of(trigger))) or {}).get("items") or [], text_of(trigger)))
    for menu in menus:
        trigger = find_trigger(scope, menu["label"])
        if trigger is not None and id(trigger) not in seen:
            seen.add(id(trigger))
            jobs.append((trigger, menu["items"], menu["label"]))
    applied, unfilled = [], []
    for index, (trigger, items, label) in enumerate(jobs):
        info = stamp_dropdown(trigger, items, soup, index)
        panel_id = trigger.get("aria-controls")
        panel = soup.find(id=panel_id) if panel_id else None
        count = len([a for a in panel.find_all("a") if text_of(a)]) if panel is not None else 0
        applied.append({"label": label, "filled": info["filled"], "items": count})
        if count == 0:
            unfilled.append(label)
    new_html = str(soup)
    if new_html != html:
        header.write_text(text[: match.start(2)] + _astro_escape(new_html) + text[match.end(2):], encoding="utf-8")
    public = root / "astro" / "public"
    (public / "styles").mkdir(parents=True, exist_ok=True)
    (public / "scripts").mkdir(parents=True, exist_ok=True)
    if not (public / "styles" / "nav-dropdown.css").is_file():
        (public / "styles" / "nav-dropdown.css").write_text(DROPDOWN_CSS, encoding="utf-8")
    if not (public / "scripts" / "nav-dropdown.js").is_file():
        shutil.copyfile(JS_TEMPLATE, public / "scripts" / "nav-dropdown.js")
    layout = root / "astro" / "src" / "layouts" / "BaseLayout.astro"
    if layout.is_file() and jobs:
        lt = layout.read_text(encoding="utf-8")
        if "/styles/nav-dropdown.css" not in lt:
            lt = lt.replace("  </head>", '    <link rel="stylesheet" href="/styles/nav-dropdown.css" />\n  </head>', 1)
        if "/scripts/nav-dropdown.js" not in lt:
            lt = lt.replace("  </body>", '    <script is:inline src="/scripts/nav-dropdown.js"></script>\n  </body>', 1)
        layout.write_text(lt, encoding="utf-8")
    receipt = {
        "ok": not unfilled,
        "writer": WRITER,
        "mode": "astro",
        "painted": bool(jobs),
        "applied": applied,
        "unfilled": unfilled,
        "scrapeMenus": [{"label": m["label"], "items": len(m["items"])} for m in menus],
        "files": ["astro/src/components/Header.astro"],
    }
    dest = root / "qa" / "phase-5-nav-dropdown.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    ap.add_argument("--astro", action="store_true",
                    help="phase 5: wire + fill dropdown panels in astro/src/components/Header.astro")
    args = ap.parse_args(argv)
    if args.astro:
        try:
            receipt = author_astro_header(args.root)
        except FileNotFoundError as exc:
            fail(str(exc))
            return 2
        print(json.dumps(receipt, indent=2))
        if not receipt["ok"]:
            fail(f"dropdown panel(s) still empty: {receipt['unfilled']} — no source items matched")
            return 2
        return 0
    try:
        receipt = author_nav_dropdown(args.root)
    except FileNotFoundError as exc:
        fail(str(exc))
        return 2
    print(json.dumps(receipt, indent=2))
    if not dropdown_receipt_ok(receipt):
        fail("qa/nav-dropdown.json is not a valid 3.2 dropdown receipt")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
