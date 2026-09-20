#!/usr/bin/env python3
"""3.3 helper: Paper layer name → HTML tag (not a 2.0 join).

2.1 authors the page. Do not stamp or join pc-ids. Do not treat this
module as a 2.2.a dump or 2.2.b lock-assist. Do not generate maps from
repeating marketing copy (hero + pricing + footer).
"""
from __future__ import annotations

import re
from typing import Iterable

NUMBERED = re.compile(r"^(\d+)\s*·\s*(.+)$")
SOURCE_TAG = re.compile(
    r"^(h[1-6]|p|img|ul|ol|li|a|button|form|label)\s*·\s*(.+)$",
    re.I,
)
HEADING = re.compile(r"(?:^|[\s_-])heading(?:$|[\s_-])|^heading$|heading$", re.I)
SCRIBBLE = re.compile(r"scribble|decorative", re.I)
FAQ = re.compile(r"\bfaq\b", re.I)
INTERACTIVE = re.compile(r"\binteractive\b", re.I)
PILL = re.compile(r"\bpill\b", re.I)
TEXT_LINK = re.compile(r"\btext-link\b", re.I)
MEDIA = re.compile(r"\bmedia\b", re.I)
NAV_DROP = re.compile(r"navbar-dropdown", re.I)
CTA = re.compile(r"\b(cta|btn-primary|button)\b", re.I)
CANVAS_CLASS = re.compile(r"\bw-\[(?:1440|1600|1920)px\]")
CANVAS_WIDTH = re.compile(
    r"(?:^|;)\s*width:\s*(?:1440|1600|1920)px\s*(?=;|$)", re.I
)

LANDMARK_SLUGS = {
    "header": "header",
    "nav": "nav",
    "navbar": "nav",
    "navigation": "nav",
    "footer": "footer",
    "main": "main",
}


def parse_paper_name(name: str) -> dict:
    raw = (name or "").strip()
    m = NUMBERED.match(raw)
    nn = m.group(1) if m else None
    rest = (m.group(2) if m else raw).strip()
    slug = re.sub(r"[^\w]+", "-", rest.lower()).strip("-")
    return {"raw": raw, "nn": nn, "rest": rest, "slug": slug}


def _heading_tag(heading_index: int) -> str:
    return ("h1", "h2", "h3", "h4", "h5", "h6")[min(heading_index, 5)]


def class_from_paper_name(name: str) -> str | None:
    if PILL.search(name):
        return "pill"
    if TEXT_LINK.search(name):
        return "text-link"
    if MEDIA.search(name):
        return "media"
    if NAV_DROP.search(name):
        return "navbar-dropdown"
    if CTA.search(name):
        return "btn-primary"
    return None


