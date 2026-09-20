#!/usr/bin/env python3
"""2.2.b: leftover Paper page bands that are still <div> → <section>.

retag_from_layer_names only rewrites existing <section> wrappers
(header/nav/footer). A geometry-lock dump that left
`<div data-paper-section="features">` never gets a real landmark.
This promote is tag-only: keep attrs, inner frames, and geometry.

  from section_promote import promote_sections, section_gate_errors
  python3 section_promote.py rebuild/index.html -o rebuild/index.html

Chrome slugs (nav / header / footer / main) become those landmarks,
not <section>. Inner frames without a Paper section name stay <div>.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_layer_names import LANDMARK_SLUGS, parse_paper_name

_OPEN_DIV = re.compile(r"<div\b([^>]*)>", re.I)
_PAPER_SEC = re.compile(r"""\bdata-paper-section=["']([^"']+)["']""", re.I)
_ID = re.compile(r"""\bid=["']([^"']+)["']""", re.I)
_NAME = re.compile(
    r"""(?:data-name|layer-name|data-paper-name)\s*=\s*["']([^"']+)["']""",
    re.I,
)
_CLOSE_DIV = re.compile(r"<div\b|</div>", re.I)

# Named marketing bands. Used when the only hint is id= (no data-paper-section).
CONTENT_SLUGS = {
    "hero",
    "hero-section",
    "features",
    "feature",
    "about",
    "about-section",
    "testimonials",
    "testimonial",
    "article",
    "article-section",
    "cta",
    "cta-section",
    "pricing",
    "pricing-section",
    "services",
    "service",
    "blog",
    "contact",
    "faq",
    "team",
    "gallery",
    "partners",
    "clients",
    "stats",
    "logos",
    "how-it-works",
    "content-section",
    "ready-to-take-your-business",
}

CHROME_PREFIX = re.compile(r"^(header|nav|navbar|navigation|footer|main)(--|-2|-\d+)?$")


def is_chrome_slug(slug: str) -> bool:
    s = (slug or "").strip().lower()
    if not s:
        return False
    if s in LANDMARK_SLUGS:
        return True
    if s in {"header-2", "navbar", "navigation"}:
        return True
    return bool(CHROME_PREFIX.match(s))


def is_content_band(slug: str) -> bool:
    """Named page band (hero / features / …), not nav/header/footer."""
    s = (slug or "").strip().lower()
    if not s or is_chrome_slug(s):
        return False
    if s in CONTENT_SLUGS:
        return True
    if s.endswith("-section") or s.endswith("_section"):
        return True
    stem = s.split("-")[0]
    if stem in CONTENT_SLUGS:
        return True
    return True


def _slug_from_attrs(attrs: str) -> str | None:
    paper = _PAPER_SEC.search(attrs)
    if paper:
        return paper.group(1).strip()
    named = _NAME.search(attrs)
    if named:
        parsed = parse_paper_name(named.group(1))
        rest = parsed["rest"]
        if parsed["nn"] or rest.lower().endswith("section") or rest.lower().endswith(" section"):
            return parsed["slug"]
    ident = _ID.search(attrs)
    if ident:
        raw = ident.group(1).strip()
        parsed = parse_paper_name(raw)
        if parsed["nn"]:
            return parsed["slug"]
        slug = parsed["slug"] or raw
        if slug in CONTENT_SLUGS or slug.endswith("-section") or slug.endswith("_section"):
            return slug
    return None


def _target_tag(slug: str) -> str:
    if not is_chrome_slug(slug):
        return "section"
    if slug in LANDMARK_SLUGS:
        return LANDMARK_SLUGS[slug]
    stem = slug.split("-")[0]
    if stem in LANDMARK_SLUGS:
        return LANDMARK_SLUGS[stem]
    if slug.startswith("header"):
        return "header"
    if slug.startswith("nav"):
        return "nav"
    if slug.startswith("footer"):
        return "footer"
    return "main"


def _should_promote(attrs: str) -> str | None:
    """Return the landmark/section tag, or None if this div stays a div."""
    slug = _slug_from_attrs(attrs)
    if not slug:
        return None
    if _PAPER_SEC.search(attrs) or _NAME.search(attrs):
        return _target_tag(slug)
    # id-only: only known content / chrome slugs, never inner frames.
    if is_chrome_slug(slug) or slug in CONTENT_SLUGS or slug.endswith("-section") or slug.endswith("_section"):
        return _target_tag(slug)
    return None


def _find_matching_close(html: str, after_open: int) -> tuple[int, int] | None:
    depth = 1
    for m in _CLOSE_DIV.finditer(html, after_open):
        token = m.group(0)
        if token.lower().startswith("</"):
            depth -= 1
            if depth == 0:
                return (m.start(), m.end())
        else:
            depth += 1
    return None


def promote_sections(html: str) -> str:
    """Retag leftover named <div> page bands. No-op when already <section>."""
    hits: list[tuple[int, int, str, str]] = []
    for m in _OPEN_DIV.finditer(html):
        tag = _should_promote(m.group(1))
        if tag:
            hits.append((m.start(), m.end(), m.group(1), tag))
    if not hits:
        return html
    out = html
    for start, end, attrs, tag in reversed(hits):
        close = _find_matching_close(out, end)
        if close is None:
            continue
        out = (
            f"{out[:start]}<{tag}{attrs}>{out[end:close[0]]}</{tag}>{out[close[1]:]}"
        )
    return out


def section_gate_errors(html: str) -> list[str]:
    """FAIL rows: a data-paper-section content band is still a <div>."""
    errors: list[str] = []
    token = re.compile(
        r"<(div|section|header|nav|footer|main|article|aside)\b([^>]*)>",
        re.I,
    )
    for m in token.finditer(html):
        tag = m.group(1).lower()
        attrs = m.group(2)
        paper = _PAPER_SEC.search(attrs)
        if not paper:
            continue
        slug = paper.group(1).strip()
        if not is_content_band(slug):
            continue
        if tag == "div":
            errors.append(
                f'data-paper-section="{slug}" is still a <div> — promote to <section>'
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args(argv)
    html = args.input.read_text(encoding="utf-8")
    out = promote_sections(html)
    dest = args.output or args.input
    if out != html:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        print(f"wrote {dest} (promoted leftover Paper bands)")
    else:
        if args.output and args.output != args.input:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out, encoding="utf-8")
        print(f"OK no leftover Paper <div> bands in {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
