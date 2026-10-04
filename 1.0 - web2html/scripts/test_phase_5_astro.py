#!/usr/bin/env python3
"""Phase 5 — Astro-first site: scaffold + shared chrome, authored bodies, routes, SEO."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


html_to_astro = _load("html_to_astro", "html_to_astro.py")
astro_build = _load("astro_build", "astro_build.py")
scaffold_astro = _load("scaffold_astro", "scaffold-astro.py")
extract_astro = _load("extract_astro", "extract-astro-components.py")
convert_home = _load("convert_astro_home", "convert-astro-home.py")
record_pages = _load("record_phase_5_pages", "record-phase-5-pages.py")
wire_astro = _load("wire_astro", "wire-astro-routes.py")
build_dist = _load("build_astro_dist", "build-astro-dist.py")
open_review = _load("open_phase_5_review", "open-phase-5-review.py")
shared_sections = _load("shared_sections", "shared_sections.py")
nav_audit = _load("phase_5_nav_audit", "phase_5_nav_audit.py")

CTA_COPY = (
    "<h2>Ready to grow your business with us today</h2>"
    "<p>Join thousands of teams who trust our platform to plan, track and ship their best work every week.</p>"
    '<img src="images/cta-photo.jpg" alt="" />'
)
FAQ_COPY = (
    "<h2>Frequently asked questions about our service</h2>"
    "<p>How long does setup take for a new team account?</p><p>Most teams finish onboarding in under a day with our guided checklist.</p>"
    "<p>Can I cancel my plan at any time without a fee?</p><p>Yes, every plan is month to month and you can cancel from settings.</p>"
)
TEAM_COPY = (
    "<h2>Meet the people behind the studio</h2>"
    "<p>Ana Ruiz founder and creative director with fifteen years in brand design.</p>"
    "<p>Leo Park lead engineer who keeps every launch fast and accessible for everyone.</p>"
)


def _capture(root: Path, slug: str, sections: dict[str, str]) -> None:
    cap = root / "capture" / f"{slug}-desktop"
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "00-header.html").write_text("<header>nav</header>")
    for idx, (name, body) in enumerate(sections.items(), start=1):
        (cap / f"{idx:02d}-{name}.html").write_text(f"<header layer-name=\"{name}\">{body}</header>")

HOME = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Home</title>
  <meta name="description" content="Signed homepage" />
  <link rel="stylesheet" href="css/tokens.css" />
  <link rel="stylesheet" href="css/fonts.css" />
  <link rel="stylesheet" href="css/qa-overlay.css"/>
  <link rel="stylesheet" href="css/nav-menu.css" />
  <style>
    .wrap { max-width: 1200px; margin: 0 auto; }
    .hero { background: url(../images/hero.png); }
  </style>
</head>
<body>
  <header class="site-header"><a href="index.html">Brand</a><nav><a href="about.html">About</a><a href="#">Work</a></nav></header>
  <main>
    <section id="hero"><h1>Hello</h1><img src="images/hero.png" alt="Hero" /></section>
    <a class="btn btn-primary" href="about.html">About</a>
    <!-- component: Card -->
    <article class="card" data-component="Card"><h2>Team</h2></article>
  </main>
  <footer><a href="about.html">About</a></footer>
  <script src="js/vendor/gsap.min.js"></script>
  <script src="js/nav-menu.js"></script>
  <script src="js/qa-overlay.js"></script>
  <script>window.__boot = { nav: true };</script>
</body>
</html>
"""

ABOUT_ASTRO = """---
import BaseLayout from '../layouts/BaseLayout.astro';
import Header from '../components/Header.astro';
import Footer from '../components/Footer.astro';
const title = `About`;
const description = ``;
const lang = `en`;
---
<BaseLayout title={title} description={description} lang={lang}>
  <Header />
  <main>
    <section id="about-hero"><h1>About</h1><p>Interior.</p><a class="btn btn-primary" href="#">Home</a><a href="#">Work</a><img src="/images/hero.png" alt="Hero" /></section>
  </main>
  <Footer />
</BaseLayout>
"""

ABOUT_LIVE = (
    "<html lang='es'><head>"
    "<title>About Live</title>"
    '<meta name="description" content="About from scrape.">'
    '<meta property="og:image" content="https://example.com/og-about.png">'
    "</head><body></body></html>"
)

REUSE_HOME = HOME.replace(
    "<!-- component: Card -->",
    f'<section id="cta">{CTA_COPY}<a class="btn btn-primary" href="about.html">About</a></section>\n    <!-- component: Card -->',
)


