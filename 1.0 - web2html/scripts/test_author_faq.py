#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("author_faq", _SCRIPTS / "author-faq.py")
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(mod)

POLISH_FAQ = """<!DOCTYPE html><html><head>
<link href="css/tokens.css" rel="stylesheet"/>
</head><body>
<main>
<section id="faq">
<h2>FAQs</h2>
<article class="faq-row">
<h3>What is pricing?</h3>
</article>
<article class="faq-row">
<h3>How does billing work?</h3>
</article>
</section>
</main>
</body></html>
"""

SCRAPE_FAQ = """<!DOCTYPE html><html><body>
<section id="faq">
<h2>FAQs</h2>
<details><summary>What is pricing?</summary><p>Plans start at forty a month.</p></details>
<details><summary>How does billing work?</summary><p>Invoices go out on the first.</p></details>
</section>
</body></html>
"""

NO_FAQ = """<!DOCTYPE html><html><head></head><body>
<main><section id="hero"><h1>Home</h1></section></main>
</body></html>
"""


def _project(tmp: str, html: str, scrape: str = "") -> Path:
    root = Path(tmp)
    (root / "qa").mkdir()
    (root / "rebuild" / "css").mkdir(parents=True)
    (root / "rebuild" / "js").mkdir(parents=True)
    (root / "rebuild" / "index-polish.html").write_text(html, encoding="utf-8")
    if scrape:
        (root / "source-site").mkdir()
        (root / "source-site" / "index.html").write_text(scrape, encoding="utf-8")
    return root


class AuthorFaqTest(unittest.TestCase):
    def test_fills_empty_answers_from_scrape_and_wires_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, POLISH_FAQ, SCRAPE_FAQ)
            receipt = mod.author_faq(root)
            self.assertTrue(mod.faq_receipt_ok(receipt))
            self.assertTrue(receipt["painted"])
            self.assertGreaterEqual(len(receipt["applied"]), 2)
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertIn('data-action="toggle-faq"', html)
            self.assertIn("Plans start at forty a month.", html)
            self.assertIn("Invoices go out on the first.", html)
            self.assertIn("js/faq.js", html)
            self.assertIn("css/faq.css", html)
            self.assertTrue((root / "rebuild" / "js" / "faq.js").is_file())
            self.assertEqual(html.count("Plans start at forty a month."), 1)
            self.assertEqual(html.count("Invoices go out on the first."), 1)

    def test_no_faq_is_ok_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, NO_FAQ)
            receipt = mod.author_faq(root)
            self.assertTrue(mod.faq_receipt_ok(receipt))
            self.assertFalse(receipt["painted"])
            self.assertEqual(receipt["applied"], [])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertNotIn("js/faq.js", html)

    def test_banned_empty_bodies_skip_fails_when_painted(self):
        payload = {
            "ok": True,
            "writer": "author-faq.py",
            "painted": True,
            "applied": [],
            "skipped": [{
                "finding": "FAQ accordion",
                "reason": "2.3 dump/Paper signed empty bodies. Do not invent copy.",
            }],
        }
        self.assertFalse(mod.faq_receipt_ok(payload))


if __name__ == "__main__":
    unittest.main()
