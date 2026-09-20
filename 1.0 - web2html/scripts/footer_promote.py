"""2.2.b footer chrome: last site band → <footer> + real links/form.

Paper often leaves the footer as an unnamed sibling of the last CTA
section (`ready-to-take-your-business`). retag_from_layer_names only
retags named landmarks (`NN · footer`). Library-class / href maps only
hit exact copy (+ optional styleIncludes), so About / social text /
icon-only socials stay divs. Pitfall #92.

  from footer_promote import promote_footer, footer_gate_errors
"""
from __future__ import annotations

import re
from typing import Iterable

FOOTER_MARKERS = (
    "copyright",
    "quick links",
    "our newsletter",
    "all rights reserved",
)
COLUMN_LABELS = {
    "quick links",
    "social",
    "our newsletter",
    "newsletter",
    "company",
    "legal",
    "resources",
    "explore",
    "menu",
}
SOCIAL_NETWORKS = (
    "twitter",
    "linkedin",
    "facebook",
    "instagram",
    "github",
)
SOCIAL_LABELS = {
    "twitter": "Twitter",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "github": "GitHub",
}
SUBMIT_LABELS = {"join", "subscribe", "sign up", "sign-up"}
EMAIL_PLACEHOLDERS = {
    "email address",
    "email",
    "your email",
    "enter your email",
    "e-mail",
}
SECTION_ALIASES = {
    "about": ("about",),
    "services": ("services", "content-section"),
    "service": ("content-section", "services"),
    "blog": ("blog", "article-section"),
    "contact": ("contact", "ready-to-take-your-business"),
    "home": ("hero-section",),
}
DESTINATIONS = {
    "about",
    "services",
    "service",
    "blog",
    "contact",
    "home",
    *SOCIAL_NETWORKS,
}
WORDMARK_SIZE = re.compile(r"\btext-(?:2xl|3xl|4xl)\b")
PX_RE = re.compile(r"(-?[\d.]+)px")
WIDTH_STYLE = re.compile(r"(?:^|;)\s*width\s*:\s*[^;]+;?", re.I)
HEIGHT_STYLE = re.compile(r"(?:^|;)\s*height\s*:\s*[^;]+;?", re.I)


def _class_str(el) -> str:
    cls = el.get("class") if hasattr(el, "get") else None
    if not cls:
        return ""
    if isinstance(cls, list):
        return " ".join(str(c) for c in cls)
    return str(cls)


def _style(el) -> str:
    return (el.get("style") or "") if hasattr(el, "get") else ""


def _text(el) -> str:
    return " ".join(t.strip() for t in el.stripped_strings if t.strip())


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _layer_blob(el) -> str:
    return " ".join(
        str(el.get(k) or "")
        for k in ("data-name", "layer-name", "data-paper-name", "id", "data-paper-section")
    ).lower()


def _is_named_footer(el) -> bool:
    return "footer" in _layer_blob(el)


def _style_px(style: str, prop: str) -> float | None:
    m = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", style or "", re.I)
    if not m:
        return None
    px = PX_RE.search(m.group(1))
    return float(px.group(1)) if px else None


def _is_text_leaf(el) -> bool:
    if getattr(el, "name", None) not in {"div", "p", "span", "a"}:
        return False
    own = "".join(s for s in el.contents if isinstance(s, str)).strip()
    if not own:
        return False
    for child in el.children:
        if getattr(child, "name", None) and _text(child):
            return False
    return True


def _has_section_cta(el) -> bool:
    """True when this band also holds the last-section CTA heading."""
    for h in el.find_all(True):
        text = _text(h)
        if len(text.split()) <= 3:
            continue
        cls = _class_str(h)
        st = _style(h)
        if h.name in {"h1", "h2"}:
            return True
        if "text-5xl" in cls or "text-6xl" in cls or "text-7xl" in cls:
            return True
        if re.search(r"text-wrap:\s*pretty", st, re.I):
            return True
    return False