def tag_from_paper_name(
    name: str,
    *,
    heading_index: int = 0,
    paper_type: str | None = None,
) -> dict:
    raw = (name or "").strip()
    source = SOURCE_TAG.match(raw)
    if source:
        tag = source.group(1).lower()
        rest = source.group(2).strip()
        slug = re.sub(r"[^\w]+", "-", rest.lower()).strip("-")
        cls = class_from_paper_name(name)
        if tag.startswith("h") and tag[1:].isdigit():
            kind = "heading"
        elif tag == "img":
            kind = "image"
        elif tag in {"a", "button"}:
            kind = "control"
        elif tag in {"ul", "ol", "li"}:
            kind = "list"
        elif tag == "form":
            kind = "form"
        else:
            kind = "text"
        return {
            "tag": tag,
            "id": slug or None,
            "class": cls,
            "kind": kind,
            "decorative": False,
            "notes": "from 1.4 source-semantics · live tag",
        }

    parsed = parse_paper_name(name)
    rest = parsed["rest"]
    slug = parsed["slug"]
    kind_type = (paper_type or "").strip()
    cls = class_from_paper_name(name)

    if INTERACTIVE.search(rest):
        return {
            "tag": None,
            "id": slug or None,
            "class": cls,
            "kind": "interactive",
            "decorative": False,
            "notes": "hover.css / 2.2.c / 2.2.d — do not dump into the lander",
        }

    if SCRIBBLE.search(rest):
        return {
            "tag": "svg",
            "id": slug or None,
            "class": cls,
            "kind": "decorative",
            "decorative": True,
            "notes": "aria-hidden decorative; keep svg or img",
        }

    if FAQ.search(rest):
        return {
            "tag": "details",
            "id": slug or None,
            "class": cls,
            "kind": "faq",
            "decorative": False,
            "notes": "from A/6 accordion, not a new pattern",
        }

    if cls in {"pill", "btn-primary"} or CTA.search(rest):
        return {
            "tag": "a",
            "id": slug or None,
            "class": cls or "btn-primary",
            "kind": "control",
            "decorative": False,
            "notes": "hoist href onto painted max-content pill only",
        }

    if HEADING.search(rest) or (slug.endswith("-heading") or slug.endswith("heading")):
        return {
            "tag": _heading_tag(heading_index),
            "id": slug or None,
            "class": cls,
            "kind": "heading",
            "decorative": False,
            "notes": "text-wrap: pretty already on titles",
        }

    if kind_type.lower() == "image":
        return {
            "tag": "img",
            "id": slug or None,
            "class": cls,
            "kind": "image",
            "decorative": False,
            "notes": "never empty Rectangle",
        }

    if kind_type.lower() == "text":
        return {
            "tag": "p",
            "id": slug or None,
            "class": cls,
            "kind": "text",
            "decorative": False,
            "notes": "do not retag Text to div",
        }

    landmark = LANDMARK_SLUGS.get(slug) or LANDMARK_SLUGS.get(rest.lower())
    if landmark:
        return {
            "tag": landmark,
            "id": slug,
            "class": cls,
            "kind": "landmark",
            "decorative": False,
            "notes": "keep id / data-section",
        }

    if parsed["nn"] or rest.lower().endswith("-section") or rest.lower().endswith(" section"):
        return {
            "tag": "section",
            "id": slug,
            "class": cls,
            "kind": "section",
            "decorative": False,
            "notes": "id from slug after ·",
        }

    return {
        "tag": "div",
        "id": slug or None,
        "class": cls,
        "kind": "frame",
        "decorative": False,
        "notes": "inner Frame stays div unless the name is semantic",
    }


def build_semantic_map(names: Iterable[str]) -> dict:
    layers = []
    heading_i = 0
    for name in names:
        if not (name or "").strip():
            continue
        spec = tag_from_paper_name(name, heading_index=heading_i)
        if spec["kind"] == "heading":
            heading_i += 1
        layers.append({"name": name, **spec})
    h1: list[str] = []
    h2: list[str] = []
    h3: list[str] = []
    links: dict[str, dict] = {}
    for row in layers:
        source = SOURCE_TAG.match(row["name"])
        if not source:
            continue
        tag = source.group(1).lower()
        rest = source.group(2).strip()
        if not rest:
            continue
        if tag == "h1" and rest not in h1:
            h1.append(rest)
        elif tag == "h2" and rest not in h2:
            h2.append(rest)
        elif tag == "h3" and rest not in h3:
            h3.append(rest)
        elif tag in {"a", "button"}:
            links.setdefault(rest, {"href": "#", "component": tag})
    return {
        "generatedFrom": "paper-layer-names",
        "layers": layers,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "faq": [],
        "links": links,
        "ctaComponents": [
            row["class"]
            for row in layers
            if row.get("class") in {"pill", "btn-primary"}
        ],
    }


def build_library_class_map(names: Iterable[str]) -> dict:
    paint = []
    seen: set[str] = set()
    for name in names:
        cls = class_from_paper_name(name)
        if not cls or cls in seen:
            continue
        seen.add(cls)
        paint.append({"class": cls, "namePrefix": name})
    return {
        "generatedFrom": "paper-layer-names",
        "paint": paint,
        "leaves": [],
        "require": [],
    }


_ATTR = re.compile(
    r"""(?:data-name|layer-name|data-paper-name)\s*=\s*["']([^"']+)["']""",
    re.I,
)
_SECTION = re.compile(
    r"<section\b([^>]*)>",
    re.I,
)
_ID = re.compile(r"""\bid=["']([^"']+)["']""", re.I)
_PAPER_SEC = re.compile(r"""\bdata-paper-section=["']([^"']+)["']""", re.I)


