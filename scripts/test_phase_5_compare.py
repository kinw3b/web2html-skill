#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import paper_23_clip_compare as compare
import paper_23_disk_gold as gold
import phase_5_compare as phase5
import section_22_gate as gate


def _plant_clip(root: Path, folder: str, stem: str, slug: str) -> None:
    dest = root / "capture" / folder / "source-sections"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{stem}.png").write_bytes(gate.TINY_PNG)
    (dest / f"{stem}.json").write_text(
        json.dumps({"id": stem.split("-", 1)[0], "slug": slug, "png": f"{stem}.png"})
        + "\n",
        encoding="utf-8",
    )


class Phase5CompareTest(unittest.TestCase):
    def test_page_and_width_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "about.html").write_text('<section id="hero"></section>')
            _plant_clip(root, "about-desktop", "01-hero", "hero")
            self.assertEqual(
                gold.main([str(root), "--page", "about", "--widths", "1600"]),
                0,
            )
            payload = json.loads((root / gold.OUT).read_text())
            self.assertEqual(payload["page"], "about")
            self.assertEqual(payload["widths"], [1600])
            skip = root / compare.SKIP
            skip.parent.mkdir(parents=True, exist_ok=True)
            skip.write_text(json.dumps({"skipped": True}) + "\n")
            self.assertEqual(
                compare.main([
                    str(root),
                    "--page",
                    "about",
                    "--widths",
                    "1600",
                    "--receipt",
                    "qa/paper-measure/about-clip.json",
                ]),
                0,
            )

    def test_53_fails_without_desktop_clips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            dist = root / "astro" / "dist" / "about"
            dist.mkdir(parents=True)
            (dist / "index.html").write_text('<section id="hero"></section>')
            (root / "qa" / "phase-4-pages.json").write_text(
                json.dumps({"pages": [{"slug": "about"}]}) + "\n"
            )
            self.assertEqual(phase5.main([str(root), "--mode", "desktop"]), 2)
            receipt = json.loads((root / "qa" / "phase-5-clip-compare.json").read_text())
            self.assertFalse(receipt["ok"])
            self.assertTrue(any("about-desktop" in item for item in receipt["missing"]))

    def test_54_fails_without_responsive_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            dist = root / "astro" / "dist" / "about"
            dist.mkdir(parents=True)
            (dist / "index.html").write_text('<section id="hero"></section>')
            (root / "qa" / "phase-4-pages.json").write_text(
                json.dumps({"pages": [{"slug": "about"}]}) + "\n"
            )
            _plant_clip(root, "about-desktop", "01-hero", "hero")
            self.assertEqual(phase5.main([str(root), "--mode", "responsive"]), 2)
            receipt = json.loads((root / "qa" / "phase-5-responsive.json").read_text())
            self.assertFalse(receipt["ok"])
            self.assertTrue(any("768" in item or "390" in item for item in receipt["missing"]))

    def test_section_gate_page_widths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "about.html").write_text('<section id="hero"></section>')
            _plant_clip(root, "about-desktop", "01-hero", "hero")
            self.assertEqual(
                gate.main([str(root), "--page", "about", "--widths", "1600"]),
                0,
            )
            self.assertEqual(gate.main([str(root), "--page", "about", "--widths", "768"]), 2)


if __name__ == "__main__":
    unittest.main()
