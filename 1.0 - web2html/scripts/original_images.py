#!/usr/bin/env python3
"""Original image bytes for stage 2 and stage 5.

1.1 used to save the first srcset candidate. Framer lists
`?scale-down-to=512` before the unscaled file, and both share a basename,
so the thumb occupied the original's name. Stage 2 / 5 then copied that
thumb, a Paper file-asset, or a re-encode. The ship must be a byte-copy of
the largest on-disk original (source-site/assets, source-html, capture
assets) — never a resized CDN URL and never app.paper.design/file-assets.
Pitfall #243.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXT = re.compile(r"\.(?:png|jpe?g|webp|avif|gif|svg)(?:$|[?#])", re.I)
RASTER_EXT = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif"}
RESIZE_KEYS = {
    "scale-down-to",
    "w",
    "width",
    "h",
    "height",
    "q",
    "quality",
    "fit",
    "dpr",
    "fm",
    "auto",
    "cs",
    "ixlib",
    "crop",
}
ABS_URL_RE = re.compile(r"https?://[^\"'()\s<>]+", re.I)
SRCSET_RE = re.compile(r"srcset\s*=\s*([\"'])(.*?)\1", re.I | re.S)
REF_RE = re.compile(
    r"""(?:src|href)\s*=\s*(["'])([^"']+)\1|url\(\s*(["']?)([^"')]+)\3\s*\)""",
    re.I,
)
PAPER_ASSET_RE = re.compile(r"app\.paper\.design/file-assets/|paper-asset://", re.I)
GENERATED_FROM = "web2html/bind_source_images"
RECEIPT = Path("qa/source-images.json")
UA = "Mozilla/5.0 web2html-original-images/2.39"


def original_url(url: str) -> str:
    """Strip CDN resize params. The path without them is the original file."""
    raw = (url or "").strip().strip("\"'").rstrip(".,;)")
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError:
        return raw
    if parsed.path.rstrip("/").endswith("/_next/image"):
        inner = urllib.parse.parse_qs(parsed.query).get("url", [""])[0]
        if inner:
            return original_url(urllib.parse.unquote(inner))
    marker = "/cdn-cgi/image/"
    if marker in parsed.path:
        rest = parsed.path.split(marker, 1)[1]
        idx = rest.find("http")
        if idx >= 0:
            return original_url(urllib.parse.unquote(rest[idx:]))
    kept = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in RESIZE_KEYS
    ]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(kept)))


def is_downscale_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    keys = {key.lower() for key, _ in urllib.parse.parse_qsl(parsed.query)}
    return bool(keys & RESIZE_KEYS)


def basename_of(url: str) -> str:
    try:
        name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    except ValueError:
        return ""
    return name.split("?")[0]


def is_image_url(url: str) -> bool:
    try:
        path = urllib.parse.urlparse(url).path
    except ValueError:
        return False
    return bool(IMAGE_EXT.search(path))


def collect_original_urls(html: str, page_url: str) -> list[str]:
    """One URL per basename: the unscaled original, not the srcset thumb."""
    order: list[str] = []
    chosen: dict[str, str] = {}

    def add(raw: str) -> None:
        clean = urllib.parse.urljoin(page_url, raw.strip().strip("\"'").rstrip(".,;)"))
        if clean.startswith("//"):
            clean = "https:" + clean
        orig = original_url(clean)
        if not is_image_url(orig):
            return
        name = basename_of(orig)
        if not name:
            return
        prev = chosen.get(name)
        if prev is None:
            chosen[name] = orig
            order.append(name)
            return
        if is_downscale_url(prev) and not is_downscale_url(orig):
            chosen[name] = orig

    for raw in ABS_URL_RE.findall(html or ""):
        add(raw)
    return [chosen[name] for name in order]


def srcset_max_width(html: str, name: str) -> int | None:
    best = 0
    for match in SRCSET_RE.finditer(html or ""):
        for part in match.group(2).split(","):
            bits = part.strip().split()
            if len(bits) < 2 or not bits[1].lower().endswith("w"):
                continue
            if basename_of(original_url(bits[0])) != name:
                continue
            try:
                best = max(best, int(bits[1][:-1]))
            except ValueError:
                continue
    return best or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return _webp_size(data)
    return None


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 8 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[index + 5 : index + 9])
            return width, height
        if marker in (0xD8, 0xD9):
            index += 2
            continue
        if index + 4 > len(data):
            return None
        index += 2 + struct.unpack(">H", data[index + 2 : index + 4])[0]
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    if data[12:16] == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if data[12:16] == b"VP8 " and len(data) >= 30:
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height
    return None


