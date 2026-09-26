# Stage spine (quick load)

`SKILL.md` is the index. This file is the tight run order. Per-step detail
is the table in `SKILL.md` — read **one** reference, then act. Do not page
`SKILL.md`.

## Order

First action of a **new run**: `pipeline-progress.py start <template-project>` — the script writes and opens that folder's `pipeline.html`. First action of a **continued session (2 or 3)**: `pipeline-progress.py resume <project> --at <step> --owner <session>` — same board, never reset. `start` on a run in flight throws the run away. If the tab does not open, **stop**. Invoke `/web2html` / `Convert <URL> to HTML`. Before each step, read that step's **Findings to watch**. They are built-in, not optional. Caught = gate. Watch = you.
Never overwrite the repository `pipeline.html`.
Never skip a child (1.1 → 3.4). `skip` fails on required steps. Phase 4 is optional after 3.4 on a URL run. On a Webflow / HTML folder run Phase 4 is required through 4.4 (Pitfall #225). Phase 5 is optional after 4.4. A get_jsx dump is not a finished run (Pitfall #98).
Do not write `rebuild/*.html` from a scrape or from memory. `rebuild_write_gate.py` is red until 1.4 is signed off. First allowed write is 2.1. Leftover ship HTML is quarantined (Pitfall #148).
Stamp `mark --step <id> --status active|done` at every boundary. Every step marks the live board; a frozen board is Pitfall #96.
Todos use these same IDs.
The live board's dependency cards and scrolling timeline use the same stamps. Timeline rows read `✓ COMPLETE`, `IN PROGRESS`, or `UP NEXT`. Done rows stay full contrast (never muted), keep the landing-page step icons, and turn their left rail segment lime. Dependency cards may overlap: URL (`1.1`), Evidence (`1.1`–`1.3`), Paper (`1.2`–`1.4`), Static site (`2.1`–`2.4` including `2.2`), and QA proof (`3.1`–`3.4`). A card stays active from its first started milestone until all of its milestones are done.


`1.0 → 2.0 → 3.0 → 3.4 → STOP or optional 4.0 → STOP or optional 5.0 (Astro site)`

**Homepage vs all pages.** `1.0 → 3.4` is the required homepage run (`/`).
`4.0–5.0` are optional all-pages phases that start only after 3.4 opt-in. They
reuse the signed library and chrome; they do not recapture `/` or mine a second
library. 4.x is Paper-only. 5.x binds the site into `astro/`: Header / Footer /
components pulled once from the 3.4 polish, then one `.astro` body per Paper
page. It never replaces `rebuild/`.

Display ids as `1.4` / `2.1` / `2.2` / `2.3` / `2.4`, not `2.2.a` or `B/2b`.

```text
SESSION 1 · operator tier
1.0 Design: 1.1 light scrape (URL + images + Latin fonts);
    1.2 capture homepage 1600/768/390 + Navigation at all three (plain capture,
        nothing authored) + geometry QA (clip-content FAIL);
    1.3 Design Library + tokens, then pull unique buttons/components from desktop;
    1.4 human Paper review HARD STOP → emits the SESSION 2 prompt.
        Capture Tool is leftover live hover only (`open-capture`).
SESSION 2 · strong tier
2.0 Build: 2.1 Design System;
    2.2 Author;
    2.3 Validate;
    2.4 TAGS → emits the SESSION 3 prompt.
SESSION 3 · operator tier
3.x after 2.4; 1.3 source-CSS hover at 3.2; 3.3 SEO scrape-only.
Optional 4.x after 3.4: sitemap → desktop Paper pages → seed tokens → review.
Optional 5.x after 4.4: scaffold Astro + shared chrome → author page bodies → desktop QA on dist → live 768/390 → wire routes + SEO + build → review (tidy).
CMS is parked in archive/ — not this pipeline
```

**Sessions and handoffs.** 2.0 and optional 5.0 are recommended on the strong tier;
the tier is advice, never a gate — any model may run any session. `mark --step 1.4
--status done` and `mark --step 2.4 --status done` release the controller lease
and print a copy-ready prompt for the next session. 4.4 opted in prints
`qa/handoff-5.0.md`. Detail in
`references/model-routing.md`.

Live board IDs for Design stay `1.1`–`1.4` — now (contract, capture + Navigation, Design Library + Buttons/Components pull, human Paper sign-off). 1.2 does not stamp pc-path trees as Paper `layer-name`. Sidecars are optional and invisible. Geometry QA (clip-content FAIL) is the 1.2 postflight. 2.0 children are `2.1` / `2.2` / `2.3` / `2.4`. Internal capture ids stay capture-side only.

- **A/1** = light scrape. One script (`scrape-web.sh`) curls the URL,
  parallel-downloads images + Latin fonts, and writes a stub
  `qa/fidelity-contract.md`. **Default and hard cap: 1 page (`/`)**.
  Extra sitemap routes do not enter Paper. Do not import `/contact`,
  `/features`, `/pricing`, `/blog` unless the user named those routes
  **and** passed `--allow-multi-page`. Default `--max` / `--max-pages` is
  1. **Exit** if `plan.pages.length > 1` without the flag. Never ask to
  approve a page count. Do not author a long contract. Do not self-host
  fonts into `rebuild/` at 1.1.
  `web-responsive` default viewports: 390×844, 768×1024, 1280×800, 1600 (or
  1920). **768 and 390 are required Stage P captures.** Required viewport ⇒
  Paper capture — never allow-drift “mobile DOM not re-captured.” Listing
  768 as sanity-only while the live tablet layout differs fails A/4.
- **A/2 / A/3** = folded into 1.1. Images are a cache for 1.2
  `localize-html-images.mjs` (which downloads any remaining live images).
  Latin `U+0000-00FF` woff2 only — not every unicode-range subset
  (Pitfall #185). Font self-host is 2.1. Extra sitemap routes do not expand
  a homepage-only contract.
- **A/6 (4.0-4.4) / 1.4 leftover** = Chrome **Capture Tool extension** + native
  bridge. **OPTIONAL leftover live hover** — 1.3 already filled FRAME `Buttons`
  and FRAME `Components` from token-seeded desktop. Run `open-capture` only when
  the live site has hover pairs 1.2/1.3 could not serialize. `mark --step 1.4
  --status active` opens **Paper and the browser on the stamped source URL**
  (`capture-doctor` first, Pitfall #217); `open-capture` re-opens that tab. Write `qa/paper-human-review.md`,
  then fire the 1.4 question modal: walk 1600 / 768 / 390, FRAME `Navigation`,
  FRAME `Buttons`, FRAME `Components`, Design Library; pin comments. Choices:
  **Done & continue to next step** or **Provide hand-off prompt to start fresh
  session**. The library already exists from **1.3**; if Capture Tool added
  frames, re-run the bind over those frames only — never a second `Design
  Library`. The **Paper sign-off of 1.4** emits the session 2 prompt once
  `qa/paper-human-review.md` exists. Pairs land in
  `source-site/components/<page>/<kind>/` (`nav/ buttons/ forms/ footer/` —
  state HTML + per-kind `manifest.json`). It
  runs **after Stage P has pulled every contract page and section**, sequentially
  in the foreground. Closing Chrome without Done is still 1.4 (Pitfall #102).
  C/3 still reads these states.
  **No GIFs** — default/hover state pairs. 4.0 skips floating chrome · 4.1 navbar
  · 4.2 buttons/CTAs/icon links · **4.3** `--kind forms` only · 4.4 footer links.
  Do not hunt accordions (`--allow-faq` only if the human named one).
  Homepage-only: `--pages home` **and** `--expected-pages home` (leftover
  first-run folders ignored). Transparent light-text roots get the nearest
  painted ancestor on the Slot/root (Pitfall #27). 4.1 / 4.4 serialize **links**
  (not the navbar or footer block). 4.2 walks Stage P sections; same CTA
  label in two sections is two components. New visual patterns get new
  tokens (`pill`, `text-link`); repeats share a name (Pitfall #57).
  Slots `height: fit-content` + post-write QA (Pitfall #28). Ancestor-color
  Slot hugs the control with 24px padding (Pitfall #38). **P-0 rulers
  first** (Pitfall #37): `Ruler · desktop` before any A/6 frame. Kinds are
  sections of `A/6 · {page} · states`; other review frames park in a
  horizontal row under that line (Pitfall #39). Navbar dropdowns
  (`--allow-dropdown`) and 768/390 click burgers own FRAME
  `Interactive components` — not A/6. Capture dropdowns at 1600, not 1440.
  Burgers: `02 · nav-mobile-768` / `03 · nav-mobile-390`. FAQ stays on A/6.
  Do not hunt dropdowns. generate → token-pass (Pitfalls #65 #67).
  **Native hover paint (Pitfall #56):** flatten abs stroke/gradient overlays
  to parent `border` / `background-image`; collapse duplicate text-swap
  labels. A/7 fails leftovers.
  **Visible Chrome** (Pitfall #30): live `whileHover` is not CSS `:hover`;
  `--headless` is CI-only. Pin the live hover fill.
  **Human hover unwrap** (Pitfall #100): `fe()` returns `{ status, html }`.
  Never `String()` that object onto disk or Paper.
  **Desktop section names** (Pitfalls #34 #41): home-desktop layers are
  `01 · slug` (the name is the comment; no legend artboard).
  A/6 labels `{id} · control`. Repeating lists capture one representative.
- **1.2 / A/4 (P)** = live **pre-pesticide** inventory first
  (`pre-pesticide.mjs` → `pre-pesticide.json`; HUD `x-paper-prepesticide`),
  then per-section SOURCE clips at 1600 / 768 / 390
  (`capture/home-{desktop,768,390}/source-sections/01-slug.png`; headless collect
  hides overlays; pre-pesticide CLI keeps pesticide on;
  **review sequence** `01` = hero + nav, then hover;
  `Screenshots` board is 1600 only at 50% opacity; never a full-page source shot — Pitfall #71 / #188),
  then `url-to-paper` in one **hidden** Chrome, single agent — 1.2 opens no
  window and mounts no in-page HUD (Pitfall #121).
  Write `capture/<page>/fullpage.png`. Do **not** import a Paper source-screenshot
  artboard unless a person asks. If nav is missing from layers, rebuild chrome
  from the disk PNG + live site. A live **fixed** nav must be the **last
  lander layer** at **`x: 0` / `y: 0`** so the hero does not cover it
  (Pitfall #97). **`web-responsive` lander:**
  `hover-reel/scripts/capture-session.mjs` — a **plain capture** at all three widths. Nothing is
  model-authored here (`references/12-desktop-source.md`). **FRAME `Navigation`
  is captured at 1600 / 768 / 390** as `01 · nav-1600` / `02 · nav-768` /
  `03 · nav-390`, each serialized at its own viewport so the compact and burger
  variants are real paint. Capture Tool is leftover live hover only.
  **P-0:** create
  `Ruler · desktop` only; `Design Library` must not exist before 1.3.
  Arrange page rows only. 768 and 390 are not Step 3.
  Pre-pesticide is the live DOM contract; rebuild `qa-overlay` is end-of-build
  outlines (Pitfall #70).
- **1.2 postflight / A/5** = automatic mechanical gate at the end of the collect.
  `capture-session.mjs` runs `stretch-root.mjs --prove --artboard home-desktop`
  only — not `qa-paper` or `merge-split-headings`. It writes
  `qa/stretch-root-evidence.md`. **FAIL 1.2** if the stretch proof fails.
  Image QA matches icon **box metrics** (size, container, gap) from the live
  inventory at that width — do not copy `flex-wrap` / 2+1 from 768 onto
  1600/1440 (Pitfall #75).
- **A/5-R** is part of the 1.2 automatic postflight. Section bands follow a
  stretched artboard; site containers keep `max-width`. A/7 then runs exactly
  two read-only lenses (manifest coverage + Paper geometry) from one hashed
  snapshot. They write evidence only under `qa/agent-findings/`; the controller
  accepts current findings, fixes/reimports serially, and both lenses rerun.
- **A/8 / 1.4** = **Human Review + Paper Comments HARD STOP.** After **1.3**
  (`Design Library` + `qa/buttons-components-pull.json`),
  `mark --step 1.4 --status active` writes `qa/paper-human-review.md` if
  missing and opens Paper. **Stop**. Walk 1600 / 768 / 390, FRAME `Navigation`,
  FRAME `Buttons`, FRAME `Components`, Design Library. Pin comments. No 2.1 /
  `get_jsx` until those threads are listed and fixed (or the file is clean).
  **`mark --step 1.4 --status done` requires `qa/paper-human-review.md`**; it
  releases the controller lease and emits the SESSION 2 prompt
  (`qa/handoff-2.0.md`) — copy that into a new session for 2.0 (strong tier recommended).
  Capture Tool is leftover live hover (`open-capture`).
- **B/1 (L) / 1.3** = the **only** Design Library creation and mining pass. It
  runs **immediately after the 1.2 capture**, on the frames that capture wrote:
  landers at 1600 / 768 / 390 plus FRAME `Navigation` at all three widths. It
  does **not** wait on Capture Tool.
  `Design Library` = **foundations only** (fonts, type, colors, spacing,
  radius) labeled with CSS root names. After seed QA, pull unique buttons
  and components from token-seeded `home-desktop` onto FRAME `Buttons` and
  FRAME `Components`. `qa/buttons-components-pull.json` is required.
  Mine colors, families, weights, and
  styles; leftover SEMANTIC roles if the hex appears, then a Tailwind floor of
  at least five SEMANTIC colors (`--color-danger` / `--color-warning` /
  `--color-success` / `--color-info` / `--color-muted`). Type **sizes** go
  `--text-xs`…`--text-12xl` (large → small, `Aa` in the primary sans, 7xl–12xl
  labeled DISPLAY). Colour swatches are four per row. Spacing / radius /
  elevation stay Tailwind defaults (Pitfall #64) — do not
  rebuild those scales. Rebuild maps a measured px value to the closest
  Tailwind class. **No** `LIBRARY — Components`, no isolated atom sheet, no
  `site-components` / `kit-components` dump. Never a second `Design Library`.
  Prefer **no Theme Library**. If Theme Library exists = tokens + **full
  homepage regions** (Nav, Footer as on the page), not detached tiles.
  Tokens registered + `design-library/library.json`. After brand colors,
  leftover homepage / A/6 hexes override a semantic role when they match;
  unused leftover-only roles stay off, but the five Tailwind SEMANTIC colors
  always ship.
  `run-design-library-step.mjs` inventories all eligible landers and Capture
  Tool frames once, mines them once (Pitfall #112: kill 20s of silence), creates exactly one `Design Library`
  first in the row, replaces Paper tokens with one canonical deduplicated set,
  then `apply-theme-tokens.mjs` binds exact matches across landers + A/6 +
  Interactive components + Design Library to `var(--token)` without inventing
  fills on unpainted 1.2 frames (Pitfall #157) and writes
  `qa/token-pass.json` plus `qa/token-pass-qa.json`. Census every node —
  tree minus the QA file, or an unlisted raw hex/px, fails (Pitfall #76).
  Unmatched measured values stay unchanged and are reported as literals.
  `token-geometry-guard.mjs` compares pre/post geometry; movement, resize,
  wrapping, typography, or flex-sizing drift fails (Pitfall #108).
  The same pass sets `textWrap: "pretty"` on heading Text nodes (Pitfall #65).
  1.3 ends only when those boards consume the library tokens.
  **NON-NEGOTIABLE HARD STOP.** Never skippable. Blocks **all** of 2a/2b
  and any production write under `rebuild/` (except Step 1/1.4 assets). Capture
  pages in Paper alone are **not** enough — no build until the library exists
  **in Paper**, not only on disk.
- **B/2a** = **tokens from 1.3**, signed at 1.4 — not a dump prelude. Confirm Paper
  `get_tokens` is non-empty and copy the canonical set into
  `rebuild/css/tokens.css`. Write `css/fonts.css` from the 1.1 Latin files
  (`source-site/assets/*.woff2`). `verify-fonts.py` runs here, not at 1.1.
  No get_jsx dump. No gallery-as-the-build.
- **B/2** = **2.1 Design System / 2.2 author / 2.3 validate / 2.4 TAGS**. 2.1
  emits `rebuild/design-system.html` + tokens from `library.json`. 2.2
  frontend-design writes `rebuild/index-semantic.html` from Paper desktop
  using those tokens (aesthetic-risk OFF). 2.3 seeds `index.html` and walks each homepage band
  against the 1.2 source clips at those three widths (`section_22_gate.py`). 2.4 injects the overlay
  with TAGS on and stops (`open-build-review.py . --stage 2.4`).
  B/2b get_jsx is deleted. B/2b-T / B/2b-S are deleted as ship. B/2b-R
  is folded into 2.1 + 2.3. **B/3 is retired (2.8.38)**.
- **B/4** = **Gate**, not a rebuild: functional QA in **Chrome on `file://`**.
  **No server, ever.** After 2.4. Hover CSS ≠ clicking the FAQ.
- **2.4 TAGS checkpoint** = first ship-page Chrome open. Overlay default
  is TAGS. Run `open-build-review.py . --stage 2.4`. Human receipt
  `qa/build-checkpoint.md` then 3.x. Controller still remediates open
  Paper comments before 3.0.
- **C/1 + C/2** = **Gate** vs source screenshots, **1 agent, 2 passes**. Not a
  repeat of Pass 1 (Paper). Catches fonts/images/chrome Paper dropped.
- **Pass 3 / C/3 hover** = 1.3 `qa/button-hover.json` (source CSS `:hover` on
  pulled Buttons) implemented by `apply-hover-css.py` at 3.2. Optional leftover
  Capture Tool manifests may refine the same `library.json` names. Read the
  **painted `<a>` in the hover HTML**, not `styleDelta[0]` and not
  UA `rgb(0,0,238)` (Pitfall #33). Copy that pill when 1.3 source CSS or Paper
  default and hover differ. Invent a `:hover` only when those two cells are
  identical and 1.3 found no source paint (Pitfall #152). Section-scope
  same-label CTAs. Write hover CSS to `rebuild/css/hover.css` on those
  **same** `library.json` class names. Hover is 1.3 + 3.2, not a 2.2 letter.
  Do not skip because Capture Tool did not run (Pitfall #207).
  If a hamburger is painted, `author-nav-drawer.py` stacks the same desktop
  links into `#nav-panel`. Do not skip that sheet for Capture Tool
  (Pitfall #208).
  If FAQ rows are painted, `author-faq.py` wires the accordion and fills
  empty answers from the scrape (Pitfall #209).
  If a nav dropdown is painted or the scrape has a matching submenu,
  `author-nav-dropdown.py` wires hover/click (Pitfall #210).
- **C/3.1–3.3 polish** = after those gates: impeccable → design-taste → emil
  with receipts in `qa/polish-passes/`, the three 3.2 companion receipts
  (`qa/web-design-guidelines.md`, `qa/find-animation-opportunities.md`,
  `qa/apple-design.md`, Pitfall #215), and `qa/polish-report.html`
  plus `rebuild/polish-report.html` (`verify-polish-passes.py`).
  Scope is **a11y / contrast / anti-slop / hover-if-live / painted burger
  drawer / FAQ accordion / nav dropdowns / mandatory GSAP in-view / scrape-only SEO**.
  2.4 freeze (`qa/fidelity-freeze-24.json`) must still verify. Do not
  restore Paper icons/gaps/type. Do not skip GSAP from a 1.4 archive
  (Pitfall #204).
  **3.3** is `semantics_pass.py --freeze-structure` + `verify-semantics.py`.
  Pitfall #93 #196.
  **3.4** is `open-human-review.py .` — Chrome opens `index.html` (2.4),
  `index-polish.html?qa-outlines=off` (QA; `?qa-outlines=tags` turns outlines
  on), and the 3.1–3.3 report (Pitfall #63 #203 #223). Marking 3.4 done
  promotes polish to `index.html` and archives the other homepage HTML, then
  stops the live-board
  refresh, plays confetti, and shows port targets. Then tidy drops `qa/`,
  `capture/`, scrape trees, and run files. The finished `pipeline.html` stays
  at the project root next to `rebuild/`. Do not write `NEXT.html`. Tidy never
  runs before 1.1–3.4 are done (Pitfall #151).
- **C/4** = docs + design-system polish, then **open Chrome on the `file://` path
  and hand it over. End.**
- **C/5** = CMS import — **only on explicit user request, in a later turn.**

## Agentic steps are mandatory

`TaskCreate` every stage row on load; `TaskUpdate` on every enter/exit/skip;
progress-pulse every ~5–10 tool calls. Two actions per boundary: update the task,
then do the work. Running with no visible task list is a process failure — this
was missed on a previous run.

Stage **H** (harness first-pass) is **removed**. Stage **M** is **retired** — the
region manifest is copied out of Stage L's `library.json`.

## Folders

| Path | Role |
|---|---|
| `capture/` | Stage P per-section serialized DOM |
| `design-library/` | Stage L Paper components + tokens → Steps 3, 9 |
| `source-site/` | 1.1 light scrape — HTML + images + Latin fonts (1.2 downloads remaining live images) |
| `source-site/components/` | A/6 Steps 4.0-4.4 hover-reel — `<page>/<kind>/` state HTML + per-kind `manifest.json` → Paper artboards + C/3 |
| `analysis/` | **Optional** — only if Paper's export fell short |
| `rebuild/` | **Ship** |
| `astro/` | Optional Phase 5 — static Astro app: chrome from the signed homepage, one `.astro` body per Paper page |
| `qa/` | Gates, diffs, states, ledgers |
| `cms/` | Instatic — C/5 only |

## Hard gates

1. **Never reuse another project's `rebuild/`, `css/`, `capture/`,
   `design-library/`, assets, or `qa/`** — every run builds from its own capture.
   Similarly-named sibling folders (`-2`, `-test`, ` copy`) are the trap. Check
   `pwd` / `ls ..` before Step 1 writes anything.
2. 1.1 light scrape before 1.2 so `source-site/assets/` is a cache for localize-html-images; Latin fonts are ready for 2.1
3. Stage P runs in **headed Chrome** — no silent headless fallback; no `--keep-open` in multi-page loops; no `| tail` on capture; settle waits are bounded
4. **1.2 Capture 1600 / 768 / 390 + Navigation:** capture all three landers and
   their source-section clips, capture FRAME `Navigation` at each width, run
   `stretch-root.mjs --prove` on `home-desktop` and `breakpoint-shot-qa.mjs`.
   Missing shots, a missing Navigation take at any width, or a red QA keeps 1.2
   open. Nothing here is authored — if a frame is wrong, fix the capture.
4a. **1.4 Human Paper checkpoint:** after **1.3 is on the canvas**,
    `mark --step 1.4 --status active` writes `qa/paper-human-review.md` if
    missing and opens Paper. Walk 1600 / 768 / 390, FRAME `Navigation`, FRAME
    `Buttons`, FRAME `Components`, Design Library. Pin comments. **Stop**.
    Capture Tool is leftover live hover (`open-capture`) — not a 1.4 done-gate.
    `mark --step 1.4 --status done` requires `qa/paper-human-review.md`; it
    releases the controller lease and emits the SESSION 2 prompt.
4b. **1.3 single-mine Design Library + Tokens:** immediately after the 1.2
    capture, run the one authoritative sequence: inventory every eligible frame; mine colors +
    families/weights/styles once; create exactly one foundations-only Design
    Library; replace Paper tokens with the canonical set; bind exact matches;
    keep opaque brand fills distinct from alpha washes of the same RGB
    (Pitfall #154); restore collapsed fills from capture HTML on a re-run
    only when Paper already has a fill — never invent paint on an unpainted
    1.2 frame or snap a near hue (Pitfall #157);
    prove pre/post geometry unchanged; then pair each 1600 / 768 / 390 source-section
    clip with the matching Paper band and rebind until color, type, and layout
    hold (`qa/library-seed-qa.json`, Pitfall #156). Extra saturation vs a quiet
    source clip fails 1.3 with no retry. Missing any clip dir fails 1.3.
    Write `design-library/library.json`. After seed QA is green, pull unique
    buttons and components from token-seeded `home-desktop` onto FRAME `Buttons`
    and FRAME `Components` on a `#6F6F6F` review stage that hugs the source
    pixel width (Pitfall #222 #230, `references/13-buttons-components.md`).
    Then author
    button hover from source CSS (`author-button-hover.mjs`). Receipts
    `qa/buttons-components-pull.json` and `qa/button-hover.json` are required
    to mark 1.3 done (Pitfall #205 #207 #222 #230).
    P-0 and every earlier stage must leave Design Library absent.
4c. **2.1 comment gate:** first Build action is `list-paper-comments.mjs`.
    Exit 2 = apply every open thread, resolve it, re-run. Do this even if
    the user never mentioned comments. Then theme CSS.
4d. **Stage L is 1.3, never skippable:** no 2.1 until 1.4 is signed
    **and** Paper has a `Design Library` artboard
    (foundations only; no Components sheet) + tokens and
    `design-library/library.json` is written.
    Disk-only library without Paper artboard = fail.
5. **Preview default is `file://`** — no HTTP server in the pipeline.
   Relative asset paths are therefore mandatory. HTTP is **user-opt-in**
   only (overlay extensions like Pesticide often fail on `file://`).
5b. **2.2 Paper-first (2.13.0)** — first `index-semantic.html` is frontend-design
   authored semantic HTML+CSS of the QA-passed homepage. 2.3 seeds
   `index.html` from that file. Paper is the
   brief, not a JSX dump. Never freehand. Never React / Tailwind CDN.
   Never a get_jsx dump — the dump is not even a lock assistant
   (Pitfall #109). B/2a does not author site pages.
5e. **2.3 then 2.4 on the same file** — walk each homepage band against
   the 1.2 source clips at 1600 / 768 / 390 (`section_22_gate.py`). Then inject the overlay
   (TAGS on) and open the 2.4 checkpoint. Do not paste soup as
   `index.html` (Pitfalls #77 #109 #148). C/3 adds hover from A/6
   Paper states when the live site has them. `verify-rebuild-trees.py`
   before B/4. No sibling rebuild folders.
5d. **Stop-at-every-level** — when asked, after A/1, A/2, A/4, B/1, B/2a,
   B/2b, B/4, C/1 write `qa/runs/<run-id>/STOP-<stage>.md` (did / broke /
   scale patch). Scale learning agent applies the patch.
6. Live tasks via `TaskCreate`/`TaskUpdate`: lettered parents A/B/C with numbered
   children; one foreground `in_progress`. Only A/7's two readers may
   inspect in parallel; every reviewer is read-only and the
   controller owns Paper, shared files, progress, and canonical gates. Update
   on enter/exit. 2.3 compares disk clips (serial or max two workers);
   only the controller writes `rebuild/`. Pixel-perfect is a one-pass
   assist, not a loop. No Paper MCP at 2.3.
7. Do not open Chrome on `rebuild/index.html` at 2.1. First ship
   preview is 2.4 (`open-build-review.py . --stage 2.4`, TAGS on).
   Pitfall #133.
8. C/1 + C/2 (Step 7) is **two passes, one vision-capable agent** — pass 1 find+fix, pass 2 re-verify;
   never stop after a single pass; no multi-agent fan-out
9. C/3 = 8a animation parity (every captured-state row implemented or
   explicitly drifted/blocked in `qa/animation-parity.md`) **then** all three
   polish skills in order on every workflow; do not skip either half
10. **Never ask permission** between A/1 and C/4 — no page-count question, no
    pre-QA confirmation
11. Stop at C/4 with a working `file://` preview. CMS / C/5 is parked in `archive/`.

## Companions

- `hover-reel` on A/6 (Steps 4.0-4.4 = optional 1.4, after A/4, sequential) + C/3 — the source's
  hover/interaction layer as **state pairs with measured deltas**, not GIFs: a
  Paper capture records no `:hover`, so each state is serialized under a real
  pointer and imported as layers
- `url-to-paper` on A/4
- Structure: 2.1 authored HTML from Paper + 1.3 tokens (signed at 1.4). Spacing: Tailwind / `var(--spacing-*)` from `design-tokens`.
- `pixel-perfect` on 2.3 as a one-pass assist (not the driver, not a loop). Not C/1 / C/2.
- polish **C/3.1–3.3** on `rebuild/` **after** those gates (**required**, receipts + report)

Mirror folders in the flow-skills repo carry the stage number
(`1.2 url-to-paper`). Installed package names never do.
