#!/usr/bin/env python3
"""2.1 — self-host Latin fonts into rebuild/fonts + css/fonts.css.

tokens.css only names families (`--font-sans-figtree: Figtree`). file://
cannot load Google Fonts, so index-raw / design-system stay on system-ui
until @font-face points at local woff2 (Pitfall #164 #59).

  python3 emit_fonts.py /path/to/project
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from scrape_light import basename_of, latin_font_urls, parse_font_faces

GENERATED_FROM = "web2html/emit-fonts"
RECEIPT = Path("qa/fonts-21.json")
FONTS_CSS = Path("rebuild/css/fonts.css")
FONTS_DIR = Path("rebuild/fonts")
LIBRARY = Path("design-library/library.json")
TOKENS = Path("rebuild/css/tokens.css")
SCRAPE_TOKENS = Path("source-site/scraped-tokens.md")
SCRAPE_ASSETS = Path("source-site/assets")
SCRAPE_HTML = Path("source-site/index.html")

GENERIC = {
    "system-ui",
    "sans-serif",
    "serif",
    "monospace",
    "ui-sans-serif",
    "ui-serif",
    "ui-monospace",
    "emoji",
    "cursive",
    "fantasy",
    "-apple-system",
    "blinkmacsystemfont",
}
WEIGHT_WORDS = {
    "thin": "100",
    "extralight": "200",
    "ultralight": "200",
    "light": "300",
    "regular": "400",
    "normal": "400",
    "book": "400",
    "medium": "500",
    "semibold": "600",
    "demibold": "600",
    "bold": "700",
    "extrabold": "800",
    "ultrabold": "800",
    "black": "900",
    "heavy": "900",
}

TOKEN_FONT_RE = re.compile(
    r"--font-(?!weight)([a-z0-9-]+)\s*:\s*([^;]+);",
    re.I,
)



def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").casefold()).strip("-")


def first_face(value: str) -> str:
    raw = (value or "").strip().strip("\"'")
    if not raw:
        return ""
    return raw.split(",")[0].strip().strip("\"'")


def is_generic(face: str) -> bool:
    return first_face(face).casefold() in GENERIC


def css_family(face: str) -> str:
    name = first_face(face)
    if not name:
        return ""
    if re.search(r"[\s]", name):
        return f'"{name}"'
    return name


def weight_from_name(name: str) -> str:
    stem = Path(name).stem.casefold()
    m = re.search(r"(?:^|[-_])([1-9]00)(?:$|[-_])", stem)
    if m:
        return m.group(1)
    for word, num in WEIGHT_WORDS.items():
        if num == "400":
            continue  # "normal" may describe style alongside "medium" weight.
        if re.search(rf"(?:^|[-_]){word}(?:$|[-_])", stem):
            return num
    return "400"


def library_families(root: Path) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    library = root / LIBRARY
    if library.is_file():
        try:
            payload = json.loads(library.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = {}
        for token in payload.get("proposedTokens") or []:
            if not isinstance(token, dict) or token.get("type") != "fontFamily":
                continue
            face = first_face(str(token.get("family") or token.get("paperValue") or token.get("value") or ""))
            if not face or is_generic(face) or slug(face) in seen:
                continue
            seen.add(slug(face))
            out.append({"family": face, "token": str(token.get("name") or "")})
    tokens = root / TOKENS
    if tokens.is_file():
        try:
            css = tokens.read_text(encoding="utf-8")
        except OSError:
            css = ""
        for name, value in TOKEN_FONT_RE.findall(css):
            if name.startswith("weight"):
                continue
            face = first_face(value)
            if not face or is_generic(face) or slug(face) in seen:
                continue
            seen.add(slug(face))
            out.append({"family": face, "token": f"--font-{name}"})
    return out


def scrape_table_faces(root: Path) -> list[dict]:
    """Recover legacy tables' missing style from the exact source CSS face.

    Hashed font names carry no style information. Never assume they are
    upright, or substitute the first file with a matching family.
    """
    html_path = root / SCRAPE_HTML
    source = []
    if html_path.is_file():
        html = html_path.read_text(encoding="utf-8", errors="replace")
        source = [
            {**face, "file": basename_of(face["url"]), "weight": face["weight"] or "400"}
            for face in latin_font_urls(parse_font_faces(html, html_path.as_uri()))
        ]
    md = root / SCRAPE_TOKENS
    rows: list[dict] = []
    headers: list[str] = []
    for line in md.read_text(encoding="utf-8").splitlines() if md.is_file() else []:
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if cells[0].lower() == "family":
            headers = [cell.lower() for cell in cells]
            continue
        row = dict(zip(headers, cells))
        if not row.get("file") or set(row["file"]) <= {"-", ":"}:
            continue
        family, filename = row["family"], row["file"]
        weight = row.get("weight", "400")
        if weight in {"—", "-", "?", ""}:
            weight = weight_from_name(filename)
        matches = [f for f in source if slug(f["family"]) == slug(family)
                   and f["weight"] == weight and f["file"] == filename]
        if row.get("style"):
            styled = [f for f in matches if f["style"] == row["style"]]
            if matches and not styled:
                raise ValueError(f"font style conflicts with source CSS: {filename}")
            matches = styled
        if matches:
            rows.extend(matches)
            continue
        style = row.get("style") or style_from_name(filename, family)
        if style is None:
            raise ValueError(f"unknown font style: {filename} — restore source-site/index.html @font-face metadata")
        urange = row.get("unicode-range", "")
        rows.append({"family": family, "weight": weight, "style": style,
                     "file": filename, "unicode": "" if urange == "full" else urange})
    return rows or source


def style_from_name(filename: str, family: str) -> str | None:
    name = Path(filename).stem.casefold()
    if "italic" in name:
        return "italic"
    if "oblique" in name:
        return "oblique"
    # Only explicitly upright names are evidence when CSS is unavailable.
    if slug(family) in slug(name) and re.search(r"regular|normal|roman|upright", name):
        return "normal"
    return None


def face_key(face: dict) -> tuple[str, str, str, str]:
    return (slug(face["family"]), " ".join((face.get("weight") or "400").split()),
            " ".join(face.get("style", "normal").lower().split()),
            re.sub(r"\s+", "", face.get("unicode", "")).upper())


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font_face_errors(root: Path) -> list[str]:
    """Read-only gate: CSS descriptors AND bytes must match the saved source."""
    root = root.resolve()
    css = root / FONTS_CSS
    if not css.is_file():
        return []
    errors = []
    try:
        source = scrape_table_faces(root)
    except ValueError as exc:
        return [str(exc)]
    faces = parse_font_faces(css.read_text(encoding="utf-8"), css.as_uri())
    if source and not faces:
        errors.append("fonts.css has no @font-face rules despite source fonts")
    for face in faces:
        path = root / FONTS_DIR / basename_of(face["url"])
        label = f"{face['family']} {face['weight'] or '400'} {face['style']}"
        if not path.is_file():
            errors.append(f"{label}: missing {path.name}")
            continue
        if not source:
            continue
        matches = [s for s in source if face_key(s) == face_key(face)]
        if not matches:
            errors.append(f"{label}: descriptors do not match a source @font-face")
            continue
        originals = [root / SCRAPE_ASSETS / s["file"] for s in matches]
        if not any(p.is_file() and file_hash(p) == file_hash(path) for p in originals):
            errors.append(f"{label}: font bytes do not match source style/weight — rerun emit_fonts.py")
    return errors


def existing_woff(root: Path) -> list[Path]:
    files: list[Path] = []
    for folder in (root / FONTS_DIR, root / SCRAPE_ASSETS):
        if not folder.is_dir():
            continue
        for ext in ("woff2", "woff", "ttf", "otf"):
            files.extend(sorted(folder.glob(f"*.{ext}")))
    return files


def match_file(family: str, files: list[Path]) -> list[Path]:
    key = slug(family)
    hits: list[Path] = []
    for path in files:
        stem = slug(path.stem)
        if key and key in stem:
            hits.append(path)
            continue
        # "Open Sauce One Regular" vs open-sauce-regular
        words = [w for w in key.split("-") if w not in {"one", "the"}]
        if words and all(w in stem for w in words[:2]):
            hits.append(path)
    return hits


def copy_into_rebuild(root: Path, src: Path, family: str, weight: str, style: str) -> Path:
    dest_dir = root / FONTS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Styles/subsets sharing family + weight must never overwrite each other.
    dest = dest_dir / f"{slug(family)}-{slug(weight)}-{slug(style)}-{file_hash(src)[:12]}{src.suffix.lower()}"
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def emit_fonts(root: Path) -> dict:
    root = root.resolve()
    families = library_families(root)
    scrape = scrape_table_faces(root)
    files = existing_woff(root)
    faces: list[dict] = []
    used: set[tuple] = set()
    planned: list[tuple[dict, Path]] = []

    wanted = {slug(f["family"]): f["family"] for f in families}
    if not wanted:
        for row in scrape:
            wanted[slug(row["family"])] = row["family"]

    for key, family in wanted.items():
        scrape_hits = [row for row in scrape if slug(row["family"]) == key]
        for row in scrape_hits:
            src = root / SCRAPE_ASSETS / row["file"]
            if not src.is_file():
                raise ValueError(f"missing exact source font: {src} — do not substitute another weight/style")
            planned.append(({**row, "family": family}, src))
        if scrape_hits:
            continue
        for src in match_file(family, files):
            weight = weight_from_name(src.name)
            style = style_from_name(src.name, family)
            if style is None:
                raise ValueError(f"unknown font style: {src.name} — restore source @font-face metadata")
            planned.append(({"family": family, "weight": weight, "style": style, "unicode": ""}, src))

    # Resolve metadata before copying; a bad input must not partially rewrite CSS.
    for row, src in planned:
        digest = file_hash(src)
        ident = (*face_key(row), digest)
        if ident in used:
            continue
        used.add(ident)
        dest = copy_into_rebuild(root, src, row["family"], row["weight"], row["style"])
        faces.append({"family": row["family"], "weight": row["weight"], "style": row["style"],
                      "unicode": row.get("unicode", ""), "file": dest.name,
                      "source": src.relative_to(root).as_posix(), "sha256": digest})

    css_dir = root / "rebuild" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "/* 2.1 self-host. Token values must match these font-family names. */",
        "/* file:// cannot load Google Fonts (Pitfall #164). */",
        "",
    ]
    for face in faces:
        fmt = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}[Path(face["file"]).suffix]
        lines += [
            "@font-face {",
            f"  font-family: {css_family(face['family'])};",
            f"  font-style: {face['style']};",
            f"  font-weight: {face['weight']};",
            "  font-display: swap;",
            f'  src: url("../fonts/{face["file"]}") format("{fmt}");',
        ]
        if face["unicode"]:
            lines.append(f"  unicode-range: {face['unicode']};")
        lines += ["}", ""]
    lines += [
        "html {",
        "  font-family: system-ui, sans-serif;",
        "}",
        "",
    ]
    dest = root / FONTS_CSS
    dest.write_text("\n".join(lines), encoding="utf-8")
    receipt = {
        "generatedFrom": GENERATED_FROM,
        "schemaVersion": 2,
        "ok": True,
        "families": sorted({f["family"] for f in faces}),
        "faces": faces,
        "fontsCss": FONTS_CSS.as_posix(),
        "updated": _now_iso(),
    }
    rec = root / RECEIPT
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = emit_fonts(args.root.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
