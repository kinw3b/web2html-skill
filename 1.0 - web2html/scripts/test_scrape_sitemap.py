import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("scrape-sitemap.py")
SPEC = importlib.util.spec_from_file_location("scrape_sitemap", MODULE_PATH)
scrape = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(scrape)

URLSET = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/pricing</loc></url>
  <url><loc>https://other.com/nope</loc></url>
  <url><loc>https://example.com/logo.png</loc></url>
</urlset>
"""

INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>
"""


class ScrapeSitemapTests(unittest.TestCase):
    def test_parse_urlset_and_index(self):
        pages, children = scrape.parse_sitemap_xml(URLSET)
        self.assertIn("https://example.com/about/", pages)
        self.assertEqual(children, [])
        pages, children = scrape.parse_sitemap_xml(INDEX)
        self.assertEqual(pages, [])
        self.assertEqual(children, ["https://example.com/sitemap-pages.xml"])

    def test_robots_and_path_helpers(self):
        self.assertEqual(
            scrape.parse_robots("User-agent: *\nSitemap: https://example.com/s.xml\n"),
            ["https://example.com/s.xml"],
        )
        self.assertEqual(scrape.normalize_path("https://example.com/about/"), "/about")
        self.assertEqual(scrape.paper_name_from_path("/blog/hello-world"), "Blog / Hello World")
        self.assertTrue(scrape.is_dropped_path("/"))
        self.assertTrue(scrape.is_dropped_path("/cdn-cgi/l/email"))
        self.assertTrue(scrape.is_dropped_path("/hero.png"))

    def test_run_writes_receipt_and_drops_home(self):
        bodies = {
            "https://example.com/sitemap.xml": URLSET,
            "https://example.com/robots.txt": "Sitemap: https://example.com/sitemap.xml\n",
        }

        def fetch(url: str) -> str:
            if url not in bodies:
                raise scrape.URLError("missing")
            return bodies[url]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-site").mkdir()
            (root / "source-site" / "pages.json").write_text(
                json.dumps([{"path": "/", "url": "https://example.com/", "file": "index.html"}])
            )
            receipt = scrape.run(root, cap=40, fetch_fn=fetch)
            self.assertEqual(receipt["source"], "sitemap")
            paths = [row["path"] for row in receipt["pages"]]
            self.assertEqual(paths, ["/about", "/pricing"])
            self.assertTrue((root / "qa" / "phase-4-sitemap.json").is_file())
            pages = json.loads((root / "source-site" / "pages.json").read_text())
            self.assertTrue(any(row.get("path") == "/about" for row in pages))

    def test_crawl_fallback_when_no_sitemap(self):
        def fetch(url: str) -> str:
            raise scrape.URLError("no sitemap")

        html = '<html><a href="/team">Team</a><a href="https://example.com/careers">Jobs</a><a href="/">Home</a></html>'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-site").mkdir()
            (root / "source-site" / "index.html").write_text(html)
            (root / "source-site" / "pages.json").write_text(
                json.dumps([{"path": "/", "url": "https://example.com/"}])
            )
            receipt = scrape.run(root, cap=40, fetch_fn=fetch)
            self.assertEqual(receipt["source"], "crawl")
            self.assertEqual([row["path"] for row in receipt["pages"]], ["/team", "/careers"])

    def test_collapse_templates_keeps_one_sample_per_dynamic_parent(self):
        rows = [
            {"path": p, "url": f"https://example.com{p}", "slug": "s", "paperName": "P"}
            for p in [
                "/about",
                "/pricing",
                "/blog",
                "/blog/post-a",
                "/blog/post-b",
                "/blog/post-c",
                "/blog/post-d",
                "/legal/privacy",
                "/legal/terms",
            ]
        ]
        kept, collapsed = scrape.collapse_templates(rows)
        kept_paths = [row["path"] for row in kept]
        # Distinct templates and the blog index survive; only one blog post.
        self.assertEqual(
            kept_paths,
            ["/about", "/pricing", "/blog", "/blog/post-a", "/legal/privacy", "/legal/terms"],
        )
        sample = next(row for row in kept if row["path"] == "/blog/post-a")
        self.assertEqual(sample["template"], "/blog/*")
        self.assertTrue(sample["templateSample"])
        self.assertEqual([row["path"] for row in collapsed], ["/blog/post-b", "/blog/post-c", "/blog/post-d"])
        # Two legal pages stay below the template threshold — both kept.
        self.assertNotIn("template", kept[-1])


if __name__ == "__main__":
    unittest.main()
