#!/usr/bin/env python3
"""Pitfall #248 — stage-5 review + self-validation regressions.

The kp-avanta run shipped 17 Astro routes where: every interior compare
paired zero bands (ids never name-matched the 4.2 clips, and the ship path
pointed at a rebuild/{slug}.html that does not exist on an Astro run), the
Framer "All Pages" mega menu shipped empty, chrome links pointed at in-page
anchors, and the human could not tell components from pasted markup.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import astro_build
import interior_seo as seo
import paper_23_disk_gold as gold
import phase_5_scorecard as scorecard
import section_22_gate as gate

_SCRIPTS = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


dropdown = _load("author_nav_dropdown_r", "author-nav-dropdown.py")
wire = _load("wire_astro_routes_r", "wire-astro-routes.py")

FRAMER_SCRAPE = """<html><body><div data-framer-name="Container">
<a data-framer-name="Logo" href="./"><img alt="Brand"></a>
<div data-framer-name="Menu"><a data-framer-name="Variant 1"><p>All Pages</p></a>
<a href="./pricing"><p>Pricing</p></a><a href="./contact"><p>Contact</p></a></div>
<div data-framer-name="Mega Menu"><div data-framer-name="Menu Block">
<a href="./"><p>Homepage 01</p></a><a href="./about"><p>About</p></a>
<a href="./blog/post-03"><p>Blog Details</p></a><a href="./pricing"><p>Pricing</p></a>
</div></div></div>
<footer><a href="./about">About</a><a href="https://x.com">X</a></footer></body></html>"""

HEADER_FRAGMENT = """---
const html = `<header class="site-header"><a class="logo" href="#hero"><img alt="Brand"/></a>
<nav aria-label="Primary"><div data-nav-dropdown=""><button data-nav-dropdown-trigger="" aria-haspopup="true" type="button">All Pages</button><div data-nav-dropdown-panel="" id="nav-dropdown-0" aria-hidden="true"></div></div>
<a href="#pricing-section">Pricing</a><a href="#footer">Contact</a></nav></header>`;
---
<Fragment set:html={html} />
"""


class DiskGoldOrdinalTest(unittest.TestCase):
    def _clips(self, root: Path, slug: str, stems: list[str]) -> None:
        dest = root / "capture" / f"{slug}-desktop" / "source-sections"
        dest.mkdir(parents=True, exist_ok=True)
        for stem in stems:
            (dest / f"{stem}.png").write_bytes(gate.TINY_PNG)

    def test_interior_ids_fall_back_to_capture_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._clips(root, "about", ["01-banner-section", "02-content-section", "03-cta-section", "04-footer"])
            clips = gold.list_clips(root / gold.lander_dir("about", 1600))
            ids = ["about-our-company", "joinourteamsection", "cta-section", "footer"]
            got = {k: (v or {}).get("stem") for k, v in gold.assign_clips(ids, clips, page="about").items()}
            self.assertEqual(got, {
                "about-our-company": "01-banner-section",
                "joinourteamsection": "02-content-section",
                "cta-section": "03-cta-section",
                "footer": "04-footer",
            })

    def test_home_stays_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._clips(root, "home", ["01-banner-section"])
            clips = gold.list_clips(root / gold.lander_dir("home", 1600))
            self.assertIsNone(gold.assign_clips(["hero-x"], clips, page="home")["hero-x"])

    def test_build_index_reads_the_astro_ship(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._clips(root, "about", ["01-banner-section"])
            dist = root / "astro" / "dist" / "about"
            dist.mkdir(parents=True)
            (dist / "index.html").write_text('<main><section id="about-intro"></section></main>')
            mapped = gold.build_index(root, page="about", widths=(1600,),
                                      ship_rel=Path("astro/dist/about/index.html"))
            self.assertEqual(len(mapped["sections"]), 1)
            self.assertTrue(mapped["sections"][0]["source"]["1600"])


class BuilderDropdownTest(unittest.TestCase):
    def test_framer_mega_menu_is_a_submenu(self) -> None:
        menus = dropdown.scrape_dropdowns(FRAMER_SCRAPE)
        self.assertEqual([m["label"] for m in menus], ["All Pages"])
        labels = [i["label"] for i in menus[0]["items"]]
        self.assertEqual(labels, ["Homepage 01", "About", "Blog Details", "Pricing"])

    def test_astro_header_panel_is_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-site").mkdir()
            (root / "source-site" / "index.html").write_text(FRAMER_SCRAPE)
            comps = root / "astro" / "src" / "components"
            comps.mkdir(parents=True)
            (comps / "Header.astro").write_text(HEADER_FRAGMENT)
            layouts = root / "astro" / "src" / "layouts"
            layouts.mkdir(parents=True)
            (layouts / "BaseLayout.astro").write_text("<html><head>\n  </head>\n<body><slot />\n  </body></html>")
            self.assertEqual(dropdown.main([str(root), "--astro"]), 0)
            header = (comps / "Header.astro").read_text()
            self.assertIn("Homepage 01", header)
            self.assertTrue(header.startswith("---\nconst html = `"))
            layout = (layouts / "BaseLayout.astro").read_text()
            self.assertIn("/styles/nav-dropdown.css", layout)
            self.assertIn("/scripts/nav-dropdown.js", layout)
            self.assertTrue((root / "astro" / "public" / "scripts" / "nav-dropdown.js").is_file())


class SourceLabelRoutingTest(unittest.TestCase):
    ROWS = [
        {"slug": "about", "path": "/about"},
        {"slug": "pricing", "path": "/pricing"},
        {"slug": "contact", "path": "/contact"},
        {"slug": "blog-post-01", "path": "/blog/post-01", "template": "/blog/*"},
    ]

    def test_relative_and_template_hrefs(self) -> None:
        mapping = seo.route_map(self.ROWS)
        self.assertEqual(seo.dest_for_href("./about", mapping), "/about/")
        self.assertEqual(seo.dest_for_href("./", mapping), "/")
        self.assertEqual(seo.dest_for_href("./blog/post-03", mapping), "/blog-post-01/")

    def test_anchor_href_routes_by_source_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-site").mkdir()
            (root / "source-site" / "index.html").write_text(FRAMER_SCRAPE)
            mapping = seo.route_map(self.ROWS)
            labels = seo.source_label_map(root, mapping)
            self.assertEqual(labels["pricing"], "/pricing/")
            self.assertEqual(labels["blog details"], "/blog-post-01/")
            out, n = seo.rewrite_anchor_hrefs(
                '<a href="#pricing-section">Pricing</a><a class="logo" href="#hero">x</a>'
                '<a href="#faq">Unknown</a>',
                mapping, labels,
            )
            self.assertIn('href="/pricing/"', out)
            self.assertIn('class="logo" href="/"', out)
            self.assertIn('href="#faq"', out)  # never invent a route
            self.assertEqual(n, 2)

    def test_link_audit_flags_dead_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            comps = root / "astro" / "src" / "components"
            comps.mkdir(parents=True)
            (comps / "Header.astro").write_text('<a href="#pricing-section">Pricing</a><a href="/about/">About</a>')
            routes = [{"slug": "about", "route": "/about/"}, {"slug": "pricing", "route": "/pricing/"}]
            audit = wire.link_audit(root, routes, {"pricing": "/pricing/"})
            self.assertEqual(len(audit["dead"]), 1)
            self.assertEqual(audit["unreachable"], ["/pricing/"])


class ComponentReviewTest(unittest.TestCase):
    def test_stamp_components_marks_every_root_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            astro = Path(tmp) / "astro"
            comps = astro / "src" / "components"
            comps.mkdir(parents=True)
            (comps / "TeamSection.astro").write_text(
                "---\nconst html = `<section id=\"a\"><p>x</p></section>\n<section id=\"b\"></section>`;\n---\n"
                "<Fragment set:html={html} />\n"
            )
            (comps / "Btn.astro").write_text("---\nconst { href = '#' } = Astro.props;\n---\n<a class=\"btn\" href={href}>Go</a>\n")
            self.assertEqual(sorted(astro_build.stamp_components(astro)), ["Btn", "TeamSection"])
            team = (comps / "TeamSection.astro").read_text()
            self.assertEqual(team.count('data-astro-component="TeamSection"'), 2)
            self.assertNotIn('<p data-astro-component', team)
            self.assertIn('<a data-astro-component="Btn"', (comps / "Btn.astro").read_text())
            self.assertEqual(astro_build.stamp_components(astro), [])

    def test_review_overlay_is_wired_relative_and_bare_url_stays_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            (dist / "about").mkdir(parents=True)
            (dist / "index.html").write_text("<html><head></head><body><main></main></body></html>")
            (dist / "about" / "index.html").write_text("<html><head></head><body><main></main></body></html>")
            wired = astro_build.inject_review_overlay(dist)
            self.assertEqual(sorted(wired), ["about/index.html", "index.html"])
            about = (dist / "about" / "index.html").read_text()
            self.assertIn("../qa-review/qa-overlay.js", about)
            self.assertIn('data-qa-ship="final"', about)
            self.assertIn('"components"', about)  # boot snippet knows the mode
            self.assertTrue((dist / "qa-review" / "qa-overlay.css").is_file())
            js = (dist / "qa-review" / "qa-overlay.js").read_text()
            self.assertIn("data-astro-component", js)


class ScorecardTest(unittest.TestCase):
    def test_scorecard_counts_components_and_dead_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            (root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": [{"slug": "about"}]}))
            (root / "qa" / "phase-5-links.json").write_text(json.dumps({"sourceLabels": {"pricing": "/pricing/"}}))
            dist = root / "astro" / "dist"
            (dist / "about").mkdir(parents=True)
            page = (
                '<html><body><header data-astro-component="Header"><nav><a href="#p">Pricing</a>'
                '<a href="../index.html">Home</a></nav></header><main>'
                '<section data-astro-component="TeamSection"><h1>T</h1></section><section>inline</section>'
                "</main><footer></footer></body></html>"
            )
            (dist / "index.html").write_text(page.replace("../index.html", "index.html"))
            (dist / "about" / "index.html").write_text(page)
            receipt = scorecard.score(root)
            about = next(p for p in receipt["pages"] if p["slug"] == "about")
            self.assertEqual((about["componentBlocks"], about["inlineBlocks"]), (1, 1))
            self.assertEqual(about["links"]["chromeDead"], 1)
            self.assertEqual(about["links"]["chromeLive"], 1)
            self.assertFalse(about["compareLoop"]["ran"])
            self.assertEqual(receipt["totals"]["componentShare"], 50)
            self.assertTrue((root / "qa" / "phase-5-scorecard.md").is_file())


if __name__ == "__main__":
    unittest.main()
