---
name: web2html
description: "Convert a live URL to pixel-perfect static HTML via Paper. Invoke as /web2html or Convert <URL> to HTML. First tool: pipeline-progress.py start for a NEW run (git init -b main and .gitignore when missing), resume for a continued session. Optional: orca_workspace.py ensure <slug> first when you want the run folder registered as an Orca project (never automatic; WEB2HTML_ORCA_WORKSPACE=off disables). Never write rebuild HTML before 2.1. Never scrape-to-site, Firecrawl-to-HTML, Tailwind CDN, or freehand a homepage. If rebuild/index.html exists without a live board and 1.4 sign-off, quarantine it and start from 1.1. 2.1 emits the Design System page from 1.3 tokens; 2.2 authors rebuild/index.html — the one homepage file — from Paper using those tokens; 2.3 and 3.x edit that same file in place. A run spans three sessions (1 capture / 2 build / 3 QA) plus optional Phase 4 (Paper) and Phase 5 (Astro site: shared chrome pulled once from the 3.4 polish, then each page's body); 2.0 and optional 5.0 are recommended on the strong model; the tier is advice, never a gate — run any session on whichever model the operator chose. Homepage only until 3.4. file:// preview. No GIFs, no local server."
version: 2.39.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [website, rebuild, static, html, css, js, paper, semantic, astro]
    related_skills:
      - frontend-design
      - hover-reel
      - url-to-paper
      - design-tokens
      - design-taste-frontend
      - impeccable
      - emil-design-eng
      - find-animation-opportunities
      - apple-design
      - pixel-perfect
      - orchestration
      - orca-cli
---

> `$SKILLS` — the directory your agent loads skill packages from.
> Set it once: `export SKILLS=~/.claude/skills` (or wherever you keep them).
> Compat alias: `$SKILLS/website-to-html` is this same package.

# web2html: any site → Paper → semantic HTML

**This file is the index (~200 lines). Do not page it. Do not say it is huge.
Do not read it twice.** Detail lives in `references/` and is loaded **per
step** — see the table below. `read_file` that one file, then act.

## Summon — first tool, before anything else

**Invoke:** `/web2html`  
**Trigger:** `Convert <URL> to HTML`

```sh
# NEW run — start the board in the folder you choose (create + cd first if new)
# start git-inits that folder on main and writes .gitignore when either is missing
mkdir -p /path/to/templates/<project> && cd /path/to/templates/<project>
python3 $SKILLS/web2html/scripts/pipeline-progress.py start .
# OPTIONAL first, only when you want the run folder registered as an Orca
# project (folder context in the Orca app): ensure creates/reuses one primary
# workspace and prints its RUN ROOT — pass that to start instead. Never
# automatic; start never registers anything. WEB2HTML_ORCA_WORKSPACE=off
# disables registration globally.
python3 $SKILLS/web2html/scripts/orca_workspace.py ensure <project-slug>
python3 $SKILLS/web2html/scripts/pipeline-progress.py start <RUN ROOT>
# continued session 2 or 3 — never start, it resets the board
# resume does not reopen the board; the start tab stays open
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --at 2.1 --owner session-2
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --owner session-2   # --at detected from the board
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --owner session-2 --model claude-fable-5.1   # record who runs this session
# only after an explicit ensure: show prints the recorded RUN ROOT
python3 $SKILLS/web2html/scripts/orca_workspace.py show <project-slug>
```

