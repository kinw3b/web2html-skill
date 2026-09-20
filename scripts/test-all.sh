#!/usr/bin/env bash
# Run every suite in this checkout, then the artifact check.
#
#   ./scripts/test-all.sh     # same as `npm test` and the .githooks/pre-push hook
#
# Suites: web2html (python unittest), url-to-paper (node --test), hover-reel
# (node --test), check-skill-artifacts.sh, then lint-docs.py (doc surfaces vs
# pipeline.json). Each node package needs one `npm i` before the first run.
# Exits 1 if any suite, the artifact check, or the doc lint fails.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

run() {
  local label="$1"
  shift
  echo "▶ $label"
  if "$@"; then
    echo "✓ $label"
  else
    echo "✗ $label"
    fail=1
  fi
  echo
}

run "web2html python tests"   python3 -m unittest discover -q -s "$ROOT/1.0 - web2html/scripts" -p 'test_*.py'
run "url-to-paper node tests" npm --prefix "$ROOT/1.2 url-to-paper" test --silent
run "hover-reel node tests"   npm --prefix "$ROOT/1.3 hover-reel" test --silent
run "skill artifacts"         "$ROOT/scripts/check-skill-artifacts.sh"
run "doc lint"                python3 "$ROOT/1.0 - web2html/scripts/lint-docs.py"

if [[ "$fail" -ne 0 ]]; then
  echo "test-all: FAILED"
  exit 1
fi
echo "test-all: OK"
