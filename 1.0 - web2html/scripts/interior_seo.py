#!/usr/bin/env python3
"""Shared 5.5 helpers — sitemap → Astro route map and per-page scrape-only SEO.

Used by wire-astro-routes.py. Maps qa/phase-4-sitemap.json paths and nav /
footer labels to Astro routes (`/about/`; home is `/`). External / mailto /
tel stay `#`. Scrapes each interior's OWN live page (or its 4.x local copy)
for title / description / OG / canonical / lang. Never merges the homepage
qa/scrape-meta.json onto an interior.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from semantics_pass import _meta_from_html

HOME = "/"
A_RE = re.compile(
    r"<a\b([^>]*?)\bhref=(['\"])(.*?)\2([^>]*)>(.*?)</a>",
    re.I | re.S,
)
LOGO_RE = re.compile(r"""class=(['"])[^'"]*\b(logo|brand|site-logo|wordmark)\b""", re.I)
UA = "Mozilla/5.0 web2html-phase5/2.20.0"
TIMEOUT = 12
LOCAL_SCRAPE = (
    "source-site/{slug}.html",
    "capture/{slug}-desktop/captured.html",
    "capture/{slug}-desktop/page.html",
)


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_sitemap(root: Path) -> list[dict]:
    src = root / "qa" / "phase-4-sitemap.json"
    if not src.is_file():
        raise FileNotFoundError("need qa/phase-4-sitemap.json")
    payload = load_json(src)
    rows = payload.get("pages") if isinstance(payload, dict) else []
    return [row for row in rows or [] if isinstance(row, dict)]


def load_phase4_pages(root: Path) -> list[dict]:
    payload = load_json(root / "qa" / "phase-4-pages.json")
    rows = payload.get("pages") if isinstance(payload, dict) else []
    return [row for row in rows or [] if isinstance(row, dict)]


def route_for(slug: str) -> str:
    clean = (slug or "").strip().strip("/").lower()
    return HOME if clean in {"", "home", "index"} else f"/{clean}/"


def route_map(rows: list[dict]) -> dict[str, str]:
    """Lower-cased slug / sitemap path / Paper name → Astro route."""
    mapping: dict[str, str] = {"": HOME, "/": HOME, "home": HOME, "index": HOME}
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        path = str(row.get("path") or "").strip() or f"/{slug}"
        if not slug or slug == "home":
            continue
        dest = route_for(slug)
        mapping[slug.lower()] = dest
        mapping[path.rstrip("/").lower() or f"/{slug}"] = dest
        name = str(row.get("paperName") or slug).strip().lower()
        if name:
            mapping[name] = dest
        # 4.1 collapses dynamic children to ONE sample per template; any other
        # child of that template (e.g. the source's own "Blog Details" link)
        # routes to the sample (Pitfall #248).
        template = str(row.get("template") or "").strip().lower()
        if template.endswith("/*"):
            mapping.setdefault(template, dest)
    return mapping


def _norm_path(raw: str) -> str:
    """'./about' / '../about/' / 'about.html' → '/about'; './' → '/'."""
    path = urlparse(raw).path or ""
    while path.startswith(("./", "../")):
        path = path[2:] if path.startswith("./") else path[3:]
    if path in {"", ".", ".."}:
        return "/"
    if path.endswith(".html"):
        path = path[:-5]
        if path.endswith("/index") or path == "index":
            path = path[: -len("index")]
    return "/" + path.strip("/")


def source_label_map(root: Path, mapping: dict[str, str]) -> dict[str, str]:
    """label → route from the SOURCE scrape's own internal links.

    The 2.2 rebuild replaces source hrefs with in-page anchors (#pricing-section,
    #footer) — label routing never fired on those, so the built chrome linked
    nowhere (Pitfall #248). The source scrape still knows that 'Pricing' goes
    to /pricing and 'Homepage 02' to /home-2. Only labels with ONE internal
    destination are kept; ambiguous labels ('Get Started Now') are dropped."""
    src = root / "source-site" / "index.html"
    if not src.is_file():
        return {}
    text = src.read_text(encoding="utf-8", errors="replace")
    seen: dict[str, set[str]] = {}
    for _before, _q, href, _after, inner in A_RE.findall(text):
        label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner or "")).strip().lower()
        label = re.sub(r"&[a-z#0-9]+;", " ", label).strip()
        if not label or len(label) > 60:
            continue
        dest = dest_for_href(href, mapping)
        if dest in (None, "#"):
            continue
        seen.setdefault(label, set()).add(dest)
    return {label: next(iter(dests)) for label, dests in seen.items() if len(dests) == 1}