def _rank(path: Path) -> tuple[int, int]:
    size = image_size(path)
    pixels = (size[0] * size[1]) if size else 0
    try:
        nbytes = path.stat().st_size
    except OSError:
        nbytes = 0
    return pixels, nbytes


def _iter_image_files(folder: Path):
    if not folder.is_dir():
        return
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if "node_modules" in path.parts or path.name.startswith("."):
            continue
        if path.suffix.lower() in RASTER_EXT or path.suffix.lower() == ".svg":
            yield path


def source_dirs(root: Path) -> list[Path]:
    return [
        root / "source-site" / "assets",
        root / "source-html",
        root / "capture" / "assets",
        root / "capture" / "capture" / "assets",
        root / "capture" / "rebuild" / "images",
    ]


def gather_originals(root: Path) -> dict[str, Path]:
    """Largest file per basename across the source folders. Not the ship."""
    best: dict[str, Path] = {}
    for folder in source_dirs(root):
        for path in _iter_image_files(folder) or ():
            name = path.name
            prev = best.get(name)
            if prev is None or _rank(path) > _rank(prev):
                best[name] = path
    return best


def _read_htmls(paths: list[Path]) -> str:
    chunks = []
    for path in paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def source_html_paths(root: Path) -> list[Path]:
    paths = [root / "source-site" / "index.html"]
    source_html = root / "source-html"
    if source_html.is_dir():
        paths.extend(
            path
            for path in source_html.rglob("*.html")
            if "node_modules" not in path.parts
        )
    return [path for path in paths if path.is_file()]


def publish_ship_copies(root: Path, installed: dict[str, Path]) -> None:
    """Stage 2 / 5 read rebuild/images and astro/public/images, not the scrape thumb."""
    targets = [root / "rebuild" / "images"]
    if (root / "astro").is_dir():
        targets.append(root / "astro" / "public" / "images")
    for dest_dir in targets:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name, path in installed.items():
            if not path.is_file():
                continue
            dest = dest_dir / name
            if dest.resolve() == path.resolve():
                continue
            if not dest.is_file() or _rank(path) > _rank(dest):
                dest.write_bytes(path.read_bytes())


def install_originals(root: Path, originals: dict[str, Path]) -> dict[str, Path]:
    """Copy the largest file into source-site/assets when that copy is smaller."""
    assets = root / "source-site" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    installed: dict[str, Path] = {}
    for name, path in originals.items():
        dest = assets / name
        if dest.resolve() == path.resolve():
            installed[name] = dest
            continue
        if not dest.is_file() or _rank(path) > _rank(dest):
            dest.write_bytes(path.read_bytes())
        installed[name] = dest if dest.is_file() else path
    return installed


def fetch_missing(root: Path, originals: dict[str, Path]) -> list[str]:
    """Download the unscaled URL when the local file is missing or a srcset thumb."""
    html = _read_htmls(source_html_paths(root))
    if not html:
        return []
    notes: list[str] = []
    assets = root / "source-site" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for url in collect_original_urls(html, "https://example.invalid/"):
        # collect_original_urls already absolutized against a dummy base for
        # absolute URLs. Relative URLs are not in the light scrape.
        if not url.startswith("http"):
            continue
        name = basename_of(url)
        if not name:
            continue
        dest = assets / name
        local = originals.get(name)
        size = image_size(local) if local else None
        width = size[0] if size else 0
        wanted = srcset_max_width(html, name) or 0
        if local and local.is_file() and (not wanted or width >= wanted or width == 0):
            continue
        data = _download(url)
        if data is None:
            notes.append(f"could not download original {url}")
            continue
        if dest.is_file() and len(data) <= dest.stat().st_size and _rank(dest) >= (0, len(data)):
            continue
        dest.write_bytes(data)
        originals[name] = dest
        notes.append(f"saved original {name} ({len(data)} bytes)")
    return notes


