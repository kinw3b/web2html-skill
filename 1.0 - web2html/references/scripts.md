# Scripts (on demand)

Gates and helpers. Paths are `$SKILLS/web2html/scripts/` unless noted.

| Script | Step | Role |
|---|---|---|
| `run_config.py` | 1.0 | `intake <project> --source … --speed …` records the run questions to `qa/run-config.json` (copies + classifies a source folder into `source-html/`). Question 1 is live URL or Webflow / HTML source; a folder choice is followed by the absolute path. Clean HTML is adopted: that folder is the ship, Phase 2 is off, Phase 4 is required through 4.4. Fast writes the 1.3 / 2.1 skip receipts. `show` prints the contract. |
| `source_fidelity.py` | 3.1 / 4.3 | Adopt only. `snapshot` locks `source-html/` before the light polish. `verify` fails a class, copy, CSS, or JS change. `gaps` writes `qa/source-gaps.json`. `record-gaps` checks `qa/phase-4-gap-plan.json` and locks every page that was not a gap. |
| `hover-reel/scripts/source-hover-light.mjs` | 3.2 (fast) | No 1.3 receipt → mine source CSS `:hover` for the ship's CTAs into `qa/button-hover.json` (same shape `apply-hover-css.py` reads). Run by `mark 3.2 active` when the library was skipped. Never invents a hover. |
| `orca_workspace.py` | start | `ensure <slug>` creates the run's single primary workspace folder and prints `RUN ROOT`: registered in Orca as a project / folder context (`repo add`) when the CLI is reachable, a plain folder otherwise; reuses the recorded workspace on every later call — never a second worktree. `show <slug>` prints it again for a continued session. `start` registers the folder itself if ensure was skipped. Never a gate |
| `pipeline-progress.py` | all | `start` / `resume` / `mark` (1.4 active opens Paper + stamped Capture Tool tab) / `handoff` / `open-capture` (re-open) / `capture-doctor` (bridge check; FAIL = side panel OFFLINE) / `relay` (mid-session handoff to a fresh agent of the **same source** at a receipt boundary; Orca terminal when reachable, else prints the prompt; never a human stop — Pitfall #218) |
| `run_report.py` | every mark done | `build` (re)writes `<project>/run-report.md` — the portable run log: sessions, agent + model, per-step / per-phase durations, human-checkpoint outcomes, captured Paper review comments, and notes. `note <project> --step 2.4 --text "…" [--author human]` logs an additional request from a checkpoint. Runs automatically inside `mark done`; never a gate |
| `open_doc.py` | start / 2.4 / 3.4 / 5.6 | Open a pipeline document: Orca browser tab (`orca tab create --url`, `file://` works) when inside a reachable Orca, else the caller's fallback (Chrome / `open` / `xdg-open`). `WEB2HTML_BROWSER=auto\|orca\|default`. Used by `open_live_board`, `open-build-review.py`, `open-human-review.py`, `open-phase-5-review.py`. Never a gate |
| `harness_probe.py` | start / resume | Which harness, whether Orca is reachable, which agent id is the same source (Pitfall #220), and the adapter rungs `waves orca\|subagent\|serial` / `relay orca-terminal\|print-prompt`. Writes `qa/harness-probe.json`. Always exit 0 (Pitfall #219) |
| `context_budget.py` | every mark | Context spent: Claude Code transcript → statusline sidecar → spend ledger in `qa/pipeline-progress.json` (fed by `--shoot` / `--record` / `mark`). `--brief` one line; arm 50 % / force 75 % (`WEB2HTML_RELAY_ARM` / `_FORCE`, `WEB2HTML_CONTEXT_WINDOW`) |
| `wave.py` | 2.3 (required) / 3.2 / 5.2 | 2.3 VALIDATE LOOK **MUST** run this after `--shoot-open`. `prepare` (snapshot + a reviewer lease per open band / companion / page) → `start` (`orca`: `run-create` + `worker-start --agent <same source>`; `subagent` / `serial`: prints the specs) → `wait` (one `check --wait`; validates `worker_done`, `worker-release`s, acks; exit 4 on a question) → `ready` → `apply` (2.3: patch + `--record` per band; 3.2: promote reports to `qa/<skill>.md`). Workers are read-only; `check --agent` is their self-check. Recipe `references/orca-relay.md`. Pitfall #221 |
| `hover-reel/scripts/pull-desktop-specimens.mjs` | 1.3 | After seed, duplicate unique buttons + components from `home-desktop` onto FRAME `Buttons` / `Components`, then author button hover from source CSS. Stamps the source pixel width, hugs the row, restacks by section `NN`, and clears Components past the measured Buttons edge. Refuses a section shell or a read-back that drifted. Receipt `qa/buttons-components-pull.json` needs `geometry.ok`. Also writes `qa/button-hover.json`. |
| `hover-reel/scripts/author-button-hover.mjs` | 1.3 | Light pass: mine source CSS `:hover` onto pulled Buttons. Usually invoked from the pull. Receipt `qa/button-hover.json` |
| `scrape-web.sh` + `scrape_light.py` | 1.1 | One URL, images + Latin fonts, stub contract |
| `rebuild_write_gate.py` | 2.1+ | No ship HTML before 1.4. `--allow design-system` at 2.1; `--allow index` at 2.2+; `--allow polish` at 3.x; `--allow pages` at 5.x |
| `design_system_21_gate.py` | 2.1 | Emitted `rebuild/design-system.html` + `tokens.css` from `library.json` |
| `emit_fonts.py` | 2.1 | Latin `@font-face` → `rebuild/css/fonts.css` + `rebuild/fonts/*.woff2` |
| `dump_index_raw.py` + `jsx_to_static_html.py` | 2.2 | Paper get_jsx JSON → file:// `index-raw.html` with tokens.css + fonts.css; expand `<div />` |
| `author_21_gate.py` | 2.2 | Authored `rebuild/index-semantic.html`, not a get_jsx dump, no source/external hrefs. Raw dump is HTML not JSON |
| `seed_index.py` | 2.2 / 2.3 | Copy `rebuild/index-semantic.html` → `rebuild/index.html` (never overwrite) |
| `section_22_gate.py` | 2.3 | Every homepage section at 1600 / 768 / 390 |
| `raw_23_census.py` | 2.3 | index-raw SVG/icon fills vs authored `index.html` |
| `paper_23_disk_gold.py` | 2.3 | Map ship bands → 1.2 `source-sections/NN-*.png` |
| `paper_23_rebuild_shots.py` | 2.3 | `file://` rebuild PNGs at 1600 / 768 / 390 (includes footer) |
| `paper_23_clip_compare.py` | 2.3 | Pull numbered 1.2 clips into `qa/paper-measure/compare/` + side-by-sides |
| `paper_23_validate.py` | 2.3 | VALIDATE after APPLY: `--shoot-open` (every open band), then `wave.py` LOOK, then `--record` from the findings / `--residual`, `--status`. `--next` / `--id X --shoot` remain for a single band. ≤3 rounds per band. Receipt `qa/paper-measure/<id>.validate.json` + applied 2.3 wave (Pitfall #216 #221) |
| `inject-qa-overlay.py` | 2.4 | Outlines toggle. Always `rebuild/css` + `rebuild/js`. Never a sibling `css/` |
| `open-build-review.py` | 2.4 | `--stage 2.4` TAGS on. `qa/build-checkpoint-opened.json` |
| `verify-rebuild-trees.py` | 2.x | One `rebuild/`. Sibling `-semantic` / `-hover` fail |
| `verify-fonts.py` | 2.2 | Latin `@font-face`, fallbacks. Not a 1.1 job |
| `semantics_pass.py` + `verify-semantics.py` | 3.3 | Landmarks + scrape-only SEO on `index-polish.html` (`--freeze-structure`) |
| `fidelity_freeze.py` | 2.4 / 3.x | Snapshot 2.4 `index.html` hash + type + library classes; verify polish did not restyle |
| `seed_index_polish.py` | 3.1 | Copy `rebuild/index.html` → `rebuild/index-polish.html` when 3.x goes active (never overwrite; not at 2.4 done) |
| `inject-gsap-reveal.py` / `verify-gsap-reveal.py` | 3.2 | Mandatory sequential GSAP in-view on `index-polish.html` (`top 75%`, parent groups → children). Never skip from 1.4 |
| `apply-hover-css.py` | 3.2 | Write + link `rebuild/css/hover.css` from 1.3 `qa/button-hover.json`. Receipt `qa/button-hover-css.json`. Never skip because Capture Tool did not run |
| `author-nav-drawer.py` | 3.2 | If polish paints a hamburger, author `#nav-panel` from desktop links + wire `nav-drawer.css` / `nav-drawer.js`. Receipt `qa/nav-drawer.json`. Never skip because Capture Tool did not run |
| `author-faq.py` | 3.2 | If polish paints FAQ rows, wire accordion + fill empty answers from scrape. Receipt `qa/faq.json`. Never skip empty Paper bodies |
| `author-nav-dropdown.py` | 3.2 | If polish paints a dropdown or scrape has a matching submenu, wire hover/click panel. Receipt `qa/nav-dropdown.json`. Never skip for Capture Tool |
| `record-polish-pass.py` / `render-polish-report.py` / `verify-polish-passes.py` | 3.1–3.4 | Polish receipts. Receipt names `c3-3.1-impeccable` / `c3-3.2-design-taste-frontend` / `c3-3.3-emil-design-eng` are **C/3 sub-pass ids** (impeccable → taste → emil), not board steps: impeccable + taste land during board **3.1**, emil during board **3.2**. The 3.2 companions (`web-design-guidelines` / `find-animation-opportunities` / `apple-design`) take no C/3 receipt; each writes `qa/<skill>.md`, rendered as its own card and required by `verify-polish-passes.py` (Pitfall #215) |
| `open-human-review.py` | 3.4 | Opens 2.4 `index.html` + `index-polish.html?qa-outlines=off` + polish report. `?qa-outlines=tags` turns outlines on |
| `promote_ship.py` | 3.4 done | Promotes `index-polish.html` → `index.html`, archives the other homepage HTML under `rebuild/archive/`, stamps outlines off (`data-qa-ship="final"`). `?qa-outlines=` toggles. Writes `rebuild/.vercelignore` (`archive`) |
| `scrape-sitemap.py` | 4.1 | Extra same-origin URLs → `qa/phase-4-sitemap.json` |
| `open-phase-4-review.py` | 4.4 | Writes `qa/phase-4-review.md` and opens Paper |
| `scaffold-astro.py` | 5.1 | Writes `astro/` from the 3.4 rebuild + `qa/phase-5-scaffold.json` |
| `extract-astro-components.py` | 5.1 | Header + Footer (once) plus Paper/comment components → `qa/phase-5-components.json` |
| `convert-astro-home.py` | 5.1 | Polish homepage → `src/pages/index.astro` + `qa/phase-5-home.json` |
| `html_to_astro.py` / `astro_build.py` | 5.x | Shared helpers: HTML → .astro fragments; `astro build` + `file://` relativize of `astro/dist` |
| `dump-interior-raw.mjs` | 5.2 | Serial `get_jsx` → `rebuild/{slug}-raw.html` (wrapper; real dump is `url-to-paper`) |
| `record-phase-5-pages.py` | 5.2 | `astro/src/pages/{slug}.astro` on the 5.1 chrome, contamination + `#` hrefs → `qa/phase-5-pages.json` |
| `build-astro-dist.py` | 5.3 / 5.4 | `astro build` + relativize → `qa/phase-5-build.json`; the ship for shots is `astro/dist/{slug}/index.html` |
| `phase_5_compare.py` | 5.3 / 5.4 | `--mode desktop` (1600) or `responsive` (768,390) against `astro/dist` shots |
| `wire-astro-routes.py` / `interior_seo.py` | 5.5 | Sitemap path / label → `/slug/`; `/` home; per-page scrape-only SEO into frontmatter; `astro build` → `qa/phase-5-links.json` |
| `open-phase-5-review.py` | 5.6 | Writes `qa/phase-5-review.md`; opens built home + first interior on `file://` |
| `watch_agent_ping.py` | 1.4 | Optional: wake into Paper sign-off after Capture Tool Done |

Sibling packages (load the skill, then its scripts):

| Package | Step |
|---|---|
| `url-to-paper` | 1.2 capture + `create-paper-file.mjs` (reuses `qa/paper-file.json`; `--new-file` opts out) + geometry + Design Library mine + 2.1 `emit-design-system.mjs` + 4.3 `seed-interior-page-tokens.mjs` + 5.2 `dump-interior-raw.mjs` |
| `hover-reel` | 1.2 `capture-session.mjs`; 1.3 `pull-desktop-specimens.mjs` + `author-button-hover.mjs`; 1.4 optional Capture Tool; 4.2 `capture-extra-pages.mjs`; 5.4 `capture-interior-breakpoints.mjs` |
| `frontend-design` | 2.2 author · 5.2 interior bodies |
| `pixel-perfect` | 2.3 one-pass assist (disk-clip gold). Not a refine loop. Not 3.x. |
| `design-tokens` | token skill (folder `2.1 design-tokens` ≠ 2.1 Author) |
| `impeccable` / `design-taste-frontend` | 3.1 |
| `emil-design-eng` / `web-design-guidelines` / `apple-design` / `find-animation-opportunities` | 3.2 |

CLI signatures and Playwright facts: `references/tooling-notes.md`.
