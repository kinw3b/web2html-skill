#!/usr/bin/env python3
"""2.3 + /compare — viewport side-by-side pairs: source left, rebuild right.

The 1.2 clip compare (paper_23_clip_compare.py) pairs cropped element clips at
620px columns. This tool pairs FULL VIEWPORT windows at the same scroll stop so
a reviewer sees what a human sees in a split browser: heading wrap counts,
cards clipped or bleeding at the pane edge, band spacing, sticky chrome.

  python3 paper_23_side_by_side.py /path/to/project
  python3 paper_23_side_by_side.py /path/to/project --id pricing --id hero
  python3 paper_23_side_by_side.py /path/to/project --source live --source-url https://…

Source pane (default --source disk): crop capture/home-{desktop,768,390}/
fullpage.png (mandatory 1.2 artifact) at the matched clip's sidecar bbox.y —
the captured, 1.4-signed source at the same scroll stop, offline. Falls back
to the numbered 1.2 clip itself when fullpage.png is absent (legacy runs or a
tidied run folder). --source live re-shoots the live URL instead (index-paired
top-level sections; sticky-nav parity; needs network).

Rebuild pane: one Playwright launch, viewport W×H on file://rebuild/index.html,
each section top scrolled to the viewport top, animations off, fonts ready.

Stitch: label bar + source pane + 2px divider + rebuild pane, native scale, at
qa/side-by-side/<width>/NN-slug-side.png plus an index.html contact sheet.
Diff % (luminance > 16, same tolerance as paper_23_validate.py) is a HINT,
never the gate — font hinting never reaches zero. section_22_gate.py refuses
2.3 sign-off while qa/side-by-side/report.json is missing or stale (the ship
changed after the pairs were shot; the report stamps the ship fingerprint).

Invokable at any phase through the /compare skill (targeted --id runs); the
skill owns how fixes land under the current phase's write rules.

Exit 0 ok (or Playwright skipped) · 2 missing ship / no stops / rebuild
selector missing / --fail-over exceeded.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_disk_gold as gold
import paper_23_rebuild_shots as shots
import section_22_gate as gate

GENERATED_FROM = "web2html/section-23-side-by-side"
OUT = Path("qa/side-by-side/report.json")
SKIP = Path("qa/side-by-side/skip.json")
SHEET = Path("qa/side-by-side/index.html")
WIDTHS = (1600, 768, 390)
DEFAULT_HEIGHT = 1000
LABEL_H = 44
DIVIDER = 2
PAD_COLOR = (200, 200, 200)
LABEL_BG = (18, 18, 22)
DIFF_TOLERANCE = 16  # same luminance tolerance as paper_23_validate.py
FREEZE_CSS = (
    "*,*::before,*::after{animation:none!important;transition:none!important;"
    "scroll-behavior:auto!important}"
)
LIVE_STOPS_JS = (
    "document.querySelectorAll('body > header, main > section, body > section,"
    " body > footer')"
)


def run_widths(root: Path) -> tuple[int, ...]:
    """Configured widths from qa/run-config.json (fast run = 1600 + 390)."""
    try:
        import run_config

        return tuple(run_config.widths(root))
    except Exception:  # noqa: BLE001
        return WIDTHS


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def fullpage_path(page: str, width: int) -> Path:
    """1.2 mandatory full-page capture for one breakpoint lander."""
    slug = page or "home"
    folder = f"{slug}-desktop" if width >= 1400 else f"{slug}-{width}"
    return Path(f"capture/{folder}/fullpage.png")


def sidecar_top(sidecar: Path | None) -> int | None:
    """bbox.y of a 1.2 clip sidecar — the clip's top inside fullpage.png."""
    if sidecar is None or not sidecar.is_file():
        return None
    payload = _read_json(sidecar)
    if not payload:
        return None
    box = payload.get("bbox") if isinstance(payload.get("bbox"), dict) else {}
    for key in ("y", "top"):
        value = box.get(key, payload.get(key))
        if isinstance(value, (int, float)) and value >= 0:
            return int(value)
    return None


