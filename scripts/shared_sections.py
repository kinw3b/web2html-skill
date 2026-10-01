#!/usr/bin/env python3
"""5.1 — plan shared sections across the whole sitemap BEFORE any page is authored.

Phase 5 used to lift only Header / Footer / buttons, so 5.2 workers re-authored
the same CTA, FAQ, testimonial, team, or gallery band on every interior page
(Pitfall #244). This pass reads every section the run already has on disk and
groups the ones that repeat across pages, by copy and image overlap — never by
section name, because names like `content-section` repeat for unrelated bands.

Section sources, per page:
  index            the 3.4 ship's <main> children (rebuild/index.html;
                   source-html/index.html on an adopted run)
  interior {slug}  capture/{slug}-desktop/NN-*.html (4.2 live capture), else
                   the top-level bands of rebuild/{slug}-raw.html (5.2 dump)

Each group with members on two or more pages becomes ONE component:
  origin "home"      the homepage already ships this band; 5.1
                     extract-astro-components.py lifts it from the signed
                     homepage and convert-astro-home.py renders it as a tag.
  origin "interior"  the band only repeats on interior pages; it is marked
                     buildFirst — the controller authors
                     astro/src/components/{Name}.astro BEFORE the 5.2 page
                     workers start, and they import it.

Member match is "identical" (same copy, render the component as-is) or
"variant" (same structure, some copy differs; extend the component with props
or a slot — never re-author the band). record-phase-5-pages.py enforces both.

  python3 shared_sections.py /path/to/project      # writes qa/phase-5-reuse.json
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

GENERATED_FROM = "web2html/phase-5-reuse"
OUT = Path("qa/phase-5-reuse.json")
CHROME_NAMES = frozenset({"header", "footer", "chrome", "navbar", "nav", "navigation"})
STRIP_RE = re.compile(r"<(style|script|svg)\b.*?</\1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[a-z0-9']+")
IMG_RE = re.compile(r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.I)
OPEN_TAG_RE = re.compile(r"<([a-zA-Z][\w:-]*)\b[^>]*>")
CAPTURE_FILE_RE = re.compile(r"^(\d{2})-(.+)\.html$")
SHINGLE = 3
# A pair joins a group only when BOTH hold: most of the smaller band's copy
# sits inside the larger (containment) and the two are mostly the same band
# (jaccard). Containment alone chains a short CTA onto every long page.
JOIN_CONTAINMENT = 0.7
JOIN_JACCARD = 0.5
IDENTICAL_JACCARD = 0.85
MIN_SIGNATURE = 12


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def pascal(raw: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", raw or "") if p and not p.isdigit()]
    return "".join(p[:1].upper() + p[1:].lower() for p in parts)


def balanced(src: str, start: int) -> str:
    """The element opening at `start`, closed at its matching end tag."""
    first = OPEN_TAG_RE.match(src, start)
    if not first:
        return ""
    tag = first.group(1)
    if first.group(0).endswith("/>"):
        return first.group(0)
    open_re = re.compile(rf"<{re.escape(tag)}\b[^>]*?(/?)>", re.I)
    close_re = re.compile(rf"</{re.escape(tag)}\s*>", re.I)
    depth, cursor = 1, first.end()
    while depth:
        nxt_close = close_re.search(src, cursor)
        if not nxt_close:
            return ""
        nxt_open = open_re.search(src, cursor)
        if nxt_open and nxt_open.start() < nxt_close.start():
            if not nxt_open.group(1):
                depth += 1
            cursor = nxt_open.end()
            continue
        depth -= 1
        cursor = nxt_close.end()
    return src[start:cursor]


def children(element: str) -> list[str]:
    """Direct child elements of `element`."""
    first = OPEN_TAG_RE.match(element)
    if not first:
        return []
    out: list[str] = []
    cursor = first.end()
    end = element.rfind("</")
    while cursor < end:
        match = OPEN_TAG_RE.search(element, cursor, end)
        if not match:
            break
        child = balanced(element, match.start())
        if not child:
            break
        out.append(child)
        cursor = match.start() + len(child)
    return out


def signature(markup: str) -> set[str]:
    """Copy shingles + image basenames: what makes a band the same band."""
    text = html_lib.unescape(TAG_RE.sub(" ", STRIP_RE.sub(" ", markup))).lower()
    words = WORD_RE.findall(text)
    sig = {" ".join(words[i : i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1))}
    for src in IMG_RE.findall(markup):
        name = Path(src.split("?", 1)[0]).name.lower()
        if name:
            sig.add(f"img:{name}")
    return sig


def _home_path(root: Path) -> Path:
    try:
        import run_config

        if run_config.adopt_mode(root):
            return root / "source-html" / "index.html"
    except Exception:  # noqa: BLE001
        pass
    return root / "rebuild" / "index.html"


def chrome_signatures(root: Path) -> list[set[str]]:
    """Copy of the ship's own <header> / <footer> — Paper dumps repeat it as a band."""
    home = _home_path(root)
    if not home.is_file():
        return []
    text = home.read_text(encoding="utf-8", errors="replace")
    sigs = []
    for tag in ("header", "footer"):
        match = re.search(rf"<{tag}\b[^>]*>", text, re.I)
        if match:
            sig = signature(balanced(text, match.start()))
            if len(sig) >= MIN_SIGNATURE:
                sigs.append(sig)
    return sigs


