#!/usr/bin/env bash
# Install these skill packages into an agent's skills directory, as symlinks.
#
#   ./scripts/install-skills.sh                  # -> ~/.claude/skills
#   ./scripts/install-skills.sh ~/.hermes/skills # -> any other skills directory
#   SKILLS=~/somewhere ./scripts/install-skills.sh
#   DRY_RUN=1 ./scripts/install-skills.sh        # print, change nothing
#
# The checkout can live anywhere — nothing here depends on where you keep it.
# Symlinks (not copies) mean an edit in the checkout is live immediately.
#
# Mirror folders carry a stage prefix ("1.2 url-to-paper") so the pipeline order
# is visible when browsing. The INSTALLED name is always the plain skill name:
# that name is the identifier agents invoke, and a space or digit in it breaks
# discovery.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-${SKILLS:-$HOME/.claude/skills}}"
DEST="${DEST/#\~/$HOME}"
DRY_RUN="${DRY_RUN:-}"

[[ -n "$DRY_RUN" ]] && echo "DRY RUN — nothing will be written"
echo "repo:    $ROOT"
echo "install: $DEST"
echo

[[ -n "$DRY_RUN" ]] || mkdir -p "$DEST"

linked=0
skipped=0
for dir in "$ROOT"/*/; do
  base="$(basename "$dir")"
  # Parked trees are not installed. Move archive/ out of the repo to split later.
  [[ "$base" == "archive" ]] && continue
  [[ -f "$dir/SKILL.md" ]] || continue
  name="$(printf '%s' "$base" | sed -E 's/^[0-9]+(\.[0-9]+)* +(- +)?//')"
  target="$DEST/$name"

  # A real directory that is not our symlink belongs to something else.
  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "SKIP  $name — $target exists and is not a symlink"
    skipped=$((skipped + 1))
    continue
  fi

  prev=""
  if [[ -L "$target" ]]; then
    prev="$(readlink "$target")"
    [[ "$prev" == "$ROOT/$base" ]] && prev=""
  fi
  if [[ -z "$DRY_RUN" ]]; then
    ln -sfn "$ROOT/$base" "$target"
  fi
  if [[ -n "$prev" ]]; then
    echo "link  $name -> $base  (was -> $prev)"
  else
    echo "link  $name -> $base"
  fi
  linked=$((linked + 1))
done

# Invoke name is /web2html. Keep $SKILLS/website-to-html and
# $SKILLS/design-tokens as compat aliases.
alias_link() {
  local name="$1" base="$2"
  local target="$DEST/$name"
  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "SKIP  $name — $target exists and is not a symlink"
    skipped=$((skipped + 1))
    return
  fi
  if [[ -n "$DRY_RUN" ]]; then
    echo "alias $name -> $base"
  else
    ln -sfn "$ROOT/$base" "$target"
    echo "alias $name -> $base"
  fi
  linked=$((linked + 1))
}
if [[ -d "$ROOT/1.0 - web2html" ]]; then
  alias_link website-to-html "1.0 - web2html"
fi
if [[ -d "$ROOT/2.1 design-tokens" ]]; then
  alias_link design-tokens "2.1 design-tokens"
fi

echo
echo "$linked linked, $skipped skipped"

# Capture Tool native bridge (macOS) is OPT-IN: INSTALL_CAPTURE_HOST=1. The
# extension is a separate download (https://github.com/kinw3b/paper-bridge);
# without the bridge the side panel shows OFFLINE (web2html Pitfall #217).
CAPTURE_INSTALLER="$ROOT/1.3 hover-reel/capture-extension/install-native-host.command"
if [[ "$(uname -s)" == "Darwin" && -f "$CAPTURE_INSTALLER" && -n "${INSTALL_CAPTURE_HOST:-}" ]]; then
  echo
  if [[ -n "$DRY_RUN" ]]; then
    echo "bridge  would run: sh \"$CAPTURE_INSTALLER\" --quiet"
  elif sh "$CAPTURE_INSTALLER" --quiet; then
    echo "bridge  Paper Capture Tool native host installed"
  else
    echo "bridge  FAIL — Capture Tool will show OFFLINE. Fix node, then rerun:" >&2
    echo "        sh \"$CAPTURE_INSTALLER\" --quiet" >&2
  fi
fi

cat <<EOF

Commands inside these skills refer to \$SKILLS — the directory you just
installed into. Export it so the examples run as written:

  export SKILLS="$DEST"
EOF