def crop_box(page_h: int, y: int, height: int) -> tuple[int, int]:
    """(top, box height) clamped to the page — last stops crop short."""
    top = max(0, min(y, max(page_h - 1, 0)))
    return top, max(1, min(height, page_h - top))


def build_stops(
    root: Path,
    page: str,
    widths: tuple[int, ...],
    ids: list[str] | None = None,
) -> tuple[list[dict], list[str]]:
    """Ship bands × matched 1.2 clips, one row per band with per-width tops."""
    ship = root / gold.ship_rel_for(page)
    html = ship.read_text(encoding="utf-8") if ship.is_file() else ""
    available = shots.ship_section_ids(html)
    wanted = list(ids) if ids else available
    missing: list[str] = []
    stops: list[dict] = []
    clips_by_width = {
        width: gold.list_clips(root / gold.lander_dir(page, width)) for width in widths
    }
    for sid in wanted:
        if sid not in available:
            missing.append(f"{sid} not in ship")
            continue
        row: dict = {"id": sid, "nn": None, "slug": sid, "source": {}, "sidecar": {}}
        for width in widths:
            clip = gold.match_clip(sid, clips_by_width[width])
            row["source"][str(width)] = clip
            row["sidecar"][str(width)] = sidecar_top(clip["json"] if clip else None)
            if clip and row["nn"] is None:
                stem = re.match(r"^(\d{2})-(.+)$", clip.get("stem") or "")
                if stem:
                    row["nn"], row["slug"] = stem.group(1), stem.group(2)
        stops.append(row)
    return stops, missing


def safe_stem(nn: str | None, slug: str, width: int) -> str:
    number = nn if nn and re.fullmatch(r"\d{2}", nn) else "00"
    name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", slug).strip("-") or "section"
    return f"{number}-{name}-{width}"


def pane_dir(width: int) -> Path:
    return OUT.parent / str(width)


def source_pane_path(root: Path, stop: dict, width: int) -> Path:
    return root / pane_dir(width) / f"{safe_stem(stop['nn'], stop['slug'], width)}-source.png"


def rebuild_pane_path(root: Path, stop: dict, width: int) -> Path:
    return root / pane_dir(width) / f"{safe_stem(stop['nn'], stop['slug'], width)}-rebuild.png"


