#!/usr/bin/env python3
"""5.6 — Phase 5 quality scorecard: one page that measures the Astro build.

Reads ONLY receipts and the built pages already on disk (no browser, no
network) and scores every route on the factors the 5.6 human checks:

  fidelity     5.3 desktop + 5.4 responsive clip compare ok, side-by-sides > 0
  compare loop qa/side-by-side/{slug}/report.json + an APPLIED
               `wave.py --phase compare --page {slug}` covering every band
               (the multi-agent self-validation loop actually ran)
  nav          qa/phase-5-nav.json: hidden nav items wired on that page
  links        built Header/Footer hrefs that reach real routes; dead `#…`
               chrome links; interior routes no chrome link reaches
  components   share of <main> top-level blocks that are Astro components
               ([data-astro-component]) vs markup pasted inline
  semantics    one <h1>, <main>, <header>, <footer>, <nav>

Writes qa/phase-5-scorecard.json + qa/phase-5-scorecard.md. Never a gate by
itself — open-phase-5-review.py runs it and prints the summary so the human
can judge 5.6 on numbers, not vibes (Pitfall #248).

  python3 phase_5_scorecard.py /path/to/project
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from astro_build import COMPONENT_ATTR, dist_page_rel  # noqa: E402

OUT_JSON = Path("qa/phase-5-scorecard.json")
OUT_MD = Path("qa/phase-5-scorecard.md")
A_HREF_RE = re.compile(r"""<a\b[^>]*\bhref=(['"])(.*?)\1[^>]*>(.*?)</a>""", re.I | re.S)
CHROME_RE = re.compile(r"<(header|footer)\b.*?</\1>", re.I | re.S)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _slugs(root: Path) -> list[str]:
    rows = _load(root / "qa" / "phase-4-pages.json").get("pages") or []
    out = ["home"]
    for row in rows:
        slug = str((row or {}).get("slug") or "").strip() if isinstance(row, dict) else ""
        if slug and slug not in {"home", "index"}:
            out.append(slug)
    return out


def _applied_bands(root: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in sorted((root / "qa" / "agent-runs").glob("*/compare/wave.json")):
        wave = _load(path)
        if not wave.get("appliedAt"):
            continue
        bands = out.setdefault(str(wave.get("page") or "home"), set())
        for task in wave.get("tasks") or []:
            if isinstance(task, dict) and task.get("band"):
                bands.add(str(task["band"]))
    return out


def _page_row(receipt: dict, slug: str) -> dict:
    for row in receipt.get("pages") or []:
        if isinstance(row, dict) and str(row.get("slug")) in {slug, "index" if slug == "home" else slug}:
            return row
    return {}


def _components(html: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    blocks = [el for el in (main.find_all(recursive=False) if main else []) if el.name not in {"script", "style"}]
    comp = [el for el in blocks if el.get(COMPONENT_ATTR) or el.find(attrs={COMPONENT_ATTR: True})]
    names = sorted({el.get(COMPONENT_ATTR) for el in soup.find_all(attrs={COMPONENT_ATTR: True})})
    return {
        "mainBlocks": len(blocks),
        "componentBlocks": len(comp),
        "inlineBlocks": len(blocks) - len(comp),
        "names": names,
        "share": round(len(comp) / len(blocks), 2) if blocks else None,
        "semantics": {
            "h1": len(soup.find_all("h1")),
            "main": len(soup.find_all("main")),
            "header": bool(soup.find("header")),
            "footer": bool(soup.find("footer")),
            "nav": bool(soup.find("nav")),
        },
    }


def _label(inner: str) -> str:
    text = re.sub(r"<[^>]+>", " ", inner or "")
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _links(html: str, page: Path, dist: Path, source_labels: dict[str, str]) -> dict:
    """dead = a chrome link still on `#…` whose label the SOURCE sends to an
    internal page (a link the build dropped). Source-true `#` links don't count."""
    chrome = " ".join(m.group(0) for m in CHROME_RE.finditer(html))
    live, dead, broken = 0, [], []
    for _q, href, inner in A_HREF_RE.findall(chrome):
        value = href.strip()
        if not value or value.startswith("#"):
            label = _label(inner)
            if label in source_labels:
                dead.append(label)
            continue
        if re.match(r"^(https?:|mailto:|tel:|//)", value, re.I):
            continue
        target = (page.parent / value.split("#", 1)[0].split("?", 1)[0])
        if target.is_dir():
            target = target / "index.html"
        if target.resolve().is_file() and dist.resolve() in target.resolve().parents:
            live += 1
        else:
            broken.append(value)
    return {"chromeLive": live, "chromeDead": len(dead), "deadLabels": sorted(set(dead)), "chromeBroken": broken[:8]}


def score(root: Path) -> dict:
    root = root.resolve()
    dist = root / "astro" / "dist"
    desktop = _load(root / "qa" / "phase-5-clip-compare.json")
    responsive = _load(root / "qa" / "phase-5-responsive.json")
    nav = _load(root / "qa" / "phase-5-nav.json")
    links_receipt = _load(root / "qa" / "phase-5-links.json")
    applied = _applied_bands(root)
    pages: list[dict] = []
    for slug in _slugs(root):
        rel = dist_page_rel(slug)
        page = root / rel
        row: dict = {"slug": slug, "dist": rel, "built": page.is_file()}
        if slug != "home":
            d, r = _page_row(desktop, slug), _page_row(responsive, slug)
            row["fidelity"] = {
                "desktopOk": d.get("ok") is True,
                "responsiveOk": r.get("ok") is True,
                "desktopSides": d.get("sides"),
                "responsiveSides": r.get("sides"),
            }
            report = _load(root / "qa" / "side-by-side" / slug / "report.json")
            stops = [s for s in report.get("stops") or [] if isinstance(s, dict)]
            bands = {str(s.get("id")) for s in stops if s.get("id")}
            diffs = [s["diffPct"] for s in stops if isinstance(s.get("diffPct"), (int, float))]
            row["compareLoop"] = {
                "bands": len(bands),
                "sides": sum(1 for s in stops if s.get("side")),
                "reviewedBands": len(bands & applied.get(slug, set())),
                "ran": bool(bands) and bands <= applied.get(slug, set()),
                "meanDiffPct": round(sum(diffs) / len(diffs), 2) if diffs else None,
            }
        nav_row = _page_row(nav, slug)
        row["nav"] = {
            "items": len(nav_row.get("items") or []),
            "broken": [f"{b.get('kind')} '{b.get('trigger')}' {b.get('state')}" for b in nav_row.get("broken") or []],
        }
        if page.is_file():
            html = page.read_text(encoding="utf-8", errors="replace")
            row.update(_components(html))
            row["links"] = _links(html, page, dist, links_receipt.get("sourceLabels") or {})
        pages.append(row)
    unreachable = (links_receipt.get("links") or {}).get("unreachable") or []
    interior = [p for p in pages if p["slug"] != "home"]

    def pct(n: int, d: int) -> int:
        return round(100 * n / d) if d else 0

    totals = {
        "pages": len(pages),
        "built": sum(1 for p in pages if p["built"]),
        "fidelityOk": pct(sum(1 for p in interior if p["fidelity"]["desktopOk"] and p["fidelity"]["responsiveOk"]), len(interior)),
        "compareLoopRan": pct(sum(1 for p in interior if p["compareLoop"]["ran"]), len(interior)),
        "navWired": pct(sum(1 for p in pages if not p["nav"]["broken"]), len(pages)),
        "chromeDeadLinks": sum((p.get("links") or {}).get("chromeDead", 0) for p in pages),
        "routesUnreachable": len(unreachable),
        "componentShare": pct(
            sum(p.get("componentBlocks", 0) for p in pages), sum(p.get("mainBlocks", 0) for p in pages)
        ),
        "oneH1": pct(sum(1 for p in pages if (p.get("semantics") or {}).get("h1") == 1), len(pages)),
    }
    receipt = {
        "generatedFrom": "web2html/phase-5-scorecard",
        "totals": totals,
        "unreachableRoutes": unreachable,
        "pages": pages,
        "updated": _now_iso(),
    }
    (root / OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    (root / OUT_JSON).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (root / OUT_MD).write_text(render_md(receipt), encoding="utf-8")
    return receipt


def render_md(receipt: dict) -> str:
    t = receipt["totals"]
    lines = [
        "# Phase 5 scorecard",
        "",
        f"| factor | score |",
        "|---|---|",
        f"| pages built | {t['built']}/{t['pages']} |",
        f"| clip fidelity ok (5.3 + 5.4) | {t['fidelityOk']}% |",
        f"| /compare self-validation loop ran | {t['compareLoopRan']}% |",
        f"| hidden nav wired | {t['navWired']}% |",
        f"| dead chrome links (source links them, build left `#`) | {t['chromeDeadLinks']} |",
        f"| routes no Header/Footer link reaches | {t['routesUnreachable']} |",
        f"| `<main>` blocks that are components | {t['componentShare']}% |",
        f"| pages with exactly one `<h1>` | {t['oneH1']}% |",
        "",
        "| page | built | fidelity | loop (reviewed/bands) | mean diff % | nav broken | dead links | components / inline | h1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in receipt["pages"]:
        fid = p.get("fidelity") or {}
        loop = p.get("compareLoop") or {}
        fid_s = "—" if p["slug"] == "home" else ("ok" if fid.get("desktopOk") and fid.get("responsiveOk") else "FAIL")
        loop_s = "—" if p["slug"] == "home" else f"{loop.get('reviewedBands', 0)}/{loop.get('bands', 0)}"
        lines.append(
            f"| `{p['slug']}` | {'yes' if p['built'] else 'NO'} | {fid_s} | {loop_s} | "
            f"{loop.get('meanDiffPct') if loop.get('meanDiffPct') is not None else '—'} | "
            f"{len(p['nav']['broken'])} | {(p.get('links') or {}).get('chromeDead', '—')} | "
            f"{p.get('componentBlocks', '—')} / {p.get('inlineBlocks', '—')} | "
            f"{(p.get('semantics') or {}).get('h1', '—')} |"
        )
    if receipt["unreachableRoutes"]:
        lines += ["", "Unreachable from the chrome: " + ", ".join(f"`{r}`" for r in receipt["unreachableRoutes"])]
    lines += [
        "",
        "Open any built page with `?qa-outlines=components` — Astro components are boxed purple and",
        "named; orange dashed blocks are markup pasted into the page instead of a component.",
        "`?qa-outlines=tags` shows the semantic tags. ⌥O / Alt+O cycles off → on → tags → components → mono.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    receipt = score(args.root)
    print(json.dumps(receipt["totals"], indent=2))
    print(f"scorecard → {OUT_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
