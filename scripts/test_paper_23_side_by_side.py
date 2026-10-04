#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import paper_23_side_by_side as sbs
import section_22_gate as gate

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:  # pragma: no cover - Pillow guard
    HAS_PIL = False


def _plant(root: Path, *, fullpage: bool = True) -> None:
    (root / "rebuild").mkdir()
    (root / "rebuild" / "index.html").write_text(
        '<section id="hero"></section><section id="pricing"></section>',
        encoding="utf-8",
    )
    for folder, width in (("home-desktop", 1600), ("home-768", 768), ("home-390", 390)):
        lander = root / "capture" / folder
        sections = lander / "source-sections"
        sections.mkdir(parents=True, exist_ok=True)
        if fullpage and HAS_PIL:
            Image.new("RGB", (width, 3000), (240, 240, 240)).save(lander / "fullpage.png")
        for nn, slug, top in (("01", "hero", 200), ("02", "pricing", 1400)):
            png = sections / f"{nn}-{slug}.png"
            if HAS_PIL:
                Image.new("RGB", (width, 900), (200, 210, 220)).save(png)
            else:
                png.write_bytes(gate.TINY_PNG)
            (sections / f"{nn}-{slug}.json").write_text(
                json.dumps(
                    {"id": slug, "slug": slug, "bbox": {"x": 0, "y": top, "w": width, "h": 900}}
                )
                + "\n",
                encoding="utf-8",
            )


def _plant_rebuild_panes(root: Path, widths=(1600,)) -> None:
    for width in widths:
        dest = root / sbs.pane_dir(width)
        dest.mkdir(parents=True, exist_ok=True)
        for nn, slug in (("01", "hero"), ("02", "pricing")):
            (dest / f"{nn}-{slug}-{width}-rebuild.png").write_bytes(gate.TINY_PNG)


class StopsTest(unittest.TestCase):
    def test_build_stops_maps_clips_and_sidecar_tops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            stops, missing = sbs.build_stops(root, "home", (1600,))
            self.assertEqual(missing, [])
            self.assertEqual([stop["id"] for stop in stops], ["hero", "pricing"])
            self.assertEqual(stops[0]["nn"], "01")
            self.assertEqual(stops[0]["slug"], "hero")
            self.assertEqual(stops[0]["sidecar"]["1600"], 200)
            self.assertEqual(stops[1]["sidecar"]["1600"], 1400)

    def test_unknown_id_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            stops, missing = sbs.build_stops(root, "home", (1600,), ids=["nope"])
            self.assertEqual(stops, [])
            self.assertEqual(missing, ["nope not in ship"])

    def test_crop_box_clamps_to_page(self) -> None:
        self.assertEqual(sbs.crop_box(3000, 2900, 1000), (2900, 100))
        self.assertEqual(sbs.crop_box(3000, -5, 100), (0, 100))
        self.assertEqual(sbs.crop_box(500, 200, 1000), (200, 300))


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class CompareTest(unittest.TestCase):
    def test_pairs_source_left_rebuild_right(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            _plant_rebuild_panes(root)
            payload = sbs.compare_project(root, widths=(1600,))
            self.assertTrue(payload["ok"], payload["missing"])
            self.assertEqual(payload["sides"], 2)
            hero = payload["stops"][0]
            self.assertEqual(hero["sourceMode"], "disk")
            side = root / str(hero["side"])
            self.assertTrue(side.is_file())
            canvas = Image.open(side)
            self.assertEqual(canvas.size[0], 1600 * 2 + sbs.DIVIDER)
            self.assertEqual(canvas.size[1], sbs.LABEL_H + 1000)
            self.assertTrue((root / sbs.SHEET).is_file())
            self.assertTrue((root / sbs.OUT).is_file())

    def test_clip_fallback_when_fullpage_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root, fullpage=False)
            _plant_rebuild_panes(root)
            payload = sbs.compare_project(root, widths=(1600,))
            self.assertTrue(payload["ok"], payload["missing"])
            self.assertEqual(payload["stops"][0]["sourceMode"], "clip")

    def test_missing_source_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root, fullpage=False)
            for clip in (root / "capture" / "home-desktop" / "source-sections").glob("*"):
                clip.unlink()
            _plant_rebuild_panes(root)
            payload = sbs.compare_project(root, widths=(1600,))
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["missing"])

    def test_diff_pct_zero_for_identical_panes(self) -> None:
        left = Image.new("RGB", (40, 40), (10, 20, 30))
        right = Image.new("RGB", (40, 40), (10, 20, 30))
        self.assertEqual(sbs.diff_pct(left, right), 0.0)
        other = Image.new("RGB", (40, 40), (200, 200, 200))
        self.assertGreater(sbs.diff_pct(left, other), 90.0)

    def test_stitch_pads_shorter_pane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "side.png"
            left = Image.new("RGB", (100, 50), (255, 255, 255))
            right = Image.new("RGB", (100, 80), (0, 0, 0))
            self.assertTrue(sbs.stitch(left, right, dest, "SOURCE", "REBUILD", 100))
            self.assertEqual(Image.open(dest).size, (202, sbs.LABEL_H + 80))


