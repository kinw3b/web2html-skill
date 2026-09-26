# Skills source of truth

This repo is **website-to-html**: any live site → Paper → semantic HTML.
Install with `node scripts/npx-install.js` (what `npx github:kinw3b/web2html-skill`
runs), which **symlinks** each package into every agent's skills directory and
installs the skills' npm dependencies. From a checkout it links the checkout;
never `cp`: a copy goes stale the moment you edit. The Capture Tool extension
and its native bridge are NOT installed — they are a separate download
(https://github.com/kinw3b/paper-bridge); `INSTALL_CAPTURE_HOST=1
./scripts/install-skills.sh` opts in. `pipeline-progress.py capture-doctor`
reports a bridge that would show OFFLINE (Pitfall #217).

**Orchestrator version (web2html):** **2.30.0**

This file is the **repo** index. The agent-facing index is `1.0 - web2html/SKILL.md`
(~130 lines). Detail lives in `web2html/references/` and is read **per step**,
not on every turn.

| Need | Read |
|---|---|
| Agent summon + per-step load table | `1.0 - web2html/SKILL.md` (do not page; do not say it is huge) |
| 1.1 light scrape | `web2html/references/step-11.md` |
| Live board / todos / never-reuse | `web2html/references/live-board.md` |
| Script catalog | `web2html/references/scripts.md` |
| Versioned rule for the step you are on (the old Pillar table) | `web2html/references/pillars.md` |
| Fidelity gates, folder contract, documentation contract | `web2html/references/gates.md` |
| Stage P / A/6 / Step 7 / Step 2b working notes + commands | `web2html/references/stage-p-notes.md` |
| Install paths, repo layout, package conventions, glossary | `web2html/references/repo-conventions.md` |
| Findings from real runs | `web2html/references/pitfalls.md` |
| Tight run spine | `web2html/references/stage-spine.md` |
| 1.2 desktop source + authored 768/390 | `web2html/references/12-desktop-source.md` |
| 1.3 pull Buttons + Components from desktop | `web2html/references/13-buttons-components.md` |
| 3.2 painted burger drawer (no Capture Tool) | `web2html/references/nav-drawer.md` |
| 3.2 FAQ accordion (scrape answers, no skip) | `web2html/references/faq.md` |
| 3.2 nav dropdown (scrape submenu, no skip) | `web2html/references/nav-dropdown.md` |
| 1.4 optional Capture Tool (leftover live hover) | `web2html/scripts/watch_agent_ping.py` |
| Model routing, the three sessions, handoff prompts | `web2html/references/model-routing.md` |
| Paper is the 2.2 brief (not a JSX dump); 2.1 Design System page; 2.3 section loop; 2.4 TAGS | `web2html/references/paper-design-to-code.md` |
| Hover if live has it (1.4 + 3.x; not 2.2.c) | `web2html/references/hover-22c.md` |
| 768/390 born in 2.1 + signed in 2.3 (not 2.2.d) | `web2html/references/responsive-22d.md` |
| 3.3 semantics (scrape-only SEO) | `web2html/references/semantics-pass.md` |
| Run order (human surface) | `pipeline.html` |
| Commands, gates, edge cases | `workflow.html` |
| Branching skill encyclopedia | `index.html` |

**Before each step, read that step's accordion on `pipeline.html` and its rows in
`pillars.md`.** Do not act on memory of a rule — the numbers move.

**A run spans three sessions so the model can change per phase.**
`1 capture (1.1–1.4)` → `2 build (2.1–2.4)` → `3 QA (3.1–3.4)` → optional `4 pages (4.1–4.4)` → optional `5 astro site (5.1–5.6)`. **2.0** and optional **5.0**
are recommended on the strong tier: those are the phases that author HTML or Astro bodies no
earlier artifact contains. 1.0, 3.0, and 4.0 are recommended on the operator tier — every
step there either lands on a script that opens the artifacts or stops for a human.
**The tier is advice, never a gate.** No script checks the model; run any session on
whichever model the operator chose and never stop to ask for a switch.
`mark --step 1.4 --status done` and `mark --step 2.4 --status done` release the
controller lease and print a copy-ready prompt for the next session
(`qa/handoff-2.0.md` / `qa/handoff-3.0.md`). **4.4 opted in** prints
`qa/handoff-5.0.md`. **5.6 done** tidies. **A new session resumes with**
`pipeline-progress.py resume . --owner <session>` (optionally `--at <step>`;
omitted, the step is detected from the board) — never `start`,
which force-resets the board.** Detail in `references/model-routing.md`.

**Timing (2.28.0).** Marks are the clock. `mark active` stamps `started`,
`mark done` stamps `ended` + `durationSeconds` and prints the step's duration
plus the run total. The total is the **sum of step durations, never wall clock**
— pauses between sessions add nothing. `start` / `resume` log the session under
`sessions[]`; the board shows finished / took per step, per-phase sums, and the
total in the HUD. `timing <project> [--json]` prints the table. Rule for every
new agent session: `resume` first (it prints where the run sits and the total so
far), then `mark active` before touching the step. Pitfall #227 #228.

**Agent + model (2.28.0).** Each session records who ran it: `resume` /
`start` take `--agent` (defaults to the harness probe) and `--model` (or
`WEB2HTML_MODEL`). `mark active` stamps the step with the recording session's
agent, so a phase that mixed agents still shows each one. The HUD names the
current session; every phase card carries a `duration · agent · model` line.
The Capture Tool block never prints the stamped address — `Copy` and `Open`
appear only while step 1.4 is active and the URL exists. Pitfall #229.

**Run report (2.29.0).** Every `mark done` refreshes `<project>/run-report.md`
— a plain, portable Markdown log of the run for the human to drop into any
database afterwards: sessions with agent + model, per-step and per-phase
durations, each human checkpoint with its status / duration / who ran it, the
Paper review comments captured around 1.4 (with resolved status from the
append-only `qa/paper-comments-log.jsonl`), and free-form notes. Log an
additional request at a checkpoint with
`run_report.py note . --step 2.4 --text "…" --author human`. The report is an
output, never a gate: a failed refresh never fails a mark, and it survives the
end-of-run tidy at the project root.

**Homepage (1–3) vs all pages (4–6).** 1.0–3.0 rebuild `/` only and are required
through 3.4. 4.0–6.0 are optional: Paper the extra URLs, author interiors, then
convert to Astro. They reuse the signed homepage tokens and chrome. They do not
recapture `/`, do not mine a second Design Library, and do not rewrite 2.3 geometry.

The live board marks completed timeline rail segments in lime; pending segments remain muted.

**2.0 is model-authored, and optional 5.0 / 6.0 are too.** Paper is the visual brief, not a JSX dump. Live children: 2.1 Design System → 2.2 Author → 2.3 Validate → 2.4 TAGS. 2.1 emits `rebuild/design-system.html` + tokens from the signed 1.3 library (script, not the ship). 2.2 frontend-design authors `rebuild/index-semantic.html` from Paper desktop using those tokens (aesthetic-risk OFF). 2.3 seeds `rebuild/index.html` from that first pass and validates each section against the 1.2 clips at those three widths plus index-raw. 2.4 is the human TAGS checkpoint and emits the session 3 prompt. 2.0 does not join on capture ids, does not ship get_jsx, and does not add Paper frames that only serve a join. 1.2 scrapes for fidelity and does not stamp pc-path trees as Paper `layer-name`. Hover if live has it is 3.x plus optional Capture Tool leftover hover. Compact chrome parks on FRAME Navigation at 1.2 at **all three widths** (Pitfall #168).

---

## Pipeline order (non-negotiable spine)

```
A → B → C → STOP
```

```text
A — Evidence & capture                                    [SESSION 1 · operator tier]
  A/1 light scrape (URL + images + Latin fonts; auto contract)
  A/4 Stage P page/section capture (1600/768/390 + Navigation at all three)
      + automatic geometry/stretch-root postflight
  B/1 Design Library in Paper — mined off those frames (1.3, HARD STOP)
  A/6 component states (4.0–4.4, OPTIONAL) · A/7 component QA
  A/8 Paper sign-off → emits the SESSION 2 prompt
B — Build from Paper                                       [SESSION 2 · strong tier]
  B/2a tokens from 1.3
  B/2 2.1 Design System / 2.2 author / 2.3 validate / 2.4 TAGS (B/2b get_jsx deleted; B/2b-R folded in)
  B/4 functional QA · 2.4 → emits the SESSION 3 prompt
C — Verify & handoff                                       [SESSION 3 · operator tier]
  C/1 Step 7 QA pass 1 · C/2 Step 7 QA pass 2 · C/3 hover parity + polish
  C/4 docs/handoff
```

Top-level tracker tasks are letters; children are numbers. Keep exactly one
foreground writer active. Reviewer waves are evidence-only: the controller
owns Paper, `rebuild/`, the live board, and canonical QA receipts. During A/7
two read-only QA lenses may run in parallel. 2.3 VALIDATE LOOK is `wave.py`
(adapter from the probe); only the controller writes `rebuild/`.

Display IDs are `1.4` / `2.1` / `2.2` / `2.3` / `2.4` / `3.1`. Cards are two bands
of three: homepage Capture / Build / QA (required), then Pages / Site / Astro
(optional all-pages). Never place 3.x rows inside the Build card. The public `index.html` rail uses each displayed step label
once and keeps each summary to one short overview sentence; commands, gates, and
edge cases belong in `workflow.html`, not duplicated on the lander. Keep generous
vertical space between its top-level step nodes; compact spacing is for nested
branch panels only. Public copy describes the deliverable as plain semantic
HTML/CSS/JS with a reusable CSS token system — never as Tailwind output.
**Phase 1 order is 1.1 contract → 1.2 capture → 1.3 Design Library + pull
Buttons/Components → 1.4 human Paper sign-off, one checkpoint.** Capture Tool
is leftover live hover only (`open-capture`). The Design Library mines the
1.2 Paper frames, then 1.3 fills FRAME `Buttons` and FRAME `Components`.
Do not open 2.4 until every homepage section is Paper-signed.
The final card is exactly: **3.1 QA pass 1** (a11y + contrast + anti-slop),
**3.2 QA pass 2** (1.3 source-CSS button hover via `apply-hover-css.py` + painted burger drawer via `author-nav-drawer.py` + FAQ accordion via `author-faq.py` + nav dropdowns via `author-nav-dropdown.py` + guidelines a11y + mandatory GSAP in-view), **3.3 Semantics + SEO
sweep** (freeze-structure; does not retag signed 2.3 markup or touch hover),
then **3.4 Human checkpoint**. 3.x writes `rebuild/index-polish.html` only
(the 2.4 `index.html` stays the lock; the polish file is created when 3.1
starts, not at 2.4). 3.x must not change font-size, Design
Library class names, or 2.3 geometry (Pitfall #196 #203). 3.2 must inject
GSAP in-view on the polish file and must run `apply-hover-css.py` plus
`author-nav-drawer.py` plus `author-faq.py` plus `author-nav-dropdown.py` (Pitfall #204 #207 #208 #209 #210). Its three companions (`web-design-guidelines`, `find-animation-opportunities`, `apple-design`) each leave `qa/<skill>.md`; no receipt, no 3.2 done (Pitfall #215).

**1.2** is `hover-reel/scripts/capture-session.mjs` — **headless**, and it is a **plain capture**.
The agent does **not** author `home-768` / `home-390`; those frames are captured
through the existing `url-to-paper` capture path like desktop is, then
`breakpoint-shot-qa.mjs` runs one pass against the disk shots
(`references/12-desktop-source.md`). Nothing in 1.0 is model-authored any more.
**Navigation is captured at all three widths, not just desktop.** Serializer
chrome (`00-header` / `00-nav`) parks on FRAME `Navigation` as
`01 · nav-1600` / `02 · nav-768` / `03 · nav-390`, each serialized at its own
viewport so the compact/burger variant is real paint and not a guess. That
board already holds the compact and burger paint, so Capture Tool is leftover
hover only. If desktop is missing that
navbar, port the same compact stack onto the lander — never the live Framer
page/hero shell (Pitfall #110). Opens no browser window and mounts no in-page
HUD; there is no navbar picker at 1.2 (Pitfall #121).
Source-section clips are taken at `scale: "css"` and every `Screenshots`
row is capped at **1600** so that board matches `home-desktop` (Pitfall
#119). 768 / 390 clips stay on disk — they are not a second Screenshots
board (Pitfall #71). Collect seeds FRAME `Buttons` (legacy `Hover States`),
`Components`, and `Navigation` after desktop exists. Captured 768 / 390 then
sit between desktop and those review frames.

**1.3** is the **Design Library**, then the **Buttons / Components pull**. It
runs immediately after 1.2 and mines the Paper frames the capture just wrote —
landers at 1600 / 768 / 390 plus FRAME `Navigation`. One inventory, one mine,
exactly one foundations-only `Design Library`, one canonical token set, bind
without moving geometry. After seed QA is green, the agent walks every `NN ·`
section on token-seeded `home-desktop`, writes `qa/buttons-components-plan.json`,
and runs `pull-desktop-specimens.mjs` so unique CTAs land on FRAME `Buttons`
and unique cards/snippets land on FRAME `Components`. Each parked row sits on a neutral grey stage (`#6F6F6F`) so transparent specimens and white type stay visible (Pitfall #222). The row hugs the specimen at its source pixel width — never a 1600px slot, never `width: fit-content` on the copy — then restacks by section `NN`, and Components clears the measured Buttons edge by 160px (Pitfall #230). The pull then authors
button hover from source CSS `:hover` onto those Buttons rows
(`qa/button-hover.json`). Receipts `qa/buttons-components-pull.json` and
`qa/button-hover.json` are required to mark 1.3 done. Detail in
`references/13-buttons-components.md`. Pitfall #205 #207 #222.

**1.4** is the single **human Paper checkpoint**. First action is
`pipeline-progress.py mark <project> --step 1.4 --status active`, which writes
`qa/paper-human-review.md` if missing, **opens Paper**, runs `capture-doctor`,
and **opens the browser on the source URL stamped with `paperFileId` +
`projectRoot`** so the Capture Tool side panel connects (Pitfall #217). Stop. Last action is
the **two-option question modal**: walk 1600 / 768 / 390, FRAME `Navigation`,
FRAME `Buttons`, FRAME `Components`, and Design Library; pin comments on
anything wrong. Choices: **Done & continue to next step** (mark 1.4 done and
continue into 2.1 here) and **Provide hand-off prompt to start fresh session**
(`handoff`; do not start 2.1). No HTML until they sign off. **Marking 1.4 done**
requires `qa/paper-human-review.md`; it releases the controller lease and prints
the SESSION 2 prompt (`qa/handoff-2.0.md`). Capture Tool is leftover live hover
only — the tab is opened by `mark 1.4 active`; `open-capture` re-opens it and
`capture-doctor` checks the native bridge — not a 1.4 done-gate. Do not rename
Paper from pc-ids. Semantic tags come from the 1.2 `layer-ids.json` census.

**The intent is that Capture Tool becomes unnecessary.** 1.3 already fills
Buttons and Components from desktop. Treat a run that needed the extension as
a signal to improve 1.2 / 1.3, not as the norm.

**Responsive Navbar capture is a 1.2 job, not a 1.4 job.** The confirmed desktop
Navbar fingerprints two further captures at 768 and 390; each responsive match
parks on FRAME `Navigation` automatically and rejects full-page/hero shells. At
768 / 390 the capture opens a sized context, waits until the page is actually
that width, then rematches the compact logo + menu / Framer `Phone`·`Tablet`
bar (Pitfall #121). All three takes land before 1.3 mines the library, so the
compact and burger paint are in the token census. The same fingerprint rules
below apply whether the match is made by 1.2 automatically or by a human in the
optional 1.4 extension — 1.2 is the default path and 1.4 is the fallback. Green checks must always be backed by Paper
node receipts. Manual Navbar targeting begins on the exact DOM node; only
explicit ↑/↓ traversal or Auto may promote it to a wrapper. Navbar Auto must
climb a bounded ancestor set and accept only a compact parent containing logo
+ navigation links/CTA/dropdown, or logo + menu control at responsive widths.
Missing `nav`/`header`/named-logo attributes are not a miss: seed from those
children and pick the smallest compact parent. Skip `html`/`body`/`main` and
oversized header/section shells (Pitfall #120). Announcement strips and
hero/page shells never qualify. Confirmed-take
wrappers must hug their serialized states (`width` / `height: fit-content`),
never carry a fixed board width. Exact component serialization starts at that
selected root. Never add a `capture-context`, sampled-background shell, or
presentation padding around a take; resolve referenced SVG symbols and retain
real border/outline paint. The Navbar gate may disable Continue only with
visible Desktop / Tablet / Mobile status, a loader during active work, an
exact Paper-confirmation count, and a retry state. Keep that progress card
hidden until the human has captured the desktop Navbar; then reveal it while
desktop, tablet, and mobile reach Paper. It unlocks automatically when all
three receipts reach Paper.
1.2 does not mutate layer names. Keep the scrape / HTML name or let Paper
name the layer. `layer-ids.json` / `paper-layer-ids.json` are optional and
invisible — never required, never written onto frames. There is no Tags Scan
step. 2.0 must not stamp, join, or retag on those ids.

---

## Hard rules

1. **Never skip a numbered step** (1.1 → 3.4). **Run intake first (2.24.0):**
 `mark 1.1 active` refuses until `run_config.py intake` has recorded the three
 questions (live URL, or Webflow / HTML source — then the folder path — then full or fast?) in
 `qa/run-config.json`. With `--checkpoints auto` (forced by `--speed fast`) 1.4 and
 2.4 self-accept — receipts stamped AUTO-ACCEPTED, nothing opened, same session
 continues. **3.4 is never automatic on a URL run.** A Webflow / HTML folder run
 does not stop at 3.4: Phase 4 is required and the stop is 4.4. A fast run marks 1.3 / 2.1 done on the
 intake's skip receipts (no Design Library, `emit_fonts.py` only), authors 2.2
 without `index-raw.html` or a token contract, and captures / validates at
 1600 / 390 (every 2.3 gate reads widths from the config). Otherwise 1.4's
 Paper-review, the 2.4 TAGS checkpoint, polish and 3.4 are not optional. **Capture Tool is
 leftover live hover** — `mark 1.4 active` opens the stamped tab;
 `open-capture` re-opens it. It is not a 1.4 done-gate.
 **Phase 4 is optional after 3.4 on a URL run** — write `qa/phase-4-opted.json` or
 `qa/phase-4-skipped.json` before marking 3.4 done. **On a Webflow / HTML folder run Phase 4 is required** — do not ask, and `mark 3.4 done` writes `qa/phase-4-opted.json`. **Phase 5 is optional after 4.4**
 — write `qa/phase-5-opted.json` or `qa/phase-5-skipped.json` before marking 4.4
 done. `skip` fails on 1.1–3.4 and is allowed on 5.x after that phase's opt-in;
 on 4.x it is allowed only on a URL run after Phase 4 opt-in and is refused
 outright on a Webflow / HTML folder run (Phase 4 is required there). `mark`
 cannot open 2.1+ while 1.1–1.4 are unfinished, 4.x while Phase 4 is closed, or
 5.x while Phase 5 is closed. If blocked, stay on that step and stop.
 Pitfall #98 #148.
2. **Stage L is never skippable on a full run.** No `rebuild/*.html` until Paper has a
 `Design Library` artboard (foundations only), `get_tokens` is non-empty,
   the 1.2 geometry postflight passed, and `design-library/library.json` exists on disk. Disk-only
   does not count. If Paper MCP is down, stop the run.
 **The Design Library does not exist before 1.3.** P-0 creates only
 `Ruler · desktop`. **1.3 runs as soon as 1.2 has written its frames** — the
   landers at 1600 / 768 / 390 and FRAME `Navigation` at all three widths. It no
   longer waits on the extension. 1.3 mines every eligible frame once, creates
   `Design Library` once, replaces Paper tokens with one canonical set, and binds
   exact matches back without changing geometry. If 1.4 later adds hover or
   component frames, re-run the bind over the new frames only — never a second
   `Design Library`. Opaque brand fills and alpha tints of the
   same RGB stay separate (`--color-accent` vs `--color-accent-soft`; Pitfall
   #154). A re-run restores collapsed fills from capture HTML only when Paper
   already has a fill — never paint a frame 1.2 left unpainted, and never snap
   a near hue onto it (Pitfall #157). The foundations sheet always floors at least
   five Tailwind semantic colors, `--text-xs`…`--text-12xl` large → small with
   `Aa` in the primary sans, and a 4-up colour grid. Desktop mines line-height as
   `--line-height-{n}` (%) and letter-spacing as `--letter-spacing-*` (rem) onto
   the type sheet (Paper types `lineHeight` / `letterSpacing`). Bind exact
   converted matches back onto landers / Navigation / components; unmatched
   measurements stay literals. Semantic colour bars are
   always 15px high so they remain subordinate to 104px mined brand swatches.
   Every foundations render upserts all Paper-supported proposed tokens into the
   Theme panel before painting; a complete sheet with stale/missing Paper tokens
   is a failure. Shadows and font styles remain CSS-only because Paper has no
   matching token type. Pitfall #66.
   **Never run `flatten-paper-buttons.mjs`.** 1.2 keeps scrape / Paper names;
   collapsing wrapper chains after import has merged nav CTAs and section grids.
   1.3 is mine + tokens, then pull Buttons/Components from desktop.
   Pitfall #131. After bind, pair each 1600 / 768 / 390 source-section clip with that
   named Paper band and rebind until color, type, and layout hold
   (`qa/library-seed-qa.json`). Missing any clip dir fails 1.3. Extra saturation
   vs a quiet source clip is `color-spill` and fails with no retry (Pitfall #157).
   This is not 1.4. Pitfall #156.
3. **Never import more than one page into Paper during 1.2.** Default is `/`.
 Extra routes stay out of capture unless `--allow-multi-page` is explicit.
 Exit if `plan.pages.length > 1` at 1.2. 1600 / 768 / 390 are viewports, not
 pages. Homepage only until 3.4. Optional Phase 4 imports remaining sitemap
 URLs as desktop Paper pages in the same file. Optional Phase 5 binds the
 site into `astro/` after 4.4 opt-in: 5.1 pulls Header / Footer / components
 once from the 3.4 polish, 5.2 authors only each page's `<main>` as
 `astro/src/pages/{slug}.astro`. **5.5 is the one post-3.4 href exception**
 (Astro routes across `astro/src`), plus 3.3-style scrape-only SEO per page.
4. **Never list a required viewport and then allow-drift skipping its capture.**
5. **No Components artboard.** Design Library = foundations only.
6. **First `index-semantic.html` = 2.2 frontend-design** of the QA-passed homepage.
   2.3 seeds `rebuild/index.html` from that file (never overwrite) and is the
   only writer of the lock. Never freehand, never a scrape-to-site rewrite, never a broken frame,
   never React / Tailwind CDN, never a `get_jsx` dump — the dump is not even
   a lock assistant. Pitfall #109 #148 #206.
7. **2.3 before 2.4** — walk each homepage section against the 1.2 clips
   at 1600 / 768 / 390 plus `index-raw.html`. Real tablet + phone CSS, not
   a `width:100% !important` hack. After APPLY, VALIDATE: `--shoot-open`,
   then **MUST** `wave.py prepare/start/wait/apply` for LOOK, then apply
   patches and `--record` from the findings; ≤3 rounds per band, then a
   residual line (Pitfall #216 #221). Do not open 2.4 while a section is open.
8. **One `rebuild/`.** The 2.4 lock is `rebuild/index.html` until 3.4.
   3.x writes `rebuild/index-polish.html` (seeded when 3.1 goes active, not at
   2.4 done). **Marking 3.4 done** promotes that file to `index.html`, moves
   `index-raw.html`, `index-semantic.html`, and the 2.4 lock into
   `rebuild/archive/`, and stamps outlines off (`?qa-outlines=tags` turns them
   on). Extra `rebuild-semantic/` trees fail `verify-rebuild-trees.py`.
   Pitfall #223.
9. **Never start a local HTTP server.** Do not open Chrome on
   `rebuild/index.html` at 2.1. After the 2.3 loop and overlay, **2.4 must
   open** the checkpoint via `open-build-review.py . --stage 2.4`
   (`?qa-outlines=tags`, TAGS on by default) and wait for human approval.
   Pitfall #133.
10. Never copy skill trees into agent folders — only `ln -s`.
11. **Kill a silent shell.** If a pipeline command prints nothing for 20s
    (especially 1.3 `run-design-library-step.mjs`), kill the PID and rerun
    once with live logs. Do not wait 2–3 minutes on silence. Pitfall #112.
12. **Build comments are an autonomous remediation loop.** At 2.1 and after
    the 2.4 checkpoint, run `list-paper-comments.mjs`. If threads
    are open, apply every fix on the canvas and the matching build, resolve
    the thread only after the fix lands, and re-run until exit 0. Do not stop
    to ask whether to fix a pinned problem. Every snapshot also appends to
    `qa/paper-comments-log.jsonl`, which feeds the run report. Pitfall #132.
13. **2.0 does not join on capture ids.** The dump-era join scripts are deleted
    (2.10.0) — there is nothing left to run. 1.2 does not stamp pc-path trees as
    Paper `layer-name`. Sidecars are optional.
14. **2.3 is per-section against disk gold.** Controller lists ship bands
    from `rebuild/index.html`, runs `paper_23_disk_gold.py` +
    `paper_23_clip_compare.py`, and measures each band against the numbered
    1.2 `NN-slug.png` clips at 1600 / 768 / 390 plus `index-raw.html`.
    Measure/APPLY is serial. VALIDATE LOOK **MUST** run `wave.py` after
    `--shoot-open` (adapter from the probe: `orca` / `subagent` / `serial`).
    **No Paper MCP at 2.3** (Pitfall #202). Controller is the only
    `rebuild/` writer. Pixel-perfect is a **one-pass assist** (layout,
    type, geometry, icons, radius, imagery, absolute overlays, 2.2
    hallucinations) — not a refine loop. Pitfall #195 #221. `section_22_gate.py`
    green. `mark --step 2.3 --status done` and 2.4 `open-build-review.py`
    fail while a section is open or a 2.3 wave is missing.
15. **Hover is 1.3 source CSS + 3.2 CSS, not a 2.2 letter.** After the 1.3
    Buttons pull, `author-button-hover.mjs` parks a hover cell from source
    CSS `:hover` paint (not Capture Tool). **3.2** runs `apply-hover-css.py`
    so `rebuild/css/hover.css` is linked on `index-polish.html`. Do not skip
    because Capture Tool did not run (Pitfall #207). Invent hover CSS only
    when 1.3 found no source paint. Pitfall #152. **If a hamburger is
    painted, 3.2 authors the open drawer** (`author-nav-drawer.py`) from
    the same desktop links stacked. Do not skip for a missing Capture
    Tool pair (Pitfall #208). **If FAQ rows are painted, 3.2 authors the
    accordion** (`author-faq.py`) and fills empty answers from the scrape.
    Do not skip because Paper signed empty bodies (Pitfall #209). **If a
    nav dropdown is painted or the scrape has a matching submenu, 3.2
    authors the panel** (`author-nav-dropdown.py`). Do not skip for
    Capture Tool / `--allow-dropdown` (Pitfall #210). **GSAP in-view is
    mandatory at 3.2** on `index-polish.html`. Never skip because 1.4 did not
    record motion (Pitfall #204).
16. **Paper is the brief, not a JSX dump.** 2.1 authors the page. Do not
    extract inline from a get_jsx soup or treat the dump as a lock assistant.
    Pitfall #109.
17. **Do not add Paper frames that only serve a join.** No dump artboards,
    pc-id annotation layers, or emit-only Interactive copies.
18. **Reviewer-wave provenance is not a gate.** Reviewers may write only
    schema-validated findings under `qa/agent-findings/` from a hashed input
    snapshot. They never mutate Paper, `rebuild/`, `design-library/`, progress,
    or canonical `qa/` receipts. `sync` ignores their files; only the controller
    may run a fresh official gate. No active reviewer lease may remain at 3.4.
19. **No pipeline bypass.** First tool of a **new run** is
    `orca_workspace.py ensure <slug>` — it creates the run's single primary
    workspace folder (an Orca project / folder context when the Orca CLI is
    reachable, a plain folder otherwise; reused on every later call, never a
    second worktree) — then `pipeline-progress.py start <RUN ROOT>` on the
    printed path; the session continues on that root. `start` registers the
    folder in Orca itself if ensure was skipped. First tool of a **continued session** (2 or 3)
    is `pipeline-progress.py resume . --at <step> --owner <session>` — `start`
    force-resets the board and would throw the run away. Do not
    scrape-to-site, Firecrawl-to-HTML, or write `rebuild/*.html` before 1.4 is
    done and 2.1 is open. Run `rebuild_write_gate.py` before any ship HTML.
    `start` quarantines leftover `rebuild/index.html`. If you already wrote a
    freehand page, leave the quarantine in place and restart from 1.1. Do not
    polish it. Pitfall #148.
20. **Gate evidence must be truthful.** Ship markup cannot retain raw
    `get_jsx-inline-styles` metadata or invalid block content inside `<p>`.
    2.3 receipts must sign real homepage sections at 1600 / 768 / 390.
    Missing or reconstructed evidence keeps 2.1 / 2.3 red.
21. **Orca is an accelerator, never a dependency.** `start` / `resume` print a
    probe line (`harness_probe.py`). **2.3 VALIDATE LOOK always runs `wave.py`**
    (Pitfall #221). `orca reachable` is the adapter that opens Orca terminals
    of the **same agent**; `subagent` / `serial` still write the same finding
    files. 3.2 / 5.2 waves and a mid-session **relay** (`pipeline-progress.py
    relay` when `mark` prints `RELAY armed`) stay optional. Absent Orca, 2.3
    still calls `wave.py` and nothing asks. Workers and relay terminals run the
    **same agent** as the orchestrator that summoned `/web2html`, never a
    hardcoded one; `--model` is never passed. A relay is a change of agent at a
    receipt boundary, not a human stop: no CTA. Recipe `references/orca-relay.md`.
    Pitfall #218 #219 #220 #221.

### Hard stops (the run pauses for a human)

| Stop | Condition |
|---|---|
| **1.4 / A/8** | After 1.3. `mark --step 1.4 --status active` writes `qa/paper-human-review.md` if missing, **opens Paper**, and **opens the browser on the stamped source URL** (`capture-doctor` first; Pitfall #217). **Stop**. Last action is the **two-option question modal**: walk 1600 / 768 / 390, FRAME `Navigation`, FRAME `Buttons`, FRAME `Components`, Design Library; pin comments on anything wrong. Choices: **Done & continue to next step** (mark 1.4 done and continue into 2.1 here) and **Provide hand-off prompt to start fresh session** (`pipeline-progress.py handoff`; do not start 2.1). No HTML until they sign off. **Marking 1.4 done requires `qa/paper-human-review.md`**; it releases the controller lease and prints the SESSION 2 prompt (`qa/handoff-2.0.md`). Capture Tool is leftover live hover only (tab already open; `open-capture` re-opens). Pitfall #149 #217. |
| **1.2 postflight / A/5-R** | After the 1600 / 768 / 390 landers land, `run-geometry-postflight.mjs` runs `stretch-root.mjs --prove --artboard home-desktop` only. Fail 1.2 if stretch fails. Do not run `qa-paper` or `merge-split-headings` in this postflight (merge-after-census breaks `pc-#`). Evidence in `qa/stretch-root-evidence.md`. Failure keeps 1.2 open. Do not open Capture Tool until stretch is green. |
| **2.3** | Agent loop — disk clips + index-raw at 1600 / 768 / 390. VALIDATE LOOK is `wave.py` (adapter from the probe). No Paper MCP. Pixel-perfect is a one-pass assist, not a loop. `section_22_gate.py` green. Not a human stop. |
| **2.4** | After overlay inject, run `open-build-review.py . --stage 2.4`. Chrome must open with TAGS on and write `qa/build-checkpoint-opened.json`. Stop for review. Write `qa/build-checkpoint.md` only after approval. No 3.x before sign-off. **Marking 2.4 done releases the lease and prints the SESSION 3 prompt** (`qa/handoff-3.0.md`). Continue starts 3.0 polish at 3.1. `index-polish.html` is created then, not at 2.4. |
| **3.4 / C/4** | **URL run:** compare `rebuild/index.html` (2.4 lock) with `rebuild/index-polish.html` (3.1–3.3, outlines off; `?qa-outlines=` toggles) plus the polish report. Two-option: finish (`qa/phase-4-skipped.json`, tidy) or continue to optional Phase 4 (`qa/phase-4-opted.json`, no tidy). **Marking 3.4 done** promotes polish to `index.html` and archives the other homepage HTML under `rebuild/archive/` (Pitfall #223). **Webflow / HTML folder:** do not ask. Ship stays `source-html/index.html`. `mark 3.4 done` writes `qa/phase-4-opted.json` and the run continues through 4.4 (Pitfall #225). Do not write `NEXT.html`. Never tidy mid-flow (Pitfall #151 #203). |
| **4.4** | Review extra Paper pages. Two-option: finish (`qa/phase-5-skipped.json`, tidy) or continue to optional Phase 5 (`qa/phase-5-opted.json`, no tidy). Marking 4.4 done without one of those receipts fails. |
| **5.6** | Review the built Astro routes (`open-phase-5-review.py`, `file://` on `astro/dist`). Marking 5.6 done without `qa/phase-5-review.md` fails; done tidies and keeps `rebuild/` + `astro/` + finished `pipeline.html`. |
| **Stop-at-every-level** | Only when asked: write `qa/runs/<run-id>/STOP-<stage>.md` after A/1, A/2, A/4, A/8, B/1, B/2a, B/2b, B/4, C/1. |

### Live board

Invoke `/web2html` or `Convert <URL> to HTML`. Instant first action of a **new
run**: `orca_workspace.py ensure <slug>` (one primary workspace folder — an Orca
project when the CLI is reachable, plain otherwise; never a second worktree),
then `pipeline-progress.py start <RUN ROOT>` — it writes **and opens**
that folder's `pipeline.html`. A **continued session** uses
`pipeline-progress.py resume <project> --at <step> --owner <session>`, which
opens the same board without resetting it. If the board does not open, **stop**. Print the `file://`
URI. Never overwrite `web2html/pipeline.html`. `start` quarantines leftover
`rebuild/*.html`. Do not write ship HTML until `rebuild_write_gate.py` is
green. Stamp `mark --step 1.2 --status active` before work. Todos use 1.1 … 3.4.

---

## Folder contract (projects)

```
capture/   design-library/   source-site/   rebuild/   astro/   qa/
```

Tokens land in **`rebuild/css/tokens.css`**. Never `site/` or `v1/` as ship
paths. Optional Phase 5 adds `astro/`. Per-folder detail is in `web2html/references/gates.md`.

## Documentation contract (MANDATORY on every skill fix)

You edit the skill package. Update a **doc surface only when that surface's
role changed**. Do not restamp files that still match.

| File | Role | Touch when |
|---|---|---|
| `web2html/pipeline.json` | Single source of truth (step ids, tiers, references, orchestrator version) | A step, tier, reference wiring, or the orchestrator version changed — `web2html/scripts/lint-docs.py` fails any surface that drifts from it |
| `AGENTS.md` or `web2html/references/*.md` | Agent rules | A version, gate, or hard rule changed |
| `pipeline.html` | Run order | Step IDs, cards, or order changed |
| `workflow.html` | Commands, gates, edge cases | A command or gate copy changed |
| `index.html` | Public lander one-liners | A public step label or overview sentence changed |

`README.md` (repo root and `1.0 - web2html/README.md`) is a pointer at those
four. It carries no versions, stage numbers, skill lists, or pipeline rules.
**Never edit it for a skill fix.**

```text
[ ] Edited the skill package in this checkout (SKILL.md and/or scripts)
[ ] Updated web2html/pipeline.json if a step, tier, reference, or version changed
[ ] Updated AGENTS.md or the matching web2html/references/*.md if agent rules changed
[ ] Updated pipeline.html if the run order changed
[ ] Updated workflow.html if commands / gates / edge cases changed
[ ] Updated index.html if public lander copy changed
[ ] ./scripts/sync-from-agents.sh
[ ] ./scripts/test-all.sh   (every suite + check-skill-artifacts; same as `npm test`)
[ ] git commit + push origin main
```

Skipping a surface **that actually changed** is a **process failure** — that is
how map drift happens. Touching a surface that did not change is also a failure.

## Installed names are never numbered

Folders here carry a stage prefix (`1.2 url-to-paper`) so the pipeline order is
visible when browsing. **That prefix exists only here.** The installed directory
name *is* the skill identifier; a space or digit breaks discovery and every
symlink. `scripts/install-skills.sh` strips it.

## Sync

```bash
./scripts/sync-from-agents.sh      # agents → this repo
./scripts/check-skill-artifacts.sh # claimed scripts must exist
./scripts/test-all.sh              # all three suites + artifact check (also `npm test`)
git config core.hooksPath .githooks # once per clone: test-all runs before every push
```
