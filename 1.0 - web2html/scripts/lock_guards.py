"""Guards so semantic wrap cannot turn Paper layout shells into <a>/<button>.

Paper get_jsx of a Framer lander is almost all <div>s. Pricing columns use
`width: round(32%, 1px)` (or 32%) plus padding + radius. Pre-footer bands use
`width: 100%` + padding-top + radius. Those look like Pitfall #29 CTA chrome
if the hoist only checks radius + padding.

A label-wide semantic map ("Pricing", "Try 14 Days Free Trial") then hoists
every repeat onto the nearest padded card — three-column pricing and the
Join band collapse into inline anchors.

After the token pass, CTA chrome is often utilities (`bg-accent`, `rounded-*`,
`w-max`) rather than inline `background-color` / `width: max-content`. Hoist
must read both. A Join *cell* (`w-full` inside a max-content grid column)
is the painted pill and should become <button>; the Join *band* stays a div.
Hover-slot chrome (Source · Hover States gray DEFAULT/HOVER cards) must
never ship — only the actual component (the pill) is the interactive node.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

LAYOUT_SHELL_RE = re.compile(
    r"width:\s*(?:[0-9.]+%|round\([^)]*%[^)]*\))|flex-grow:\s*1|flex-basis:\s*0",
    re.I,
)
CTA_WIDTH_RE = re.compile(r"width:\s*max-content", re.I)
RADIUS_RE = re.compile(r"border-radius:", re.I)
PADDING_RE = re.compile(r"padding(?:-block|-inline|-top|-bottom|-left|-right)?:", re.I)
FILL_RE = re.compile(r"background-(?:color|image):", re.I)
BORDER_STYLE_RE = re.compile(
    r"border(?:-width|-style|-color|-block|-inline)?:", re.I
)
CTA_WIDTH_CLASS_RE = re.compile(r"(?:^|\s)w-max(?:\s|$)")
RADIUS_CLASS_RE = re.compile(r"(?:^|\s)rounded(?:-[a-z0-9]+)?(?:\s|$)")
PADDING_CLASS_RE = re.compile(
    r"(?:^|\s)(?:p|px|py|pt|pb|pl|pr|ps|pe)-[a-z0-9-]+(?:\s|$)"
)
FILL_CLASS_RE = re.compile(
    r"(?:^|\s)bg-(?:accent|primary|dark|ink|black)(?:-[a-z0-9-]+)?(?:\s|$)"
)
PAINTED_FILL_CLASS_RE = re.compile(
    r"(?:^|\s)bg-accent(?:-[a-z0-9-]+)?(?:\s|$)"
)
BORDER_CLASS_RE = re.compile(r"(?:^|\s)border(?:-[trblxyse])?(?:-[a-z0-9-]+)?(?:\s|$)")
SEMANTIC_TAGS = ("a", "button", "h1", "h2", "h3", "header", "footer", "nav", "p")
LANDMARK_TAGS = frozenset(
    {"html", "body", "main", "section", "header", "footer", "nav", "head"}
)
LAYOUT_ANCHOR_RE = re.compile(
    r"<a\b[^>]*style=\"[^\"]*(?:width:\s*(?:[0-9.]+%|round\()|flex-grow:\s*1)[^\"]*\"",
    re.I,
)
DEFAULT_CTA_COMPONENTS = (
    "BtnDark",
    "BtnPrimary",
    "BtnAccent",
    "Link",
    "btn-primary",
    "btn-accent",
    "btn-ghost",
)


def _class_str(classes: str | Iterable[str] | None) -> str:
    if not classes:
        return ""
    if isinstance(classes, str):
        return classes
    return " ".join(str(c) for c in classes)


def is_layout_shell(style: str, classes: str | Iterable[str] | None = None) -> bool:
    """True for % / flex-grow cards. `w-full` class alone is not a shell
    (Join cell in a max-content grid column is a painted pill)."""
    return bool(LAYOUT_SHELL_RE.search(style or ""))


def is_cta_chrome(style: str, classes: str | Iterable[str] | None = None) -> bool:
    """True only for a painted pill, never a card or section.

    Inline: max-content + radius + padding + fill.
    After token map: `w-max` + `rounded-*` + padding + (`bg-accent*` or border).
    """
    st = style or ""
    cl = _class_str(classes)
    if is_layout_shell(st, cl):
        return False
    has_width = bool(CTA_WIDTH_RE.search(st) or CTA_WIDTH_CLASS_RE.search(cl))
    has_radius = bool(RADIUS_RE.search(st) or RADIUS_CLASS_RE.search(cl))
    has_padding = bool(PADDING_RE.search(st) or PADDING_CLASS_RE.search(cl))
    has_fill = bool(FILL_RE.search(st) or FILL_CLASS_RE.search(cl))
    has_border = bool(BORDER_STYLE_RE.search(st) or BORDER_CLASS_RE.search(cl))
    if not (has_width and has_radius and has_padding):
        return False
    return has_fill or has_border


def is_painted_pill(style: str, classes: str | Iterable[str] | None = None) -> bool:
    """Compact painted chrome, including Join cells (`bg-accent` + padding).

    Does not require `w-max` / radius. Still refuses layout shells.
    """
    if is_cta_chrome(style, classes):
        return True
    st = style or ""
    cl = _class_str(classes)
    if is_layout_shell(st, cl):
        return False
    has_fill = bool(PAINTED_FILL_CLASS_RE.search(cl) or FILL_CLASS_RE.search(cl))
    has_padding = bool(PADDING_RE.search(st) or PADDING_CLASS_RE.search(cl))
    return bool(has_fill and has_padding)


def count_tags(html: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}\b", html, flags=re.I))


def layout_shell_anchor_count(html: str) -> int:
    return len(LAYOUT_ANCHOR_RE.findall(html))


def leaf_text_counts(html: str) -> Counter[str]:
    texts = re.findall(r"<div style=\"[^\"]*\">([^<]+)</div>", html)
    texts += re.findall(r"<div style='[^']*'>([^<]+)</div>", html)
    return Counter(t.strip() for t in texts if t.strip())


def repeated_link_labels(html: str, links: dict, *, max_repeats: int = 2) -> list[str]:
    counts = leaf_text_counts(html)
    bad: list[str] = []
    for label, info in (links or {}).items():
        allow = False
        if isinstance(info, dict):
            allow = bool(info.get("repeat") or info.get("allow_repeat"))
        if allow:
            continue
        if counts.get(label, 0) > max_repeats:
            bad.append(f"{label!r} x{counts[label]}")
    return bad


def _hoist_candidates(html: str, components: list[str]) -> bool:
    if any(tok in html for tok in ("btn-primary", "btn-accent", "btn-ghost")):
        return True
    if 'data-component="' in html:
        return True
    return any(c and c in html for c in components)


def _btn_classes(classes: Iterable[str] | None) -> list[str]:
    return [c for c in (classes or []) if str(c).startswith("btn-")]


def _single_label(node) -> bool:
    texts = [t.strip() for t in node.stripped_strings if t.strip()]
    return len(texts) == 1


def _is_cta_leaf(el) -> bool:
    if el.name in ("a", "button"):
        return True
    return bool(_btn_classes(el.get("class")))


def _find_painted_ancestor(leaf):
    from bs4 import Tag

    node = leaf
    for _ in range(10):
        node = getattr(node, "parent", None)
        if not isinstance(node, Tag):
            return None
        if node.name in LANDMARK_TAGS:
            return None
        if node.name in ("a", "button"):
            return None
        if node.name != "div":
            continue
        st = node.get("style") or ""
        cl = node.get("class")
        if is_layout_shell(st, cl):
            continue
        if not (is_cta_chrome(st, cl) or is_painted_pill(st, cl)):
            continue
        if _single_label(node):
            return node
    return None


def _promote_painted(painted, leaf) -> None:
    href = leaf.get("href") if leaf.name == "a" else None
    comp = leaf.get("data-component")
    leaf_classes = list(leaf.get("class") or [])
    btn_cls = _btn_classes(leaf_classes)

    if href:
        painted.name = "a"
        painted["href"] = href
    else:
        painted.name = "button"
        if not painted.get("type"):
            painted["type"] = "button"

    if comp:
        painted["data-component"] = comp

    pcls = list(painted.get("class") or [])
    for c in btn_cls:
        if c not in pcls:
            pcls.append(c)
    if pcls:
        painted["class"] = pcls

    leaf.name = "span"
    if leaf.has_attr("href"):
        del leaf["href"]
    if leaf.has_attr("data-component"):
        del leaf["data-component"]
    rest = [c for c in leaf_classes if not str(c).startswith("btn-")]
    if rest:
        leaf["class"] = rest
    elif leaf.has_attr("class"):
        del leaf["class"]

    st = painted.get("style") or ""
    extras: list[str] = []
    compact = st.replace(" ", "")
    if "cursor:pointer" not in compact:
        extras.append("cursor: pointer")
    if painted.name == "a" and "text-decoration" not in st:
        extras.append("text-decoration: none")
    if extras:
        painted["style"] = f"{st}; {'; '.join(extras)}" if st else "; ".join(extras)


def hoist_painted_ctas(html: str, components: list[str] | None = None) -> str:
    """Hoist href / button onto the painted pill (Pitfall #29 / #61).

    Selects `a.btn-primary`, `a.btn-accent`, `.btn-*` leaves, and
    `data-component=Link|Btn*`. After token map, `bg-accent` / `rounded-*`
    / `w-max` count as chrome. Join cell `w-full` in a max-content column
    becomes <button> when it is the painted pill. Layout shells stay divs.
    """
    comps = [c for c in (components or []) if c]
    if not _hoist_candidates(html, comps):
        return html

    from bs4 import BeautifulSoup, Tag

    soup = BeautifulSoup(html, "html.parser")
    seen: set[int] = set()
    leaves: list = []

    selectors = [
        "a.btn-primary",
        "a.btn-accent",
        "a.btn-ghost",
        "a[data-component]",
        ".btn-primary",
        ".btn-accent",
        ".btn-ghost",
    ]
    for c in comps + list(DEFAULT_CTA_COMPONENTS):
        selectors.append(f'a[data-component="{c}"]')
        selectors.append(f'[data-component="{c}"]')

    for el in soup.select(",".join(dict.fromkeys(selectors))):
        if not isinstance(el, Tag):
            continue
        ident = id(el)
        if ident in seen:
            continue
        seen.add(ident)
        leaves.append(el)

    promoted: set[int] = set()
    for leaf in leaves:
        if id(leaf) in promoted:
            continue
        st = leaf.get("style") or ""
        cl = leaf.get("class")
        if leaf.name in ("a", "button") and (
            is_cta_chrome(st, cl) or is_painted_pill(st, cl)
        ):
            continue
        painted = _find_painted_ancestor(leaf)
        if painted is None or painted.name in ("a", "button"):
            continue
        if id(painted) in promoted:
            continue
        _promote_painted(painted, leaf)
        promoted.add(id(painted))

    # Post-token: painted pill with exactly one a/button/.btn-* leaf.
    for node in list(soup.find_all("div")):
        if not isinstance(node, Tag) or node.name in ("a", "button"):
            continue
        if id(node) in promoted:
            continue
        st = node.get("style") or ""
        cl = node.get("class")
        if is_layout_shell(st, cl):
            continue
        if not (is_cta_chrome(st, cl) or is_painted_pill(st, cl)):
            continue
        if not _single_label(node):
            continue
        kids = [
            el
            for el in node.find_all(True)
            if el is not node and _is_cta_leaf(el)
        ]
        if len(kids) != 1:
            continue
        leaf = kids[0]
        if leaf.name in ("a", "button") and (
            is_cta_chrome(leaf.get("style") or "", leaf.get("class"))
            or is_painted_pill(leaf.get("style") or "", leaf.get("class"))
        ):
            continue
        _promote_painted(node, leaf)
        promoted.add(id(node))

    out = str(soup)
    n_shell = layout_shell_anchor_count(out)
    if n_shell:
        raise SystemExit(
            f"semanticize refused to write: {n_shell} layout-shell <a> "
            "(width 100% / round(%) / flex-grow). Pricing columns and Join "
            "bands must stay divs. Pitfall #61."
        )
    return out



PX_RE = re.compile(r"(-?[\d.]+)px")
NAV_OPEN_RE = re.compile(r"<nav\b[^>]*>", re.I)
RASTER_COVER = 0.8


def _style_px(style: str, prop: str) -> float | None:
    m = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", style or "", re.I)
    if not m:
        return None
    px = PX_RE.search(m.group(1))
    return float(px.group(1)) if px else None


def _class_has(el, token: str) -> bool:
    return token in _class_str(el.get("class") if hasattr(el, "get") else "")


def _nav_box(nav) -> tuple[float | None, float | None]:
    st = nav.get("style") or ""
    w = _style_px(st, "width")
    h = _style_px(st, "height")
    if w is not None and h is not None:
        return w, h
    for child in getattr(nav, "children", []):
        if getattr(child, "name", None) != "div":
            continue
        cst = child.get("style") or ""
        cw = _style_px(cst, "width") or w
        ch = _style_px(cst, "height") or h
        if cw is not None or ch is not None:
            return cw, ch
    return w, h


def _img_covers_nav(nav, img) -> bool:
    nw, nh = _nav_box(nav)
    st = img.get("style") or ""
    iw = _style_px(st, "width")
    ih = _style_px(st, "height")
    if nw and nh and iw and ih:
        return iw >= RASTER_COVER * nw and ih >= RASTER_COVER * nh
    cl = _class_str(img.get("class"))
    parent = getattr(img, "parent", None)
    pcl = _class_str(parent.get("class") if parent is not None else "")
    if "object-cover" in cl and ("w-full" in pcl or "w-full" in cl):
        return True
    if nw and iw and iw >= RASTER_COVER * nw:
        return True
    return False


def nav_is_raster_only(nav) -> bool:
    """True when a <nav> has no a[href] and is only / mostly a full-bleed img.

    Pitfall #91: missing-elements prepended a fullpage.png crop as 00 · nav.
    A logo <img> next to real links is fine. Mobile hamburger headers are
    not this pattern.
    """
    if nav is None:
        return False
    classes = _class_str(nav.get("class"))
    if "nav-mobile" in classes:
        return False
    if nav.find("a", href=True):
        return False
    if nav.find(["button", "input", "select", "textarea"]):
        return False
    imgs = nav.find_all("img")
    if not imgs:
        return False
    text = " ".join(t.strip() for t in nav.stripped_strings if t.strip())
    if not text:
        return True
    return any(_img_covers_nav(nav, img) for img in imgs)


def iter_nav_elements(html: str):
    from bs4 import BeautifulSoup, Tag

    soup = BeautifulSoup(html, "html.parser")
    for nav in soup.find_all("nav"):
        if isinstance(nav, Tag):
            yield nav


def raster_only_navs(html: str) -> list[str]:
    """Return ids / chips for <nav> nodes that shipped as a screenshot."""
    hits: list[str] = []
    for nav in iter_nav_elements(html):
        if not nav_is_raster_only(nav):
            continue
        nid = nav.get("id") or nav.get("data-paper-section") or "nav"
        hits.append(str(nid))
    return hits


def harvest_nav_ia(html: str, spec: dict | None = None) -> dict:
    """Logo + links + CTA from mobile nav, then spec. Never invent copy."""
    from bs4 import BeautifulSoup, Tag

    spec = spec or {}
    explicit = spec.get("nav") if isinstance(spec.get("nav"), dict) else {}
    soup = BeautifulSoup(html, "html.parser")
    mobile = soup.find(class_="nav-mobile") or soup.find(attrs={"data-nav-mobile": True})
    logo = None
    links: list[dict] = []
    ctas: list[dict] = []
    if isinstance(mobile, Tag):
        logo_el = mobile.find(class_="nav-mobile__logo")
        if isinstance(logo_el, Tag):
            logo = {
                "text": logo_el.get_text(" ", strip=True),
                "href": logo_el.get("href") or "index.html",
            }
        for a in mobile.find_all("a", href=True):
            if not isinstance(a, Tag):
                continue
            classes = list(a.get("class") or [])
            if "nav-mobile__logo" in classes:
                continue
            item = {
                "text": a.get_text(" ", strip=True),
                "href": a.get("href"),
                "classes": classes,
            }
            if not item["text"]:
                continue
            if any(str(c).startswith("btn-") for c in classes):
                ctas.append(item)
            else:
                links.append(item)
    if explicit.get("logo"):
        logo = explicit["logo"]
    if explicit.get("links"):
        links = list(explicit["links"])
    if explicit.get("cta"):
        ctas = [explicit["cta"]]
    if not links:
        for label, info in (spec.get("links") or {}).items():
            href = info["href"] if isinstance(info, dict) else info
            comp = info.get("component", "Link") if isinstance(info, dict) else "Link"
            item = {"text": label, "href": href, "classes": []}
            if str(comp).lower().startswith("btn") or "cta" in str(comp).lower():
                ctas.append({**item, "classes": ["btn-ghost"]})
            else:
                links.append(item)
    cta = None
    if ctas:
        demo = [c for c in ctas if "demo" in c["text"].lower()]
        cta = demo[-1] if demo else ctas[-1]
        if not any(str(c).startswith("btn-") for c in cta.get("classes") or []):
            cta = {**cta, "classes": ["btn-ghost"]}
    return {"logo": logo, "links": links, "cta": cta}


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_semantic_nav_inner(ia: dict, *, height: str = "160px") -> str:
    logo = ia.get("logo") or {"text": "", "href": "index.html"}
    logo_text = _escape(logo.get("text") or "")
    logo_href = _escape(logo.get("href") or "index.html")
    links_html = []
    for item in ia.get("links") or []:
        links_html.append(
            f'<a class="navbar-link" href="{_escape(item["href"])}">{_escape(item["text"])}</a>'
        )
    cta = ia.get("cta")
    cta_html = ""
    if cta:
        classes = " ".join(cta.get("classes") or ["btn-ghost"]) or "btn-ghost"
        cta_html = (
            f'<a class="{_escape(classes)}" href="{_escape(cta["href"])}">'
            f'{_escape(cta["text"])}</a>'
        )
    return (
        f'<div class="nav-main shrink-0 w-full" '
        f'style="height: {height}; left: 0px; top: 0px; '
        f'background-color: var(--color-surface-2)">'
        f'<div class="nav-inner">'
        f'<a class="nav-logo" href="{logo_href}">{logo_text}</a>'
        f'<div class="nav-links">{"".join(links_html)}</div>'
        f"{cta_html}"
        f"</div></div>"
    )


def reconstruct_raster_nav(html: str, spec: dict | None = None) -> str:
    """Replace a screenshot-only <nav> with logo + links + CTA (Pitfall #91).

    Harvests IA from `.nav-mobile` / spec. Leaves the nav untouched when
    there is no IA — the verify-rebuild-trees gate then fails.
    """
    hits = raster_only_navs(html)
    if not hits:
        return html
    ia = harvest_nav_ia(html, spec)
    if not ia.get("links"):
        return html
    from bs4 import BeautifulSoup, Tag

    out = html
    for m in list(NAV_OPEN_RE.finditer(html)):
        end = html.find("</nav>", m.end())
        if end < 0:
            continue
        chunk = html[m.start() : end + len("</nav>")]
        soup = BeautifulSoup(chunk, "html.parser")
        nav = soup.find("nav")
        if not isinstance(nav, Tag) or not nav_is_raster_only(nav):
            continue
        height = "160px"
        for el in [nav, *list(nav.find_all("div", recursive=False))]:
            h = _style_px(el.get("style") or "", "height")
            if h:
                height = f"{int(h) if h == int(h) else h}px"
                break
        inner = build_semantic_nav_inner(ia, height=height)
        rebuilt = m.group(0) + inner + "</nav>"
        out = out.replace(chunk, rebuilt, 1)
    return out
