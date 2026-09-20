#!/usr/bin/env python3
"""5.6 — write the Phase 5 review note and open the built Astro site.

Opens the built home + first interior from astro/dist on file:// (never a
server). The human may also run `npm run preview`. Marking 5.6 done tidies
and keeps rebuild/ + astro/ + pipeline.html.

  python3 open-phase-5-review.py /path/to/project
  python3 open-phase-5-review.py /path/to/project --no-open
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from astro_build import dist_page_rel

TEMPLATE = """# Phase 5 human review — Astro site

Walk every route. Shared Header / Footer must match the 3.4 polish chrome.
Interior bodies must match their Paper desktop pages. Tokens stay the 2.1 set.
Hrefs should already connect the site (5.5).

Routes:

{pages}

Built pages open on file:// (relativized at 5.5). Preview server, if you want one
(you run this — the agent does not start a server):

```
cd astro
npm install
npm run preview
```

After sign-off, `mark --step 5.6 --status done`. That tidies the project and keeps
`rebuild/` + `astro/` + `pipeline.html`.
"""


def load_pages(root: Path) -> list[dict]:
    pages_path = root / "qa" / "phase-5-links.json"
    if not pages_path.is_file():
        pages_path = root / "qa" / "phase-5-pages.json"
    if not pages_path.is_file():
        return []
    try:
        payload = json.loads(pages_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("routes") or payload.get("pages") or []
    return [row for row in rows if isinstance(row, dict) and row.get("slug")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    pages = load_pages(root)
    slugs = ["index"] + [str(row["slug"]) for row in pages if row["slug"] != "index"]
    rows = []
    to_open: list[Path] = []
    for slug in slugs:
        rel = dist_page_rel(slug)
        path = root / rel
        route = "/" if slug == "index" else f"/{slug}/"
        astro = "astro/src/pages/index.astro" if slug == "index" else f"astro/src/pages/{slug}.astro"
        state = path.as_uri() if path.is_file() else "(not built — run wire-astro-routes.py / build-astro-dist.py)"
        rows.append(f"- `{route}` — {astro} — {state}")
        if path.is_file() and len(to_open) < 2:
            to_open.append(path)
    dest = root / "qa" / "phase-5-review.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(TEMPLATE.format(pages="\n".join(rows) or "- (none)"), encoding="utf-8")
    opened = []
    for path in to_open:
        uri = path.as_uri()
        opened.append(uri)
        if not args.no_open:
            subprocess.call(["open", "-a", "Google Chrome", uri])
    receipt = root / "qa" / "phase-5-review-opened.json"
    receipt.write_text(
        json.dumps(
            {
                "generatedFrom": "web2html/open-phase-5-review",
                "review": "qa/phase-5-review.md",
                "opened": opened,
                "openedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(dest)
    print("Review the Astro routes (built pages on file://), then mark 5.6 done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
