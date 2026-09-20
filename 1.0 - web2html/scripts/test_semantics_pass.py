#!/usr/bin/env python3
"""Unit tests for 3.3 / pre-2.2.e semantics pass (fixtures only)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from section_promote import promote_sections, section_gate_errors
from semantics_pass import (
    apply_semantics,
    build_qa,
    has_skip_link,
    semantics_gate_errors,
)

_vspec = importlib.util.spec_from_file_location(
    "verify_semantics", _SCRIPTS / "verify-semantics.py"
)
_verify = importlib.util.module_from_spec(_vspec)
assert _vspec.loader
_vspec.loader.exec_module(_verify)


def _page(inner: str, *, head: str = "<title>Demo</title>") -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        + head
        + "</head><body>"
        '<div id="paper-root" class="paper-semantic">'
        + inner
        + "</div></body></html>"
    )


def _complete(*, extra_section: str = "", email_labeled: bool = True) -> str:
    email = (
        '<label class="sr-only" for="email">Email</label>'
        '<input id="email" type="email" name="email">'
        if email_labeled
        else '<input type="email" name="email">'
    )
    return _page(
        '<header>'
        '<nav aria-label="Primary"><a href="/">Home</a></nav>'
        "</header>"
        '<main id="main-content" style="display: contents">'
        '<section data-paper-section="hero" id="hero" aria-labelledby="hero-title">'
        '<h1 id="hero-title">Welcome</h1>'
        "<p>A body sentence lives here.</p>"
        "</section>"
        '<section data-paper-section="services" id="services" aria-labelledby="services-title">'
        '<h2 id="services-title">Services</h2>'
        '<article class="card"><h3>Design</h3><p>We design things.</p></article>'
        '<article class="card"><h3>Build</h3><p>We build things.</p></article>'
        "</section>"
        + extra_section
        + "</main>"
        "<footer>"
        '<a href="#services">Services</a>'
        '<form aria-label="Newsletter">'
        + email
        + '<button type="submit">Join</button>'
        "</form>"
        "</footer>"
    )


class SectionPromoteComposeTest(unittest.TestCase):
    def test_leftover_div_band_still_gated(self) -> None:
        html = _page(
            '<div data-paper-section="features" id="features">'
            '<div class="content-center">x</div></div>'
        )
        self.assertTrue(section_gate_errors(html))
        self.assertTrue(any("features" in e for e in semantics_gate_errors(html)))
        promoted = promote_sections(html)
        self.assertIn("<section", promoted)
        self.assertEqual(section_gate_errors(promoted), [])
        out, _, _ = apply_semantics(html)
        self.assertNotIn('<div data-paper-section="features"', out)
        self.assertFalse(any("data-paper-section" in e for e in semantics_gate_errors(out)))


class LandmarkTest(unittest.TestCase):
    def test_missing_main_header_footer_detected(self) -> None:
        html = _page(
            '<div id="announce" class="topbar">Free shipping this week</div>'
            '<nav><a href="/">Home</a></nav>'
            '<section data-paper-section="hero" id="hero">'
            "<h1>Welcome</h1><p>Hello there.</p></section>"
            '<div class="copyright">© 2026 All rights reserved</div>'
        )
        errs = semantics_gate_errors(html)
        joined = " ".join(errs).lower()
        self.assertIn("header", joined)
        self.assertIn("main", joined)
        self.assertIn("footer", joined)

    def test_apply_wraps_header_main_footer(self) -> None:
        html = _page(
            '<div id="announce" class="topbar">Free shipping this week</div>'
            '<nav><a href="/">Home</a></nav>'
            '<section data-paper-section="hero" id="hero">'
            '<div class="text-6xl font-bold" style="text-wrap: pretty">Welcome</div>'
            "<p>Hello there.</p></section>"
            '<div data-name="footer" id="site-footer">'
            '<a href="#hero">Home</a>'
            '<form><input type="email" name="email">'
            '<button type="submit">Join</button></form>'
            "<p>© 2026 All rights reserved</p></div>"
        )
        out, receipt, _ = apply_semantics(html)
        self.assertIn("<header", out)
        self.assertIn('<main', out)
        self.assertIn('id="main-content"', out)
        self.assertIn("<footer", out)
        self.assertFalse(has_skip_link(out))
        self.assertNotIn("skip-link", out.lower())
        self.assertTrue(any("header" in a or "main" in a for a in receipt["applied"]))


class ArticleClusterTest(unittest.TestCase):
    def test_card_cluster_without_article_fails(self) -> None:
        html = _complete(
            extra_section=""
        )
        # Replace articles with divs inside a copy that still has chrome.
        dirty = html.replace("<article class=\"card\">", '<div class="card">').replace(
            "</article>", "</div>"
        )
        errs = semantics_gate_errors(dirty)
        self.assertTrue(any("article" in e.lower() for e in errs), errs)

    def test_card_cluster_with_article_passes(self) -> None:
        html = _complete()
        errs = [e for e in semantics_gate_errors(html) if "article" in e.lower()]
        self.assertEqual(errs, [])

    def test_apply_wraps_card_cluster(self) -> None:
        html = _page(
            '<header><nav aria-label="Primary"><a href="/">Home</a></nav></header>'
            '<main id="main-content">'
            '<section data-paper-section="services" id="services">'
            '<h2 id="services-title">Services</h2>'
            '<div class="card"><h3>Design</h3><p>We design things.</p></div>'
            '<div class="card"><h3>Build</h3><p>We build things.</p></div>'
            "</section></main>"
            '<footer><a href="#services">Services</a></footer>'
        )
        self.assertTrue(any("article" in e.lower() for e in semantics_gate_errors(html)))
        out, _, _ = apply_semantics(html)
        self.assertIn("<article", out)
        self.assertFalse(any("article" in e.lower() for e in semantics_gate_errors(out)))


class HeadingRankTest(unittest.TestCase):
    def test_two_h1_fails(self) -> None:
        html = _complete(
            extra_section='<section id="about"><h1>Second title</h1></section>'
        )
        errs = semantics_gate_errors(html)
        self.assertTrue(any("h1" in e.lower() for e in errs), errs)


class SkipLinkTest(unittest.TestCase):
    def test_skip_link_not_required(self) -> None:
        html = _complete()
        self.assertFalse(has_skip_link(html))
        errs = semantics_gate_errors(html)
        self.assertFalse(any("skip" in e.lower() for e in errs), errs)
        qa = build_qa(html)
        self.assertFalse(qa["skip_link_required"])
        self.assertTrue(qa["ok"], qa["errors"])

    def test_apply_does_not_insert_skip_link(self) -> None:
        html = _page(
            '<nav><a href="/">Home</a></nav>'
            '<section data-paper-section="hero" id="hero">'
            '<div class="text-6xl font-bold" style="text-wrap: pretty">Welcome</div>'
            "<p>Hello there.</p></section>"
            '<footer><a href="#hero">Home</a>'
            '<form><input type="email" name="email">'
            '<button type="submit">Join</button></form></footer>'
        )
        self.assertFalse(has_skip_link(html))
        out, receipt, _ = apply_semantics(html)
        self.assertFalse(has_skip_link(out))
        self.assertNotIn("skip-link", out.lower())
        self.assertNotIn("Skip to", out)
        self.assertFalse(any("skip" in a.lower() for a in receipt["applied"]))


class InputLabelTest(unittest.TestCase):
    def test_unlabeled_email_fails_until_sr_only_label(self) -> None:
        dirty = _complete(email_labeled=False)
        errs = semantics_gate_errors(dirty)
        self.assertTrue(any("email" in e.lower() and "label" in e.lower() for e in errs), errs)
        out, receipt, css = apply_semantics(dirty, utilities_css="/* utilities */\n")
        self.assertIn('class="sr-only"', out)
        self.assertIn("<label", out)
        self.assertIn(".sr-only", css or "")
        self.assertTrue(any("sr-only" in a for a in receipt["applied"]))
        self.assertFalse(
            any("unlabeled" in e.lower() or ("email" in e.lower() and "label" in e.lower())
                for e in semantics_gate_errors(out)),
            semantics_gate_errors(out),
        )


class MetaAndVerifyCliTest(unittest.TestCase):
    def test_missing_og_does_not_fail(self) -> None:
        html = _complete()
        out, receipt, _ = apply_semantics(html, scrape={"title": "Demo"})
        self.assertTrue(receipt["meta"]["skipped"])
        self.assertIn("not invented", receipt["meta"]["why"])
        self.assertNotIn('property="og:title"', out)
        self.assertFalse(any("og" in e.lower() for e in semantics_gate_errors(out)))

    def test_emits_og_only_from_scrape(self) -> None:
        html = _complete()
        out, receipt, _ = apply_semantics(
            html,
            scrape={
                "title": "Live Title",
                "description": "Live description from scrape.",
                "og_image": "images/og.png",
                "canonical": "https://example.com/",
            },
        )
        self.assertFalse(receipt["meta"]["skipped"])
        self.assertIn('property="og:title"', out)
        self.assertIn("Live Title", out)
        self.assertIn("twitter:card", out)
        self.assertIn('property="og:type"', out)
        self.assertIn('rel="canonical"', out)
        self.assertNotIn("keywords", out.lower())


class PerfAndLangTest(unittest.TestCase):
    def test_hero_eager_rest_lazy(self) -> None:
        html = _page(
            '<header><img src="logo.png" alt="Brand"></header>'
            "<main>"
            '<section data-paper-section="hero" id="hero">'
            '<h1>Welcome</h1><img src="hero.png" alt="Hero"></section>'
            '<section data-paper-section="gallery" id="gallery">'
            '<h2>More</h2><img src="card.png" alt="Card"></section>'
            "</main>"
            "<footer><p>Done.</p></footer>"
        )
        out, receipt, _ = apply_semantics(html)
        self.assertIn('src="hero.png"', out)
        self.assertIn('fetchpriority="high"', out)
        self.assertIn('loading="lazy"', out)
        self.assertTrue(any("hero img" in a for a in receipt["applied"]))
        self.assertTrue(any("loading=lazy" in a for a in receipt["applied"]))
        # Header chrome stays eager.
        header_chunk = out[out.find("<header") : out.find("</header>")]
        self.assertNotIn('loading="lazy"', header_chunk)

    def test_lang_from_scrape_not_invented(self) -> None:
        html = (
            '<!DOCTYPE html><html><head><title>Demo</title></head><body>'
            '<main><section data-paper-section="hero" id="hero">'
            "<h1>Hola</h1></section></main></body></html>"
        )
        out_blank, _, _ = apply_semantics(html)
        self.assertNotIn('lang="en"', out_blank)
        out_es, receipt, _ = apply_semantics(html, scrape={"lang": "es"})
        self.assertIn('lang="es"', out_es)
        self.assertTrue(any("html lang=es" in a for a in receipt["applied"]))

    def test_freeze_structure_does_not_retag_headings(self) -> None:
        html = _page(
            '<header><nav aria-label="Primary"><a href="#">Home</a></nav></header>'
            '<main id="main-content">'
            '<section data-paper-section="hero" id="hero">'
            '<div class="text-6xl font-bold" style="text-wrap:pretty">Keep me a div</div>'
            "<p>A body sentence lives here.</p>"
            "</section></main><footer><p>Done.</p></footer>"
        )
        out, receipt, _ = apply_semantics(html, freeze_structure=True)
        self.assertIn("Keep me a div", out)
        self.assertNotIn("<h1", out)
        self.assertTrue(any("freeze-structure" in s for s in receipt["skipped"]))
        self.assertNotIn("heading_promote", receipt["applied"])

    def test_verify_cli_fails_then_passes(self) -> None:
        dirty = _page(
            '<nav><a href="/">Home</a></nav>'
            '<section data-paper-section="hero" id="hero"><h1>Hi</h1></section>'
        )
        clean = _complete()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            path.write_text(dirty, encoding="utf-8")
            self.assertEqual(_verify.main(["--html", str(path)]), 2)
            path.write_text(clean, encoding="utf-8")
            self.assertEqual(_verify.main(["--html", str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
