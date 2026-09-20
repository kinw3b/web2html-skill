"""Paper get_jsx paints photos as empty divs with background-image.

Future runs MUST download those URLs into rebuild/images/ and promote the
empty fill boxes to <img>, then hoist each <img> out of data-decorative
pointer-events:none wrappers. Outlines then show img, not div>div>div.
Pitfalls #47 / #48.
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

BG_URL = re.compile(
    r"background-image:\s*url\((['\"]?)([^)'\"]+)\1\)",
    re.I,
)
REMOTE = re.compile(
    r"^https?://(?:app\.paper\.design/file-assets/|framerusercontent\.com/)",
    re.I,
)


def basename_from_url(url: str) -> str | None:
    try:
        name = Path(unquote(urlparse(url).path)).name
    except Exception:
        return None
    name = name.split("?")[0]
    return name or None


def split_decls(style: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for part in style.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        k, v = part.split(":", 1)
        out.append((k.strip().lower(), v.strip()))
    return out


def join_decls(decls: list[tuple[str, str]]) -> str:
    return "; ".join(f"{k}: {v}" for k, v in decls if v)


def localize_url(url: str, images_dir: Path, images_href: str) -> str:
    name = basename_from_url(url)
    if name and images_dir.is_dir() and (images_dir / name).is_file():
        return f"{images_href.rstrip('/')}/{name}"
    return url


def download_urls(urls: list[str], images_dir: Path) -> list[str]:
    images_dir.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        name = basename_from_url(url)
        if not name:
            failed.append(url)
            continue
        dest = images_dir / name
        if dest.is_file() and dest.stat().st_size > 0:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "prior-run"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dest.write_bytes(r.read())
        except Exception:
            failed.append(url)
    return failed


def collect_bg_urls(html: str) -> list[str]:
    return [m.group(2) for m in BG_URL.finditer(html)]


def promote_empty_bg_fills(html: str, images_dir: Path, images_href: str) -> tuple[str, int]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    n = 0
    for el in list(soup.find_all(style=True)):
        style = el.get("style") or ""
        m = BG_URL.search(style)
        if not m:
            continue
        has_kids = any(
            getattr(c, "name", None) or (isinstance(c, str) and c.strip())
            for c in el.children
        )
        if has_kids:
            continue
        url = m.group(2)
        decls = split_decls(style)
        size = "cover"
        pos = "50%"
        kept: list[tuple[str, str]] = []
        for k, v in decls:
            if k == "background-image":
                continue
            if k == "background-size":
                size = v
                continue
            if k == "background-position":
                pos = v
                continue
            if k in ("background-repeat", "background-clip"):
                continue
            kept.append((k, v))
        fit = "cover"
        sl = size.lower()
        if "contain" in sl:
            fit = "contain"
        elif sl in ("100% 100%", "100%"):
            fit = "fill"
        kept.append(("object-fit", fit))
        kept.append(("object-position", pos))
        if not any(k == "display" for k, _ in kept):
            kept.append(("display", "block"))
        # Do not put pointer-events in style: html.parser serializes
        # `style="…"; pointer-events: auto` (Pitfall #48).
        src = localize_url(url, images_dir, images_href)
        img = soup.new_tag("img")
        img["src"] = src
        img["alt"] = ""
        img["style"] = join_decls(kept)
        el.replace_with(img)
        n += 1
    if n == 0:
        return hoist_imgs_out_of_decorative(html), 0
    return hoist_imgs_out_of_decorative(str(soup)), n


JUNK_IMG_ATTRS = re.compile(
    r"<img\s+;=\"\"\s+alt=\"\"\s+auto=\"\"\s+pointer-events:=\"\"\s+",
    re.I,
)
BROKEN_PE = re.compile(
    r'(<img\b[^>]*style="[^"]*)";\s*pointer-events:\s*auto',
    re.I,
)
DECORATIVE_IMG = re.compile(
    r'<div(?=[^>]*\bdata-decorative="true")[^>]*>\s*(<img\b[^>]*/?>)\s*</div>',
    re.I,
)


ABS_POS_RE = re.compile(r"position\s*:\s*absolute", re.I)
_ZERO_BOX = {"0", "0px", "0%"}


def _style(el) -> str:
    return el.get("style") or ""


def _class_list(el) -> list[str]:
    cls = el.get("class") or []
    if isinstance(cls, str):
        return cls.split()
    return list(cls)


def is_absolute_box(el) -> bool:
    st = _style(el)
    if ABS_POS_RE.search(st):
        return True
    return "absolute" in _class_list(el)


def has_abs_offset(el) -> bool:
    """Non-zero left/top/bottom/right, or a non-100% width/height percent."""
    st = _style(el)
    for part in st.split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k, v = k.strip().lower(), v.strip().lower()
        if k in {"left", "top", "bottom", "right"} and v not in _ZERO_BOX:
            return True
        if k in {"width", "height"} and v.endswith("%") and v not in {"100%", "100.00%"}:
            return True
    return False


def has_visual(el) -> bool:
    name = getattr(el, "name", None)
    if name in {"img", "svg"}:
        return True
    return bool(el.find("img") or el.find("svg"))


def is_infographic_frame(el) -> bool:
    """Parent with 2+ visual children, at least one absolutely placed.

    Expense/receipt lock: relative 613×512 frame, photo inset 0, card
    `left: 27px; bottom: 29px; width: 68%; height: 21%`. Pitfall #80.
    """
    kids = [c for c in el.children if getattr(c, "name", None)]
    visuals = [c for c in kids if has_visual(c)]
    if len(visuals) < 2:
        return False
    return any(is_absolute_box(c) or has_abs_offset(c) for c in visuals)


def is_overlapping_abs_stack_child(wrap) -> bool:
    """True when unwrapping this decorative wrap would flatten a stack."""
    if is_absolute_box(wrap) and has_abs_offset(wrap):
        return True
    parent = getattr(wrap, "parent", None)
    if parent is None or not getattr(parent, "name", None):
        return False
    if is_infographic_frame(parent):
        return True
    visuals = [
        c
        for c in parent.children
        if getattr(c, "name", None) and has_visual(c)
    ]
    if len(visuals) >= 2 and any(
        is_absolute_box(v) or has_abs_offset(v) for v in visuals
    ):
        return True
    return False


def hoist_imgs_out_of_decorative(html: str) -> str:
    """Unwrap photos from paint-only abs stacks so Outlines hit <img> (#48).

    Do not unwrap an absolute layer that is one of several siblings in a
    relative infographic frame (Pitfall #80 / prior-run expense).
    """
    html = JUNK_IMG_ATTRS.sub("<img alt=\"\" ", html)
    html = BROKEN_PE.sub(r"\1", html)
    if 'data-decorative="true"' not in html or "<img" not in html.lower():
        prev = None
        while prev != html:
            prev = html
            html = DECORATIVE_IMG.sub(r"\1", html)
        return html
    from bs4 import BeautifulSoup, Tag

    soup = BeautifulSoup(html, "html.parser")
    changed = False
    for wrap in list(soup.select('[data-decorative="true"]')):
        if not isinstance(wrap, Tag):
            continue
        kids = [c for c in wrap.children if getattr(c, "name", None)]
        imgs = [c for c in kids if c.name == "img"]
        if len(imgs) != 1 or len(kids) != 1:
            continue
        if is_overlapping_abs_stack_child(wrap):
            continue
        wrap.replace_with(imgs[0])
        changed = True
    if not changed:
        return html
    looks_full = bool(re.search(r"<html[\s>]", html, re.I))
    out = str(soup)
    if looks_full and html.lstrip().lower().startswith("<!doctype") and not out.lstrip().lower().startswith("<!doctype"):
        out = "<!doctype html>\n" + out
    if not looks_full and soup.body is not None:
        return "".join(str(c) for c in soup.body.contents)
    return out
