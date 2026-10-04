#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import phase_5_nav_audit as nav

HEADER = """<header><a class="logo" href="#">Brand</a>
<nav aria-label="Primary">NAV</nav></header>"""

FLAT_NAV = '<a href="#">About</a><a href="#">Work</a>'

DROPDOWN_NAV = """<a href="#">About</a>
<span data-nav-dropdown><a href="#" data-nav-dropdown-trigger aria-haspopup="true"
 aria-expanded="false" aria-controls="nav-dropdown-0">Products</a>
<div data-nav-dropdown-panel id="nav-dropdown-0" aria-hidden="true">
<a href="#">Widget</a><a href="#">Gadget</a></div></span>"""

BURGER_NAV = FLAT_NAV + '<button class="burger" data-nav-toggle aria-controls="nav-panel"></button>'
BURGER_PANEL = '<div id="nav-panel" data-nav-panel class="nav-panel"><a href="#">About</a></div>'

SCRAPE = """<!DOCTYPE html><html><body><header><nav>
<ul><li><a href="/products">Products</a>
<ul><li><a href="/widget">Widget</a></li><li><a href="/gadget">Gadget</a></li></ul>
</li><li><a href="/about">About</a></li></ul>
</nav></header></body></html>"""

DROPDOWN_MANIFEST = {
    "kind": "dropdown",
    "mode": "dropdown",
    "pageSlug": "home",
    "states": [
        {
            "component": "01 · products",
            "closedFile": "00-closed.html",
            "openFile": "00-open.html",
            "triggerLabel": "Products",
            "items": [{"i": 0, "label": "Widget"}, {"i": 1, "label": "Gadget"}],
        }
    ],
}

BURGER_MANIFEST = {
    "kind": "nav-mobile-390",
    "mode": "hamburger",
    "pageSlug": "home",
    "states": [{"component": "01 · menu", "triggerLabel": "Menu"}],
}


