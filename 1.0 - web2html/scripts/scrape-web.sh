#!/usr/bin/env bash
# 1.1 light scrape: one supplied URL only.
#
# Capture (1.2) owns visual evidence: per-section clips and the Paper
# Screenshots board. This command keeps SSR HTML, images, and Latin fonts
# for later attribution. It never crawls extra routes, never downloads
# every unicode-range subset, and never writes rebuild HTML.
#
# 1.2 localize-html-images.mjs reuses source-site/assets and downloads any
# remaining live images. Font self-host into rebuild/fonts is a 2.1 job.

set -euo pipefail

URL="${1:?Usage: scrape-web.sh <url> [output_dir]}"
OUT="${2:-source-site}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

command -v curl >/dev/null || { echo "✗ curl missing"; exit 1; }
command -v python3 >/dev/null || { echo "✗ python3 missing"; exit 1; }

mkdir -p "$OUT/assets"
echo "→ 1.1 light scrape: $URL"
curl --fail --location --silent --show-error \
  -A "Mozilla/5.0 web2html-light-scrape/1.1" "$URL" -o "$OUT/index.html"
cp "$OUT/index.html" "$OUT/index.raw.html"

PROJECT="$(cd "$(dirname "$OUT")" && pwd)"
if [[ "$(basename "$OUT")" != "source-site" ]]; then
  PROJECT="$(pwd)"
fi

python3 "$SCRIPT_DIR/scrape_light.py" \
  --url "$URL" \
  --out "$OUT" \
  --project "$PROJECT"
