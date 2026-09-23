#!/usr/bin/env python3
"""Shared HTML → Astro helpers for optional Phase 5 (Astro-first site).

Parses the signed 3.4 homepage, strips QA overlay chrome, rewrites asset and
page hrefs, and emits .astro fragments that keep the original semantics.
Interiors are authored straight into astro/src/pages at 5.2.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

SKIP_SHIP = frozenset({
    "design-system.html",
    "polish-report.html",
    "index-raw.html",
    "index-semantic.html",
    "index.html",
})
SKIP_SUFFIX = "-raw.html"
QA_HREF_RE = re.compile(
    r"""<link[^>]+href\s*=\s*['"][^'"]*qa-overlay[^'"]*['"][^>]*/?>""",
    re.I,
)
QA_SCRIPT_RE = re.compile(
    r"""<script[^>]+src\s*=\s*['"][^'"]*qa-overlay[^'"]*['"][^>]*>\s*</script>""",
    re.I,
)
HEADER_RE = re.compile(r"<header\b[^>]*>.*?</header>", re.I | re.S)
FOOTER_RE = re.compile(r"<footer\b[^>]*>.*?</footer>", re.I | re.S)
MAIN_RE = re.compile(r"<main\b[^>]*>.*?</main>", re.I | re.S)
HTML_COMMENT_COMPONENT_RE = re.compile(
    r"<!--\s*(?:@)?(?:component|reusable|extract)\s*:?\s+([A-Za-z][\w-]*)\s*-->",
    re.I,
)
PAPER_NOMINATE_RE = re.compile(
    r"(?:this|that)\s+is\s+(?:a\s+)?(?:shared\s+)?component"
    r"|reuse\s+(?:this|the)\s+[\w-]+"
    r"|extract\s+(?:this|the)\s+[\w-]+"
    r"|make\s+(?:this|the)\s+[\w-]+\s+a\s+component"
    r"|shared\s+component"
    r"|component:\s*[\w-]+",
    re.I,
)
PAPER_NAME_RE = re.compile(
    r"(?:component|reuse|extract|shared)\s+(?:the\s+)?([A-Za-z][\w-]*)",
    re.I,
)
CONTROL_OPEN_RE = re.compile(
    r"<(?P<tag>a|button)\b(?P<attrs>[^>]*)>",
    re.I,
)
ATTR_RE = re.compile(
    r"""([^\s=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?""",
    re.I,
)
CLASS_RE = re.compile(r"""\bclass\s*=\s*(['"])(.*?)\1""", re.I)
DATA_COMPONENT_RE = re.compile(
    r"""\bdata-component\s*=\s*(['"])([^'"]+)\1""",
    re.I,
)
GENERIC_PAPER_NAMES = frozenset({
    "frame", "image", "div", "text", "container", "box", "section",
    "group", "wrapper", "row", "col", "column", "item", "block",
})
PAPER_TOKENS = (
    "btn-primary",
    "btn-secondary",
    "btn-accent",
    "pill",
    "text-link",
    "navbar-link",
    "navbar-dropdown",
)
CHROME_ONLY_TOKENS = frozenset({"navbar-link", "navbar-dropdown"})
PAPER_BOARDS = frozenset({"Components", "Buttons", "Hover States", "Navigation"})
COMMENT_FILES = (
    "qa/paper-comments.json",
    "qa/build-paper-comments.json",
    "qa/paper-human-review.md",
    "qa/phase-4-review.md",
    "qa/phase-5-review.md",
)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
DESC_RE = re.compile(
    r"""<meta\b[^>]*\bname\s*=\s*['"]description['"][^>]*\bcontent\s*=\s*['"]([^'"]*)['"][^>]*>""",
    re.I,
)
LANG_RE = re.compile(r"""<html\b[^>]*\blang\s*=\s*['"]([^'"]+)['"]""", re.I)
HREF_RE = re.compile(r"""\b(href|src|action)\s*=\s*(['"])([^'"]+)\2""", re.I)
URL_CSS_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
HTML_PAGE_RE = re.compile(r"^[./]*(?P<slug>[A-Za-z0-9_-]+)\.html(?:#(?P<frag>.*))?$", re.I)