def collect_layer_names(html: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        name = name.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    for m in _ATTR.finditer(html):
        add(m.group(1))

    section_i = 0
    for m in _SECTION.finditer(html):
        attrs = m.group(1)
        named = _ATTR.search(attrs)
        if named:
            add(named.group(1))
            section_i += 1
            continue
        slug = None
        paper = _PAPER_SEC.search(attrs)
        ident = _ID.search(attrs)
        if paper:
            slug = paper.group(1)
        elif ident:
            slug = ident.group(1)
        if slug:
            section_i += 1
            add(f"{section_i:02d} · {slug}")
    return names



_DIV_TOKEN = re.compile(r"<div\b[^>]*>|</div>", re.I)
_OPEN_DIV_PAPER = re.compile(
    r"<div\b([^>]*\bdata-paper-section=(['\"])([^'\"]+)\2[^>]*)>",
    re.I,
)


def promote_paper_section_divs(html: str) -> str:
    """Leftover <div data-paper-section> bands become <section> (or nav/header/footer)."""
    matches = list(_OPEN_DIV_PAPER.finditer(html))
    if not matches:
        return html
    out = html
    for m in reversed(matches):
        slug = m.group(3)
        tag = LANDMARK_SLUGS.get(slug.lower(), "section")
        start, open_end = m.start(), m.end()
        depth = 1
        close_at = None
        for tok in _DIV_TOKEN.finditer(out, open_end):
            if tok.group(0).lower().startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    close_at = tok
                    break
        open_tag = f"<{tag}{m.group(1)}>"
        if close_at is None:
            out = out[:start] + open_tag + out[open_end:]
            continue
        out = (
            out[:start]
            + open_tag
            + out[open_end : close_at.start()]
            + f"</{tag}>"
            + out[close_at.end() :]
        )
    return out


_NAMED_OPEN = re.compile(
    r"<([a-zA-Z][\w:-]*)\b([^>]*\b(?:data-name|data-paper-name|layer-name)=(['\"])([^'\"]+)\3[^>]*)(/?)>",
    re.I,
)
_SOURCE_RETAG = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "a", "button", "form", "label",
}
_VOID_HTML = {"img", "input", "br", "hr", "meta", "link"}


def retag_source_semantics(html: str) -> str:
    """Retag named inner layers (`h1 · …`) from the 1.4 source census."""
    matches = list(_NAMED_OPEN.finditer(html))
    if not matches:
        return html
    out = html
    for m in reversed(matches):
        cur = m.group(1).lower()
        name = m.group(4)
        spec = tag_from_paper_name(name)
        if "source-semantics" not in (spec.get("notes") or ""):
            continue
        want = spec["tag"]
        if want not in _SOURCE_RETAG or want == cur:
            continue
        if want == "img":
            continue
        attrs = m.group(2)
        self_close = m.group(5) == "/" or cur in _VOID_HTML
        if self_close:
            continue
        token = re.compile(rf"<{re.escape(cur)}\b|</{re.escape(cur)}>", re.I)
        depth = 1
        close_at = None
        for tok in token.finditer(out, m.end()):
            if tok.group(0).startswith("</") or tok.group(0).lower().startswith(f"</{cur}"):
                depth -= 1
                if depth == 0:
                    close_at = tok
                    break
            else:
                depth += 1
        if want == "a" and not re.search(r"\bhref=", attrs, re.I):
            attrs = f'{attrs} href="#"'
        open_tag = f"<{want}{attrs}>"
        if close_at is None:
            out = out[: m.start()] + open_tag + out[m.end() :]
            continue
        out = (
            out[: m.start()]
            + open_tag
            + out[m.end() : close_at.start()]
            + f"</{want}>"
            + out[close_at.end() :]
        )
    return out


def retag_from_layer_names(html: str, names: list[str] | None = None) -> str:
    """Retag section wrappers from Paper names, then 1.4 source-tag leaves."""
    html = promote_paper_section_divs(html)
    collected = names if names is not None else collect_layer_names(html)

    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        name = None
        named = _ATTR.search(attrs)
        if named:
            name = named.group(1)
        else:
            paper = _PAPER_SEC.search(attrs)
            ident = _ID.search(attrs)
            slug = (paper.group(1) if paper else None) or (
                ident.group(1) if ident else None
            )
            if slug:
                for candidate in collected:
                    if parse_paper_name(candidate)["slug"] == slug:
                        name = candidate
                        break
                if name is None:
                    name = slug
        if not name:
            return m.group(0)
        spec = tag_from_paper_name(name)
        tag = spec["tag"]
        if tag not in {"header", "nav", "footer", "main", "section"}:
            return m.group(0)
        return f"<{tag}{attrs}>"

    out = _SECTION.sub(repl, html)
    # Close matching tags we opened as landmarks.
    for tag in ("header", "nav", "footer", "main"):
        # Only rewrite </section> that belong to a retagged open tag is hard
        # with regex; pair by walking.
        out = _fix_section_closes(out, tag)
    return retag_source_semantics(out)


