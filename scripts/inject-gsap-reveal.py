#!/usr/bin/env python3
"""Copy vendored GSAP + inject sequential in-view reveals (Emil / 3.2).

  python3 inject-gsap-reveal.py rebuild/index-polish.html
  python3 inject-gsap-reveal.py rebuild/

Mandatory on every run. Do not skip because 1.4 did not record motion
(Pitfall #204). Writes polish only — skips rebuild/index.html when
index-polish.html is in the set (Pitfall #203).

Idempotent. Marks parent groups with data-reveal (Pitfall #1): section/article
hosts, section heads, mixed inners, and grids — not every heading leaf.
Runtime staggers each group's first children + siblings. Never class="reveal".
Never invents skip-links. file:// only — copies templates/vendor/gsap into
rebuild/js/vendor/. Never paper-asset://.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _hint(step: str, status: str = "active", root=None) -> None:
    try:
        import importlib.util
        p = Path(__file__).resolve().parent / "pipeline-progress.py"
        spec = importlib.util.spec_from_file_location("pipeline_progress", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if root is not None:
            mod.hint(step, status, root)
        else:
            mod.hint(step, status)
    except Exception:
        pass


TEMPLATES = HERE.parent / "templates"
VENDOR_SRC = TEMPLATES / "vendor" / "gsap"
RUNTIME_NAME = "gsap-reveal.js"
GSAP_NAME = "gsap.min.js"
ST_NAME = "ScrollTrigger.min.js"
SKIP_HTML_NAMES = {
    "polish-report.html",
    "design-system.html",
    "index-raw.html",
    "index-semantic.html",
}

SKIP_TAGS = {
    "nav",
    "svg",
    "path",
    "script",
    "style",
    "link",
    "meta",
    "noscript",
    "br",
    "hr",
    "img",
    "source",
    "track",
    "canvas",
}

SKIP_TOKEN = re.compile(
    r"(?:^|[\s_/#.-])"
    r"(?:nav|navbar|header|hero|skip-?link|qa-overlay|decorative)"
    r"(?:$|[\s_/#.-])",
    re.I,
)
SKIP_ATTR_NEEDLE = re.compile(
    r"""(?:\bid|class|role|href|data-[\w-]*)\s*=\s*(['"])(.*?)\1""",
    re.I | re.S,
)
OPEN_CANDIDATE = re.compile(
    r"<(section|article|footer|blockquote|figure)(\s[^>]*)?>",
    re.I,
)
OPEN_GROUP = re.compile(
    r"<(div|li|aside|ul|ol|header)(\s[^>]*(?:class|id)\s*=\s*['\"][^'\"]*"
    r"\b(?:card|feature|quote|testimonial|cta|band|pricing|plan|"
    r"grid|head|intro|inner|copy|banner)[^'\"]*['\"][^>]*)>",
    re.I,
)
SECTION_INNER = re.compile(r"\bsection-inner\b", re.I)
OPEN_ANY = re.compile(r"<([a-zA-Z][\w:-]*)(\s[^>]*)?>")
SKIP_LINK_OPEN = re.compile(
    r"<a\b[^>]*(?:class|id)\s*=\s*['\"][^'\"]*skip-?link[^'\"]*['\"][^>]*>",
    re.I,
)
HERO_OPEN = re.compile(
    r"<(section|article|div|header)\b[^>]*(?:class|id)\s*=\s*['\"][^'\"]*"
    r"\bhero\b[^'\"]*['\"][^>]*>",
    re.I,
)
NAV_OPEN = re.compile(r"<nav\b[^>]*>", re.I)
SITE_HEADER_OPEN = re.compile(
    r"<header\b(?=[^>]*\b(?:class|id)\s*=\s*['\"][^'\"]*"
    r"\b(?:site-header|site-nav|navbar|masthead|global-header)\b)[^>]*>",
    re.I,
)
DECORATIVE_OPEN = re.compile(
    r"<([a-zA-Z][\w:-]*)\b(?=[^>]*\b(?:data-decorative|id|class)\s*=)"
    r"[^>]*(?:data-decorative|(?:id|class)\s*=\s*['\"][^'\"]*qa-overlay)[^>]*>",
    re.I,
)


def _attr_blob(attrs: str) -> str:
    parts = []
    for m in SKIP_ATTR_NEEDLE.finditer(attrs or ""):
        parts.append(m.group(2))
    return " ".join(parts)


def _should_skip_open(tag: str, attrs: str) -> bool:
    tag_l = tag.lower()
    if tag_l in SKIP_TAGS:
        return True
    blob = _attr_blob(attrs or "")
    if SKIP_TOKEN.search(blob):
        return True
    if "data-decorative" in (attrs or ""):
        return True
    if "qa-overlay" in (attrs or "").lower():
        return True
    if tag_l == "a" and re.search(r"skip-?link", attrs or "", re.I):
        return True
    return False


VOID_TAGS = {
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


def _match_end(html: str, tag: str, after_open: int) -> int:
    if tag.lower() in VOID_TAGS:
        return after_open
    pat = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.I)
    depth = 1
    for m in pat.finditer(html, after_open):
        token = m.group(0)
        if token.startswith("</"):
            depth -= 1
            if depth == 0:
                return m.end()
        elif token.endswith("/>"):
            continue
        else:
            depth += 1
    return len(html)


def skip_ranges(html: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []

    def add_opens(pattern: re.Pattern[str], tag_from_match: bool = False) -> None:
        for m in pattern.finditer(html):
            if tag_from_match:
                tag = m.group(1)
            else:
                raw = m.group(0)
                tag = re.match(r"<([a-zA-Z][\w:-]*)", raw).group(1)
            ranges.append((m.start(), _match_end(html, tag, m.end())))

    add_opens(NAV_OPEN)
    add_opens(SITE_HEADER_OPEN)
    add_opens(HERO_OPEN)
    add_opens(DECORATIVE_OPEN, tag_from_match=True)
    for m in SKIP_LINK_OPEN.finditer(html):
        ranges.append((m.start(), _match_end(html, "a", m.end())))
    for m in re.finditer(r"<svg\b[^>]*>", html, re.I):
        ranges.append((m.start(), _match_end(html, "svg", m.end())))
    return ranges


def _inside(ranges: list[tuple[int, int]], index: int) -> bool:
    return any(start <= index < end for start, end in ranges)


def _with_data_reveal(open_tag: str) -> str:
    if re.search(r"\bdata-reveal\b", open_tag):
        return open_tag
    if open_tag.endswith("/>"):
        return open_tag[:-2] + " data-reveal/>"
    if open_tag.endswith(">"):
        return open_tag[:-1] + " data-reveal>"
    return open_tag


HEADING_REVEAL = re.compile(
    r"<(h[1-6])(\s[^>]*?)\s*\bdata-reveal(?:\s*=\s*(['\"][^'\"]*['\"])?)?([^>]*)>",
    re.I,
)


def strip_heading_reveals(html: str) -> str:
    """Drop leftover heading leaves so parents own the stagger (re-inject)."""

    def repl(m: re.Match[str]) -> str:
        attrs = f"{m.group(2) or ''}{m.group(4) or ''}"
        attrs = re.sub(
            r"\s*\bdata-reveal(?:\s*=\s*(['\"][^'\"]*['\"]))?",
            "",
            attrs,
        )
        return f"<{m.group(1)}{attrs}>"

    return HEADING_REVEAL.sub(repl, html)


def mark_reveals(html: str) -> tuple[str, int]:
    """Add data-reveal on parent groups (heads, grids, inners, hosts)."""
    html = strip_heading_reveals(html)
    banned = skip_ranges(html)
    count = 0
    out: list[str] = []
    last = 0

    def consider(m: re.Match[str]) -> None:
        nonlocal count, last
        tag = m.group(1)
        attrs = m.group(2) or ""
        if _inside(banned, m.start()):
            return
        if _should_skip_open(tag, attrs):
            return
        if SECTION_INNER.search(attrs):
            return
        if re.search(r"\bdata-reveal\b", m.group(0)):
            return
        out.append(html[last : m.start()])
        out.append(_with_data_reveal(m.group(0)))
        last = m.end()
        count += 1

    events: list[re.Match[str]] = []
    events.extend(OPEN_CANDIDATE.finditer(html))
    events.extend(OPEN_GROUP.finditer(html))
    events.sort(key=lambda m: (m.start(), -m.end()))

    seen_starts: set[int] = set()
    for m in events:
        if m.start() in seen_starts:
            continue
        seen_starts.add(m.start())
        consider(m)

    out.append(html[last:])
    return "".join(out), count


SCRIPT_TAGS = (
    '<script src="js/vendor/gsap.min.js"></script>',
    '<script src="js/vendor/ScrollTrigger.min.js"></script>',
    f'<script src="js/{RUNTIME_NAME}"></script>',
)


def inject_scripts(html: str) -> str:
    if RUNTIME_NAME in html and GSAP_NAME in html and ST_NAME in html:
        return html
    block = "\n".join(
        tag
        for tag in SCRIPT_TAGS
        if (
            (RUNTIME_NAME in tag and RUNTIME_NAME not in html)
            or (GSAP_NAME in tag and GSAP_NAME not in html)
            or (ST_NAME in tag and ST_NAME not in html)
        )
    )
    if not block:
        return html
    if "</body>" in html:
        return html.replace("</body>", f"{block}\n</body>", 1)
    return html + "\n" + block + "\n"


def copy_assets(rebuild_root: Path) -> None:
    vendor_dest = rebuild_root / "js" / "vendor"
    vendor_dest.mkdir(parents=True, exist_ok=True)
    for name in (GSAP_NAME, ST_NAME):
        src = VENDOR_SRC / name
        if not src.is_file():
            raise FileNotFoundError(
                f"missing vendored {src} — official gsap.min.js + "
                "ScrollTrigger.min.js must live under templates/vendor/gsap/"
            )
        shutil.copy2(src, vendor_dest / name)
    runtime_src = TEMPLATES / RUNTIME_NAME
    if not runtime_src.is_file():
        raise FileNotFoundError(f"missing {runtime_src}")
    js_dest = rebuild_root / "js"
    js_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime_src, js_dest / RUNTIME_NAME)


def collect_html(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.glob("*.html")))
        else:
            found.append(path)
            if path.name == "index.html":
                for sib in sorted(path.parent.glob("*.html")):
                    if sib not in found:
                        found.append(sib)
    polish_present = any(path.name == "index-polish.html" for path in found)
    out: list[Path] = []
    seen: set[Path] = set()
    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        if path.name in SKIP_HTML_NAMES:
            continue
        if polish_present and path.name == "index.html":
            continue
        seen.add(resolved)
        out.append(path)
    return out


def inject_file(path: Path) -> tuple[int, bool]:
    text = path.read_text(encoding="utf-8")
    marked, count = mark_reveals(text)
    injected = inject_scripts(marked)
    if injected != text:
        path.write_text(injected, encoding="utf-8")
    return count, injected != text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path, nargs="+")
    ap.add_argument(
        "--assets-dir",
        type=Path,
        help="Where to write js/vendor + js/gsap-reveal.js "
        "(default: parent of first html / given dir)",
    )
    args = ap.parse_args(argv)
    _hint("3.2", "active", args.html[0] if args.html else None)
    pages = collect_html(args.html)
    if not pages:
        print("no rebuild html to inject", flush=True)
        return 2
    root = args.assets_dir
    if root is None:
        first = args.html[0]
        root = first.resolve() if first.is_dir() else first.resolve().parent
    copy_assets(root)
    for path in pages:
        count, changed = inject_file(path)
        print(f"injected gsap-reveal → {path} ({count} data-reveal, changed={changed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
