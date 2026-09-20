#!/usr/bin/env python3
"""Fixtures for type-align inherit + census + verify (Pitfall #94).

Skip-link / invented meta are not involved. Heading rank stays the
heading_promote tests' job.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from heading_promote import promote_visual_headings
from semantics_pass import apply_semantics
from type_align import (
    align_matches,
    census_type_align,
    compare_row,
    size_matches_token,
    write_census,
)

import importlib.util

_cspec = importlib.util.spec_from_file_location(
    "census_type_align_cli", _SCRIPTS / "census-type-align.py"
)
_census_cli = importlib.util.module_from_spec(_cspec)
assert _cspec.loader
_cspec.loader.exec_module(_census_cli)


def _page(*sections: str) -> str:
    return (
        '<!DOCTYPE html><html lang="en"><body>'
        '<div id="paper-root" class="paper-semantic">'
        '<nav id="nav"><a href="/">Home</a></nav>'
        '<main style="display: contents">'
        + "".join(sections)
        + "</main></div></body></html>"
    )


class InheritAlignOnRetagTest(unittest.TestCase):
    def test_centered_parent_title_keeps_center(self) -> None:
        html = _page(
            '<section id="mission">'
            '<div class="flex flex-col justify-center text-center w-full">'
            '<div class="text-6xl font-bold w-full" style="text-wrap: pretty">'
            "Lead your life the way you want</div>"
            "</div></section>"
        )
        out, qa = promote_visual_headings(html)
        self.assertTrue(qa["ok"], qa)
        self.assertIn("<h1", out)
        self.assertIn("text-align: center", out)
        self.assertNotIn("font-family:", out)
        self.assertNotIn("letter-spacing: -1.5px", out)
        self.assertNotIn("55.2px", out)

    def test_left_aligned_hero_stays_left(self) -> None:
        html = _page(
            '<section id="hero-section">'
            '<div class="text-6xl font-bold text-left" style="text-wrap: pretty">'
            "Ready to get a better lifestyle?</div>"
            "</section>"
        )
        out, qa = promote_visual_headings(html)
        self.assertTrue(qa["ok"], qa)
        self.assertIn("<h1", out)
        self.assertIn("text-left", out)
        self.assertNotIn("text-align: center", out)
        self.assertNotIn("font-family:", out)

    def test_p_promote_inherits_parent_center(self) -> None:
        html = (
            '<!DOCTYPE html><html lang="en"><head><title>Demo</title></head><body>'
            '<header><nav aria-label="Primary"><a href="/">Home</a></nav></header>'
            '<main id="main-content">'
            '<section data-paper-section="hero" id="hero">'
            '<div class="text-6xl font-bold" style="text-wrap: pretty">Welcome</div>'
            '<div class="text-center">'
            "<div>A body sentence lives here.</div>"
            "</div></section></main>"
            "<footer><a href=\"#hero\">Home</a></footer></body></html>"
        )
        out, receipt, _ = apply_semantics(html)
        self.assertIn("<p", out)
        self.assertIn("text-align: center", out)
        self.assertFalse(any("skip" in a.lower() for a in receipt["applied"]))
        self.assertNotIn("skip-link", out.lower())
        self.assertNotIn('property="og:title"', out)


class CensusGoldTest(unittest.TestCase):
    def test_census_is_align_and_size_only(self) -> None:
        html = _page(
            '<section id="hero-section">'
            '<h1 class="text-6xl font-bold text-left">Hero title</h1>'
            "<p>Body copy stays here.</p>"
            "</section>"
            '<section id="mission">'
            '<h2 class="text-5xl text-center">Our mission</h2>'
            "</section>"
        )
        rows = census_type_align(html, source="lock")
        self.assertTrue(rows)
        self.assertTrue(all("fontFace" not in r for r in rows))
        self.assertTrue(any(r["text"] == "Hero title" and r["align"] == "start" for r in rows))
        self.assertTrue(any(r["text"] == "Our mission" and r["align"] == "center" for r in rows))
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "type-align-census.json"
            write_census(dest, rows, meta={"kind": "lock"})
            payload = json.loads(dest.read_text(encoding="utf-8"))
            rows_blob = json.dumps(payload["rows"])
            self.assertNotIn("letter-spacing", rows_blob)
            self.assertNotIn("55.2px", rows_blob)
            self.assertNotIn("#mission-heading", rows_blob)
            self.assertNotIn("fontFace", rows_blob)
            self.assertTrue(any("baked font" in r for r in payload["refused"]))

    def test_census_cli_prefers_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_dir = root / "qa" / "fixtures"
            lock_dir.mkdir(parents=True)
            ship_dir = root / "rebuild"
            ship_dir.mkdir()
            lock = lock_dir / "geometry-lock-home.html"
            lock.write_text(
                _page(
                    '<section><h1 class="text-5xl text-center">Lock title</h1></section>'
                ),
                encoding="utf-8",
            )
            (ship_dir / "index.html").write_text(
                _page('<section><h1 class="text-5xl">Ship title</h1></section>'),
                encoding="utf-8",
            )
            qa = root / "qa" / "type-align-census.json"
            rc = _census_cli.main(
                ["--root", str(root), "--html", str(ship_dir / "index.html"), "--qa", str(qa)]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(qa.read_text(encoding="utf-8"))
            texts = [r["text"] for r in payload["rows"]]
            self.assertIn("Lock title", texts)
            self.assertNotIn("Ship title", texts)


class VerifyLogicTest(unittest.TestCase):
    def test_rejects_start_when_gold_is_center(self) -> None:
        errors = compare_row(
            {
                "text": "Lead your life the way you want",
                "align": "center",
                "fontSize": "text-5xl",
            },
            {
                "fontSize": "48px",
                "fontSizePx": 48,
                "textAlign": "start",
            },
        )
        self.assertTrue(any("textAlign" in e for e in errors), errors)

    def test_accepts_start_as_left_and_size_snap(self) -> None:
        self.assertTrue(align_matches("left", "start"))
        self.assertTrue(align_matches("start", "left"))
        self.assertTrue(size_matches_token("text-5xl", 48))
        self.assertTrue(size_matches_token("48px", 47.5))
        self.assertFalse(size_matches_token("text-5xl", 60))

    def test_skip_link_and_meta_not_in_contract(self) -> None:
        html = _page(
            '<section><h1 class="text-5xl text-left">Only title</h1><p>Body.</p></section>'
        )
        rows = census_type_align(html, source="ship")
        blob = json.dumps(rows)
        self.assertNotIn("skip", blob.lower())
        self.assertNotIn("og:title", blob)
        self.assertNotIn("mission-heading", blob)


if __name__ == "__main__":
    unittest.main()