def _fix_section_closes(html: str, open_tag: str) -> str:
    token = re.compile(rf"<{open_tag}\b|</section>|</{open_tag}>", re.I)
    out: list[str] = []
    opens = 0
    last = 0
    for m in token.finditer(html):
        out.append(html[last : m.start()])
        s = m.group(0)
        if s.lower().startswith(f"<{open_tag}"):
            opens += 1
            out.append(s)
        elif s.lower() == f"</{open_tag}>":
            out.append(s)
            if opens:
                opens -= 1
        elif opens:
            opens -= 1
            out.append(f"</{open_tag}>")
        else:
            out.append(s)
        last = m.end()
    out.append(html[last:])
    return "".join(out)


_ROOT = re.compile(
    r'(<div\b)([^>]*\bid=["\']paper-root["\'][^>]*)(>)',
    re.I,
)


def strip_canvas_root_widths(html: str) -> str:
    """After lock QA: page root only. Leave section geometry alone."""

    def repl(m: re.Match) -> str:
        prefix, attrs, end = m.group(1), m.group(2), m.group(3)
        attrs = CANVAS_CLASS.sub("", attrs)
        attrs = re.sub(r'class="\s*"', "", attrs)
        attrs = re.sub(r"class='\s*'", "", attrs)

        def style_repl(sm: re.Match) -> str:
            q = sm.group(1)
            body = CANVAS_WIDTH.sub("", sm.group(2))
            body = re.sub(r";;+", ";", body).strip(" ;")
            if "width:" not in body.lower():
                body = f"{body}; width: 100%" if body else "width: 100%"
            return f"style={q}{body}{q}"

        if re.search(r"\bstyle=", attrs, re.I):
            attrs = re.sub(
                r"""style=(["'])(.*?)\1""",
                style_repl,
                attrs,
                count=1,
                flags=re.I | re.DOTALL,
            )
        else:
            attrs += ' style="width: 100%"'
        attrs = re.sub(r"\s{2,}", " ", attrs)
        return f"{prefix}{attrs}{end}"

    return _ROOT.sub(repl, html, count=1)


def ensure_main_landmark(html: str) -> str:
    """One <main> around inner sections. display:contents so numbers stay."""
    if re.search(r"<main\b", html, re.I):
        return html
    m = re.search(
        r'(<div\b[^>]*\bid=["\']paper-root["\'][^>]*>)(.*)(</div>)',
        html,
        re.I | re.DOTALL,
    )
    if not m:
        return html
    prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
    parts: list[tuple[str, str]] = []
    child = re.compile(
        r"<(header|nav|section|footer|main)\b[^>]*>.*?</\1>",
        re.I | re.DOTALL,
    )
    last = 0
    for cm in child.finditer(inner):
        if cm.start() > last:
            lead = inner[last : cm.start()]
            if lead.strip():
                parts.append(("text", lead))
            else:
                parts.append(("ws", lead))
        tag = cm.group(1).lower()
        parts.append((tag, cm.group(0)))
        last = cm.end()
    if last < len(inner):
        tail = inner[last:]
        parts.append(("ws" if not tail.strip() else "text", tail))

    if not any(k == "section" for k, _ in parts):
        return html

    out: list[str] = []
    main_open = False
    for kind, chunk in parts:
        if kind in {"header", "nav", "footer"}:
            if main_open:
                out.append("</main>")
                main_open = False
            out.append(chunk)
        elif kind == "section":
            if not main_open:
                out.append('<main style="display: contents">')
                main_open = True
            out.append(chunk)
        else:
            out.append(chunk)
    if main_open:
        out.append("</main>")
    return html[: m.start()] + prefix + "".join(out) + suffix + html[m.end() :]
