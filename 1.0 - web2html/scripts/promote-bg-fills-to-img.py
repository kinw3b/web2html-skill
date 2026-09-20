#!/usr/bin/env python3
"""Download Paper/Framer background fills and promote empty boxes to <img>.

  python3 promote-bg-fills-to-img.py rebuild/index.html \\
      --images-dir rebuild/images --images-href images --download

Must-have on every B/2b convert (Pitfall #47).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bg_fills import (
    collect_bg_urls,
    download_urls,
    hoist_imgs_out_of_decorative,
    promote_empty_bg_fills,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path, nargs="+")
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--images-href", default="images")
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args(argv)

    urls: list[str] = []
    for path in args.html:
        urls.extend(collect_bg_urls(path.read_text(encoding="utf-8")))
    if args.download:
        failed = download_urls(urls, args.images_dir)
        if failed:
            print("download failed:", *failed[:8], file=sys.stderr)

    for path in args.html:
        html = path.read_text(encoding="utf-8")
        html2, n = promote_empty_bg_fills(html, args.images_dir, args.images_href)
        html2 = hoist_imgs_out_of_decorative(html2)
        path.write_text(html2, encoding="utf-8")
        print(f"{path}: promoted {n} fills → <img> (hoisted decorative wraps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
