#!/usr/bin/env bash
# Verify every artifact a skill claims actually ships in this repo.
#
# Runs against the checkout, so it works the same on any machine and needs no
# install. Point it elsewhere (an installed skills directory, say) with:
#   SKILLS_ROOT=~/.claude/skills ./scripts/check-skill-artifacts.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_ROOT="${SKILLS_ROOT:-$ROOT}"
fail=0

# Package folders may carry a stage prefix here ("1.3 hover-reel") and never do
# once installed. Resolve a plain skill name to whichever form exists.
pkg() {
  local name="$1" dir
  for dir in "$SKILLS_ROOT/$name" "$SKILLS_ROOT"/[0-9]*" $name" "$SKILLS_ROOT"/[0-9]*"- $name"; do
    [[ -d "$dir" ]] && { printf '%s' "$dir"; return 0; }
  done
  printf '%s' "$SKILLS_ROOT/$name"
}

need_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "MISSING: ${path#$SKILLS_ROOT/}"
    fail=1
  fi
}

# --- Core KEEP packages (archive/ is not required) ---
need_file "$(pkg web2html)/SKILL.md"
need_file "$(pkg web2html)/scripts/design_system_21_gate.py"
need_file "$(pkg web2html)/scripts/emit_fonts.py"
need_file "$(pkg web2html)/scripts/dump_index_raw.py"
need_file "$(pkg web2html)/scripts/jsx_to_static_html.py"
need_file "$(pkg web2html)/scripts/author_21_gate.py"
need_file "$(pkg web2html)/scripts/section_22_gate.py"
need_file "$(pkg web2html)/scripts/raw_23_census.py"
need_file "$(pkg web2html)/scripts/paper_23_disk_gold.py"
need_file "$(pkg web2html)/scripts/paper_23_clip_compare.py"
need_file "$(pkg web2html)/scripts/paper_23_rebuild_shots.py"
need_file "$(pkg web2html)/scripts/paper_23_validate.py"
need_file "$(pkg web2html)/references/section-23-paper-loop.md"
need_file "$(pkg web2html)/scripts/promote-bg-fills-to-img.py"
need_file "$(pkg web2html)/scripts/bg_fills.py"
need_file "$(pkg web2html)/scripts/paper_layer_names.py"
# 3.3 semantics_pass.py imports these three at module scope — deleting them
# silently breaks the whole step (regression caught in 2.10.0).
need_file "$(pkg web2html)/scripts/semantics_pass.py"
need_file "$(pkg web2html)/scripts/fidelity_freeze.py"
need_file "$(pkg web2html)/scripts/seed_index.py"
need_file "$(pkg web2html)/scripts/seed_index_polish.py"
need_file "$(pkg web2html)/scripts/inject-gsap-reveal.py"
need_file "$(pkg web2html)/scripts/verify-gsap-reveal.py"
need_file "$(pkg web2html)/templates/gsap-reveal.js"
need_file "$(pkg web2html)/references/gsap-inview.md"
need_file "$(pkg web2html)/scripts/open-human-review.py"
need_file "$(pkg web2html)/scripts/promote_ship.py"
need_file "$(pkg web2html)/references/polish-visual-restore.md"
need_file "$(pkg web2html)/scripts/footer_promote.py"
need_file "$(pkg web2html)/scripts/heading_promote.py"
need_file "$(pkg web2html)/scripts/section_promote.py"
need_file "$(pkg web2html)/scripts/inject-qa-overlay.py"
need_file "$(pkg web2html)/templates/qa-overlay.css"
need_file "$(pkg web2html)/templates/qa-overlay.js"
need_file "$(pkg web2html)/scripts/section-diff-loop.py"
need_file "$(pkg web2html)/scripts/agent_loop.py"
need_file "$(pkg web2html)/scripts/agent_findings_schema.json"
need_file "$(pkg web2html)/scripts/run_component_qa_wave.py"
need_file "$(pkg web2html)/scripts/run_responsive_review_wave.py"
need_file "$(pkg web2html)/scripts/rebuild_write_gate.py"
need_file "$(pkg web2html)/scripts/scrape-web.sh"
need_file "$(pkg web2html)/scripts/scrape_light.py"
need_file "$(pkg web2html)/scripts/scrape-sitemap.py"
need_file "$(pkg web2html)/scripts/open-phase-4-review.py"
need_file "$(pkg web2html)/scripts/scaffold-astro.py"
need_file "$(pkg web2html)/scripts/extract-astro-components.py"
need_file "$(pkg web2html)/scripts/convert-astro-home.py"
need_file "$(pkg web2html)/scripts/html_to_astro.py"
need_file "$(pkg web2html)/scripts/astro_build.py"
need_file "$(pkg web2html)/scripts/dump-interior-raw.mjs"
need_file "$(pkg web2html)/scripts/record-phase-5-pages.py"
need_file "$(pkg web2html)/scripts/build-astro-dist.py"
need_file "$(pkg web2html)/scripts/phase_5_compare.py"
need_file "$(pkg web2html)/scripts/interior_seo.py"
need_file "$(pkg web2html)/scripts/wire-astro-routes.py"
need_file "$(pkg web2html)/scripts/open-phase-5-review.py"
need_file "$(pkg web2html)/references/phase-5-astro.md"
need_file "$(pkg web2html)/references/step-11.md"
need_file "$(pkg web2html)/references/live-board.md"
need_file "$(pkg web2html)/references/scripts.md"
need_file "$(pkg web2html)/references/stage-spine.md"
need_file "$(pkg web2html)/references/paper-design-to-code.md"

