#!/usr/bin/env python3
"""5.5 helpers — sitemap → Astro routes, label wiring, frontmatter SEO."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import interior_seo as seo

_WIRE_PATH = Path(__file__).with_name("wire-astro-routes.py")
_SPEC = importlib.util.spec_from_file_location("wire_astro_routes", _WIRE_PATH)
wire = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(wire)

SITEMAP = [
    {"path": "/about", "slug": "about", "paperName": "About"},
    {"path": "/work", "slug": "work", "paperName": "Our Work"},
]


class RouteMapTest(unittest.TestCase):
    def test_routes_not_html_files(self) -> None:
        mapping = seo.route_map(SITEMAP)
        self.assertEqual(mapping["about"], "/about/")
        self.assertEqual(mapping["/about"], "/about/")
        self.assertEqual(mapping["our work"], "/work/")
        self.assertEqual(mapping["/"], "/")
        self.assertEqual(mapping["home"], "/")

    def test_dest_for_href(self) -> None:
        mapping = seo.route_map(SITEMAP)
        self.assertEqual(seo.dest_for_href("/about", mapping), "/about/")
        self.assertEqual(seo.dest_for_href("https://example.com/about", mapping), "#")
        self.assertEqual(seo.dest_for_href("mailto:hi@x.com", mapping), "#")
        self.assertEqual(seo.dest_for_href("/", mapping), "/")
        self.assertEqual(seo.dest_for_href("about.html", mapping), "/about/")
        self.assertIsNone(seo.dest_for_href("/about/", mapping))  # already a route
        self.assertIsNone(seo.dest_for_href("#", mapping))
        self.assertIsNone(seo.dest_for_href("/nowhere", mapping))

    def test_dest_for_label(self) -> None:
        mapping = seo.route_map(SITEMAP)
        self.assertEqual(seo.dest_for_label("<span>Our  Work</span>", mapping), "/work/")
        self.assertEqual(seo.dest_for_label("Home", mapping), "/")
        self.assertIsNone(seo.dest_for_label("Pricing", mapping))

    def test_rewrite_anchor_hrefs_in_fragment_literal(self) -> None:
        mapping = seo.route_map(SITEMAP)
        fragment = (
            "---\nconst html = `<nav><a href=\"#\">Home</a><a href=\"/about\">About</a>"
            "<a href=\"#\">Our Work</a><a href=\"https://x.com\">X</a><a href=\"#faq\">FAQ</a></nav>`;\n---\n"
        )
        out, changed = seo.rewrite_anchor_hrefs(fragment, mapping)
        self.assertEqual(changed, 4)
        self.assertIn('<a href="/">Home</a>', out)
        self.assertIn('<a href="/about/">About</a>', out)
        self.assertIn('<a href="/work/">Our Work</a>', out)
        self.assertIn('<a href="#">X</a>', out)
        self.assertIn('<a href="#faq">FAQ</a>', out)


class FrontmatterSeoTest(unittest.TestCase):
    PAGE = (
        "---\n"
        "import BaseLayout from '../layouts/BaseLayout.astro';\n"
        "const title = `About`;\n"
        "const description = ``;\n"
        "const lang = `en`;\n"
        "---\n"
        "<BaseLayout title={title} description={description} lang={lang}>\n"
        "  <main><h1>About</h1></main>\n"
        "</BaseLayout>\n"
    )

    def test_fills_and_wires_props_without_inventing(self) -> None:
        meta = {"title": "About `Us`", "description": "Scraped.", "lang": "es", "canonical": "https://x.com/about", "og_image": "https://x.com/og.png"}
        out, applied = wire.apply_frontmatter_seo(self.PAGE, meta)
        self.assertEqual(applied, ["title", "description", "lang", "canonical", "ogImage"])
        self.assertIn("const title = `About \\`Us\\``;", out)
        self.assertIn("const description = `Scraped.`;", out)
        self.assertIn("const lang = `es`;", out)
        self.assertIn("const canonical = `https://x.com/about`;", out)
        self.assertIn("const ogImage = `https://x.com/og.png`;", out)
        self.assertIn("<BaseLayout title={title} description={description} lang={lang} canonical={canonical} ogImage={ogImage}>", out)
        self.assertEqual(out.count("<BaseLayout"), 1)
        self.assertIn("<main><h1>About</h1></main>", out)

    def test_empty_meta_leaves_page_alone(self) -> None:
        out, applied = wire.apply_frontmatter_seo(self.PAGE, {})
        self.assertEqual(applied, [])
        self.assertEqual(out, self.PAGE)


class ScrapeMetaTest(unittest.TestCase):
    def test_interior_meta_never_merges_homepage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            (root / "qa" / "scrape-meta.json").write_text(
                '{"title": "Home Title", "description": "Home description.", "lang": "es"}\n'
            )
            live = "<html><head><title>About Live</title></head><body></body></html>"
            meta = seo.scrape_meta_for(root, "about", {"url": "https://example.com/about"}, lambda url: live)
            self.assertEqual(meta["title"], "About Live")
            self.assertEqual(meta["canonical"], "https://example.com/about")
            self.assertEqual(meta["lang"], "es")  # site lang is shared; copy is not
            self.assertNotIn("description", meta)


if __name__ == "__main__":
    unittest.main()