def find_clip_top(fullpage, clip) -> int | None:
    """Fallback when the sidecar has no bbox: locate the clip's first row."""
    fw, fh = fullpage.size
    cw, ch = clip.size
    if cw > fw or ch > fh:
        return None
    first = clip.crop((0, 0, cw, 1)).tobytes()
    mid_clip = clip.crop((0, ch // 2, cw, ch // 2 + 1)).tobytes()
    for y in range(0, fh - ch + 1, 2):
        if fullpage.crop((0, y, cw, y + 1)).tobytes() == first:
            mid = y + ch // 2
            if mid < fh and fullpage.crop((0, mid, cw, mid + 1)).tobytes() == mid_clip:
                return y
    return None


def source_pane_disk(root: Path, page: str, width: int, stop: dict, height: int):
    """Crop the 1.2 fullpage.png at the stop's top; fall back to the clip."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow guard
        return None, "no-pillow"
    clip = stop["source"].get(str(width))
    clip_png = clip["png"] if clip else None
    full = root / fullpage_path(page, width)
    if full.is_file():
        page_img = Image.open(full).convert("RGB")
        fw, fh = page_img.size
        scale = width / fw if fw else 1.0
        top = stop["sidecar"].get(str(width))
        if top is None and clip_png is not None and Path(clip_png).is_file():
            top = find_clip_top(page_img, Image.open(clip_png).convert("RGB"))
        if top is None:
            top = 0
        y = int(top * scale)
        box_top, box_h = crop_box(fh, y, int(height / scale) if scale else height)
        pane = page_img.crop((0, box_top, fw, box_top + box_h))
        if scale != 1.0:
            pane = pane.resize((width, int(pane.size[1] * scale)), Image.LANCZOS)
        return pane, "disk"
    if clip_png is not None and Path(clip_png).is_file():
        return Image.open(clip_png).convert("RGB"), "clip"
    return None, "missing"


def _shoot_viewports(
    url: str,
    stops: list[dict],
    widths: tuple[int, ...],
    height: int,
    dest_for,
    selector_for,
    *,
    strict: bool,
) -> list[dict]:
    """One Playwright launch: viewport shots at every stop × width."""
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    out: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in widths:
                view = browser.new_page(viewport={"width": width, "height": height})
                view.goto(url, wait_until="load")
                view.add_style_tag(content=FREEZE_CSS)
                view.evaluate("document.fonts && document.fonts.ready")
                view.evaluate("window.scrollTo(0, 0)")
                for index, stop in enumerate(stops):
                    selector = selector_for(stop, index)
                    dest = dest_for(stop, width)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if selector and view.locator(selector).count() == 0:
                        if strict:
                            out.append(
                                {"id": stop["id"], "width": width, "path": None,
                                 "error": f"missing {selector}"}
                            )
                        else:
                            out.append(
                                {"id": stop["id"], "width": width, "path": None,
                                 "error": None}
                            )
                        continue
                    if selector:
                        view.evaluate(
                            """(sel) => {
                                const el = document.querySelector(sel);
                                if (el) window.scrollTo(
                                    0, Math.max(0, el.getBoundingClientRect().top
                                    + window.scrollY));
                            }""",
                            selector,
                        )
                    else:  # live source: index-paired top-level section
                        view.evaluate(
                            """(i) => {
                                const els = """
                            + LIVE_STOPS_JS
                            + """;
                                const el = els[i];
                                if (el) window.scrollTo(
                                    0, Math.max(0, el.getBoundingClientRect().top
                                    + window.scrollY));
                            }""",
                            index,
                        )
                    view.screenshot(path=str(dest))
                    out.append(
                        {"id": stop["id"], "width": width, "path": dest.name,
                         "error": None}
                    )
                view.close()
        finally:
            browser.close()
    return out


def capture_rebuild(root: Path, stops: list[dict], widths: tuple[int, ...],
                    height: int, page: str = "home") -> list[dict]:
    ship_rel = gold.ship_rel_for(page)
    url = (root / ship_rel).resolve().as_uri()
    return _shoot_viewports(
        url, stops, widths, height,
        lambda stop, width: rebuild_pane_path(root, stop, width),
        lambda stop, index: shots.locator_selector(stop["id"]),
        strict=True,
    )


def capture_live(root: Path, stops: list[dict], widths: tuple[int, ...],
                 height: int, url: str) -> list[dict]:
    return _shoot_viewports(
        url, stops, widths, height,
        lambda stop, width: source_pane_path(root, stop, width),
        lambda stop, index: None,
        strict=False,
    )


def pad_pair(left, right):
    """Same-size panes; the shorter one pads with PAD_COLOR (height drift shows)."""
    from PIL import Image

    width = max(left.size[0], right.size[0])
    height = max(left.size[1], right.size[1])

    def fit(img: Image.Image) -> Image.Image:
        if img.size == (width, height):
            return img
        canvas = Image.new("RGB", (width, height), PAD_COLOR)
        canvas.paste(img, (0, 0))
        return canvas

    return fit(left), fit(right)


def diff_pct(left, right) -> float | None:
    """Share of pixels whose luminance differs beyond DIFF_TOLERANCE."""
    try:
        from PIL import ImageChops
    except ImportError:  # pragma: no cover - Pillow guard
        return None
    a, b = pad_pair(left, right)
    delta = ImageChops.difference(a, b).convert("L").point(
        lambda v: 255 if v > DIFF_TOLERANCE else 0
    )
    total = a.size[0] * a.size[1]
    return round(delta.histogram()[255] * 100.0 / total, 2) if total else None


def stitch(left, right, dest: Path, left_label: str, right_label: str, width: int) -> bool:
    """Native-scale pair: label bar, source pane, divider, rebuild pane."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover - Pillow guard
        return False
    left_s, right_s = pad_pair(left, right)
    pane_h = max(left_s.size[1], right_s.size[1])
    canvas = Image.new("RGB", (width * 2 + DIVIDER, LABEL_H + pane_h), LABEL_BG)
    canvas.paste(left_s, (0, LABEL_H))
    canvas.paste(right_s, (width + DIVIDER, LABEL_H))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 14), left_label, fill=(170, 170, 180))
    draw.text((width + DIVIDER + 10, 14), right_label, fill=(170, 170, 180))
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)
    return True


