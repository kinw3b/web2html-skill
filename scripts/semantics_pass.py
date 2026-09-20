#!/usr/bin/env python3
"""3.3 / pre-2.2.e semantics pass — safe, site-agnostic promotions.

Compose heading_promote / section_promote / footer_promote. Last automated
sweep for SEO (scrape-only title / description / OG / Twitter), accessibility
(landmarks, heading rank, alts, labels), and lock-safe image performance
(eager hero, lazy below-fold). Do not invent skip-links, peeking chrome, or
marketing meta. Encode PATTERNS, not one lifestyle page's class names.

  python3 semantics_pass.py rebuild/index-polish.html -o rebuild/index-polish.html
  python3 semantics_pass.py rebuild/index-polish.html --qa qa/semantics-pass-qa.json

See references/semantics-pass.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from footer_promote import find_footer_root, footer_gate_errors, promote_footer
from heading_promote import (
    census_headings,
    hierarchy_defects,
    promote_visual_headings,
    ranks_from_dom,
    write_qa as write_heading_qa,
)
from paper_layer_names import ensure_main_landmark
from section_promote import promote_sections, section_gate_errors
from type_align import preserve_align_on_retag

SKIP_TEXT = re.compile(r"skip(?:\s+|-)?(?:to(?:\s+|-)?(?:content|main)|link)", re.I)
SKIP_CLASS = re.compile(r"\bskip(?:-?to)?(?:-?content|-?main|-?link)?\b", re.I)
ANNOUNCE = re.compile(r"announce|topbar|top-bar|ticker|promo-bar|banner-bar", re.I)
MOBILE_NAV = re.compile(r"mobile|drawer|hamburger|offcanvas|off-canvas", re.I)
CARD_HINT = re.compile(
    r"\b(card|tile|post|entry|member|quote|testimonial|service|feature)s?\b",
    re.I,
)
CLUSTER_SLUG = re.compile(
    r"\b(services?|testimonials?|blog|posts?|team|features?|articles?|"
    r"gallery|work|projects?|cases?)\b",
    re.I,
)
LAYOUT = re.compile(
    r"\b(flex|grid|contents|absolute|fixed|sticky|content-center|"
    r"content-start|content-end)\b",
    re.I,
)
ABS_STYLE = re.compile(r"position\s*:\s*(absolute|fixed)", re.I)
SENTENCE = re.compile(r"[.!?…]")
CHECK_HINT = re.compile(r"check(?:mark)?|tick|✓|✔", re.I)
DECOR_HINT = re.compile(
    r"check(?:mark)?|tick|scribble|swirl|blob|decor|divider|ornament|"
    r"bg[-_]?graphic|paint|confetti",
    re.I,
)
SLUG = re.compile(r"[^a-z0-9]+")
SR_ONLY_CSS = (
    ".sr-only {\n"
    "  position: absolute;\n"
    "  width: 1px;\n"
    "  height: 1px;\n"
    "  padding: 0;\n"
    "  margin: -1px;\n"
    "  overflow: hidden;\n"
    "  clip: rect(0, 0, 0, 0);\n"
    "  white-space: nowrap;\n"
    "  border: 0;\n"
    "}\n"
)


def _soup(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def _class_str(el) -> str:
    cls = el.get("class") if hasattr(el, "get") else None
    if not cls:
        return ""
    if isinstance(cls, list):
        return " ".join(str(c) for c in cls)
    return str(cls)


def _style(el) -> str:
    return (el.get("style") or "") if hasattr(el, "get") else ""


def _blob(el) -> str:
    parts = [
        _class_str(el),
        _style(el),
        el.get("id") or "",
        el.get("data-name") or "",
        el.get("layer-name") or "",
        el.get("data-paper-name") or "",
        el.get("data-paper-section") or "",
        el.get("alt") or "",
        el.get("src") or "",
    ]
    return " ".join(str(p) for p in parts)


def _text(el) -> str:
    return " ".join(t.strip() for t in el.stripped_strings if t.strip())


def _is_text_leaf(el) -> bool:
    if getattr(el, "name", None) not in {"div", "p", "span", "cite"}:
        return False
    own = "".join(s for s in el.contents if isinstance(s, str)).strip()
    if not own:
        return False
    for child in el.children:
        if getattr(child, "name", None) and _text(child):
            return False
    return True


def _slugify(text: str, fallback: str) -> str:
    s = SLUG.sub("-", (text or "").lower()).strip("-")
    return (s[:48] or fallback)


def has_skip_link(html: str) -> bool:
    soup = _soup(html)
    for a in soup.find_all("a", href=True):
        blob = f"{_class_str(a)} {a.get('id') or ''} {_text(a)}"
        if SKIP_TEXT.search(blob) or SKIP_CLASS.search(blob):
            return True
    return False


def _is_layout(el) -> bool:
    blob = f"{_class_str(el)} {_style(el)}"
    if LAYOUT.search(_class_str(el)) or ABS_STYLE.search(_style(el)):
        return True
    if el.get("data-decorative") in {"true", "1", True}:
        return True
    return False


def _has_accessible_name(el) -> bool:
    if el.get("aria-label") or el.get("aria-labelledby"):
        return True
    ident = el.get("id")
    soup = el
    while getattr(soup, "parent", None) is not None:
        soup = soup.parent
    if ident and soup.find("label", attrs={"for": ident}):
        return True
    if el.find_parent("label") is not None:
        return True
    title = el.get("title")
    if title and str(title).strip():
        return True
    return False


def _input_kind(el) -> str | None:
    if el.name == "textarea":
        return "text"
    if el.name != "input":
        return None
    typ = (el.get("type") or "text").lower()
    if typ in {"hidden", "submit", "button", "image", "checkbox", "radio", "file"}:
        return None
    return typ


def unlabeled_text_inputs(soup) -> list:
    out = []
    for el in soup.find_all(["input", "textarea"]):
        kind = _input_kind(el)
        if kind is None:
            continue
        if kind in {"email", "text", "search", "tel", "url"} or el.name == "textarea":
            if not _has_accessible_name(el):
                out.append(el)
    return out


def _looks_like_card(el) -> bool:
    if el.name in {"article"}:
        return True
    if CARD_HINT.search(_class_str(el)) or CARD_HINT.search(el.get("id") or ""):
        return True
    if el.find(["h2", "h3", "h4"]) and (el.find("p") or el.find("img")):
        return True
    return False


def _cluster_blob(el) -> str:
    return " ".join(
        [
            el.get("id") or "",
            el.get("data-paper-section") or "",
            el.get("data-name") or "",
            el.get("layer-name") or "",
            el.get("data-paper-name") or "",
            _class_str(el),
        ]
    )


def find_card_clusters(soup) -> list[tuple]:
    """Return (container, children) groups that should be <article>s."""
    hits = []
    seen: set[int] = set()
    sections = soup.find_all("section")
    for sec in sections:
        clusterish = bool(CLUSTER_SLUG.search(_cluster_blob(sec)))
        containers = [sec] + [
            d
            for d in sec.find_all(["div", "ul", "ol"], recursive=True)
            if d.find_parent("section") is sec
        ]
        for container in containers:
            kids = [
                c
                for c in container.children
                if getattr(c, "name", None) in {"div", "article", "li", "a"}
            ]
            if len(kids) < 2:
                continue
            hints = [CARD_HINT.search(_class_str(k) + " " + (k.get("id") or "")) for k in kids]
            same_hint = all(hints) and len({h.group(0).lower() for h in hints if h}) == 1
            structured = clusterish and all(_looks_like_card(k) or k.name == "article" for k in kids)
            if not (same_hint or structured):
                continue
            key = id(container)
            if key in seen:
                continue
            seen.add(key)
            hits.append((container, kids))
    return hits


def _card_is_article(node) -> bool:
    """The item is an <article>, sits inside one, or is a list item holding one.

    `<li><article>…</article></li>` is the correct shape for a card list whose
    Paper layer is named `li · …`: the <li> is the list slot, the <article> is
    the card. Treat it as satisfied rather than forcing the <li> to be dropped.
    """
    if node.name == "article" or node.find_parent("article") is not None:
        return True
    if node.name == "li":
        children = [c for c in node.find_all(recursive=False)]
        return len(children) == 1 and children[0].name == "article"
    return False


def card_cluster_errors(html: str) -> list[str]:
    soup = _soup(html)
    errors = []
    for container, kids in find_card_clusters(soup):
        bare = [k for k in kids if not _card_is_article(k)]
        if bare:
            sec = container if container.name == "section" else container.find_parent("section")
            label = (sec.get("id") if sec is not None else None) or (
                sec.get("data-paper-section") if sec is not None else "cluster"
            )
            errors.append(
                f"card cluster in #{label} has {len(bare)} item(s) not wrapped in <article>"
            )
    return errors


def landmark_errors(html: str) -> list[str]:
    soup = _soup(html)
    errors: list[str] = []
    navs = [
        n
        for n in soup.find_all("nav")
        if n.find_parent("footer") is None
    ]
    header = soup.find("header")
    if navs and header is None:
        errors.append("missing <header> wrapping announcement + primary nav")
    elif navs and header is not None:
        top = [
            n
            for n in navs
            if n.find_parent("header") is None
            and n.find_parent("main") is None
            and not MOBILE_NAV.search(_blob(n))
        ]
        if top:
            errors.append("primary nav is not inside <header>")
    sections = soup.find_all("section")
    main = soup.find("main")
    if sections and main is None:
        errors.append("missing <main id=\"main-content\">")
    elif main is not None and (main.get("id") or "") != "main-content":
        errors.append('<main> is missing id="main-content"')
    footer = soup.find("footer")
    footer_root = find_footer_root(soup)
    if footer is None and footer_root is not None:
        errors.append("missing <footer> for last chrome band")
    elif footer is None:
        body_text = _text(soup.body or soup).lower()
        if "all rights reserved" in body_text or "copyright" in body_text or "©" in body_text:
            errors.append("missing <footer> for last chrome band")
    for nav in navs:
        if not (nav.get("aria-label") or nav.get("aria-labelledby")):
            errors.append("nav is missing aria-label")
            break
    return errors


def heading_errors(html: str) -> list[str]:
    soup = _soup(html)
    defects = hierarchy_defects(ranks_from_dom(soup))
    qa = census_headings(html)
    for d in qa.get("defects") or []:
        if d not in defects:
            defects.append(d)
    return defects


def input_label_errors(html: str) -> list[str]:
    soup = _soup(html)
    errors = []
    for el in unlabeled_text_inputs(soup):
        kind = _input_kind(el) or "text"
        errors.append(f"unlabeled {kind} input needs <label class=\"sr-only\"> or aria-label")
    return errors


def content_img_errors(html: str) -> list[str]:
    soup = _soup(html)
    errors = []
    for img in soup.find_all("img"):
        if _is_decorative_img(img):
            continue
        alt = img.get("alt")
        if alt is None:
            errors.append("content <img> missing alt")
    return errors


def _is_decorative_img(img) -> bool:
    if img.get("data-decorative") in {"true", "1", True}:
        return True
    if img.find_parent(attrs={"data-decorative": True}) is not None:
        return True
    blob = _blob(img)
    if DECOR_HINT.search(blob) or CHECK_HINT.search(blob):
        return True
    alt = img.get("alt")
    if alt == "" and img.get("aria-hidden") in {"true", "1", True}:
        return True
    return False


def semantics_gate_errors(html: str) -> list[str]:
    """Hard-gate messages. Skip-link is never required. Missing OG is not a fail."""
    errors: list[str] = []
    errors.extend(section_gate_errors(html))
    errors.extend(heading_errors(html))
    errors.extend(landmark_errors(html))
    errors.extend(card_cluster_errors(html))
    errors.extend(input_label_errors(html))
    errors.extend(content_img_errors(html))
    # Compose footer chrome when a footer (or footer-shaped band) exists.
    soup = _soup(html)
    if soup.find("footer") is not None or find_footer_root(soup) is not None:
        for msg in footer_gate_errors(html):
            if msg not in errors:
                errors.append(msg)
    return errors


def build_qa(html: str, receipt: dict | None = None) -> dict:
    errors = semantics_gate_errors(html)
    heading_qa = census_headings(html)
    soup = _soup(html)
    qa = {
        "ok": not errors,
        "errors": errors,
        "landmarks": {
            "header": soup.find("header") is not None,
            "nav": len(soup.find_all("nav")),
            "main": soup.find("main") is not None,
            "main_id": (soup.find("main") or {}).get("id")
            if soup.find("main") is not None
            else None,
            "footer": soup.find("footer") is not None,
        },
        "articles": len(soup.find_all("article")),
        "h1": len(soup.find_all("h1")),
        "skip_link": has_skip_link(html),
        "skip_link_required": False,
        "heading": {
            "ok": heading_qa.get("ok"),
            "defects": heading_qa.get("defects") or [],
        },
        "meta": (receipt or {}).get("meta") or {"skipped": True, "why": "not applied"},
        "receipt": receipt or {},
    }
    return qa


def write_qa(path: Path, qa: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")


# --- apply helpers ---------------------------------------------------------



def _restore_footer_landmark(soup) -> str | None:
    """footer_promote may retag the chrome band to <form> when the email
    walk reaches the root. Restore the landmark; keep the inner form."""
    if soup.find("footer") is not None:
        return None
    for el in soup.find_all(True):
        if el.name in {"html", "body", "head"}:
            continue
        if "footer" not in _blob(el).lower():
            continue
        if el.name == "form":
            footer = soup.new_tag("footer")
            ident = el.get("id")
            if ident:
                footer["id"] = ident
                del el["id"]
            el.insert_before(footer)
            footer.append(el.extract())
            return "restored <footer> around newsletter form"
        el.name = "footer"
        if not el.get("id"):
            el["id"] = "footer"
        return "restored <footer> landmark"
    return None


def _wrap_header(soup) -> str | None:
    if soup.find("header") is not None:
        return None
    root = soup.find(id="paper-root") or soup.body
    if root is None:
        return None
    kids = [c for c in root.children if getattr(c, "name", None)]
    chrome = []
    for kid in kids:
        if kid.name in {"nav", "header"}:
            chrome.append(kid)
            continue
        if kid.name in {"div", "p", "aside", "section"} and ANNOUNCE.search(_blob(kid)):
            chrome.append(kid)
            continue
        break
    navs = [c for c in chrome if c.name == "nav"]
    if not navs:
        # lone top-level nav later in the tree (before main/section)
        for kid in kids:
            if kid.name == "nav" and kid.find_parent("footer") is None:
                chrome = [kid]
                navs = [kid]
                break
            if kid.name in {"main", "section", "footer"}:
                break
    if not navs:
        return None
    header = soup.new_tag("header")
    first = chrome[0]
    first.insert_before(header)
    for node in chrome:
        header.append(node.extract())
    return "wrapped announcement + primary nav in <header>"


def _ensure_main(html: str, soup) -> tuple[str, object, str | None]:
    note = None
    if soup.find("main") is None:
        html = ensure_main_landmark(html)
        soup = _soup(html)
        if soup.find("main") is not None:
            note = "wrapped content sections in <main>"
    main = soup.find("main")
    if main is not None and (main.get("id") or "") != "main-content":
        main["id"] = "main-content"
        note = (note + "; " if note else "") + 'set main id="main-content"'
    return html, soup, note


def _label_navs(soup) -> list[str]:
    notes = []
    for nav in soup.find_all("nav"):
        if nav.get("aria-label") or nav.get("aria-labelledby"):
            continue
        if MOBILE_NAV.search(_blob(nav)):
            nav["aria-label"] = "Mobile"
            notes.append('nav aria-label="Mobile"')
        else:
            nav["aria-label"] = "Primary"
            notes.append('nav aria-label="Primary"')
    return notes


def _wrap_articles(soup) -> list[str]:
    notes = []
    for _container, kids in find_card_clusters(soup):
        changed = 0
        for kid in kids:
            if kid.name == "article" or kid.find_parent("article") is not None:
                continue
            if kid.name in {"div", "li", "a"}:
                kid.name = "article"
                changed += 1
        if changed:
            notes.append(f"wrapped {changed} card(s) in <article>")
    return notes


def _label_sections(soup) -> list[str]:
    notes = []
    for sec in soup.find_all("section"):
        if sec.get("aria-labelledby") or sec.get("aria-label"):
            continue
        heading = sec.find(["h1", "h2", "h3"])
        if heading is not None:
            hid = heading.get("id")
            if not hid:
                base = sec.get("id") or _slugify(_text(heading), "section")
                hid = f"{base}-title"
                heading["id"] = hid
            sec["aria-labelledby"] = hid
            notes.append(f"section aria-labelledby={hid}")
            continue
        imgs = sec.find_all("img")
        text = _text(sec)
        if imgs and len(text) < 40:
            name = (
                sec.get("data-name")
                or sec.get("data-paper-name")
                or sec.get("data-paper-section")
                or sec.get("id")
                or ""
            )
            if name:
                sec["aria-label"] = str(name).replace("·", " ").strip()
                notes.append("gallery section aria-label from Paper name")
    return notes


def _promote_checklists(soup) -> list[str]:
    notes = []
    for container in soup.find_all(["div", "section", "ul"]):
        kids = [
            c
            for c in container.children
            if getattr(c, "name", None) in {"div", "p", "li"}
        ]
        if len(kids) < 3:
            continue
        ticks = 0
        for k in kids:
            blob = _blob(k) + " " + _text(k)
            if k.find("img") and CHECK_HINT.search(_blob(k.find("img")) + " " + (k.find("img").get("alt") or "")):
                ticks += 1
            elif CHECK_HINT.search(blob) and len(_text(k)) <= 80:
                ticks += 1
        if ticks < 3 or ticks < len(kids):
            continue
        if container.name != "ul":
            container.name = "ul"
        for k in kids:
            if k.name != "li":
                k.name = "li"
        notes.append("promoted feature ticks to <ul>/<li>")
    return notes


def _promote_cites(soup) -> list[str]:
    notes = []
    for card in soup.find_all(["article", "div"]):
        blob = _cluster_blob(card) + " " + _cluster_blob(card.find_parent("section") or card)
        if not re.search(r"testimonial|quote|review", blob, re.I):
            continue
        leaves = [el for el in card.find_all(["div", "p", "span"]) if _is_text_leaf(el)]
        if not leaves:
            continue
        author = leaves[-1]
        text = _text(author)
        if not text or SENTENCE.search(text):
            continue
        words = text.split()
        if not (1 <= len(words) <= 6):
            continue
        if author.name == "cite":
            continue
        author.name = "cite"
        notes.append("testimonial attribution → <cite>")
    return notes


def _name_forms(soup) -> list[str]:
    notes = []
    for form in soup.find_all("form"):
        if form.get("aria-label") or form.get("aria-labelledby"):
            continue
        heading = form.find(["h2", "h3", "h4", "legend"])
        if heading is not None and _text(heading):
            hid = heading.get("id") or _slugify(_text(heading), "form")
            heading["id"] = hid
            form["aria-labelledby"] = hid
        else:
            nearby = form.find_previous(["h2", "h3", "legend"])
            label = _text(nearby) if nearby is not None and len(_text(nearby)) <= 40 else ""
            if label and re.search(r"newsletter|subscribe|join", label, re.I):
                form["aria-label"] = label
            else:
                form["aria-label"] = "Newsletter"
        notes.append("form accessible name")
    return notes


def _promote_paragraphs(soup) -> list[str]:
    notes = []
    n = 0
    for el in list(soup.find_all("div")):
        if not _is_text_leaf(el):
            continue
        if _is_layout(el):
            continue
        if el.find_parent(["nav", "button", "a", "label", "h1", "h2", "h3", "h4"]):
            continue
        text = _text(el)
        if not text or len(text) > 400:
            continue
        # Body sentence, or short eyebrow / handwriting label.
        eyebrow = len(text) <= 48 and not SENTENCE.search(text)
        if not (SENTENCE.search(text) or eyebrow):
            continue
        # UA <p> is start-aligned. Keep parent/node gold (Pitfall #94).
        preserve_align_on_retag(el)
        el.name = "p"
        n += 1
    if n:
        notes.append(f"promoted {n} body/eyebrow div(s) to <p>")
    return notes


def _fix_alts(soup) -> list[str]:
    notes = []
    for img in soup.find_all("img"):
        if _is_decorative_img(img):
            if img.get("alt") is None:
                img["alt"] = ""
            img["aria-hidden"] = "true"
            notes.append("decorative img alt=\"\" aria-hidden")
            continue
        if img.get("alt") is not None:
            continue
        nearby = None
        parent = img.find_parent(["article", "section", "figure"])
        if parent is not None:
            h = parent.find(["h1", "h2", "h3", "h4", "figcaption"])
            if h is not None:
                nearby = _text(h)
        name = img.get("data-name") or img.get("data-paper-name") or ""
        alt = (nearby or name or "").strip()
        if alt:
            img["alt"] = alt[:120]
            notes.append("content img alt from nearby/Paper name")
        else:
            img["alt"] = ""
            notes.append("content img alt left empty — no nearby/Paper name")
    return notes


def _label_inputs(soup) -> list[str]:
    notes = []
    used: set[str] = set()
    for el in unlabeled_text_inputs(soup):
        kind = _input_kind(el) or "text"
        ident = el.get("id")
        if not ident:
            base = "email" if kind == "email" else ("name" if (el.get("name") or "").lower() == "name" or kind == "text" else kind)
            ident = base
            n = 2
            while soup.find(id=ident) or ident in used:
                ident = f"{base}-{n}"
                n += 1
            el["id"] = ident
        used.add(ident)
        if kind == "email":
            words = "Email"
        elif (el.get("name") or "").lower() in {"name", "fullname", "full-name"} or "name" in (el.get("placeholder") or "").lower():
            words = "Name"
        else:
            words = (el.get("placeholder") or kind).strip().capitalize() or "Input"
        label = soup.new_tag("label", attrs={"class": "sr-only", "for": ident})
        label.string = words
        el.insert_before(label)
        notes.append(f"sr-only label for {kind} input")
    return notes


def _is_chrome_img(img) -> bool:
    return img.find_parent(["header", "nav", "footer"]) is not None


def _perf_images(soup) -> list[str]:
    """Eager first content photo; lazy decode the rest. No geometry change."""
    notes: list[str] = []
    eager_done = False
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        if src.endswith(".svg") or src.startswith("data:image/svg"):
            continue
        if not img.get("decoding"):
            img["decoding"] = "async"
            notes.append("img decoding=async")
        chrome = _is_chrome_img(img)
        if chrome:
            continue
        if not eager_done:
            img["fetchpriority"] = "high"
            if img.get("loading") == "lazy":
                del img["loading"]
            eager_done = True
            notes.append("hero img fetchpriority=high (eager)")
            continue
        if not img.get("loading"):
            img["loading"] = "lazy"
            notes.append("below-fold img loading=lazy")
    return notes


def _ensure_html_lang(soup, meta: dict) -> list[str]:
    html = soup.find("html")
    if html is None:
        return []
    if (html.get("lang") or "").strip():
        return []
    lang = (meta.get("lang") or "").strip()
    if not lang:
        return []
    html["lang"] = lang
    return [f"html lang={lang} from scrape"]


def load_scrape_meta(root: Path | None, html: str, explicit: dict | None = None) -> dict:
    """Title / description / og image from scrape, capture, existing <title>, or Paper.

    Never invents marketing copy. Missing fields stay absent.
    """
    meta: dict[str, str] = {}
    if explicit:
        for key in (
            "title",
            "description",
            "og_image",
            "og:title",
            "og:description",
            "og:image",
            "lang",
            "canonical",
        ):
            val = explicit.get(key)
            if val:
                canon = {
                    "og:title": "title",
                    "og:description": "description",
                    "og:image": "og_image",
                }.get(key, key)
                meta.setdefault(canon, str(val).strip())
    candidates: list[Path] = []
    if root is not None:
        candidates.extend(
            [
                root / "qa" / "scrape-meta.json",
                root / "capture" / "home" / "meta.json",
                root / "source-site" / "index.html",
                root / "source-site" / "home.html",
            ]
        )
    for path in candidates:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                for key, canon in (
                    ("title", "title"),
                    ("description", "description"),
                    ("og_image", "og_image"),
                    ("og:title", "title"),
                    ("og:description", "description"),
                    ("og:image", "og_image"),
                    ("lang", "lang"),
                    ("canonical", "canonical"),
                ):
                    val = data.get(key)
                    if val:
                        meta.setdefault(canon, str(val).strip())
        else:
            parsed = _meta_from_html(raw)
            for k, v in parsed.items():
                meta.setdefault(k, v)
    existing = _meta_from_html(html)
    for key in ("title", "description", "og_image", "lang", "canonical"):
        if existing.get(key):
            meta.setdefault(key, existing[key])
    return {k: v for k, v in meta.items() if v}


def _meta_from_html(html: str) -> dict[str, str]:
    soup = _soup(html)
    out: dict[str, str] = {}
    html_el = soup.find("html")
    if html_el and (html_el.get("lang") or "").strip():
        out["lang"] = html_el["lang"].strip()
    title = soup.find("title")
    if title and title.string and title.string.strip():
        out["title"] = title.string.strip()
    desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if desc and desc.get("content"):
        out["description"] = desc["content"].strip()
    og_t = soup.find("meta", attrs={"property": re.compile(r"^og:title$", re.I)})
    if og_t and og_t.get("content"):
        out.setdefault("title", og_t["content"].strip())
    og_d = soup.find("meta", attrs={"property": re.compile(r"^og:description$", re.I)})
    if og_d and og_d.get("content"):
        out.setdefault("description", og_d["content"].strip())
    og_i = soup.find("meta", attrs={"property": re.compile(r"^og:image$", re.I)})
    if og_i and og_i.get("content"):
        out["og_image"] = og_i["content"].strip()
    canon = soup.find("link", attrs={"rel": re.compile(r"\bcanonical\b", re.I)})
    if canon and canon.get("href"):
        out["canonical"] = canon["href"].strip()
    return out


def _emit_meta(soup, meta: dict[str, str]) -> dict:
    """Emit title/description/OG only from provided sources. Never invent."""
    if not meta.get("title") or not meta.get("description") or not meta.get("og_image"):
        missing = [k for k in ("title", "description", "og_image") if not meta.get(k)]
        return {
            "skipped": True,
            "why": "scrape/capture missing " + ", ".join(missing) + " — not invented",
            "have": sorted(meta.keys()),
        }
    head = soup.find("head")
    if head is None:
        return {"skipped": True, "why": "no <head> to emit meta into"}
    title = soup.find("title")
    if title is None:
        tag = soup.new_tag("title")
        tag.string = meta["title"]
        head.append(tag)
    elif not (title.string or "").strip():
        title.string = meta["title"]
    def _upsert_meta(attr: str, key: str, content: str) -> None:
        el = soup.find("meta", attrs={attr: key})
        if el is None:
            el = soup.new_tag("meta", attrs={attr: key, "content": content})
            head.append(el)
        elif not el.get("content"):
            el["content"] = content

    _upsert_meta("name", "description", meta["description"])
    _upsert_meta("property", "og:title", meta["title"])
    _upsert_meta("property", "og:description", meta["description"])
    _upsert_meta("property", "og:image", meta["og_image"])
    _upsert_meta("name", "twitter:card", "summary_large_image")
    _upsert_meta("property", "og:type", "website")
    emitted = [
        "title",
        "description",
        "og:title",
        "og:description",
        "og:image",
        "og:type",
        "twitter:card",
    ]
    canon = (meta.get("canonical") or "").strip()
    if canon:
        link = soup.find("link", attrs={"rel": re.compile(r"\bcanonical\b", re.I)})
        if link is None:
            link = soup.new_tag("link", attrs={"rel": "canonical", "href": canon})
            head.append(link)
        elif not link.get("href"):
            link["href"] = canon
        emitted.append("canonical")
    return {
        "skipped": False,
        "emitted": emitted,
    }


def ensure_sr_only_css(css: str | None) -> tuple[str | None, bool]:
    if css is None:
        return None, False
    if re.search(r"\.sr-only\b", css):
        return css, False
    extra = SR_ONLY_CSS if css.endswith("\n") or not css else "\n" + SR_ONLY_CSS
    return (css + extra if css else SR_ONLY_CSS), True


def apply_semantics(
    html: str,
    *,
    scrape: dict | None = None,
    utilities_css: str | None = None,
    root: Path | None = None,
    freeze_structure: bool = False,
) -> tuple[str, dict, str | None]:
    """Safe promotions. Never inserts a skip-link. Never invents marketing meta.

    freeze_structure (3.x after 2.4): SEO / a11y / lock-safe perf only. Do
    not retag headings, wrap landmarks, or promote checklists — those moves
    undo 2.3 type and layout (Pitfall #196).
    """
    receipt: dict = {"applied": [], "skipped": [], "meta": {}}
    if not html or not html.strip():
        receipt["skipped"].append("empty html")
        return html, receipt, utilities_css

    had_skip = has_skip_link(html)

    if freeze_structure:
        receipt["skipped"].append("freeze-structure: no section/heading/footer promote")
        soup = _soup(html)
    else:
        html = promote_sections(html)
        receipt["applied"].append("section_promote")
        html, heading_qa = promote_visual_headings(html)
        receipt["applied"].append("heading_promote")
        receipt["heading"] = {"ok": heading_qa.get("ok"), "defects": heading_qa.get("defects")}
        html = promote_footer(html)
        receipt["applied"].append("footer_promote")

        soup = _soup(html)
        restored = _restore_footer_landmark(soup)
        if restored:
            receipt["applied"].append(restored)
            html = str(soup)
            soup = _soup(html)
        note = _wrap_header(soup)
        if note:
            receipt["applied"].append(note)
        html = str(soup)
        html, soup, main_note = _ensure_main(html, soup)
        if main_note:
            receipt["applied"].append(main_note)
    receipt["applied"].extend(_label_navs(soup))
    if freeze_structure:
        receipt["skipped"].append("freeze-structure: no article/checklist/cite/paragraph retag")
    else:
        receipt["applied"].extend(_wrap_articles(soup))
        receipt["applied"].extend(_promote_checklists(soup))
        receipt["applied"].extend(_promote_cites(soup))
        receipt["applied"].extend(_promote_paragraphs(soup))
    receipt["applied"].extend(_label_sections(soup))
    receipt["applied"].extend(_name_forms(soup))
    receipt["applied"].extend(_fix_alts(soup))
    receipt["applied"].extend(_label_inputs(soup))
    receipt["applied"].extend(_perf_images(soup))

    meta = load_scrape_meta(root, str(soup), explicit=scrape)
    receipt["applied"].extend(_ensure_html_lang(soup, meta))
    receipt["meta"] = _emit_meta(soup, meta)

    html = str(soup)
    if has_skip_link(html) and not had_skip:
        # Never keep an invented skip-link. Strip any we accidentally added.
        soup = _soup(html)
        for a in list(soup.find_all("a", href=True)):
            blob = f"{_class_str(a)} {a.get('id') or ''} {_text(a)}"
            if SKIP_TEXT.search(blob) or SKIP_CLASS.search(blob):
                a.decompose()
        html = str(soup)
        receipt["skipped"].append("stripped invented skip-link")

    css, added = ensure_sr_only_css(utilities_css)
    if added:
        receipt["applied"].append("added .sr-only to utilities.css")
    return html, receipt, css


def default_qa_path(ship: Path) -> Path | None:
    ship = ship.resolve()
    for parent in (ship.parent.parent, ship.parent):
        qa = parent / "qa"
        if qa.is_dir():
            return qa / "semantics-pass-qa.json"
    return None


def default_root(ship: Path) -> Path:
    ship = ship.resolve()
    if ship.parent.name == "rebuild":
        return ship.parent.parent
    return ship.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--qa", type=Path, help="Write semantics-pass-qa.json")
    ap.add_argument("--scrape", type=Path, help="Optional scrape-meta JSON")
    ap.add_argument("--utilities", type=Path, help="utilities.css to receive .sr-only")
    ap.add_argument("--root", type=Path, help="Project root for scrape/capture lookup")
    ap.add_argument(
        "--freeze-structure",
        action="store_true",
        help="3.x: SEO/a11y/perf only — do not retag signed 2.3/2.4 markup",
    )
    args = ap.parse_args(argv)
    if not args.input.is_file():
        print(f"FAIL: missing {args.input}", file=sys.stderr)
        return 1
    html = args.input.read_text(encoding="utf-8")
    scrape = None
    if args.scrape and args.scrape.is_file():
        try:
            scrape = json.loads(args.scrape.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: {args.scrape} is not JSON: {exc}", file=sys.stderr)
            return 1
    util_path = args.utilities
    if util_path is None:
        guess = args.input.parent / "css" / "utilities.css"
        if guess.is_file():
            util_path = guess
    css = util_path.read_text(encoding="utf-8") if util_path and util_path.is_file() else None
    root = args.root or default_root(args.input)
    freeze = args.freeze_structure or (root / "qa" / "fidelity-freeze-24.json").is_file()
    out, receipt, css_out = apply_semantics(
        html,
        scrape=scrape,
        utilities_css=css,
        root=root,
        freeze_structure=freeze,
    )
    dest = args.output or args.input
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")
    if css_out is not None and util_path is not None:
        util_path.parent.mkdir(parents=True, exist_ok=True)
        util_path.write_text(css_out, encoding="utf-8")
    qa = build_qa(out, receipt)
    qa_path = args.qa or default_qa_path(dest)
    if qa_path is not None:
        write_qa(qa_path, qa)
        heading_path = qa_path.with_name("heading-pass-qa.json")
        write_heading_qa(heading_path, census_headings(out))
        print(f"wrote {qa_path}")
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    print(f"semantics-pass: ok={qa['ok']} errors={qa['errors']}")
    if not qa["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
