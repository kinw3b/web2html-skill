#!/usr/bin/env python3
"""1.1 light scrape: one URL, images + Latin fonts, no crawl.

1.2 localize-html-images.mjs already downloads any remaining live images
into capture/assets (and will reuse source-site/assets as a cache).
This step is only a fast SSR cache plus the Latin woff2 files 2.1 needs.

Do not download every unicode-range subset. Framer/Google pages emit one
@font-face per script; the first hash is often Cyrillic Extended and the
full set is hundreds of files (Pitfall #185).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXT = re.compile(r"\.(?:png|jpe?g|webp|avif|gif|svg)(?:$|[?#])", re.I)
FONT_EXT = re.compile(r"\.(?:woff2?|ttf|otf)(?:$|[?#])", re.I)
FACE_RE = re.compile(r"@font-face\s*\{([^}]+)\}", re.I | re.S)
FAMILY_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.I)
WEIGHT_RE = re.compile(r"font-weight\s*:\s*([^;]+)", re.I)
STYLE_RE = re.compile(r"font-style\s*:\s*([^;]+)", re.I)
RANGE_RE = re.compile(r"unicode-range\s*:\s*([^;]+)", re.I)
SRC_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")\s]+)", re.I)
ABS_URL_RE = re.compile(r"https?://[^\"'()\s<>]+", re.I)
# Basic Latin / Latin-1. A face that only declares U+0460-052F is a skip.
LATIN_RANGE_RE = re.compile(r"U\+0*0+-0*00FF|U\+0*0+-0*007F|U\+0000-10FFFF", re.I)
UA = "Mozilla/5.0 web2html-light-scrape/1.1"
WORKERS = 12
TIMEOUT = 12


def is_latin_range(unicode_range: str) -> bool:
    text = (unicode_range or "").strip()
    if not text:
        return True
    return bool(LATIN_RANGE_RE.search(text))


def basename_of(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    name = Path(path).name
    return name or ""


def absolutize(raw: str, page_url: str) -> str:
    raw = raw.strip().strip("'\"")
    if raw.startswith("//"):
        return "https:" + raw
    return urllib.parse.urljoin(page_url, raw)


def parse_font_faces(html: str, page_url: str) -> list[dict]:
    faces: list[dict] = []
    for body in FACE_RE.findall(html):
        fam = FAMILY_RE.search(body)
        src = SRC_URL_RE.search(body)
        if not (fam and src):
            continue
        url = absolutize(src.group(1), page_url)
        if not FONT_EXT.search(urllib.parse.urlparse(url).path):
            continue
        weight = WEIGHT_RE.search(body)
        style = STYLE_RE.search(body)
        urange = RANGE_RE.search(body)
        faces.append(
            {
                "family": fam.group(1).strip().strip("'\""),
                "weight": (weight.group(1).strip() if weight else ""),
                "style": (style.group(1).strip() if style else "normal"),
                "unicode": (urange.group(1).strip() if urange else ""),
                "url": url,
            }
        )
    return faces


def latin_font_urls(faces: list[dict]) -> list[dict]:
    """Keep Latin faces without collapsing styles or shared variable-font URLs."""
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for face in faces:
        key = (face["family"].casefold(), face["weight"] or "400", face.get("style", "normal"))
        grouped.setdefault(key, []).append(face)

    kept: list[dict] = []
    seen: set[tuple] = set()
    for rows in grouped.values():
        has_range = any(r["unicode"] for r in rows)
        if has_range:
            rows = [r for r in rows if is_latin_range(r["unicode"])]
        for row in rows:
            identity = (row["family"], row["weight"], row.get("style", "normal"), row["unicode"], row["url"])
            if identity in seen:
                continue
            seen.add(identity)
            kept.append(row)
    return kept


def image_urls(html: str, page_url: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in ABS_URL_RE.findall(html):
        clean = absolutize(raw.rstrip(".,;)"), page_url)
        path = urllib.parse.urlparse(clean).path
        if not IMAGE_EXT.search(path):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        found.append(clean)
    return found


def title_of(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def collect_plan(html: str, page_url: str) -> dict:
    faces = parse_font_faces(html, page_url)
    fonts = latin_font_urls(faces)
    images = image_urls(html, page_url)
    return {
        "url": page_url,
        "title": title_of(html),
        "faces": faces,
        "fonts": fonts,
        "images": images,
        "skipped_font_faces": max(0, len(faces) - len(fonts)),
    }


def download_one(url: str, dest: Path) -> dict:
    if dest.exists() and dest.stat().st_size > 0:
        return {"url": url, "path": str(dest), "bytes": dest.stat().st_size, "ok": True, "cached": True}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            data = response.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {"url": url, "path": str(dest), "bytes": len(data), "ok": True, "cached": False}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
        return {"url": url, "path": str(dest), "bytes": 0, "ok": False, "error": str(err).split("\n")[0]}


def parallel_download(jobs: list[tuple[str, Path]], workers: int = WORKERS) -> list[dict]:
    if not jobs:
        return []
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {pool.submit(download_one, url, dest): (url, dest) for url, dest in jobs}
        for future in as_completed(future_map):
            results.append(future.result())
    return results


def write_pages_json(out: Path, page_url: str, title: str) -> None:
    (out / "pages.json").write_text(
        json.dumps([{"path": "/", "url": page_url, "file": "index.html", "title": title}], indent=2) + "\n",
        encoding="utf-8",
    )


def write_tokens_md(out: Path, plan: dict) -> None:
    families: dict[str, set[str]] = {}
    for face in plan["fonts"]:
        families.setdefault(face["family"], set()).add(face["weight"] or "?")
    lines = [
        f"# Scraped tokens — {plan['url']}",
        "",
        "Source: `source-site/index.html` (1.1 light scrape). Visual evidence is 1.2.",
        "Fonts listed here are **Latin `U+0000-00FF` only**. Non-Latin subsets were not downloaded.",
        "",
        "## Font families",
        "",
    ]
    if not families:
        lines.append("- (none found in SSR `@font-face`)")
    else:
        for name in sorted(families):
            weights = ", ".join(sorted(families[name]))
            lines.append(f"- **{name}** — weights {weights}")
    lines += ["", "## `@font-face` sources (Latin only)", "", "| Family | Weight | File | unicode-range | Style |", "|---|---|---|---|---|"]
    for face in plan["fonts"]:
        lines.append(
            f"| {face['family']} | {face['weight'] or '—'} | `{basename_of(face['url'])}` | {face['unicode'] or 'full'} | {face.get('style', 'normal')} |"
        )
    lines += [
        "",
        "Pitfall #59 / #185: do not download every unicode-range hash. Rebuild `@font-face` must use these Latin files.",
        "Self-host into `rebuild/fonts/` at **2.1**, not 1.1.",
        "",
    ]
    (out / "scraped-tokens.md").write_text("\n".join(lines), encoding="utf-8")


def write_contract(qa: Path, page_url: str, title: str) -> Path:
    qa.mkdir(parents=True, exist_ok=True)
    path = qa / "fidelity-contract.md"
    if path.exists():
        return path
    path.write_text(
        "\n".join(
            [
                f"# Fidelity contract",
                "",
                f"- Live URL: {page_url}",
                f"- Title: {title or '(from scrape)'}",
                "- Path: `homepage-only`",
                "- Classification: `web-responsive`",
                "- Paper import: this URL only. Required viewports **1600 / 768 / 390**. Not allow-drift.",
                "- Assets: `source-site/assets/` (this project only). 1.2 downloads any remaining live images.",
                "- Fonts: Latin `U+0000-00FF` only at 1.1. Self-host into `rebuild/fonts/` at **2.1**.",
                "",
                "Do not rewrite this file. The 1.1 script owns it.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_ledger(qa: Path, assets_dir: Path, downloads: list[dict], plan: dict) -> Path:
    qa.mkdir(parents=True, exist_ok=True)
    font_urls = {row["url"] for row in plan["fonts"]}
    image_set = set(plan["images"])
    rows = []
    for item in downloads:
        name = Path(item["path"]).name
        kind = "font" if item["url"] in font_urls or FONT_EXT.search(name) else "svg" if name.lower().endswith(".svg") else "image"
        rel = str(Path(item["path"]).resolve())
        try:
            rel = str(Path(item["path"]).resolve().relative_to(assets_dir.parent.parent.resolve()))
        except ValueError:
            rel = str(Path("source-site") / "assets" / name)
        rows.append(
            {
                "id": f"{kind}-{Path(name).stem}",
                "kind": kind,
                "sourceUrl": item["url"],
                "localPath": rel,
                "intrinsic": None,
                "rendered": None,
                "status": "exact" if item.get("ok") else "missing",
                "fallbackReason": None if item.get("ok") else item.get("error"),
            }
        )
    path = qa / "asset-ledger.json"
    path.write_text(
        json.dumps(
            {
                "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generatedFrom": "web2html/scrape_light",
                "assets": rows,
                "skippedFontFaces": plan["skipped_font_faces"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_regressions(qa: Path) -> None:
    qa.mkdir(parents=True, exist_ok=True)
    path = qa / "regressions.json"
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")


def run(
    page_url: str,
    out: Path,
    project: Path | None = None,
    html_path: Path | None = None,
    dry_run: bool = False,
    workers: int = WORKERS,
) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    project = project or out.parent

    if html_path:
        html = html_path.read_text(encoding="utf-8", errors="replace")
        (out / "index.html").write_text(html, encoding="utf-8")
        raw = out / "index.raw.html"
        if not raw.exists():
            raw.write_text(html, encoding="utf-8")
    else:
        html = (out / "index.html").read_text(encoding="utf-8", errors="replace")

    plan = collect_plan(html, page_url)
    write_pages_json(out, page_url, plan["title"])
    write_tokens_md(out, plan)

    jobs: list[tuple[str, Path]] = []
    for url in plan["images"]:
        name = basename_of(url)
        if name:
            jobs.append((url, assets / name))
    for face in plan["fonts"]:
        name = basename_of(face["url"])
        if name:
            jobs.append((face["url"], assets / name))

    # De-dupe dest collisions (same basename, different URL) — first wins.
    unique: dict[Path, str] = {}
    for url, dest in jobs:
        unique.setdefault(dest, url)
    jobs = [(url, dest) for dest, url in unique.items()]

    downloads: list[dict] = []
    if not dry_run:
        downloads = parallel_download(jobs, workers=workers)

    qa = project / "qa"
    if not dry_run:
        write_contract(qa, page_url, plan["title"])
        write_ledger(qa, assets, downloads, plan)
        write_regressions(qa)

    summary = {
        "page": page_url,
        "title": plan["title"],
        "images": len(plan["images"]),
        "latinFonts": len(plan["fonts"]),
        "skippedFontFaces": plan["skipped_font_faces"],
        "queued": len(jobs),
        "downloaded": sum(1 for row in downloads if row.get("ok")),
        "failed": sum(1 for row in downloads if not row.get("ok")),
        "dryRun": dry_run,
        "out": str(out),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="1.1 light scrape (images + Latin fonts)")
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", default="source-site")
    parser.add_argument("--project", default="")
    parser.add_argument("--html", default="", help="Existing HTML (skip curl)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)

    out = Path(args.out)
    project = Path(args.project) if args.project else out.parent
    html_path = Path(args.html) if args.html else None
    if html_path is None and not (out / "index.html").is_file():
        print("scrape_light.py: missing index.html — curl the URL first (scrape-web.sh)", file=sys.stderr)
        return 2

    summary = run(
        args.url,
        out,
        project=project,
        html_path=html_path,
        dry_run=args.dry_run,
        workers=args.workers,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
