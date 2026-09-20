#!/usr/bin/env python3
"""Render qa/polish-report.html from C/3 receipts + 3.2 companions (2.20.1).

  python3 render-polish-report.py .

C/3 ids are sub-pass ids, not board steps. C/3.1 impeccable and C/3.2
design-taste are board 3.1. C/3.3 emil is board 3.2, and the hover /
drawer / FAQ / dropdown rows surface on that card. The 3.2 companions
(web-design-guidelines, find-animation-opportunities, apple-design) get
one card each from qa/<skill>.md. Semantics is board 3.3 with its own
card. Pitfall #215.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _hint(step: str, status: str = "active", root=None) -> None:
    try:
        import importlib.util
        p = Path(__file__).resolve().parent / "pipeline-progress.py"
        spec = importlib.util.spec_from_file_location("pipeline_progress", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if root is not None:
            mod.hint(step, status, root)
        else:
            mod.hint(step, status)
    except Exception:
        pass


# (C/3 id, skill, receipt, title, spine label, board step)
REQUIRED = [
    (
        "3.1",
        "impeccable",
        "c3-3.1-impeccable.json",
        "Compare and fix",
        "Taste + contrast",
        "3.1",
    ),
    (
        "3.2",
        "design-taste-frontend",
        "c3-3.2-design-taste-frontend.json",
        "Taste on existing tokens",
        "Taste",
        "3.1",
    ),
    (
        "3.3",
        "emil-design-eng",
        "c3-3.3-emil-design-eng.json",
        "Hover, drawer, FAQ, dropdowns, GSAP",
        "Hover + GSAP",
        "3.2",
    ),
]

# 3.2 companions: (skill, markdown receipt, title). One card each (Pitfall #215).
COMPANIONS = [
    ("web-design-guidelines", "qa/web-design-guidelines.md", "Interface guidelines a11y"),
    (
        "find-animation-opportunities",
        "qa/find-animation-opportunities.md",
        "Motion opportunities (read-only list)",
    ),
    ("apple-design", "qa/apple-design.md", "Motion principles"),
]

CSS = """
  :root {
    color-scheme: dark;
    --bg: #0b0d0a;
    --panel: #12150f;
    --ink: #f4f7ed;
    --text: #c7cdbb;
    --muted: #858d78;
    --line: #30372a;
    --line-strong: #4a5340;
    --accent: #c7ff52;
    --human: #ffd166;
    --sans: "Geist Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    --display: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, sans-serif;
    --mono: "Geist Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; min-height: 100%; background: var(--bg); }
  body { color: var(--text); font: 15px/1.5 var(--sans); }
  a { color: inherit; }
  code { color: var(--ink); font-family: var(--mono); font-size: 0.88em; }
  :focus-visible { outline: 1px solid var(--accent); outline-offset: 3px; }
  ::selection { background: var(--accent); color: var(--bg); }
  .page { width: min(920px, 100%); margin: auto; padding: 32px 20px 80px; }
  .mast { display: flex; justify-content: space-between; gap: 16px; margin: 0 0 48px; color: var(--muted); font: 700 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .12em; }
  .mast strong, .mast-tag { color: var(--accent); }
  h1, h2, h3, h4 { font-family: var(--display); }
  h1 { margin: 0; color: var(--ink); font-size: clamp(2.1rem, 6vw, 3.6rem); font-weight: 500; line-height: 1; letter-spacing: -.035em; }
  .lead { width: 100%; max-width: 52ch; margin: 20px 0 36px; color: var(--text); font-size: 1.08rem; }
  .review-nav { display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 0 0 36px; color: var(--muted); font: 700 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .08em; }
  .review-nav a { color: var(--accent); text-decoration: none; }
  .review-nav a:hover { text-decoration: underline; }
  .eyebrow { margin: 0 0 12px; color: var(--accent); font: 700 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .1em; }
  h2 { margin: 0 0 18px; color: var(--ink); font-size: 1.35rem; font-weight: 500; letter-spacing: -.02em; }
  .spine { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0 0 48px; padding: 0; list-style: none; }
  .spine li { position: relative; padding: 13px 42px 13px 12px; border: 1px solid var(--line); background: var(--panel); }
  .spine li + li { border-left: 0; }
  .spine li:not(:last-child)::after { content: "→"; position: absolute; right: 10px; top: 50%; display: grid; width: 24px; height: 24px; place-items: center; color: var(--accent); font-weight: 800; transform: translateY(-50%); }
  .spine strong { display: block; color: var(--ink); font-size: .86rem; }
  .spine span { color: var(--muted); font: 11px/1.5 var(--mono); }
  .spine li[data-status="done"] { z-index: 1; border-color: var(--accent); background: #1d2514; }
  .spine li[data-status="done"] strong { color: var(--accent); }
  .spine li[data-status="done"]:not(:last-child)::after { color: var(--bg); background: var(--accent); }
  .passes { position: relative; margin-top: 8px; }
  .pass { position: relative; display: grid; grid-template-columns: 108px minmax(0, 1fr); padding: 0 0 48px; }
  .pass::before { content: ""; position: absolute; top: 0; bottom: 0; left: 26.5px; width: 1px; background: var(--line); }
  .pass[data-status="done"]::before { background: var(--accent); }
  .pass:first-child::before { top: 27px; }
  .pass:last-child::before { bottom: calc(100% - 27px); }
  .pass-key { position: sticky; top: 20px; align-self: start; z-index: 1; display: grid; width: 54px; height: 54px; place-items: center; border: 1px solid var(--line); background: var(--bg); color: var(--muted); font: 800 11px/1 var(--mono); letter-spacing: .04em; }
  .pass[data-status="done"] .pass-key { border-color: var(--accent); color: var(--accent); }
  .pass[data-status="pending"] { opacity: .42; }
  .pass-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .pass-head h3 { margin: 0; color: var(--ink); font-size: clamp(1.1rem, 2vw, 1.4rem); font-weight: 500; line-height: 1.25; letter-spacing: -.02em; text-wrap: balance; }
  .skill { margin: 8px 0 0; color: var(--muted); font: 700 11px/1 var(--mono); letter-spacing: .06em; }
  .pass-status { display: inline-flex; align-items: center; gap: 7px; flex: 0 0 auto; padding: 7px 9px 6px; border: 1px solid var(--line); color: var(--muted); font: 800 9px/1 var(--mono); letter-spacing: .09em; white-space: nowrap; }
  .pass[data-status="done"] .pass-status { border-color: var(--accent); color: var(--accent); }
  .pass[data-status="done"] .pass-status::before { content: ""; width: 9px; height: 5px; flex: 0 0 auto; border-left: 1.7px solid currentColor; border-bottom: 1.7px solid currentColor; transform: translateY(-1px) rotate(-45deg); }
  .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; margin: 22px 0 0; padding: 0; list-style: none; }
  .stats li { padding: 12px; border: 1px solid var(--line); background: var(--panel); }
  .stats li + li { border-left: 0; }
  .stats strong { display: block; color: var(--ink); font: 700 1.05rem/1 var(--display); }
  .stats span { color: var(--muted); font: 11px/1.5 var(--mono); }
  .meta { margin: 12px 0 0; color: var(--muted); font-size: .82rem; }
  .block { margin-top: 26px; }
  .block h4 { display: flex; align-items: center; gap: 9px; margin: 0 0 10px; color: var(--ink); font-size: .95rem; font-weight: 500; }
  .count { padding: 2px 6px 1px; border: 1px solid var(--line); color: var(--muted); font: 800 9px/1.2 var(--mono); letter-spacing: .06em; }
  .fx-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
  .fx { padding: 12px 14px; border: 1px solid var(--line); background: var(--panel); }
  .fx-tag { display: inline-block; margin: 0 0 6px; padding: 3px 7px 2px; border: 1px solid var(--line-strong); color: var(--accent); font: 800 9px/1 var(--mono); letter-spacing: .07em; text-transform: uppercase; }
  .fx-what { margin: 0; color: var(--ink); font-size: .86rem; font-weight: 500; line-height: 1.45; }
  .fx-fix { margin: 5px 0 0; color: var(--text); font-size: .8rem; line-height: 1.5; }
  .fx-fix::before { content: "→ "; color: var(--accent); }
  .fx-fix.is-same::before { content: "· "; color: var(--muted); }
  .sk-list { margin: 0; padding: 0; list-style: none; border: 1px solid var(--line); background: var(--panel); }
  .sk { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; padding: 10px 14px; border-bottom: 1px solid var(--line); }
  .sk:last-child { border-bottom: 0; }
  .sk-what { color: var(--ink); font-size: .82rem; font-weight: 500; line-height: 1.45; }
  .sk-rule { align-self: start; padding: 3px 7px 2px; border: 1px solid var(--line); color: var(--muted); font: 800 9px/1 var(--mono); letter-spacing: .07em; text-transform: uppercase; white-space: nowrap; }
  .sk-why { grid-column: 1 / -1; margin: 0; color: var(--muted); font-size: .78rem; line-height: 1.5; }
  .empty { margin: 0; padding: 10px 12px; border: 1px solid var(--line); color: var(--muted); font-size: .8rem; }
  details.files { border: 1px solid var(--line); background: var(--panel); }
  details.files summary { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 10px 14px; cursor: pointer; list-style: none; color: var(--ink); font: 700 11px/1.4 var(--mono); letter-spacing: .05em; text-transform: uppercase; }
  details.files summary::-webkit-details-marker { display: none; }
  details.files summary::after { content: "+"; margin-left: auto; color: var(--accent); font: 700 13px/1 var(--mono); }
  details.files[open] summary::after { content: "−"; }
  details.files summary:hover { color: var(--accent); }
  .chips { display: inline-flex; gap: 8px; margin-right: 8px; }
  .chips b { font: 800 10px/1 var(--mono); }
  .chip-add { color: #8ef07a; }
  .chip-del { color: #ff8a7a; }
  .files-body { border-top: 1px solid var(--line); }
  .frow { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 8px 14px; border-bottom: 1px solid var(--line); font-size: .78rem; }
  .frow:last-child { border-bottom: 0; }
  .fpath { overflow: hidden; color: var(--ink); font: 500 12px/1.45 var(--mono); text-overflow: ellipsis; white-space: nowrap; }
  .fkind { color: var(--muted); font: 700 9px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; }
  .fstat { font: 700 10px/1 var(--mono); white-space: nowrap; }
  .blurb { max-width: 60ch; margin: -6px 0 26px; color: var(--muted); font-size: .9rem; line-height: 1.55; }
  .skill a { color: var(--accent); text-decoration: none; }
  .skill a:hover { text-decoration: underline; }
  .rc-lines { margin: 0; padding: 0; list-style: none; border: 1px solid var(--line); background: var(--panel); }
  .rc-lines li { padding: 8px 14px; border-bottom: 1px solid var(--line); color: var(--text); font: 500 12px/1.5 var(--mono); overflow-wrap: anywhere; }
  .rc-lines li:last-child { border-bottom: 0; }
  .rc-lines li.more { color: var(--muted); }
  .facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; padding: 0; list-style: none; border: 1px solid var(--line); background: var(--panel); }
  .facts li { display: grid; gap: 3px; padding: 10px 12px; border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); font-size: .8rem; }
  .facts li:nth-child(2n) { border-right: 0; }
  .facts strong { color: var(--muted); font: 800 9px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; }
  .facts span { color: var(--ink); overflow-wrap: anywhere; }
  footer { margin-top: 12px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--muted); font: 400 12px/1.6 var(--mono); }
  @media (max-width: 720px) {
    .spine, .stats { grid-template-columns: 1fr; }
    .spine li + li, .stats li + li { border-left: 1px solid var(--line); border-top: 0; }
    .pass { grid-template-columns: 72px minmax(0, 1fr); }
    .pass::before { left: 21.5px; }
    .pass:first-child::before { top: 22px; }
    .pass:last-child::before { bottom: calc(100% - 22px); }
    .pass-key { width: 44px; height: 44px; }
    .pass-head { display: block; }
    .pass-status { display: inline-flex; margin-top: 12px; }
    .sk, .frow { grid-template-columns: minmax(0, 1fr); gap: 4px; }
    .facts { grid-template-columns: 1fr; }
    .facts li { border-right: 0; }
  }
