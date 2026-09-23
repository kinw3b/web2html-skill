#!/usr/bin/env python3
"""Fidelity lock and CMS-gap review for an adopted source folder (2.26.0).

source-html/ is the ship. Phase 3 may add accessibility attributes only.
Phase 4 authors the pages this review flags, from Paper screenshots, before
Astro. CSS, JS, classes, and copy stay put.

  python3 source_fidelity.py snapshot <project>
  python3 source_fidelity.py verify <project>
  python3 source_fidelity.py gaps <project>
  python3 source_fidelity.py record-gaps <project>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

GENERATED_FROM = "web2html/source-fidelity/v1"
SNAPSHOT = Path("qa/source-fidelity.json")
GAPS = Path("qa/source-gaps.json")
GAP_PLAN = Path("qa/phase-4-gap-plan.json")
GAP_AUTHOR = Path("qa/phase-4-gap-author.json")
PHASE_2_OFF = Path("qa/phase-2-off.json")
SOURCE = Path("source-html")

# Attributes a light a11y pass may add or edit. Everything else is the lock.
UNLOCKED_ATTRS = frozenset({
    "alt",
    "role",
    "lang",
    "title",
    "for",
    "tabindex",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
    "aria-hidden",
    "aria-expanded",
    "aria-controls",
    "aria-current",
    "aria-live",
    "aria-atomic",
})
SECTION_RE = re.compile(r"<section\b([^>]*)>(.*?)</section>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
DYN_EMPTY_RE = re.compile(r"w-dyn-empty|w-dyn-bind-empty", re.I)
DYN_LIST_RE = re.compile(r"w-dyn-list", re.I)
DYN_ITEM_RE = re.compile(r"w-dyn-item", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Signature(HTMLParser):
    """Tag tree + locked attributes + text. Unlocked a11y attributes are ignored."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        kept: list[str] = []
        for key, value in attrs:
            name = key.lower()
            if name in UNLOCKED_ATTRS or name.startswith("aria-"):
                continue
            kept.append(f"{name}={value or ''}")
        kept.sort()
        self.parts.append("<" + tag.lower() + (" " + " ".join(kept) if kept else "") + ">")

    def handle_endtag(self, tag: str) -> None:
        self.parts.append("</" + tag.lower() + ">")

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def html_signature(html: str) -> str:
    parser = _Signature()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # noqa: BLE001 — a broken file is a fidelity failure, not a pass
        return f"unreadable:{exc}"
    return _sha("\n".join(parser.parts).encode("utf-8"))


def _html_files(root: Path) -> list[Path]:
    folder = root / SOURCE
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*.html") if p.is_file() and "node_modules" not in p.parts)


def _asset_files(root: Path) -> list[Path]:
    folder = root / SOURCE
    found: list[Path] = []
    for sub in ("css", "js"):
        dest = folder / sub
        if not dest.is_dir():
            continue
        found.extend(p for p in dest.rglob("*") if p.is_file() and p.suffix in {".css", ".js"})
    return sorted(found)


def snapshot(root: Path) -> dict:
    """Pin source-html before the light polish. Call when 3.1 goes active."""
    root = root.resolve()
    files: dict[str, str] = {}
    signatures: dict[str, str] = {}
    for path in _html_files(root):
        rel = path.relative_to(root / SOURCE).as_posix()
        raw = path.read_bytes()
        files[rel] = _sha(raw)
        signatures[rel] = html_signature(raw.decode("utf-8", errors="replace"))
    assets: dict[str, str] = {}
    for path in _asset_files(root):
        rel = path.relative_to(root / SOURCE).as_posix()
        assets[rel] = _sha(path.read_bytes())
    payload = {
        "generatedFrom": GENERATED_FROM,
        "html": files,
        "signatures": signatures,
        "assets": assets,
        "recordedAt": _now(),
    }
    dest = root / SNAPSHOT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_snapshot(root: Path) -> dict | None:
    data = _read(root.resolve() / SNAPSHOT)
    if not data or data.get("generatedFrom") != GENERATED_FROM:
        return None
    return data


