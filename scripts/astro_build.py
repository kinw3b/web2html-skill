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


def build(root: Path, *, timeout: int = 180) -> dict:
    """npm install + astro build, then relativize dist. Never starts a server."""
    root = root.resolve()
    astro = root / "astro"
    if not (astro / "package.json").is_file():
        raise FileNotFoundError("need astro/package.json from 5.1")
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
    return {"built": True, "errors": [], "log": log, "relativized": changed}


def write_build_log(root: Path, log: str) -> str | None:
    if not log.strip():
        return None
    dest = root / "qa" / "phase-5-build.log"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(log, encoding="utf-8")
    return "qa/phase-5-build.log"