"""


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_receipt(folder: Path, name: str) -> dict | None:
    path = folder / name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def merge_hover_css(root: Path, pass_id: str, data: dict | None) -> dict | None:
    """Surface 3.2 apply-hover-css.py on the Emil (C/3.3, board 3.2) card."""
    if pass_id != "3.3" or data is None:
        return data
    path = root / "qa" / "button-hover-css.json"
    if not path.is_file():
        return data
    try:
        hover = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return data
    if not isinstance(hover, dict):
        return data
    merged = dict(data)
    applied = list(merged.get("applied") or [])
    skipped = list(merged.get("skipped") or [])
    files = list(merged.get("files_changed") or [])
    for row in hover.get("applied") or []:
        if not isinstance(row, dict):
            continue
        name = row.get("className") or "button"
        applied.insert(
            0,
            {
                "file": "rebuild/css/hover.css",
                "change": f"{name}:hover",
                "why": f"1.3 source CSS · {row.get('label') or name}",
                "src": "apply-hover-css.py",
            },
        )
    for row in hover.get("skipped") or []:
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "")
        if "no source CSS" in reason or "1.3 found no" in reason:
            continue
        skipped.append(
            {
                "finding": row.get("label") or row.get("finding") or "button hover",
                "reason": reason,
                "skill_rule": "apply-hover-css.py",
            }
        )
    for rel in hover.get("files") or []:
        path_rel = str(rel)
        files.append(
            {
                "path": path_rel,
                "kind": "modified" if path_rel.endswith(".html") else "added",
                "after_sha": "",
            }
        )
    merged["applied"] = applied
    merged["skipped"] = skipped
    merged["files_changed"] = files
    return merged


def merge_nav_drawer(root: Path, pass_id: str, data: dict | None) -> dict | None:
    """Surface 3.2 author-nav-drawer.py on the Emil (C/3.3, board 3.2) card."""
    if pass_id != "3.3" or data is None:
        return data
    path = root / "qa" / "nav-drawer.json"
    if not path.is_file():
        return data
    try:
        drawer = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return data
    if not isinstance(drawer, dict):
        return data
    merged = dict(data)
    applied = list(merged.get("applied") or [])
    skipped = list(merged.get("skipped") or [])
    files = list(merged.get("files_changed") or [])
    seen = {
        str(row.get("finding") or "").casefold()
        for row in applied
        if isinstance(row, dict)
    }
    for row in drawer.get("applied") or []:
        if not isinstance(row, dict):
            continue
        finding = str(row.get("finding") or "burger open drawer")
        if finding.casefold() in seen:
            for existing in applied:
                if (
                    isinstance(existing, dict)
                    and str(existing.get("finding") or "").casefold() == finding.casefold()
                ):
                    existing.setdefault("file", row.get("file") or "rebuild/index-polish.html")
                    existing.setdefault("change", row.get("change") or finding)
                    existing.setdefault(
                        "why",
                        row.get("why") or row.get("fix") or "Painted burger opens the same links stacked.",
                    )
            continue
        applied.insert(
            0,
            {
                "file": row.get("file") or "rebuild/index-polish.html",
                "change": row.get("change") or finding,
                "why": row.get("why") or row.get("fix") or "Painted burger opens the same links stacked.",
                "finding": finding,
                "src": "author-nav-drawer.py",
            },
        )
        seen.add(finding.casefold())
    skipped = [
        row
        for row in skipped
        if not (
            isinstance(row, dict)
            and "burger" in str(row.get("finding") or "").casefold()
            and re.search(
                r"capture tool open-nav|inventing a sheet|new chrome",
                str(row.get("reason") or ""),
                re.I,
            )
        )
    ]
    for row in drawer.get("skipped") or []:
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "")
        if re.search(r"capture tool open-nav|inventing a sheet|new chrome", reason, re.I):
            continue
        if "no painted hamburger" in reason.casefold():
            continue
        skipped.append(
            {
                "finding": row.get("finding") or "burger open drawer",
                "reason": reason,
                "skill_rule": "author-nav-drawer.py",
            }
        )
    have_paths = {str(item.get("path") or "") for item in files if isinstance(item, dict)}
    for rel in drawer.get("files") or []:
        path_rel = str(rel)
        if path_rel in have_paths:
            continue
        files.append(
            {
                "path": path_rel,
                "kind": "modified" if path_rel.endswith(".html") else "added",
                "after_sha": "",
            }
        )
    merged["applied"] = applied
    merged["skipped"] = skipped
    merged["files_changed"] = files
    return merged


def merge_faq(root: Path, pass_id: str, data: dict | None) -> dict | None:
    """Surface 3.2 author-faq.py on the Emil (C/3.3, board 3.2) card."""
    if pass_id != "3.3" or data is None:
        return data
    path = root / "qa" / "faq.json"
    if not path.is_file():
        return data
    try:
        faq = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return data
    if not isinstance(faq, dict):
        return data
    merged = dict(data)
    applied = list(merged.get("applied") or [])
    skipped = list(merged.get("skipped") or [])
    files = list(merged.get("files_changed") or [])
    for row in faq.get("applied") or []:
        if not isinstance(row, dict):
            continue
        applied.insert(
            0,
            {
                "file": row.get("file") or "rebuild/index-polish.html",
                "change": row.get("change") or "FAQ accordion",
                "why": row.get("why") or row.get("fix") or "Painted FAQ rows open on click.",
                "finding": row.get("finding") or "FAQ accordion",
                "src": "author-faq.py",
            },
        )
    skipped = [
        row
        for row in skipped
        if not (
            isinstance(row, dict)
            and "faq" in str(row.get("finding") or "").casefold()
            and re.search(
                r"empty bodies|do not invent copy|capture tool|detect-only",
                str(row.get("reason") or ""),
                re.I,
            )
        )
    ]
    for row in faq.get("skipped") or []:
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "")
        if re.search(r"empty bodies|do not invent copy|capture tool|detect-only", reason, re.I):
            continue
        if "no painted faq" in reason.casefold():
            continue
        skipped.append(
            {
                "finding": row.get("finding") or "FAQ accordion",
                "reason": reason,
                "skill_rule": "author-faq.py",
            }
        )
    have_paths = {str(item.get("path") or "") for item in files if isinstance(item, dict)}
    for rel in faq.get("files") or []:
        path_rel = str(rel)
        if path_rel in have_paths:
            continue
        files.append(
            {
                "path": path_rel,
                "kind": "modified" if path_rel.endswith(".html") else "added",
                "after_sha": "",
            }
        )
    merged["applied"] = applied
    merged["skipped"] = skipped
    merged["files_changed"] = files
    return merged


def merge_nav_dropdown(root: Path, pass_id: str, data: dict | None) -> dict | None:
    """Surface 3.2 author-nav-dropdown.py on the Emil (C/3.3, board 3.2) card."""
    if pass_id != "3.3" or data is None:
        return data
    path = root / "qa" / "nav-dropdown.json"
    if not path.is_file():
        return data
    try:
        menu = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return data
    if not isinstance(menu, dict):
        return data
    merged = dict(data)
    applied = list(merged.get("applied") or [])
    skipped = list(merged.get("skipped") or [])
    files = list(merged.get("files_changed") or [])
    for row in menu.get("applied") or []:
        if not isinstance(row, dict):
            continue
        applied.insert(
            0,
            {
                "file": row.get("file") or "rebuild/index-polish.html",
                "change": row.get("change") or "nav dropdown",
                "why": row.get("why") or row.get("fix") or "Painted nav dropdowns open on hover/click.",
                "finding": row.get("finding") or "nav dropdown",
                "src": "author-nav-dropdown.py",
            },
        )
    skipped = [
        row
        for row in skipped
        if not (
            isinstance(row, dict)
            and "dropdown" in str(row.get("finding") or "").casefold()
            and re.search(
                r"capture tool|allow-dropdown|do not hunt",
                str(row.get("reason") or ""),
                re.I,
            )
        )
    ]
    for row in menu.get("skipped") or []:
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "")
        if re.search(r"capture tool|allow-dropdown|do not hunt", reason, re.I):
            continue
        if "no painted dropdown" in reason.casefold() or "no scrape submenu" in reason.casefold():
            continue
        skipped.append(
            {
                "finding": row.get("finding") or "nav dropdown",
                "reason": reason,
                "skill_rule": "author-nav-dropdown.py",
            }
        )
    have_paths = {str(item.get("path") or "") for item in files if isinstance(item, dict)}
    for rel in menu.get("files") or []:
        path_rel = str(rel)
        if path_rel in have_paths:
            continue
        files.append(
            {
                "path": path_rel,
                "kind": "modified" if path_rel.endswith(".html") else "added",
                "after_sha": "",
            }
        )
    merged["applied"] = applied
    merged["skipped"] = skipped
    merged["files_changed"] = files
    return merged


def fmt_when(value: str) -> str:
    if not value or value in {"—", "not run"}:
        return value
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y · %H:%M UTC")
    except ValueError:
        return value


def norm_change(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    out = []
    for part in re.split(r"(?<=[.!?])\s+", text):
        part = part.strip()
        if part:
            out.append(part[:1].upper() + part[1:])
    return " ".join(out)


def finding_of(item: dict) -> str:
    for key in ("finding", "label", "change"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return str(item.get("file") or "")


def tool_name(item: dict) -> str:
    return str(item.get("src") or item.get("skill_rule") or "").strip()


def collect_files(data: dict) -> list:
    files = []
    for item in data.get("files_changed") or []:
        if isinstance(item, dict):
            path = str(item.get("path") or "").strip()
            if path:
                files.append((path, str(item.get("kind") or "modified")))
        else:
            files.append((str(item), "modified"))
    for item in data.get("applied") or []:
        if isinstance(item, dict):
            path = str(item.get("file") or "").strip()
            if path and path not in {p for p, _ in files}:
                files.append((path, "modified"))
    seen = []
    out = []
    for path, kind in files:
        if path in seen:
            continue
        seen.append(path)
        out.append((path, kind))
    return out


def diff_stats(root: Path, paths: list) -> dict:
    stats = {}
    try:
        proc = subprocess.run(
            ["git", "diff", "--numstat", "--"] + [p for p, _ in paths],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return stats
    if proc.returncode != 0:
        return stats
    for line in proc.stdout.splitlines():
        cols = line.split("\t")
        if len(cols) == 3 and cols[0].isdigit() and cols[1].isdigit():
            stats[cols[2]] = (int(cols[0]), int(cols[1]))
    return stats


def applied_list(items: list) -> str:
    entries = []
    for item in items:
        if not isinstance(item, dict):
            continue
        what = norm_change(finding_of(item))
        fix = norm_change(item.get("why") or item.get("fix") or "")
        if not what and not fix:
            continue
        src = tool_name(item)
        tag = f'<span class="fx-tag">{esc(src)}</span>' if src else ""
        if what and fix and what.casefold() != fix.casefold():
            entries.append(
                f'<li class="fx">{tag}<p class="fx-what">{esc(what)}</p>'
                f'<p class="fx-fix">{esc(fix)}</p></li>'
            )
        else:
            text = what or fix
            entries.append(
                f'<li class="fx">{tag}<p class="fx-what">{esc(text)}</p></li>'
            )
    if not entries:
        return '<p class="empty">Nothing applied.</p>'
    return '<ul class="fx-list">' + "".join(entries) + "</ul>"


def skipped_list(items: list) -> str:
    entries = []
    for item in items:
        if not isinstance(item, dict):
            continue
        what = norm_change(item.get("finding") or item.get("label") or "")
        if not what:
            continue
        reason = norm_change(item.get("reason") or "")
        rule = tool_name(item)
        badge = f'<span class="sk-rule">{esc(rule)}</span>' if rule else ""
        why = f'<p class="sk-why">{esc(reason)}</p>' if reason else ""
        entries.append(
            f'<li class="sk"><span class="sk-what">{esc(what)}</span>{badge}{why}</li>'
        )
    if not entries:
        return ""
    return '<ul class="sk-list">' + "".join(entries) + "</ul>"


def files_details(root: Path, data: dict) -> tuple[int, str]:
    files = collect_files(data)
    if not files:
        return 0, ""
    stats = diff_stats(root, files)
    adds = sum(stats.get(p, (0, 0))[0] for p, _ in files)
    dels = sum(stats.get(p, (0, 0))[1] for p, _ in files)
    chips = (
        '<span class="chips">'
        f'<b class="chip-add">+{adds}</b><b class="chip-del">−{dels}</b>'
        "</span>"
        if stats
        else ""
    )
    rows_html = []
    for path, kind in files:
        if path in stats:
            a, d = stats[path]
            stat = f'<span class="fstat"><span class="chip-add">+{a}</span> <span class="chip-del">−{d}</span></span>'
        else:
            stat = '<span class="fstat">—</span>'
        rows_html.append(
            f'<div class="frow"><span class="fpath">{esc(path)}</span>'
            f'<span class="fkind">{esc(kind)}</span>{stat}</div>'
        )
    body = '<div class="files-body">' + "".join(rows_html) + "</div>"
    html_out = (
        f'<details class="files"><summary>{chips}'
        f"<span>Files touched · {len(files)}</span></summary>{body}</details>"
    )
    return len(files), html_out


def pass_state(status: str) -> tuple[str, str]:
    if status in {"applied", "applied_with_waivers", "no_op_fidelity"}:
        return "done", "COMPLETE"
    if status == "pending":
        return "pending", "WAITING"
    return "pending", (status or "WAITING").upper().replace("_", " ")


def pass_card(
    root: Path,
    pass_id: str,
    skill: str,
    title: str,
    board: str,
    data: dict | None,
) -> str:
    if data is None:
        status = "pending"
        ended = "not run"
        applied_n = skipped_n = files_n = "—"
        applied_html = '<p class="empty">Pass has not been recorded.</p>'
        skipped_html = files_html = ""
    else:
        status = data.get("status") or "unknown"
        ended = fmt_when(data.get("ended_at") or "—")
        applied_n = str(len(data.get("applied") or []))
        skipped_n = str(len(data.get("skipped") or []))
        files_count, files_html = files_details(root, data)
        files_n = str(files_count)
        applied_html = applied_list(data.get("applied") or [])
        skipped_html = skipped_list(data.get("skipped") or [])
    state, label = pass_state(status)
    skipped_block = (
        f'<div class="block"><h4>Skipped<span class="count">{esc(skipped_n)}</span></h4>'
        f"{skipped_html}</div>"
        if skipped_html
        else ""
    )
    files_block = f'<div class="block">{files_html}</div>' if files_html else ""
    return f"""
