#!/usr/bin/env python3
"""Unit tests for Emil GSAP in-view inject + verify (no browser)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_TEMPLATES = _SCRIPTS.parent / "templates"
_VENDOR = _TEMPLATES / "vendor" / "gsap"

_spec = importlib.util.spec_from_file_location(
    "inject_gsap", _SCRIPTS / "inject-gsap-reveal.py"
)
_inject = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_inject)


SAMPLE = """<!doctype html>
<html>
<head><title>Test</title></head>
<body>
<a class="skip-link" href="#main">Skip</a>
<nav id="site-nav"><a href="#features">Features</a></nav>
<header class="site-header"><p>Brand</p></header>
<section class="hero" id="hero">
  <h1>Welcome</h1>
  <p>Above the fold story.</p>
</section>
<main id="main">
  <section id="features">
    <h2>Features</h2>
    <div class="card">Alpha</div>
    <div class="card">Beta</div>
    <svg class="deco" data-decorative viewBox="0 0 10 10"><path d="M0 0"/></svg>
  </section>
  <section id="quote">
    <blockquote>Taste is trained.</blockquote>
  </section>
  <section class="cta-band" id="cta">
    <h2>Get started</h2>
    <a class="cta" href="#cta">Book a call</a>
  </section>
</main>
<footer id="site-footer">
  <p>Footer copy.</p>