def _section_ids(soup) -> set[str]:
    ids: set[str] = set()
    for el in soup.find_all(True):
        ident = el.get("id")
        if ident:
            ids.add(str(ident))
    return ids


def resolve_dest_href(label: str, ids: Iterable[str]) -> str | None:
    key = _norm(label)
    known = set(ids)
    if key in SOCIAL_NETWORKS:
        return f"#{key}"
    aliases = SECTION_ALIASES.get(key)
    if not aliases:
        return None
    for alias in aliases:
        if alias in known:
            return f"#{alias}"
    if key == "home":
        return "index.html"
    return f"#{aliases[0]}"


def find_footer_root(soup):
    existing = soup.find("footer")
    if existing is not None:
        return existing
    for el in soup.find_all(True):
        if el.name in {"div", "section", "aside", "footer"} and _is_named_footer(el):
            return el
    candidates: list[tuple[int, object]] = []
    for el in soup.find_all(["div", "section"]):
        t = _norm(_text(el))
        score = sum(1 for m in FOOTER_MARKERS if m in t)
        if score == 0:
            continue
        kids = [c for c in el.children if getattr(c, "name", None)]
        if not kids and el.name != "section":
            continue
        candidates.append((score, el))
    if not candidates:
        return None
    no_cta = [(s, el) for s, el in candidates if not _has_section_cta(el)]
    pool = no_cta or candidates
    pool.sort(key=lambda pair: (-pair[0], len(_text(pair[1]))))
    return pool[0][1]


def _add_class(el, token: str) -> None:
    cls = list(el.get("class") or [])
    if token not in cls:
        cls.append(token)
        el["class"] = cls


def _harvest_wordmark(soup, footer) -> str:
    nav = soup.find("nav")
    if nav is not None:
        logo = nav.find(class_="nav-logo") or nav.find(class_="nav-mobile__logo")
        if logo is not None:
            t = _text(logo)
            if t:
                return t
        for a in nav.find_all("a", href=True):
            t = _text(a)
            if t and len(t.split()) == 1 and "btn-" not in _class_str(a):
                return t
    for el in footer.find_all(["div", "p", "span", "a"]):
        if not _is_text_leaf(el):
            continue
        t = _text(el)
        if len(t.split()) == 1 and WORDMARK_SIZE.search(_class_str(el)):
            return t
    return ""


def _promote_leaf_link(el, href: str, cls: str = "footer-link") -> None:
    if el.name not in {"div", "p", "span", "a"}:
        return
    el.name = "a"
    el["href"] = href
    if "text-decoration" not in _style(el):
        st = _style(el)
        extra = "text-decoration: none; cursor: pointer"
        el["style"] = f"{st}; {extra}" if st else extra
    _add_class(el, cls)


def _promote_text_destinations(footer, ids: set[str], wordmark: str) -> None:
    for el in list(footer.find_all(["div", "p", "span", "a"])):
        if not _is_text_leaf(el):
            continue
        raw = _text(el)
        key = _norm(raw)
        if key in COLUMN_LABELS:
            continue
        if key in EMAIL_PLACEHOLDERS or key in SUBMIT_LABELS:
            continue
        if "copyright" in key or "all rights reserved" in key:
            continue
        if wordmark and key == _norm(wordmark):
            if el.name != "a":
                _promote_leaf_link(el, "index.html", "footer-logo")
            elif not el.get("href"):
                el["href"] = "index.html"
            continue
        href = resolve_dest_href(raw, ids)
        if not href:
            continue
        if el.name == "a":
            current = el.get("href") or ""
            dest_id = href[1:] if href.startswith("#") else ""
            if dest_id and dest_id in ids:
                el["href"] = href
            elif not current or current == "#":
                el["href"] = href
            _add_class(el, "footer-link")
            continue
        _promote_leaf_link(el, href)


def _src_blob(el) -> str:
    parts = [
        el.get("aria-label") or "",
        el.get("alt") or "",
        el.get("title") or "",
        el.get("src") or "",
        el.get("data-name") or "",
        el.get("layer-name") or "",
        el.get("data-paper-name") or "",
    ]
    return " ".join(str(p) for p in parts).lower()


