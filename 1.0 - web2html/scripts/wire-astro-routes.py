#!/usr/bin/env python3
"""5.5 — wire Astro routes, interior SEO, then `astro build`.

1. Routes. Sitemap paths and nav / footer labels → Astro routes across
   astro/src (Header, Footer, pages). Home → `/`. `/about` → `/about/`.
   Leftover `.html` hrefs → routes. External / mailto / tel stay `#`.
2. SEO. Per-interior scrape-only title / description / lang / canonical /
   og:image into that page's frontmatter (BaseLayout props). The homepage
   takes its own qa/scrape-meta.json. Never merge homepage meta onto an
   interior. No heading / section retag — structure is frozen at 5.2.
3. Build. `astro build`, then relativize astro/dist for file://.

  python3 wire-astro-routes.py /path/to/project
  python3 wire-astro-routes.py /path/to/project --skip-build

Receipt qa/phase-5-links.json (+ qa/phase-5-semantics/{slug}.json,
qa/phase-5-build.log). The agent never starts `astro dev`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from astro_build import build, write_build_log
from html_to_astro import astro_href, astro_string, now_pages
from interior_seo import (
    default_fetch,
    homepage_meta,
    load_sitemap,
    page_rows,
    rewrite_anchor_hrefs,
    route_map,
    scrape_meta_for,
)

HTML_HREF_RE = re.compile(
    r"""\b(href|src|action)\s*=\s*(['"])([^'"]+\.html(?:#[^'"]*)?)\2""",
    re.I,
)
HTML_LEFT_RE = re.compile(
    r"""(?:href|src|action)\s*=\s*['"][^'"]+\.html""",
    re.I,
)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
BASELAYOUT_OPEN_RE = re.compile(r"<BaseLayout\b([^>]*)>")
# Astro frontmatter const name ← scrape key
SEO_PROPS = (
    ("title", "title"),
    ("description", "description"),
    ("lang", "lang"),
    ("canonical", "canonical"),
    ("ogImage", "og_image"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def rewrite_html_hrefs(text: str) -> tuple[str, int]:
    """`about.html` → `/about/` in attributes and converter template literals."""

    def repl(match: re.Match[str]) -> str:
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{astro_href(value)}{quote}"

    next_text, count = HTML_HREF_RE.subn(repl, text)

    def lit_repl(match: re.Match[str]) -> str:
        return astro_href(match.group(0))

    next_text, lit_count = re.subn(
        r"(?<![\\w/])[./]*(?:index|[A-Za-z0-9_-]+)\.html(?:#[A-Za-z0-9_-]+)?",
        lit_repl,
        next_text,
    )
    return next_text, count + lit_count


def rewrite_file(path: Path, mapping: dict[str, str]) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    next_text, n_html = rewrite_html_hrefs(text)
    next_text, n_map = rewrite_anchor_hrefs(next_text, mapping)
    if next_text != text:
        path.write_text(next_text, encoding="utf-8")
    return n_html + n_map


def leftover_html_hrefs(root: Path) -> list[str]:
    hits: list[str] = []
    src = root / "astro" / "src"
    if not src.is_dir():
        return ["missing astro/src"]
    for path in sorted(src.rglob("*.astro")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in HTML_LEFT_RE.finditer(text):
            hits.append(f"{path.relative_to(root)}:{match.group(0)}")
    return hits


def apply_frontmatter_seo(text: str, meta: dict[str, str]) -> tuple[str, list[str]]:
    """Set `const title/description/lang/canonical/ogImage` and pass them to BaseLayout.

    Only fills from `meta`. Never invents. Returns (text, applied prop names).
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, []
    front = match.group(1)
    applied: list[str] = []
    for prop, key in SEO_PROPS:
        value = (meta.get(key) or "").strip()
        if not value:
            continue
        line = f"const {prop} = `{astro_string(value)}`;"
        pattern = re.compile(rf"^const {prop}\s*=.*?;\s*$", re.M)
        if pattern.search(front):
            front = pattern.sub(line, front, count=1)
        else:
            front = front.rstrip("\n") + "\n" + line
        applied.append(prop)
    text = f"---\n{front}\n---\n" + text[match.end():]

    def open_repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        for prop in applied:
            if re.search(rf"\b{prop}=", attrs) is None:
                attrs += f" {prop}={{{prop}}}"
        return f"<BaseLayout{attrs}>"

    text = BASELAYOUT_OPEN_RE.sub(open_repl, text, count=1)
    return text, applied


def wire(root: Path, *, skip_build: bool = False, fetch_fn=default_fetch) -> dict:
    root = root.resolve()
    astro = root / "astro"
    if not (astro / "package.json").is_file():
        raise FileNotFoundError("need astro/package.json from 5.1")
    mapping = route_map(load_sitemap(root))
    rewritten = 0
    for path in sorted((astro / "src").rglob("*.astro")):
        rewritten += rewrite_file(path, mapping)
    pages = now_pages(root)
    rows = page_rows(root)
    errors: list[str] = []
    routes = []
    seo_rows = []
    for row in pages:
        dest = root / str(row.get("astro") or f"astro/src/pages/{row['slug']}.astro")
        if not dest.is_file():
            errors.append(f"missing {dest.relative_to(root)}")
            continue
        slug = row["slug"]
        if slug == "index":
            meta = homepage_meta(root)
        else:
            meta = scrape_meta_for(root, slug, rows.get(slug) or {}, fetch_fn)
        text = dest.read_text(encoding="utf-8", errors="replace")
        next_text, applied = apply_frontmatter_seo(text, meta)
        if next_text != text:
            dest.write_text(next_text, encoding="utf-8")
        receipt_dir = root / "qa" / "phase-5-semantics"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        seo_receipt = {"slug": slug, "astro": str(dest.relative_to(root)), "meta": meta, "applied": applied}
        (receipt_dir / f"{slug}.json").write_text(json.dumps(seo_receipt, indent=2) + "\n", encoding="utf-8")
        seo_rows.append(seo_receipt)
        routes.append({"slug": slug, "route": row["route"], "astro": str(dest.relative_to(root))})
    leftovers = leftover_html_hrefs(root)
    if leftovers:
        errors.extend(f"html href left: {hit}" for hit in leftovers[:8])
    built = False
    log = ""
    relativized: list[str] = []
    if not skip_build and not errors:
        result = build(root)
        built = result["built"]
        log = result["log"]
        relativized = result["relativized"]
        errors.extend(result["errors"])
    receipt = {
        "generatedFrom": "web2html/phase-5-links",
        "ok": bool(routes) and not errors,
        "map": mapping,
        "rewritten": rewritten,
        "routes": routes,
        "seo": seo_rows,
        "built": built,
        "skipBuild": skip_build,
        "relativized": relativized,
        "errors": errors,
        "updated": _now_iso(),
    }
    log_rel = write_build_log(root, log)
    if log_rel:
        receipt["buildLog"] = log_rel
    dest = root / "qa" / "phase-5-links.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args(argv)
    try:
        receipt = wire(args.root.resolve(), skip_build=args.skip_build)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(json.dumps({
        "ok": True,
        "routes": len(receipt["routes"]),
        "seo": len(receipt["seo"]),
        "built": receipt["built"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
