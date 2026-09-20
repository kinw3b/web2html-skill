#!/usr/bin/env python3
"""Tests for lint-docs.py — the pipeline.json / doc-surface linter (Review O1/O2)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_LINT = _SCRIPTS / "lint-docs.py"
_SPEC = importlib.util.spec_from_file_location("lint_docs", _LINT)
lint = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(lint)


class ExpandStepIds(unittest.TestCase):
    def test_single_id(self) -> None:
        self.assertEqual(lint.expand_step_ids("**2.2 author the page**"), {"2.2"})

    def test_endash_range_expands_the_middle(self) -> None:
        self.assertEqual(lint.expand_step_ids("4.1–4.3 extra Paper pages"), {"4.1", "4.2", "4.3"})

    def test_hyphen_range_expands(self) -> None:
        self.assertEqual(lint.expand_step_ids("6.1-6.3 Astro convert"), {"6.1", "6.2", "6.3"})

    def test_slash_list(self) -> None:
        self.assertEqual(lint.expand_step_ids("5.2 / 5.3 clip loops"), {"5.2", "5.3"})


class OrchestratorStamp(unittest.TestCase):
    def test_bold_stamp(self) -> None:
        self.assertEqual(
            lint.orchestrator_stamp("**Orchestrator version (web2html):** **2.17.1**"), "2.17.1"
        )

    def test_frontmatter_version(self) -> None:
        self.assertEqual(lint.orchestrator_stamp("---\nname: x\nversion: 2.17.1\n---\n"), "2.17.1")

    def test_none_when_absent(self) -> None:
        self.assertIsNone(lint.orchestrator_stamp("no version here"))


class ParseRoutingTiers(unittest.TestCase):
    def test_reads_tier_and_expands_ranges(self) -> None:
        doc = (
            "## Per-step\n\n"
            "| Step | Gate | Tier |\n"
            "|---|---|---|\n"
            "| 1.1 light scrape | machine | T2 |\n"
            "| **2.2 author the page** | self | **T1** |\n"
            "| 4.1–4.3 extra Paper pages | machine | T2 |\n\n"
            "## Next\n"
        )
        tiers = lint.parse_routing_tiers(doc)
        self.assertEqual(tiers["1.1"], "T2")
        self.assertEqual(tiers["2.2"], "T1")
        self.assertEqual(tiers["4.2"], "T2")  # the expanded middle of the range


class Integration(unittest.TestCase):
    """The live repo must pass the gate (non-strict) — this fails if drift is reintroduced."""

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(_LINT), *extra], capture_output=True, text=True
        )

    def test_repo_is_green_non_strict(self) -> None:
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("lint-docs: OK", r.stdout)

    def test_strict_surfaces_the_known_doc_debt(self) -> None:
        # Dangling pitfall citations / orphan reference are warnings today; --strict fails on them.
        r = self._run("--strict")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