def now_pages(root: Path) -> list[dict]:
    """Homepage (from the 3.4 polish) plus every 5.2 interior in astro/src/pages."""
    pages: list[dict] = []
    try:
        import run_config

        adopted = run_config.adopt_mode(root)
    except Exception:  # noqa: BLE001
        adopted = False
    if adopted:
        home = root / "source-html" / "index.html"
    else:
        polish = root / "rebuild" / "index-polish.html"
        home = polish if polish.is_file() else root / "rebuild" / "index.html"
    if home.is_file():
        pages.append({
            "slug": "index",
            "ship": str(home.relative_to(root)),
            "route": "/",
            "astro": "astro/src/pages/index.astro",
        })
    payload_path = root / "qa" / "phase-5-pages.json"
    if payload_path.is_file():
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        for row in payload.get("pages") or []:
            if not isinstance(row, dict):
                continue
            slug = str(row.get("slug") or "").strip()
            if not slug or slug in {"home", "index"}:
                continue
            rel = str(row.get("astro") or f"astro/src/pages/{slug}.astro")
            if (root / rel).is_file():
                pages.append({"slug": slug, "astro": rel, "route": f"/{slug}/", "raw": row.get("raw")})
    return pages


def strip_qa(html: str) -> str:
    html = QA_HREF_RE.sub("", html)
    html = QA_SCRIPT_RE.sub("", html)
    html = re.sub(r'\sdata-qa-outlines="[^"]*"', "", html)
    return html


def first_match(pattern: re.Pattern[str], html: str) -> str:
    match = pattern.search(html)
    return match.group(0) if match else ""


def page_title(html: str) -> str:
    match = TITLE_RE.search(html)
    return html_lib.unescape(match.group(1).strip()) if match else ""


def page_description(html: str) -> str:
    match = DESC_RE.search(html)
    return html_lib.unescape(match.group(1).strip()) if match else ""


def page_lang(html: str) -> str:
    match = LANG_RE.search(html)
    return match.group(1).strip() if match else "en"


def astro_href(value: str) -> str:
    raw = value.strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return raw
    if re.match(r"^[a-z][a-z0-9+.-]*:", raw, re.I):
        return raw
    if raw.startswith("/styles/") or raw.startswith("/images/") or raw.startswith("/scripts/") or raw.startswith("/fonts/"):
        return raw
    lowered = raw.split("?", 1)[0]
    if lowered in {"css/qa-overlay.css", "js/qa-overlay.js"}:
        return raw
    if lowered.startswith("css/"):
        return "/styles/" + lowered[4:]
    if lowered.startswith("./css/"):
        return "/styles/" + lowered[6:]
    if lowered.startswith("images/"):
        return "/images/" + lowered[7:]
    if lowered.startswith("./images/"):
        return "/images/" + lowered[9:]
    if lowered.startswith("img/"):
        return "/images/" + lowered[4:]
    if lowered.startswith("js/"):
        return "/scripts/" + lowered[3:]
    if lowered.startswith("./js/"):
        return "/scripts/" + lowered[5:]
    if lowered.startswith("fonts/"):
        return "/fonts/" + lowered[6:]
    page = HTML_PAGE_RE.match(raw)
    if page:
        slug = page.group("slug").lower()
        frag = page.group("frag")
        route = "/" if slug in {"index", "home"} else f"/{slug}/"
        return f"{route}#{frag}" if frag else route
    if raw in {".", "./", "index.html", "./index.html"}:
        return "/"
    return raw


