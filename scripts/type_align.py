#!/usr/bin/env python3
"""Paper-gold type + alignment helpers (Pitfall #94).

Semantic retag (div/p → h1–h6 / p) lets UA heading styles win: text-align
start, different size/weight. Alignment often lived on a parent flex
(justify-center / text-center), not the text node.

Gold is geometry-lock alignment + Tailwind size tokens — never a
site face, never a baked font list. The skill does not lock fonts.
Type sizes snap to Tailwind --text-xs…--text-12xl only (no --text-display).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ALIGN_CLASS = re.compile(
    r"\btext-(center|left|right|start|end)\b", re.I
)
JUSTIFY_CENTER = re.compile(r"\bjustify-center\b", re.I)
TEXT_ALIGN_STYLE = re.compile(
    r"text-align\s*:\s*(center|left|right|start|end|justify)", re.I
)
SIZE_CLASS = re.compile(
    r"\btext-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|10xl|11xl|12xl)\b"
)
SIZE_VAR = re.compile(
    r"--text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|10xl|11xl|12xl)\b"
)
# Fonts are per-project (Paper / tokens.css). This skill never locks a face.
FULL_WIDTH = re.compile(
    r"\bw-full\b|width\s*:\s*100%|width\s*:\s*round\(\s*100%", re.I
)
PX = re.compile(r"^(\d+(?:\.\d+)?)px$", re.I)

# Tailwind default rem→px at 16px root (1.5 type sheet).
TOKEN_PX: dict[str, float] = {
    "xs": 12,
    "sm": 14,
    "base": 16,
    "lg": 18,
    "xl": 20,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
    "5xl": 48,
    "6xl": 60,
    "7xl": 72,
    "8xl": 96,
    "9xl": 128,
    "10xl": 160,
    "11xl": 192,
    "12xl": 224,
}
SIZE_TOLERANCE_PX = 1.05

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BODY_TAGS = {"p"}
CENSUS_TAGS = HEADING_TAGS | BODY_TAGS


def _class_str(el) -> str:
    cls = el.get("class") if hasattr(el, "get") else None
    if not cls:
        return ""
    if isinstance(cls, list):
        return " ".join(str(c) for c in cls)
    return str(cls)


def _style(el) -> str:
    return (el.get("style") or "") if hasattr(el, "get") else ""


def _blob(el) -> str:
    return f"{_class_str(el)} {_style(el)}"


def normalize_align(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in {"start", "left"}:
        return "start"
    if v in {"end", "right"}:
        return "end"
    if v in {"center", "justify"}:
        return v
    return None


def align_family(value: str | None) -> str | None:
    """Map computed/gold align into compare families: center | start | end | justify."""
    return normalize_align(value)


def align_matches(expected: str | None, actual: str | None) -> bool:
    """start≈left, end≈right. Missing expected = no assert."""
    exp = align_family(expected)
    act = align_family(actual)
    if exp is None:
        return True
    if act is None:
        return False
    return exp == act


def snap_size_token(px: float | None) -> str | None:
    if px is None:
        return None
    best = None
    best_d = 1e9
    for name, val in TOKEN_PX.items():
        d = abs(val - px)
        if d < best_d:
            best_d = d
            best = name
    if best is None or best_d > SIZE_TOLERANCE_PX + 0.5:
        return None
    return best


def size_matches_token(expected: str | None, actual_px: float | None) -> bool:
    """expected is token name (text-5xl / 5xl) or px string. Tolerance ~1px."""
    if expected is None:
        return True
    if actual_px is None:
        return False
    token = expected.strip()
    if token.startswith("text-"):
        token = token[5:]
    if token.endswith("px"):
        try:
            want = float(token[:-2])
        except ValueError:
            return False
        return abs(want - actual_px) <= SIZE_TOLERANCE_PX
    want = TOKEN_PX.get(token)
    if want is None:
        m = PX.match(token)
        if not m:
            return False
        want = float(m.group(1))
    return abs(want - actual_px) <= SIZE_TOLERANCE_PX


def parse_px(value: str | None) -> float | None:
    if not value:
        return None
    m = PX.match(value.strip())
    if not m:
        return None
    return float(m.group(1))


def detect_align_on_node(el) -> str | None:
    blob = _blob(el)
    m = TEXT_ALIGN_STYLE.search(_style(el))
    if m:
        return normalize_align(m.group(1))
    m = ALIGN_CLASS.search(_class_str(el))
    if m:
        return normalize_align(m.group(1))
    return None


def is_full_width_title(el) -> bool:
    return bool(FULL_WIDTH.search(_blob(el)))


def detect_align_from_parent(el) -> str | None:
    """Immediate text-column parent: text-* class/style, or justify-center + full-width title."""
    parent = getattr(el, "parent", None)
    if parent is None or not getattr(parent, "name", None):
        return None
    # Walk a short chain of wrappers (flex column → title).
    node = parent
    for _ in range(4):
        if node is None or not getattr(node, "name", None):
            break
        if node.name in {"body", "html", "[document]"}:
            break
        own = detect_align_on_node(node)
        if own:
            return own
        blob = _blob(node)
        if JUSTIFY_CENTER.search(blob) and (
            is_full_width_title(el) or detect_align_on_node(el) is None
        ):
            # Parent flex centers a full-width / block title → gold is center.
            return "center"
        node = getattr(node, "parent", None)
    return None


def expected_align(el) -> str | None:
    """Gold align: node style/class, else immediate text-column parent. Never assume center."""
    own = detect_align_on_node(el)
    if own:
        return own
    return detect_align_from_parent(el)


def stamp_text_align(el, align: str | None) -> bool:
    """Stamp inline text-align if missing on the node. Keep class + leftover style."""
    if not align:
        return False
    if detect_align_on_node(el):
        return False
    style = _style(el).rstrip().rstrip(";")
    decl = f"text-align: {align}"
    el["style"] = f"{style}; {decl}" if style else decl
    return True


def preserve_align_on_retag(el) -> str | None:
    """Before/after retag: if the node would lose alignment, stamp it."""
    gold = expected_align(el)
    if not gold:
        return None
    if detect_align_on_node(el):
        return gold
    stamp_text_align(el, gold if gold != "start" else "left")
    # Prefer literal left/right for CSS when family is start/end.
    return gold



def size_token_from_blob(blob: str) -> str | None:
    best = None
    best_rank = -1
    rank = {n: i for i, n in enumerate(TOKEN_PX)}
    for m in SIZE_CLASS.finditer(blob):
        name = m.group(1)
        if rank.get(name, -1) > best_rank:
            best_rank = rank[name]
            best = name
    for m in SIZE_VAR.finditer(blob):
        name = m.group(1)
        if rank.get(name, -1) > best_rank:
            best_rank = rank[name]
            best = name
    return best


def find_lock_html(root: Path, ship: Path | None = None) -> Path | None:
    """Prefer geometry-lock fixture; fall back to ship HTML."""
    candidates = [
        root / "qa" / "fixtures" / "geometry-lock-home.html",
        root / "qa" / "fixtures" / "geometry-lock.html",
        root / "rebuild" / "geometry-lock.html",
        root / "design-library" / "exports-inline" / "geometry-lock.html",
    ]
    for path in candidates:
        if path.is_file():
            return path
    if ship and ship.is_file():
        return ship
    guess = root / "rebuild" / "index.html"
    if guess.is_file():
        return guess
    return None


def _soup(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def _text(el) -> str:
    return " ".join(t.strip() for t in el.stripped_strings if t.strip())


def _selector(el) -> str | None:
    ident = el.get("id") if hasattr(el, "get") else None
    if ident:
        return f"#{ident}"
    return None


def census_type_align(
    html: str,
    *,
    catalog: list[str] | None = None,
    source: str = "ship",
) -> list[dict[str, Any]]:
    """Build type-align census rows from lock or ship HTML (class/style signals).

    `catalog` is ignored. The skill does not lock or assert fonts.
    """
    soup = _soup(html)
    rows: list[dict[str, Any]] = []
    for el in soup.find_all(list(CENSUS_TAGS)):
        text = _text(el)
        if not text or len(text) > 200:
            continue
        blob = _blob(el)
        align = expected_align(el)
        size = size_token_from_blob(blob)
        if not size:
            # Try parent for size utilities sitting on a wrapper
            parent = el.parent
            for _ in range(2):
                if parent is None:
                    break
                size = size_token_from_blob(_blob(parent))
                if size:
                    break
                parent = parent.parent
        rows.append(
            {
                "text": text,
                "tag": el.name,
                "selector": _selector(el),
                "align": align,
                "fontSize": f"text-{size}" if size else None,
                "source": source,
            }
        )
    return rows


def write_census(path: Path, rows: list[dict[str, Any]], meta: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "count": len(rows),
        "rows": rows,
        "meta": meta or {},
        "refused": [
            "any baked font list or catalog-face assert in this skill",
            "global letter-spacing / line-height stamp on all h1/h2",
            "site-specific ID center/left lists",
            "hardcoded user-specific Playwright path",
            "--text-display token",
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def compare_row(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[str]:
    """Pure verify expectations — used by tests and mirrored in the mjs."""
    errors: list[str] = []
    label = expected.get("selector") or expected.get("text", "")[:40]
    if not align_matches(expected.get("align"), actual.get("textAlign")):
        errors.append(
            f"{label}: textAlign gold={expected.get('align')!r} "
            f"got={actual.get('textAlign')!r}"
        )
    actual_px = actual.get("fontSizePx")
    if actual_px is None and actual.get("fontSize"):
        actual_px = parse_px(str(actual.get("fontSize")))
    if not size_matches_token(expected.get("fontSize"), actual_px):
        errors.append(
            f"{label}: fontSize gold={expected.get('fontSize')!r} "
            f"got={actual.get('fontSize')!r}"
        )
    return errors


def default_project_root(ship: Path) -> Path:
    ship = ship.resolve()
    if ship.parent.name == "rebuild":
        return ship.parent.parent
    return ship.parent