<article class="pass" data-status="{esc(state)}">
  <div class="pass-key">{esc(pass_id)}</div>
  <div>
    <div class="pass-head">
      <div>
        <h3>{esc(title)}</h3>
        <p class="skill">{esc(skill)} · board {esc(board)}</p>
      </div>
      <span class="pass-status">{esc(label)}</span>
    </div>
    <ul class="stats">
      <li><strong>{esc(applied_n)}</strong><span>applied</span></li>
      <li><strong>{esc(skipped_n)}</strong><span>skipped</span></li>
      <li><strong>{esc(files_n)}</strong><span>files</span></li>
    </ul>
    <p class="meta">{esc(ended)}</p>
    <div class="block">
      <h4>Identified &amp; applied<span class="count">{esc(applied_n)}</span></h4>
      {applied_html}
    </div>
    {skipped_block}
    {files_block}
  </div>
</article>
"""


def load_companion(root: Path, rel: str) -> dict | None:
    """Markdown receipt → row counts + first lines. None when missing or empty."""
    path = root / rel
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return None
    body = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]

    def count(pattern: str) -> int:
        return sum(1 for ln in body if re.search(pattern, ln, re.I))

    return {
        "applied": count(r"\bapplied\b"),
        "skipped": count(r"\bskipped\b"),
        "na": count(r"\bn[-/]a\b"),
        "lines": body[:24],
        "total": len(body),
    }


def companion_card(skill: str, title: str, rel: str, href: str, data: dict | None) -> str:
    if data is None:
        state, label = "pending", "NO RECEIPT"
        stats = ""
        body = (
            f'<p class="empty">Write {esc(rel)} with applied / skipped / n-a rows. '
            "A blocked finding is a skipped row, not a missing row. Pitfall #215.</p>"
        )
    else:
        state, label = "done", "RECEIPT"
        stats = (
            '<ul class="stats">'
            f'<li><strong>{data["applied"]}</strong><span>applied</span></li>'
            f'<li><strong>{data["skipped"]}</strong><span>skipped</span></li>'
            f'<li><strong>{data["na"]}</strong><span>n-a</span></li>'
            "</ul>"
        )
        rows = "".join(f"<li>{esc(ln[:220])}</li>" for ln in data["lines"])
        more = data["total"] - len(data["lines"])
        tail = f'<li class="more">… {more} more lines in the receipt</li>' if more > 0 else ""
        body = f'<ul class="rc-lines">{rows}{tail}</ul>'
    return f"""
