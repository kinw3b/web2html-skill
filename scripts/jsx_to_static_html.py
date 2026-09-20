#!/usr/bin/env python3
"""Convert Paper get_jsx JSON / JSX into file:// HTML.

Paper `get_jsx` (format=inline-styles) returns JSON `{ "jsx": "..." }`.
That JSX uses `style={{ camelCase: 'value' }}` and self-closing `<div />`.
A browser treats those divs as unclosed tags, so the dump paints blank.

  python3 jsx_to_static_html.py dump.json -o rebuild/index-raw.html --wrap
  python3 jsx_to_static_html.py dump.json --check -o out.html

Idempotent on already-converted HTML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CAMEL_SPECIAL = {
    "MozOsxFontSmoothing": "-moz-osx-font-smoothing",
    "WebkitFontSmoothing": "-webkit-font-smoothing",
    "WebkitTextSizeAdjust": "-webkit-text-size-adjust",
    "msOverflowStyle": "-ms-overflow-style",
}

SVG_ATTR = {
    "strokeWidth": "stroke-width",
    "strokeLinecap": "stroke-linecap",
    "strokeLinejoin": "stroke-linejoin",
    "strokeDasharray": "stroke-dasharray",
    "strokeMiterlimit": "stroke-miterlimit",
    "fillRule": "fill-rule",
    "clipRule": "clip-rule",
    "clipPath": "clip-path",
    "fontSize": "font-size",
    "fontFamily": "font-family",
    "fontWeight": "font-weight",
    "viewBox": "viewBox",
    "xmlns": "xmlns",
    "points": "points",
    "fill": "fill",
    "stroke": "stroke",
    "width": "width",
    "height": "height",
    "x": "x",
    "y": "y",
    "cx": "cx",
    "cy": "cy",
    "r": "r",
    "d": "d",
    "x1": "x1",
    "x2": "x2",
    "y1": "y1",
    "y2": "y2",
}

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
SVG_VOID = {
    "path",
    "line",
    "polyline",
    "polygon",
    "circle",
    "ellipse",
    "rect",
    "stop",
    "use",
}
COMMENT_RE = re.compile(r"^<!--.*?-->\s*", re.S)
SELF_CLOSE_DIV_RE = re.compile(r"<div\b[^>]*/>", re.I)
JSX_STYLE_RE = re.compile(r"style=\{\{")
JSON_JSX_RE = re.compile(r'"jsx"\s*:')


def camel_to_css(key: str) -> str:
    if key in CAMEL_SPECIAL:
        return CAMEL_SPECIAL[key]
    if key.startswith("--"):
        return key
    return re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), key)


def parse_style_object(inner: str) -> str:
    decls: list[str] = []
    i, n = 0, len(inner)
    while i < n:
        while i < n and inner[i] in " \n\t\r,":
            i += 1
        if i >= n:
            break
        m = re.match(r"([A-Za-z0-9_\-]+)\s*:", inner[i:])
        if not m:
            break
        key = m.group(1)
        i += m.end()
        while i < n and inner[i] in " \t":
            i += 1
        if i >= n:
            break
        if inner[i] in "'\"":
            q = inner[i]
            i += 1
            start = i
            while i < n and inner[i] != q:
                if inner[i] == "\\":
                    i = min(i + 2, n)
                else:
                    i += 1
            val = inner[start:i].replace("\\'", "'").replace('\\"', '"')
            if i < n and inner[i] == q:
                i += 1
        else:
            start = i
            while i < n and inner[i] not in ",}":
                i += 1
            val = inner[start:i].strip()
        decls.append(f"{camel_to_css(key)}: {val}")
    return "; ".join(decls)


def convert_jsx(jsx: str) -> str:
    html = jsx.strip()
    if html.startswith("("):
        html = html[1:]
    if html.endswith(")"):
        html = html[:-1]
    html = html.strip()

    def repl_style(m: re.Match) -> str:
        return 'style="' + parse_style_object(m.group(1)) + '"'

    html = re.sub(r"style=\{\{(.*?)\}\}", repl_style, html, flags=re.S)

    def repl_attr(m: re.Match) -> str:
        name, val = m.group(1), m.group(2)
        if name == "className":
            html_name = "class"
        elif name[:1].islower() and any(c.isupper() for c in name):
            html_name = SVG_ATTR.get(name, camel_to_css(name))
        else:
            html_name = SVG_ATTR.get(name, name)
        return f'{html_name}="{val}"'

    html = re.sub(r'\b([A-Za-z][A-Za-z0-9]*)="([^"]*)"', repl_attr, html)

    def repl_void(m: re.Match) -> str:
        tag = m.group(1).lower()
        rest = m.group(2)
        if tag in VOID or tag in SVG_VOID:
            return f"<{m.group(1)}{rest} />"
        return f"<{m.group(1)}{rest}></{m.group(1)}>"

    html = re.sub(r"<([A-Za-z][A-Za-z0-9]*)([^>]*?)/>", repl_void, html)
    return html


def _looks_like_html(text: str) -> bool:
    head = text.lstrip()[:200].lower()
    return head.startswith("<!doctype") or head.startswith("<html") or (
        head.startswith("<div") and "style={{" not in text[:500]
    )


def extract_jsx(raw: str) -> tuple[str, str]:
    """Return (kind, markup) where kind is html | jsx."""
    text = COMMENT_RE.sub("", raw.strip(), count=1).strip()
    if not text:
        raise ValueError("empty get_jsx dump")
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        if isinstance(payload, dict):
            jsx = payload.get("jsx") or payload.get("html") or payload.get("code")
            if not jsx and isinstance(payload.get("result"), dict):
                inner = payload["result"]
                jsx = inner.get("jsx") or inner.get("html")
            if jsx:
                return "jsx", str(jsx)
        raise ValueError("JSON dump has no jsx/html field")
    if "style={{" in text or text.lstrip().startswith("("):
        return "jsx", text
    if _looks_like_html(text):
        return "html", text
    return "jsx", text


def wrap_html(
    body: str,
    *,
    title: str = "Paper dump · home-desktop",
    tokens_href: str = "css/tokens.css",
    fonts_href: str | None = None,
) -> str:
    stripped = body.lstrip()
    if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
        html = body
        if tokens_href and "tokens.css" not in html:
            html = html.replace(
                "</head>",
                f'  <link rel="stylesheet" href="{tokens_href}" />\n</head>',
                1,
            )
        if fonts_href and "fonts.css" not in html:
            if re.search(r"tokens\.css", html, re.I):
                html = re.sub(
                    r'(<link[^>]+tokens\.css[^>]*>)',
                    rf'\1\n  <link rel="stylesheet" href="{fonts_href}" />',
                    html,
                    count=1,
                    flags=re.I,
                )
            else:
                html = html.replace(
                    "</head>",
                    f'  <link rel="stylesheet" href="{fonts_href}" />\n</head>',
                    1,
                )
        if "data-export=" not in html[:800]:
            html = re.sub(
                r"<html\b",
                '<html data-export="get_jsx-inline-styles"',
                html,
                count=1,
                flags=re.I,
            )
        return html
    fonts_link = (
        f'  <link rel="stylesheet" href="{fonts_href}" />\n' if fonts_href else ""
    )
    return (
        "<!doctype html>\n"
        '<html lang="en" data-export="get_jsx-inline-styles">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f"  <title>{title}</title>\n"
        f'  <link rel="stylesheet" href="{tokens_href}" />\n'
        f"{fonts_link}"
        "  <style>\n"
        "    html, body { margin: 0; background: var(--color-surface, #fff); }\n"
        "    body { font-synthesis: none; -webkit-font-smoothing: antialiased; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def conversion_errors(html: str) -> list[str]:
    errors: list[str] = []
    if JSX_STYLE_RE.search(html):
        errors.append("leftover JSX style={{}}")
    if SELF_CLOSE_DIV_RE.search(html):
        errors.append("self-closing <div /> (browsers treat these as unclosed)")
    if JSON_JSX_RE.search(html[:1500]) and not html.lstrip().lower().startswith("<"):
        errors.append("still a JSON payload, not HTML")
    return errors


def to_static_html(
    raw: str,
    *,
    wrap: bool = True,
    title: str = "Paper dump · home-desktop",
    tokens_href: str = "css/tokens.css",
    fonts_href: str | None = None,
) -> str:
    kind, markup = extract_jsx(raw)
    body = convert_jsx(markup) if kind == "jsx" else markup
    html = wrap_html(body, title=title, tokens_href=tokens_href, fonts_href=fonts_href) if wrap else body
    if not html.endswith("\n"):
        html += "\n"
    errors = conversion_errors(html)
    if errors:
        raise ValueError("; ".join(errors))
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="get_jsx JSON, JSX, or HTML")
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--wrap", action="store_true", default=True)
    ap.add_argument("--no-wrap", action="store_false", dest="wrap")
    ap.add_argument("--check", action="store_true", help="fail if JSX leftovers remain")
    ap.add_argument("--tokens", default="css/tokens.css")
    ap.add_argument("--fonts", default="")
    ap.add_argument("--title", default="Paper dump · home-desktop")
    args = ap.parse_args(argv)
    raw = args.input.read_text(encoding="utf-8")
    try:
        html = to_static_html(
            raw,
            wrap=args.wrap,
            title=args.title,
            tokens_href=args.tokens,
            fonts_href=args.fonts or None,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.check:
        leftover = conversion_errors(html)
        if leftover:
            print("FAIL: " + "; ".join(leftover), file=sys.stderr)
            return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
        print(f"wrote {args.output} bytes {args.output.stat().st_size}")
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