need_file "$(pkg pixel-perfect)/SKILL.md"
need_file "$(pkg pixel-perfect)/scripts/section-audit.mjs"
need_file "$(pkg pixel-perfect)/scripts/validate-visual.sh"
need_file "$(pkg pixel-perfect)/scripts/summarize-validation.sh"
need_file "$(pkg pixel-perfect)/references/region-manifest.md"

# --- 3.2 polish skills: Emil + companions (Pitfall #215) ---
need_file "$(pkg emil-design-eng)/SKILL.md"
need_file "$(pkg find-animation-opportunities)/SKILL.md"
need_file "$(pkg apple-design)/SKILL.md"
need_file "$(pkg web-design-guidelines)/SKILL.md"

need_file "$(pkg hover-reel)/SKILL.md"
need_file "$(pkg hover-reel)/scripts/visible-cursor.mjs"
need_file "$(pkg hover-reel)/scripts/skill-paths.mjs"
need_file "$(pkg hover-reel)/scripts/build-capture-extension.mjs"
need_file "$(pkg hover-reel)/capture-extension/manifest.json"
need_file "$(pkg hover-reel)/capture-extension/service-worker.js"
need_file "$(pkg hover-reel)/capture-extension/content/targeting.js"
need_file "$(pkg hover-reel)/capture-extension/content/nav-breakpoints.js"
need_file "$(pkg hover-reel)/capture-extension/sidepanel/panel.html"
need_file "$(pkg hover-reel)/capture-extension/bridge/host.mjs"
need_file "$(pkg hover-reel)/capture-extension/install-native-host.command"
need_file "$(pkg hover-reel)/capture-extension/content/capture.js"
need_file "$(pkg hover-reel)/capture-extension/content/tag-overlays.js"
need_file "$(pkg hover-reel)/capture-extension/content/session-from-url.js"
need_file "$(pkg hover-reel)/capture-extension/bridge/semantics.mjs"
need_file "$(pkg hover-reel)/capture-extension/sidepanel/panel.js"