def authored_slugs(root: Path) -> set[str]:
    """Gap pages Phase 4 is allowed to rewrite. Everything else stays locked."""
    data = _read(root.resolve() / GAP_AUTHOR)
    if not data:
        return set()
    slugs: set[str] = set()
    for row in data.get("pages") or []:
        if isinstance(row, dict) and row.get("status") == "authored" and row.get("slug"):
            slugs.add(str(row["slug"]))
    return slugs


def _slug_of(rel: str) -> str:
    path = rel[: -len(".html")] if rel.endswith(".html") else rel
    if path.endswith("/index"):
        path = path[: -len("/index")]
    return path.strip("/").replace("/", "-") or "home"


def verify(root: Path, *, allow_slugs: set[str] | None = None) -> list[str]:
    """Fail if polish changed classes, copy, CSS, or JS. A11y attributes may change."""
    root = root.resolve()
    snap = load_snapshot(root)
    if not snap:
        return ["missing qa/source-fidelity.json — mark 3.1 active snapshots source-html before any polish"]
    errors: list[str] = []
    allowed = set(allow_slugs or ())
    signatures = snap.get("signatures") or {}
    for rel, digest in signatures.items():
        path = root / SOURCE / rel
        if not path.is_file():
            errors.append(f"source-html/{rel} was deleted")
            continue
        if _slug_of(rel) in allowed:
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        if html_signature(html) != digest:
            errors.append(
                f"source-html/{rel} changed beyond accessibility attributes "
                "(class, style, copy, or structure). Revert it."
            )
    assets = snap.get("assets") or {}
    for rel, digest in assets.items():
        path = root / SOURCE / rel
        if not path.is_file():
            errors.append(f"source-html/{rel} was deleted")
            continue
        if _sha(path.read_bytes()) != digest:
            errors.append(f"source-html/{rel} was edited — do not change source CSS or JS")
    for path in _asset_files(root):
        rel = path.relative_to(root / SOURCE).as_posix()
        if rel not in assets:
            errors.append(f"source-html/{rel} was added — do not invent pipeline CSS or JS")
    return errors


def _section_gaps(html: str) -> list[dict]:
    gaps: list[dict] = []
    for index, (attrs, body) in enumerate(SECTION_RE.findall(html), 1):
        reason = None
        if DYN_EMPTY_RE.search(body) or DYN_EMPTY_RE.search(attrs):
            reason = "w-dyn-empty"
        elif DYN_LIST_RE.search(body) and not DYN_ITEM_RE.search(body):
            reason = "collection-list-without-items"
        else:
            text = TAG_RE.sub(" ", body)
            words = [word for word in text.split() if word]
            if len(words) < 4 and ("w-dyn" in body or "w-dyn" in attrs):
                reason = "cms-section-without-copy"
        if reason:
            ident = ""
            match = re.search(r'\bid=["\']([^"\']+)', attrs, re.I)
            if match:
                ident = match.group(1)
            gaps.append({"n": index, "id": ident, "reason": reason})
    return gaps


