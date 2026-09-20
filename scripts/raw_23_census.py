#!/usr/bin/env python3
"""2.3 — census rebuild/index-raw.html vs authored index.html.

Paper get_jsx paints icons as empty divs with background-image: url(….svg)
and a few inline <svg> chevrons. 2.2 often drops those. Run this before
the section workers so they port real glyphs instead of inventing Lucide
icons.

  python3 raw_23_census.py /path/to/project

Writes qa/paper-measure/raw-census.json. Exit 0 always writes; gate reads it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

GENERATED_FROM = "web2html/section-23-raw-census"
SHIP = Path("rebuild/index.html")
RAW = Path("rebuild/index-raw.html")
OUT = Path("qa/paper-measure/raw-census.json")
SVG_BLOCK_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.I | re.S)
IMG_SRC_RE = re.compile(r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
BG_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", re.I)
TEXT_RE = re.compile(r">([^<]{2,80})<")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def basename(url: str) -> str:
    try:
        name = Path(unquote(urlparse(url).path)).name
    except Exception:
        name = Path(url.split("?")[0]).name
    return name.split("?")[0]


def nearby_text(html: str, index: int) -> str:
    chunk = html[max(0, index - 600) : index]
    texts = [t.strip() for t in TEXT_RE.findall(chunk) if t.strip()]
    return texts[-1] if texts else ""


def fingerprint_svg(markup: str) -> str:
    compact = re.sub(r"\s+", " ", markup.strip())[:400]
    return hashlib.sha1(compact.encode("utf-8")).hexdigest()[:12]


def census_html(html: str) -> dict:
    svgs = SVG_BLOCK_RE.findall(html or "")
    imgs = IMG_SRC_RE.findall(html or "")
    bg = BG_URL_RE.findall(html or "")
    bg_svg = [u for u in bg if basename(u).lower().endswith(".svg")]
    bg_img = [u for u in bg if not basename(u).lower().endswith(".svg")]
    inline = []
    for block in svgs:
        start = (html or "").find(block)
        vb = re.search(r'viewBox="([^"]+)"', block, re.I)
        inline.append(
            {
                "fingerprint": fingerprint_svg(block),
                "viewBox": vb.group(1) if vb else "",
                "near": nearby_text(html or "", start) if start >= 0 else "",
            }
        )
    assets = []
    for url in bg_svg:
        start = (html or "").find(url)
        assets.append(
            {
                "file": basename(url),
                "url": url,
                "near": nearby_text(html or "", start) if start >= 0 else "",
            }
        )
    names = {basename(u) for u in imgs} | {basename(u) for u in bg} | {
        basename(u) for u in bg_svg
    }
    return {
        "svg": len(svgs),
        "img": len(imgs),
        "bg": len(bg),
        "bgSvg": len(bg_svg),
        "bgOther": len(bg_img),
        "inline": inline,
        "svgAssets": assets,
        "names": sorted(n for n in names if n),
    }


def missing_assets(raw: dict, ship: dict) -> list[dict]:
    ship_names = {n.casefold() for n in ship.get("names") or []}
    ship_prints = {row.get("fingerprint") for row in ship.get("inline") or []}
    missing: list[dict] = []
    seen: set[str] = set()
    for row in raw.get("svgAssets") or []:
        name = str(row.get("file") or "")
        key = name.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        if key in ship_names:
            continue
        missing.append(
            {
                "kind": "svg-asset",
                "file": name,
                "url": row.get("url"),
                "near": row.get("near") or "",
            }
        )
    for row in raw.get("inline") or []:
        fp = row.get("fingerprint")
        if fp and fp not in ship_prints:
            missing.append(
                {
                    "kind": "inline-svg",
                    "fingerprint": fp,
                    "viewBox": row.get("viewBox") or "",
                    "near": row.get("near") or "",
                }
            )
    return missing


def run_census(root: Path) -> dict:
    root = root.resolve()
    raw_html = (root / RAW).read_text(encoding="utf-8", errors="replace")
    ship_html = (root / SHIP).read_text(encoding="utf-8", errors="replace")
    raw = census_html(raw_html)
    ship = census_html(ship_html)
    missing = missing_assets(raw, ship)
    return {
        "generatedFrom": GENERATED_FROM,
        "ok": True,
        "updated": _now_iso(),
        "raw": {
            "svg": raw["svg"],
            "img": raw["img"],
            "bg": raw["bg"],
            "bgSvg": raw["bgSvg"],
            "bgOther": raw["bgOther"],
            "svgAssets": raw["svgAssets"],
            "inline": raw["inline"],
        },
        "ship": {
            "svg": ship["svg"],
            "img": ship["img"],
            "bg": ship["bg"],
            "bgSvg": ship["bgSvg"],
            "bgOther": ship["bgOther"],
        },
        "missing": missing,
        "note": (
            "index-raw paints icons as background-image SVG assets. "
            "2.3 workers port missing glyphs onto index.html — do not invent Lucide icons."
        ),
    }


def write_census(root: Path, payload: dict) -> Path:
    dest = root / OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not (root / RAW).is_file():
        print("FAIL: missing rebuild/index-raw.html", file=sys.stderr)
        return 2
    if not (root / SHIP).is_file():
        print("FAIL: missing rebuild/index.html", file=sys.stderr)
        return 2
    payload = run_census(root)
    dest = write_census(root, payload)
    missing = payload.get("missing") or []
    print(
        f"raw-census: raw svg={payload['raw']['svg']} bgSvg={payload['raw']['bgSvg']} "
        f"ship svg={payload['ship']['svg']} img={payload['ship']['img']} "
        f"missing={len(missing)}"
    )
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
