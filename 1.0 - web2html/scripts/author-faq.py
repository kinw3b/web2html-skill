#!/usr/bin/env python3
"""3.2 — author FAQ accordion on rebuild/index-polish.html.

If the polish file paints FAQ rows, wire open/close and fill empty answers
from source-site/index.html. Do not wait for Capture Tool. Do not invent copy.
Do not skip painted rows because Paper signed empty bodies.

  python3 author-faq.py .
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from html import unescape
from pathlib import Path

WRITER = "author-faq.py"
CSS_HREF = "css/faq.css"
JS_SRC = "js/faq.js"
HERE = Path(__file__).resolve().parent
JS_TEMPLATE = HERE.parent / "templates" / "faq.js"
BANNED_SKIP = re.compile(
    r"empty bodies|do not invent copy|capture tool|detect-only|no faq capture",
    re.I,
)
FAQ_HEAD = re.compile(
    r"\b(faqs?|frequently asked|common questions|questions & answers)\b", re.I
)
FAQ_ATTR = re.compile(r"faq|accordion", re.I)
QUESTION_MARK = re.compile(r"\?\s*$")
LABEL_PREFIX = re.compile(r"^(q\s*\d+|question)\s*[-–—:.)]\s*", re.I)

FAQ_CSS = """/* 3.2 FAQ accordion — authored when FAQ rows are painted. Pitfall #79 #209 */
[data-faq-item][data-open="false"] [data-faq-answer],
[data-faq-item]:not([data-open="true"]) [data-faq-answer][aria-hidden="true"] {
  display: none;
}
[data-faq-item][data-open="true"] [data-faq-answer] {
  display: block;
  width: 100%;
}
[data-action="toggle-faq"] {
  appearance: none;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-align: inherit;
  width: 100%;
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


def looks_like_question(text: str) -> bool:
    value = text.strip()
    if len(value) < 8 or len(value) > 180:
        return False
    if QUESTION_MARK.search(value):
        return True
    return bool(re.match(r"^(what|why|how|when|where|who|can|do|does|is|are)\b", value, re.I))


def soup_of(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def dumps(soup, original: str) -> str:
    out = str(soup)
    if re.match(r"(?is)\s*<!doctype", original) and not re.match(r"(?is)\s*<!doctype", out):
        return "<!DOCTYPE html>\n" + out
    return out


def scrape_faq_pairs(html: str) -> dict[str, str]:
    if not html:
        return {}
    soup = soup_of(html)
    pairs: dict[str, str] = {}

    def add(question: str, answer: str) -> None:
        qk = key(question)
        ans = re.sub(r"\s+", " ", answer).strip()
        if qk and ans and len(ans) > 8:
            pairs.setdefault(qk, ans)

    for node in soup.find_all("details"):
        summary = node.find("summary")
        add(text_of(summary), text_of(node)[len(text_of(summary)) :].strip())
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        add(text_of(dt), text_of(dd))
    for item in soup.select("[data-faq-item]"):
        btn = item.find(attrs={"data-action": "toggle-faq"}) or item.find(["button", "h3", "h4"])
        ans = item.find(attrs={"data-faq-answer": True})
        add(text_of(btn), text_of(ans))

    roots = []
    for tag in soup.find_all(["section", "article", "div"]):
        blob = f"{tag.get('id') or ''} {' '.join(tag.get('class') or [])} {tag.get('aria-label') or ''}"
        heading = tag.find(["h1", "h2", "h3"])
        if FAQ_ATTR.search(blob) or (heading and FAQ_HEAD.search(text_of(heading))):
            roots.append(tag)
    if not roots:
        for heading in soup.find_all(["h1", "h2", "h3"]):
            if FAQ_HEAD.search(text_of(heading)) and heading.parent:
                roots.append(heading.parent)

    for root in roots:
        candidates = root.find_all(["button", "h3", "h4", "p", "summary"])
        for el in candidates:
            question = text_of(el)
            if not looks_like_question(question):
                continue
            answer_el = el.find_next_sibling()
            hops = 0
            while answer_el is not None and hops < 4:
                ans = text_of(answer_el)
                if ans and key(ans) != key(question) and len(ans) > 12:
                    add(question, ans)
                    break
                answer_el = answer_el.find_next_sibling()
                hops += 1
    return pairs


def faq_roots(soup):
    from bs4 import Tag

    found = []
    for tag in soup.find_all(["section", "article", "div"]):
        if not isinstance(tag, Tag):
            continue
        blob = f"{tag.get('id') or ''} {' '.join(tag.get('class') or [])} {tag.get('aria-label') or ''} {tag.get('data-paper-name') or ''}"
        heading = tag.find(["h1", "h2", "h3"])
        if (
            FAQ_ATTR.search(blob)
            or tag.get("id") == "faq-section"
            or tag.get("data-faq-root") is not None
            or (heading and FAQ_HEAD.search(text_of(heading)))
            or tag.select_one("[data-faq-item], [data-action='toggle-faq']")
        ):
            found.append(tag)
    found.sort(key=lambda tag: len(list(tag.parents)))
    uniq = []
    for root in found:
        if any(parent in uniq for parent in root.parents):
            continue
        uniq.append(root)
    return uniq


def faq_items(root) -> list:
    from bs4 import Tag

    items = [el for el in root.select("[data-faq-item]") if isinstance(el, Tag)]
    if len(items) >= 2:
        return items
    details = [el for el in root.find_all("details") if isinstance(el, Tag)]
    if len(details) >= 2:
        return details
    rows = []
    for el in root.find_all(["button", "h3", "h4", "article", "div"]):
        if not isinstance(el, Tag) or el is root:
            continue
        if el.find_parent(attrs={"data-faq-item": True}):
            continue
        question = text_of(el.find(["button", "h3", "h4", "p"]) or el)
        if not looks_like_question(question) and el.get("data-action") != "toggle-faq":
            continue
        card = el
        if el.name in {"button", "h3", "h4", "p"}:
            parent = el.parent
            if isinstance(parent, Tag) and parent is not root:
                card = parent
        if card not in rows:
            rows.append(card)
    return rows


def ensure_item_structure(item, soup, index: int, answers: dict[str, str]) -> dict:
    from bs4 import NavigableString, Tag

    info = {"wired": False, "filled": False, "question": "", "answer": ""}
    item["data-faq-item"] = item.get("data-faq-item") or ""
    if item.get("role") == "button":
        del item["role"]
    if item.has_attr("tabindex"):
        del item["tabindex"]

    btn = item.find(attrs={"data-action": "toggle-faq"})
    if btn is None:
        btn = item.find("button")
    if btn is None:
        heading = item.find(["h3", "h4", "p"])
        btn = soup.new_tag("button")
        btn["type"] = "button"
        if heading is not None:
            question = text_of(heading)
            heading.clear()
            heading.append(btn)
            span = soup.new_tag("span")
            span.string = question
            btn.append(span)
        else:
            question = text_of(item)
            span = soup.new_tag("span")
            span.string = question
            btn.append(span)
            item.insert(0, btn)
    btn["type"] = "button"
    btn["data-action"] = "toggle-faq"
    if not btn.get("id"):
        btn["id"] = f"faq-q-{index}"
    question = text_of(btn)
    info["question"] = question

    ans = item.find(attrs={"data-faq-answer": True})
    if ans is None:
        ans = soup.new_tag("div")
        ans["data-faq-answer"] = ""
        p = soup.new_tag("p")
        ans.append(p)
        item.append(ans)
    if not ans.get("id"):
        ans["id"] = f"faq-a-{index}"
    ans["data-faq-answer"] = ans.get("data-faq-answer") or ""
    current = text_of(ans)
    scraped = answers.get(key(question), "")
    if not current and scraped:
        p = ans.find("p")
        if p is None:
            p = soup.new_tag("p")
            ans.append(p)
        p.clear()
        p.append(NavigableString(scraped))
        info["filled"] = True
        current = scraped
    info["answer"] = current
    btn["aria-controls"] = ans["id"]
    if not item.has_attr("data-open"):
        item["data-open"] = "false"
    btn["aria-expanded"] = "true" if item.get("data-open") == "true" else "false"
    ans["aria-hidden"] = "false" if item.get("data-open") == "true" else "true"
    info["wired"] = True
    return info


def ensure_link(html: str, href: str, *, css: bool) -> str:
    if href in html:
        return html
    if css:
        tag = f'<link rel="stylesheet" href="{href}" />'
        for needle in ('href="css/tokens.css" />', 'href="css/hover.css" />', "</head>"):
            if needle in html:
                if needle == "</head>":
                    return html.replace("</head>", f"  {tag}\n</head>", 1)
                return html.replace(needle, f"{needle}\n  {tag}", 1)
        return tag + "\n" + html
    tag = f'<script src="{href}"></script>'
    if "js/gsap-reveal.js" in html:
        return html.replace(
            '<script src="js/gsap-reveal.js"></script>',
            f"{tag}\n" + '<script src="js/gsap-reveal.js"></script>',
            1,
        )
    if "</body>" in html:
        return html.replace("</body>", f"{tag}\n</body>", 1)
    return html + "\n" + tag + "\n"


def faq_receipt_ok(payload: dict) -> bool:
    if payload.get("ok") is not True or payload.get("writer") != WRITER:
        return False
    if not isinstance(payload.get("applied"), list) or not isinstance(payload.get("skipped"), list):
        return False
    painted = payload.get("painted") is True
    for row in payload.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if painted and BANNED_SKIP.search(reason) and "faq" in finding.casefold():
            return False
    return True


def author_faq(root: Path) -> dict:
    root = root.resolve()
    polish = root / "rebuild" / "index-polish.html"
    if not polish.is_file():
        raise FileNotFoundError("need rebuild/index-polish.html — 3.1 seeds it")

    html = polish.read_text(encoding="utf-8")
    scrape = ""
    scrape_path = root / "source-site" / "index.html"
    if scrape_path.is_file():
        scrape = scrape_path.read_text(encoding="utf-8", errors="replace")
    answers = scrape_faq_pairs(scrape)
    soup = soup_of(html)
    roots = faq_roots(soup)
    files: list[str] = []
    applied: list[dict] = []
    skipped: list[dict] = []
    painted = False
    items_all = []
    for section in roots:
        section["data-faq-root"] = section.get("data-faq-root") or ""
        rows = faq_items(section)
        if len(rows) >= 2 or any(row.get("data-faq-item") is not None for row in rows):
            painted = True
            items_all.extend(rows)

    if not painted:
        skipped.append({
            "finding": "FAQ accordion",
            "reason": "No painted FAQ rows on index-polish.html. Do not invent a FAQ section.",
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
        dest = root / "qa" / "faq.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt

    for index, item in enumerate(items_all):
        info = ensure_item_structure(item, soup, index, answers)
        if info["wired"]:
            applied.append({
                "finding": "FAQ accordion",
                "label": info["question"],
                "fix": "wired toggle" + (" + scrape answer" if info["filled"] else ""),
                "file": "rebuild/index-polish.html",
                "change": "data-action=toggle-faq",
                "why": "Painted FAQ rows open on click. Scrape copy is not invented (Pitfall #209).",
            })
        if info["wired"] and not info["answer"]:
            skipped.append({
                "finding": "FAQ answer",
                "label": info["question"],
                "reason": "no matching source-site answer; toggle still wired",
            })

    html_out = dumps(soup, html)
    css_dir = root / "rebuild" / "css"
    js_dir = root / "rebuild" / "js"
    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    css_path = css_dir / "faq.css"
    css_path.write_text(FAQ_CSS, encoding="utf-8")
    files.append("rebuild/css/faq.css")
    js_path = js_dir / "faq.js"
    shutil.copyfile(JS_TEMPLATE, js_path)
    files.append("rebuild/js/faq.js")
    linked = ensure_link(html_out, CSS_HREF, css=True)
    linked = ensure_link(linked, JS_SRC, css=False)
    if linked != html:
        polish.write_text(linked, encoding="utf-8")
        files.append("rebuild/index-polish.html")

    receipt = {
        "ok": True,
        "writer": WRITER,
        "painted": True,
        "applied": applied,
        "skipped": skipped,
        "files": files,
        "captureTool": False,
    }
    dest = root / "qa" / "faq.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    try:
        receipt = author_faq(args.root)
    except FileNotFoundError as exc:
        fail(str(exc))
        return 2
    print(json.dumps(receipt, indent=2))
    if not faq_receipt_ok(receipt):
        fail("qa/faq.json is not a valid 3.2 FAQ receipt")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
