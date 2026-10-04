#!/usr/bin/env python3
"""Pitfall #249 — the stage-5 page loop: one worker owns one interior page and
authors + compares it section by section until every section matches."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import page_loop
import section_22_gate as gate
import wave

PAGE = """---
import BaseLayout from '../layouts/BaseLayout.astro';
---
<BaseLayout title="About"><main>BODY</main></BaseLayout>
"""


def _project(root: Path, body: str, clips=("01-banner-section", "02-team-section")) -> Path:
    (root / "qa").mkdir(parents=True)
    (root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": [{"slug": "about"}]}))
    (root / "astro" / "src" / "pages").mkdir(parents=True)
    (root / "astro" / "package.json").write_text("{}")
    (root / "astro" / "src" / "pages" / "about.astro").write_text(PAGE.replace("BODY", body))
    dist = root / "astro" / "dist" / "about"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text(f"<html><body><header></header><main>{body}</main></body></html>")
    gold = root / "capture" / "about-desktop" / "source-sections"
    gold.mkdir(parents=True)
    for stem in clips:
        (gold / f"{stem}.png").write_bytes(gate.TINY_PNG)
    return root


def _fake_shoot(root: Path, slug: str) -> None:
    """What shoot() stores, without astro/Playwright."""
    data = page_loop.load(root, slug)
    data["lastShoot"] = {"at": "now", "pageSha": page_loop._sha(page_loop.page_src(root, slug))}
    data["coverage"] = page_loop.coverage(root, slug)
    page_loop.save(root, slug, data)


TWO = '<section id="intro"></section><section id="team"></section>'
SEEN = "1600 and 390 both show the two column split with the same heading wrap"


class PageLoopTest(unittest.TestCase):
    def test_page_is_open_until_every_band_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), TWO)
            self.assertTrue(any("no page loop yet" in e for e in page_loop.gate_errors(root)))
            _fake_shoot(root, "about")
            page_loop.record(root, "about", "intro", "match", SEEN)
            page_loop.record(root, "about", "team", "miss", SEEN)
            self.assertTrue(any("team: last verdict miss" in e for e in page_loop.page_errors(root, "about")))
            page_loop.record(root, "about", "team", "match", SEEN)
            self.assertEqual(page_loop.page_errors(root, "about"), [])
            self.assertEqual(page_loop.gate_errors(root), [])

    def test_editing_the_page_reopens_it_and_record_needs_a_fresh_shoot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), TWO)
            _fake_shoot(root, "about")
            for band in ("intro", "team"):
                page_loop.record(root, "about", band, "match", SEEN)
            src = page_loop.page_src(root, "about")
            src.write_text(src.read_text() + "\n<!-- edit -->\n")
            self.assertTrue(any("edited after the last look" in e for e in page_loop.page_errors(root, "about")))
            with self.assertRaises(ValueError):
                page_loop.record(root, "about", "intro", "match", SEEN)

    def test_demoted_and_uncovered_sections_fail(self) -> None:
        """The kp-avanta dodge: extra bands turned into <div aria-labelledby>."""
        body = '<section id="intro"></section><div aria-labelledby="x-title" id="x"></div>'
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), body)
            _fake_shoot(root, "about")
            page_loop.record(root, "about", "intro", "match", SEEN)
            errors = page_loop.page_errors(root, "about")
            self.assertTrue(any("<div aria-labelledby>" in e for e in errors), errors)
            self.assertTrue(any("02-team-section" in e for e in errors), errors)

    def test_residual_only_after_max_rounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), TWO)
            _fake_shoot(root, "about")
            with self.assertRaises(ValueError):
                page_loop.record(root, "about", "team", "residual", SEEN)
            for _ in range(page_loop.MAX_ROUNDS):
                page_loop.record(root, "about", "team", "miss", SEEN)
            page_loop.record(root, "about", "team", "residual", SEEN)
            page_loop.record(root, "about", "intro", "match", SEEN)
            self.assertEqual(page_loop.page_errors(root, "about"), [])

    def test_wave_plans_one_worker_per_open_page_with_an_owning_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), TWO)
            doc = wave.prepare(root, "p1", "page-loop")
            self.assertEqual([t["id"] for t in doc["tasks"]], ["loop-about"])
            spec = doc["tasks"][0]["spec"]
            self.assertIn("YOU OWN THIS PAGE", spec)
            self.assertIn("rebuild/about-raw.html", spec)
            self.assertIn("page_loop.py\" shoot", spec)
            self.assertIn("NEVER demote", spec)
            # a finished page is not re-dispatched
            _fake_shoot(root, "about")
            for band in ("intro", "team"):
                page_loop.record(root, "about", band, "match", SEEN)
            self.assertEqual(wave.prepare(root, "p2", "page-loop")["tasks"], [])


if __name__ == "__main__":
    unittest.main()
