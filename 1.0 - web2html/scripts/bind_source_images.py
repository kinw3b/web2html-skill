#!/usr/bin/env python3
"""Copy source originals into the ship and refuse compressed or swapped rasters.

  python3 bind_source_images.py <project>
  python3 bind_source_images.py <project> --check

Run at 2.2 before marking the homepage done, and again at 5.1 / 5.2 before
marking those steps done. Photos must be byte-copies of the unscaled file in
source-site/assets/ (or the larger capture/source-html copy). Pitfall #243.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from original_images import ready, sync


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--check", action="store_true", help="Do not download; fail if the receipt is stale")
    parser.add_argument("--no-fetch", action="store_true", help="Use on-disk originals only")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.check:
        if ready(root):
            print("source-images: ok")
            return 0
        print(
            "FAIL: ship rasters are not byte-copies of the source originals. "
            "Run bind_source_images.py (no --check) and point every photo at "
            "source-site/assets/. Pitfall #243.",
            file=sys.stderr,
        )
        return 2
    payload = sync(root, fetch=not args.no_fetch)
    if payload["errors"]:
        for err in payload["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(f"source-images: ok ({len(payload['originals'])} originals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
