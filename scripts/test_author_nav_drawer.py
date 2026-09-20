#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "author_nav_drawer", _SCRIPTS / "author-nav-drawer.py"
)
mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(mod)

THRIVE_HEADER = """<!DOCTYPE html><html><head>
<link href="css/site.css" rel="stylesheet"/>
</head><body>
<header class="site-header">
<a class="logo" href="#"><img alt="thrive" src="logo.svg"/></a>
<nav aria-label="Primary" class="nav-links" id="site-nav">
<a href="#">All Pages</a>
<a href="#">About</a>
<a href="#">Pricing</a>
<a href="#">Contact</a>
</nav>
<a class="btn btn-secondary nav-cta" href="#">Book Free Demo</a>
<button aria-controls="site-nav" aria-expanded="false" aria-label="Menu" class="burger" type="button"><span></span><span></span></button>
</header>
<script src="js/qa-overlay.js"></script>
</body></html>
"""

THRIVE_CSS = """
.burger { display: none; }
@media (max-width: 900px) {
  .nav-links, .nav-cta { display: none; }
  .burger { display: flex; }
}
"""

DOVER = """<!DOCTYPE html><html><head>
<link href="css/site.css" rel="stylesheet"/>
</head><body>
<header class="site-header">
<nav class="nav-links"><a href="#about">About</a></nav>
<button class="nav-toggle" type="button" data-nav-toggle aria-expanded="false" aria-label="Open menu"></button>
<div class="nav-panel" id="nav-panel"><a href="#about">About</a></div>
</header>
<script>
  const toggle = document.querySelector("[data-nav-toggle]");
  const panel = document.getElementById("nav-panel");
  toggle.addEventListener("click", () => {
    document.body.classList.toggle("nav-open");
  });
</script>
</body></html>
"""


def _project(tmp: str, html: str, css: str = "") -> Path:
    root = Path(tmp)
    (root / "qa").mkdir()
    (root / "rebuild" / "css").mkdir(parents=True)
    (root / "rebuild" / "js").mkdir(parents=True)
    (root / "rebuild" / "index-polish.html").write_text(html, encoding="utf-8")
    if css:
        (root / "rebuild" / "css" / "site.css").write_text(css, encoding="utf-8")
    return root


class AuthorNavDrawerTest(unittest.TestCase):
    def test_authors_sheet_from_painted_burger_without_capture_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, THRIVE_HEADER, THRIVE_CSS)
            receipt = mod.author_nav_drawer(root)
            self.assertTrue(mod.drawer_receipt_ok(receipt))
            self.assertTrue(receipt["painted"])
            self.assertEqual(receipt["maxWidth"], 900)
            self.assertFalse(receipt["captureTool"])
            self.assertTrue(any("burger open drawer" == row["finding"] for row in receipt["applied"]))
            self.assertFalse(
                any(mod.BANNED_SKIP.search(str(row.get("reason") or "")) for row in receipt["skipped"])
            )
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertIn('data-nav-toggle=""', html)
            self.assertIn('id="nav-panel"', html)
            self.assertIn("About", html)
            self.assertIn("Book Free Demo", html)
            self.assertIn("css/nav-drawer.css", html)
            self.assertIn("js/nav-drawer.js", html)
            self.assertTrue(mod.drawer_wired(html))
            css = (root / "rebuild" / "css" / "nav-drawer.css").read_text(encoding="utf-8")
            self.assertIn("900px", css)
            self.assertTrue((root / "rebuild" / "js" / "nav-drawer.js").is_file())

    def test_no_op_when_no_hamburger_painted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(
                tmp,
                "<html><body><header><nav><a href='#'>About</a></nav></header></body></html>",
            )
            receipt = mod.author_nav_drawer(root)
            self.assertTrue(receipt["ok"])
            self.assertFalse(receipt["painted"])
            self.assertEqual(receipt["applied"], [])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertNotIn("nav-panel", html)
            self.assertNotIn("js/nav-drawer.js", html)

    def test_keeps_existing_wired_panel_without_second_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, DOVER, "@media (min-width: 768px) { .nav-toggle { display: none; } }")
            receipt = mod.author_nav_drawer(root)
            self.assertTrue(receipt["ok"])
            self.assertTrue(receipt["painted"])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertEqual(html.count("id=\"nav-panel\""), 1)
            self.assertNotIn("js/nav-drawer.js", html)
            self.assertIn("css/nav-drawer.css", html)
            self.assertTrue(mod.drawer_wired(html))

    def test_idempotent_and_never_uses_capture_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, THRIVE_HEADER, THRIVE_CSS)
            first = mod.author_nav_drawer(root)
            second = mod.author_nav_drawer(root)
            self.assertTrue(first["ok"])
            self.assertTrue(second["ok"])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertEqual(html.count('id="nav-panel"'), 1)
            self.assertEqual(html.count("js/nav-drawer.js"), 1)
            payload = json.loads((root / "qa" / "nav-drawer.json").read_text(encoding="utf-8"))
            self.assertTrue(mod.drawer_receipt_ok(payload))

    def test_receipt_rejects_capture_tool_skip(self):
        bad = {
            "ok": True,
            "writer": "author-nav-drawer.py",
            "applied": [],
            "skipped": [
                {
                    "finding": "burger open drawer",
                    "reason": "No Capture Tool open-nav pair. Inventing a sheet is new chrome.",
                }
            ],
        }
        self.assertFalse(mod.drawer_receipt_ok(bad))


if __name__ == "__main__":
    unittest.main()