def _project(root: Path, *, nav_html: str = FLAT_NAV, panel: str = "",
             scrape: bool = True, reel: bool = False, interior: bool = True) -> Path:
    """A minimal 5.4-complete tree: built pages + Header + scrape + reel."""
    (root / "astro" / "src" / "components").mkdir(parents=True)
    (root / "astro" / "src" / "components" / "Header.astro").write_text(
        HEADER.replace("NAV", nav_html), encoding="utf-8"
    )
    home = root / "astro" / "dist"
    home.mkdir(parents=True)
    (home / "index.html").write_text(
        HEADER.replace("NAV", nav_html) + panel + "<main><section id='hero'></section></main>",
        encoding="utf-8",
    )
    if interior:
        about = home / "about"
        about.mkdir(parents=True)
        (about / "index.html").write_text(
            HEADER.replace("NAV", nav_html) + panel + "<main><section id='about-hero'></section></main>",
            encoding="utf-8",
        )
    (root / "qa").mkdir(parents=True)
    pages = [{"slug": "home"}] + ([{"slug": "about"}] if interior else [])
    (root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": pages}) + "\n")
    if scrape:
        (root / "source-site").mkdir(parents=True)
        (root / "source-site" / "index.html").write_text(SCRAPE, encoding="utf-8")
    if interior:
        nav.plant_compare_loop(root, "about", ["about-hero"])
    if reel:
        kinds = root / "source-site" / "components" / "home"
        (kinds / "dropdown").mkdir(parents=True)
        (kinds / "dropdown" / "manifest.json").write_text(json.dumps(DROPDOWN_MANIFEST))
        (kinds / "nav-mobile-390").mkdir(parents=True)
        (kinds / "nav-mobile-390" / "manifest.json").write_text(json.dumps(BURGER_MANIFEST))
    return root


class Phase5NavAuditTest(unittest.TestCase):
    def test_flat_nav_fails_the_scrape_submenu(self) -> None:
        """The regression this audit exists for: a scrape submenu + a flat
        built nav = missing, on EVERY page (the Header is shared)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp))
            self.assertEqual(nav.main([str(root)]), 2)
            receipt = json.loads((root / nav.OUT).read_text())
            self.assertFalse(receipt["ok"])
            by_slug = {page["slug"]: page for page in receipt["pages"]}
            self.assertIn("home", by_slug)
            self.assertIn("about", by_slug)
            for slug in ("home", "about"):
                broken = by_slug[slug]["broken"]
                self.assertTrue(any(
                    row["trigger"] == "Products" and row["state"] == "missing"
                    for row in broken
                ), broken)
            # 5.5 gate refuses on this receipt.
            self.assertTrue(nav.gate_errors(root))

    def test_wired_dropdown_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV)
            self.assertEqual(nav.main([str(root)]), 0)
            receipt = json.loads((root / nav.OUT).read_text())
            self.assertTrue(receipt["ok"], receipt["errors"])
            for page in receipt["pages"]:
                products = [row for row in page["items"] if row["trigger"] == "Products"]
                self.assertTrue(products)
                self.assertEqual(products[0]["state"], "wired")
            self.assertEqual(nav.gate_errors(root), [])

    def test_unwired_trigger_without_a_panel_fails(self) -> None:
        trigger_only = (
            '<a href="#">About</a>'
            '<a href="#" data-nav-dropdown-trigger aria-haspopup="true">Products</a>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=trigger_only)
            self.assertEqual(nav.main([str(root)]), 2)
            receipt = json.loads((root / nav.OUT).read_text())
            states = {
                row["state"]
                for page in receipt["pages"]
                for row in page["items"]
                if row["trigger"] == "Products"
            }
            self.assertIn("unwired", states)

    def test_hover_reel_drawer_is_inventoried_and_wired_check_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV, reel=True)
            # Burger captured but never authored → drawer missing on every page.
            self.assertEqual(nav.main([str(root)]), 2)
            receipt = json.loads((root / nav.OUT).read_text())
            broken = [
                row for page in receipt["pages"] for row in page["broken"]
                if row["kind"] == "drawer"
            ]
            self.assertTrue(broken)
            self.assertTrue(all(row["state"] == "missing" for row in broken))
            # Author the burger: toggle + panel → wired.
            for page_rel in ("astro/dist/index.html", "astro/dist/about/index.html"):
                path = root / page_rel
                text = path.read_text()
                text = text.replace("</nav>", BURGER_NAV.split(FLAT_NAV)[-1] + "</nav>")
                text = text.replace("</header>", BURGER_PANEL + "</header>")
                path.write_text(text)
            (root / "astro" / "src" / "components" / "Header.astro").write_text(
                HEADER.replace("NAV", DROPDOWN_NAV + BURGER_NAV.split(FLAT_NAV)[-1])
                + BURGER_PANEL,
                encoding="utf-8",
            )
            self.assertEqual(nav.main([str(root)]), 0)

    def test_empty_run_skips_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), scrape=False)
            self.assertEqual(nav.main([str(root)]), 0)
            receipt = json.loads((root / nav.OUT).read_text())
            self.assertTrue(receipt["ok"])
            self.assertTrue(receipt["skipped"])
            self.assertEqual(nav.gate_errors(root), [])

    def test_banned_skip_reason_fails(self) -> None:
        """A Capture-Tool-style skip is a failure, exactly like Pitfall #210."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), scrape=False)
            self.assertEqual(nav.main([str(root)]), 0)
            receipt_path = root / nav.OUT
            receipt = json.loads(receipt_path.read_text())
            receipt["skipped"][0]["reason"] = (
                "Capture Tool did not run — dropdown capture is off, do not hunt"
            )
            receipt_path.write_text(json.dumps(receipt))
            errors = nav.gate_errors(root)
            self.assertTrue(any("banned skip" in e for e in errors))

    def test_href_rewrite_does_not_stale_the_receipt(self) -> None:
        """5.5 rewrites hrefs onto panel items — the receipt must survive it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV)
            self.assertEqual(nav.main([str(root)]), 0)
            ship = root / "astro" / "dist" / "about" / "index.html"
            ship.write_text(
                ship.read_text().replace('<a href="#">Widget</a>', '<a href="/widget/">Widget</a>')
            )
            self.assertEqual(nav.gate_errors(root), [])
            # A structural change (panel deleted) DOES stale it.
            ship.write_text(ship.read_text().replace("data-nav-dropdown-panel", "data-x"))
            self.assertTrue(any("stale" in e for e in nav.gate_errors(root)))

    def test_gate_refuses_without_a_receipt_or_a_built_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV)
            errors = nav.gate_errors(root)
            self.assertTrue(any("missing qa/phase-5-nav.json" in e for e in errors))
            self.assertEqual(nav.main([str(root)]), 0)
            # Delete a built page → stale (fingerprint file gone is not stale,
            # but the audit rerun would report missing) — rerun catches it.
            (root / "astro" / "dist" / "about" / "index.html").unlink()
            self.assertEqual(nav.main([str(root)]), 2)
            self.assertTrue(nav.gate_errors(root))

    def test_gate_covers_every_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV)
            self.assertEqual(nav.main([str(root)]), 0)
            # A new interior appears after the audit → gate demands a rerun.
            nav.plant_compare_loop(root, "contact", ["contact-hero"])
            contact = root / "astro" / "dist" / "contact"
            contact.mkdir(parents=True)
            (contact / "index.html").write_text(HEADER.replace("NAV", DROPDOWN_NAV))
            pages = json.loads((root / "qa" / "phase-4-pages.json").read_text())
            pages["pages"].append({"slug": "contact"})
            (root / "qa" / "phase-4-pages.json").write_text(json.dumps(pages))
            errors = nav.gate_errors(root)
            self.assertTrue(any("contact" in e for e in errors))

    def test_gate_refuses_when_the_compare_loop_never_ran(self) -> None:
        """Pitfall #248: a green nav receipt is not enough — every interior
        needs side-by-sides and an APPLIED compare wave covering each band."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(Path(tmp), nav_html=DROPDOWN_NAV)
            self.assertEqual(nav.main([str(root)]), 0)
            self.assertEqual(nav.gate_errors(root), [])
            wave = next((root / "qa" / "agent-runs").glob("*/compare/wave.json"))
            payload = json.loads(wave.read_text())
            payload.pop("appliedAt")
            wave.write_text(json.dumps(payload))
            self.assertTrue(any("no applied compare wave" in e for e in nav.gate_errors(root)))
            payload["appliedAt"] = "now"
            wave.write_text(json.dumps(payload))
            report = root / "qa" / "side-by-side" / "about" / "report.json"
            data = json.loads(report.read_text())
            for row in data["stops"]:
                row["side"] = None
            report.write_text(json.dumps(data))
            self.assertTrue(any("0 side-by-sides" in e for e in nav.gate_errors(root)))


if __name__ == "__main__":
    unittest.main()
