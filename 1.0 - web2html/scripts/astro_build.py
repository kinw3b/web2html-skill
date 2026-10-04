#!/usr/bin/env python3
"""Shared `astro build` helpers for optional Phase 5 (Astro-first site).

Runs `npm install` + `astro build` inside `astro/`, then rewrites the
root-absolute URLs in `astro/dist` so every built page opens on `file://`
(the pipeline's preview rule — no local HTTP server, ever). The agent never
starts `astro dev`; the human may run `npm run preview`.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ABS_ATTR_RE = re.compile(
    r"""\b(href|src|action)\s*=\s*(['"])(/[^'"]*)\2""",
    re.I,
)
CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)(/[^'")]+)\1\s*\)""", re.I)


def dist_page_rel(slug: str) -> str:
    """Project-relative path of a built page. Home → astro/dist/index.html."""
    clean = (slug or "").strip().strip("/")
    if clean in {"", "index", "home"}:
        return "astro/dist/index.html"
    return f"astro/dist/{clean}/index.html"


def relative_url(value: str, depth: int) -> str:
    """Root-absolute → relative for a page `depth` folders below dist/.

    '/styles/a.css' at depth 1 → '../styles/a.css'
    '/about/'       at depth 0 → 'about/index.html'
    '/'             at depth 1 → '../index.html'
    Protocol-relative ('//cdn') and non-absolute values pass through.
    """
    if not value.startswith("/") or value.startswith("//"):
        return value
    path, hash_sep, frag = value.partition("#")
    path, q_sep, query = path.partition("?")
    body = path.lstrip("/")
    if body == "" or body.endswith("/"):
        body += "index.html"
    out = ("../" * depth) + body
    if q_sep:
        out += q_sep + query
    if hash_sep:
        out += hash_sep + frag
    return out


def relativize_html(html: str, depth: int) -> str:
    def attr_repl(match: re.Match[str]) -> str:
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{relative_url(value, depth)}{quote}"

    def css_repl(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        return f"url({quote}{relative_url(value, depth)}{quote})"

    return CSS_URL_RE.sub(css_repl, ABS_ATTR_RE.sub(attr_repl, html))


def relativize_css(css: str, depth: int) -> str:
    def css_repl(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        return f"url({quote}{relative_url(value, depth)}{quote})"

    return CSS_URL_RE.sub(css_repl, css)


def relativize_dist(dist: Path) -> list[str]:
    """Rewrite every built .html / .css in place. Returns the files changed."""
    changed: list[str] = []
    if not dist.is_dir():
        return changed
    for path in sorted(dist.rglob("*")):
        if path.suffix.lower() not in {".html", ".css"} or not path.is_file():
            continue
        depth = len(path.relative_to(dist).parts) - 1
        text = path.read_text(encoding="utf-8", errors="replace")
        out = relativize_html(text, depth) if path.suffix.lower() == ".html" else relativize_css(text, depth)
        if out != text:
            path.write_text(out, encoding="utf-8")
            changed.append(path.relative_to(dist).as_posix())
    return changed


ASSET_TAG_RE = re.compile(r"<link\b[^>]*>|<script\b[^>]*>", re.I)
ASSET_URL_RE = re.compile(r"""(?:href|src)\s*=\s*(['"])([^'"]+)\1""", re.I)
EXTERNAL_URL_RE = re.compile(r"^(?:https?:)?//|^data:|^#|^mailto:|^tel:", re.I)


def unresolved_assets(page: Path) -> list[str]:
    """Local stylesheet/script references in a BUILT page that miss on disk.

    `astro build` never fetches a CSS file, so a 404'd sheet rides a green
    build and ships the site unstyled (Pitfall #240). Run AFTER relativize.
    """
    text = page.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for tag in ASSET_TAG_RE.findall(text):
        if tag.lower().startswith("<link") and not re.search(r"rel\s*=\s*['\"]?stylesheet", tag, re.I):
            continue
        match = ASSET_URL_RE.search(tag)
        if not match:
            continue
        value = match.group(2).strip()
        if not value or EXTERNAL_URL_RE.match(value):
            continue
        target = (page.parent / value.split("?", 1)[0].split("#", 1)[0]).resolve()
        if not target.is_file() and value not in missing:
            missing.append(value)
    return missing


# ---------------------------------------------------------------- review ----
# Pitfall #248: the human could not tell what on a built page is an Astro
# component vs markup pasted into the page as raw HTML. Every component's
# top-level element(s) carry data-astro-component="{Name}" (stamped in src,
# so it survives every rebuild), and the BUILT pages get the same QA overlay
# as 2.4 / 3.4 — bare URL clean, ?qa-outlines=components boxes components,
# ?qa-outlines=tags shows the semantic chips. Never shipped from src.
COMPONENT_ATTR = "data-astro-component"
FRAGMENT_LITERAL_RE = re.compile(r"(const html = `)(.*?)(`;\s*\n---)", re.S)
OPEN_EL_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)\b")
REVIEW_DIR = "qa-review"


def _stamp_open(tag_src: str, name: str) -> str:
    match = OPEN_EL_RE.match(tag_src)
    if not match or COMPONENT_ATTR in tag_src[: tag_src.find(">") + 1]:
        return tag_src
    return tag_src[: match.end()] + f' {COMPONENT_ATTR}="{name}"' + tag_src[match.end():]


def stamp_component_html(html: str, name: str) -> str:
    """Stamp every TOP-LEVEL element of a fragment (a shared band component may
    hold several sibling <section>s)."""
    import shared_sections

    out, cursor = [], 0
    while True:
        match = OPEN_EL_RE.search(html, cursor)
        if not match:
            out.append(html[cursor:])
            break
        element = shared_sections.balanced(html, match.start())
        if not element:
            out.append(html[cursor:])
            break
        out.append(html[cursor:match.start()])
        out.append(_stamp_open(element, name))
        cursor = match.start() + len(element)
    return "".join(out)


def stamp_components(astro: Path) -> list[str]:
    """Idempotently mark each src/components/{Name}.astro root element(s)."""
    comps = astro / "src" / "components"
    stamped: list[str] = []
    if not comps.is_dir():
        return stamped
    for path in sorted(comps.glob("*.astro")):
        name = path.stem
        text = path.read_text(encoding="utf-8", errors="replace")
        frag = FRAGMENT_LITERAL_RE.search(text)
        if frag:
            body = stamp_component_html(frag.group(2), name)
            new = text[: frag.start(2)] + body + text[frag.end(2):]
        else:
            parts = text.split("---", 2)
            if len(parts) == 3:
                tmpl = parts[2]
                match = OPEN_EL_RE.search(tmpl)
                if not match:
                    continue
                tmpl = tmpl[: match.start()] + _stamp_open(tmpl[match.start():], name)
                new = parts[0] + "---" + parts[1] + "---" + tmpl
            else:
                continue
        if new != text:
            path.write_text(new, encoding="utf-8")
            stamped.append(name)
    return stamped


def inject_review_overlay(dist: Path) -> list[str]:
    """Copy the QA overlay into dist/qa-review/ and wire every built page
    (relative paths, file://). data-qa-ship=final keeps the bare URL clean."""
    import importlib.util

    if not dist.is_dir():
        return []
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("inject_qa_overlay", here / "inject-qa-overlay.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    review = dist / REVIEW_DIR
    review.mkdir(parents=True, exist_ok=True)
    for name in (mod.CSS_NAME, mod.JS_NAME):
        (review / name).write_bytes((mod.TEMPLATES / name).read_bytes())
    wired: list[str] = []
    for page in sorted(dist.rglob("*.html")):
        if REVIEW_DIR in page.relative_to(dist).parts:
            continue
        depth = len(page.relative_to(dist).parts) - 1
        prefix = "../" * depth + REVIEW_DIR + "/"
        text = page.read_text(encoding="utf-8", errors="replace")
        out = mod.inject(text, prefix + mod.CSS_NAME, prefix + mod.JS_NAME)
        if "data-qa-ship=" not in out:
            out = re.sub(r"<html\b", '<html data-qa-ship="final"', out, count=1)
        if out != text:
            page.write_text(out, encoding="utf-8")
        wired.append(page.relative_to(dist).as_posix())
    return wired


def build(root: Path, *, timeout: int = 180) -> dict:
    """npm install + astro build, then relativize dist. Never starts a server.

    Serialized with an exclusive lock on astro/.build.lock: page-loop workers
    build in parallel and astro rewrites the whole dist/ each time (#249)."""
    import fcntl

    root = root.resolve()
    astro = root / "astro"
    if not (astro / "package.json").is_file():
        raise FileNotFoundError("need astro/package.json from 5.1")
    with open(astro / ".build.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _build_locked(root, astro, timeout)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _build_locked(root: Path, astro: Path, timeout: int) -> dict:
    stamp_components(astro)
    log = ""
    try:
        install = subprocess.run(
            ["npm", "install", "--no-fund", "--no-audit"],
            cwd=astro,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        log += (install.stdout or "") + (install.stderr or "")
        if install.returncode != 0:
            return {"built": False, "errors": ["npm install failed"], "log": log, "relativized": []}
        built = subprocess.run(
            ["npx", "--yes", "astro", "build"],
            cwd=astro,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        log += (built.stdout or "") + (built.stderr or "")
        if built.returncode != 0:
            return {"built": False, "errors": ["astro build failed"], "log": log, "relativized": []}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"built": False, "errors": [f"astro build skipped: {exc}"], "log": log, "relativized": []}
    changed = relativize_dist(astro / "dist")
    inject_review_overlay(astro / "dist")
    return {"built": True, "errors": [], "log": log, "relativized": changed}


def write_build_log(root: Path, log: str) -> str | None:
    if not log.strip():
        return None
    dest = root / "qa" / "phase-5-build.log"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(log, encoding="utf-8")
    return "qa/phase-5-build.log"