def review_gaps(root: Path) -> dict:
    """Pages and sections the export left empty. Phase 4 authors these from Paper."""
    import run_config

    root = root.resolve()
    pages: list[dict] = []
    for path in _html_files(root):
        rel = path.relative_to(root / SOURCE).as_posix()
        if rel in {"index.html", "index.htm"}:
            continue
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            html = ""
        reasons: list[str] = []
        if run_config.page_is_empty(html):
            reasons.append("empty-page")
        sections = _section_gaps(html)
        if sections and "empty-page" not in reasons:
            reasons.append("empty-cms-section")
        if not reasons:
            continue
        pages.append({
            "file": rel,
            "slug": _slug_of(rel),
            "reasons": reasons,
            "sections": sections,
        })
    sitemap = _read(root / "qa" / "phase-4-sitemap.json") or {}
    known = {row["slug"] for row in pages}
    for row in sitemap.get("pages") or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if path in {"", "/"}:
            continue
        slug = str(row.get("slug") or path.strip("/").replace("/", "-"))
        if run_config.find_export_page(root, path) is not None:
            continue
        if slug in known:
            continue
        pages.append({
            "file": None,
            "path": path,
            "url": row.get("url"),
            "slug": slug,
            "reasons": ["absent"],
            "sections": [],
        })
    payload = {
        "generatedFrom": GENERATED_FROM,
        "ok": True,
        "pages": pages,
        "recordedAt": _now(),
    }
    dest = root / GAPS
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def gap_slugs(root: Path) -> list[str]:
    data = _read(root.resolve() / GAPS) or {}
    return [str(row.get("slug")) for row in data.get("pages") or [] if isinstance(row, dict) and row.get("slug")]


def record_gap_author(root: Path) -> dict:
    """Validate the agent's gap plan and lock every page that was not a gap."""
    root = root.resolve()
    expected = gap_slugs(root)
    plan = _read(root / GAP_PLAN)
    if plan is None and expected:
        raise FileNotFoundError(
            "need qa/phase-4-gap-plan.json — one row per source gap, status authored or residual"
        )
    rows = []
    if isinstance(plan, dict):
        rows = [row for row in plan.get("pages") or [] if isinstance(row, dict)]
    by_slug = {str(row.get("slug")): row for row in rows if row.get("slug")}
    errors: list[str] = []
    for slug in expected:
        row = by_slug.get(slug)
        if not row:
            errors.append(f"{slug} has no row in qa/phase-4-gap-plan.json")
            continue
        status = str(row.get("status") or "")
        if status not in {"authored", "residual"}:
            errors.append(f"{slug} status must be authored or residual")
        if status == "residual" and not str(row.get("note") or "").strip():
            errors.append(f"{slug} residual needs a note")
    extra = sorted(set(by_slug) - set(expected))
    for slug in extra:
        errors.append(f"{slug} is not a source gap — do not author pages the export already has")
    authored = {
        slug for slug, row in by_slug.items()
        if str(row.get("status") or "") == "authored"
    }
    fidelity = verify(root, allow_slugs=authored)
    errors.extend(fidelity)
    payload = {
        "generatedFrom": GENERATED_FROM,
        "ok": not errors,
        "pages": rows,
        "errors": errors,
        "recordedAt": _now(),
    }
    dest = root / GAP_AUTHOR
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise ValueError("; ".join(errors[:8]))
    return payload


def gap_author_ready(root: Path) -> bool:
    data = _read(root.resolve() / GAP_AUTHOR)
    return bool(data) and data.get("ok") is True and data.get("generatedFrom") == GENERATED_FROM


def write_phase_2_off(root: Path) -> Path:
    root = root.resolve()
    dest = root / PHASE_2_OFF
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "phase": "2",
                "applicable": False,
                "reason": "source folder is the ship — do not author a homepage",
                "ship": "source-html/index.html",
                "recordedAt": _now(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def phase_2_off(root: Path) -> bool:
    data = _read(root.resolve() / PHASE_2_OFF)
    return bool(data) and data.get("applicable") is False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("snapshot", "verify", "gaps", "record-gaps"):
        parser = sub.add_parser(name)
        parser.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.cmd == "snapshot":
            payload = snapshot(root)
            print(f"snapshot → {len(payload['signatures'])} html · {len(payload['assets'])} assets")
            return 0
        if args.cmd == "verify":
            errors = verify(root)
            if errors:
                for err in errors:
                    print(f"FAIL: {err}", file=sys.stderr)
                return 2
            print("source fidelity ok")
            return 0
        if args.cmd == "gaps":
            payload = review_gaps(root)
            print(f"source gaps → {len(payload['pages'])}  qa/source-gaps.json")
            return 0
        payload = record_gap_author(root)
        print(f"gap author ok → {len(payload['pages'])} pages")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