need_file "$(pkg url-to-paper)/SKILL.md"
need_file "$(pkg url-to-paper)/scripts/overlay.js"
need_file "$(pkg url-to-paper)/scripts/pre-pesticide.js"
need_file "$(pkg url-to-paper)/scripts/pre-pesticide.mjs"
need_file "$(pkg url-to-paper)/scripts/pre-pesticide-core.mjs"
need_file "$(pkg url-to-paper)/scripts/source-sections.mjs"
need_file "$(pkg url-to-paper)/scripts/capture-source-sections.mjs"
need_file "$(pkg url-to-paper)/scripts/seed-source-board.mjs"
need_file "$(pkg url-to-paper)/scripts/review-sequence.mjs"
need_file "$(pkg url-to-paper)/scripts/apply-review-sequence.mjs"
need_file "$(pkg url-to-paper)/scripts/detect-sections.js"
need_file "$(pkg url-to-paper)/scripts/experiment-capture-home.mjs"
need_file "$(pkg url-to-paper)/scripts/layer-ids-census.mjs"
need_file "$(pkg url-to-paper)/scripts/chrome-bars.mjs"
need_file "$(pkg url-to-paper)/scripts/breakpoint-shot-qa.mjs"
need_file "$(pkg hover-reel)/scripts/park-12-chrome.mjs"
need_file "$(pkg web2html)/references/12-desktop-source.md"
need_file "$(pkg web2html)/references/13-buttons-components.md"
need_file "$(pkg hover-reel)/scripts/pull-desktop-specimens.mjs"
need_file "$(pkg hover-reel)/scripts/author-button-hover.mjs"
need_file "$(pkg hover-reel)/scripts/source-button-hover.mjs"
need_file "$(pkg web2html)/scripts/apply-hover-css.py"
need_file "$(pkg web2html)/scripts/author-nav-drawer.py"
need_file "$(pkg web2html)/scripts/test_author_nav_drawer.py"
need_file "$(pkg web2html)/templates/nav-drawer.js"
need_file "$(pkg web2html)/references/nav-drawer.md"
need_file "$(pkg web2html)/scripts/author-faq.py"
need_file "$(pkg web2html)/scripts/test_author_faq.py"
need_file "$(pkg web2html)/templates/faq.js"
need_file "$(pkg web2html)/references/faq.md"
need_file "$(pkg web2html)/scripts/author-nav-dropdown.py"
need_file "$(pkg web2html)/scripts/test_author_nav_dropdown.py"
need_file "$(pkg web2html)/templates/nav-dropdown.js"
need_file "$(pkg web2html)/references/nav-dropdown.md"
need_file "$(pkg url-to-paper)/scripts/emit-design-system.mjs"
need_file "$(pkg url-to-paper)/scripts/create-paper-file.mjs"
need_file "$(pkg url-to-paper)/scripts/assemble-lander.mjs"
need_file "$(pkg url-to-paper)/scripts/import-sections.mjs"
need_file "$(pkg url-to-paper)/scripts/stretch-root.mjs"
need_file "$(pkg url-to-paper)/scripts/run-geometry-postflight.mjs"
need_file "$(pkg url-to-paper)/scripts/arrange-artboards.mjs"
need_file "$(pkg url-to-paper)/scripts/rulers.mjs"
need_file "$(pkg url-to-paper)/scripts/draw-rulers.mjs"
need_file "$(pkg url-to-paper)/scripts/run-design-library-step.mjs"
need_file "$(pkg url-to-paper)/scripts/token-geometry-guard.mjs"
need_file "$(pkg url-to-paper)/scripts/library-sheet.mjs"
need_file "$(pkg url-to-paper)/scripts/tailwind-defaults.mjs"
need_file "$(pkg url-to-paper)/templates/library/foundations/01-header.html"
need_file "$(pkg url-to-paper)/templates/library/foundations/05-elevation-radii.html"
need_file "$(pkg url-to-paper)/scripts/localize-html-images.mjs"
need_file "$(pkg url-to-paper)/scripts/repair-paper-images.mjs"
need_file "$(pkg url-to-paper)/scripts/flatten-decorative-abs.mjs"
need_file "$(pkg url-to-paper)/scripts/flatten-paper-abs.mjs"
need_file "$(pkg url-to-paper)/scripts/overlay-paint-order.mjs"
need_file "$(pkg url-to-paper)/scripts/fix-overlay-paint-order.mjs"
need_file "$(pkg url-to-paper)/scripts/qa-paper.mjs"
need_file "$(pkg url-to-paper)/scripts/missing-elements-lib.mjs"
need_file "$(pkg url-to-paper)/scripts/missing-elements-qa.mjs"
need_file "$(pkg url-to-paper)/scripts/apply-missing-elements-fix.mjs"
need_file "$(pkg url-to-paper)/scripts/run-missing-elements.mjs"
need_file "$(pkg url-to-paper)/references/missing-elements-playbook.md"
need_file "$(pkg url-to-paper)/scripts/merge-split-headings.mjs"
need_file "$(pkg url-to-paper)/scripts/extract-library.mjs"
need_file "$(pkg url-to-paper)/scripts/tailwind-defaults.mjs"
need_file "$(pkg url-to-paper)/scripts/library-tokens.mjs"
need_file "$(pkg url-to-paper)/scripts/capture-paints.mjs"
need_file "$(pkg url-to-paper)/scripts/library-seed-compare.mjs"
need_file "$(pkg url-to-paper)/scripts/validate-library-seed.mjs"
need_file "$(pkg url-to-paper)/scripts/render-library.mjs"
need_file "$(pkg url-to-paper)/scripts/apply-theme-tokens.mjs"
need_file "$(pkg hover-reel)/scripts/capture-session.mjs"
need_file "$(pkg hover-reel)/scripts/capture-extra-pages.mjs"
need_file "$(pkg hover-reel)/scripts/capture-interior-breakpoints.mjs"
need_file "$(pkg url-to-paper)/scripts/seed-interior-page-tokens.mjs"
need_file "$(pkg url-to-paper)/scripts/dump-interior-raw.mjs"
need_file "$(pkg hover-reel)/scripts/run-paper-phase.mjs"
need_file "$(pkg url-to-paper)/scripts/park-nav.mjs"
need_file "$(pkg url-to-paper)/scripts/paper-walk.mjs"
need_file "$(pkg url-to-paper)/scripts/write-paper-section.mjs"
need_file "$(pkg hover-reel)/scripts/source-semantics.mjs"
need_file "$(pkg hover-reel)/scripts/apply-source-semantics.mjs"
need_file "$(pkg hover-reel)/scripts/prepare-state-html.mjs"
need_file "$(pkg hover-reel)/scripts/dropdown-capture.mjs"
need_file "$(pkg hover-reel)/scripts/write-dropdown-pair.mjs"
need_file "$(pkg hover-reel)/scripts/park-capture-boards.mjs"
need_file "$(pkg hover-reel)/scripts/park-source-hover.mjs"
need_file "$(pkg hover-reel)/scripts/hamburger-capture.mjs"
need_file "$(pkg hover-reel)/scripts/capture-hamburger-states.mjs"
need_file "$(pkg hover-reel)/scripts/capture-menu-states.mjs"
need_file "$(pkg hover-reel)/scripts/build-paper-states.mjs"
need_file "$(pkg url-to-paper)/scripts/apply-theme-tokens.mjs"
need_file "$(pkg url-to-paper)/scripts/token-pass-targets.mjs"

