#!/usr/bin/env python3
"""Unit tests for Paper layer name → HTML tag (3.3 helper, not a 2.0 join)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper_layer_names import (
    build_library_class_map,
    build_semantic_map,
    collect_layer_names,
    ensure_main_landmark,
    promote_paper_section_divs,
    retag_from_layer_names,
    strip_canvas_root_widths,
    tag_from_paper_name,
)


class TagFromPaperNameTest(unittest.TestCase):
    def test_numbered_header(self) -> None:
        spec = tag_from_paper_name("01 · header")
        self.assertEqual(spec["tag"], "header")
        self.assertEqual(spec["id"], "header")
        self.assertEqual(spec["kind"], "landmark")

    def test_numbered_nav(self) -> None:
        spec = tag_from_paper_name("01 · nav")
        self.assertEqual(spec["tag"], "nav")
        self.assertEqual(spec["id"], "nav")

    def test_hero_section(self) -> None:
        spec = tag_from_paper_name("02 · hero")
        self.assertEqual(spec["tag"], "section")
        self.assertEqual(spec["id"], "hero")

    def test_named_section_suffix(self) -> None:
        spec = tag_from_paper_name("03 · pricing-section")
        self.assertEqual(spec["tag"], "section")
        self.assertEqual(spec["id"], "pricing-section")

    def test_footer(self) -> None:
        spec = tag_from_paper_name("12 · footer")
        self.assertEqual(spec["tag"], "footer")
        self.assertEqual(spec["id"], "footer")

    def test_source_semantics_layer_name(self) -> None:
        spec = tag_from_paper_name("h1 · The future of design")
        self.assertEqual(spec["tag"], "h1")
        self.assertEqual(spec["kind"], "heading")
        self.assertIn("source-semantics", spec["notes"])
        self.assertEqual(tag_from_paper_name("p · A short lead")["tag"], "p")
        self.assertEqual(tag_from_paper_name("img · hero photo")["tag"], "img")
        self.assertEqual(tag_from_paper_name("a · Get Started Now")["tag"], "a")
        self.assertEqual(tag_from_paper_name("01 · hero-section")["tag"], "section")

    def test_retag_source_semantics_heading_leaf(self) -> None:
        html = (
            '<section data-name="01 · hero-section">'
            '<div data-name="h1 · The future of design" style="font-size:72px">'
            "The future of design</div></section>"
        )
        out = retag_from_layer_names(html)
        self.assertIn("<section", out)
        self.assertIn('<h1 data-name="h1 · The future of design"', out)
        self.assertIn("</h1>", out)
        self.assertEqual(
            build_semantic_map(["h1 · The future of design"])["h1"],
            ["The future of design"],
        )

    def test_first_heading_is_h1(self) -> None:
        spec = tag_from_paper_name("hero-heading", heading_index=0)
        self.assertEqual(spec["tag"], "h1")
        self.assertEqual(spec["kind"], "heading")

    def test_second_heading_is_h2(self) -> None:
        spec = tag_from_paper_name("features-heading", heading_index=1)
        self.assertEqual(spec["tag"], "h2")

    def test_scribble_stays_decorative(self) -> None:
        spec = tag_from_paper_name("heading-scribble decorative")
        self.assertIn(spec["tag"], {"svg", "img", None})
        self.assertTrue(spec.get("decorative"))
        self.assertEqual(spec["kind"], "decorative")

    def test_text_type_is_p_unless_heading(self) -> None:
        spec = tag_from_paper_name("body-copy", paper_type="Text")
        self.assertEqual(spec["tag"], "p")
        heading = tag_from_paper_name("hero-heading", paper_type="Text")
        self.assertEqual(heading["tag"], "h1")

    def test_image_type_is_img(self) -> None:
        spec = tag_from_paper_name("hero-shot", paper_type="Image")
        self.assertEqual(spec["tag"], "img")
        self.assertEqual(spec["kind"], "image")

    def test_a6_pill_is_anchor(self) -> None:
        spec = tag_from_paper_name("hero-cta pill")
        self.assertEqual(spec["tag"], "a")
        self.assertEqual(spec["class"], "pill")

    def test_faq_row(self) -> None:
        spec = tag_from_paper_name("faq-row")
        self.assertEqual(spec["tag"], "details")
        self.assertEqual(spec["kind"], "faq")

    def test_interactive_not_dumped(self) -> None:
        spec = tag_from_paper_name("Navbar dropdown Interactive")
        self.assertEqual(spec["kind"], "interactive")
        self.assertIsNone(spec["tag"])


class MapBuilderTest(unittest.TestCase):
    def test_semantic_map_from_names_not_copy(self) -> None:
        names = [
            "01 · header",
            "02 · hero",
            "hero-heading",
            "12 · footer",
            "Get 14 Days Free Trial",
        ]
        spec = build_semantic_map(names)
        self.assertEqual(spec["generatedFrom"], "paper-layer-names")
        self.assertEqual(spec["links"], {})
        self.assertEqual(spec["h1"], [])
        self.assertEqual(spec["h2"], [])
        layer_names = [row["name"] for row in spec["layers"]]
        self.assertIn("01 · header", layer_names)
        self.assertIn("hero-heading", layer_names)
        # Repeating marketing copy is not a generated link target.
        self.assertNotIn("Get 14 Days Free Trial", spec["links"])

    def test_library_class_map_from_a6_names(self) -> None:
        names = ["hero-cta pill", "footer text-link", "hero-shot media"]
        spec = build_library_class_map(names)
        self.assertEqual(spec["generatedFrom"], "paper-layer-names")
        classes = {row["class"] for row in spec["paint"]}
        self.assertEqual(classes, {"pill", "text-link", "media"})
        self.assertEqual(spec["leaves"], [])


class RetagAndCleanupTest(unittest.TestCase):
    def test_collects_data_name_and_section_id(self) -> None:
        html = (
            '<div id="paper-root">'
            '<section id="header" data-paper-section="header" '
            'data-name="01 · header"></section>'
            '<section id="hero" data-paper-section="hero"></section>'
            '<div layer-name="hero-heading">Title</div>'
            "</div>"
        )
        names = collect_layer_names(html)
        self.assertIn("01 · header", names)
        self.assertIn("02 · hero", names)
        self.assertIn("hero-heading", names)

    def test_retag_nav_keeps_id(self) -> None:
        html = (
            '<section id="nav" data-paper-section="nav" '
            'data-name="01 · nav" data-section="nav">'
            "<div>Home</div></section>"
        )
        out = retag_from_layer_names(html)
        self.assertIn("<nav", out)
        self.assertIn('id="nav"', out)
        self.assertIn('data-section="nav"', out)
        self.assertIn("</nav>", out)
        self.assertNotIn("<section", out)

    def test_strip_canvas_root_not_section(self) -> None:
        html = (
            '<div id="paper-root" class="w-[1600px]" '
            'style="width: 1600px; min-height: 800px">'
            '<section id="hero" style="width: 1600px">'
            "<div>x</div></section></div>"
        )
        out = strip_canvas_root_widths(html)
        root = out.split("<section", 1)[0]
        self.assertNotIn("w-[1600px]", root)
        self.assertNotIn("width: 1600px", root)
        self.assertIn("width: 100%", root)
        self.assertIn('<section id="hero" style="width: 1600px">', out)

    def test_one_main_around_inner_sections(self) -> None:
        html = (
            '<div id="paper-root">'
            '<header id="header"></header>'
            '<section id="hero"></section>'
            '<section id="pricing"></section>'
            '<footer id="footer"></footer>'
            "</div>"
        )
        out = ensure_main_landmark(html)
        self.assertEqual(out.count("<main"), 1)
        self.assertEqual(out.count("</main>"), 1)
        self.assertIn("<header", out)
        self.assertIn("<footer", out)
        self.assertLess(out.find("<header"), out.find("<main"))
        self.assertLess(out.find("</main>"), out.find("<footer"))


class PromoteSectionDivsTest(unittest.TestCase):
    def test_div_paper_section_becomes_section(self) -> None:
        html = (
            '<div id="paper-root">'
            '<div data-paper-section="features" id="features">'
            '<div class="content-center">cards</div>'
            "</div></div>"
        )
        out = promote_paper_section_divs(html)
        self.assertIn('<section data-paper-section="features" id="features">', out)
        self.assertIn("</section>", out)
        self.assertIn('<div class="content-center">', out)
        self.assertNotIn('<div data-paper-section="features"', out)

    def test_nav_slug_becomes_nav(self) -> None:
        html = '<div data-paper-section="nav" id="nav"><a href="/">Home</a></div>'
        out = promote_paper_section_divs(html)
        self.assertIn("<nav", out)
        self.assertIn("</nav>", out)


if __name__ == "__main__":
    unittest.main()