def rewrite_attrs(html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{astro_href(value)}{quote}"

    return HREF_RE.sub(repl, html)


def rewrite_css_urls(css: str) -> str:
    def repl(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        if value.startswith(("data:", "http:", "https:", "/", "#")):
            return match.group(0)
        name = Path(value.split("?", 1)[0]).name
        if name.endswith((".woff2", ".woff", ".ttf", ".otf")):
            rewritten = f"/fonts/{name}"
        elif name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif")):
            rewritten = f"/images/{name}"
        else:
            rewritten = astro_href(value)
        return f"url({quote}{rewritten}{quote})"

    return URL_CSS_RE.sub(repl, css)


def extract_regions(html: str) -> dict[str, str]:
    cleaned = rewrite_attrs(strip_qa(html))
    header = first_match(HEADER_RE, cleaned)
    footer = first_match(FOOTER_RE, cleaned)
    main = first_match(MAIN_RE, cleaned)
    return {
        "header": header,
        "footer": footer,
        "main": main,
        "title": page_title(cleaned),
        "description": page_description(cleaned),
        "lang": page_lang(html),
        "html": cleaned,
    }


def astro_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def fragment_file(html: str) -> str:
    return (
        "---\n"
        f"const html = `{astro_string(html)}`;\n"
        "---\n"
        "<Fragment set:html={html} />\n"
    )


def pascal_name(raw: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", (raw or "").strip())
    words = [part for part in parts if part]
    if not words:
        return ""
    if len(words) == 1 and words[0][:1].isupper() and words[0].isalnum():
        return words[0]
    return "".join(word[:1].upper() + word[1:] for word in words)


def _parse_attrs(attr_src: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(attr_src or ""):
        key = match.group(1)
        if key == "/":
            continue
        attrs[key.lower()] = match.group(2) or match.group(3) or match.group(4) or ""
    return attrs


def _class_list(attrs: dict[str, str] | str) -> list[str]:
    if isinstance(attrs, str):
        match = CLASS_RE.search(attrs)
        raw = match.group(2) if match else ""
    else:
        raw = attrs.get("class") or ""
    return [token for token in raw.split() if token]


def _data_component(attrs: dict[str, str] | str) -> str:
    if isinstance(attrs, str):
        match = DATA_COMPONENT_RE.search(attrs)
        return match.group(2).strip() if match else ""
    return (attrs.get("data-component") or "").strip()


def _balanced_element(html: str, start: int, tag: str) -> str:
    open_re = re.compile(rf"<{re.escape(tag)}\b[^>]*>", re.I)
    close_re = re.compile(rf"</{re.escape(tag)}\s*>", re.I)
    first = open_re.match(html, start)
    if not first:
        return ""
    depth = 1
    cursor = first.end()
    while depth:
        nxt_open = open_re.search(html, cursor)
        nxt_close = close_re.search(html, cursor)
        if not nxt_close:
            return ""
        if nxt_open and nxt_open.start() < nxt_close.start():
            depth += 1
            cursor = nxt_open.end()
            continue
        depth -= 1
        cursor = nxt_close.end()
    return html[start:cursor]


def _inner_html(element: str) -> str:
    match = re.match(r"<[^>]+>(.*)</[^>]+>\s*$", element, re.S)
    return match.group(1) if match else ""


def _text_only(inner: str) -> str:
    if re.search(r"<[a-zA-Z]", inner or ""):
        return ""
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<!--.*?-->", "", inner or "", flags=re.S))).strip()


def _span_overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start >= left and end <= right for left, right in spans)


def _region_spans(html: str) -> dict[str, list[tuple[int, int]]]:
    spans = {"header": [], "footer": [], "main": []}
    for key, pattern in (("header", HEADER_RE), ("footer", FOOTER_RE), ("main", MAIN_RE)):
        for match in pattern.finditer(html):
            spans[key].append((match.start(), match.end()))
    return spans


def _paper_token_in(classes: list[str]) -> str:
    found = [token for token in PAPER_TOKENS if token in classes]
    if not found:
        return ""
    return sorted(found, key=len, reverse=True)[0]


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _walk_strings(payload: object) -> list[str]:
    out: list[str] = []
    if isinstance(payload, str):
        out.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            out.extend(_walk_strings(value))
    elif isinstance(payload, list):
        for value in payload:
            out.extend(_walk_strings(value))
    return out


def library_component_names(root: Path) -> list[str]:
    path = root / "design-library" / "library.json"
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return []
    names: list[str] = []
    raw = payload.get("components")
    rows: list[object] = []
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = list(raw.get("inPage") or []) + list(raw.get("crossPage") or []) + list(raw.get("shared") or [])
    for row in rows:
        if isinstance(row, str):
            names.append(row)
            continue
        if not isinstance(row, dict):
            continue
        boards = {str(item) for item in (row.get("pageNames") or [])}
        on_paper = bool(boards & PAPER_BOARDS) or not boards
        for key in ("name", "token", "class", "exampleName"):
            value = row.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            token = value.strip()
            if token.lower() in GENERIC_PAPER_NAMES:
                continue
            if key == "exampleName" and not on_paper:
                continue
            if key == "exampleName" and not _looks_like_component_name(token):
                continue
            names.append(token)
    return _unique(names)


def _looks_like_component_name(raw: str) -> bool:
    low = raw.lower()
    if any(part in low for part in ("btn", "button", "card", "nav", "pill", "cta", "link", "footer", "header")):
        return True
    return bool(re.match(r"^[A-Z][A-Za-z0-9]+$", raw))


def capture_component_names(root: Path) -> list[str]:
    names: list[str] = []
    base = root / "source-site" / "components"
    if not base.is_dir():
        return []
    for manifest in sorted(base.rglob("manifest.json")):
        payload = _load_json(manifest)
        if not isinstance(payload, dict):
            continue
        for state in payload.get("states") or []:
            if not isinstance(state, dict):
                continue
            for key in ("component", "token", "label", "name"):
                value = state.get(key)
                if isinstance(value, str) and value.strip() and _looks_like_component_name(value):
                    names.append(value.strip())
        kind = str(payload.get("kind") or "").strip()
        if kind in {"buttons", "nav", "forms", "footer"}:
            names.append(kind)
    return _unique(names)


def comment_nominations(root: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for rel in COMMENT_FILES:
        path = root / rel
        if not path.is_file():
            continue
        if path.suffix == ".json":
            texts = _walk_strings(_load_json(path))
        else:
            texts = [path.read_text(encoding="utf-8", errors="replace")]
        for text in texts:
            if not PAPER_NOMINATE_RE.search(text):
                continue
            for match in PAPER_NAME_RE.finditer(text):
                name = match.group(1)
                if name.lower() in GENERIC_PAPER_NAMES | {"this", "that", "the", "a"}:
                    continue
                found.append({"name": name, "source": rel})
            for match in HTML_COMMENT_COMPONENT_RE.finditer(text):
                found.append({"name": match.group(1), "source": rel})
    return found


def html_comment_names(html: str) -> list[tuple[int, str]]:
    return [(match.end(), match.group(1)) for match in HTML_COMMENT_COMPONENT_RE.finditer(html)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip()
        if not key:
            continue
        low = key.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(key)
    return out


def _control_name(attrs: dict[str, str], nominated: set[str]) -> str:
    marked = _data_component(attrs)
    if marked:
        return pascal_name(marked)
    token = _paper_token_in(_class_list(attrs))
    if token:
        return pascal_name(token)
    for name in nominated:
        token = name.lower().replace(" ", "-")
        classes = {item.lower() for item in _class_list(attrs)}
        if token in classes or token in {attrs.get("id", "").lower(), _data_component(attrs).lower()}:
            return pascal_name(name)
    return ""


def _iter_controls(html: str) -> list[dict]:
    found: list[dict] = []
    for match in CONTROL_OPEN_RE.finditer(html):
        element = _balanced_element(html, match.start(), match.group("tag"))
        if not element:
            continue
        attrs = _parse_attrs(match.group("attrs"))
        found.append({
            "start": match.start(),
            "end": match.start() + len(element),
            "html": element,
            "tag": match.group("tag").lower(),
            "attrs": attrs,
        })
    return found


def _following_element(html: str, cursor: int) -> str:
    match = re.search(r"<([a-zA-Z][\w:-]*)\b[^>]*>", html[cursor:])
    if not match:
        return ""
    start = cursor + match.start()
    return _balanced_element(html, start, match.group(1))


def discover_page_candidates(html: str, *, nominated: set[str] | None = None) -> list[dict]:
    """Find reusable controls and comment-marked blocks in one signed page."""
    nominated = {name for name in (nominated or set()) if name}
    nominated_l = {name.lower() for name in nominated}
    cleaned = rewrite_attrs(strip_qa(html))
    spans = _region_spans(cleaned)
    chrome = spans["header"] + spans["footer"]
    candidates: list[dict] = []

    for start, raw_name in html_comment_names(cleaned):
        element = _following_element(cleaned, start)
        if not element:
            continue
        el_start = cleaned.find(element, start)
        if el_start < 0 or _span_overlaps(el_start, el_start + len(element), chrome):
            continue
        name = pascal_name(raw_name)
        if not name:
            continue
        candidates.append({
            "name": name,
            "kind": "comment",
            "html": element,
            "region": "main" if _span_overlaps(el_start, el_start + len(element), spans["main"]) else "page",
            "sources": [f"html-comment:{raw_name}"],
        })

    for control in _iter_controls(cleaned):
        if _span_overlaps(control["start"], control["end"], chrome):
            continue
        name = _control_name(control["attrs"], nominated_l)
        if not name:
            continue
        token = _paper_token_in(_class_list(control["attrs"]))
        if token in CHROME_ONLY_TOKENS:
            continue
        marked = _data_component(control["attrs"])
        sources = []
        if marked:
            sources.append(f"data-component:{marked}")
        if token:
            sources.append(f"paper-token:{token}")
        if name.lower() in nominated_l:
            sources.append("paper-comment")
        kind = "button" if control["tag"] in {"a", "button"} else "component"
        candidates.append({
            "name": name,
            "kind": kind,
            "html": control["html"],
            "tag": control["tag"],
            "attrs": control["attrs"],
            "region": "main" if _span_overlaps(control["start"], control["end"], spans["main"]) else "page",
            "sources": sources or ["html"],
        })
    return candidates


def should_extract(item: dict, *, paper_names: set[str], nominated: set[str], uses: int) -> tuple[bool, str]:
    name_l = str(item.get("name") or "").lower()
    sources = " ".join(item.get("sources") or [])
    paper_l = {value.lower() for value in paper_names}
    nominated_l = {value.lower() for value in nominated}
    if item.get("kind") == "chrome":
        return True, "chrome"
    if item.get("kind") == "comment" or "html-comment:" in sources:
        return True, "html-comment"
    if name_l in nominated_l or "paper-comment" in sources:
        return True, "paper-comment"
    if name_l in paper_l or "paper-token:" in sources or "data-component:" in sources:
        return uses >= 1, "paper"
    if uses >= 2:
        return True, "repeated"
    return False, "one-off"


def props_from_element(element: str) -> dict[str, str] | None:
    match = CONTROL_OPEN_RE.match(element.strip())
    if not match:
        return None
    inner = _text_only(_inner_html(element))
    if not inner:
        return None
    attrs = _parse_attrs(match.group("attrs"))
    props = {"label": inner}
    if match.group("tag").lower() == "a":
        props["href"] = astro_href(attrs.get("href") or "#")
    elif attrs.get("type"):
        props["type"] = attrs["type"]
    extra = [cls for cls in _class_list(attrs) if cls not in PAPER_TOKENS and cls != "btn"]
    if extra:
        props["class"] = " ".join(extra)
    return props


def control_component_file(element: str) -> str:
    match = CONTROL_OPEN_RE.match(element.strip())
    if not match:
        return fragment_file(element)
    tag = match.group("tag").lower()
    attrs = _parse_attrs(match.group("attrs"))
    classes = _class_list(attrs)
    class_attr = " ".join(classes)
    inner = _text_only(_inner_html(element))
    if not inner:
        return fragment_file(element)
    if tag == "a":
        default_href = astro_href(attrs.get("href") or "#")
        return (
            "---\n"
            "interface Props {\n"
            "  href?: string;\n"
            "  label?: string;\n"
            "  class?: string;\n"
            "}\n"
            f"const {{ href = `{astro_string(default_href)}`, label = `{astro_string(inner)}`, class: className = '' }} = Astro.props;\n"
            "---\n"
            f'<a class:list={{["{astro_string(class_attr)}", className]}} href={{href}}>{{label}}</a>\n'
        )
    type_attr = attrs.get("type") or "button"
    return (
        "---\n"
        "interface Props {\n"
        "  label?: string;\n"
        "  type?: string;\n"
        "  class?: string;\n"
        "}\n"
        f"const {{ label = `{astro_string(inner)}`, type = `{astro_string(type_attr)}`, class: className = '' }} = Astro.props;\n"
        "---\n"
        f'<button class:list={{["{astro_string(class_attr)}", className]}} type={{type}}>{{label}}</button>\n'
    )


def _sentinel(name: str, props: dict[str, str] | None) -> str:
    payload = json.dumps(props or {}, separators=(",", ":"), ensure_ascii=True).replace("-->", "--\\u003e")
    return f"<!--w2h:{name}:{payload}-->"


def apply_component_replacements(html: str, catalog: list[dict]) -> str:
    """Replace extracted in-page instances with sentinels convert-astro-home (5.1) turns into tags."""
    if not catalog or not html:
        return html
    updated = html
    controls = list(_iter_controls(updated))
    comment_hits = []
    for start, raw_name in html_comment_names(updated):
        element = _following_element(updated, start)
        if not element:
            continue
        el_start = updated.find(element, start)
        if el_start < 0:
            continue
        comment_hits.append((el_start, pascal_name(raw_name), element))

    replacements: list[tuple[int, int, str]] = []
    catalog_names = {str(row.get("name") or "") for row in catalog}
    for control in controls:
        name = _control_name(control["attrs"], {item.lower() for item in catalog_names})
        row = next((item for item in catalog if item.get("name") == name), None)
        if not row:
            continue
        if row.get("mode") == "props":
            props = props_from_element(control["html"])
            if not props:
                continue
            replacements.append((control["start"], control["end"], _sentinel(name, props)))
            continue
        if row.get("mode") == "fragment" and control["html"].strip() == (row.get("html") or "").strip():
            replacements.append((control["start"], control["end"], _sentinel(name, None)))

    for idx, name, element in comment_hits:
        row = next((item for item in catalog if item.get("name") == name), None)
        if not row:
            continue
        if row.get("mode") == "fragment" and element.strip() != (row.get("html") or "").strip():
            continue
        replacements.append((idx, idx + len(element), _sentinel(name, None)))

    replacements.sort(key=lambda item: item[0], reverse=True)
    used: list[tuple[int, int]] = []
    for start, end, token in replacements:
        if any(not (end <= left or start >= right) for left, right in used):
            continue
        updated = updated[:start] + token + updated[end:]
        used.append((start, end))
    return updated


def main_parts(main_html: str) -> list[dict]:
    pattern = re.compile(r"<!--w2h:([A-Za-z][\w-]*):(.*?)-->", re.S)
    parts: list[dict] = []
    cursor = 0
    for match in pattern.finditer(main_html):
        if match.start() > cursor:
            parts.append({"type": "html", "html": main_html[cursor:match.start()]})
        try:
            props = json.loads(match.group(2) or "{}")
        except json.JSONDecodeError:
            props = {}
        parts.append({"type": "component", "name": match.group(1), "props": props})
        cursor = match.end()
    if cursor < len(main_html):
        parts.append({"type": "html", "html": main_html[cursor:]})
    return parts or [{"type": "html", "html": main_html}]


def _prop_attr(key: str, value: str) -> str:
    escaped = astro_string(value)
    return f'{key}={{`{escaped}`}}'


def page_file(
    *,
    title: str,
    description: str,
    lang: str,
    main_html: str,
    layout_import: str = "../layouts/BaseLayout.astro",
    header_import: str = "../components/Header.astro",
    footer_import: str = "../components/Footer.astro",
    extras: list[dict] | None = None,
) -> str:
    extras = extras or []
    import_lines = [
        f"import BaseLayout from '{layout_import}';\n",
        f"import Header from '{header_import}';\n",
        f"import Footer from '{footer_import}';\n",
    ]
    for row in extras:
        import_lines.append(f"import {row['name']} from '{row['import']}';\n")
    parts = main_parts(main_html) if extras else [{"type": "html", "html": main_html}]
    body_chunks: list[str] = []
    html_i = 0
    front: list[str] = [
        "---\n",
        *import_lines,
        f"const title = `{astro_string(title)}`;\n",
        f"const description = `{astro_string(description)}`;\n",
        f"const lang = `{astro_string(lang or 'en')}`;\n",
    ]
    for part in parts:
        if part["type"] == "html":
            key = f"main{html_i}"
            html_i += 1
            front.append(f"const {key} = `{astro_string(part['html'])}`;\n")
            body_chunks.append(f"  <Fragment set:html={{{key}}} />\n")
            continue
        attrs = "".join(f" {_prop_attr(key, value)}" for key, value in (part.get("props") or {}).items() if value)
        body_chunks.append(f"  <{part['name']}{attrs} />\n")
    front.append("---\n")
    return (
        "".join(front)
        + '<BaseLayout title={title} description={description} lang={lang}>\n'
        + "  <Header />\n"
        + "".join(body_chunks)
        + "  <Footer />\n"
        + "</BaseLayout>\n"
    )


def paper_backed_names(root: Path) -> set[str]:
    names = set(PAPER_TOKENS)
    names.update(library_component_names(root))
    names.update(capture_component_names(root))
    return {name for name in names if name}


def inventory_components(root: Path) -> dict:
    """Union Paper tokens, Capture Tool names, comments, and signed HTML."""
    paper = paper_backed_names(root)
    nominations = comment_nominations(root)
    nominated = {row["name"] for row in nominations}
    nominated.update(paper)
    pages = now_pages(root)
    grouped: dict[str, dict] = {}
    for page in pages:
        html = (root / page["ship"]).read_text(encoding="utf-8", errors="replace")
        for hit in discover_page_candidates(html, nominated=nominated):
            key = hit["name"]
            bucket = grouped.setdefault(key, {
                "name": key,
                "kind": hit.get("kind") or "component",
                "html": hit.get("html") or "",
                "sources": [],
                "uses": 0,
                "pages": [],
                "tag": hit.get("tag") or "",
            })
            bucket["uses"] += 1
            if page["slug"] not in bucket["pages"]:
                bucket["pages"].append(page["slug"])
            for source in hit.get("sources") or []:
                if source not in bucket["sources"]:
                    bucket["sources"].append(source)
            if not bucket["html"]:
                bucket["html"] = hit.get("html") or ""
    inventory = []
    skipped = []
    paper_l = {name.lower() for name in paper} | {pascal_name(name).lower() for name in paper}
    nominated_l = {name.lower() for name in nominated} | {pascal_name(name).lower() for name in nominated}
    for item in grouped.values():
        extract, reason = should_extract(
            item,
            paper_names=paper_l,
            nominated=nominated_l,
            uses=item["uses"],
        )
        props = props_from_element(item["html"]) if item["kind"] == "button" else None
        row = {
            **item,
            "extract": extract,
            "reason": reason,
            "mode": "props" if props else "fragment",
        }
        if extract:
            inventory.append(row)
        else:
            skipped.append({**row, "reason": reason})
    inventory.sort(key=lambda row: (0 if row["name"] in {"Header", "Footer"} else 1, row["name"]))
    return {
        "inventory": inventory,
        "skipped": skipped,
        "paper": sorted(paper),
        "nominated": sorted({pascal_name(name) or name for name in nominated}),
        "commentSources": nominations,
    }


def interior_slugs(root: Path) -> list[str]:
    rebuild = root / "rebuild"
    if not rebuild.is_dir():
        return []
    slugs = []
    for path in sorted(rebuild.glob("*.html")):
        name = path.name
        if name in SKIP_SHIP or name.endswith(SKIP_SUFFIX) or name == "index-polish.html":
            continue
        slugs.append(path.stem)
    return slugs