def _download(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def ship_html_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    home = root / "rebuild" / "index.html"
    if home.is_file():
        paths.append(home)
    astro = root / "astro" / "src"
    if astro.is_dir():
        paths.extend(sorted(astro.rglob("*.astro")))
        paths.extend(sorted(astro.rglob("*.html")))
    return paths


def _refs(html: str) -> list[str]:
    found = []
    for match in REF_RE.finditer(html or ""):
        found.append(match.group(2) or match.group(4) or "")
    return [ref.strip() for ref in found if ref.strip()]


def resolve_ref(html_path: Path, ref: str, root: Path) -> Path | None:
    if ref.startswith(("data:", "http:", "https:", "//", "paper-asset:")):
        return None
    if ref.startswith("/images/") or ref.startswith("/img/"):
        rel = ref.lstrip("/")
        for base in (root / "astro" / "public", root / "rebuild"):
            cand = (base / rel).resolve()
            if cand.is_file():
                return cand
        return (root / "astro" / "public" / rel).resolve()
    return (html_path.parent / ref).resolve()


def check_ships(root: Path, hashes: set[str]) -> list[str]:
    errors: list[str] = []
    for html_path in ship_html_paths(root):
        try:
            html = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError as err:
            errors.append(f"{html_path.name}: {err}")
            continue
        if PAPER_ASSET_RE.search(html) or "scale-down-to=" in html:
            errors.append(
                f"{html_path.relative_to(root)} still points at a Paper file-asset "
                "or a scale-down-to URL. Use the source original."
            )
        for ref in _refs(html):
            if not _is_raster_ref(ref):
                continue
            if ref.startswith(("http:", "https:", "//")) or "scale-down-to=" in ref:
                errors.append(f"{html_path.relative_to(root)} uses remote image {ref}")
                continue
            if ref.startswith("data:image/") and not ref.startswith("data:image/svg"):
                errors.append(f"{html_path.relative_to(root)} embeds a raster data URI")
                continue
            path = resolve_ref(html_path, ref, root)
            if path is None or not path.is_file():
                errors.append(f"{html_path.relative_to(root)} missing image {ref}")
                continue
            digest = sha256_file(path)
            if digest not in hashes:
                errors.append(
                    f"{path.relative_to(root)} is not a byte-copy of a source original. "
                    "Copy the unscaled file from source-site/assets/. Do not re-encode, "
                    "do not download ?scale-down-to=, do not use a Paper file-asset."
                )
    return errors


def _is_raster_ref(ref: str) -> bool:
    path = urllib.parse.urlparse(ref.split("?")[0]).path or ref.split("?")[0]
    return Path(path).suffix.lower() in RASTER_EXT


def ledger_rows(originals: dict[str, Path], root: Path) -> list[dict]:
    rows = []
    for name in sorted(originals):
        path = originals[name]
        if not path.is_file():
            continue
        size = image_size(path)
        try:
            rel = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            rel = str(path)
        rows.append(
            {
                "name": name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "width": size[0] if size else None,
                "height": size[1] if size else None,
                "path": rel,
            }
        )
    return rows


def write_receipt(root: Path, payload: dict) -> Path:
    dest = root / RECEIPT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def load_receipt(root: Path) -> dict | None:
    path = root / RECEIPT
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def sync(root: Path, fetch: bool = True) -> dict:
    root = root.resolve()
    originals = gather_originals(root)
    notes = fetch_missing(root, originals) if fetch else []
    installed = install_originals(root, originals)
    publish_ship_copies(root, installed)
    rows = ledger_rows(installed, root)
    hashes = {row["sha256"] for row in rows}
    errors = check_ships(root, hashes)
    payload = {
        "generatedFrom": GENERATED_FROM,
        "ok": not errors,
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "originals": rows,
        "notes": notes,
        "checked": [str(path.relative_to(root)) for path in ship_html_paths(root)],
        "errors": errors,
    }
    write_receipt(root, payload)
    return payload


def ready(root: Path) -> bool:
    """True when the ship has no rasters, or every raster hashes to a receipt original."""
    root = root.resolve()
    ships = ship_html_paths(root)
    if not ships:
        return True
    referenced = False
    for path in ships:
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        if any(_is_raster_ref(ref) for ref in _refs(html)):
            referenced = True
            break
        if PAPER_ASSET_RE.search(html) or "scale-down-to=" in html:
            referenced = True
            break
    if not referenced:
        return True
    receipt = load_receipt(root)
    if not receipt or receipt.get("generatedFrom") != GENERATED_FROM or receipt.get("ok") is not True:
        return False
    hashes = {row.get("sha256") for row in receipt.get("originals") or [] if row.get("sha256")}
    return not check_ships(root, hashes)


