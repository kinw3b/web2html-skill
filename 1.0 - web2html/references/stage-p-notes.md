# Stage P, A/6, Step 7 and Step 2b working notes

Split out of `AGENTS.md`. Read when entering that stage.

## Stage P — serialize + disk PNG (url-to-paper 1.2.39)

Paper-first **pages** are **2.8.10** (B/2b). This section is still the Stage P
capture/import notes.

**One Paper file per run.** The first `capture-session.mjs` calls `create_file`.
A retry reopens `qa/paper-file.json` from this project. Never `list_files` /
never `open_file` a similarly-named document from another project
(Pitfall #187 #224). Pin that id for the rest of this run. Desktop, tablet,
and mobile landers, QA pairs, hover/component states, and the Design Library
are named artboards/pages in **that file**. Do not invent a second file later
in the same run. `--new-file` is the only fresh document. `start` clears a
leftover receipt.

### Homepage-only / lander path (first-class)

**Pre-pesticide first (url-to-paper 1.2.29) + SOURCE clips (1.2.30).** On the live homepage, before
`experiment-capture-home.mjs` / `assemble-lander.mjs`:

```bash
node "$SKILLS/url-to-paper/scripts/pre-pesticide.mjs" \
  --url "$URL" --width 1600 --out capture/home-desktop/pre-pesticide.json
PAPER_FILE_ID=$PAPER_FILE_ID node "$SKILLS/url-to-paper/scripts/seed-source-board.mjs" \
  --dir capture/home-desktop/source-sections --page home
```

Visible Chrome; `--headless` is CI-only. Writes the live DOM contract
(`sections[]` with `childCounts`, `images[]`, `forms[]`, `landmarks[]`)
and per-section outlined clips at 1600 / 768 / 390 in
`capture/home-{desktop,768,390}/source-sections/01-slug.png` (same IDs). Seed
`Screenshots` from the 1600 clips as a review board — vertical stack, A/6 red badge, **50% opacity** so it recedes next to `home-desktop`.
**Never** a full-page source shot. HUD tag/id is `x-paper-prepesticide` —
the serializer already skips `x-paper-`. Destroy the HUD before serialize.
This is **not** rebuild `qa-overlay` (that is end-of-build Outlines). Diff
the JSON after import (prior semantic-lock run: live imgs vs Paper 0). Match **box
metrics** (icon size, container `w`/`h`, gap) per width — do not copy
`flex-wrap` / `round(46%)` / 2+1 from 768 onto 1600/1440 (Pitfall #75).
Homepage only by default. Do not invent a second Paper file later in the same run.

**Paper import is one page.** A/1 defaults to **`/` only** plus the classified
viewport set (1600 / 768 / 390 of that page). Do not import `/contact`,
`/features`, `/pricing`, `/blog` unless the user named those routes **and**
passed `--allow-multi-page`. Default `--max` / `--max-pages` is 1. **Exit**
if `plan.pages.length > 1` without the flag. Extra sitemap routes stay in
the scrape. After import: run `qa-paper.mjs` on the homepage, **FAIL**
before 2.1 author if sections are misplaced or overlapping.
Keep `fullpage.png` on disk. Design Library = foundations only — no
Components sheet.

Classify with pixel-perfect `responsive-scope-playbook.md`. A source template
whose nav or layout changes at phone is `web-responsive`. Default set:
**390×844, 768×1024, 1280×800, 1600 (or 1920)**. Primary Stage P remains
1600; **768 and 390 are required Stage P captures** (`experiment-capture-home.mjs`
+ `assemble-lander.mjs`, separate out-dirs and artboards, same file). Tablet
is a third source layout (hamburger + remaining two-column hero on prior responsive run),
not a squeezed desktop. Do not defer 768 or 390 to Step 3.

**Contract contradiction is a process failure.** If a viewport is required,
it must be captured in Paper. Forbidden allowed-drift: “Mobile DOM not
re-captured unless material divergence” while 390 is on the required list.

### Responsive Paper geometry — 2.1 born responsive + 2.3 loop

B/2b-R / 2.2.d is retired as a live letter. 768 / 390 live in **2.1**
(authored responsive) and **2.3** (each section Paper-signed). Do not
`get_jsx` tablet/phone as the build.

1. Widened-root Paper audit (captured viewport widths → `width: 100%` on
   section/full-bleed layers; inner `max-width` kept)
2. For `web-responsive`: `--width 768` and `--width 390` capture dirs + named
   `home-768` and `home-390` artboards
3. 2.1 writes real `@media` that match those frames — not a 1600 freeze
4. 2.3 signs each homepage section at 1600 / 768 / 390
   (`qa/section-align-22.json`)

A CSS hack that only forces `#paper-root > section > div { width:100%
!important }` **fails** 2.1 / 2.3.

### Stop-at-every-level learning loop

When the user asks to stop at every level, after each **A/1, A/2, A/4, B/1,
B/2a, B/2b, B/3, C/1** write `qa/runs/<run-id>/STOP-<stage>.md` with: what
we did, what broke / was missing, the scale patch. The scale learning agent
owns applying the patch to this repo.

### Anti-freeze (ora-portfolio 2026-08)

| Forbidden | Why |
|---|---|
| `--keep-open` in multi-page loops | Process never exits; next page never starts |
| Pipe capture through `tail` / `head` | Buffers until exit — looks hung |
| Unbounded image `onload` wait | Hung live `/about` on “settling page…” |

**Required:** current scripts — fonts 5s + images 8s timeouts, scroll height cap,
soft networkidle, log line `settle complete`. Prefer `2>&1 | tee capture/<page>.log`.

### Full-page PNG (nav/menu QA)

Serializer + section detection **often drop fixed/sticky nav and menus**. Keep
`capture/<slug>/fullpage.png` on disk. If chrome is in the PNG but not in Paper
layers, rebuild header/nav from that file + the live site — not freehand.

Do **not** import `{page} — source screenshot` unless a person asks for
left/right in Paper. `qa-paper` runs on the **page** artboard. A missing sibling
does not fail the 1.2 postflight.

**Opt-in sibling:** `--screenshots-only` then pairing arrange. Pin explicit
image width/height. Never `height:auto`.

**A/5-R stretch-root (prior responsive run).** Capture freezes section roots at the
viewport px (`1600px` / `768px` / `390px`). A designer stretching the
artboard then sees a short band. After A/5 geometry, before A/6:

```bash
PAPER_FILE_ID=$PAPER_FILE_ID node "$SKILLS/url-to-paper/scripts/stretch-root.mjs" --prove
node "$SKILLS/url-to-paper/scripts/qa-paper.mjs" --depth 2 --json qa/stretch-root-qa.json
```

`stretch-root.mjs` sets named section roots (and nested full-bleed wrappers
at the capture width) to `width: 100%`. Site containers keep
`max-width: <measured>`. `--prove` widens each page artboard, checks
sections follow, then restores the capture width. `qa-paper` fails A/5-R on
any `frozen-root` finding. Record `qa/stretch-root-evidence.md`. This is
**not** a substitute for 768/390 Stage P captures or for B/2b-R HTML
`@media`.

**P-0 · Canvas ruler (prior responsive run).** Before the first content `create_artboard`,
`draw-rulers.mjs --file $PAPER_FILE_ID --init` (or let assemble/import do it).
Paper has no native guides. One thin red `Ruler · desktop` at the top.
`Source · {page}`, then `home-desktop`, `home-768`, and `home-390`, then
A/6 and `Interactive components` sit **left to right** under it — never their
own vertical stacks. `Design Library` does not exist yet. Frames hang **≥100px below**
the bar. The lintel is **20000px**. `create_artboard` ignores `left`/`top`
— pin with `update_styles`. Do **not** ignore `Source · {page}` when
computing lander `rightEdge`. Pitfalls #37 #42.

**P-0 creates the ruler only.** `draw-rulers.mjs --init` must not create,
seed, mine, or render `Design Library`. The library does not exist before 1.4.
After all landers and Capture Tool frames are on Paper and extension **Done** is
recorded, `run-design-library-step.mjs` inventories every eligible frame once,
mines once, creates exactly one foundations-only `Design Library` after
`Navigation`, replaces Paper tokens with the canonical deduplicated set, and
binds exact matches back. The sheet always floors five Tailwind SEMANTIC
colors, `--text-xs`…`--text-12xl` large → small with `Aa` in the primary
sans, and four colour swatches per row. `token-geometry-guard.mjs` must prove that no
non-library node moved, resized, rewrapped, or changed flex sizing (Pitfall #108).

**Arrange.** `assemble-lander.mjs` writes the ruler, then `Source · {page}`,
then the lander. After all width assembles: `arrange-artboards.mjs` (no
`--order` needed). Before 1.3 the row is Source → desktop → tablet → mobile →
A/6 → Interactive components. At 1.3, place the newly created Design Library
first in the row, ahead of Source. Do **not** run `--screenshots-only` unless asked. Nudge with
`left`/`top`, never `x`/`y`.

### A/6 component states after the full Paper capture

**Default is the Chrome extension, not the auto runner.** One session runs Nav
→ Hover → Multi → Single → Tags, including responsive evidence and semantics.
The agent **stops until Extension Done** (`human-hover-done.json`), then waits
for the user to type **Continue** in chat before starting 1.4. `--auto` /
`capture-site-component-states.mjs` is CI / leftover only.

Once A/4 has imported every contract page and its named sections, the
coverage validator (A/7) still runs after Done:

```bash
node "$SKILLS/hover-reel/scripts/capture-site-component-states.mjs" \
  --pages-json source-site/pages.json --pages home,contact,about \
  --capture-dir capture --out source-site/components --max 40
node "$SKILLS/hover-reel/scripts/validate-component-captures.mjs" \
  --dir source-site/components --expected-pages home,contact,about \
  --json qa/component-state-coverage.json
# Homepage-only — capture AND validate must name the same page. Leftover
# first-run about/pricing/contact/404 folders are warned, not walked.
node "$SKILLS/hover-reel/scripts/capture-site-component-states.mjs" \
  --pages-json source-site/pages.json --pages home \
  --capture-dir capture --out source-site/components --max 40
node "$SKILLS/hover-reel/scripts/validate-component-captures.mjs" \
  --dir source-site/components --expected-pages home \
  --json qa/component-state-coverage.json
# In the second read-only lens, run qa-paper against the state artboards:
node "$SKILLS/url-to-paper/scripts/qa-paper.mjs" \
  --json qa/component-paper-qa.json --shots qa/component-paper-shots
```

`qa-paper.mjs --shots` preserves the human-readable artboard label while
replacing path separators with `∕`, so A/6 titles such as `A/6 · home · Navbar
states` always produce review evidence instead of an accidental nested path.

The runner writes `<page>/<kind>/manifest.json`, preserving section labels and
measured rectangles so buttons and text links are discovered across the full
page rather than only the first route. A/7 has two independent read-only
lenses: the coverage validator above, and Paper geometry review with
`qa-paper.mjs`/`get_node_info`/`get_screenshot`. The controller first creates
one hashed snapshot of the manifests plus both QA receipts; the two lenses may
inspect concurrently and write only `qa/agent-findings/<run-id>/a7/`. It rejects
stale reports, fixes and reimports serially, then both lenses rerun from a fresh
snapshot. A truncated
candidate pool, missing page/kind, unconfirmed hover, zero-size state root, or
unproven FAQ open blocks B/1. A confirmed `changed: false` state does not block;
it is retained for C/3. An intentionally empty FAQ/form kind is recorded
with a reason and is not treated as a missing manifest.

Serializer often omits the parent band. Hero CTAs and footer links arrive as
white type with no fill; a white Paper cell makes them invisible. Capture
records `ancestorBackground`; `build-paper-states.mjs` paints the Slot and
the imported root when the root is transparent and the type is light
(Pitfall #27). FAQ grouping is by **width only** so an already-open first
row still matches; “open” climbs to the **innermost** ancestor that grew
≥8px. Accordion titles also match `--kind buttons` with `changed: false` —
acceptable noise, not a second button pattern. **P-0:** `Ruler · desktop`
exists before any A/6 frame. Kinds append as sections of
`A/6 · {page} · states`. Other review frames park in a **horizontal
row** under that ruler (Pitfalls #37 #39). A/6
launches **visible Chrome** like Stage P. live `whileHover` needs
reduced-motion off and the live hover fill pinned (Pitfall #30).

## Step 7 QA (v2.6.1) — one agent, two passes

Against `source-site/screenshots/` (not Paper):

1. **Pass 1** — capture side-by-sides, review all sections, fix high/medium at shared token/component layer  
2. **Pass 2** — re-capture + second review; residual fixes; then exit  

Stopping after pass 1 is a **process failure**. No multi-agent fan-out.