def infer_social_network(el) -> str | None:
    blob = _src_blob(el)
    parent = getattr(el, "parent", None)
    if parent is not None:
        blob += " " + _src_blob(parent) + " " + _layer_blob(parent)
    for net in SOCIAL_NETWORKS:
        if net in blob:
            return net
        if net == "twitter" and re.search(r"\bx(?:\.com)?\b", blob):
            return "twitter"
    svg = el if el.name == "svg" else el.find("svg")
    if svg is None:
        return None
    vb = (svg.get("viewbox") or svg.get("viewBox") or "").replace(" ", "")
    paths = svg.find_all("path")
    evenodd = any(
        (p.get("clip-rule") or p.get("fill-rule") or "").lower() == "evenodd"
        for p in paths
    )
    if vb in {"001815", "0018.15"} or (vb.startswith("0018") and len(paths) == 1):
        return "twitter"
    if vb in {"00915", "009.15"} or (vb.startswith("009") and len(paths) == 1):
        return "facebook"
    if len(paths) >= 3:
        return "instagram"
    if evenodd:
        return "github"
    return None


def _media_box(el):
    """Return the painted icon box (small flex wrapper), else the media node."""
    node = el
    for _ in range(4):
        parent = getattr(node, "parent", None)
        if parent is None or parent.name != "div":
            break
        st = _style(parent)
        w = _style_px(st, "width")
        h = _style_px(st, "height")
        if w and h and w <= 32 and h <= 32:
            node = parent
            continue
        break
    return node


def _is_logo_media(el, wordmark: str) -> bool:
    st = _style(el)
    parent = getattr(el, "parent", None)
    pst = _style(parent) if parent is not None else ""
    w = _style_px(st, "width") or _style_px(pst, "width")
    h = _style_px(st, "height") or _style_px(pst, "height")
    if (w and w >= 28) or (h and h >= 28):
        return True
    if wordmark:
        row = el
        for _ in range(5):
            row = getattr(row, "parent", None)
            if row is None or row.name in {
                "footer", "section", "main", "nav", "header", "body", "html",
            }:
                break
            if wordmark.lower() in _norm(_text(row)) and len(_text(row).split()) <= 4:
                # wordmark cluster, not the 4-icon social row
                if len(row.find_all(["svg", "img"])) == 1:
                    return True
    return False


def _looks_social_media(el, wordmark: str) -> bool:
    if _is_logo_media(el, wordmark):
        return False
    if infer_social_network(el):
        return True
    st = _style(el)
    parent = getattr(el, "parent", None)
    pst = _style(parent) if parent is not None else ""
    w = _style_px(st, "width") or _style_px(pst, "width")
    h = _style_px(st, "height") or _style_px(pst, "height")
    if w and h and w <= 24 and h <= 24:
        return True
    return False


def unwrapped_social_icons(footer, wordmark: str = "") -> list:
    hits = []
    for media in footer.find_all(["img", "svg"]):
        if media.find_parent("a") is not None:
            continue
        if not _looks_social_media(media, wordmark):
            continue
        hits.append(media)
    return hits


def _retag_as_link(el, href: str, label: str) -> None:
    from bs4 import Tag

    if el.name in {"div", "span", "p"}:
        el.name = "a"
        target = el
    else:
        a = Tag(name="a")
        el.insert_before(a)
        a.append(el)
        target = a
    target["href"] = href
    target["aria-label"] = label
    st = target.get("style") or ""
    if "cursor" not in st:
        target["style"] = f"{st}; cursor: pointer" if st else "cursor: pointer"


