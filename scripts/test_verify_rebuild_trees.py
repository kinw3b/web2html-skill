#!/usr/bin/env python3
"""verify-rebuild-trees.py gate: skip link, semantic nav, leaked overlay."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_vspec = importlib.util.spec_from_file_location(
    "verify_trees", _SCRIPTS / "verify-rebuild-trees.py"
)
_verify = importlib.util.module_from_spec(_vspec)
assert _vspec.loader
_vspec.loader.exec_module(_verify)


SEMANTIC_NAV = (
    '<nav id="nav">'
    '<a class="nav-logo" href="index.html">Techty</a>'
    '<a class="navbar-link" href="#hero-section">Home</a>'
    '<a class="btn-ghost" href="#demo">Request A Free Demo</a>'
    "</nav>"
)


class VerifyRebuildTreesGateTest(unittest.TestCase):
    def _ship(self, nav: str, extra: str = "") -> Path:
        root = Path(tempfile.mkdtemp())
        ship = root / "rebuild"
        (ship / "css").mkdir(parents=True)
        (ship / "js").mkdir(parents=True)
        html = (
            '<!DOCTYPE html><html><head>'
            '<link rel="stylesheet" href="css/qa-overlay.css">'
            "</head><body>"
            '<div id="paper-root">'
            f"{nav}{extra}"
            '<main class="contents"><section id="hero-section">'
            "<h1>Title</h1></section></main>"
            '<footer id="footer"><a href="index.html">Home</a></footer>'
            "</div>"
            '<script src="js/qa-overlay.js"></script>'
            "</body></html>"
        )
        (ship / "index.html").write_text(html, encoding="utf-8")
        (ship / "css" / "qa-overlay.css").write_text("/* overlay */\n" * 20)
        (ship / "js" / "qa-overlay.js").write_text("/* overlay */\n" * 20)
        return root

    def test_verify_fails_skip_link(self) -> None:
        root = self._ship(SEMANTIC_NAV)
        html_path = root / "rebuild" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        html_path.write_text(
            html.replace("<body>", '<body><a id="skip-to-content">Skip</a>'),
            encoding="utf-8",
        )
        rc = _verify.main([str(root)])
        self.assertEqual(rc, 2)

    def test_verify_passes_semantic_nav(self) -> None:
        root = self._ship(SEMANTIC_NAV)
        rc = _verify.main([str(root)])
        self.assertEqual(rc, 0)

    def test_verify_fails_leaked_overlay_beside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            templates = Path(tmp)
            root = templates / "kp-demo"
            ship = root / "rebuild"
            (ship / "css").mkdir(parents=True)
            (ship / "js").mkdir(parents=True)
            html = (
                "<!DOCTYPE html><html><head>"
                '<link rel="stylesheet" href="css/qa-overlay.css">'
                "</head><body>"
                f"{SEMANTIC_NAV}"
                '<main class="contents"><section id="hero-section">'
                "<h1>Title</h1></section></main>"
                '<footer id="footer"><a href="index.html">Home</a></footer>'
                '<script src="js/qa-overlay.js"></script>'
                "</body></html>"
            )
            (ship / "index.html").write_text(html, encoding="utf-8")
            (ship / "css" / "qa-overlay.css").write_text("/* overlay */\n" * 20)
            (ship / "js" / "qa-overlay.js").write_text("/* overlay */\n" * 20)
            leaked = templates / "css"
            leaked.mkdir()
            (leaked / "qa-overlay.css").write_text("/* leaked */\n", encoding="utf-8")
            rc = _verify.main([str(root)])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
