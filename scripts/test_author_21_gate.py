#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import author_21_gate as gate


class Author21GateTest(unittest.TestCase):
    def test_missing_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("rebuild/index-semantic.html", errors)
            self.assertFalse(gate.ready(root))

    def test_dump_and_skip_link_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-semantic.html").write_text(
                '<html><body data-export="get_jsx-inline-styles">'
                '<a id="skip-to-content">Skip</a><p><div>Soup</div></p></body></html>'
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("get_jsx", errors)
            self.assertIn("skip-link", errors)
            self.assertIn("invalid HTML nesting", errors)

    def test_passing_artifacts_are_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            self.assertEqual(gate.gate_errors(root), [])
            self.assertTrue(gate.ready(root))

    def test_missing_index_raw_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-raw.html").unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("index-raw.html", errors)

    def test_json_index_raw_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-raw.html").write_text(
                '{"jsx": "<div />"}',
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("JSON", errors)
            self.assertIn("dump_index_raw", errors)

    def test_self_closing_div_index_raw_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-raw.html").write_text(
                '<html data-export="get_jsx-inline-styles">'
                '<link rel="stylesheet" href="css/tokens.css">'
                '<div style="background-image:url(x.png)" /></html>\n',
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("self-closing", errors)

    def test_in_page_hash_hrefs_are_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            ship = root / "rebuild" / "index-semantic.html"
            ship.write_text(
                ship.read_text(encoding="utf-8").replace(
                    "<p>Brand</p>",
                    '<p>Brand</p><nav><a href="#">Home</a><a href="#about">About</a></nav>',
                ),
                encoding="utf-8",
            )
            self.assertEqual(gate.gate_errors(root), [])

    def test_source_and_external_hrefs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-semantic.html").write_text(
                "<!doctype html><html><body>"
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=x">'
                '<a href="https://calendly.com/book">Book</a>'
                '<a href="/pricing">Pricing</a>'
                '<a href="mailto:hi@example.com">Email</a>'
                '<a href="#cta">In page</a>'
                "</body></html>\n",
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("source/external", errors)
            self.assertIn("https://calendly.com/book", errors)
            self.assertIn("/pricing", errors)
            self.assertIn("mailto:hi@example.com", errors)
            self.assertNotIn("fonts.googleapis.com", errors)
            self.assertNotIn("#cta", errors)


if __name__ == "__main__":
    unittest.main()
