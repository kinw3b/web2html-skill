#!/usr/bin/env python3
"""1.1 scrape_light: Latin-only fonts, no full unicode-range dump."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scrape_light import collect_plan, is_latin_range, run, write_tokens_md

FIXTURE = """<!doctype html>
<html><head><title>Demo Site</title>
<style>
@font-face {
  font-family: Inter;
  src: url("https://example.com/cyrillic.woff2");
  unicode-range: U+0460-052F;
}
@font-face {
  font-family: Inter;
  src: url("https://example.com/latin.woff2");
  font-weight: 400;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153;
}
@font-face {
  font-family: Inter;
  src: url("https://example.com/full.woff2");
  font-weight: 700;
}
</style></head>
<body>
<img src="https://example.com/hero.png">
<img src="https://example.com/logo.svg">
<a href="https://example.com/page">skip</a>
</body></html>
"""


class LatinFilterTests(unittest.TestCase):
    def test_preserves_normal_italic_oblique_and_shared_url_weights(self) -> None:
        css = "\n".join(
            f'@font-face {{font-family: Demo; font-weight: {weight}; '
            f'font-style: {style}; src: url("/variable.woff2"); unicode-range: U+0000-00FF;}}'
            for weight, style in (("400", "normal"), ("700", "normal"),
                                  ("400", "italic"), ("100 900", "oblique 0deg 12deg"))
        )
        plan = collect_plan(css, "https://example.com/")
        self.assertEqual(len(plan["fonts"]), 4)
        self.assertEqual({f["style"] for f in plan["fonts"]}, {"normal", "italic", "oblique 0deg 12deg"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tokens_md(root, plan)
            table = (root / "scraped-tokens.md").read_text()
            self.assertIn("| Style |", table)
            self.assertIn("| italic |", table)
            self.assertIn("| oblique 0deg 12deg |", table)

    def test_range_detection(self) -> None:
        self.assertTrue(is_latin_range(""))
        self.assertTrue(is_latin_range("U+0000-00FF"))
        self.assertTrue(is_latin_range("U+0000-00FF, U+0131"))
        self.assertFalse(is_latin_range("U+0460-052F"))
        self.assertFalse(is_latin_range("U+0100-024F"))

    def test_collect_skips_non_latin_subsets(self) -> None:
        plan = collect_plan(FIXTURE, "https://example.com/")
        urls = [row["url"] for row in plan["fonts"]]
        self.assertIn("https://example.com/latin.woff2", urls)
        self.assertIn("https://example.com/full.woff2", urls)
        self.assertNotIn("https://example.com/cyrillic.woff2", urls)
        self.assertEqual(plan["skipped_font_faces"], 1)
        self.assertEqual(
            plan["images"],
            ["https://example.com/hero.png", "https://example.com/logo.svg"],
        )

    def test_dry_run_writes_tokens_not_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html = root / "page.html"
            html.write_text(FIXTURE, encoding="utf-8")
            out = root / "source-site"
            summary = run(
                "https://example.com/",
                out,
                project=root,
                html_path=html,
                dry_run=True,
            )
            self.assertEqual(summary["latinFonts"], 2)
            self.assertEqual(summary["images"], 2)
            self.assertEqual(summary["queued"], 4)
            self.assertTrue((out / "scraped-tokens.md").is_file())
            self.assertTrue((out / "pages.json").is_file())
            self.assertFalse((root / "qa" / "fidelity-contract.md").exists())
            self.assertEqual(list((out / "assets").glob("*")), [])


if __name__ == "__main__":
    unittest.main()