def write_skip(root: Path, reason: str) -> Path:
    dest = root / SKIP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": True,
                "skipped": True,
                "reason": reason,
                "updated": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def write_sheet(root: Path, payload: dict) -> Path:
    dest = root / SHEET
    rows: list[str] = []
    for stop in payload.get("stops") or []:
        side = stop.get("side")
        if not side:
            continue
        diff = stop.get("diffPct")
        badge = "—" if diff is None else f"{diff}%"
        rows.append(
            f"<figure><figcaption>{stop.get('width')}px · "
            f"{stop.get('nn') or '00'}-{stop.get('slug')} · diff {badge}</figcaption>"
            f"<img src=\"{side}\" alt=\"source left, rebuild right at "
            f"{stop.get('width')}px\"></figure>"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "<!doctype html><meta charset=utf-8><title>2.3 viewport pairs</title>"
        "<style>body{margin:0;background:#121216;color:#eee;font:14px system-ui}"
        "figure{margin:0 0 28px}figcaption{padding:8px 12px;color:#9a9aa4}"
        "img{width:100%;display:block;border:0}</style>"
        f"<h1 style=\"padding:12px\">2.3 viewport pairs · {payload.get('mode')} · "
        f"{payload.get('updated')}</h1>" + "".join(rows) + "\n",
        encoding="utf-8",
    )
    return dest


