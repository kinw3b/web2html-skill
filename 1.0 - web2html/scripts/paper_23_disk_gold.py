#!/usr/bin/env python3
"""2.3 — map ship bands to 1.2 source-section clips already on disk.

Does not talk to Paper MCP. Workers compare rebuild shots to these PNGs.

  python3 paper_23_disk_gold.py /path/to/project

Exit 0 all ship bands have source clips at 1600 / 768 / 390.
Exit 2 missing ship HTML, or a band has no clip.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_rebuild_shots as shots

GENERATED_FROM = "web2html/section-23-disk-gold"
OUT = Path("qa/paper-measure/disk-gold.json")
WIDTHS = (1600, 768, 390)
CLIP_RE = re.compile(r"^(\d{2})-(.+)\.png$", re.I)
def run_widths(root: Path) -> tuple[int, ...]:
    """Configured widths from qa/run-config.json (fast run = 1600 + 390)."""
    try:
        import run_config

        return tuple(run_config.widths(root))
    except Exception:  # noqa: BLE001
        return WIDTHS


LANDER = {
    1600: Path("capture/home-desktop/source-sections"),
    768: Path("capture/home-768/source-sections"),
    390: Path("capture/home-390/source-sections"),
}


def parse_widths(raw: str | None, root: Path | None = None) -> tuple[int, ...]:
    if not raw:
        return run_widths(root) if root is not None else WIDTHS
    out = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    return out or WIDTHS


def lander_dir(page: str, width: int) -> Path:
    slug = page or "home"
    if width >= 1400:
        return Path(f"capture/{slug}-desktop/source-sections")
    return Path(f"capture/{slug}-{width}/source-sections")


def ship_rel_for(page: str) -> Path:
    slug = page or "home"
    return Path("rebuild/index.html") if slug == "home" else Path(f"rebuild/{slug}.html")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def list_clips(folder: Path) -> list[dict]:
    if not folder.is_dir():
        return []
    rows: list[dict] = []
    for path in sorted(folder.iterdir()):
        match = CLIP_RE.match(path.name)
        if not match:
            continue
        slug = match.group(2)
        sidecar = path.with_suffix(".json")
        extra: dict = {}
        if sidecar.is_file():
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, dict):
                extra = payload
        rows.append(
            {
                "stem": path.stem,
                "slug": slug,
                "png": path,
                "json": sidecar if sidecar.is_file() else None,
                "id": str(extra.get("id") or ""),
                "jsonSlug": str(extra.get("slug") or ""),
                "tag": str(extra.get("tag") or ""),
            }
        )
    return rows


def match_clip(section_id: str, clips: list[dict]) -> dict | None:
    want = _norm(section_id)
    if not want:
        return None
    exact: list[dict] = []
    fuzzy: list[dict] = []
    for clip in clips:
        names = [
            clip.get("slug") or "",
            clip.get("jsonSlug") or "",
            clip.get("id") or "",
            clip.get("stem") or "",
        ]
        norms = [_norm(name) for name in names if name]
        if want in norms:
            exact.append(clip)
            continue
        if any(want in name or name in want for name in norms if len(name) >= 4 and len(want) >= 4):
            fuzzy.append(clip)
    if section_id == "footer":
        for clip in clips:
            if (clip.get("tag") or "").lower() == "footer" or _norm(clip.get("slug") or "") == "footer":
                exact.append(clip)
    if exact:
        return exact[0]
    if len(fuzzy) == 1:
        return fuzzy[0]
    return None


def relative_or_none(root: Path, path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_index(
    root: Path,
    *,
    page: str = "home",
    widths: tuple[int, ...] | None = None,
    ship_rel: Path | None = None,
) -> dict:
    root = root.resolve()
    widths = tuple(widths) if widths else run_widths(root)
    ship = root / (ship_rel or ship_rel_for(page))
    html = ship.read_text(encoding="utf-8") if ship.is_file() else ""
    ids = shots.ship_section_ids(html) if html else []
    clips_by_width = {width: list_clips(root / lander_dir(page, width)) for width in widths}
    sections: list[dict] = []
    missing: list[str] = []
    for sid in ids:
        source: dict[str, str | None] = {}
        sidecar: dict[str, str | None] = {}
        rebuild: dict[str, str | None] = {}
        for width in widths:
            clip = match_clip(sid, clips_by_width[width])
            source[str(width)] = relative_or_none(root, clip["png"] if clip else None)
            sidecar[str(width)] = relative_or_none(root, clip["json"] if clip else None)
            rebuild[str(width)] = relative_or_none(root, shots.shot_path(root, sid, width, page))
            if source[str(width)] is None:
                missing.append(f"{sid}@{width}")
        clip1600 = match_clip(sid, clips_by_width.get(1600) or clips_by_width[widths[0]])
        stem = (clip1600 or {}).get("stem") or ""
        numbered = re.match(r"^(\d{2})-(.+)$", stem)
        sections.append(
            {
                "id": sid,
                "nn": numbered.group(1) if numbered else None,
                "slug": numbered.group(2) if numbered else sid,
                "source": source,
                "sidecar": sidecar,
                "rebuild": rebuild,
            }
        )
    return {
        "generatedFrom": GENERATED_FROM,
        "ok": bool(ids) and not missing,
        "page": page,
        "widths": list(widths),
        "sections": sections,
        "missing": missing,
        "updated": _now_iso(),
    }


def write_index(root: Path, payload: dict, dest_rel: Path = OUT) -> Path:
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--page", default="home")
    ap.add_argument("--widths", default="")
    ap.add_argument("--receipt", default=str(OUT))
    args = ap.parse_args(argv)
    root = args.root.resolve()
    widths = parse_widths(args.widths or None, root)
    ship = ship_rel_for(args.page)
    if not (root / ship).is_file():
        print(f"FAIL: missing {ship.as_posix()}", file=sys.stderr)
        return 2
    payload = build_index(root, page=args.page, widths=widths, ship_rel=ship)
    dest = write_index(root, payload, Path(args.receipt))
    if not payload["ok"]:
        print(f"FAIL: {dest.relative_to(root)} missing {payload['missing']}", file=sys.stderr)
        return 2
    print(f"paper-23-disk-gold: ok {len(payload['sections'])} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
