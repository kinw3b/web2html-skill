from __future__ import annotations

import json
import unittest

import open_doc

ORCA_ENV = {"ORCA_TERMINAL_HANDLE": "term_1", "ORCA_WORKTREE_ID": "repo::/wt", "ORCA_CLI_COMMAND": "/bin/orca"}
URI = "file:///tmp/demo/pipeline.html"


def runner(code: int, body: object):
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv)
        return code, json.dumps(body)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def caller(code: int = 0):
    calls: list[list[str]] = []

    def call(argv):
        calls.append(argv)
        return code

    call.calls = calls  # type: ignore[attr-defined]
    return call


class OpenDocTests(unittest.TestCase):
    def test_orca_tab_wins_inside_an_orca_terminal(self):
        run = runner(0, {"ok": True, "result": {"browserPageId": "page_1"}})
        call = caller()
        result = open_doc.open_doc(URI, ["open", "-a", "Google Chrome", URI], env=ORCA_ENV, run=run, call=call)
        self.assertEqual(result, {"opened": True, "via": "orca", "pageId": "page_1"})
        self.assertEqual(run.calls[0][:3], ["/bin/orca", "tab", "create"])
        self.assertIn("--worktree", run.calls[0])
        self.assertEqual(run.calls[0][run.calls[0].index("--worktree") + 1], "id:repo::/wt")
        self.assertEqual(run.calls[0][run.calls[0].index("--url") + 1], URI)
        self.assertEqual(call.calls, [], "the fallback browser is not touched when Orca opened the tab")

    def test_outside_orca_the_fallback_runs_and_orca_is_never_called(self):
        run = runner(0, {"result": {"browserPageId": "page_1"}})
        call = caller()
        result = open_doc.open_doc(URI, ["open", "-a", "Google Chrome", URI], env={"PATH": ""}, run=run, call=call)
        self.assertEqual(result["via"], "fallback")
        self.assertEqual(run.calls, [])
        self.assertEqual(call.calls, [["open", "-a", "Google Chrome", URI]])

    def test_orca_failure_degrades_to_the_fallback(self):
        for code, body in ((1, {"ok": False, "error": "runtime not running"}), (0, {"result": {}})):
            run = runner(code, body)
            call = caller()
            result = open_doc.open_doc(URI, ["open", URI], env=ORCA_ENV, run=run, call=call)
            self.assertEqual(result["via"], "fallback")
            self.assertEqual(call.calls, [["open", URI]])

    def test_operator_preference(self):
        run = runner(0, {"result": {"browserPageId": "page_1"}})
        call = caller()
        result = open_doc.open_doc(URI, ["open", URI], env={**ORCA_ENV, "WEB2HTML_BROWSER": "default"}, run=run, call=call)
        self.assertEqual((result["via"], run.calls, call.calls), ("fallback", [], [["open", URI]]))
        run = runner(1, {})
        call = caller()
        result = open_doc.open_doc(URI, ["open", URI], env={**ORCA_ENV, "WEB2HTML_BROWSER": "orca"}, run=run, call=call)
        self.assertEqual((result["opened"], result["via"], call.calls), (False, "none", []))

    def test_fallback_failure_is_reported_not_raised(self):
        result = open_doc.open_doc(URI, ["open", URI], env={"PATH": ""}, run=runner(1, {}), call=caller(3))
        self.assertEqual((result["opened"], result["via"]), (False, "none"))
        self.assertIn("exit 3", result["error"])

    def test_open_docs_gives_each_uri_an_orca_tab_or_one_fallback_call(self):
        uris = [URI, URI.replace("pipeline", "index-polish"), URI.replace("pipeline", "polish-report")]
        run = runner(0, {"result": {"browserPageId": "p"}})
        call = caller()
        results = open_doc.open_docs(uris, ["open", "-a", "Google Chrome", *uris], env=ORCA_ENV, run=run, call=call)
        self.assertEqual([r["via"] for r in results], ["orca"] * 3)
        self.assertEqual(len(run.calls), 3)
        self.assertEqual(call.calls, [])
        run = runner(1, {})
        call = caller()
        results = open_doc.open_docs(uris, ["open", "-a", "Google Chrome", *uris], env=ORCA_ENV, run=run, call=call)
        self.assertEqual([r["via"] for r in results], ["fallback"] * 3)
        self.assertEqual(call.calls, [["open", "-a", "Google Chrome", *uris]], "Chrome takes every URI in one call")

    def test_describe(self):
        self.assertEqual(open_doc.describe({"via": "orca"}), "Orca browser")
        self.assertEqual(open_doc.describe({"via": "fallback"}), "default browser")
        self.assertIn("not opened", open_doc.describe({"via": "none", "error": "x"}))


if __name__ == "__main__":
    unittest.main()