def compare_project(
    root: Path,
    *,
    page: str = "home",
    widths: tuple[int, ...] | None = None,
    height: int = DEFAULT_HEIGHT,
    source_mode: str = "disk",
    source_url: str = "",
    ids: list[str] | None = None,
) -> dict:
    """Pair panes already on disk (shot by capture_rebuild / capture_live)."""
    root = root.resolve()
    widths = tuple(widths) if widths else run_widths(root)
    stops, missing = build_stops(root, page, widths, ids=ids)
    (root / OUT.parent).mkdir(parents=True, exist_ok=True)
    for width in widths:
        (root / pane_dir(width)).mkdir(parents=True, exist_ok=True)
    ship_rel = gold.ship_rel_for(page)
    rows: list[dict] = []
    sides = 0
    for stop in stops:
        for width in widths:
            key = str(width)
            stem = safe_stem(stop["nn"], stop["slug"], width)
            row = {
                "id": stop["id"],
                "nn": stop["nn"],
                "slug": stop["slug"],
                "width": width,
                "sourceMode": source_mode,
                "sourceY": stop["sidecar"].get(key),
                "sourcePane": None,
                "rebuildPane": None,
                "side": None,
                "diffPct": None,
            }
            left = None
            mode = source_mode
            live_pane = source_pane_path(root, stop, width)
            if source_mode == "live" and live_pane.is_file():
                try:
                    from PIL import Image

                    left = Image.open(live_pane).convert("RGB")
                except (ImportError, OSError, ValueError):
                    left = None
            if left is None:
                left, mode = source_pane_disk(root, page, width, stop, height)
            row["sourceMode"] = mode
            rebuild_pane = rebuild_pane_path(root, stop, width)
            if left is not None:
                row["sourcePane"] = f"{pane_dir(width)}/{stem}-source.png"
                if mode != "live" or not live_pane.is_file():
                    left.save(root / row["sourcePane"])
            if rebuild_pane.is_file():
                row["rebuildPane"] = f"{pane_dir(width)}/{stem}-rebuild.png"
            else:
                missing.append(f"{stop['id']}@{width} rebuild pane")
            if left is not None and row["rebuildPane"]:
                try:
                    from PIL import Image

                    right = Image.open(rebuild_pane).convert("RGB")
                except (ImportError, OSError, ValueError):
                    right = None
                if right is not None:
                    row["diffPct"] = diff_pct(left, right)
                    side_rel = f"{pane_dir(width)}/{stem}-side.png"
                    if stitch(
                        left,
                        right,
                        root / side_rel,
                        f"SOURCE · {mode} · {width}px · {stop['nn'] or '00'}-{stop['slug']}",
                        f"REBUILD · {ship_rel.as_posix()} · {width}px",
                        width,
                    ):
                        row["side"] = side_rel
                        sides += 1
            if left is None:
                missing.append(f"{stop['id']}@{width} source pane")
            rows.append(row)
    payload = {
        "generatedFrom": GENERATED_FROM,
        "ok": bool(rows) and not missing,
        "mode": source_mode,
        "page": page,
        "widths": list(widths),
        "viewportHeight": height,
        "rebuild": ship_rel.as_posix(),
        "sourceUrl": source_url if source_mode == "live" else None,
        "stops": rows,
        "sides": sides,
        "missing": missing,
        "shipFingerprint": gate.ship_fingerprint(root),
        "updated": _now_iso(),
    }
    (root / OUT).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if sides:
        write_sheet(root, payload)
    skip = root / SKIP
    if skip.is_file():
        skip.unlink()
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--page", default="home")
    ap.add_argument("--widths", default="")
    ap.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    ap.add_argument("--source", choices=("disk", "live"), default="disk")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--id", action="append", dest="ids",
                    help="section id to target (repeatable; default: every band)")
    ap.add_argument(
        "--fail-over",
        type=float,
        default=0.0,
        help="exit 2 when any pair's diff %% exceeds this (0 = off)",
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    ship_rel = gold.ship_rel_for(args.page)
    if not (root / ship_rel).is_file():
        print(f"FAIL: missing {ship_rel.as_posix()}", file=sys.stderr)
        return 2
    if args.source == "live" and not args.source_url:
        print("FAIL: --source live needs --source-url", file=sys.stderr)
        return 2
    widths = gold.parse_widths(args.widths or None, root)
    stops, stop_missing = build_stops(root, args.page, widths, ids=args.ids)
    if not stops:
        print(
            f"FAIL: no targetable <section id> in {ship_rel.as_posix()} "
            f"({stop_missing or 'ship has no sections'})",
            file=sys.stderr,
        )
        return 2
    try:
        import playwright.sync_api  # noqa: F401  type: ignore[import-not-found]
    except ImportError:
        write_skip(root, "Playwright not installed — read the 1.2 clip side-by-sides")
        print("paper-23-side-by-side: skipped (no Playwright)")
        return 0
    rebuild_rows = capture_rebuild(root, stops, widths, args.height, args.page)
    errors = [row for row in rebuild_rows if row.get("error")]
    if errors:
        for row in errors:
            print(f"FAIL: {row['id']}@{row['width']} {row['error']}", file=sys.stderr)
        return 2
    if args.source == "live":
        capture_live(root, stops, widths, args.height, args.source_url)
    payload = compare_project(
        root,
        page=args.page,
        widths=widths,
        height=args.height,
        source_mode=args.source,
        source_url=args.source_url,
        ids=args.ids,
    )
    print(
        f"paper-23-side-by-side: ok {len(payload['stops'])} pairs "
        f"({payload['sides']} side-by-sides at {', '.join(str(w) for w in widths)})"
    )
    if args.fail_over:
        hot = [
            row for row in payload["stops"]
            if row.get("diffPct") is not None and row["diffPct"] > args.fail_over
        ]
        if hot:
            worst = max(hot, key=lambda row: row["diffPct"])
            print(
                f"FAIL: {len(hot)} pairs over {args.fail_over}% diff — worst "
                f"{worst['id']}@{worst['width']} {worst['diffPct']}% "
                f"({worst['side']})",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