<article class="pass" data-status="{esc(state)}">
  <div class="pass-key">3.2</div>
  <div>
    <div class="pass-head">
      <div>
        <h3>{esc(title)}</h3>
        <p class="skill">{esc(skill)} · board 3.2 · <a href="{esc(href)}">{esc(rel)}</a></p>
      </div>
      <span class="pass-status">{esc(label)}</span>
    </div>
    {stats}
    <div class="block">{body}</div>
  </div>
</article>
"""


def load_semantics(root: Path) -> dict | None:
    path = root / "qa" / "semantics-pass-qa.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def semantics_card(data: dict | None, href: str) -> str:
    if data is None:
        state, label = "pending", "WAITING"
        body = (
            '<p class="empty">Pass has not been recorded. semantics_pass.py '
            "--freeze-structure on index-polish.html writes qa/semantics-pass-qa.json.</p>"
        )
    else:
        failed = data.get("ok") is False
        state, label = ("pending", "FAILED") if failed else ("done", "COMPLETE")
        facts = []
        for key, value in data.items():
            if isinstance(value, (bool, int, float, str)):
                facts.append(
                    f"<li><strong>{esc(key)}</strong><span>{esc(str(value)[:160])}</span></li>"
                )
            elif isinstance(value, list):
                facts.append(f"<li><strong>{esc(key)}</strong><span>{len(value)} rows</span></li>")
            if len(facts) >= 8:
                break
        body = ('<ul class="facts">' + "".join(facts) + "</ul>") if facts else ""
        body += f'<p class="meta">Receipt <a href="{esc(href)}">qa/semantics-pass-qa.json</a></p>'
    return f"""