def _wrap_social_icons(footer, wordmark: str) -> None:
    unused = list(SOCIAL_NETWORKS)
    for media in list(footer.find_all(["img", "svg"])):
        if media.find_parent("a") is not None:
            continue
        if _is_logo_media(media, wordmark):
            box = _media_box(media)
            if box.find_parent("a") is None:
                _retag_as_link(box, "index.html", wordmark or "Home")
            continue
        if not _looks_social_media(media, wordmark):
            continue
        net = infer_social_network(media)
        if net is None and unused:
            net = unused[0]
        if net is None:
            continue
        if net in unused:
            unused.remove(net)
        box = _media_box(media)
        if box.find_parent("a") is not None:
            continue
        _retag_as_link(box, f"#{net}", SOCIAL_LABELS.get(net, net.title()))


def _is_form_chrome(el) -> bool:
    st = _style(el)
    cl = _class_str(el)
    has_border = (
        "border-width" in st
        or re.search(r"border(?:-color|-style)?\s*:", st)
        or bool(re.search(r"(?:^|\s)border(?:-[trblxyse])?(?:-[a-z0-9-]+)?(?:\s|$)", cl))
    )
    has_radius = "border-radius" in st or "rounded" in cl
    return bool(has_border and (has_radius or "overflow-clip" in cl or "overflow-hidden" in cl))


def _find_email_leaf(footer):
    for el in footer.find_all("input"):
        if (el.get("type") or "").lower() == "email":
            return el
    for el in footer.find_all(["div", "p", "span", "label"]):
        if not _is_text_leaf(el):
            continue
        if _norm(_text(el)) in EMAIL_PLACEHOLDERS:
            return el
    return None


def _find_join(footer, email_el):
    scope = footer
    if email_el is not None:
        for parent in email_el.parents:
            if parent is footer:
                break
            if parent.find(string=re.compile(r"^\s*(Join|Subscribe|Sign up)\s*$", re.I)):
                scope = parent
                break
    found = None
    for el in scope.find_all(["button", "a", "div", "span", "input"]):
        if el.name == "input" and (el.get("type") or "").lower() == "submit":
            return el
        label = _norm(_text(el)) if el.name != "input" else _norm(el.get("value") or "")
        if label not in SUBMIT_LABELS:
            continue
        found = el
        if el.name == "button":
            return el
    return found


def _leaf_to_email_input(el) -> None:
    if el.name == "input":
        el["type"] = "email"
        if not el.get("name"):
            el["name"] = "email"
        if not el.get("placeholder"):
            el["placeholder"] = el.get("aria-label") or "Email address"
        return
    placeholder = _text(el) or "Email address"
    el.name = "input"
    el.clear()
    el["type"] = "email"
    el["name"] = "email"
    el["placeholder"] = placeholder
    el["aria-label"] = placeholder
    st = _style(el)
    st = WIDTH_STYLE.sub(";", st)
    st = HEIGHT_STYLE.sub(";", st)
    extras = []
    compact = st.replace(" ", "").lower()
    if "background" not in compact:
        extras.append("background: transparent")
    if "border" not in compact:
        extras.append("border: none")
    if "outline" not in compact:
        extras.append("outline: none")
    if extras:
        st = f"{st}; {'; '.join(extras)}" if st.strip(" ;") else "; ".join(extras)
    el["style"] = re.sub(r";{2,}", ";", st).strip(" ;")
    _add_class(el, "w-full")


def _fix_join_button(btn) -> None:
    if btn.name == "input":
        btn["type"] = "submit"
        return
    if btn.name not in {"button", "a", "div", "span"}:
        return
    if btn.name != "button":
        # hoist onto painted pill if this is a label span
        parent = btn.parent
        if (
            parent is not None
            and parent.name in {"button", "div"}
            and _norm(_text(parent)) in SUBMIT_LABELS
        ):
            btn = parent
        btn.name = "button"
    btn["type"] = "submit"
    cls = [c for c in (btn.get("class") or []) if c != "w-full"]
    if cls:
        btn["class"] = cls
    elif btn.has_attr("class"):
        del btn["class"]
    st = _style(btn)
    extras = []
    compact = st.replace(" ", "").lower()
    if "height:" not in compact:
        extras.append("height: 100%")
    if "width:" not in compact:
        extras.append("width: auto")
    if "align-self" not in compact:
        extras.append("align-self: stretch")
    if extras:
        btn["style"] = f"{st}; {'; '.join(extras)}" if st else "; ".join(extras)
    parent = btn.parent
    if (
        parent is not None
        and parent.name == "div"
        and not parent.get("class")
        and not parent.get("style")
    ):
        kids = [c for c in parent.children if getattr(c, "name", None)]
        if len(kids) == 1:
            parent.unwrap()


