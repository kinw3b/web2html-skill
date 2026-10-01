#!/usr/bin/env python3
"""Original images: unscaled URL wins, ship rasters must match those bytes."""

from __future__ import annotations

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from original_images import (
    collect_original_urls,
    original_url,
    ready,
    sync,
)
from scrape_light import collect_plan


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


SRCSET = """
<img src="https://framerusercontent.com/images/hero.png"
     srcset="https://framerusercontent.com/images/hero.png?scale-down-to=512 512w, https://framerusercontent.com/images/hero.png?scale-down-to=1024 1024w, https://framerusercontent.com/images/hero.png 1456w">
<img src="https://example.com/logo.svg">
"""


class OriginalUrlTests(unittest.TestCase):
    def test_strips_scale_down_and_keeps_one_basename(self) -> None:
        self.assertEqual(
            original_url("https://framerusercontent.com/images/hero.png?scale-down-to=512"),
            "https://framerusercontent.com/images/hero.png",
        )
        urls = collect_original_urls(SRCSET, "https://example.com/")
        self.assertEqual(
            urls,
            [
                "https://framerusercontent.com/images/hero.png",
                "https://example.com/logo.svg",
            ],
        )

    def test_scrape_plan_drops_srcset_thumbs(self) -> None:
        plan = collect_plan(SRCSET, "https://example.com/")
        self.assertEqual(
            plan["images"],
            [
                "https://framerusercontent.com/images/hero.png",
                "https://example.com/logo.svg",
            ],
        )

    def test_ship_must_match_source_bytes(self) -> None:
        thumb = _png(8, 4, (1, 2, 3))
        original = _png(16, 8, (9, 8, 7))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "source-site" / "assets"
            assets.mkdir(parents=True)
            (assets / "hero.png").write_bytes(original)
            images = root / "rebuild" / "images"
            images.mkdir(parents=True)
            (images / "hero.png").write_bytes(thumb)
            (root / "rebuild" / "index.html").write_text(
                '<img src="images/hero.png">\n',
                encoding="utf-8",
            )
            self.assertFalse(ready(root))
            payload = sync(root, fetch=False)
            self.assertTrue(payload["ok"], payload["errors"])
            self.assertEqual((images / "hero.png").read_bytes(), original)
            self.assertTrue(ready(root))

    def test_rename_ok_when_bytes_match(self) -> None:
        original = _png(4, 4, (4, 5, 6))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "source-site" / "assets"
            assets.mkdir(parents=True)
            (assets / "abc.png").write_bytes(original)
            images = root / "rebuild" / "images"
            images.mkdir(parents=True)
            (images / "about.png").write_bytes(original)
            (root / "rebuild" / "index.html").write_text(
                '<img src="images/about.png">\n',
                encoding="utf-8",
            )
            payload = sync(root, fetch=False)
            self.assertTrue(payload["ok"], payload["errors"])

    def test_paper_file_asset_fails(self) -> None:
        original = _png(2, 2, (0, 0, 0))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "source-site" / "assets"
            assets.mkdir(parents=True)
            (assets / "abc.png").write_bytes(original)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                '<img src="https://app.paper.design/file-assets/abc.png">\n',
                encoding="utf-8",
            )
            payload = sync(root, fetch=False)
            self.assertFalse(payload["ok"])
            self.assertTrue(any("Paper" in err or "remote" in err for err in payload["errors"]))

    def test_capture_larger_file_replaces_thumb_in_source(self) -> None:
        thumb = _png(4, 2, (1, 1, 1))
        original = _png(12, 6, (2, 2, 2))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "source-site" / "assets"
            assets.mkdir(parents=True)
            (assets / "hero.png").write_bytes(thumb)
            capture = root / "capture" / "assets"
            capture.mkdir(parents=True)
            (capture / "hero.png").write_bytes(original)
            images = root / "rebuild" / "images"
            images.mkdir(parents=True)
            (root / "rebuild" / "index.html").write_text(
                '<img src="images/hero.png">\n',
                encoding="utf-8",
            )
            payload = sync(root, fetch=False)
            self.assertTrue(payload["ok"], payload["errors"])
            self.assertEqual((assets / "hero.png").read_bytes(), original)
            self.assertEqual((images / "hero.png").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