</footer>
<div id="qa-overlay" class="qa-overlay">inspector</div>
<script src="js/qa-overlay.js" defer></script>
</body>
</html>
"""


def _require_vendor() -> None:
    missing = [
        name
        for name in ("gsap.min.js", "ScrollTrigger.min.js")
        if not (_VENDOR / name).is_file()
    ]
    if missing:
        raise unittest.SkipTest("vendored GSAP missing: " + ", ".join(missing))
    if not (_TEMPLATES / "gsap-reveal.js").is_file():
        raise unittest.SkipTest("missing templates/gsap-reveal.js")


class GsapRevealInjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _require_vendor()

    def test_mark_reveals_skips_nav_hero_svg_overlay(self) -> None:
        html, count = _inject.mark_reveals(SAMPLE)
        self.assertGreater(count, 0)
        self.assertIn('<section id="features" data-reveal>', html)
        self.assertIn('<div class="card" data-reveal>', html)
        self.assertIn("<blockquote data-reveal>", html)
        self.assertIn('<footer id="site-footer" data-reveal>', html)
        self.assertNotIn("<h2 data-reveal>", html)
        self.assertNotIn('class="reveal"', html)
        self.assertNotIn('class="skip-link" data-reveal', html)
        self.assertNotIn('id="site-nav" data-reveal', html)
        self.assertNotIn('class="hero" id="hero" data-reveal', html)
        self.assertNotIn("<h1 data-reveal>", html)
        self.assertNotIn("data-decorative data-reveal", html)
        self.assertNotIn('class="qa-overlay" data-reveal', html)
        self.assertNotIn("<svg data-reveal", html)
        self.assertNotIn("<path data-reveal", html)

    def test_inject_scripts_idempotent(self) -> None:
        once = _inject.inject_scripts("<html><body></body></html>")
        self.assertIn("gsap.min.js", once)
        self.assertIn("ScrollTrigger.min.js", once)
        self.assertIn("gsap-reveal.js", once)
        twice = _inject.inject_scripts(once)
        self.assertEqual(once.count("gsap-reveal.js"), 1)
        self.assertEqual(twice, once)

    def test_end_to_end_temp_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            html_path = rebuild / "index.html"
            html_path.write_text(SAMPLE, encoding="utf-8")
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "inject-gsap-reveal.py"), str(html_path)]
            )
            self.assertEqual(rc, 0)
            out = html_path.read_text(encoding="utf-8")
            self.assertIn('src="js/vendor/gsap.min.js"', out)
            self.assertIn('src="js/vendor/ScrollTrigger.min.js"', out)
            self.assertIn('src="js/gsap-reveal.js"', out)
            self.assertGreater(out.count("data-reveal"), 0)
            self.assertEqual(out.count('class="reveal"'), 0)
            self.assertTrue((rebuild / "js" / "vendor" / "gsap.min.js").is_file())
            self.assertTrue((rebuild / "js" / "gsap-reveal.js").is_file())
            runtime = (rebuild / "js" / "gsap-reveal.js").read_text(encoding="utf-8")
            self.assertIn('START = "top 75%"', runtime)
            self.assertIn("membersOf", runtime)
            self.assertIn("pickParents", runtime)
            self.assertNotIn("top 85%", runtime)
            self.assertNotIn("top 80%", runtime)
            self.assertNotIn("top 88%", runtime)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "inject-gsap-reveal.py"), str(html_path)]
            )
            self.assertEqual(rc, 0)
            again = html_path.read_text(encoding="utf-8")
            self.assertEqual(again.count("gsap-reveal.js"), 1)
            self.assertEqual(again.count("data-reveal"), out.count("data-reveal"))
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-gsap-reveal.py"), str(root)]
            )
            self.assertEqual(rc, 0)
            qa = json.loads((root / "qa" / "gsap-reveal-qa.json").read_text(encoding="utf-8"))
            self.assertTrue(qa["ok"])
            self.assertGreater(qa["data_reveal"], 0)
            self.assertEqual(qa["class_reveal"], 0)

    def test_inject_skips_index_html_when_polish_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            lock = rebuild / "index.html"
            polish = rebuild / "index-polish.html"
            lock.write_text(SAMPLE, encoding="utf-8")
            polish.write_text(SAMPLE, encoding="utf-8")
            rc = subprocess.call(
                [
                    sys.executable,
                    str(_SCRIPTS / "inject-gsap-reveal.py"),
                    str(rebuild),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertNotIn("gsap-reveal.js", lock.read_text(encoding="utf-8"))
            self.assertNotIn("data-reveal", lock.read_text(encoding="utf-8"))
            polished = polish.read_text(encoding="utf-8")
            self.assertIn("gsap-reveal.js", polished)
            self.assertGreater(polished.count("data-reveal"), 0)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-gsap-reveal.py"), str(root)]
            )
            self.assertEqual(rc, 0)

    def test_verify_fails_class_reveal_and_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            (rebuild / "index.html").write_text(
                '<html><body><div class="reveal">x</div></body></html>',
                encoding="utf-8",
            )
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-gsap-reveal.py"), str(root)]
            )
            self.assertEqual(rc, 2)
            qa = json.loads((root / "qa" / "gsap-reveal-qa.json").read_text(encoding="utf-8"))
            self.assertFalse(qa["ok"])
            self.assertGreaterEqual(qa["class_reveal"], 1)

    def test_mark_parent_groups_not_heading_leaves(self) -> None:
        html, count = _inject.mark_reveals(PETOPIA)
        self.assertGreater(count, 0)
        self.assertIn('<header class="section-head" data-reveal>', html)
        self.assertIn('<div class="section-head" data-reveal>', html)
        self.assertIn('<div class="about-inner" data-reveal>', html)
        self.assertIn('<div class="plan-grid" data-reveal>', html)
        self.assertIn('<div class="service-grid" data-reveal>', html)
        self.assertIn('<ul class="about-features" data-reveal>', html)
        self.assertIn('<article class="plan" data-reveal>', html)
        self.assertNotIn("<h2 data-reveal", html)
        self.assertNotIn("<h3 data-reveal", html)
        self.assertNotIn('class="site-header" data-reveal', html)
        self.assertNotIn('class="hero" data-reveal', html)
        self.assertNotIn('class="section-inner" data-reveal', html)
        self.assertNotIn("<p class=\"eyebrow\" data-reveal", html)

    def test_strip_heading_reveals_on_reinject(self) -> None:
        dirty = PETOPIA.replace("<h2 id=\"pricing-title\">", '<h2 id="pricing-title" data-reveal="">')
        dirty = dirty.replace("<h3>Basic</h3>", '<h3 data-reveal="">Basic</h3>')
        html, _count = _inject.mark_reveals(dirty)
        self.assertNotIn("<h2 data-reveal", html)
        self.assertNotIn("<h3 data-reveal", html)
        self.assertIn('<div class="plan-grid" data-reveal>', html)

    def test_runtime_plan_heads_and_grids(self) -> None:
        groups = _inspect_groups(PETOPIA)
        by_host = {g["host"]: g["members"] for g in groups}
        head_keys = [k for k in by_host if "section-head" in k]
        self.assertTrue(head_keys, groups)
        head_members = by_host[head_keys[0]]
        self.assertTrue(
            any("eyebrow" in m or m.startswith("p.") for m in head_members),
            head_members,
        )
        self.assertTrue(any(m.startswith("h2") for m in head_members), head_members)
        grid_keys = [k for k in by_host if "plan-grid" in k]
        self.assertTrue(grid_keys, groups)
        self.assertEqual(
            [m for m in by_host[grid_keys[0]] if m.startswith("article")],
            ["article.plan", "article.plan.is-featured", "article.plan"],
        )
        about_keys = [k for k in by_host if "about-inner" in k]
        self.assertTrue(about_keys, groups)
        about = by_host[about_keys[0]]
        self.assertTrue(any(m.startswith("h2") for m in about), about)
        self.assertGreaterEqual(sum(1 for m in about if m.startswith("li")), 4, about)
        self.assertTrue(any("about-photo" in m or m.startswith("img") for m in about), about)
        self.assertTrue(
            any("quotes-title" in k for k in by_host),
            groups,
        )
        self.assertFalse(any("h3" in m for g in groups for m in g["members"]))


PETOPIA = """<!doctype html>
<html>
<head><title>Petopia</title></head>
<body>
<header class="site-header"><nav id="site-nav"><a href="#about">About</a></nav></header>
<section class="hero" id="hero"><h1>Hero</h1></section>
<main>
<section id="services">
  <div class="section-inner">
    <header class="section-head">
      <p class="eyebrow">Our Service</p>
      <div class="stack">
        <h2 id="services-title">We Look after your pets</h2>
        <p class="section-lead">From grooming and training.</p>
      </div>
    </header>
    <div class="service-grid">
      <article class="service-card"><h3>Safety First</h3><p>Join us.</p></article>
      <article class="service-card"><h3>Play Yards</h3><p>Join us.</p></article>
    </div>
  </div>