def dest_for_href(href: str, mapping: dict[str, str]) -> str | None:
    """Route for an authored href, `#` for off-site, None when unknown."""
    raw = (href or "").strip()
    if raw in {"#", ""} or raw.startswith("#"):
        return None
    if raw.startswith(("mailto:", "tel:", "javascript:", "https://", "http://")):
        return "#"
    if raw == "/":
        return HOME
    if raw.startswith((".", "/")) or "/" in raw or raw.endswith(".html"):
        norm = _norm_path(raw)
        if norm == "/":
            return HOME
        key = norm.lower()
        if raw.startswith("/") and raw.endswith("/") and key.strip("/") in {k.strip("/") for k in mapping}:
            return None  # already a route
        if key in mapping:
            return mapping[key]
        if key.strip("/") in mapping:
            return mapping[key.strip("/")]
        for tpl, dest in mapping.items():
            if tpl.endswith("/*") and key.startswith(tpl[:-1]):
                return dest
    if raw.startswith("/") and raw.endswith("/") and raw.strip("/").lower() in {
        key.strip("/") for key in mapping
    }:
        return None  # already a route
    parsed = urlparse(raw)
    path = parsed.path or ""
    if path in {"", "/"} and not parsed.fragment:
        return HOME
    key = path.rstrip("/").lower()
    if key in mapping:
        return mapping[key]
    slug = key.rsplit("/", 1)[-1]
    if slug.endswith(".html"):
        slug = slug[:-5]
    if slug in mapping:
        return mapping[slug]
    return None


def dest_for_label(text: str, mapping: dict[str, str]) -> str | None:
    label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip().lower()
    if not label:
        return None
    if label in {"home", "homepage"}:
        return HOME
    return mapping.get(label)


def rewrite_anchor_hrefs(
    text: str, mapping: dict[str, str], labels: dict[str, str] | None = None
) -> tuple[str, int]:
    """Rewrite `<a href>` inside HTML or an .astro template literal.

    `labels` (source_label_map) routes a placeholder / in-page-anchor href by
    its visible label when the source linked that label to an internal page."""
    changed = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        before, quote, href, after, inner = match.groups()
        dest = dest_for_href(href, mapping)
        placeholder = href.strip() in {"#", ""} or href.strip().startswith("#")
        if dest is None and placeholder and labels:
            label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner or "")).strip().lower()
            dest = labels.get(label)
        if dest is None and placeholder and LOGO_RE.search(f"{before} {after}"):
            dest = HOME  # the brand mark links home on every page
        if dest is None and href.strip() in {"#", ""}:
            dest = dest_for_label(inner, mapping)
        if dest is None or dest == href:
            return match.group(0)
        changed += 1
        return f"<a{before}href={quote}{dest}{quote}{after}>{inner}</a>"

    return A_RE.sub(repl, text), changed


def default_fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def site_lang(root: Path) -> str:
    meta = load_json(root / "qa" / "scrape-meta.json")
    lang = str(meta.get("lang") or "").strip()
    if lang:
        return lang
    home = root / "source-site" / "index.html"
    if home.is_file():
        return str(_meta_from_html(home.read_text(encoding="utf-8", errors="replace")).get("lang") or "")
    return ""


def local_scrape_html(root: Path, slug: str) -> str:
    for rel in LOCAL_SCRAPE:
        path = root / rel.format(slug=slug)
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def page_rows(root: Path) -> dict[str, dict]:
    by_slug: dict[str, dict] = {}
    for row in load_sitemap(root) + load_phase4_pages(root):
        slug = str(row.get("slug") or "").strip()
        if not slug or slug == "home":
            continue
        by_slug[slug] = {**by_slug.get(slug, {}), **row}
    return by_slug


def scrape_meta_for(root: Path, slug: str, row: dict, fetch_fn) -> dict[str, str]:
    """Per-page scrape only. Never merge homepage title / description / OG."""
    meta: dict[str, str] = {}
    local = local_scrape_html(root, slug)
    if local:
        meta.update(_meta_from_html(local))
    url = str(row.get("url") or "").strip()
    if url and fetch_fn is not None:
        try:
            live = fetch_fn(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            live = ""
        if live:
            meta.update({k: v for k, v in _meta_from_html(live).items() if v})
    if url and not meta.get("canonical"):
        meta["canonical"] = url
    lang = site_lang(root)
    if lang:
        meta.setdefault("lang", lang)
    return {k: v for k, v in meta.items() if v}


def homepage_meta(root: Path) -> dict[str, str]:
    """Homepage meta from the 1.1 scrape receipt (for index.astro only)."""
    meta = load_json(root / "qa" / "scrape-meta.json")
    return {k: str(v) for k, v in meta.items() if isinstance(v, str) and v}