def _promote_newsletter(footer) -> None:
    email = _find_email_leaf(footer)
    if email is None:
        return
    join = _find_join(footer, email)
    chrome = None
    node = email
    for _ in range(8):
        node = getattr(node, "parent", None)
        if node is None or node is footer:
            break
        if _is_form_chrome(node):
            chrome = node
            break
    if chrome is None:
        chrome = email.parent
        while chrome is not None and chrome is not footer:
            if chrome.name == "div" and (
                "grid" in _class_str(chrome) or "flex" in _class_str(chrome)
            ):
                break
            chrome = chrome.parent
    if chrome is None:
        chrome = email.parent
    if chrome is not None and chrome.name != "form":
        chrome.name = "form"
        if not chrome.get("action"):
            chrome["action"] = "#"
    _leaf_to_email_input(email)
    if join is not None:
        _fix_join_button(join)


def _has_email_field(footer) -> bool:
    if footer.find("input", attrs={"type": "email"}):
        return True
    for el in footer.find_all(["div", "p", "span", "label", "input"]):
        if el.name == "input" and "email" in (el.get("placeholder") or "").lower():
            return True
        if _is_text_leaf(el) and _norm(_text(el)) in EMAIL_PLACEHOLDERS:
            return True
    return False


def _has_submit(footer) -> bool:
    for el in footer.find_all(["button", "input"]):
        typ = (el.get("type") or "").lower()
        if typ == "submit":
            return True
        if el.name == "button" and _norm(_text(el)) in SUBMIT_LABELS:
            return True
        if el.name == "input" and _norm(el.get("value") or "") in SUBMIT_LABELS:
            return True
    return False


def footer_gate_errors(html: str) -> list[str]:
    """Hard-gate messages for verify-rebuild-trees (Pitfall #92)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    footer = soup.find("footer")
    errors: list[str] = []
    if footer is None:
        errors.append(
            "no <footer> — last chrome band must be retagged (Pitfall #92)"
        )
        return errors
    if footer.find("a", href=True) is None:
        errors.append("footer has 0 a[href] (Pitfall #92)")
    wordmark = _harvest_wordmark(soup, footer)
    icons = unwrapped_social_icons(footer, wordmark)
    if icons:
        errors.append(
            "footer social icon(s) not inside <a> "
            f"({len(icons)}). Wrap img/svg in <a aria-label>. Pitfall #92"
        )
    if _has_email_field(footer) and not _has_submit(footer):
        errors.append(
            "newsletter email field without a button/input submit (Pitfall #92)"
        )
    return errors


def promote_footer(html: str) -> str:
    """Retag last chrome band, promote destinations, wrap icons, fix form."""
    from bs4 import BeautifulSoup, Tag

    if not html or not html.strip():
        return html
    soup = BeautifulSoup(html, "html.parser")
    root = find_footer_root(soup)
    if root is None or not isinstance(root, Tag):
        return html
    if root.name != "footer":
        root.name = "footer"
        if not root.get("id"):
            root["id"] = "footer"
    ids = _section_ids(soup)
    wordmark = _harvest_wordmark(soup, root)
    _promote_text_destinations(root, ids, wordmark)
    _wrap_social_icons(root, wordmark)
    _promote_newsletter(root)
    return str(soup)


# silence unused-import pattern used in wrap fallback
__all__ = [
    "promote_footer",
    "find_footer_root",
    "footer_gate_errors",
    "resolve_dest_href",
    "infer_social_network",
    "unwrapped_social_icons",
]
