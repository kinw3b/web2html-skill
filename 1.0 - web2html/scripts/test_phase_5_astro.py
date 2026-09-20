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

HOME = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Home</title>
  <meta name="description" content="Signed homepage" />
  <link rel="stylesheet" href="css/tokens.css" />
  <link rel="stylesheet" href="css/qa-overlay.css"/>
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
  <script src="js/qa-overlay.js"></script>
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
        (rebuild / "js" / "main.js").write_text("console.log('ok');\n")
        (rebuild / "images" / "hero.png").write_bytes(b"png")
        (rebuild / "fonts" / "figtree-500.woff2").write_bytes(b"woff")
        (rebuild / "index-polish.html").write_text(HOME)
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
            self.assertEqual(record_pages.main([str(root)]), 0)
            pages = json.loads((root / "qa" / "phase-5-pages.json").read_text())
            self.assertTrue(pages["ok"])
            self.assertEqual(pages["pages"][0]["astro"], "astro/src/pages/about.astro")
            self.assertEqual(pages["pages"][0]["route"], "/about/")
            self.assertEqual(pages["pages"][0]["dist"], "astro/dist/about/index.html")

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
            (dist / "about").mkdir(parents=True)
            (dist / "index.html").write_text('<link href="/styles/tokens.css"><a href="/about/">A</a>')
            (dist / "about" / "index.html").write_text('<link href="/styles/tokens.css"><a href="/">H</a>')
            self.assertEqual(build_dist.main([str(root), "--skip-build"]), 0)
            self.assertIn('href="../styles/tokens.css"', (dist / "about" / "index.html").read_text())
            self.assertIn('href="about/index.html"', (dist / "index.html").read_text())
            build = json.loads((root / "qa" / "phase-5-build.json").read_text())
            self.assertEqual([row["dist"] for row in build["pages"]], ["astro/dist/index.html", "astro/dist/about/index.html"])

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


if __name__ == "__main__":
    unittest.main()
