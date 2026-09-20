#!/usr/bin/env python3
"""Lint the web2html documentation surfaces against pipeline.json.

pipeline.json (in `1.0 - web2html/`) is the single source of truth for step
ids, tiers, reference wiring, and the orchestrator version. This script fails
when a hand-maintained doc surface drifts from it. Wire it into
scripts/test-all.sh so the documentation contract is a gate, not a checklist.

    python3 "1.0 - web2html/scripts/lint-docs.py"          # lint
    python3 "1.0 - web2html/scripts/lint-docs.py" --strict # warnings fail too

Implements O1/O2 of the web2html Pipeline Orchestration Review — September 2026.
Stdlib only; no third-party deps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # 1.0 - web2html/scripts
SKILL_DIR = SCRIPT_DIR.parent                          # 1.0 - web2html
ROOT = SKILL_DIR.parent                                # repo root
PIPELINE_JSON = SKILL_DIR / "pipeline.json"

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read(rel: str) -> str | None:
    """Read a repo-relative file; record an error and return None if absent."""
    path = ROOT / rel
    if not path.is_file():
        err(f"missing file referenced by pipeline.json: {rel}")
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def skill_frontmatter_version(rel: str) -> str | None:
    text = read(rel)
    if text is None:
        return None
    m = re.search(r"^version:\s*([0-9][0-9A-Za-z.\-]*)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def orchestrator_stamp(text: str) -> str | None:
    """The `Orchestrator version (web2html): **X**` stamp, or a SKILL frontmatter version."""
    m = re.search(r"Orchestrator version \(web2html\):\*\*\s*\*\*([0-9][0-9A-Za-z.\-]*)\*\*", text)
    if m:
        return m.group(1)
    m = re.search(r"^version:\s*([0-9][0-9A-Za-z.\-]*)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def expand_step_ids(cell: str) -> set[str]:
    """Extract step ids from a model-routing table cell, expanding A.x-A.y ranges."""
    ids = set(re.findall(r"\b(\d\.\d)\b", cell))
    for lo, hi in re.findall(r"(\d\.\d)\s*[–—-]\s*(\d\.\d)", cell):
        maj_lo, min_lo = lo.split(".")
        maj_hi, min_hi = hi.split(".")
        if maj_lo == maj_hi:
            for n in range(int(min_lo), int(min_hi) + 1):
                ids.add(f"{maj_lo}.{n}")
    return ids


def parse_routing_tiers(text: str) -> dict[str, str]:
    """Map every step id in model-routing.md's `## Per-step` table to its tier."""
    tiers: dict[str, str] = {}
    section = text.split("## Per-step", 1)
    if len(section) < 2:
        err("model-routing.md: no `## Per-step` section found")
        return tiers
    body = section[1].split("\n## ", 1)[0]
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3:
            continue
        step_cell, tier_cell = cols[0], cols[-1]
        tm = re.search(r"\bT([123])\b", tier_cell)
        if not tm:
            continue
        tier = "T" + tm.group(1)
        for sid in expand_step_ids(step_cell):
            tiers[sid] = tier
    return tiers


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    if not PIPELINE_JSON.is_file():
        print(f"lint-docs: pipeline.json not found at {PIPELINE_JSON}", file=sys.stderr)
        return 2
    pipeline = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))

    orch = pipeline["orchestratorVersion"]
    ref_dir = pipeline["referenceDir"]

    # 1. Orchestrator version stamped consistently across surfaces.
    for rel in pipeline["versionStampSurfaces"]:
        text = read(rel)
        if text is None:
            continue
        stamp = orchestrator_stamp(text)
        if stamp is None:
            err(f"{rel}: no orchestrator version stamp found")
        elif stamp != orch:
            err(f"{rel}: orchestrator version {stamp!r} != pipeline.json {orch!r}")

    # 2. Each package's declared SKILL version matches its SKILL.md frontmatter.
    for pkg in pipeline["packages"]:
        declared = pkg["declaredSkillVersion"]
        actual = skill_frontmatter_version(f"{pkg['path']}/SKILL.md")
        if actual is not None and actual != declared:
            err(f"{pkg['path']}/SKILL.md: version {actual!r} != pipeline.json declaredSkillVersion {declared!r}")

    # 3. Every step id appears in SKILL.md's step table.
    skill_text = read("1.0 - web2html/SKILL.md") or ""
    skill_ids = set(re.findall(r"\b(\d\.\d)\b", skill_text))
    for step in pipeline["steps"]:
        if step["id"] not in skill_ids:
            err(f"SKILL.md: step {step['id']} is in pipeline.json but not in the step table")

    # 4. Every step's tier matches model-routing.md.
    routing_text = read("1.0 - web2html/references/model-routing.md") or ""
    routing_tiers = parse_routing_tiers(routing_text)
    for step in pipeline["steps"]:
        sid, tier = step["id"], step["tier"]
        if sid not in routing_tiers:
            err(f"model-routing.md: step {sid} has no tier row")
        elif routing_tiers[sid] != tier:
            err(f"model-routing.md: step {sid} tier {routing_tiers[sid]} != pipeline.json {tier}")

    # 5. Every referenced references/*.md exists (no dangling links).
    referenced: set[str] = set()
    for step in pipeline["steps"]:
        for ref in step["references"]:
            referenced.add(ref)
            if not (ROOT / ref_dir / ref).is_file():
                err(f"step {step['id']}: reference {ref_dir}/{ref} does not exist")

    # 6. pitfalls.md integrity: no duplicate id; no cited-but-undefined id.
    pit_text = read("1.0 - web2html/references/pitfalls.md") or ""
    defined: dict[int, int] = {}   # id -> count
    for line in pit_text.splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|", line)
        if m:
            pid = int(m.group(1))
            defined[pid] = defined.get(pid, 0) + 1
    for pid, count in sorted(defined.items()):
        if count > 1:
            err(f"pitfalls.md: id #{pid} is defined {count} times (duplicate)")

    # Citations: any `#NNN` on a line that mentions "Pitfall". High precision
    # (skips hex colours, version strings like 2.8.121) and high recall for this corpus.
    doc_files = ["1.0 - web2html/SKILL.md", "AGENTS.md"]
    doc_files += [f"{ref_dir}/{p.name}" for p in sorted((ROOT / ref_dir).glob("*.md"))]
    cited: dict[int, str] = {}     # id -> first surface citing it
    for rel in doc_files:
        path = ROOT / rel
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "pitfall" not in line.lower():
                continue
            for m in re.findall(r"#(\d{1,3})\b", line):
                cited.setdefault(int(m), rel)
    # A dangling citation is doc debt, not a broken build: warn by default so the
    # gate can be green, and let --strict escalate it for a cleanup / nightly run.
    for pid, where in sorted(cited.items()):
        if pid not in defined:
            warn(f"{where}: cites Pitfall #{pid} which pitfalls.md does not define")

    # 7. (WARNING) reference files nothing links to. Build a corpus of every
    # doc's text keyed by filename so a file does not "link to itself".
    ref_files = sorted((ROOT / ref_dir).glob("*.md"))
    all_docs: dict[str, str] = {}
    for rel in pipeline.get("linkScanSurfaces", []):
        t = read(rel)
        if t:
            all_docs[rel] = t
    for p in ref_files:
        all_docs[f"{ref_dir}/{p.name}"] = p.read_text(encoding="utf-8", errors="replace")
    for p in ref_files:
        name = p.name
        linked = False
        for key, text in all_docs.items():
            if key.endswith("/" + name):
                continue  # a file linking to itself does not count
            if name in text:
                linked = True
                break
        if not linked:
            warn(f"{ref_dir}/{name}: no doc surface links to it (orphan reference — link or remove)")

    # Report.
    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")

    n_steps = len(pipeline["steps"])
    if errors or (args.strict and warnings):
        print(f"lint-docs: FAILED ({len(errors)} error(s), {len(warnings)} warning(s); {n_steps} steps checked)")
        return 1
    print(f"lint-docs: OK ({len(warnings)} warning(s); {n_steps} steps checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