**Every new session `resume`s first** — it detects where the run sits, logs the
session, and prints the run total so far. Then `mark --status active` before
touching an agent step: marks are the clock. Each agent step's duration is
`ended − started` and the run total is the **sum of those durations, never
wall clock**. Human checkpoints (1.4, 2.4, 3.4, 4.4, 5.6) are not timed and
are not added to the total (Pitfall #231).
`timing <project>` prints the table (Pitfall #227 #228). `--agent` defaults to
the harness probe; `--model` (or `WEB2HTML_MODEL`) names the model. The board
HUD names the current session and each phase card carries a
`duration · agent · model` line, so a phase that mixed agents shows both
(Pitfall #229).

**Run report (2.29.0).** Every `mark done` refreshes `<project>/run-report.md` —
the portable run log (sessions, agent + model, per-step / per-phase agent
durations, checkpoint outcomes — the wait is not timed — captured Paper review
comments, notes). At a human
checkpoint, log any additional request the human made with
`run_report.py note . --step 2.4 --text "…" --author human`. Never a gate.

**Requested advance (2.32.0).** If the human asked this session to move to the
next phase, pass `--requested` on `resume` and on the `mark` that closes the
checkpoint. Red polish / semantics / fidelity / type gates **warn and do not
stop**. Do not remediate them. Write the phase receipt they asked for, then
`mark --step 3.4 --status done --requested` and enter the next phase.
`open-human-review.py --requested` still opens. Subagents, and any mark the
human did not ask for, must **not** pass `--requested` — those still refuse.
Predecessor, artifact, ship-file, and intake-skip gates stay hard either way.
Pitfall #235.

Both print a **probe** line (`harness_probe.py <project> --brief`): the harness, whether
Orca is reachable, the same-source agent id, and the rungs `waves orca|subagent|serial` /
`relay orca-terminal|print-prompt`. `orca reachable` → read `references/orca-relay.md`
once and load `orchestration` + `orca-cli` (stubs; `orca skills get …`) before the
first Orca verb. At **2.3**, `wave.py` is required on every rung — Orca terminals
when `waves orca`, this harness's subagent tool when `subagent`, the printed specs
when `serial`. Anything else → never load `orchestration` / `orca-cli`; still run
`wave.py` at 2.3 (Pitfall #219 #220 #221).

## Intake — question 1, then a path when they have a folder, then speed, then checkpoints on full (2.26.0)

`mark --step 1.1 --status active` **refuses** until `qa/run-config.json` exists.
`start` prints this script. Fire this harness's native question tool, then record:

```sh
python3 $SKILLS/web2html/scripts/run_config.py intake /path/to/templates/<project> \
  --source none|/abs/path/to/html-export --speed full|fast [--checkpoints human|auto]
```

1. **Where does this run start?** One choice, these labels:
   - `Live URL — author from Paper` → `--source none`
   - `Webflow / HTML source` → fire a **follow-up** before anything else.
     Question: `Paste the absolute path to the HTML folder.` The answer is the
     path, typed in the text field. Do not guess a folder. Do not record intake
     until that path exists on disk. `--source /abs/path` copies it to
     `<project>/source-html/` and classifies it.
   `clean-html` (Webflow export / static build) is **adopted**: `source-html/` is the ship.
   Do not create `rebuild/`. Do not author a homepage. Phase 2 is marked off on the board.
   Phase 3 may add accessibility attributes only. **Phase 4 is required** — do not ask
   at 3.4. Continue through 4.4. Phase 4 authors only empty CMS layouts from Paper
   screenshots. Tokens are never bound back. `framework-dump` (`_next/`, `__NEXT_DATA__`,
   Framer runtime, empty React root) is not adopted — 2.2 authors from Paper.
2. **Full or fast?** `fast` forces auto checkpoints: 1.2 shoots **1600 + 390** · 1.3 skipped ·
   2.1 skipped except `emit_fonts.py` on a non-adopt run · 2.3 at the configured widths ·
   3.2 button hover from source CSS. **3.4 always stops on a URL run; a folder run's stop is 4.4.**
   `run_config.py show <project>` prints the contract.
3. **Only when they chose full — human checkpoints or autonomous?** `human` (default)
   stops at 1.4 / 2.4 / 3.4. `auto` is the autonomous run: full fidelity (all three
   widths + Design Library), 1.4 and 2.4 self-accept, and the session runs unattended
   through Phase 3 — **3.4 is still the human check on a URL run** (a folder run's stop
   is 4.4). Pass `--checkpoints auto`. Fast never asks this — it is always auto.

`start` is the only command that opens the live board. If **that** tab does
not open, **stop**. Print the `file://` URI. `resume` / `mark` / later
sessions never reopen it. Then read
`references/live-board.md` once (todos, mark, never-reuse). Derive `<project>`
from the URL slug under `Documents/templates/<project>`. Never overwrite the
spec `web2html/pipeline.html`.

**Writing `rebuild/*.html` now is a failed run.** Gate:

```sh
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project>
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project> --allow design-system  # 2.1
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project> --allow index           # 2.2+
```

Red means stop. Do not polish a quarantined file (Pitfall #148).

## Hard rules

1. Never skip a numbered step (1.1 → 3.4). `skip` fails on required steps. A **fast** run does not skip 1.3 / 2.1 — the intake writes `qa/design-library-skipped.json` / `qa/design-system-skipped.json` and those steps mark done on the receipt. Capture Tool is optional leftover hover at 1.4 (tab opened by `mark 1.4 active`; `open-capture` re-opens). On a **URL run**, Phase 4 is optional after 3.4 (`qa/phase-4-opted.json` or `qa/phase-4-skipped.json`). On a **Webflow / HTML folder** run, Phase 4 is required: do not ask, do not write `qa/phase-4-skipped.json`, and do not `skip` 4.1–4.4. Phase 5 is optional after 4.4 (`qa/phase-5-opted.json` or `qa/phase-5-skipped.json`). A **full + autonomous** run (intake question 3) self-accepts 1.4 / 2.4 and stops at 3.4 (folder run: 4.4).
2. No `rebuild/*.html` until 1.4 is signed and 2.1 is open. First rebuild HTML is 2.1 `design-system.html` (token contract). First authored write is 2.2 `rebuild/index.html` — never scrape-to-site, never a get_jsx dump. 2.3 patches that same file in place.
3. Homepage only through 3.4. Extra routes stay out of 1.2. Phase 4 is Paper-only. Phase 5 binds the site into `astro/` after 4.4 opt-in: 5.1 pulls Header / Footer / components **once** from the 3.4 polish, 5.2 authors only each page's `<main>` as `astro/src/pages/{slug}.astro`. 5.5 is the one post-3.4 href exception, plus 3.3-style scrape-only SEO per page. Exit if `plan.pages.length > 1` at 1.2 without `--allow-multi-page`.
4. Stage L is never skippable on a **full** run. No ship HTML until Paper has a `Design Library` artboard (foundations only), `get_tokens` is non-empty, and `design-library/library.json` exists. Disk-only does not count. On a **fast** run the intake receipt stands in for the library and 2.2 authors without a token contract.
5. One `rebuild/`, one homepage file. `rebuild/index.html` is the ONLY homepage HTML from 2.2 on: authored (2.2), patched in place (2.3), locked (2.4), polished in place (3.1–3.3). **3.4 done** strips the QA overlay from that same file (`finalize_ship.py`) — no promote, no archive, no `index-semantic` / `index-polish` / `rebuild/index-raw` siblings (the Paper dump lives at `qa/index-raw.html`; Pitfall #223 #234 #237). Optional Phase 5 writes `astro/` and does not replace `rebuild/`. No local HTTP server. Preview is `file://` in the **machine's default browser** (`open` / `xdg-open` — Chrome, Brave, or whatever is set), including when the probe says `orca reachable` (`open_doc.py`: the board, 2.4 review, 3.4 compare + polish report, 5.6 routes, any `index.html`). Concurrent runs must not open those in Orca (Pitfall #242). `WEB2HTML_BROWSER=orca|auto` opts into an Orca tab. 5.3+ relativizes `astro/dist` so built pages open on `file://`. The agent verifies with `astro build`, never `astro dev`; the human may run `npm run preview`.
6. Human stops: **1.4**, **2.4**, **3.4**, optional **4.4**, optional **5.6**. With `--checkpoints auto` (or any fast run) 1.4 and 2.4 self-accept and the session keeps going; **3.4 is never automatic on a URL run.** A **Webflow / HTML folder** run does not stop at 3.4 — Phase 4 is required and the stop is **4.4**. Session 2 does not yield until **2.4** (Phase 2 is off on an adopted folder). **3.4** on a URL run is finish vs Phase 4. **4.4** is finish vs Phase 5. **5.6** is finish (tidy). CTA only at those yields (Pitfall #190 #192 #225). If the human asked this session to move to the next phase, pass `--requested`: red polish / semantics / fidelity / type warns and does not stop (Pitfall #235). Subagents do not pass it. A **relay** (`pipeline-progress.py relay`, when `mark` prints `RELAY armed`) is a change of agent at a receipt boundary, not a yield: same-source agent, Orca terminal when reachable, else print the prompt; never a CTA (Pitfall #218 #219 #220).
7. Silent shell 20s → kill (Pitfall #112). Gate evidence must be truthful.
8. **1.2 creates one Paper document per run.** The first capture `create_file`s. A retry reopens `qa/paper-file.json`. Never `list_files`. Never open a similarly-named file from another project. `--new-file` is the only second document (Pitfall #187 #224).

Versioned rows: `references/pillars.md`. Findings: `references/pitfalls.md`.
Spine: `references/stage-spine.md`. Gates / folders: `references/gates.md`.

## Pipeline

```
HOMEPAGE · required · / only
SESSION 1 · operator   1.1 → 1.2 → 1.3 → 1.4  → handoff-2.0.md
SESSION 2 · strong     2.1 → 2.2 → 2.3 → 2.4  → handoff-3.0.md
SESSION 3 · operator   3.1 → 3.2 → 3.3 → 3.4

ALL PAGES · optional
SESSION 4 · operator   4.1 → 4.2 → 4.3 → 4.4
SESSION 5 · strong     5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6
```

2.0 and optional 5.0 are recommended on the strong tier. The tier is advice, never a
gate: run any session on whichever model the operator chose, and never stop to ask for a
switch. `mark --step 1.4/2.4 --status done` releases the lease and prints the next prompt. 4.4 opted in prints `qa/handoff-5.0.md`.
Resume with `resume`, never `start`.

**Homepage vs all pages.** Phases **1–3** are the required homepage run (`/` only):
capture at 1600 / 768 / 390 (fast: 1600 / 390), mine one Design Library (fast: none), author `rebuild/index.html` (the one
homepage file), patch it in place at 2.3, polish the same file starting at 3.1. **On a URL run, 3.4 can stop the run.** A Webflow / HTML folder run continues through Phase 4 and stops at 4.4. Phases **4–5** are optional
on a URL run. They reuse those tokens and chrome. They do not recapture `/`,
do not mine a second library, and do not rewrite 2.3 geometry.

- **4.x Paper:** extra sitemap URLs into the same file, desktop only, bind existing tokens.
- **5.x Astro site:** scaffold `astro/` and pull Header / Footer / components once from the 3.4 polish, author each Paper page's `<main>` as `src/pages/{slug}.astro`, clip-QA the built pages (desktop, then live 768/390 — no extra Paper frames), wire routes + SEO, `astro build`. Never replaces `rebuild/`.

## Before each step — read that row, not this file

| Step | Do | Read |
|---|---|---|
| **1.1** | `scrape-web.sh` — URL + images + Latin fonts. Stub contract. Images are the unscaled original, not a srcset `scale-down-to` thumb (Pitfall #243). | `references/step-11.md` |
| **1.2** | Headless `hover-reel/scripts/capture-session.mjs`. First capture `create_file`s one Paper document. A retry reopens `qa/paper-file.json` — do not create a second file. Never `list_files`. Then the run-config widths (1600/768/390; fast 1600/390) + Navigation + stretch-root. | `references/12-desktop-source.md` + `references/stage-p-notes.md` |
| **1.3** | **Fast run: skipped** (intake receipt). Otherwise `run-design-library-step.mjs` once. Foundations only. Then pull unique buttons + components from token-seeded `home-desktop` onto FRAME `Buttons` and FRAME `Components` (compact card, source pixel width; the script refuses a section shell, a width drift, or a row that does not hug), and author button hover from source CSS. | `references/pillars.md` (1.3 rows) + `references/13-buttons-components.md` |
| **1.4** | `checkpoints=auto`: self-accepts, nothing opens, continue to 2.1. Otherwise required Paper sign-off. `mark 1.4 active` opens Paper **and** the browser on the stamped source URL (Capture Tool connects off that tab; `capture-doctor` FAIL = OFFLINE, relay its fix). Optional leftover hover only. Fire the two-option question modal. Stop. | `references/live-board.md` + pillars 1.4 row |
| **2.1** | **Adopted clean HTML: off** (`qa/phase-2-off.json`). Do not emit a Design System page. **Fast run:** `emit_fonts.py .` only. Otherwise `emit-design-system.mjs` writes `rebuild/design-system.html` + `tokens.css` + `fonts.css`. Not the ship. | `references/paper-design-to-code.md` |
| **2.2** | **Adopted clean HTML: off.** Do not copy into `rebuild/` and do not author. Otherwise `get_jsx` → `dump_index_raw.py` → `qa/index-raw.html` (**fast: skip the dump**). `frontend-design` authors `rebuild/index.html` — the one homepage file. Photos are byte-copies of `source-site/assets/` (`bind_source_images.py`). | same |
| **2.3** | **Adopted clean HTML: off.** Otherwise pull numbered 1.2 `NN-slug.png` clips at the run-config widths, side-by-side vs `rebuild/index.html` (patched in place; measure against `qa/index-raw.html`), plus viewport pairs from `paper_23_side_by_side.py` (source left, rebuild right, native scale, every run width; re-run after every patch — the gate refuses a stale `qa/side-by-side/report.json`; `/compare` wraps it at any phase). Measure/APPLY is serial (controller is the only `rebuild/` writer). **No Paper MCP.** Never skip. Then VALIDATE: `paper_23_validate.py . --shoot-open`, **MUST** `wave.py prepare/start/wait/apply` for LOOK, apply printed patches, `--record` from the findings; ≤3 rounds per band, `--residual` from round 2 (`--shoot-open` restamps bands another patch only staled; Pitfall #232). Adapter from the probe: `orca` opens Orca terminals, `subagent` dispatches this harness's subagents, `serial` means the controller does each printed spec. Do not Read the sides yourself on the orca/subagent rungs (Pitfall #216 #221). | same + `references/responsive-22d.md` + `references/section-23-paper-loop.md` + `references/orca-relay.md` |
| **2.4** | **Adopted clean HTML: off.** Do not open TAGS. Continue at 3.1. `checkpoints=auto`: self-accepts once 2.3 is green, continue to 3.1. Otherwise `open-build-review.py . --stage 2.4` (TAGS on). Stop. Continue starts Session 3 polish — the same file, edited in place. | same |
| **3.1** | **Adopted clean HTML:** `mark 3.1 active` snapshots `source-html/` (`qa/source-fidelity.json`). Accessibility attributes only. Do not seed `index-polish.html`. Otherwise `mark --step 3.1 --status active` pins the fidelity freeze (`qa/fidelity-freeze-24.json`) and opens the polish: Impeccable + Taste edit `rebuild/index.html` in place. | `references/polish-visual-restore.md` |
| **3.2** | **Adopted clean HTML:** do not run hover, drawer, FAQ, dropdown, or GSAP authors. Fidelity lock must stay green. Otherwise `mark 3.2 active` writes hover CSS, the painted burger drawer, FAQ accordion, nav dropdowns, and **GSAP in-view** on `rebuild/index.html` (`qa/gsap-reveal-qa.json`). Do not inject GSAP by hand at 3.4 — `open-human-review.py` refreshes that inject (Pitfall #236). Never skip hover, the drawer, FAQ, or dropdowns because Capture Tool did not run. Companion receipts `qa/web-design-guidelines.md` / `qa/find-animation-opportunities.md` / `qa/apple-design.md` before `mark --step 3.2 --status done` (Pitfall #215). | `references/gsap-inview.md` + `references/hover-22c.md` + `references/nav-drawer.md` + `references/faq.md` + `references/nav-dropdown.md` + `references/orca-relay.md` (companion wave) |
| **3.3** | **Adopted clean HTML:** do not retag. Fidelity lock must stay green. Otherwise semantics + scrape-only SEO on `rebuild/index.html` (`--freeze-structure`). | `references/semantics-pass.md` |
| **3.4** | **Adopted clean HTML:** ship stays `source-html/index.html`. Do not promote a polish file. Do not ask. `mark 3.4 done` writes `qa/phase-4-opted.json` and you continue at 4.1. The next stop is 4.4. **URL run:** review `rebuild/index.html` (outlines off; `?qa-outlines=tags` turns them on) plus the polish report. Marking done strips the QA overlay from that same file (`finalize_ship.py`). Two-option: finish (`qa/phase-4-skipped.json`, tidy) or continue to optional Phase 4 (`qa/phase-4-opted.json`, no tidy). If the human asked to move on, `mark 3.4 done --requested` warns on red polish / semantics / fidelity / type and still closes. Do not pass `--requested` unless they asked. | `references/live-board.md` (handoff) |
| **4.1** | Scrape sitemap.xml for extra URLs. Homepage stays out. Near-duplicate dynamic detail slugs (blog posts, case studies — a parent with 3+ children) collapse to ONE sample per template; never import every slug. **Adopted clean HTML:** also writes `qa/source-gaps.json` (empty CMS layouts). | `references/scripts.md` |
| **4.2** | Desktop capture each URL onto the HOME canvas of the 1.2 file — one horizontal row under a single `Ruler · pages` below the existing frames. NEVER `create_page` / a Paper page per URL. | same |
| **4.3** | **Adopted clean HTML:** author the `qa/source-gaps.json` pages from Paper screenshots into `source-html/`, then `source_fidelity.py record-gaps`. Do not bind tokens. Do not rewrite pages the export already has. Otherwise serial bind of existing Design Library tokens. No second library. | same |
| **4.4** | Human review of the extra Paper pages. Two-option: finish (`qa/phase-5-skipped.json`, tidy) or continue to Phase 5 (`qa/phase-5-opted.json`, no tidy). | `references/live-board.md` |
| **5.1** | `scaffold-astro.py` → `extract-astro-components.py` (runs the sitemap reuse plan `shared_sections.py` → `qa/phase-5-reuse.json` and lifts homepage bands repeated on other pages as `{Name}Section.astro`; Pitfall #244) → `convert-astro-home.py`. **Adopted clean HTML:** scaffold from `source-html/`, not `rebuild/`. Do not invent `hover.css`. Otherwise scaffold `astro/` from the 3.4 rebuild CSS / fonts / images / scripts (copied recursively), pull Header + Footer + Paper-backed / comment-nominated components **once** from `index.html` (the finalized ship), convert the homepage to `src/pages/index.astro`. BaseLayout's sheet/script wiring is derived from the ship's own head — each inline `<style>` → its own `public/styles/site*.css`, inline `<script>` → `public/scripts/ship-inline-N.js` (never pasted into the `.astro` template) — and the scaffold receipt fails any referenced asset missing under `public/` (Pitfall #240). `bind_source_images.py` before mark done — rasters stay source originals (Pitfall #243). | `references/phase-5-astro.md` |
| **5.2** | Serial `get_jsx` dumps → re-run `shared_sections.py` → controller **builds each `buildFirst` shared section once** → at most two author workers that import every `byPage[slug]` section and never re-author it, each writing **only** the `<main>` of `astro/src/pages/{slug}.astro` on the 5.1 chrome. Photos from `source-site/assets/` via `bind_source_images.py`, not Paper file-assets. `record-phase-5-pages.py`. | same + `references/orca-relay.md` (page wave) |
| **5.3** | `build-astro-dist.py`, then desktop clip compare of `astro/dist/{slug}/index.html` vs `capture/{slug}-desktop/source-sections/` (1600). | `references/section-23-paper-loop.md` + same |
| **5.4** | Live 768/390 clips, rebuild, then the same compare on `astro/dist`. No extra Paper frames. | same |
| **5.5** | `wire-astro-routes.py`: sitemap paths / labels → routes, per-page scrape-only SEO into frontmatter, `astro build`. Geometry, type, and library classes stay frozen. | `references/phase-5-astro.md` + `references/semantics-pass.md` |
| **5.6** | `open-phase-5-review.py` — review built routes on `file://`, then tidy. Keeps `rebuild/` + `astro/`. | `references/live-board.md` |

Commands and edge cases: `workflow.html`. Public lander is human copy only.

**Do not** `skill_view` this package again mid-run. **Do not** load
`url-to-paper` / `hover-reel` SKILL.md unless you are stuck — their scripts
are enough; the refs above carry the pipeline rules.

## Companion skills (by step)

| When | Skill |
|---|---|
| 2.1 | `url-to-paper` `emit-design-system.mjs` |
| 2.2 / 5.2 | `frontend-design` |
| 2.3 / 5.3 | `pixel-perfect` (one-pass assist; disk-clip gold). Not a refine loop. Not 3.x. |
| **2.3 VALIDATE LOOK** | **MUST** `wave.py` after `--shoot-open`. When the probe says `waves orca`, load `orchestration` + `orca-cli` (stubs; `orca skills get …`) before `wave.py start` (Pitfall #221). |
| 1.2 scripts | `url-to-paper` (scripts only) |
| 1.3 pull | `hover-reel` `pull-desktop-specimens.mjs` then `author-button-hover.mjs` |
| 1.4 optional extension | `hover-reel` Capture Tool |
| 1.2 session + 5.4 | `hover-reel` (scripts / extension) |
| 1.3 tokens | `design-tokens` (folder ≠ 2.1 Author) |
| 3.1 | `impeccable`, `design-taste-frontend` |
| 3.2 | `emil-design-eng`, `find-animation-opportunities`, `apple-design` |
| any step, only when the probe says `orca reachable` | `orchestration` + `orca-cli` (stubs; guide via `orca skills get …`) — 2.3 wave terminals + relay, same-source agent (Pitfall #219 #220 #221) |

Script index: `references/scripts.md`.

## What this skill does not do

No React, no Tailwind CDN, no JSX, no CMS, no analytics, no
local server, no GIFs, no second `rebuild-*` tree, no invented skip-link,
no extra Paper frames that only serve a join. No bundler until optional
Phase 5, which writes `astro/` only.

Deliverable: plain semantic HTML/CSS/JS in `rebuild/` plus a reusable CSS
token system. Optional Phase 5 adds a static Astro app in `astro/` — chrome pulled once, one `.astro` body per page.
