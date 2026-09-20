#!/usr/bin/env bash
# Optional: pull skills from a separate edit store into this repo.
# Only needed if you keep a working copy outside the checkout — the packages
# here are the source, and install-skills.sh symlinks them into place.
# Copies SKILL.md + scripts/references/templates when present.
# Does NOT recurse into nested skills/ (prevents matryoshka packages).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="${AGENTS_SKILLS:-$HOME/.agents/skills}"

if [[ ! -d "$AGENTS" ]]; then
  echo "No edit store at $AGENTS — nothing to sync."
  echo "The packages in this repo are the source; install them with"
  echo "  ./scripts/install-skills.sh"
  echo "Set AGENTS_SKILLS=<dir> if your edit store lives somewhere else."
  exit 0
fi

# mirror folder|relative path under the edit store
#
# Mirror folders carry a stage prefix so the pipeline order is visible when
# browsing. Directory names in the edit store stay unprefixed
# — those names are the skill identifiers agents invoke (`/web2html`), and
# a space or digit in them breaks discovery and every symlink. Numbering is a
# presentation concern of this mirror only.
#
# Stages: 0 orchestrator · 1 capture · 2 tokens · 3 build · 4 QA.
# Parked skills live under archive/ and are not synced here.
SKILLS=(
  "1.0 - web2html|creative/website-to-html"
  "1.2 url-to-paper|url-to-paper"
  "1.3 hover-reel|hover-reel"
  "2.1 design-tokens|creative/design-tokens"
  "4.1 pixel-perfect|creative/pixel-perfect"
  "4.2 impeccable|impeccable"
  "4.3 design-taste-frontend|design-taste-frontend"
  "4.4 emil-design-eng|emil-design-eng"
  "4.5 find-animation-opportunities|find-animation-opportunities"
  "4.6 apple-design|apple-design"
  "4.7 web-design-guidelines|web-design-guidelines"
)

synced=0
for entry in "${SKILLS[@]}"; do
  name="${entry%%|*}"
  rel="${entry##*|}"
  src_dir="$AGENTS/$rel"
  src_skill="$src_dir/SKILL.md"
  if [[ ! -f "$src_skill" ]]; then
    if [[ "$name" == "1.0 - web2html" || "$name" == "1.3 hover-reel" ]]; then
      src_dir="$ROOT/$name"
      src_skill="$src_dir/SKILL.md"
    fi
    if [[ ! -f "$src_skill" ]]; then
      echo "WARN missing: $AGENTS/$rel/SKILL.md and $src_skill" >&2
      continue
    fi
  fi

  mkdir -p "$ROOT/$name"
  dest_skill="$ROOT/$name/SKILL.md"
  # install-skills.sh symlinks the repo into the edit store. cp onto itself
  # then exits 1 under set -e ("are identical").
  if [[ -e "$dest_skill" && "$src_skill" -ef "$dest_skill" ]]; then
    echo "skip self-copy $name (symlink install)"
  else
    cp "$src_skill" "$dest_skill"
  fi

  # Full package at top-level (scripts, references, templates)
  for sub in scripts references templates; do
    if [[ -d "$src_dir/$sub" ]]; then
      mkdir -p "$ROOT/$name/$sub"
      if [[ "$src_dir/$sub" -ef "$ROOT/$name/$sub" ]]; then
        continue
      fi
      cp -a "$src_dir/$sub/." "$ROOT/$name/$sub/"
    fi
  done

  # Package docs. These used to be left behind, so the mirror kept stale copies
  # long after the package moved on — including install paths that no longer
  # existed. Copy them like any other artifact.
  for doc in README.md CONFIGURE.md CONFIG.example.env; do
    if [[ -f "$src_dir/$doc" ]]; then
      if [[ -e "$ROOT/$name/$doc" && "$src_dir/$doc" -ef "$ROOT/$name/$doc" ]]; then
        continue
      fi
      cp "$src_dir/$doc" "$ROOT/$name/$doc"
    fi
  done

  # Prune build junk that must never enter the mirror. Skip when the
  # package IS the live checkout (symlink install) — wiping node_modules
  # here can delete hover-reel's Playwright and break capture.
  if [[ "$src_dir" -ef "$ROOT/$name" ]]; then
    echo "skip prune $name (live package)"
  else
    find "$ROOT/$name" \
      \( -name node_modules -o -name .venv -o -name __pycache__ -o -name '_tmp*' \) \
      -prune -exec rm -rf {} + 2>/dev/null || true
    find "$ROOT/$name" \
      \( -name 'package-lock.json' -o -name '*.pyc' \) \
      -delete 2>/dev/null || true
  fi

  # hover-reel ships its tests and the installable Capture Tool extension
  # alongside scripts/, plus the package.json its runner needs for `npm i`.
  # capture-extension/ is the Paper-connected developer package and the only
  # 1.3 capture path — it must stay in sync.
  if [[ "$name" == "1.3 hover-reel" ]]; then
    for sub in test capture-extension; do
      if [[ -d "$src_dir/$sub" ]]; then
        mkdir -p "$ROOT/$name/$sub"
        if [[ "$src_dir/$sub" -ef "$ROOT/$name/$sub" ]]; then
          continue
        fi
        cp -a "$src_dir/$sub/." "$ROOT/$name/$sub/"
      fi
    done
    for f in package.json README.md .gitignore; do
      if [[ -f "$src_dir/$f" ]]; then
        if [[ -e "$ROOT/$name/$f" && "$src_dir/$f" -ef "$ROOT/$name/$f" ]]; then
          continue
        fi
        cp "$src_dir/$f" "$ROOT/$name/$f"
      fi
    done
  fi

  echo "synced $name"
  synced=$((synced + 1))
done

# Drop known junk. Nested `<skill>/skills/` trees are retired.
for pkg in "1.0 - web2html"; do
  rm -rf "$ROOT/$pkg/skills" 2>/dev/null || true
done

echo "Done. $synced skill(s) synced from $AGENTS"

# If this sync followed a behavior change (not a pure typo), update only the
# matching surface: AGENTS.md / pipeline.html / workflow.html / index.html.
# README.md is a pointer — do not restamp it.
echo "Reminder: behavior changes update the matching doc surface. Skip README."
