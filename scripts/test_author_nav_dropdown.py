#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "author_nav_dropdown", _SCRIPTS / "author-nav-dropdown.py"
)
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(mod)

POLISH_NAV = """<!DOCTYPE html><html><head>
<link href="css/tokens.css" rel="stylesheet"/>
</head><body>
<header>
<a class="logo" href="#">Brand</a>
<nav aria-label="Primary">
<a href="#">Product</a>
<a href="#">About</a>
</nav>
</header>
<main><section id="hero"><h1>Home</h1></section></main>
</body></html>
"""

SCRAPE_NAV = """<!DOCTYPE html><html><body>
<header>
<nav>
<li>
<a href="/product">Product</a>
<ul>
<a href="/one">Feature One</a>
<a href="/two">Feature Two</a>
</ul>
</li>
<a href="/about">About</a>
</nav>
</header>
</body></html>
"""

NO_DROPDOWN = """<!DOCTYPE html><html><head></head><body>
<header><nav><a href="#">About</a><a href="#">Contact</a></nav></header>
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


class AuthorNavDropdownTest(unittest.TestCase):
    def test_authors_panel_from_scrape_submenu(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, POLISH_NAV, SCRAPE_NAV)
            receipt = mod.author_nav_dropdown(root)
            self.assertTrue(mod.dropdown_receipt_ok(receipt))
            self.assertTrue(receipt["painted"])
            self.assertGreaterEqual(len(receipt["applied"]), 1)
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertIn("data-nav-dropdown-trigger", html)
            self.assertIn("Feature One", html)
            self.assertIn("Feature Two", html)
            self.assertIn("js/nav-dropdown.js", html)
            self.assertIn("css/nav-dropdown.css", html)
            self.assertNotIn("https://", html)

    def test_no_dropdown_is_ok_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, NO_DROPDOWN)
            receipt = mod.author_nav_dropdown(root)
            self.assertTrue(mod.dropdown_receipt_ok(receipt))
            self.assertFalse(receipt["painted"])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertNotIn("js/nav-dropdown.js", html)

    def test_capture_tool_skip_fails(self):
        payload = {
            "ok": True,
            "writer": "author-nav-dropdown.py",
            "painted": True,
            "applied": [],
            "skipped": [{
                "finding": "nav dropdown",
                "reason": "Capture Tool did not run. --allow-dropdown was not passed. Do not hunt.",
            }],
        }
        self.assertFalse(mod.dropdown_receipt_ok(payload))


if __name__ == "__main__":
    unittest.main()