def is_chrome(sig: set[str], chrome: list[set[str]]) -> bool:
    return any(_scores(sig, c)[1] >= JOIN_CONTAINMENT for c in chrome)


def heading_name(markup: str) -> str:
    """First heading's words (else first text run) — names a Paper-dump band with no id."""
    match = re.search(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>", markup, re.I | re.S)
    text = match.group(1) if match else STRIP_RE.sub(" ", markup)
    words = [w for w in WORD_RE.findall(html_lib.unescape(TAG_RE.sub(" ", text)).lower()) if not w.isdigit()]
    return "-".join(words[:3])


def home_sections(root: Path) -> list[dict]:
    home = _home_path(root)
    if not home.is_file():
        return []
    text = home.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<main\b[^>]*>", text, re.I)
    if not match:
        return []
    main = balanced(text, match.start())
    rows = []
    for idx, child in enumerate(children(main), start=1):
        open_tag = OPEN_TAG_RE.match(child).group(0)  # type: ignore[union-attr]
        sid = ID_RE.search(open_tag)
        name = sid.group(1) if sid else f"section-{idx:02d}"
        rows.append({
            "page": "index",
            "section": name,
            "sectionId": sid.group(1) if sid else "",
            "order": idx,
            "source": str(home.relative_to(root)),
            "html": child,
        })
    return rows


def interior_slugs(root: Path) -> list[str]:
    path = root / "qa" / "phase-4-pages.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    slugs = []
    for row in payload.get("pages") or []:
        slug = str((row or {}).get("slug") or "").strip() if isinstance(row, dict) else ""
        if slug and slug not in {"home", "index"} and slug not in slugs:
            slugs.append(slug)
    return slugs


def interior_sections(root: Path, slug: str) -> tuple[list[dict], str]:
    """(sections, source kind) — live capture first, then the 5.2 Paper dump."""
    cap = root / "capture" / f"{slug}-desktop"
    rows: list[dict] = []
    if cap.is_dir():
        for path in sorted(cap.glob("[0-9][0-9]-*.html")):
            match = CAPTURE_FILE_RE.match(path.name)
            if not match or match.group(2).lower() in CHROME_NAMES:
                continue
            rows.append({
                "page": slug,
                "section": match.group(2),
                "order": int(match.group(1)),
                "source": str(path.relative_to(root)),
                "html": path.read_text(encoding="utf-8", errors="replace"),
            })
        if rows:
            return rows, "capture"
    raw = root / "rebuild" / f"{slug}-raw.html"
    if raw.is_file():
        text = raw.read_text(encoding="utf-8", errors="replace")
        body = re.search(r"<body\b[^>]*>", text, re.I)
        start = body.end() if body else 0
        first = OPEN_TAG_RE.search(text, start)
        frame = balanced(text, first.start()) if first else ""
        for idx, child in enumerate(children(frame), start=1):
            rows.append({
                "page": slug,
                "section": heading_name(child) or f"band-{idx:02d}",
                "order": idx,
                "source": str(raw.relative_to(root)),
                "html": child,
            })
        if rows:
            return rows, "paper-raw"
    return [], ""


def _scores(a: set[str], b: set[str]) -> tuple[float, float]:
    inter = len(a & b)
    if not inter:
        return 0.0, 0.0
    return inter / len(a | b), inter / min(len(a), len(b))


def plan(root: Path) -> dict:
    root = root.resolve()
    sections = home_sections(root)
    sources: dict[str, str] = {"index": "ship"} if sections else {}
    pending: list[str] = []
    for slug in interior_slugs(root):
        rows, kind = interior_sections(root, slug)
        if not rows:
            pending.append(slug)
            continue
        sources[slug] = kind
        sections.extend(rows)
    chrome = chrome_signatures(root)
    for row in sections:
        row["sig"] = signature(row["html"])
    usable = [
        row for row in sections
        if len(row["sig"]) >= MIN_SIGNATURE and not (row["page"] != "index" and is_chrome(row["sig"], chrome))
    ]

    parent = list(range(len(usable)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(usable):
        for j in range(i + 1, len(usable)):
            b = usable[j]
            if a["page"] == b["page"]:
                continue
            jac, con = _scores(a["sig"], b["sig"])
            if con >= JOIN_CONTAINMENT and jac >= JOIN_JACCARD:
                parent[find(i)] = find(j)

    buckets: dict[int, list[dict]] = {}
    for i, row in enumerate(usable):
        buckets.setdefault(find(i), []).append(row)

    groups: list[dict] = []
    used_names: set[str] = set()
    for members in buckets.values():
        pages = sorted({m["page"] for m in members}, key=lambda p: (p != "index", p))
        if len(pages) < 2:
            continue
        home_members = [m for m in members if m["page"] == "index"]
        if home_members:
            anchor = home_members[0]
        else:  # medoid: the band most like all the others
            anchor = max(members, key=lambda m: sum(_scores(m["sig"], o["sig"])[0] for o in members))
        votes: dict[str, int] = {}
        for m in members:
            key = m.get("sectionId") or m["section"]
            if not re.match(r"^(band|section)-\d+$", key):
                votes[key] = votes.get(key, 0) + 1
        label = anchor.get("sectionId") or anchor["section"]
        if votes and not home_members:
            label = max(votes, key=lambda k: (votes[k], k == label))
        base = pascal(label) or "Shared"
        if not base.endswith("Section"):
            base += "Section"
        name, n = base, 2
        while name in used_names or name in {"Header", "Footer"}:
            name, n = f"{base}{n}", n + 1
        used_names.add(name)
        rows = []
        for m in sorted(members, key=lambda m: (m["page"] != "index", m["page"], m["order"])):
            jac, con = _scores(anchor["sig"], m["sig"]) if m is not anchor else (1.0, 1.0)
            rows.append({
                "page": m["page"],
                "section": m["section"],
                "source": m["source"],
                "match": "identical" if jac >= IDENTICAL_JACCARD else "variant",
                "jaccard": round(jac, 3),
                "containment": round(con, 3),
            })
        origin = "home" if home_members else "interior"
        groups.append({
            "name": name,
            "file": f"src/components/{name}.astro",
            "import": f"../components/{name}.astro",
            "origin": origin,
            "buildFirst": origin == "interior",
            "anchor": {
                "page": anchor["page"],
                "section": anchor["section"],
                "sectionId": anchor.get("sectionId", ""),
                "source": anchor["source"],
            },
            "pages": pages,
            "interiorPages": [p for p in pages if p != "index"],
            "members": rows,
            "signature": sorted(anchor["sig"]),
        })
    groups.sort(key=lambda g: (-len(g["pages"]), g["name"]))
    by_page: dict[str, list[str]] = {}
    for group in groups:
        for page in group["interiorPages"]:
            by_page.setdefault(page, []).append(group["name"])
    return {
        "generatedFrom": GENERATED_FROM,
        "ok": True,
        "sources": sources,
        "pending": pending,
        "thresholds": {
            "joinContainment": JOIN_CONTAINMENT,
            "joinJaccard": JOIN_JACCARD,
            "identicalJaccard": IDENTICAL_JACCARD,
            "minSignature": MIN_SIGNATURE,
        },
        "sectionsScanned": len(sections),
        "groups": groups,
        "buildFirst": [g["name"] for g in groups if g["buildFirst"]],
        "fromHome": [g["name"] for g in groups if not g["buildFirst"]],
        "byPage": by_page,
        "updated": _now_iso(),
    }


def write(root: Path, payload: dict) -> Path:
    dest = root / OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def load(root: Path) -> dict | None:
    path = root / OUT
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def stale_pending(root: Path, payload: dict) -> list[str]:
    """Pages the plan could not see that now have a section source on disk."""
    return [slug for slug in payload.get("pending") or [] if interior_sections(root, slug)[0]]


def inline_copies(text: str, payload: dict, slug: str) -> list[str]:
    """Shared groups whose copy is pasted into this page instead of imported."""
    stripped = re.sub(r"<[A-Z][\w]*\b[^>]*/>", " ", text)
    page_sig = signature(stripped)
    hits = []
    for group in payload.get("groups") or []:
        if slug not in group.get("interiorPages", []):
            continue
        sig = set(group.get("signature") or [])
        if len(sig) < MIN_SIGNATURE:
            continue
        if len(sig & page_sig) / len(sig) >= JOIN_CONTAINMENT:
            hits.append(group["name"])
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not _home_path(root).is_file():
        print(f"FAIL: need {_home_path(root).relative_to(root)}", file=sys.stderr)
        return 2
    payload = plan(root)
    dest = write(root, payload)
    astro = root / "astro"
    missing = [g["name"] for g in payload["groups"] if astro.is_dir() and not (astro / g["file"]).is_file()]
    print(json.dumps({
        "ok": True,
        "receipt": str(dest.relative_to(root)),
        "fromHome": payload["fromHome"],
        "buildFirst": payload["buildFirst"],
        "pending": payload["pending"],
        "missingComponents": missing,
        "groups": [
            {"name": g["name"], "origin": g["origin"], "pages": len(g["pages"])}
            for g in payload["groups"]
        ],
    }, indent=2))
    if payload["pending"]:
        print(
            "NOTE: no section source yet for "
            + ", ".join(payload["pending"])
            + " — re-run after dump-interior-raw.mjs, before any 5.2 worker starts.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
