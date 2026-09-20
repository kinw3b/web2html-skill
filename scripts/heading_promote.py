#!/usr/bin/env python3
"""2.2.b visual titles → real h1–h6 (heading rank).

Paper frames are often unnamed, and `semantic-map.json` h1/h2/h3 stay empty
(Pitfall #77). Rank from type-scale, `text-wrap: pretty`, and section role.
Retag only: keep class + leftover style. If the new heading would lose
alignment (UA start), stamp text-align from the node or parent
(text-center / justify-center+full-width / inline). Do not invent copy,
a font, or px (Pitfall #94).

  python3 heading_promote.py rebuild/index.html -o rebuild/index.html \\
      --qa qa/heading-pass-qa.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from type_align import preserve_align_on_retag

SIZE_NAMES = ("xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl", "9xl", "10xl", "11xl", "12xl")
SIZE_RANK = {name: i for i, name in enumerate(SIZE_NAMES, start=1)}
SIZE_CLASS = re.compile(r"\btext-(xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|10xl|11xl|12xl)\b")
SIZE_VAR = re.compile(r"--text-(xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|10xl|11xl|12xl)\b")
BOLD_CLASS = re.compile(r"\bfont-(bold|extrabold)\b")
BOLD_WEIGHT = re.compile(r"font-weight:\s*(bold|700|800|900|var\(--font-weight-bold\))", re.I)
PRETTY = re.compile(r"text-wrap:\s*pretty", re.I)
STAT = re.compile(r"^(?:0?\d{1,2}|\d+x|[\d,]{1,3}(?:\.\d+)?%)$", re.I)
HEADING_NAME = re.compile(r"(?:^|[\s_-])heading(?:$|[\s_-])|heading$", re.I)
SENTENCE_END = re.compile(r"[.!?]$")

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
REWRITABLE = {"div", "p", "span"}
CANDIDATE_TAGS = REWRITABLE | HEADING_TAGS
INTERACTIVE = {"a", "button", "input", "textarea", "select"}
CHROME_PARENTS = {"nav", "header", "footer"}
TITLE_MAX = 80

# Hero/first-section rule (documented): only the largest unique title is a
# heading. Sibling text-2xl bold that is not pretty stays body (lead).
LEAD_RULE = (
    "first content section: only the largest unique title is a heading; "
    "sibling text-2xl bold that is not pretty / not named *-heading stays body"
)


@dataclass
class Candidate:
    el: object
    text: str
    size: int
    pretty: bool
    named: bool
    bold: bool
    section: object | None
    doc_order: int
    assigned: str | None = None


def _classes(el) -> str:
    cls = el.get("class")
    if not cls:
        return ""
    if isinstance(cls, list):
        return " ".join(cls)
    return str(cls)


def _style(el) -> str:
    return el.get("style") or ""


def _blob(el) -> str:
    return f"{_classes(el)} {_style(el)}"


def size_rank(el) -> int:
    blob = _blob(el)
    best = 0
    for m in SIZE_CLASS.finditer(_classes(el)):
        best = max(best, SIZE_RANK.get(m.group(1), 0))
    for m in SIZE_VAR.finditer(blob):
        best = max(best, SIZE_RANK.get(m.group(1), 0))
    return best


def has_pretty(el) -> bool:
    return bool(PRETTY.search(_style(el)))


def is_bold(el) -> bool:
    return bool(BOLD_CLASS.search(_classes(el)) or BOLD_WEIGHT.search(_style(el)))


def layer_name(el) -> str:
    return (
        el.get("data-name")
        or el.get("layer-name")
        or el.get("data-paper-name")
        or ""
    )


def is_named_heading(el) -> bool:
    return bool(HEADING_NAME.search(layer_name(el)))


def is_stat(text: str) -> bool:
    t = text.strip()
    if STAT.match(t):
        return True
    # "01" / "4x" / "99.7%" already covered; reject bare numeric codes
    return False


def is_text_leaf(el) -> bool:
    if getattr(el, "name", None) not in CANDIDATE_TAGS:
        return False
    for child in el.find_all(True):
        own = "".join(s for s in child.contents if isinstance(s, str)).strip()
        if own:
            return False
    return bool(el.get_text(" ", strip=True))


def in_interactive(el) -> bool:
    if el.name in INTERACTIVE:
        return True
    return el.find_parent(list(INTERACTIVE)) is not None


def in_chrome(el) -> bool:
    return el.find_parent(list(CHROME_PARENTS)) is not None


def is_decorative(el) -> bool:
    if el.get("data-decorative") in {"true", "1", True}:
        return True
    return el.find_parent(attrs={"data-decorative": True}) is not None


def is_footer_label(el, text: str) -> bool:
    """Column labels: footer descendants, or bold short with no xl+/pretty."""
    if el.find_parent("footer") is not None:
        return True
    if has_pretty(el) or size_rank(el) >= 1:
        return False
    if is_bold(el) and len(text) <= 40:
        return True
    return False


def is_visual_signal(el, text: str) -> bool:
    if is_named_heading(el):
        return True
    if has_pretty(el):
        return True
    if size_rank(el) >= 1:
        return True
    if is_bold(el) and 0 < len(text) <= TITLE_MAX and el.find_parent("section"):
        return True
    return False


def content_sections(soup) -> list:
    main = soup.find("main")
    root = main if main is not None else soup
    out = []
    for el in root.find_all("section"):
        if el.find_parent("section") is not None:
            continue
        out.append(el)
    return out


def nearest_section(el, sections: list):
    parent = el.find_parent("section")
    if parent is not None:
        return parent
    return sections[0] if sections else None


def is_wordmark(el, text: str, section_max: int) -> bool:
    """Single-token brand/logo under a larger pretty/5xl section title."""
    if has_pretty(el) or is_named_heading(el):
        return False
    if size_rank(el) >= 5:
        return False
    if len(text.split()) != 1:
        return False
    if re.search(r"[.!?:]", text):
        return False
    if section_max >= 5 and size_rank(el) < section_max and size_rank(el) <= 3:
        return True
    return False


def is_first_section_lead(el, section_max: int) -> bool:
    """See LEAD_RULE. Not first/largest and not pretty → body lead."""
    if has_pretty(el) or is_named_heading(el):
        return False
    if size_rank(el) >= section_max and size_rank(el) >= 5:
        return False
    return True


def _soup(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def collect_raw(soup, sections: list) -> list[Candidate]:
    raw: list[Candidate] = []
    order = 0
    for el in soup.find_all(list(CANDIDATE_TAGS)):
        if not is_text_leaf(el):
            continue
        text = el.get_text(" ", strip=True)
        if not text or len(text) > TITLE_MAX:
            continue
        named = is_named_heading(el)
        if in_interactive(el) or in_chrome(el) or is_decorative(el):
            continue
        if not is_visual_signal(el, text):
            continue
        if not named:
            if is_stat(text) or is_footer_label(el, text):
                continue
        order += 1
        raw.append(
            Candidate(
                el=el,
                text=text,
                size=size_rank(el),
                pretty=has_pretty(el),
                named=named,
                bold=is_bold(el),
                section=nearest_section(el, sections),
                doc_order=order,
            )
        )
    return raw


def accept_candidates(raw: list[Candidate], sections: list) -> list[Candidate]:
    by_sec: dict[int, list[Candidate]] = {}
    for c in raw:
        by_sec.setdefault(id(c.section), []).append(c)
    first_id = id(sections[0]) if sections else None
    accepted: list[Candidate] = []
    for c in raw:
        group = by_sec.get(id(c.section), [])
        section_max = max((x.size for x in group), default=0)
        if first_id is not None and id(c.section) == first_id:
            if is_first_section_lead(c.el, section_max):
                continue
        elif is_wordmark(c.el, c.text, section_max):
            continue
        accepted.append(c)
    return accepted


def assign_ranks(accepted: list[Candidate], sections: list) -> list[Candidate]:
    by_sec: dict[int, list[Candidate]] = {}
    for c in accepted:
        by_sec.setdefault(id(c.section), []).append(c)
    first = True
    for sec in sections or [None]:
        group = by_sec.get(id(sec), [])
        if not group:
            if first and sec is (sections[0] if sections else None):
                first = False
            continue
        group_sorted = sorted(
            group, key=lambda c: (-c.size, -int(c.pretty), c.doc_order)
        )
        if first:
            group_sorted[0].assigned = "h1"
            for c in group_sorted[1:]:
                if c.named:
                    c.assigned = "h2"
            first = False
            continue
        h2 = None
        for c in group_sorted:
            if c.pretty or c.size >= 5 or c.named:
                h2 = c
                break
        if h2 is None:
            h2 = group_sorted[0]
        h2.assigned = "h2"
        for c in group:
            if c is h2:
                continue
            c.assigned = "h3"
    # Candidates whose section was not in `sections` (shouldn't happen)
    for c in accepted:
        if c.assigned is None:
            c.assigned = "h2" if any(x.assigned == "h1" for x in accepted) else "h1"
    return accepted


def retag(el, tag: str) -> None:
    if el.name in INTERACTIVE:
        return
    # UA heading styles reset text-align to start. Stamp gold align from
    # the node or its text-column parent before the tag change (Pitfall #94).
    preserve_align_on_retag(el)
    el.name = tag
    if el.get("data-prop") == "description":
        el["data-prop"] = "title"
    elif not el.get("data-prop"):
        el["data-prop"] = "title"


def hierarchy_defects(ranks: list[dict]) -> list[str]:
    defects: list[str] = []
    h1s = [r for r in ranks if r["tag"] == "h1"]
    if len(h1s) == 0:
        defects.append("0 h1")
    elif len(h1s) > 1:
        defects.append(">1 h1")
    last = 0
    for r in ranks:
        n = int(r["tag"][1])
        if last and n > last + 1:
            defects.append("skipped levels")
            break
        last = n
    return defects


def section_title_defects(accepted: list[Candidate], sections: list) -> list[str]:
    defects: list[str] = []
    by_sec: dict[int, list[Candidate]] = {}
    for c in accepted:
        by_sec.setdefault(id(c.section), []).append(c)
    for sec in sections:
        group = by_sec.get(id(sec), [])
        if not group:
            continue
        primary = sorted(group, key=lambda c: (-c.size, -int(c.pretty), c.doc_order))[0]
        if primary.el.name not in HEADING_TAGS:
            defects.append(
                f"visual section title still {primary.el.name}: {primary.text[:80]}"
            )
    return defects


def ranks_from_dom(soup) -> list[dict]:
    ranks = []
    for el in soup.find_all(list(HEADING_TAGS)):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        ranks.append({"tag": el.name, "text": text})
    return ranks


def build_qa(accepted: list[Candidate], soup, sections: list) -> dict:
    missing = []
    for c in accepted:
        if c.el.name not in HEADING_TAGS:
            missing.append({"text": c.text, "tag": c.el.name})
    ranks = ranks_from_dom(soup)
    defects = hierarchy_defects(ranks) + section_title_defects(accepted, sections)
    # de-dupe while keeping order
    seen: set[str] = set()
    uniq = []
    for d in defects:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    accounted = len(accepted) - len(missing)
    ok = not missing and not uniq
    return {
        "ok": ok,
        "coverage": {
            "candidates": len(accepted),
            "accounted": accounted,
            "missing": missing,
        },
        "defects": uniq,
        "ranks": ranks,
        "leadRule": LEAD_RULE,
    }


def census_headings(html: str) -> dict:
    """Re-census ship HTML. Does not mutate."""
    soup = _soup(html)
    sections = content_sections(soup)
    raw = collect_raw(soup, sections)
    accepted = accept_candidates(raw, sections)
    return build_qa(accepted, soup, sections)


def promote_visual_headings(html: str) -> tuple[str, dict]:
    soup = _soup(html)
    sections = content_sections(soup)
    raw = collect_raw(soup, sections)
    accepted = accept_candidates(raw, sections)
    assign_ranks(accepted, sections)
    for c in accepted:
        if c.assigned and c.el.name in (REWRITABLE | HEADING_TAGS):
            retag(c.el, c.assigned)
    qa = build_qa(accepted, soup, sections)
    return str(soup), qa


def default_qa_path(ship: Path) -> Path | None:
    ship = ship.resolve()
    for parent in (ship.parent.parent, ship.parent):
        qa = parent / "qa"
        if qa.is_dir():
            return qa / "heading-pass-qa.json"
    return None


def write_qa(path: Path, qa: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--qa", type=Path, help="Write heading-pass-qa.json here")
    args = ap.parse_args(argv)
    if not args.input.is_file():
        print(f"FAIL: missing {args.input}", file=sys.stderr)
        return 1
    html = args.input.read_text(encoding="utf-8")
    out, qa = promote_visual_headings(html)
    dest = args.output or args.input
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")
    qa_path = args.qa or default_qa_path(dest)
    if qa_path is not None:
        write_qa(qa_path, qa)
        print(f"wrote {qa_path}")
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    cov = qa["coverage"]
    print(
        f"heading-pass: ok={qa['ok']} candidates={cov['candidates']} "
        f"accounted={cov['accounted']} missing={len(cov['missing'])} "
        f"defects={qa['defects']}"
    )
    if not qa["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
