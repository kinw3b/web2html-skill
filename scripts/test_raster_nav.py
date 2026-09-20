#!/usr/bin/env python3
"""Unit tests for Pitfall #91 — raster-only nav must not ship."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lock_guards import (
    harvest_nav_ia,
    nav_is_raster_only,
    raster_only_navs,
    reconstruct_raster_nav,
)

try:
    import bs4  # noqa: F401
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

_vspec = importlib.util.spec_from_file_location(
    "verify_trees", _SCRIPTS / "verify-rebuild-trees.py"
)
_verify = importlib.util.module_from_spec(_vspec)
assert _vspec.loader
_vspec.loader.exec_module(_verify)


RASTER_NAV = (
    '<nav data-paper-section="nav" id="nav">'
    '<div class="shrink-0 w-full" style="height: 160px; left: 0px; top: 0px">'
    '<img alt="" class="object-cover block" '
    'src="images/7SS95JSFAE3WR82CQKEHJHCSRR.jpg" '
    'style="height: 160px; width: 1600px; object-position: 50%"/></div>'
    "</nav>"
)

MOBILE = (
    '<header class="nav-mobile" data-nav-mobile="">'
    '<a class="nav-mobile__logo" href="index.html">Techty</a>'
    '<button type="button" aria-label="Open menu" data-nav-toggle="">'
    "<span></span></button>"
    '<div class="nav-mobile__panel" id="nav-mobile-panel">'
    '<a href="#hero-section">Home</a>'
    '<a href="#about">About</a>'
    '<a href="#content-section">Service</a>'
    '<a href="#article-section">Blog</a>'
    '<a href="#ready-to-take-your-business">Contact</a>'
    '<a class="btn-ghost" href="#demo">Request A Free Demo</a>'
    "</div></header>"
)

SEMANTIC_NAV = (
    '<nav id="nav">'
    '<a class="nav-logo" href="index.html">Techty</a>'
    '<a class="navbar-link" href="#hero-section">Home</a>'
    '<a class="btn-ghost" href="#demo">Request A Free Demo</a>'
    "</nav>"
)


def _page(nav: str, extra: str = "") -> str:
    return (
        "<!DOCTYPE html><html><body>"
        '<div id="paper-root" class="paper-semantic">'
        f"{nav}{extra}"
        '<main class="contents"><section id="hero-section">'
        "<h1>Title</h1></section></main>"
        '<footer id="footer"><a href="index.html">Home</a></footer>'
        "</div></body></html>"
    )


@unittest.skipUnless(_HAS_BS4, "lock_guards raster reconstruct needs BeautifulSoup; retired as 2.0 ship path")
class RasterNavDetectTest(unittest.TestCase):
    def test_full_bleed_img_is_raster_only(self) -> None:
        self.assertEqual(raster_only_navs(_page(RASTER_NAV)), ["nav"])

    def test_semantic_nav_is_not_raster(self) -> None:
        self.assertEqual(raster_only_navs(_page(SEMANTIC_NAV)), [])

    def test_logo_img_with_links_is_ok(self) -> None:
        html = (
            '<nav id="nav"><a href="index.html">'
            '<img src="images/logo.svg" style="width: 39px; height: 40px" alt="Techty">'
            "</a>"
            '<a class="navbar-link" href="#about">About</a></nav>'
        )
        self.assertEqual(raster_only_navs(_page(html)), [])

    def test_cover_threshold(self) -> None:
        html = (
            '<nav id="nav" style="width: 1600px; height: 160px">'
            '<img src="x.jpg" style="width: 1600px; height: 160px" alt="">'
            "</nav>"
        )
        self.assertEqual(raster_only_navs(_page(html)), ["nav"])
        html = (
            '<nav id="nav" style="width: 1600px; height: 160px">'
            '<img src="x.jpg" style="width: 39px; height: 40px" alt="">'
            "<span>Techty</span></nav>"
        )
        # leftover wordmark + small logo, no covering bitmap
        self.assertEqual(raster_only_navs(_page(html)), [])

    def test_nav_mobile_not_flagged(self) -> None:
        html = '<nav class="nav-mobile"><img src="x.jpg" alt=""></nav>'
        self.assertEqual(raster_only_navs(_page(html)), [])


@unittest.skipUnless(_HAS_BS4, "lock_guards raster reconstruct needs BeautifulSoup; retired as 2.0 ship path")
class RasterNavReconstructTest(unittest.TestCase):
    def test_harvest_from_mobile(self) -> None:
        ia = harvest_nav_ia(_page(RASTER_NAV, MOBILE))
        self.assertEqual(ia["logo"]["text"], "Techty")
        self.assertEqual([x["text"] for x in ia["links"]], [
            "Home", "About", "Service", "Blog", "Contact"
        ])
        self.assertEqual(ia["cta"]["text"], "Request A Free Demo")
        self.assertIn("btn-ghost", ia["cta"]["classes"])

    def test_reconstruct_replaces_img_with_links(self) -> None:
        out = reconstruct_raster_nav(_page(RASTER_NAV, MOBILE))
        self.assertEqual(raster_only_navs(out), [])
        self.assertIn('<a class="navbar-link" href="#hero-section">Home</a>', out)
        self.assertIn("Request A Free Demo", out)
        self.assertIn('class="btn-ghost"', out)
        self.assertIn("Techty", out)
        self.assertNotIn("7SS95JSFAE3WR82CQKEHJHCSRR.jpg", out)
        self.assertIn('id="nav"', out)

    def test_reconstruct_noop_without_ia(self) -> None:
        html = _page(RASTER_NAV)
        out = reconstruct_raster_nav(html)
        self.assertEqual(raster_only_navs(out), ["nav"])
        self.assertIn("7SS95JSFAE3WR82CQKEHJHCSRR.jpg", out)

class RasterNavGateTest(unittest.TestCase):
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
