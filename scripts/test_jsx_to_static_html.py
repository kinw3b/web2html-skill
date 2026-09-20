#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsx_to_static_html as conv


JSX = """(
  <div style={{ backgroundColor: '#fff', display: 'flex' }}>
    <div style={{ backgroundImage: 'url(https://example.com/photo.png)' }} />
    <svg>
      <polyline points="6 9 12 15 18 9" strokeWidth="2" />
    </svg>
  </div>
)
"""


class JsxToStaticHtmlTest(unittest.TestCase):
    def test_json_payload_becomes_html(self) -> None:
        raw = json.dumps({"jsx": JSX, "contentHash": {"tokens": "abc"}})
        html = conv.to_static_html(raw)
        self.assertIn("<!doctype html>", html)
        self.assertIn('data-export="get_jsx-inline-styles"', html)
        self.assertIn("css/tokens.css", html)
        self.assertIn("background-color: #fff", html)
        self.assertIn("background-image: url(https://example.com/photo.png)", html)
        self.assertNotIn("style={{", html)
        self.assertEqual(len(conv.SELF_CLOSE_DIV_RE.findall(html)), 0)
        self.assertIn("<div style=\"background-image:", html)
        self.assertIn("</div>", html)
        self.assertIn("stroke-width=\"2\"", html)
        self.assertIn("<polyline", html)

    def test_comment_prefixed_json(self) -> None:
        raw = "<!-- paper get_jsx -->\n" + json.dumps({"jsx": "<div style={{ color: 'red' }} />"})
        html = conv.to_static_html(raw)
        self.assertIn("color: red", html)
        self.assertNotRegex(html, r"<div[^>]*/>")

    def test_already_html_is_idempotent(self) -> None:
        first = conv.to_static_html(json.dumps({"jsx": JSX}))
        second = conv.to_static_html(first)
        self.assertEqual(first, second)

    def test_check_rejects_self_closing_div(self) -> None:
        html = '<div style="x:1" />'
        errors = conv.conversion_errors(html)
        self.assertTrue(any("self-closing" in e for e in errors))


class DumpIndexRawTest(unittest.TestCase):
    def test_writes_html_with_tokens(self) -> None:
        import dump_index_raw as dump

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "qa").mkdir()
            (root / "rebuild" / "css" / "tokens.css").write_text(":root { --color-ink: #111; }\n")
            src = root / "qa" / "index-raw.jsx.json"
            src.write_text(json.dumps({"jsx": JSX}), encoding="utf-8")
            receipt = dump.dump_index_raw(root, src)
            html = (root / "rebuild" / "index-raw.html").read_text(encoding="utf-8")
            self.assertTrue(receipt["ok"])
            self.assertIn("css/tokens.css", html)
            self.assertIn("css/fonts.css", html)
            self.assertNotIn("style={{", html)
            self.assertTrue((root / "qa" / "index-raw-22.json").is_file())

    def test_fails_without_tokens(self) -> None:
        import dump_index_raw as dump

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            (root / "qa" / "index-raw.jsx.json").write_text(json.dumps({"jsx": JSX}))
            with self.assertRaises(FileNotFoundError):
                dump.dump_index_raw(root)


if __name__ == "__main__":
    unittest.main()