def _plant_interior(root: Path, slug: str = "about") -> None:
    """Interior clips + built dist page — the phase-5 /compare pair source."""
    dist = root / "astro" / "dist" / slug
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        '<section id="about-hero"></section>', encoding="utf-8"
    )
    lander = root / "capture" / f"{slug}-desktop"
    sections = lander / "source-sections"
    sections.mkdir(parents=True, exist_ok=True)
    if HAS_PIL:
        Image.new("RGB", (1600, 3000), (240, 240, 240)).save(lander / "fullpage.png")
        png = sections / "01-about-hero.png"
        Image.new("RGB", (1600, 900), (200, 210, 220)).save(png)
    else:
        (sections / "01-about-hero.png").write_bytes(gate.TINY_PNG)
    (sections / "01-about-hero.json").write_text(
        json.dumps({"id": "about-hero", "slug": "about-hero",
                    "bbox": {"x": 0, "y": 200, "w": 1600, "h": 900}}) + "\n",
        encoding="utf-8",
    )


class InteriorCompareTest(unittest.TestCase):
    """Phase 5: --page {slug} pairs the built interior, per-slug output dirs."""

    @unittest.skipUnless(HAS_PIL, "Pillow not installed")
    def test_interior_pairs_land_in_the_slug_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant_interior(root)
            # Panes "shot" from astro/dist/about/index.html (capture_rebuild output).
            dest = root / sbs.pane_dir(1600, "about")
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "01-about-hero-1600-rebuild.png").write_bytes(gate.TINY_PNG)
            payload = sbs.compare_project(
                root,
                page="about",
                widths=(1600,),
                ship_rel=Path("astro/dist/about/index.html"),
            )
            self.assertTrue(payload["ok"], payload["missing"])
            self.assertEqual(payload["page"], "about")
            self.assertEqual(payload["rebuild"], "astro/dist/about/index.html")
            self.assertEqual(payload["sides"], 1)
            report = root / "qa" / "side-by-side" / "about" / "report.json"
            self.assertTrue(report.is_file())
            # The homepage report is untouched — per-slug dirs never clobber it.
            self.assertFalse((root / sbs.OUT).exists())
            side = root / str(payload["stops"][0]["side"])
            self.assertTrue(side.is_file())
            self.assertIn("side-by-side/about", payload["stops"][0]["side"])

    def test_interior_fingerprint_tracks_the_built_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant_interior(root)
            ship = Path("astro/dist/about/index.html")
            first = sbs.ship_fingerprint_for(root, ship)
            (root / ship).write_text('<section id="about-hero">patched</section>', encoding="utf-8")
            self.assertNotEqual(first, sbs.ship_fingerprint_for(root, ship))
            # Home keeps the 2.3 fingerprint.
            (root / "rebuild").mkdir(parents=True)
            (root / "rebuild" / "index.html").write_text("<main></main>", encoding="utf-8")
            self.assertEqual(
                sbs.ship_fingerprint_for(root, Path("rebuild/index.html")),
                gate.ship_fingerprint(root),
            )

    def test_main_refuses_a_missing_ship(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = sbs.main([str(root), "--page", "about",
                             "--ship", "astro/dist/about/index.html"])
            self.assertEqual(code, 2)

    def test_skip_receipt_lands_in_the_slug_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sbs.write_skip(root, "Playwright not installed", "about")
            self.assertTrue((root / "qa" / "side-by-side" / "about" / "skip.json").is_file())
            self.assertFalse((root / sbs.SKIP).exists())


class GateStalenessTest(unittest.TestCase):
    def test_gate_requires_fresh_side_by_side(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            errors = " ".join(gate.gate_errors(root))
            self.assertNotIn("side-by-side", errors)
            ship = root / gate.SHIP
            ship.write_text(ship.read_text(encoding="utf-8") + "<!-- patch -->\n",
                            encoding="utf-8")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("stale", errors)
            gate.install_passing_side_by_side(root)  # pairs re-run after the patch
            self.assertNotIn("stale", " ".join(gate.gate_errors(root)))

    def test_legacy_report_without_fingerprint_falls_back_to_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            report = root / gate.SIDE_BY_SIDE
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload.pop("shipFingerprint", None)
            report.write_text(json.dumps(payload), encoding="utf-8")
            ship = root / gate.SHIP
            old = ship.stat().st_mtime - 60
            os.utime(report, (old, old))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("stale", errors)

    def test_gate_requires_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.SIDE_BY_SIDE).unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("paper_23_side_by_side.py", errors)

    def test_skip_receipt_satisfies_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.SIDE_BY_SIDE).unlink()
            sbs.write_skip(root, "Playwright not installed")
            errors = " ".join(gate.gate_errors(root))
            self.assertNotIn("side-by-side", errors)


if __name__ == "__main__":
    unittest.main()
