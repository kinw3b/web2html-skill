# 2.3 measure — disk gold, at most two workers, no live Paper MCP

This file is the **2.3 driver**. Do **not** load `/pixel-perfect` as the
step. Do **not** call Paper MCP from 2.3.

Eyeballing `rebuild/index.html` against a zoomed Paper screenshot is not
2.3. Gold is already on disk from 1.2 / 2.2:

| Need | Disk |
|---|---|
| Visual at 1600 / 768 / 390 | `capture/home-{desktop,768,390}/source-sections/NN-slug.png` — **numbered per band, all three breakpoints** (1.2, not 1.1 scrape full-page) |
| Pulled compare | `qa/paper-measure/compare/NN-slug-{1600,768,390}-{source,rebuild,side}.png` |
| Desktop numbers + SVG/icons | `rebuild/index-raw.html` (2.2 Paper `get_jsx` dump) |
| Clip geometry | matching `NN-slug.json` sidecars |
| Actual | `qa/paper-measure/rebuild/<id>-{1600,768,390}.png` |

`section_22_gate.py` grades those receipts — it never opens an image
(`references/model-routing.md`). **Never skip 2.3.** Each section
self-validates against **disk gold + index-raw**, then a worker may call
pixel-perfect **once** as an assist, still against those PNGs. Close
enough fails. A 10-loop refine also fails (Pitfall #195). Eight Paper MCP
workers in one spawn also fails (Pitfall #202).

Load this file at 2.3. Do not invent 1024 / 1320. Do not restyle the whole
page to fix one band. Pitfall #176 #185 #195 #202 #216.

The one-pass loop below is the **measure**. It is not the end of 2.3. After
APPLY comes the **VALIDATE walk** (§ below): every band, top to bottom,
re-shot, **looked at**, fixed, re-shot, until it matches or round 3. That
walk is what used to happen by hand at 2.4 from screenshots. It is now
inside 2.3 and gated (Pitfall #216).

## Why disk, not Paper MCP

1.2 already clipped every homepage band at 1600 / 768 / 390. 1.4 signed
those frames. 2.2 already dumped Paper desktop into `index-raw.html`
(inline computed styles + SVG fills). Re-querying Paper at 2.3 does not
add a number that file does not have — it rate-limits the desktop MCP
and stalls the session.

Paper stays the brief. The brief is **frozen to disk** before 2.3 opens.
If a source clip is missing, fail 2.3 and go back to 1.2. Do not open
`get_guide` / `get_basic_info` / `get_computed_styles` / `get_screenshot`
to paper over a hole.

## Shape

Do not yield to chat. Session 2 runs until 2.4.

```
Controller (this session — only rebuild/ writer):
  0. SEED     seed_index.py .  (copies index-semantic.html → index.html;
              never overwrite; do not mutate the 2.2 first pass)
  1. LIST     ship bands from rebuild/index.html (<section id> + footer)
  2. CENSUS   raw_23_census.py .
  3. GOLD     paper_23_disk_gold.py .   (maps each band → 01-slug.png)
  4. SHOOT    paper_23_rebuild_shots.py . --all
  5. PULL     paper_23_clip_compare.py .  (copies NN-slug.png at 1600/768/390
              next to rebuild shots; writes side-by-sides)
  6. COMPARE  Read those pulled PNGs. Serial here, or at most TWO workers.
  7. APPLY    merge each section patch serially onto rebuild/index.html
              (port missing dump SVG/icons — do not invent Lucide stand-ins)
  8. RESHOOT  only sections whose CSS changed (max 1 re-shoot each)
  9. INDEX    qa/paper-measure/_index.json + qa/section-align-22.json
 10. VALIDATE paper_23_validate.py . --next → --id <band> --shoot →
              Read the three side PNGs → patch that band → --record;
              repeat ≤ 3 rounds per band, top to bottom, then --residual
 11. GATE     section_22_gate.py .  (needs every <id>.validate.json)

Do not skip this loop. Missing rebuild/index-raw.html,
qa/paper-measure/raw-census.json, qa/paper-measure/disk-gold.json, or
qa/paper-measure/clip-compare.json keeps 2.3 open.
```

Each compare, for section S at 1600 / 768 / 390:

```
  MEASURE  index-raw.html (type / button / overlay / list / SVG)
           + qa/paper-measure/compare/NN-<id>-{1600,768,390}-side.png
             (1.2 numbered clip left, rebuild right). If no side file,
             Read the pulled -source.png and -rebuild.png pair.
           + sidecar bbox when you need a number
  WRITE    qa/paper-measure/<id>.json  (before proposing CSS)
           must set rawCompared: true, diskCompared: true,
           clipCompared: true
  CHECK    self-validate vs disk gold + index-raw (watch list below)
  ASSIST   pixel-perfect at most once, only if the watch list missed,
           and only against those PNGs — never Paper MCP
  PATCH    qa/paper-measure/<id>.patch.md  (S only) — or none
  STOP     one compare + one proposed fix here. The bounded re-check is
           the VALIDATE walk below, not a second measure pass.
```

Hard caps:

- **Paper MCP calls at 2.3: zero.** Workers and the controller. Comment
  remediation is 2.1 and after 2.4, not here.
- **Task spawn: at most 2 live children.** Default is serial in this
  session. Never one worker per section in a single fan-out. Never 8.
- Pixel-perfect: **at most once per section**, **one compare + one fix**.
  Skip it when MEASURE already matches the watch list.
- No 10-loop refine. No full-page spec. No user-verification handoff.
- Remaining drift after the one-pass cap goes to the **VALIDATE walk**
  (≤ 3 looked-at rounds per band), not to 3.x and not to the human at 2.4.
- Workers **never** write `rebuild/`. The controller does, serially.

If this harness has no parallel task tool, run the same contract
serially. Still one-pass. Still no pixel-perfect loop. Still no Paper.

## Watch list (why pixel-perfect may fire)

Use the assist **only** for these — layout, type, and 2.2 hallucinations.
Not polish. Not a restyle.

| Hit | Look for |
|---|---|
| **Layout** | split vs stack, column count, band order |
| **Typography** | `fontSize`, **line-height in px**, weight, tracking, wrap |
| **Geometry / shift** | width, height, gap, padding, inset; a band that jumped |
| **Missing icons** | list / perk vectors Paper paints and 2.2 dropped. **Gold is index-raw:** empty `div` + `background-image: url(….svg)` or inline `<svg>`. Port that markup/asset. Do not invent Lucide/Heroicons. |
| **Raw dump SVG** | `qa/paper-measure/raw-census.json` lists dump SVG assets the ship lacks. Each worker owns the ones near their section copy. |
| **Radius** | buttons and cards — 10 vs 8 vs pill. Do not assume `radius-full` |
| **Imagery** | photo box size, crop, radius |
| **Absolute overlays** | floating infographic cards, `position: absolute` siblings of the photo |
| **2.2 hallucination** | invented blocks, missing overlays, extra chrome Paper never had |

Sub-2px noise is drift. A missing overlay card, a pill where the dump is
10px, or a 3-line heading that the desktop dump wraps in 4 is a miss.

## Controller — spawn

Prefer **no spawn**. Walk the `disk-gold.json` section list here.

If you do spawn: this harness’s parallel task tool, **at most two**
children at a time, then the next pair. Never a single 8-way batch.
Children know nothing of the parent chat. They receive disk paths only.
They **must not** load Paper MCP, `get_guide`, or `get_basic_info`.

Workers write only under `qa/paper-measure/<id>.*`. They are **not**
reviewer-wave agents (those stay read-only under `qa/agent-findings/`).
Canonical `_index.json` / `section-align-22.json` stay controller-only.

### Child prompt (copy-ready)

```
You are a web2html 2.3 section worker. One section, then stop.
Do not call Paper MCP. Do not call get_guide / get_basic_info /
get_computed_styles / get_node_info / get_screenshot / get_children.

Project: <root>
Section: <id>
Raw dump: rebuild/index-raw.html
Raw census: qa/paper-measure/raw-census.json
Disk gold: qa/paper-measure/disk-gold.json
Clip compare: qa/paper-measure/clip-compare.json
Pulled 1.2 clips: qa/paper-measure/compare/NN-<id>-{1600,768,390}-source.png
Side-by-sides: qa/paper-measure/compare/NN-<id>-{1600,768,390}-side.png
Rebuild shots: qa/paper-measure/rebuild/<id>-{1600,768,390}.png
Recipe: web2html/references/section-23-paper-loop.md

1. MEASURE from the pulled 1.2 clips. Read the three
   NN-<id>-{1600,768,390}-side.png files (1.2 numbered clip left,
   rebuild right). Those are the 1.2 source-sections/NN-slug.png shots
   at each breakpoint — not a Paper MCP screenshot. Census index-raw.html
   (inline <svg>, polyline/chevrons, background-image url(….svg)). Use
   sidecar bbox when you need a number. Read raw-census.json for dump
   assets whose nearby text sits in this section. Port those glyphs.
2. WRITE qa/paper-measure/<id>.json BEFORE proposing any CSS.
   Include rawCompared: true, diskCompared: true, clipCompared: true,
   gold: "disk", and raw: { svg, bgSvg, ported[] }.
3. Self-validate against the side-by-sides + index-raw. If the watch
   list is clean, patch = none, assist = none, measured = true, stop.
4. On a miss: propose CSS/HTML for THIS section only in
   qa/paper-measure/<id>.patch.md. Selectors must be scoped to <id>
   (#hero, section.features, …). No global token restyle. Do not edit
   index-raw.html. Missing icons: copy SVG markup or the asset URL from
   index-raw. Do not invent a Lucide/Heroicon stand-in.
5. Pixel-perfect is optional and bounded. Load it only for this section,
   only for watch-list misses, only against the disk PNGs, one compare +
   one fix, then stop. Do not read the standalone studio body. Do not
   ask the user. Do not open Paper.
6. MUST NOT write rebuild/index.html or tokens.css. MUST NOT write
   index-raw.html.
7. MUST NOT invent 1024 / 1320. MUST NOT touch another section.
8. MUST NOT skip 2.3. A clean watch list skips the assist, not the step.

Return: id, measured, diskCompared, clipCompared, watchHits[], patch
path or none, ppPasses 0|1.
```

## Controller — apply

Apply patches in lander order (hero first). Reject a patch that:

- touches another section
- changes `--color-*` / `--font-*` names
- sets a global `* { }` / `body` / `:root` rule to “fix” one band
- invents a 1024 / 1320 breakpoint

Map measured px onto the closest 1.3 token when the value **is** that
token (`var(--text-7xl)`, `var(--radius-lg)`). Keep an exact px literal
when the dump painted off-token (hero `line-height: 92px`, overlay `right:
27px`, card `306px`). Do not invent `--color-*` / `--font-*`.

Absolute overlays stay **siblings of the photo**, `position: absolute`
inside a `position: relative` media frame. Replacing the photo with the
card, or inlining the card in document flow, fails COMPARE.

One apply + one re-shoot per changed section. Then sign the receipt.
Fail is revert-that-section, not a second pixel-perfect loop. Then walk
VALIDATE.

## VALIDATE — top-to-bottom self-correction (2.21.0)

This is the part that used to happen by hand: the operator sent one
section screenshot at a time and the agent fixed what it saw. Do that
here, before the gate, for every band in ship order. Pitfall #216.

```
for band in ship order (paper_23_validate.py . --next names it):
  SHOOT    paper_23_validate.py . --id <band> --shoot
           re-shoots <band> at 1600 / 768 / 390 (file://) and rebuilds
           qa/paper-measure/compare/NN-<band>-{1600,768,390}-side.png
  LOOK     Read all three side PNGs. 1.2 clip left, rebuild right.
           Then index-raw.html for the numbers behind what you see.
  JUDGE    per width: match | miss. A miss is layout / type / geometry /
           missing icon or overlay / invented block — the watch list.
           Sub-2px noise is not a miss.
  FIX      patch <band> only (scoped selectors, tokens where the value is
           a token, px literal where the dump painted off-token). Port
           glyphs from index-raw. Controller writes rebuild/. No Paper MCP.
  RECORD   paper_23_validate.py . --id <band> --record
             --seen "<one line: what the three sides showed>"
             --verdict 1600=match,768=miss,390=match
             --miss "768|<what differs>|<scoped fix>" --patched
  REPEAT   --shoot the next round until every width is match.
  CAP      round 3 still misses → --record … --residual "<what stays off
           and why>". One line. 2.4 reads it. No round 4.
```

Rules of the walk:

- **Look every round.** `--seen` is the proof. Empty or generic `seen`
  fails the gate. Say what differed, or why all three match.
- **One band at a time, ship order.** `--next` is the pointer. Do not
  batch-record bands you did not re-shoot.
- **A miss before round 3 must be patched** (`--patched`). Recording a
  miss and moving on is the old drop-through; the script refuses it.
- **No patch after the last look.** `--shoot` fingerprints the ship
  (`rebuild/index.html` + `rebuild/css/*.css`, minus the 2.4 QA overlay
  and the 3.x sheets). The gate recomputes it; a changed ship fails 2.3
  until you `--shoot` and Read again. Round 3 refuses `--patched` for the
  same reason — a fix nobody re-shot is invisible.
- **Caps.** 3 rounds per band. Controller only. Serial. No pixel-perfect
  inside the walk — VALIDATE replaces the second pass it was never allowed
  to run. No Paper MCP. Not 1.1 `source-site/screenshots/`.
- **No Playwright?** `--shoot` records `shotsSkipped`; compare on the
  open `file://` tab in DevTools at 1600 / 768 / 390, still `--record`
  with a real `seen`. The fingerprint rule still applies.

Receipt: `qa/paper-measure/<id>.validate.json`

```json
{
  "generatedFrom": "web2html/section-23-validate",
  "id": "hero", "nn": "01", "maxRounds": 3,
  "status": "match",
  "residual": "",
  "rounds": [
    {"round": 1,
     "shots": {"1600": "qa/paper-measure/rebuild/hero-1600.png", "...": "..."},
     "sides": {"1600": "qa/paper-measure/compare/01-hero-1600-side.png", "...": "..."},
     "seen": "768 stacks the feature cards 1-col; Paper paints 2-col. 1600 + 390 match.",
     "verdict": {"1600": "match", "768": "miss", "390": "match"},
     "misses": [{"width": 768, "what": "cards 1-col", "fix": "#hero .grid repeat(2,1fr) @768"}],
     "patched": true},
    {"round": 2, "seen": "All three match the 1.2 clip.", "verdict": {"1600": "match", "768": "match", "390": "match"}, "misses": [], "patched": false}
  ]
}
```

`status` is `match` (last round all match) or `residual` (round 3, with a
reason). Anything else keeps 2.3 open. `paper_23_validate.py . --status`
prints the table and exits 2 while a band is open.

## 1. Measure — disk, not live Paper

```
paper_23_disk_gold.py .
paper_23_clip_compare.py .  # pulls 01-slug.png at 1600 / 768 / 390
# then Read, do not re-query Paper:
qa/paper-measure/compare/NN-<id>-1600-side.png
qa/paper-measure/compare/NN-<id>-768-side.png
qa/paper-measure/compare/NN-<id>-390-side.png
rebuild/index-raw.html
```

1.1 `source-site/screenshots/` is the 3.x live scrape. 2.3 gold is the
**1.2 numbered clips** (`01-hero.png` at each breakpoint). Do not pair
against a 1.1 full-page or `section-01.png` scrape shot.

Write every number you will apply into `qa/paper-measure/<id>.json`
**before** editing CSS. A later patch without a measured source is a restyle.

### What to census (Watch)

These are the misses the Thrive run actually had. Census them on every
section that paints them — not only the hero.

| Layer | Record |
|---|---|
| **Headings** | `fontSize`, `lineHeight` (px, not unitless guess), `letterSpacing`, `fontWeight`, `textAlign`, wrap width |
| **Body / muted** | size, line-height, color token, max-width |
| **Buttons** | padding, **border-radius in px** (10 vs 8 vs pill), fill, border, label size. Do not assume `radius-full` |
| **Play / icon chips** | width × height, radius (circle vs rounded-rect), gap to label |
| **Hero / split media** | absolute image frame (`width %`, `right`, `minHeight`), green/shape band, device width + `right` / `translate` + drop-shadow |
| **Photo composites** | photo box width × height × radius; **sibling overlay cards** with `position: absolute` + inset (right/bottom/left) + size |
| **User / stat chips** | 74px avatars, name size, status color (accent vs danger), card 431×94 class sizes |
| **ul / perk vectors** | icon box px (often 22×22), fill (`--color-accent-2` yellow, not a generic green check), radius 100px, grid vs stack, gap. **Copy the glyph from index-raw** (bg SVG asset or inline svg) — do not draw a new check. |
| **Nav chrome** | compact 768/390 = logo + burger only; desktop link padding / CTA radius. Chevron from index-raw polyline, not a made-up caret. |

`get_jsx` of the lander is **2.2** (`rebuild/index-raw.html`), not a 2.3
re-dump. That file is the icon/SVG brief **and** the desktop number
brief. Run `raw_23_census.py .` before comparing. Do not dump Tailwind.
Do not snap a measured `92px` line-height onto `1.15` because it “looks
close”. Do not skip 2.3. Do not call `get_computed_styles` to re-read a
value already in the dump.

## 2. Shoot — `file://`, no server

Shared first pass (controller, once):

```sh
python3 $SKILLS/web2html/scripts/raw_23_census.py .
python3 $SKILLS/web2html/scripts/paper_23_disk_gold.py .
python3 $SKILLS/web2html/scripts/paper_23_rebuild_shots.py . --all
python3 $SKILLS/web2html/scripts/paper_23_clip_compare.py .
```

`--all` includes `<section id>` and `<footer>`. Writes
`qa/paper-measure/rebuild/<id>-{1600,768,390}.png`. Playwright Chromium,
`file://…/rebuild/index.html`, viewport = that width. Never
`python3 -m http.server`. If Playwright is missing, write the skip
receipt and still MEASURE + COMPARE against the 1.2 source clips +
index-raw (DevTools on the open `file://` tab is allowed).

After APPLY, re-shoot **only** the sections whose CSS changed. Max one
re-shoot each.

## Receipts

`qa/paper-measure/_index.json` — required by `section_22_gate.py`:

```json
{
  "generatedFrom": "web2html/section-23-paper-loop",
  "ok": true,
  "widths": [1600, 768, 390],
  "sections": [
    {
      "id": "hero",
      "measured": true,
      "receipt": "qa/paper-measure/hero.json",
      "assist": "none",
      "ppPasses": 0,
      "1600": "aligned",
      "768": "aligned",
      "390": "aligned"
    }
  ]
}
```

`assist` is `"none"` or `"pixel-perfect"`. `ppPasses` is `0` or `1` —
never 2+. Optional on the gate; required in the recipe.

Per-section `qa/paper-measure/<id>.json` must include `diskCompared:
true`, `clipCompared: true`, `gold: "disk"`, the computed
type/button/overlay/list rows you applied (from index-raw / sidecar),
`rawCompared: true`, a `raw` census (svg / bgSvg / ported dump assets),
a one-line compare note, and `ppPasses`. `measured: false`, missing
`rawCompared`, missing `diskCompared`, missing `clipCompared`, missing
`disk-gold.json`, missing `clip-compare.json`, or a missing
`raw-census.json` keeps 2.3 open.

Then the existing align receipt:

```sh
python3 $SKILLS/web2html/scripts/section_22_gate.py .
```

`qa/section-align-22.json` stays the human-readable row list. The measure
index is the proof the rows were not guessed. The `<id>.validate.json`
receipts are the proof each band was **looked at** after its last patch
(`seen` non-empty, last round match or capped residual, ship fingerprint
unchanged since that round was shot). Pitfall #216.

## Not 2.3

- Loading `/pixel-perfect` as the 2.3 driver, or walking every homepage
  section through its refine loop (Pitfall #195)
- Spawning one Paper-bound Task worker per section (Pitfall #202)
- Any Paper MCP call from a 2.3 worker, including `get_guide`
- More than one pixel-perfect pass on a section
- Workers writing `rebuild/`
- 3.x `section-diff-loop.py` vs `source-site/screenshots/` (live PNG, after 2.4)
- 3.x polish (`impeccable` / taste). Do not reload `/pixel-perfect` after 2.4.
- Opening TAGS (that is 2.4)
- A mega-pass that restyles tokens globally
- Signing `"aligned"` from a zoomed shot without index-raw numbers
- Skipping the VALIDATE walk, recording a round without Reading its side
  PNGs, batch-recording bands, a fourth round, or a residual before round 3
  (Pitfall #216)
- Loading pixel-perfect inside VALIDATE — the walk is the controller's own
  bounded re-check, not the assist's refine loop