<article class="pass" data-status="{esc(state)}">
  <div class="pass-key">3.3</div>
  <div>
    <div class="pass-head">
      <div>
        <h3>Semantics + scrape-only SEO</h3>
        <p class="skill">semantics_pass.py · board 3.3</p>
      </div>
      <span class="pass-status">{esc(label)}</span>
    </div>
    <div class="block">{body}</div>
  </div>
</article>
"""


def spine_item(pass_id: str, short: str, data: dict | None) -> str:
    status = (data or {}).get("status") or "pending"
    state, _ = pass_state(status)
    return (
        f'<li data-status="{esc(state)}"><strong>{esc(pass_id)}</strong>'
        f"<span>{esc(short)}</span></li>"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    _hint("2.4", "active", args.root)
    root = args.root.resolve()
    folder = root / "qa" / "polish-passes"
    folder.mkdir(parents=True, exist_ok=True)
    cards = []
    spine = []
    done = 0
    for pass_id, skill, name, title, short, board in REQUIRED:
        data = merge_nav_dropdown(
            root,
            pass_id,
            merge_faq(
                root,
                pass_id,
                merge_nav_drawer(
                    root, pass_id, merge_hover_css(root, pass_id, load_receipt(folder, name))
                ),
            ),
        )
        if data is not None and pass_state(data.get("status") or "")[0] == "done":
            done += 1
        cards.append(pass_card(root, pass_id, skill, title, board, data))
        spine.append(spine_item(pass_id, short, data))
    companions = [
        (skill, title, rel, load_companion(root, rel)) for skill, rel, title in COMPANIONS
    ]
    companions_done = sum(1 for *_, data in companions if data is not None)
    semantics = load_semantics(root)
    generated = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")

    def page_for(lock_href: str, polish_href: str, qa_prefix: str) -> str:
        companion_cards = "".join(
            companion_card(skill, title, rel, qa_prefix + rel[len("qa/"):], data)
            for skill, title, rel, data in companions
        )
        semantics_html = semantics_card(semantics, qa_prefix + "semantics-pass-qa.json")
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="dark" />
<meta name="theme-color" content="#0b0d0a" />
<title>Web2Html — polish report</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=Geist+Mono:wght@100..900&family=IBM+Plex+Sans:wght@100..700&display=swap" rel="stylesheet" />
<style>
{CSS}
</style>
</head>
<body>
<main class="page">
  <p class="mast"><strong>Polish report</strong><span class="mast-tag">C/3 {done} / 3 · companions {companions_done} / 3</span></p>
  <h1>Polish report</h1>
  <p class="lead">What 3.1–3.3 applied or skipped. Compare the 2.4 lock with the QA polish file before you sign off.</p>
  <p class="review-nav"><a href="{lock_href}">2.4 ship</a><a href="{polish_href}">QA polish</a><span>generated {esc(generated)}</span></p>
  <p class="eyebrow">The run</p>
  <h2>3.1 → 3.3</h2>
  <ol class="spine" aria-label="Polish passes">{"".join(spine)}</ol>
  <div class="passes">
{"".join(cards)}
  </div>
  <p class="eyebrow">Board 3.2 companions</p>
  <h2>Guidelines, motion list, principles</h2>
  <p class="blurb">Emil applies; these three audit. Each leaves a markdown receipt in qa/. A finding stopped by a fidelity lock is a skipped or n-a row, never a missing row.</p>
  <div class="passes">
{companion_cards}
  </div>
  <p class="eyebrow">Board 3.3</p>
  <h2>Semantics</h2>
  <div class="passes">
{semantics_html}
  </div>
  <footer>qa/polish-passes · verify-polish-passes.py · rebuild/index.html · rebuild/index-polish.html</footer>
</main>
</body>
</html>
"""

    qa_out = root / "qa" / "polish-report.html"
    qa_out.parent.mkdir(parents=True, exist_ok=True)
    qa_out.write_text(
        page_for("../rebuild/index.html", "../rebuild/index-polish.html", ""),
        encoding="utf-8",
    )
    ship_dir = root / "rebuild"
    if ship_dir.is_dir():
        ship = ship_dir / "polish-report.html"
        ship.write_text(
            page_for("index.html", "index-polish.html", "../qa/"), encoding="utf-8"
        )
        polish = ship_dir / "index-polish.html"
        if polish.is_file():
            html = polish.read_text(encoding="utf-8")
            if "polish-report.html" not in html:
                tag = '<link rel="polish-report" href="polish-report.html"/>'
                html = (
                    html.replace("</head>", f"  {tag}\n</head>", 1)
                    if "</head>" in html
                    else tag + "\n" + html
                )
                polish.write_text(html, encoding="utf-8")
        print(f"wrote {qa_out}")
        print(f"wrote {ship}")
    else:
        print(f"wrote {qa_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