need_file "$(pkg design-tokens)/SKILL.md"
need_file "$(pkg impeccable)/SKILL.md"
need_file "$(pkg design-taste-frontend)/SKILL.md"
need_file "$(pkg emil-design-eng)/SKILL.md"
need_file "$(pkg find-animation-opportunities)/SKILL.md"
need_file "$(pkg apple-design)/SKILL.md"

# validate-visual must exit non-zero on fail
if ! grep -q 'exit 1' "$(pkg pixel-perfect)/scripts/validate-visual.sh" 2>/dev/null; then
  echo "WARN: validate-visual.sh may not exit 1 on fail"
  fail=1
fi

# frame-to-html typo
if grep -q 'frame-to-html' "$(pkg design-tokens)/SKILL.md" 2>/dev/null; then
  echo "MISSING fix: frame-to-html typo still in design-tokens"
  fail=1
fi

# No machine-specific paths may ship. A skill that hardcodes one breaks the
# moment the checkout moves or someone else installs it.
leaks=$(grep -rIn   --exclude-dir=.git --exclude=.git --exclude-dir=node_modules \
  --exclude-dir=.venv --exclude-dir=.context --exclude-dir=.impeccable \
  --exclude-dir=.conductor --exclude-dir=archive \
  --exclude-dir=.claude --exclude-dir=.terminalgraph --exclude-dir=.hermes \
  --exclude="check-skill-artifacts.sh" \
  -e '/Users/' -e 'conductor/repos' -e '\.agents/skills/' \
  "$SKILLS_ROOT" 2>/dev/null || true)
if [[ -n "$leaks" ]]; then
  echo "MACHINE-SPECIFIC PATHS (use \$SKILLS or resolve from the script):"
  printf '%s\n' "$leaks" | sed "s|$SKILLS_ROOT/||"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "check-skill-artifacts: FAILED"
  exit 1
fi
echo "check-skill-artifacts: OK"