def _page(slug: str, imports: list[str], body: str) -> str:
    lines = "".join(f"import {name} from '../components/{name}.astro';\n" for name in imports)
    return (
        "---\n"
        "import BaseLayout from '../layouts/BaseLayout.astro';\n"
        "import Header from '../components/Header.astro';\n"
        "import Footer from '../components/Footer.astro';\n"
        f"{lines}"
        f"const title = `{slug}`;\nconst description = ``;\nconst lang = `en`;\n"
        "---\n"
        "<BaseLayout title={title} description={description} lang={lang}>\n"
        f"  <Header />\n  <main>\n    {body}\n  </main>\n  <Footer />\n"
        "</BaseLayout>\n"
    )


class Phase5AstroTests(unittest.TestCase):
    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        rebuild = root / "rebuild"
        (rebuild / "css").mkdir(parents=True)
        (rebuild / "js").mkdir()
        (rebuild / "images").mkdir()
        (rebuild / "fonts").mkdir()
        (rebuild / "css" / "tokens.css").write_text(":root { --color-ink: #111; }\n")
        (rebuild / "css" / "fonts.css").write_text(
            '@font-face { src: url("../fonts/figtree-500.woff2") format("woff2"); }\n'
        )
        (rebuild / "css" / "site.css").write_text("body { color: var(--color-ink); }\n")
        (rebuild / "css" / "nav-menu.css").write_text(".nav__dropdown { opacity: 0; visibility: hidden; }\n")
        (rebuild / "js" / "main.js").write_text("console.log('ok');\n")
        (rebuild / "js" / "nav-menu.js").write_text("/* nav-menu */\n")
        (rebuild / "js" / "vendor").mkdir(parents=True)
        (rebuild / "js" / "vendor" / "gsap.min.js").write_text("/* gsap */\n")
        (rebuild / "images" / "hero.png").write_bytes(b"png")
        (rebuild / "fonts" / "figtree-500.woff2").write_bytes(b"woff")
        (rebuild / "index.html").write_text(HOME)
        (root / "qa").mkdir()
        (root / "qa" / "phase-4-pages.json").write_text(
            json.dumps({"pages": [{"slug": "about", "url": "https://example.com/about"}]}) + "\n"
        )
        (root / "qa" / "phase-4-sitemap.json").write_text(
            json.dumps({
                "pages": [
                    {"path": "/about", "slug": "about", "paperName": "About", "url": "https://example.com/about"},
                    {"path": "/work", "slug": "work", "paperName": "Work"},
                ]
            })
            + "\n"
        )
        (root / "qa" / "scrape-meta.json").write_text(
            json.dumps({"title": "Home Title", "description": "Home description.", "og_image": "images/home.png", "lang": "en"})
            + "\n"
        )
        (root / "design-library").mkdir()
        (root / "design-library" / "library.json").write_text(
            json.dumps({"components": [{"name": "btn-primary"}, {"name": "Card"}]}),
            encoding="utf-8",
        )
        buttons = root / "source-site" / "components" / "home" / "buttons"
        buttons.mkdir(parents=True)
        (buttons / "manifest.json").write_text(
            json.dumps({
                "kind": "buttons",
                "states": [{"component": "btn-primary", "label": "About", "token": "btn-primary"}],
            }),
            encoding="utf-8",
        )
        (root / "qa" / "paper-comments.json").write_text(
            json.dumps({
                "openCount": 0,
                "threads": [
                    {"text": "This is a component: Card. Reuse the card across every route."}
                ],
            }),
            encoding="utf-8",
        )
        return root

    def _author_about(self, root: Path, text: str = ABOUT_ASTRO) -> None:
        (root / "astro" / "src" / "pages" / "about.astro").write_text(text)
        (root / "rebuild" / "about-raw.html").write_text("<html><body><h1>About</h1></body></html>")

    def test_discovers_paper_and_comment_components(self):
        html = (
            "<main>"
            '<a class="btn btn-primary" href="about.html">About</a>'
            "<!-- component: Card -->"
            '<article class="card" data-component="Card"><h2>Team</h2></article>'
            "<a href=\"#only-once\">Unique</a>"
            "</main>"
        )
        hits = html_to_astro.discover_page_candidates(html, nominated={"Card"})
        names = {row["name"] for row in hits}
        self.assertIn("BtnPrimary", names)
        self.assertIn("Card", names)
        self.assertNotIn("Unique", names)

    def test_href_rewrite(self):
        self.assertEqual(html_to_astro.astro_href("about.html"), "/about/")
        self.assertEqual(html_to_astro.astro_href("index.html#cta"), "/#cta")
        self.assertEqual(html_to_astro.astro_href("css/tokens.css"), "/styles/tokens.css")
        self.assertEqual(html_to_astro.astro_href("images/hero.png"), "/images/hero.png")
        self.assertEqual(html_to_astro.astro_href("#about"), "#about")
        self.assertEqual(html_to_astro.astro_href("mailto:hi@x.com"), "mailto:hi@x.com")

    def test_dist_relativize_for_file_urls(self):
        self.assertEqual(astro_build.relative_url("/styles/a.css", 1), "../styles/a.css")
        self.assertEqual(astro_build.relative_url("/about/", 0), "about/index.html")
        self.assertEqual(astro_build.relative_url("/", 1), "../index.html")
        self.assertEqual(astro_build.relative_url("/#cta", 1), "../index.html#cta")
        self.assertEqual(astro_build.relative_url("//cdn.x/y.js", 1), "//cdn.x/y.js")
        self.assertEqual(astro_build.relative_url("https://x.com/", 2), "https://x.com/")
        html = '<link href="/styles/a.css"><a href="/about/">A</a><style>body{background:url(/images/b.png)}</style>'
        out = astro_build.relativize_html(html, 1)
        self.assertIn('href="../styles/a.css"', out)
        self.assertIn('href="../about/index.html"', out)
        self.assertIn("url(../images/b.png)", out)
        self.assertEqual(astro_build.dist_page_rel("index"), "astro/dist/index.html")
        self.assertEqual(astro_build.dist_page_rel("about"), "astro/dist/about/index.html")

    def test_full_phase_5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            # 5.1 — scaffold + shared chrome + homepage
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertTrue((root / "astro" / "package.json").is_file())
            self.assertTrue((root / "qa" / "phase-5-scaffold.json").is_file())
            fonts = (root / "astro" / "public" / "styles" / "fonts.css").read_text()
            self.assertIn("/fonts/figtree-500.woff2", fonts)
            layout = (root / "astro" / "src" / "layouts" / "BaseLayout.astro").read_text()
            self.assertIn("canonical", layout)
            self.assertIn("ogImage", layout)
            # wiring is derived from the ship head, in ship order (#240)
            for ref in ("/styles/tokens.css", "/styles/fonts.css", "/styles/nav-menu.css"):
                self.assertIn(ref, layout)
            order = [layout.index(ref) for ref in
                     ("/styles/tokens.css", "/styles/fonts.css", "/styles/nav-menu.css")]
            self.assertEqual(order, sorted(order))
            self.assertIn('src="/scripts/vendor/gsap.min.js"', layout)
            self.assertIn('src="/scripts/nav-menu.js"', layout)
            boot = (root / "astro" / "public" / "scripts" / "ship-inline-1.js").read_text()
            self.assertIn("window.__boot = { nav: true }", boot)
            self.assertIn('src="/scripts/ship-inline-1.js"', layout)
            # `{` in the .astro template is an Astro expression — the ship script must not be inlined
            self.assertNotIn("window.__boot", layout.split("---", 2)[-1])
            self.assertIn("is:inline", layout)
            self.assertNotIn("qa-overlay", layout)
            # inline <style> is materialized — fixture ships css/site.css, so site-inline.css
            inline_sheet = root / "astro" / "public" / "styles" / "site-inline.css"
            self.assertTrue(inline_sheet.is_file())
            self.assertIn(".wrap", inline_sheet.read_text())
            self.assertIn("/images/hero.png", inline_sheet.read_text())  # url() rewritten
            self.assertIn('href="/styles/site-inline.css"', layout)
            self.assertTrue((root / "astro" / "public" / "scripts" / "vendor" / "gsap.min.js").is_file())
            scaffold_receipt = json.loads((root / "qa" / "phase-5-scaffold.json").read_text())
            self.assertTrue(scaffold_receipt["ok"], scaffold_receipt["errors"])
            self.assertEqual(scaffold_receipt["wiring"]["inlineCss"], "site-inline.css")
            self.assertEqual(extract_astro.main([str(root)]), 0)
            header = (root / "astro" / "src" / "components" / "Header.astro").read_text()
            self.assertIn("/about/", header)
            self.assertNotIn("qa-overlay", header)
            self.assertTrue((root / "astro" / "src" / "components" / "BtnPrimary.astro").is_file())
            self.assertTrue((root / "astro" / "src" / "components" / "Card.astro").is_file())
            receipt = json.loads((root / "qa" / "phase-5-components.json").read_text())
            names = {row["name"] for row in receipt["inventory"]}
            self.assertEqual({"Header", "Footer", "BtnPrimary", "Card"} - names, set())
            self.assertEqual(convert_home.main([str(root)]), 0)
            home = (root / "astro" / "src" / "pages" / "index.astro").read_text()
            self.assertIn("import Header", home)
            self.assertIn("import BtnPrimary", home)
            self.assertIn("import Card", home)
            self.assertIn("<h1>Hello</h1>", home)
            self.assertIn("/images/hero.png", home)
            self.assertIn("<BtnPrimary", home)
            self.assertIn("<Card", home)
            self.assertNotIn("qa-overlay", home)
            self.assertFalse((root / "astro" / "src" / "pages" / "about.astro").exists())
            self.assertTrue(json.loads((root / "qa" / "phase-5-home.json").read_text())["ok"])

            # 5.2 — a worker authored only the <main> body on the shared chrome
            self._author_about(root)
            self.assertEqual(shared_sections.main([str(root)]), 0)  # re-plan after the dump
            self.assertEqual(record_pages.main([str(root)]), 0)
            pages = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertTrue(pages["ok"])
            self.assertEqual(pages["pages"][0]["astro"], "astro/src/pages/about.astro")
            self.assertEqual(pages["pages"][0]["route"], "/about/")
            self.assertEqual(pages["pages"][0]["dist"], "astro/dist/about/index.html")

            # 5.4+ — hidden-nav audit on the BUILT pages gates 5.5 (Pitfall #247)
            dist = root / "astro" / "dist"
            (dist / "about").mkdir(parents=True)
            (dist / "index.html").write_text('<link rel="stylesheet" href="/styles/tokens.css"><a href="/about/">A</a>')
            (dist / "about" / "index.html").write_text('<link rel="stylesheet" href="/styles/tokens.css"><a href="/">H</a>')
            self.assertEqual(nav_audit.main([str(root)]), 0)
            nav_receipt = json.loads((root / "qa" / "phase-5-nav.json").read_text())
            self.assertTrue(nav_receipt["ok"], nav_receipt["errors"])
            self.assertEqual({row["slug"] for row in nav_receipt["pages"]}, {"home", "about"})
            # 5.5 refuses without the audit receipt
            (root / "qa" / "phase-5-nav.json").unlink()
            with self.assertRaises(ValueError) as ctx:
                wire_astro.wire(root, skip_build=True, fetch_fn=lambda url: ABOUT_LIVE)
            self.assertIn("phase-5-nav", str(ctx.exception))
            self.assertEqual(nav_audit.main([str(root)]), 0)
            # 5.5 also refuses until the interior /compare loop ran (Pitfall #248)
            with self.assertRaises(ValueError) as ctx:
                wire_astro.wire(root, skip_build=True, fetch_fn=lambda url: ABOUT_LIVE)
            self.assertIn("side-by-side/about", str(ctx.exception))
            nav_audit.plant_compare_loop(root, "about", ["about-hero"])
            from unittest import mock

            self.addCleanup(mock.patch.stopall)
            import page_loop as _pl

            mock.patch.object(_pl, "gate_errors", return_value=[]).start()

            # 5.5 — routes + per-page SEO (build skipped: no npm in tests)
            receipt = wire_astro.wire(root, skip_build=True, fetch_fn=lambda url: ABOUT_LIVE)
            self.assertTrue(receipt["ok"], receipt["errors"])
            self.assertEqual({row["route"] for row in receipt["routes"]}, {"/", "/about/"})
            header = (root / "astro" / "src" / "components" / "Header.astro").read_text()
            self.assertIn('href="/about/"', header)
            self.assertIn('href="/work/"', header)  # label "Work" on a # placeholder → sitemap route
            about = (root / "astro" / "src" / "pages" / "about.astro").read_text()
            self.assertIn('href="/"', about)  # label "Home" on a # placeholder → /
            self.assertIn("const title = `About Live`;", about)
            self.assertIn("About from scrape.", about)
            self.assertIn("const lang = `es`;", about)
            self.assertIn("https://example.com/about", about)
            self.assertIn("og-about.png", about)
            self.assertIn("canonical={canonical}", about)
            self.assertIn("ogImage={ogImage}", about)
            self.assertNotIn("Home Title", about)
            home = (root / "astro" / "src" / "pages" / "index.astro").read_text()
            self.assertIn("images/home.png", home)
            self.assertNotIn("About Live", home)
            self.assertTrue((root / "qa" / "phase-5-semantics" / "about.json").is_file())
            links = json.loads((root / "qa" / "phase-5-links.json").read_text())
            self.assertTrue(links["ok"])
            self.assertFalse(links["built"])

            # 5.3 / 5.4 — built pages are the ship; check-only pass on a planted dist
            dist = root / "astro" / "dist"
            (dist / "about").mkdir(parents=True, exist_ok=True)
            (dist / "styles").mkdir(parents=True)
            (dist / "styles" / "tokens.css").write_text(":root { --x: 1; }\n")
            (dist / "index.html").write_text('<link rel="stylesheet" href="/styles/tokens.css"><a href="/about/">A</a>')
            (dist / "about" / "index.html").write_text('<link rel="stylesheet" href="/styles/tokens.css"><a href="/">H</a>')
            self.assertEqual(build_dist.main([str(root), "--skip-build"]), 0)
            self.assertIn('href="../styles/tokens.css"', (dist / "about" / "index.html").read_text())
            self.assertIn('href="about/index.html"', (dist / "index.html").read_text())
            build = json.loads((root / "qa" / "phase-5-build.json").read_text())
            self.assertEqual([row["dist"] for row in build["pages"]], ["astro/dist/index.html", "astro/dist/about/index.html"])
            self.assertTrue(all(row["unresolved"] == [] for row in build["pages"]))

            # 5.6 — review note over the built routes
            self.assertEqual(open_review.main([str(root), "--no-open"]), 0)
            review = (root / "qa" / "phase-5-review.md").read_text()
            self.assertIn("/about/", review)
            self.assertIn("mark --step 5.6 --status done", review)

    def test_record_rejects_inline_chrome_and_missing_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual(extract_astro.main([str(root)]), 0)
            bad = ABOUT_ASTRO.replace("import Header from '../components/Header.astro';\n", "").replace(
                "<main>", "<header>dup</header><main>"
            )
            self._author_about(root, bad)
            self.assertEqual(record_pages.main([str(root)]), 2)
            receipt = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertFalse(receipt["ok"])
            joined = " ".join(receipt["errors"])
            self.assertIn("does not import Header", joined)
            self.assertIn("inlines <header>/<footer>", joined)

    def test_record_needs_raw_dump_and_no_external_hrefs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual(extract_astro.main([str(root)]), 0)
            (root / "astro" / "src" / "pages" / "about.astro").write_text(
                ABOUT_ASTRO.replace('href="#">Home', 'href="https://example.com/about">Home')
            )
            self.assertEqual(record_pages.main([str(root)]), 2)
            receipt = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertIn("missing rebuild/about-raw.html", receipt["errors"])
            (root / "rebuild" / "about-raw.html").write_text("<html></html>")
            self.assertEqual(record_pages.main([str(root)]), 2)
            receipt = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertTrue(any("source/external hrefs" in err for err in receipt["errors"]))

    def _reuse_project(self, tmp: str) -> Path:
        """Home ships a CTA band; about + pricing + contact repeat it; FAQ/Team repeat only inside."""
        root = self._project(tmp)
        (root / "rebuild" / "index.html").write_text(REUSE_HOME)
        (root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": [
            {"slug": "about"}, {"slug": "pricing"}, {"slug": "contact"},
        ]}) + "\n")
        _capture(root, "about", {"hero-section": "<h1>About our studio and story</h1><p>We started small in a garage.</p>",
                                 "team-section": TEAM_COPY, "cta-section": CTA_COPY})
        _capture(root, "pricing", {"faq-section": FAQ_COPY, "cta-section": CTA_COPY})
        _capture(root, "contact", {"faq-section": FAQ_COPY, "team": TEAM_COPY,
                                   "cta-section": CTA_COPY.replace("today", "now")})
        for slug in ("about", "pricing", "contact"):
            (root / "rebuild" / f"{slug}-raw.html").write_text("<html><body><div></div></body></html>")
        return root

    def test_shared_sections_plan_groups_by_copy_not_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._reuse_project(tmp)
            plan = shared_sections.plan(root)
            groups = {g["name"]: g for g in plan["groups"]}
            self.assertEqual(set(groups), {"CtaSection", "FaqSection", "TeamSection"})
            cta = groups["CtaSection"]
            self.assertEqual(cta["origin"], "home")
            self.assertFalse(cta["buildFirst"])
            self.assertEqual(cta["pages"], ["index", "about", "contact", "pricing"])
            self.assertEqual(cta["anchor"]["sectionId"], "cta")
            matches = {m["page"]: m["match"] for m in cta["members"]}
            self.assertEqual(matches["contact"], "variant")  # one word differs
            for name in ("FaqSection", "TeamSection"):
                self.assertEqual(groups[name]["origin"], "interior")
                self.assertTrue(groups[name]["buildFirst"])
            # "team" on contact joins TeamSection by copy, despite a different name
            self.assertEqual(groups["TeamSection"]["interiorPages"], ["about", "contact"])
            self.assertNotIn("HeroSection", groups)  # one-off band stays inline
            self.assertEqual(plan["byPage"]["contact"], ["CtaSection", "FaqSection", "TeamSection"])

    def test_raw_dump_footer_band_is_not_a_shared_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            footer = "<p>" + " ".join(f"link{i} company legal" for i in range(12)) + "</p>"
            home = HOME.replace("<footer>", f"<footer>{footer}")
            (root / "rebuild" / "index.html").write_text(home)
            (root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": [{"slug": "a"}, {"slug": "b"}]}))
            for slug in ("a", "b"):
                (root / "rebuild" / f"{slug}-raw.html").write_text(
                    f"<html><body><div><div><h1>{slug} unique page hero copy here today</h1></div><div>{footer}</div></div></body></html>"
                )
            self.assertEqual(shared_sections.plan(root)["groups"], [])

    def test_shared_home_section_becomes_component_on_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._reuse_project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual(extract_astro.main([str(root)]), 0)
            receipt = json.loads((root / "qa" / "phase-5-components.json").read_text())
            self.assertEqual(receipt["shared"]["fromHome"], ["CtaSection"])
            self.assertEqual(sorted(receipt["shared"]["buildFirst"]), ["FaqSection", "TeamSection"])
            cta = (root / "astro" / "src" / "components" / "CtaSection.astro").read_text()
            self.assertIn("Ready to grow your business", cta)
            self.assertIn("/about/", cta)  # hrefs rewritten like the rest of the chrome
            self.assertFalse((root / "astro" / "src" / "components" / "FaqSection.astro").exists())
            self.assertEqual(convert_home.main([str(root)]), 0)
            home = (root / "astro" / "src" / "pages" / "index.astro").read_text()
            self.assertIn("import CtaSection from '../components/CtaSection.astro';", home)
            self.assertIn("<CtaSection />", home)
            self.assertNotIn("Ready to grow your business", home)
            self.assertIn("<Card", home)  # comment component next to it still converts

    def test_record_enforces_shared_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._reuse_project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual(extract_astro.main([str(root)]), 0)
            pages = root / "astro" / "src" / "pages"
            # Worker re-authors every shared band inline — the old behaviour.
            for slug in ("about", "pricing", "contact"):
                (pages / f"{slug}.astro").write_text(
                    _page(slug, [], f'<section id="cta">{CTA_COPY}</section><section>{FAQ_COPY}</section>')
                )
            self.assertEqual(record_pages.main([str(root)]), 2)
            errors = " ".join(json.loads((root / "qa" / "phase-5-pages.json").read_text())["errors"])
            self.assertIn("build-first shared section FaqSection is missing", errors)
            self.assertIn("about.astro re-authors shared section CtaSection", errors)
            self.assertIn("contact.astro re-authors shared section TeamSection", errors)

            # Controller builds the interior-only bands first; pages import everything.
            comps = root / "astro" / "src" / "components"
            (comps / "FaqSection.astro").write_text(f"<section>{FAQ_COPY}</section>\n")
            (comps / "TeamSection.astro").write_text(f"<section>{TEAM_COPY}</section>\n")
            (pages / "about.astro").write_text(_page("about", ["TeamSection", "CtaSection"],
                                                     "<section><h1>About</h1></section><TeamSection /><CtaSection />"))
            (pages / "pricing.astro").write_text(_page("pricing", ["FaqSection", "CtaSection"], "<FaqSection /><CtaSection />"))
            # Imports the component AND pastes the copy — still a re-author.
            (pages / "contact.astro").write_text(_page(
                "contact", ["FaqSection", "TeamSection", "CtaSection"],
                f"<FaqSection /><TeamSection /><CtaSection /><section>{FAQ_COPY}</section>",
            ))
            self.assertEqual(record_pages.main([str(root)]), 2)
            errors = json.loads((root / "qa" / "phase-5-pages.json").read_text())["errors"]
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("contact.astro renders <FaqSection /> AND pastes its copy inline", errors[0])
            (pages / "contact.astro").write_text(_page(
                "contact", ["FaqSection", "TeamSection", "CtaSection"], "<FaqSection /><TeamSection /><CtaSection />",
            ))
            self.assertEqual(record_pages.main([str(root)]), 0)
            receipt = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertEqual(sorted(receipt["shared"]), ["CtaSection", "FaqSection", "TeamSection"])

    def test_record_refuses_a_stale_reuse_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual(extract_astro.main([str(root)]), 0)  # plans before about has any source
            self.assertEqual(json.loads((root / "qa" / "phase-5-reuse.json").read_text())["pending"], ["about"])
            self._author_about(root)  # the dump lands after the plan
            (root / "rebuild" / "about-raw.html").write_text(
                f"<html><body><div><div>{CTA_COPY}</div></div></body></html>"
            )
            self.assertEqual(record_pages.main([str(root)]), 2)
            errors = " ".join(json.loads((root / "qa" / "phase-5-pages.json").read_text())["errors"])
            self.assertIn("predates the section source for about", errors)
            (root / "qa" / "phase-5-reuse.json").unlink()
            self.assertEqual(record_pages.main([str(root)]), 2)
            errors = " ".join(json.loads((root / "qa" / "phase-5-pages.json").read_text())["errors"])
            self.assertIn("missing qa/phase-5-reuse.json", errors)

    def test_ship_wiring_extracts_in_order(self):
        wiring = html_to_astro.ship_wiring(
            '<html><head>'
            '<link rel="stylesheet" href="css/tokens.css">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/x.css">'
            '<link rel="preload" href="fonts/a.woff2">'
            '<style>.a{color:red}</style>'
            '<script type="application/ld+json">{"@type":"Thing"}</script>'
            '</head><body>'
            '<script src="js/vendor/g.js" defer></script>'
            '<script>window.x = 1;</script>'
            '<script src="js/qa-overlay.js"></script>'
            '</body></html>'
        )
        links = [row["href"] for row in wiring["styles"] if row["kind"] == "link"]
        self.assertEqual(links, ["/styles/tokens.css", "https://fonts.googleapis.com/x.css"])
        self.assertFalse(wiring["styles"][0]["external"])
        self.assertTrue(wiring["styles"][1]["external"])
        self.assertEqual(wiring["styles"][-1]["kind"], "style")
        self.assertEqual(wiring["styles"][-1]["css"], ".a{color:red}")
        self.assertEqual(wiring["styles"][-1]["where"], "head")
        self.assertEqual(
            [(row["kind"], row.get("src")) for row in wiring["scripts"]],
            [("src", "/scripts/vendor/g.js"), ("inline", None)],
        )
        self.assertEqual(wiring["scripts"][0]["flags"], ["defer"])
        self.assertEqual(wiring["scripts"][1]["js"], "window.x = 1;")

    def test_scaffold_materializes_inline_css_as_site_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            (root / "rebuild" / "css" / "site.css").unlink()
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            site = root / "astro" / "public" / "styles" / "site.css"
            self.assertTrue(site.is_file())
            self.assertIn(".wrap", site.read_text())
            layout = (root / "astro" / "src" / "layouts" / "BaseLayout.astro").read_text()
            self.assertIn('href="/styles/site.css"', layout)
            receipt = json.loads((root / "qa" / "phase-5-scaffold.json").read_text())
            self.assertTrue(receipt["ok"], receipt["errors"])
            self.assertEqual(receipt["wiring"]["inlineCss"], "site.css")

    def test_scaffold_config_has_no_trailing_slash_and_seeds_live_collections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            astro = root / "astro"
            config = (astro / "astro.config.mjs").read_text()
            self.assertNotIn("trailingSlash", config)
            self.assertNotIn("build:", config)  # default directory format: dist/{slug}/index.html
            pkg = json.loads((astro / "package.json").read_text())
            self.assertRegex(pkg["dependencies"]["astro"], r"^\^7\.")
            live = (astro / "src" / "live.config.ts").read_text()
            self.assertIn("defineLiveCollection", live)
            self.assertIn("CMS_API_URL", live)
            self.assertIn("loadEntry", (astro / "src" / "loaders" / "cms.ts").read_text())
            self.assertIn(".env", (astro / ".gitignore").read_text().split())
            # a wired CMS loader survives a re-scaffold
            (astro / "src" / "live.config.ts").write_text("// wired\n")
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            self.assertEqual((astro / "src" / "live.config.ts").read_text(), "// wired\n")
            receipt = json.loads((root / "qa" / "phase-5-scaffold.json").read_text())
            self.assertIn("src/live.config.ts", receipt["liveCollections"])

    def test_scaffold_fails_on_dangling_asset_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            index = root / "rebuild" / "index.html"
            index.write_text(index.read_text().replace('href="css/nav-menu.css"', 'href="css/ghost.css"'))
            self.assertEqual(scaffold_astro.main([str(root)]), 2)
            receipt = json.loads((root / "qa" / "phase-5-scaffold.json").read_text())
            self.assertFalse(receipt["ok"])
            self.assertIn("/styles/ghost.css", " ".join(receipt["errors"]))

    def test_build_dist_flags_unresolved_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            dist = root / "astro" / "dist"
            (dist / "styles").mkdir(parents=True)
            (dist / "styles" / "tokens.css").write_text(":root{}\n")
            (dist / "index.html").write_text(
                '<link rel="stylesheet" href="/styles/tokens.css">'
                '<link rel="stylesheet" href="/styles/ghost.css">'
                '<script src="/scripts/nope.js"></script>'
            )
            self.assertEqual(build_dist.main([str(root), "--skip-build"]), 2)
            receipt = json.loads((root / "qa" / "phase-5-build.json").read_text())
            self.assertFalse(receipt["ok"])
            joined = " ".join(receipt["errors"])
            self.assertIn("ghost.css", joined)
            self.assertIn("nope.js", joined)
            self.assertEqual(receipt["pages"][0]["unresolved"], ["styles/ghost.css", "scripts/nope.js"])

    def test_style_blocks_keep_cascade_and_inline_js_stays_out_of_the_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            (root / "rebuild" / "css" / "site.css").unlink()
            (root / "rebuild" / "index.html").write_text(
                "<!doctype html><html><head>"
                '<link rel="stylesheet" href="css/tokens.css" media="print">'
                "<style>.first{color:red}</style>"
                '<link rel="stylesheet" href="css/nav-menu.css">'
                "<style>.sr{position:absolute}</style>"
                "<script>document.documentElement.classList.add(\"intro-pending\");</script>"
                "</head><body><main><h1>Hi</h1></main>"
                "<script>window.__boot = { nav: true };</script>"
                "</body></html>"
            )
            self.assertEqual(scaffold_astro.main([str(root)]), 0)
            layout = (root / "astro" / "src" / "layouts" / "BaseLayout.astro").read_text()
            body = layout.split("---", 2)[-1]
            self.assertNotIn("window.__boot", body)
            self.assertNotIn("intro-pending", body)
            self.assertIn('media="print"', layout)
            head, _, rest = body.partition("</head>")
            self.assertIn('src="/scripts/ship-inline-1.js"', head)
            self.assertIn('src="/scripts/ship-inline-2.js"', rest)
            self.assertIn("intro-pending", (root / "astro" / "public" / "scripts" / "ship-inline-1.js").read_text())
            self.assertIn("{ nav: true }", (root / "astro" / "public" / "scripts" / "ship-inline-2.js").read_text())
            i_tokens = layout.index("/styles/tokens.css")
            i_site = layout.index('href="/styles/site.css"')
            i_nav = layout.index("/styles/nav-menu.css")
            i_site2 = layout.index('href="/styles/site-2.css"')
            self.assertLess(i_tokens, i_site)
            self.assertLess(i_site, i_nav)
            self.assertLess(i_nav, i_site2)
            self.assertIn(".first", (root / "astro" / "public" / "styles" / "site.css").read_text())
            self.assertNotIn(".sr", (root / "astro" / "public" / "styles" / "site.css").read_text())
            self.assertIn(".sr", (root / "astro" / "public" / "styles" / "site-2.css").read_text())
            receipt = json.loads((root / "qa" / "phase-5-scaffold.json").read_text())
            self.assertEqual(receipt["wiring"]["inlineSheets"], ["site.css", "site-2.css"])


if __name__ == "__main__":
    unittest.main()
