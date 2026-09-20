#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import section_22_gate as gate


class Section22GateTest(unittest.TestCase):
    def test_missing_receipt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            for folder in gate.CAPTURE_DIRS:
                (root / folder).mkdir(parents=True)
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("section-align-22.json", errors)

    def test_invented_breakpoint_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            payload = json.loads((root / gate.RECEIPT).read_text())
            payload["widths"] = [1600, 1320, 768, 390]
            (root / gate.RECEIPT).write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("1320", errors)

    def test_open_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            payload = json.loads((root / gate.RECEIPT).read_text())
            payload["sections"][0]["390"] = "open"
            payload["ok"] = False
            (root / gate.RECEIPT).write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("hero@390", errors)

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

    def test_missing_validate_receipt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            gate.validate_receipt_path(root, "hero").unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("VALIDATE receipt", errors)
            self.assertIn("#216", errors)

    def test_open_validate_round_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            path = gate.validate_receipt_path(root, "hero")
            payload = json.loads(path.read_text())
            payload["status"] = "open"
            payload["rounds"][0]["verdict"]["768"] = "miss"
            path.write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("still open", errors)

    def test_empty_seen_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            path = gate.validate_receipt_path(root, "hero")
            payload = json.loads(path.read_text())
            payload["rounds"][0]["seen"] = "ok"
            path.write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("`seen`", errors)

    def test_too_many_rounds_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            path = gate.validate_receipt_path(root, "hero")
            payload = json.loads(path.read_text())
            first = payload["rounds"][0]
            payload["rounds"] = [dict(first, round=n) for n in (1, 2, 3, 4)]
            path.write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("cap is 3", errors)

    def test_missing_semantic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index-semantic.html").unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("index-semantic.html", errors)


if __name__ == "__main__":
    unittest.main()
