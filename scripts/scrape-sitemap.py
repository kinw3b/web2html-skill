#!/usr/bin/env python3
"""4.1 — list extra source routes for optional Phase 4.

Reads the 1.1 origin, fetches sitemap.xml + robots.txt Sitemap: lines, walks
sitemapindex, and writes qa/phase-4-sitemap.json. Homepage `/` stays out.
No sitemap: crawl same-origin hrefs from source-site/index.html.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

UA = "web2html-phase4/2.10.13"
TIMEOUT = 20
DEFAULT_CAP = 40
ASSET_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf",
    ".woff", ".woff2", ".ttf", ".css", ".js", ".map", ".xml", ".json",
    ".mp4", ".webm", ".zip",
}
DROP_PREFIXES = ("/cdn-cgi", "/404", "/not-found")
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def origin_of(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def normalize_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def slug_from_path(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "home"
    slug = "-".join(parts).lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
    return slug or "page"


def paper_name_from_path(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "Home"
    return " / ".join(part.replace("-", " ").replace("_", " ").title() for part in parts)


def is_dropped_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    lower = path.lower()
    if any(lower.startswith(prefix) for prefix in DROP_PREFIXES):
        return True
    ext = Path(path).suffix.lower()
    return ext in ASSET_EXT


def same_origin(url: str, origin: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    return origin_of(url) == origin


def loc_texts(xml_text: str, tag: str) -> list[str]:
    root = ET.fromstring(xml_text)
    found: list[str] = []
    for node in root.iter():
        local = node.tag.split("}", 1)[-1]
        if local == tag and node.text:
            found.append(node.text.strip())
    return found


def parse_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls)."""
    urls = loc_texts(xml_text, "loc")
    root = ET.fromstring(xml_text)
    local = root.tag.split("}", 1)[-1]
    if local == "sitemapindex":
        return [], urls
    return urls, []


def parse_robots(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            found.append(line.split(":", 1)[1].strip())
    return found


class HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.hrefs.append(value)


def crawl_homepage_links(html: str, base_url: str) -> list[str]:
    parser = HrefParser()
    parser.feed(html)
    origin = origin_of(base_url)
    out: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, href.split("#", 1)[0])
        if not same_origin(absolute, origin):
            continue
        path = normalize_path(absolute)
        if is_dropped_path(path) or path in seen:
            continue
        seen.add(path)
        out.append(urlunparse(urlparse(absolute)._replace(path=path, query="", fragment="")))
    return out


def collect_urls(origin: str, fetch_fn=fetch) -> tuple[list[str], str]:
    seeds = [f"{origin}/sitemap.xml"]
    try:
        seeds.extend(parse_robots(fetch_fn(f"{origin}/robots.txt")))
    except (HTTPError, URLError, TimeoutError, OSError):
        pass
    pages: list[str] = []
    seen_sitemaps: set[str] = set()
    queue = [url for url in seeds if url]
    while queue:
        sm_url = queue.pop(0)
        if sm_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sm_url)
        try:
            body = fetch_fn(sm_url)
        except (HTTPError, URLError, TimeoutError, OSError):
            continue
        locs, children = parse_sitemap_xml(body)
        pages.extend(locs)
        queue.extend(children)
    return pages, "sitemap" if pages else "none"


def page_record(url: str, origin: str) -> dict | None:
    if not same_origin(url, origin):
        return None
    path = normalize_path(url)
    if is_dropped_path(path):
        return None
    clean = urlunparse(urlparse(url)._replace(path=path, query="", fragment=""))
    return {
        "url": clean,
        "path": path,
        "slug": slug_from_path(path),
        "paperName": paper_name_from_path(path),
    }


def dedupe_records(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = row["path"]
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


# A parent path with this many (or more) children is a dynamic detail template
# (blog posts, case studies): same layout, different slugs. Phase 4 imports
# ONE sample per template, never every slug.
TEMPLATE_MIN_CHILDREN = 3


def collapse_templates(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collapse near-duplicate detail pages to one sample per parent template.

    Depth>=2 pages are grouped by parent path. A parent with
    TEMPLATE_MIN_CHILDREN+ children keeps only its first child, stamped as the
    template sample; the rest are returned as collapsed overflow. Distinct
    top-level templates (depth-1 pages) always survive.
    """
    children: dict[str, list[dict]] = {}
    for row in rows:
        parts = [p for p in row["path"].split("/") if p]
        if len(parts) >= 2:
            children.setdefault("/" + "/".join(parts[:-1]), []).append(row)
    template_parents = {
        parent for parent, kids in children.items() if len(kids) >= TEMPLATE_MIN_CHILDREN
    }
    kept: list[dict] = []
    collapsed: list[dict] = []
    sampled: set[str] = set()
    for row in rows:
        parts = [p for p in row["path"].split("/") if p]
        parent = "/" + "/".join(parts[:-1]) if len(parts) >= 2 else ""
        if parent in template_parents:
            if parent in sampled:
                collapsed.append({**row, "template": f"{parent}/*"})
                continue
            sampled.add(parent)
            kept.append({**row, "template": f"{parent}/*", "templateSample": True})
        else:
            kept.append(row)
    return kept, collapsed


def source_url(root: Path) -> str:
    pages = root / "source-site" / "pages.json"
    if pages.is_file():
        try:
            payload = json.loads(pages.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, list) and payload and payload[0].get("url"):
            return str(payload[0]["url"])
        if isinstance(payload, dict) and payload.get("url"):
            return str(payload["url"])
    paper = root / "qa" / "paper-file.json"
    if paper.is_file():
        try:
            payload = json.loads(paper.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if payload.get("url"):
            return str(payload["url"])
    raise SystemExit("FAIL: no source URL in source-site/pages.json or qa/paper-file.json")


def merge_pages_json(root: Path, extras: list[dict]) -> None:
    path = root / "source-site" / "pages.json"
    existing: list[dict] = []
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = []
    by_path = {str(row.get("path") or "/"): row for row in existing if isinstance(row, dict)}
    for row in extras:
        by_path.setdefault(row["path"], {
            "path": row["path"],
            "url": row["url"],
            "file": None,
            "title": row["paperName"],
            "phase": "4",
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(by_path.values()), indent=2) + "\n", encoding="utf-8")


def run(root: Path, cap: int = DEFAULT_CAP, fetch_fn=None) -> dict:
    url = source_url(root)
    origin = origin_of(url)
    getter = fetch_fn or fetch
    raw_urls, source = collect_urls(origin, getter)
    if source == "none":
        home = root / "source-site" / "index.html"
        if home.is_file():
            raw_urls = crawl_homepage_links(home.read_text(encoding="utf-8", errors="replace"), url)
            source = "crawl"
    records = dedupe_records([row for row in (page_record(u, origin) for u in raw_urls) if row])
    records, collapsed = collapse_templates(records)
    kept = records[:cap]
    overflow = records[cap:]
    receipt = {
        "ok": True,
        "origin": origin,
        "source": source,
        "cap": cap,
        "pages": kept,
        "overflow": overflow,
        "collapsedTemplates": collapsed,
    }
    qa = root / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "phase-4-sitemap.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    merge_pages_json(root, kept)
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP)
    args = ap.parse_args(argv)
    receipt = run(args.root.resolve(), cap=max(1, args.cap))
    print(json.dumps({
        "ok": True,
        "source": receipt["source"],
        "pages": len(receipt["pages"]),
        "overflow": len(receipt["overflow"]),
        "out": "qa/phase-4-sitemap.json",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