</section>
<section class="about" id="about">
  <div class="about-inner">
    <div class="about-copy">
      <div class="about-head">
        <p class="eyebrow">About Us</p>
        <div class="about-intro">
          <h2 id="about-title">Custom Care for Every Pet</h2>
          <p class="section-lead">From grooming and training.</p>
        </div>
        <img alt="" class="about-paw" src="paw.svg"/>
      </div>
      <ul class="about-features">
        <li>Certified Groomer</li>
        <li>Professional Service</li>
        <li>Security And Trust</li>
        <li>Complete Facilities</li>
      </ul>
    </div>
    <div class="about-media">
      <img alt="Groomer" class="about-photo" src="photo.png"/>
      <img alt="12+ Years" class="about-badge" src="badge.png"/>
    </div>
  </div>
</section>
<section class="pricing" id="pricing">
  <div class="section-inner">
    <div class="section-head">
      <p class="eyebrow">Pricing Plans</p>
      <div class="stack">
        <h2 id="pricing-title">Discover Our Pet Care Plans</h2>
        <p class="section-lead">Whether your furry friend.</p>
      </div>
    </div>
    <div class="plan-grid">
      <article class="plan"><h3>Basic</h3><p class="desc">Essential.</p></article>
      <article class="plan is-featured"><h3>Standard</h3><p class="desc">Essential.</p></article>
      <article class="plan"><h3>Premium</h3><p class="desc">Essential.</p></article>
    </div>
  </div>
</section>
<section class="quotes" id="quotes">
  <div class="section-inner">
    <h2 id="quotes-title">Hear from our customers</h2>
    <div class="quote-grid">
      <article class="quote"><p>One</p></article>
      <article class="quote"><p>Two</p></article>
    </div>
  </div>
</section>
</main>
<footer id="site-footer"><p>Footer</p></footer>
</body>
</html>
"""


def _inspect_groups(html: str) -> list[dict]:
    """Boot the runtime against marked HTML and read __gsapRevealInspect."""
    marked, _count = _inject.mark_reveals(html)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise unittest.SkipTest("playwright missing") from exc

    runtime = (_TEMPLATES / "gsap-reveal.js").read_text(encoding="utf-8")
    page_html = marked.replace(
        "</body>",
        "<script>" + runtime + "</script>\n</body>",
        1,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "page.html"
        path.write_text(page_html, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1600, "height": 900})
                page.goto(path.resolve().as_uri(), wait_until="load")
                page.wait_for_function("() => window.__gsapRevealInspect")
                return page.evaluate("() => window.__gsapRevealInspect()")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
