#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import emit_fonts


class EmitFontsTest(unittest.TestCase):
    def test_writes_font_face_from_library_and_rebuild_fonts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "design-library").mkdir()
            (root / "rebuild" / "fonts").mkdir(parents=True)
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "qa").mkdir()
            (root / "design-library" / "library.json").write_text(
                json.dumps(
                    {
                        "proposedTokens": [
                            {
                                "type": "fontFamily",
                                "name": "--font-sans-figtree",
                                "value": "Figtree",
                                "family": "Figtree",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            woff = root / "rebuild" / "fonts" / "figtree-medium-normal.woff2"
            woff.write_bytes(b"wOFF2")
            receipt = emit_fonts.emit_fonts(root)
            css = (root / "rebuild" / "css" / "fonts.css").read_text(encoding="utf-8")
            self.assertTrue(receipt["ok"])
            self.assertIn("Figtree", receipt["families"])
            self.assertIn("@font-face", css)
            self.assertIn("font-family: Figtree;", css)
            self.assertIn("../fonts/figtree-500-normal-", css)
            self.assertIn("font-weight: 500;", css)
            self.assertNotIn("100 900", css)
            self.assertIn("system-ui, sans-serif", css)

    def test_copies_scrape_latin_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "design-library").mkdir()
            (root / "source-site" / "assets").mkdir(parents=True)
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "qa").mkdir()
            (root / "design-library" / "library.json").write_text(
                json.dumps(
                    {
                        "proposedTokens": [
                            {
                                "type": "fontFamily",
                                "name": "--font-sans-figtree",
                                "value": "Figtree",
                                "family": "Figtree",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            hashed = root / "source-site" / "assets" / "_Xmz-latin.woff2"
            hashed.write_bytes(b"wOFF2")
            (root / "source-site" / "scraped-tokens.md").write_text(
                "| Family | Weight | File | unicode-range | Style |\n"
                "| Figtree | 500 | `_Xmz-latin.woff2` | U+0000-00FF | normal |\n",
                encoding="utf-8",
            )
            emit_fonts.emit_fonts(root)
            dest = next((root / "rebuild" / "fonts").glob("figtree-500-normal-*.woff2"))
            self.assertTrue(dest.is_file())
            css = (root / "rebuild" / "css" / "fonts.css").read_text(encoding="utf-8")
            self.assertIn("figtree-500-normal-", css)
            self.assertEqual(dest.read_bytes(), hashed.read_bytes())

    def source_project(self, root: Path, faces: list[tuple], legacy: bool = True) -> None:
        """Distinct test bytes exercise copying, not browser font validity."""
        assets = root / "source-site/assets"
        assets.mkdir(parents=True)
        css = []
        table = ["| Family | Weight | File | unicode-range |" + ("" if legacy else " Style |")]
        for filename, weight, style, urange, data in faces:
            (assets / filename).write_bytes(data)
            css.append(f'@font-face {{font-family: Demo; font-weight: {weight}; '
                       f'font-style: {style}; src: url("https://example.com/{filename}");'
                       + (f' unicode-range: {urange};' if urange else '') + '}')
            table.append(f"| Demo | {weight} | `{filename}` | {urange or 'full'} |"
                         + ("" if legacy else f" {style} |"))
        (root / "source-site/index.html").write_text("\n".join(css))
        (root / "source-site/scraped-tokens.md").write_text("\n".join(table))

    def test_same_weight_regular_and_italic_never_overwrite_in_either_order(self) -> None:
        pair = [("hashA.woff2", "400", "normal", "U+0000-00FF", b"upright"),
                ("hashB.woff2", "400", "italic", "U+0000-00FF", b"italic")]
        for reverse in (False, True):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.source_project(root, pair[::-1] if reverse else pair)
                receipt = emit_fonts.emit_fonts(root)
                by_style = {f["style"]: f for f in receipt["faces"]}
                self.assertEqual(set(by_style), {"normal", "italic"})
                self.assertNotEqual(by_style["normal"]["file"], by_style["italic"]["file"])
                for style, expected in (("normal", b"upright"), ("italic", b"italic")):
                    self.assertEqual((root / "rebuild/fonts" / by_style[style]["file"]).read_bytes(), expected)
                first_css = (root / emit_fonts.FONTS_CSS).read_bytes()
                emit_fonts.emit_fonts(root)
                self.assertEqual((root / emit_fonts.FONTS_CSS).read_bytes(), first_css)
                self.assertEqual(emit_fonts.font_face_errors(root), [])

    def test_old_overwritten_normal_face_fails_byte_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("r.woff2", "700", "normal", "", b"upright"),
                                       ("i.woff2", "700", "italic", "", b"italic")])
            rec = emit_fonts.emit_fonts(root)
            normal = next(f for f in rec["faces"] if f["style"] == "normal")
            (root / "rebuild/fonts" / normal["file"]).write_bytes(b"italic")
            self.assertIn("font bytes do not match", " ".join(emit_fonts.font_face_errors(root)))

    def test_missing_face_does_not_fall_back_to_other_style_or_rewrite_css(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("r.woff2", "400", "normal", "", b"upright"),
                                       ("i.woff2", "400", "italic", "", b"italic")])
            emit_fonts.emit_fonts(root)
            css = (root / emit_fonts.FONTS_CSS).read_bytes()
            (root / "source-site/assets/r.woff2").unlink()
            with self.assertRaisesRegex(ValueError, "missing exact source font"):
                emit_fonts.emit_fonts(root)
            self.assertEqual((root / emit_fonts.FONTS_CSS).read_bytes(), css)

    def test_unknown_legacy_hash_fails_instead_of_assuming_normal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("hash.woff2", "400", "italic", "", b"italic")])
            (root / "source-site/index.html").unlink()
            with self.assertRaisesRegex(ValueError, "unknown font style"):
                emit_fonts.emit_fonts(root)
            self.assertFalse((root / emit_fonts.FONTS_CSS).exists())

    def test_explicit_style_table_works_without_source_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("hash.woff2", "400", "italic", "", b"italic")], legacy=False)
            (root / "source-site/index.html").unlink()
            receipt = emit_fonts.emit_fonts(root)
            self.assertEqual(receipt["faces"][0]["style"], "italic")
            self.assertEqual(receipt["faces"][0]["weight"], "400")

    def test_html_only_keeps_latin_style_and_variable_range_and_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("cyrillic.woff", "100 900", "oblique 0deg 12deg", "U+0460-052F", b"cyrillic"),
                                       ("latin.woff", "100 900", "oblique 0deg 12deg", "U+0000-00FF", b"latin")])
            (root / "source-site/scraped-tokens.md").unlink()
            rec = emit_fonts.emit_fonts(root)
            self.assertEqual(len(rec["faces"]), 1)
            css = (root / emit_fonts.FONTS_CSS).read_text()
            self.assertIn("font-weight: 100 900;", css)
            self.assertIn("font-style: oblique 0deg 12deg;", css)
            self.assertIn('format("woff")', css)
            self.assertEqual(emit_fonts.font_face_errors(root), [])

    def test_two_latin_faces_same_descriptor_keep_distinct_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_project(root, [("a.woff2", "400", "normal", "U+0000-00FF", b"version-a"),
                                       ("b.woff2", "400", "normal", "U+0000-00FF", b"version-b")])
            rec = emit_fonts.emit_fonts(root)
            self.assertEqual(len({f["file"] for f in rec["faces"]}), 2)
            self.assertEqual(emit_fonts.font_face_errors(root), [])


if __name__ == "__main__":
    unittest.main()
