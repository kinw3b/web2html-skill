---
name: url-to-paper
description: Pull any live URL (or one section of it) into Paper (paper.design) as real editable layers — not a screenshot. Renders the page in headless Chromium, serializes the settled DOM to inline-styled HTML using the serializer lifted from the Paper Snapshot extension, then writes it into the open Paper file via the Paper MCP `write_html`. Triggers: "pull <url> into paper", "url to paper", "import site into paper", "snapshot this page into paper", "add this section to my paper file".
version: 1.2.86
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [paper, capture, import, dom-serialization, mcp]
    related_skills: [website-to-html, pixel-perfect]
---

> `$SKILLS` — the directory your agent loads skill packages from.
> Set it once: `export SKILLS=~/.claude/skills` (or wherever you keep them).

# URL → Paper

Import a live web page into Paper as editable layers.

Not a screenshot and not a rebuild: it walks the *rendered* DOM and emits
self-contained inline-styled HTML, which Paper's `write_html` parses into
real nodes with real text, real fills, and real type.

## Place in the pipeline — 1.2 of `website-to-html`

Runs standalone, but inside a rebuild it is **1.2**, after the contract and
light scrape have settled the homepage and before Stage L. It **replaces Stage H** (the
agent-authored harness first-pass) whenever the brief has a reachable URL —
serializing the settled DOM is evidence where Stage H was a good guess.
It does **not** mutate Paper layer names. Keep the name the scrape / HTML
already has, or omit it and let Paper name the layer.

It does **not** replace Step 0. Capture HTML still serializes remote
`<img src="https://…">` and drops `@font-face`. **Before `write_html`**,
`localize-html-images.mjs` maps those URLs onto scrape files
(`source-site/assets/` from 1.1, then `capture/assets/`) or downloads into
`capture/assets/`, then rewrites `src` to `paper-asset://<absolute-path>`.
1.1 is a fast SSR cache (images + Latin fonts only) — not a second asset
pipeline. 1.2 still downloads any remaining live images.
It also rewrites host-specific asset-reference data URIs (common
on 768/390 captures) to the same desktop file. Paper cannot load that
scheme, `file://`, or a bare relative path — the slot becomes an empty
Rectangle. `qa-paper` flags `empty-image` and `breakpoint-image-gap`
(Pitfall #58). Fonts and analysis still come from the scrape.

**Lean 1.x — do not mutate layer names (1.2.85).** `scripts/serializer.js`
keeps `layer-name` only when the scrape / HTML already has a human name
(`layer-name` or `data-framer-name` that is not a generated `pc-*` path).
Otherwise omit it and let Paper name the layer. Do **not** stamp
`pc-<section>-<child-index-path>` (or any generated path id) onto imported
nodes. Do not rename, retag, or grow a pc-id tree in the Paper file.
`test/serializer-layer-ids.test.mjs` asserts names are **not** pc-path trees.

`layer-ids.json` / `paper-layer-ids.json` are **not required** and must **not**
be written onto frames. If a sidecar still helps 1.2 QA, it is optional and
invisible. 2.0 does not join on those files. Do not revive `get_jsx`,
the deleted dump-era join scripts as a 1.2 or 2.0 path.

**Lean 1.x (live IDs stay `1.1`–`1.4`):**

1. Light scrape of the one supplied URL — HTML + images + Latin fonts only. No crawl, no screenshots, no full unicode-range dump.
2. url-to-paper captures 1600 / 768 / 390 into Paper. Do not mutate layer names. Navigation parks navbar chrome at all three widths.
3. Design Library is mined from those Paper frames and tokens bind once. No seed-retry loop.
4. Capture Tool is optional (hover/interaction 1.2 missed). Human Paper sign-off is required. Then 2.0.

When detect-sections finds no chrome, `chrome-bars.mjs` serializes compact
top + nav bars as `00-header.html` / `00-nav.html` (`layer-name="Navbar"`
when stacked). Official 1.2 parks that stack on FRAME `Navigation` via
`park-12-chrome.mjs` (relative). Never onto landers (Pitfall #168 / #110).

## Navigation at all three widths (2.10.0)

`Navigation` is a **three-take board**, not a desktop-only one:

```text
Navigation
  01 · nav-1600
  02 · nav-768
  03 · nav-390
```

Each take is serialized with the viewport **actually at that width** — set the
width, let the page settle, then serialize — so the compact bar and the burger
are captured paint rather than a reflow guess. Where the live site opens a menu
at 768 / 390, capture closed **and** open so both states reach Paper. A missing
take at any width keeps 1.2 open.

This board is the reason the 1.4 Capture Tool is **optional**: the nav and its
responsive states already exist in Paper before any human opens the extension,
and 1.3 mines them into the Design Library straight away. **Treat every run that
still needed the extension as a gap in this capture.** The target is that manual
component capture stops being necessary — each capability added here should
shrink what 1.4 is still for.

Nothing at 1.2 is model-authored. The old "author `home-768` / `home-390` from
desktop" pass is retired: all three landers are captured through this same path.
If a breakpoint frame is wrong, fix the capture — never hand-build the frame.

Section roots keep their band name — `assemble-lander` still labels the
first created node `01 · hero-area` for review sequence. That is a section
band, not a generated path id.

Downstream: `design-library/` feeds **1.3** tokens (signed at **1.4**) and **2.2** bind.

**Pre-pesticide (1.2.29) + per-section SOURCE shots (1.2.82).** Before `experiment-capture-home.mjs` / `assemble-lander.mjs`, run the live overlay on `/` (homepage only by default). It is the smart sibling of rebuild `qa-overlay` (end-of-build Pesticide outlines): pre = live DOM contract; post = rebuild outlines. HUD root is `x-paper-prepesticide` so the serializer skips it. Writes `pre-pesticide.json` (sections / images / forms / landmarks) so 1.2 can diff “live had N imgs in a named section, Paper has 0”. Pitfall #70. At **1600 / 768 / 390** the same session clips each detected section **with pesticide outlines on** into `capture/home-{desktop,768,390}/source-sections/01-hero.png` + `01-hero.json` (same `section-ids.mjs` ids; files stay `NN-slug` at every width). `seed-source-board.mjs` stacks the **1600** rows on one `Screenshots` review board under `Ruler · desktop`: **no Headings/title row** (the artboard name already reads Screenshots, so `01` is the first child), each `NN · slug` as a **red section-number** + **1px solid** 1600 shot. Clips are taken with `scale: "css"` and every row is capped at `SOURCE_SHOT_MAX_WIDTH` **1600** (downscale only, ratio kept), so the board lands ~1744 wide next to `home-desktop` — visible Chrome on a Retina Mac ignores `deviceScaleFactor: 1` and would otherwise write 3200px clips and a 3344-wide board. Pitfall #119. **No Hover States column, no grey well, no red divider.** Hover pairs stack on FRAME `Hover States`. Board and rows are `height: fit-content` / `overflow: visible` (board gap 16 / row gap 16 / pad 24). **Never** a single full-page source shot. **No 768/390 source boards on Paper** — those clips stay on disk. Destroy the HUD before any serializer write. Pitfall #65. This is **not** the P-0 canvas ruler.

**Review sequence (1.2.64).** After the shots exist, number Paper
`01, 02, 03…` for the **content** bands — not capture-time chrome.
`01` is hero + navigation (nav stays `01 · nav` beside `01 · hero-section`).
Overlay bars are not numbered. `apply-review-sequence.mjs` renames Source
rows + desktop layers and writes `review-sequence.json`. Hover reads that
file. Hidden Playwright captures all three landers, then clips 768 / 390 shots
on disk. **Do not author `home-768` / `home-390` from desktop**
(`web2html/references/12-desktop-source.md`). Hide every `x-paper-*` overlay
before Playwright clips (Pitfall #104). Do not open Hover until this
sequence is on Paper.
The 1.2 automatic geometry postflight runs after **Send to Paper**. Stretch-root
and breakpoint-shot-qa stay required. `layer-ids-census.json` is optional
and invisible — 1.2 does not fail on it and 2.0 does not join on it. Then 1.3
mines the Design Library from those frames. It does not wait for Capture Tool
**Done**.

**P-0 · Canvas ruler (HARD GATE, 1.2.25).** Paper has no native guides.
The **first and only P-0 artifact** is `Ruler · desktop`. `Design Library`
does not exist before 1.3. Do **not** draw
`Ruler · 768` or `Ruler · 390`. Everything else sits **in one row**
under that bar, left to right:

1. `Screenshots` (section-number + shot, **50% opacity**)
2. `home-desktop` (captured)
3. `home-768` (captured at 768, not authored from desktop)
4. `home-390` (captured at 390, not authored from desktop)
5. `Buttons` (legacy name `Hover States`)
6. `Components`
7. `Navigation` (serializer chrome parks here during collect — all three widths)

Do **not** seed `1.3 hover pairs · {page} · states`. Draw the ruler **before** any page or source shot.
`assemble-lander.mjs` / `import-sections.mjs` do this.
On an empty file: `node scripts/draw-rulers.mjs --file $PAPER_FILE_ID --init`.
That `--init` creates the ruler only. Content hangs **≥100px below** the
line. The lintel is **20000px** wide so later pages and review frames
have room. `ensureRulers` re-pins width + Y and deletes leftover
breakpoint bars. Ignore rulers, A/6, and
`Interactive components` when computing lander `rightEdge` — **do not**
ignore `Source · {page}` (desktop parks to its right). Never
`create_artboard` content on a ruler-less canvas. `create_artboard`
ignores `left`/`top` — pin with `update_styles`. Pitfalls #37 #42 #72
#73 #74.

**Single-mine 1.3 + token-pass (1.2.72).** After the 1.2 Paper frames exist, run
`run-design-library-step.mjs`. It does not wait for Capture Tool Done. It
inventories every eligible frame once, mines colors and font families/weights/styles once, creates
exactly one foundations-only `Design Library` first in the row (ahead of `Source`), replaces the
Paper token set with one deduplicated canonical set, then
`apply-theme-tokens.mjs` walks `{page}-(desktop|768|390)`
landers (`home-desktop` and extra routes such as `homepage-desktop`) +
`Design Library` + FRAME `Navigation` (and Buttons / Components frames if they already exist): `Buttons`, `Components`,
legacy `A/6 · {page} · states`, and `Interactive components`.
Only exact value matches bind; near matches remain unchanged and are reported
as intentional literals. `token-geometry-guard.mjs` compares the full pre/post
census and fails movement, resize, wrapping, font-size, line-height, or flex
sizing drift. Generate → token-pass. Specimens use `var(--token)`, not raw px/hex.
`--list-targets` must include every frame that exists in the file.
Token writes upsert by name; use `--replace-tokens` once to remove duplicate
names left by older append-only runs before recreating the canonical set.
**Never run `flatten-paper-buttons.mjs`.** Leave imported scrape / Paper
names alone (Pitfall #131).

**Build comment remediation (1.2.78).** `list-paper-comments.mjs` is the
Build gate at 2.1 and after the 2.4 TAGS checkpoint: exit 2 while any Paper
thread is open. Apply every pin without waiting for permission, fix the
matching build output, resolve it, and re-run. Before 3.0, save the zero-open
report as `qa/build-paper-comments.json`, record the work in
`qa/build-comment-remediation.md`, and request final build approval
(`qa/build-final-review.md`). The user prompt does not waive this
(Pitfall #132).

**HARD (Pitfall #158).** Design Library is created/updated **only** by
`run-design-library-step.mjs` → `render-library.mjs --kind foundations`
(`templates/library/foundations` ← `library-sheet.mjs` ← `tailwind-defaults.mjs`).
**Forbidden:** `write_html` / `create_artboard` of a hand-built “Design Library”
or any substitute sheet. If node/1.4 scripts cannot run, **STOP** and say so —
do not invent a frame. `mark` 1.4 requires `qa/design-library-step.json` from
that writer. Gate: `library_14_foundations_gate.py`.

**1.4 creates Design Library once.** The authoritative command is:

```bash
node scripts/run-design-library-step.mjs \
  --project /path/to/project --file $PAPER_FILE_ID
```

The command refuses a missing 1.3 Extension Done receipt, missing eligible frames, or a
pre-existing/multiple final `Design Library`. It prints `[1.4] starting …`
before each child, heartbeats while that child is alive, and **kills** a child
that stays silent for 20s (4-minute hard cap) — Pitfall #112. Seed screenshots
are allowed 90s of quiet so `get_screenshot` is not killed mid-band. Do not sit on a
silent mine. It renders the five foundations
templates (`01-header` … `05-elevation-radii`) after the mine, then parks the
new artboard first in the row (ahead of `Source`). After bind it pairs each
1600 / 768 / 390 `source-sections/NN-*.png` with the matching lander band and
rebinds up to 3 times if color, type, or layout drifted. Missing any clip dir fails
1.4. Do not dump those PNGs into Paper. 1.5 remains the human walk
(Pitfall #156).

**Layout gold** (shell only — do not copy its brand):
The local `templates/library/foundations/` package is the layout gold. Do not copy
its display face / accent into other projects. Do not `duplicate_nodes`
from that file.

Mine colors + families / weights / styles; leftover SEMANTIC roles only if
that exact hex appears, then floor to at least five Tailwind semantic colors
(danger / warning / success / info / muted). Do **not** rebuild spacing /
type sizes / radius / elevation. Do **not** create a second `Design Library`.
DISPLAY is 7xl–12xl (72 / 96 / 128 / 160 / 192 / 224). Specimens are `Aa`
in the primary sans, large → small, four color swatches per row. Do not add
`--text-display` / `--text-display-xl` names. `assertFoundationsContract`
fails extract/render if the five SEMANTIC colors or `--text-10xl`…`12xl`
are missing.

**Flatten abs decorations (1.2.26) + trim phantom borders (1.2.27).** Before every `write_html`, `flattenDecorativeAbs` hoists empty inset `position:absolute` strokes/fills/**CSS gradients** onto the parent (`border: 1px solid`, `background-image: linear-gradient(…)`, hairlines, radius) and drops the floater. Then `trimPaperStyles` drops source borders CSS does not paint — orphan `border-*-width`/`-color` with no style, and `border: 1px solid rgba(…, 0)`. Paper otherwise turns those into black / `#2A2A2A` boxes on nav and footer text links. Real strokes stay. Pitfall #57. 1.3 hover HTML uses the same helper via `prepareStateHtml` — do not leave button strokes or hover fills as floating Frame+Rectangle layers (Pitfall #95). Paint is `background-color` on the pill. `collapseAnimatedLabelStacks` drops source text-swap duplicate labels. `qa-paper` flags leftovers as `abs-decoration`. `flatten-paper-abs.mjs` also walks `1.3 hover pairs · {page} · states`. Never ship a sibling `Desktop section IDs` legend — desktop layers are named `01 · slug` (Paper has no `create_comment`). Pitfalls #40 #41 #56.

**P-0c · Merge split headings (1.2.31).** After 1.2 import, `qa-paper` flags source line-box titles still stacked as sibling Text nodes **or one-Text row Frames** as `split-heading` (high; optional later `qa-paper`, not the 1.2 postflight). The walk starts at each named section (`01 ·` / `02 ·` …) so feature headings are not missed; scribble `SVG` + `Path` / `SVGVisualElement` children are decorations, not extras. Repair with `merge-split-headings.mjs` (`--artboard <id>` or whole-file landers): one Text node, full copy, `text-align: center` when the live heading is centered; heading SVGs `position: absolute` + `data-decorative` + `pointer-events: none`. `set_text_content` uses `{ updates: [{ nodeId, textContent }] }`. Pitfall #69. **Paper font tokens (1.2.53–1.2.54).** `create_tokens` / `set_tokens` `fontFamily` values are a native catalog face from this scrape — never a CSS stack. `get_font_family_info` on the bare names before write. Unavailable faces skip or fall back to a catalog face Paper can run and are recorded; do not invent a font. `library.json` / rebuild keep the full CSS stack + fallbacks so HTML can load installed / `@font-face` files. Pitfall #88. **Sheet + lander bind (1.2.54).** Design Library `theme.sans` / `display` / `mono` and family Aa are catalog faces from this scrape, not stacks or unbound `var(--font-serif)`. After `create_tokens` and `write_html`, `bind-paper-fonts.mjs` / token-pass maps System Sans-Serif / generics / stacks on Text to the matching token. `qa-paper` `unbound-font` (high) fails 1.4. Do not skip the bind because a previous URL was refused. Pitfall #89. See `references/paper-font-bind.md`. **Overlay paint order (1.2.52).** After flatten+trim and before every `write_html`, `reorderOverlayPaintOrder` stacks image → dim overlay → type last so Paper last-sibling paint cannot bury copy (Pitfall #84). Do **not** clone the overlay on top. `qa-paper` flags leftovers as `overlay-covers-type`. Repair already-written landers with `fix-overlay-paint-order.mjs` (apply on the current file). **Assemble / repair (1.2.32).** After any `write_html` insert into a named section, hug that section with `update_styles` `{ height: "min-content" }` — do not guess a new px height (Pitfall #67). Never put `paper-asset://` in `write_html` (it hangs Paper); use the live image URL from this scrape (never `paper-asset://` inside `write_html`). Image QA is visual vs live at 1600 / 768 / 390, not only `qa-paper` empty-image: inventory `deferred-image`, empty `SVG` in a ~50–107px circle, and `file` Rectangles with no fill (Pitfall #68). **Box metrics, not wrap (1.2.39).** Match icon size + icon container box + gap from the live/pre-pesticide inventory at that width. Do **not** copy `flex-wrap` / `round(46%)` / 2+1 from 768 onto 1600/1440. `home-desktop` stays 3 columns, no wrap. Tablet/mobile wrap is breakpoint-correct. There is no wrap-copy helper in detect/assemble — do not invent one. Pitfall #75. Never ship a sibling `Desktop section IDs` legend — desktop layers are named `01 · slug` (Paper has no `create_comment`). Pitfalls #40 #41 #56.

In the `flow-skills` mirror this is `1.2 url-to-paper`; the canonical directory
name stays unnumbered because that name is the skill identifier.

## Requirements

- **Paper Desktop.** The MCP server is bound to the Paper app process, not a
  background daemon — quit Paper and port `29979` closes. `ensure-paper.mjs`
  handles this: it probes the port, runs `open -a Paper`, and waits (observed
  ready in ~2s, restoring its last file). Full autonomy from a closed Paper is
  verified; `create_file` / `open_file` do the rest. Paper Desktop itself is
  macOS; capture scripts also run on Linux agents.
- `playwright-core` + a cached Chromium (see Setup).
- macOS or Linux for capture. Clipboard fallback (`osascript`) remains Mac-only.

## Setup (once)

```bash
claude mcp add paper --transport http http://127.0.0.1:29979/mcp --scope user
cd $SKILLS/url-to-paper && npm install playwright-core
```

Chromium is auto-detected from `~/Library/Caches/ms-playwright/` (macOS) or
`~/.cache/ms-playwright/` (Linux). On Linux agents, set an explicit binary:

```bash
export PW_CHROME=/usr/bin/google-chrome   # or chromium / playwright chrome
```

If `mcp__paper__*` tools aren't in the session (MCP added after startup), use
`scripts/paper-mcp.mjs` — it speaks JSON-RPC to the endpoint directly and needs
no restart. Native tools are preferred when available.

## 1.2 capture — headless, one page

**1.2 is `hover-reel/scripts/capture-session.mjs`** (in the hover-reel skill, not this one). It is headless and imports exactly one
route: `/`. 1600 / 768 / 390 are viewports of that page, not extra pages —
never `/contact`, `/features`, `/pricing`, `/blog` unless the user names
those routes **and** passes `--allow-multi-page`. Do not raise capture width
to "finish the template."

The visible-Chrome, multi-page `discover-urls.mjs` / `site-to-paper.mjs` /
`arrange-artboards.mjs` workflow this section used to document is retired —
capture never opens a browser window; navbar/hover/component capture belongs
to the 1.4 Capture Tool extension, which does open one on purpose.

### Automatic geometry postflight — end of 1.2 (1.2.71)

After the headless collect writes the landers and seeds the three Capture Tool
frames, `capture-session.mjs` runs this postflight before Step 1.2 exits. 1.2
opens no browser window; navbar, dropdown, and hover capture are 1.3 in the
Chrome Capture Tool extension:

1. Run `stretch-root.mjs --prove` on the homepage artboard (`--artboard home-desktop`).
2. Write `qa/stretch-root-evidence.md`.
3. Fail 1.2 only if the stretch proof fails. Do **not** run `qa-paper.mjs` here. Do not auto-run `merge-split-headings.mjs`.

After 1.4, **1.5 is the missing-elements check** — the human compares
    source-section clips to named Paper sections and pins comments. Do **not**
    run `run-missing-elements.mjs` as a numbered step. `childCount > 0` is not
    a page-order pass (Pitfall #82). Optional diagnostic only if the human
    asks: `references/missing-elements-playbook.md`.

2. Keep `capture/<page>/fullpage.png`. Open it if chrome is missing from layers.
3. Do **not** import `{page} — source screenshot` unless a person asks.

**FAIL the pipeline** if Paper sections are misplaced, overlapping, clip
children, or a heading is still split into stacked Text siblings
(`split-heading`, Pitfall #69). Repair with `merge-split-headings.mjs`, then
re-run `qa-paper`. A missing Paper sibling JPEG is not a fail. First
`index.html` = 2.1 frontend-design of the **QA-passed** homepage only. Do not revive `get_jsx`.

**Watch for near-duplicate routes.** Many templates ship variant pages
(`/about` and `/about-boxed`) that are byte-identical at desktop width. Do not
import them.

## Paper writes stay serial

**The Paper import phase stays serial, on purpose.** Paper fetches every remote
image while parsing, and that fetcher is the bottleneck: ten writes fired back
to back already produced broken images while every call reported success.
N agents writing concurrently makes that strictly worse and the failure is
silent. Do not "speed up" the import by parallelising it.

## Always pin `--file-id`

Paper routes calls to a *sticky* active file, which changes when the user clicks
another file in the UI. Observed: an extraction run silently mined
"Welcome to Paper" instead of the site file. Every script accepts `--file-id`,
and `extract-library.mjs` also takes `--expect-file <substring>` as a guard that
refuses to run against the wrong document.

## Policy — new Paper file at 1.2

Keep **one Paper file per run**, created at 1.2, named `{project-slug} {YYYY-MM-DD HHMM}`.
Desktop lander, mobile lander, QA pairs, hover/component states, and the design library
are named artboards **inside that new file**.

- `capture-session.mjs` always `create_file`. Omit `--file`.
- Never `list_files` to resume a similarly-named existing document.
- Never `open_file` last week's "Thrive" / "kp-thrive" because the slug matches.
- Pin the **created** id from `qa/paper-file.json` for the rest of **this** run.
- Do not split desktop, mobile, experiment, hover, or library work into
  separate Paper files later in the same run.
- Pitfall #187.

## Design library extraction

```bash
node scripts/extract-library.mjs --file-id <id> --expect-file <this-project-slug> \
  --depth 10 --json library.json [--write-tokens] [--min-uses 3]
```

Read-only unless `--write-tokens`. Produces the source of truth a rebuild
targets instead of re-inlining styles.

**Mine colors, fonts, and styles. Tailwind utilities for type sizes, spacing,
radius, and elevation.** Do not walk every node to invent `--text-3xl: 56px`
or a snapped-gap census. A later rebuild maps a Paper dump’s measured px
value to the **closest Tailwind class** (`closestFontSize` / `closestSpacing`
/ `closestRadius` in `scripts/tailwind-defaults.mjs`).

| Token group | Source |
|---|---|
| Color | Mined fills and text colors (luminance / saturation roles; near-dupes merge **only when RGB and alpha match**). Opaque `--color-accent` is named before a more common 10% wash (`--color-accent-soft`). A re-run restores those paints from capture HTML when Paper already collapsed them onto one var **and that node still has a fill**. Never invent a fill on a transparent 1.2 frame. Pitfall #154 #157 |
| Font family | Mined (`--font-sans`, display/serif/mono if present). Weight-suffixed faces collapse (`Family-Bold` → the regular family name). **Paper** stores the bare catalog face from this scrape; **build** keeps the CSS stack + fallbacks. Call `get_font_family_info` before `create_tokens` (Pitfall #88). Sheet / lander `write_html` also uses the catalog face — never the stack (Pitfall #89) |
| Font weight / style | Mined (`--font-weight-bold`, `--font-style-italic`). Paper has no `fontStyle` token type — styles stay in `library.json` + the sheet |
| Type **sizes** | Tailwind `text-xs` … `text-12xl` (sheet is large → small; 7xl–12xl labeled **DISPLAY**; specimens `Aa` in primary sans) |
| Spacing | Full Tailwind 4px scale through `96` / 384px. Paper names use a hyphen for dots (`--spacing-0-5`); `step` keeps `0.5` |
| Radius / elevation | Tailwind default radii and shadows. Shadows are CSS / `library.json` only — `create_tokens` has no shadow type |

Structure comes from `get_tree_summary` at `depth: 10` — **one call per
artboard** instead of one per node — then styles are batched 60 at a time
for **colors and fonts** (and component fingerprints). Spacing / type-size /
radius / elevation tokens do not read those computed values.

**Token naming for colors is derived from measurement, not frequency.** Ranking
by count produced `--color-primary: #FFFFFF` (white is merely the most common
background). Roles now come from luminance and saturation, with separate rules
for surfaces and text — a dark brand teal is body copy, not an accent. Near
duplicate colours merge (`#0E2C35` → `#0D2C35`, one hex apart) **only when
alpha matches**. `#EF4B3C` and `#EF4B3C1A` stay two tokens; the opaque fill
is `--color-accent` even when the wash is more common (Pitfall #154). If 1.4
already bound both to one var, the next mine reads capture HTML (rgb vs rgba)
and restores those Paper nodes from capture HTML before bind only
when the Paper node already has a fill. An optional sidecar is never required. Do not stamp capture-HTML ancestor
fills onto unpainted frames (Pitfall #157). Family
role comes from the name, so Vollkorn is `--font-serif`, not the `--font-mono`
that index-based naming produced.

**`create_tokens` has no shadow type** (and no `fontStyle` type). Shadows and
font styles are reported for the rebuild / sheet but are not registered as
Paper design tokens. Supported types: breakpoint, color, container,
fontFamily, fontSize, fontWeight, letterSpacing, lineHeight, radius, spacing.
Names cannot contain `.` — `--spacing-0.5` fails; write `--spacing-0-5`.

**Paper `fontFamily` is a native face, not a CSS stack (1.2.53).** Mined
`value` stays the CSS stack + fallbacks for HTML / `tokens.css` /
`library.json`. `paperValue` / `paperCreateTokens` send the catalog face
(the exact name `get_font_family_info` returns). If the catalog is down, still
send the bare family — never the stack. If the face is unavailable,
skip or fall back to a confirmed face
(the catalog face Paper can run) and record it. Do not invent a font. Seed
`--font-sans` labels can stay `--font-sans`; the stored Paper value is
that catalog face. Pitfall #88. Different from #25 (weight-suffixed faces in
`write_html`).

**Sheet + lander Text must actually wear that face (1.2.54).**
`theme.sans` / `theme.display` / `theme.mono` on Design Library HTML are
catalog faces from this scrape, never a CSS stack. Family
Aa is `font-family: <catalog face>` plus `data-font-token="--font-serif"` — not
`var(--font-serif)` alone (Paper inspector otherwise stays System
Sans-Serif while the caption names the intended face). The family **name**
(`Inter`, `DM Serif Text`) is ink at `--text-xl` / 600 in that face; the
token name is the caption. The FAMILIES heading is ink at `--text-sm`, never
a light accent. After `create_tokens` and any
`write_html`, run the font bind (`bind-paper-fonts.mjs` or token-pass).
`qa-paper` `unbound-font` (high) fails 1.4 if library
typography Text is still System Sans-Serif / generic / a stack. Pitfall
#89. `references/paper-font-bind.md`.

### Component detection — three guardrails, all learned the hard way

**Identity is by ROLE, not geometry.** Width is excluded from the signature.
Including it made five nav links (33/44/58/59/62px — one component holding
different words) register as five components. Height buckets to 8px and a style
fingerprint (font, colour, radius, shadow, border) separates genuinely different
things. Each role reports `widthVariants` and `variantNodeIds` so you can still
clone every variant deliberately. Effect: 186 signatures → 153, with the nav
link collapsing 15 widths into one atom.

**Rank by instances, not page count.** Sorting by pages let site chrome (nav and
footer, present on all 6 pages) crowd out every content component — the first
run reported 30 components and **not one card**. Cards repeat *within* a page,
which is just as strong a signal. The report now carries per-level lists
(`atoms`, `molecules`, `organisms`) plus `inPage` for content components, so
chrome can't starve them.

**Never mine generated artboards.** Names matching `LIBRARY` / `Design Library` / `qa-` are excluded.
Re-running after building the library fed its own swatches and spec cards back
in as site components (1480 → 2366 nodes).

Verified on the reference site: the footer and both nav bars as organisms, plus
the team-member card (291×443) and blog card (346×423) that the first pass
missed entirely.

### Scales are Tailwind defaults, not a capture census (1.2.29–1.2.35)

Walking every frame for gap / padding / `fontSize` / radius / shadow produced
a measurement report (raw px + drift + use-counts) and an invented scale
(`--text-3xl: 56px`). That is expensive and the wrong source of truth.

Ship the default Tailwind scale as a **specimen** (token name + value +
bar/swatch). Colors, families, weights, and styles stay unique to the design.
When HTML is built, map a measured value to the closest Tailwind class — do
not invent a custom scale from the capture. Pitfall #64.

**Painted layers bind Paper tokens (1.2.30).** Foundations HTML uses
`font-size: var(--text-6xl)`, `color: var(--color-ink)`,
`font-family: var(--font-sans)`, `width: var(--spacing-32)`,
`border-radius: var(--radius-lg)` — not a hardcoded `60` / `128`. The px
value is a caption only. If `write_html` strips `var()`, `render-library.mjs`
rebinds with `update_styles` (tokens as CSS variables).

**Display / XXL titles (1.2.68, every run).** The type sheet always
registers `--text-7xl` 72 through `--text-12xl` 224 (7xl–9xl are Tailwind
defaults; 10xl / 11xl / 12xl are 160 / 192 / 224). Those rows are labeled
**DISPLAY**. Scale order is **large → small**. Specimens use the primary
sans and the glyph `Aa`. Do not add `--text-display` 160 or
`--text-display-xl` 192. A larger measured value stays literal unless it
exactly matches a registered token. `apply-theme-tokens` maps a 72px hero
to `var(--text-7xl)` and a 160px title to `var(--text-10xl)`.

**1.4 token-pass (1.2.66, authoritative single mine).** After 1.3 Extension Done,
`run-design-library-step.mjs` mines newly parked Capture Tool content together
with every eligible lander exactly once, then creates Design Library. 1.4 is
not done until landers and all Capture Tool frames consume exact matches from
the canonical token set. **Census, not sample** (Pitfall #76). Walk
**every** node on `{page}-desktop` / `{page}-768` / `{page}-390`
(`home-desktop` and extra routes such as `homepage-desktop`),
`Buttons`, `Components`, `Navigation`, legacy
`A/6 · {page} · states`, `Interactive components`, and `Design Library`.
Map a painted style only when its resolved value exactly equals a registered
token. Never snap a near value to the closest token in Paper. Never write
`backgroundColor` / `fill` onto a node whose current Paper fill is transparent
or onto a wrapper that already contains two+ named `NN ·` sections (Pitfall #157).
Unmatched
`fontSize` / `fontFamily` / `fontWeight` / `color` / `fill` / `gap` /
`padding*` / `radius` values remain unchanged and are listed as intentional
literals.
Empty / System Sans-Serif / generic / CSS-stack `fontFamily` on Text is
`unbound-font` and must bind to the matching catalog token (Pitfall #89).
Only the skip taxonomy may stay raw — and each must be listed:
images (`skip-image`), decorative scribble px pins (`skip-scribble`),
spacing **>128** with no token, spacer widths with no exact token (do
not resize). `Source · home` (JPEG outlines) is out of scope and still
counts as `skipped-board`. Anything already `var(--…)` stays. Shadows
stay CSS if Paper has no shadow token. Writes `qa/token-pass.json` **and**
`qa/token-pass-qa.json` (`nodesTouchedCount`, `propsReboundCount`,
`leftovers[]`, `coverage: { treeNodes, accounted, missing[] }`).
Tree minus the QA file, or `missing.length > 0`, or an unlisted raw
hex/px outside the explicit leftover taxonomy, **fails the run** (exit
non-zero). `token-geometry-guard.mjs` also fails any pre/post movement, resize,
wrapping, typography, or flex-sizing drift (Pitfall #108). After bind, stop.
Do not re-run `validate-library-seed.mjs` / `apply-theme-tokens.mjs` in a
retry loop. Color-wash, color-spill, or layout shift is a 1.4 human pin, not
an automatic rebind (Pitfall #156). Do not
`write_html` the source PNGs. 1.4 remains the human missing-elements walk.
If `apply-theme-tokens.mjs`
is missing locally, fail — do not silently `update_styles` a subset.
This is **not** 2.0 / `get_jsx`.

**Semantic leftover colors (1.2.68).** After brand colors are mined,
register leftover homepage / A/6 hexes into a fixed **role** set so
token-pass does not leave orphans. Then **floor** every run with at least
five Tailwind semantic colors (`red-500` danger, `amber-500` warning,
`green-500` success, `blue-500` info, `gray-500` muted). A leftover hex
overrides the floor when it matches. Colour swatches are **four per row**.

| Token | When |
|---|---|
| `--color-danger` | Leftover error red, else Tailwind `#EF4444` |
| `--color-warning` | Leftover amber, else `#F59E0B` |
| `--color-success` | Leftover green, else `#22C55E` |
| `--color-info` | Leftover blue, else `#3B82F6` |
| `--color-muted` | Leftover gray, else `#6B7280` |
| `--color-surface-alt` | Near-white that is not `--color-surface` (`#FBFBFB`) |
| `--color-surface-muted` | Light grey fill (`#F2F2F2`) |
| `--color-text-subtle` | `#999999` |
| `--color-text-secondary` | `#666666` (distinct from mined `--color-text-muted`) |
| `--color-ink-soft` | `#333333` or `#111111` (whichever appears) |
| `--color-ink-strong` | The other of `#333333` / `#111111` when **both** appear |
| `--color-overlay` | Alpha hex (`#1D2B19B3`) if Paper accepts 8-digit; else solid `#1D2B19` |

`#FFFFFF` stays `--color-surface` and does not also become surface-alt.
Foundations swatches bind `var(--color-danger)` / `var(--color-warning)` /
`var(--color-success)` / `var(--color-info)` / `var(--color-muted)`.
The colour sheet splits SURFACE & UI and TEXT into labeled **MINED**
(brand) and **SEMANTIC** (roles + Tailwind floor) groups; each swatch carries
a MINED / SEMANTIC badge. Do not dump them in one mixed grid.

**1.4 headings · `text-wrap: pretty` (1.2.33, required).** Titles must
use CSS `text-wrap: pretty` so orphans do not sit on the last line.
`apply-theme-tokens.mjs` sets `textWrap: "pretty"` on heading Text nodes
when the layer name contains `heading` / `title`, the font-size token is
`--text-xl` and up, or computed `fontSize` ≥ 28px. Do **not** set it on
body / nav / footer / button labels. This can change wrap vs the
source/Paper capture — prefer correct CSS at 2.1 over pixel-identical
line breaks (Pitfall #65). Keep `text-wrap: pretty` on the Paper node;
nothing downstream may strip it.

```bash
node scripts/apply-theme-tokens.mjs --file-id $PAPER_FILE_ID \
  --library design-library/library.json \
  --json qa/token-pass.json --qa qa/token-pass-qa.json
```

Treat mined color / font names as **proposals to confirm** — the report
carries `uses`, `luminance`, and `saturation` so each call is auditable.

### The library KIT — do not re-author the layout

`templates/library/**` holds the reusable shells. **Render them; do not have an
agent write the sheet from scratch.** The first build cost two agents ~75k
tokens and ~50 tool calls each to produce a layout that is identical for every
site — only the data changes.

```bash
# preview to disk, zero Paper calls
node scripts/render-library.mjs --library library.json --kind foundations \
  --dry-run --out-dir rendered/

# 1.4 — one mine, one Design Library, guarded exact-match binding
node scripts/run-design-library-step.mjs \
  --project /path/to/project --file <id>
```

There are **three render modes**. Pick by what you're producing:

| `--kind` | Produces | Agent needed |
|---|---|---|
| `kit-foundations` / `kit-components` | Neutral starting base — greyscale placeholders, names only, no site data | none |
| `site-components` | Real components cloned from the imported pages, clean name-only labels | none, once you have an inventory |
| `foundations` / `components` | Scale specimens (token + value + swatch) plus mined colors/fonts | none / slots only |

**Do not render `site-components` or `kit-components` as a finished library.**
Those modes dump isolated atoms-in-boxes (`LIBRARY — Components`, ButtonPrimary
tiles, FAQ atoms). That is forbidden. Default finished library is
`--kind foundations` on **`Design Library`** only. If you still have an
inventory script, do **not** write it onto the canvas.

`kit-*` needs no `library.json` at all — the placeholder inventory lives in
`render-library.mjs`, so changing what a fresh library starts with is a one-line
edit.

**The theme is derived, never hard-coded.** `deriveTheme()` pulls ink, accent,
surfaces, border, muted and the two families out of the mined tokens; templates
reference `{{theme.*}}` only. Two derivations worth keeping:

- The **sans** token often names a weight-specific face (`Family-Bold`), which
  would set the whole sheet bold. Strip to the base family.
- The **accent** is the colour that *contrasts* with the ink, not the most
  saturated one. Picking by saturation chose a dark teal (0.76) over the site's
  gold (0.51) — but that teal shares the ink's hue, so it reads as brand base.
  Score by `chroma × hue-distance from ink`.

Templates use `{{value}}`, `{{#each list}}…{{/each}}` (fields as `{{.field}}`),
and `{{#if path}}…{{/if}}` so sections vanish cleanly when a site has no data
(e.g. no radii). The engine does **not** support nested `{{#each}}` — flatten to
explicit blocks instead.

### Presentation rules — three things that went wrong

**Containers must FIT their component. Never use a fixed cell.** The first
version used uniform boxes (400×480 cards, 214×104 buttons) with
`overflow:hidden`, so anything larger was silently cropped — a 627×252
testimonial card lost its right third, a 490px form-submit button was clipped in
a 214px slot. Because the inventory already resolves real geometry, size each
container to `component + padding` and set `flex:none` on both container and
clone. Regions get **no minimum height** so a 46px announcement bar isn't padded
out to the same box as a 614px footer. Accept the taller artboard; showing a
component at true size matters more than a tidy grid.

**Labels are the component name and nothing else.** Id chips, dimensions,
instance counts, page counts, variant counts, descriptions and correction notes
all belong in `library.json`, not on the sheet. They doubled the artboard height
and buried the components. Keep provenance in the report; keep the canvas clean.

**Buttons are their own section, never atoms** — with a `default` (live clone)
beside an empty dashed `hover` slot, each sized to that button. A static DOM
capture cannot record hover, so state that on the sheet and leave the slot empty
rather than inventing a hover style.

Chrome stays neutral greyscale even on a real-site sheet, so the labels read as
spec-sheet furniture instead of competing with the components.

### Choosing what goes in — the agent's actual job

**No "Components" artboard / no isolated component sheet.** Do **not**
create or render:

- `LIBRARY — Components`
- a "Components" section of isolated buttons/cards/FAQ atoms
- `site-components` / `kit-components` dumps of atoms-in-boxes

- **`Design Library`** — **foundations only**. Fonts, type hierarchy, colors,
  spacing, radius. Every chip is labeled with the **CSS variable root name**
  (`--color-ink`, `--text-base`, `--spacing-8`, `--radius-sm`). No cloned
  nav/cards/buttons. No invented sample copy or a second type family.
- **`Theme Library`** — optional. Prefer **none** if Design Library + the
  homepage artboard already hold the truth. If it exists = tokens + **full
  page regions cloned from the homepage** (Nav, Footer as they appear on
  the page), **not** a catalog of detached ButtonPrimary / FeatureCard tiles.

`Design Library` is absent until 1.4 creates it after the completed-frame mine.
Do **not** append `site-components` onto it or create another.

**Do not produce a component-tile inventory for the canvas.** `library.json`
may list tokens and homepage **sections**. It must not drive a
`site-components` / `kit-components` render. Nav and Footer stay on the
homepage artboard (or, only if needed, as **full regions** on Theme Library).
Buttons, cards, FAQ rows stay in place on the page. A library of isolated
tiles is a process failure.

**Verify before you place.** Structural signatures find repeats reliably but name
them badly: labels come from whichever page a node was first seen on. Check each
candidate with `get_node_info` / `get_tree_summary` / `get_screenshot`, give it a
real name (`blog-card`, `nav-link`, `stat-block`), and annotate corrections on
the card. Past runs correctly caught a "CTA button" that was only a label
wrapper and a "footer link" that was an address line.

**Mark near-white components `dark: true` in the inventory.** They are invisible
on a light card and need the site's ink ground. Clones of SVG and image-fill
nodes also stretch to fill a flex parent unless given explicit
`width`/`height`/`flex:none` — the renderer does this, so don't undo it.

Instance counts, sizes, page coverage and node ids stay in `library.json` and
the agent's report — **not on the sheet**. See the presentation rules above.

**Spacing / type-size / radius / elevation on the sheet are the Tailwind
default scale**, not a snapped census of this file. Do not print `uses`,
`raw · drift`, or a “Paper has no shadow type” essay on those rows. The
library is the rebuild's source of truth; a 15px dump maps to `--spacing-4`
(16px) at build time, it does not become its own token.

## QA pass

```bash
node scripts/qa-paper.mjs --depth 4 --json qa-report.json [--shots qa/] [--artboard <id>]
```

**1.2 geometry postflight / A/5-R** (automatic before 1.3; Design Library is still absent):

```bash
node scripts/run-geometry-postflight.mjs \
  --project /path/to/project --file "$PAPER_FILE_ID" --artboard home-desktop
```

Capture freezes section roots at the viewport px. `stretch-root.mjs` sets
those (and nested full-bleed wrappers) to `width: 100%`, pins site containers
to `max-width: <measured>`, then `--prove` widens the homepage artboard and
checks sections follow before restoring the capture width. Record
`qa/stretch-root-evidence.md`. The postflight does **not** run `qa-paper`
(or merge-split-headings). `qa-paper` remains a later optional diagnostic
and still reports `frozen-root` if a named section is locked to the artboard px.
This is not a substitute for 768/390 captures.

**Nested chrome (HARD GATE, 1.2.22 · Pitfall #51).** The source page often wraps one
menu as `<header><header><nav>`. Detecting every `header`/`nav` and stacking
them in Paper produces 2–3 identical navbars and a short 1224px content
band. `detect-sections.js` keeps the **outermost** chrome only.
`import-sections.mjs` drops descendant chrome (`header-2`, inner `nav`)
and sets each written section to `width: 100%`. First content Y must
match capture `top` (source gap, not height-sum). `qa-paper` fails
`nested-chrome` and `narrow-section`.

Geometric checks against real node coordinates: `overflow` (clipped content),
`clip-content` (section Clip content / overflow not visible), `clipped-section`
(a child sheared past the section frame — Height Fit is not a waiver),
`zero-size`, `overlap` (siblings intersecting), `gap` (dead vertical space),
`empty-frame`, `empty-image` (hollow Rectangle / `deferred-image` /
empty circular `SVG`+`file` overlay),
`breakpoint-image-gap` (desktop has photos the 768/390 lander lost),
`artboard-fit`, `abs-decoration` (empty inset 1px stroke
overlay that should be parent `border`). Findings are severity-ranked.
Default walk depth is **4**. `clip-content`, `clipped-section`,
`empty-image`, `breakpoint-image-gap`, and `split-heading` (source
line-box titles still stacked as sibling Text nodes or one-Text row Frames) are high and fail A/5
(Pitfalls #55 #58 #67 #68 #69). Repair split titles after import:

```bash
PAPER_FILE_ID=$PAPER_FILE_ID node scripts/merge-split-headings.mjs
PAPER_FILE_ID=$PAPER_FILE_ID node scripts/merge-split-headings.mjs --artboard <id>
```

Then re-run `qa-paper` — merged titles must not report `split-heading`.

**Import flatten (HARD GATE, 1.2.18) + phantom-border trim (1.2.27).**
`import-sections.mjs` and `assemble-lander.mjs` run `flattenDecorativeAbs`
then `trimPaperStyles` after image localize and before `write_html`. That
is the clean QA pass — Paper never receives the Rectangle or the source page's
invisible link outlines. Repair an already-imported file with
`flatten-paper-abs.mjs` (abs) and `update_styles` `borderWidth: 0` on
text-link frames (phantom stroke). Scan capture HTML with
`flatten-decorative-abs.mjs --scan capture/home-desktop`. Pitfall #57.

When `--shots` is supplied, screenshot evidence uses a filesystem-safe form of
the visible artboard name. In particular, a pipeline label such as `A/6 · home
· Navbar states` writes as `A∕6 · home · Navbar states.jpg`, rather than
silently becoming a missing nested path.

**Geometry must come from `get_node_info`.** `get_computed_styles` returns only
*authored* styles — an auto-sized frame comes back as `{flexShrink:"0"}` with no
width or height, so every geometric check silently skips. Measured: styles-only
resolved 12 of 50 nodes and reported a false all-clear. The report includes a
`coverage` field for exactly this reason — **if `withGeometry` < `scanned`, the
clean result is not trustworthy.**

The detector is self-test verified: a deliberately broken frame (640px child in
a 400px clipped parent, plus a 420px margin gap) produced 3 `overflow` findings
and 1 `gap`.

### Where the design skills fit — and don't

Neither `impeccable` nor `emil-design-eng` can operate on a Paper canvas. Both
are worth using, at different moments:

- **`emil-design-eng`** is a pure knowledge skill — philosophy, no scripts, no
  tools. It cannot read Paper, but it is a strong *critique lens* to apply to
  screenshots pulled via `get_screenshot` (Paper MCP). Use it for the judgement half of QA
  (hierarchy, spacing rhythm, restraint) after `qa-paper.mjs` has cleared the
  mechanical faults.
- **`impeccable`** expects a codebase: it loads `PRODUCT.md` / `DESIGN.md`,
  edits real files, and runs `npx impeccable`. Pointing it at Paper is a
  mismatch. Its natural slot is **after** Paper → `rebuild/`, where the output
  is actual frontend code — which is its domain.
- **Paper's own Review Checkpoints** (via `get_guide`) are the rubric to use
  inside Paper: spacing, typography, contrast, alignment, artboard fit,
  repetition. That guidance ships with the MCP and is canvas-aware.

Order: `qa-paper.mjs` (mechanical, coordinates) → screenshots + Paper Review
Checkpoints / `emil-design-eng` (visual judgement) → `impeccable` later, on the
rebuilt code.

## Three Paper API traps

All three fail *silently* — the call succeeds and nothing happens.

1. **`update_styles` takes `nodeIds` (an array)**, not `nodeId`.
2. **Artboard canvas position is `left`/`top`**, not `x`/`y`. Setting `x`/`y`
   updates those style values and does not move the artboard; `worldX`/`worldY`
   track `left`/`top`.
3. **Layout propagates asynchronously.** Reading `get_basic_info` right after a
   move returns the *previous* coordinates, making a successful arrange look
   like a no-op. Wait ~2.5s before verifying.

## 1.2 capture is headless, not "visible section-by-section"

The visible-Chrome, per-section flow this section used to document
(`capture-sections.mjs` → `import-sections.mjs` → `getshot.mjs`) is retired
along with those scripts. Orchestrator 1.2 is `hover-reel/scripts/capture-session.mjs`
— headless, one hidden Chrome, desktop assemble + 768/390 screenshots + serializer
chrome + postflight. See `AGENTS.md` and the 1.0 `SKILL.md` §1.2 for the current spec.
`getshot.mjs` (screenshot a Paper node) is also retired; use `get_screenshot` via
the Paper MCP tools directly, or `mcp-client.mjs` / `paper-mcp.mjs` for a raw call.

### Agent anti-freeze rules (1.2 serialize)

Historically these three mistakes made capture look "frozen." They are not
Paper bugs, and `capture-session.mjs` already applies the bounded waits below
— if a run still looks stuck, kill the PID and rerun with live logs rather
than waiting:

| Mistake | What happens | Do this instead |
|---|---|---|
| `… \| tail -N` / `head` on capture stdout | `tail` buffers until process exit → **no live progress** and agent timeouts | Log with `tee path.log` only, or bare stderr; never pipe capture through `tail`/`head` |
| Waiting past 20s of silent output | Usually a hung sub-process, not a slow page | Kill the PID and rerun once with live logs (Pitfall #112) |

`capture-session.mjs` logs `settle complete` after its bounded waits (fonts
5s + images 8s timeouts, scroll height cap 20k, `domcontentloaded` + 15s
`networkidle` soft timeout) so a hang after that line is elsewhere.

**Per-section paint settle.** `reducedMotion: reduce` is not enough:
Framer appear still starts at `opacity: 0` + `translate(0px, 28px)`. The
serializer used to keep those in-flow nodes, so Paper imported them at
**0% blending** (invisible but present) and source clips landed mid-fade.
`settle-page.mjs` `settlePainted(page, selector)` waits (bounded), then
**snaps** leftover in-flow appear tweens to opacity 1 / transform none.
`paper-walk.mjs` `serializeSelector` and `source-sections.mjs` shots call
it immediately before capture. Do not serialize on an 80ms timer after
`scrollIntoView`. Absolute/fixed `opacity: 0` overlays stay dropped.


### Full-page PNG on disk (required). Paper sibling (opt-in)

**Problem:** the serializer + section detector almost always miss **fixed/sticky
navbars and menus** (they sit outside `<main>`). Rebuilding from Paper layers
alone can ship pages without chrome.

**Default:** every 1.2 capture **must** write `capture/<page>/fullpage.png`.
Do **not** create `{page} — source screenshot` in Paper unless a person asks
for left/right landmarks on the canvas. `qa-paper.mjs` uses node geometry on
the **page** artboard. It does not read the JPEG.

If nav/menu is in the PNG but not in Paper layers, rebuild chrome from the
**disk PNG + live site**. Log `qa/capture-interventions.md`.

**Opt-in:** `import-sections.mjs … --screenshots-only` embeds `fullpage-paper.jpg`
on a sibling artboard. Pin explicit width/height (never `height:auto`). Pair
with `arrange-artboards.mjs`. A missing sibling is not an A/5 fail.

After import, run `scripts/qa-paper.mjs` on the **homepage artboard only**.
Height Fit is not a waiver if a photo or dashboard is sheared (Pitfall #55).
Misplaced/overlapping/clipped sections **fail** — do not start 2.1.

**Rebuild contract (website-to-html):**

1. If nav/menu is missing from Paper layers, **rebuild chrome from `fullpage.png` + live site**.
2. Copy shots into `qa/paper-reference/<page>/` if needed for later live-site QA; never ship them inside `rebuild/`.

Detection also tries to **prepend** chrome sections when possible — fixed/sticky
bars always, plus relative/absolute/static source top bars whose
source name matches Nav Bar / Navbar / Navigation / Header (or
`<nav>`/`<header>` tags). Screenshots remain mandatory even when that succeeds.

### Learnings — single homepage / section QA

Overnight source homepage import experiment, plus a lander failure
(desktop-only 1600 lock). Use this path when the orchestrator contract is
**homepage-only / lander**, or when doing one-page section QA:

1. **Pre-pesticide on the live homepage (1.2.29) + SOURCE clips (1.2.30).** Before any
   `experiment-capture-home.mjs` / `assemble-lander.mjs` write:
   ```bash
   node scripts/pre-pesticide.mjs --url "<url>" --width 1600 \
     --out capture/home-desktop/pre-pesticide.json
   # seed Source · home first (screenshots → landers)
   PAPER_FILE_ID=$PAPER_FILE_ID node scripts/seed-source-board.mjs \
     --dir capture/home-desktop/source-sections --page home
   ```
   Visible Chrome (same launch as 1.2). `--headless` is CI-only.
   `--inspect` keeps the HUD up for a human walk. `--bookmarklet` prints a
   `javascript:` URL. The HUD outlines like Pesticide; hover/click a node for
   tag, id, classes, `data-framer-name`, role, text, img `src`/`alt`/natural
   size, and whether it is `header|nav|main|section|footer|form|img|a|button|h1-h3`.
   Copy Tailwind v3 (optional `tw-` prefix) and a Paper row (suggested section
   slug, Text/Image/SVG/Frame, decorative vs content). The JSON is the live
   contract: `sections[]` (slug, tag, layer name, bbox, `childCounts`),
   `images[]`, `forms[]`, `landmarks[]`. Diff it after import. 1600 / 768 / 390
   each write `source-sections/01-slug.png` + `.json` (pesticide on in this CLI,
   one clip per section). Headless 1.2 collect hides overlays instead. `pre-pesticide.json` stays the page-level contract. Diff **box metrics**
   (icon size, container `w`/`h`, gap) per width — not `flex-wrap` /
   `round(46%)` / 2+1 from another breakpoint (Pitfall #75). Seed
   `Screenshots` **first** under `Ruler · desktop` (≥100px below the
   lintel) from the **1600** clips only, then the three landers. The artboard
   is **50% opacity** so the clips recede next to `home-desktop`. Design Library is absent until 1.4. Inside: sections stacked
   vertically, one `section-number` (A/6 red `#E11D2E`) per row + outlined shot as a `data:image`
   `<img>` (never `paper-asset://` / `file://` — those paint badges on white).
   `seed-source-board.mjs` **replaces** an existing blank board. Layer names
   `01 · slug`. Never a sibling `Desktop section IDs` legend. Never one tall
   full-page screenshot. No 768/390 source boards on Paper. Do **not** merge this HUD
   into `overlay.js` or rebuild `qa-overlay`. Do not invent a second Paper
   file. Homepage only by default.
2. **Hide the capture HUD before Playwright section shots.** The serializer skips
   `x-paper-*` nodes, but element screenshots still composite the fixed
   "capturing N/M" overlay. `overlay.js` exposes `hide()` / `show()`
   (`visibility`) before `destroy()`. Call `hide()` + `clearHighlight()` before
   each section JPEG and `show()` in `finally`. Pre-pesticide must already have
   exited (or been destroyed) so only the capture HUD is in the page — both
   are `x-paper-` prefixed either way. Capture scripts call
   `__xPaperPrePesticide.destroy()` before serialize so leftover outlines
   cannot leak into computed styles.
3. **Ruler + Source first, then landers. Design Library waits for 1.5.**
   On a new or ruler-less file, P-0 is the first Paper write:
   ```bash
   node scripts/draw-rulers.mjs --file "$PAPER_FILE_ID" --init
   ```
   That `--init` draws `Ruler · desktop` only. `assemble-lander.mjs` seeds
   `Source · {page}` first, then the lander. No earlier command may create,
   seed, mine, or render Design Library.
   ```bash
   node scripts/experiment-capture-home.mjs --url "<url>" --out-dir capture/home-desktop --width 1600
   PAPER_FILE_ID=<project-file-id> node scripts/assemble-lander.mjs \
     --manifest capture/home-desktop/manifest.json \
     --name "home-desktop" --width 1600
   # optional: --prepend path/to/nav.html when nav was captured separately
   ```
   `assemble-lander.mjs` writes **layers only** (no source-screenshot artboard).
   **Desktop section names (1.2.18).** On a 1600 / `home-desktop` assemble, each
   section layer is named `01 · slug` in document order. That name **is** the
   comment — Paper MCP can list/resolve threads but cannot `create_comment`.
   Never create a `Desktop section IDs` (or any sibling legend) artboard;
   `retireSectionIdLegend` deletes leftovers. Slugs also stay in
   `capture/home/section-ids.json`. Tablet and phone keep slug layer names.
   A/6 buttons label themselves with the **desktop** ID. Repair looks up by
   `id` or slug.
   After **all three** width assembles, arrange **one horizontal row**:
   ```bash
   node scripts/arrange-artboards.mjs --gap 120
   ```
   Before 1.4, order is Source → desktop → tablet → mobile → A/6 →
   Interactive components. Same Y. Step 1.4 creates Design Library once and it
   heads the row, ahead of Source.
   Skip `--screenshots-only` unless a person asks for a Paper sibling PNG.
   Reuses `PAPER_FILE_ID` / `--file-id`. Pass `--new-file` only when you
   explicitly want a fresh Paper file.
4. **Relative source nav.** Some source templates put the top bar in normal flow
   (`position: relative|absolute|static`) named Nav Bar / Navbar / Navigation / Header.
   `detect-sections.js` prepends those as chrome, not only fixed/sticky.
   **Overlay nav (Pitfall #87).** If the live bar is
   `position: absolute` or `fixed` over the hero, Paper still parks the
   prepended chrome **relative** (Absolute position unchecked) and the
   hero drops. After assemble, tick Absolute on the nav layer at 1600 /
   768 / 390 so it sits on the photo, not above it.
   **Fixed nav stack (Pitfall #97).** Paper paints later siblings on top.
   The fixed bar must be the **last child** of the lander and sit at
   **`left: 0` / `top: 0`**. A mid-tree layer (e.g. `02 · explore-demos`
   nested under frames) disappears behind the hero. Do **not** merge this
   with overlay-behind-type (Pitfall #84).
5. **Desktop vs tablet vs mobile = separate artboards, same file (required
   for `web-responsive`).** The live site serves different DOM per width. Capture
   `--width 1600` (`capture/home-desktop`), `--width 768` (`capture/home-768`),
   **and** `--width 390` (`capture/home-390`), then `assemble-lander` each as
   its own artboard (`home-desktop`, `home-768`, `home-390`) in the pinned
   project file — do not stack widths on one artboard, do not create a second
   Paper file, and do **not** skip 768 or 390 because “responsive is Step 3”
   or “tablet is sanity only.” A lander that only has the 1600 artboard is an
   incomplete 1.2. Keep `fullpage.png` on disk. Do not attach Paper
   sibling screenshots unless asked.
6. **`PW_CHROME` on Linux.** Capture runs on Linux agents; Paper MCP still needs
   Paper Desktop (macOS). Point Playwright at a real binary:
   `export PW_CHROME=/usr/bin/google-chrome` (or the Playwright cache chrome).

### Why section-by-section is the default

A whole-page write produces layers **all named `"Frame"`**. The serializer
strips classes and semantic tags, so `get_jsx` comes back visually correct but
semantically anonymous — useless as a rebuild source. Capturing per section and
calling `rename_nodes` on the way in is the only point where real names can be
attached.

### Three rules that are load-bearing

**Ruler first, then the capture row (P-0).** The first artboard is
`Ruler · desktop`. Do not add 768 / 390 bars. Do not drop a page, source shot,
or A/6 board onto a canvas with no lintel. `draw-rulers.mjs --init` on empty
files creates only the ruler; assemble / import / arrange pin Design Library → Source → desktop
→ tablet → mobile → 1.3 capture frames. Everything parks **100px** below the
ruler, left to right. After 1.3 Extension Done, 1.4 creates Design Library exactly once
and it heads the row, ahead of Source. The bar is 20000px wide (Pitfalls #37 #42 #108).

**Overlay elements MUST be `x-paper-` prefixed.** The serializer skips any
element whose tag or id starts with `x-paper-`, which is how the capture HUD
and the pre-pesticide HUD exclude themselves from the capture. Rename anything
in `overlay.js` or `pre-pesticide.js` and the chrome starts appearing inside
your Paper artboard. Verified: 0 leaks across 10 sections. Pre-pesticide root
is `x-paper-prepesticide` (tag + id).

**Never fire `write_html` calls back to back.** Paper fetches every remote image
while parsing. Ten rapid writes outrun that fetcher and images land as broken
placeholders — *silently*, with all calls reporting success. `import-sections.mjs`
paces writes (`--pace`, default 2500ms, plus 250ms per image in the section).
Verified: identical HTML that failed inside a 10-write burst imported perfectly
when written alone; with pacing, 27/27 images landed.

Large images are also just slow — a 992 KB hero took ~40s to appear. **Wait
before screenshotting** or you will diagnose a bug that isn't there.

## Manual / whole-page workflow

### 1. Establish the Paper target — ALWAYS FIRST

```bash
node scripts/paper-mcp.mjs get_basic_info '{}'
```

Returns `fileName`, `pageName`, `pageId`, `rootNodeId`, existing artboards, and
the page list. **Never write without reading this first** — you need `rootNodeId`,
and you need to know what's already on the page so you don't land on top of it.

If there is no `Ruler · desktop`, draw it **now** (`draw-rulers.mjs --init`)
before any content `create_artboard`. That is P-0. Frames go below the line.

If the user named a page ("page 3"), confirm it's the active one. The MCP writes
to the *active* page; it will not switch pages for you.

### 2. Choose scope

Full page:

```bash
node scripts/capture.mjs --url "<url>" --selector body --out full.html
```

One section — list candidates first, then pick:

```bash
node scripts/capture.mjs --url "<url>" --list-sections
node scripts/capture.mjs --url "<url>" --selector "header" --out hero.html
```

`--list-sections` returns selector, dimensions, depth, and a text snippet. Map the
user's plain words ("the pricing table") to a selector yourself — don't make them
hunt. Prefer the shallowest element whose text matches.

### 3. Verify BEFORE writing

```bash
node scripts/shot.mjs full.html preview.png   # if present, else wrap + screenshot
```

Look at the render. A capture that lost its content looks obviously empty —
catching that here costs nothing; catching it after a 900-node write costs a
cleanup. Check especially: did entrance-animated content survive, did images
resolve, did type land.

### 4. Write into Paper

```bash
node scripts/paper-mcp.mjs write_html '{"html": "<PASTE OR READ FROM full.html>", "targetNodeId": "<rootNodeId>", "mode": "insert-children"}'
```

Read the HTML from disk in your own tooling and inline it into the JSON-RPC
call — never pass a full page as a shell arg (~750 KB blows ARG_MAX). If
native `mcp__paper__*` tools are in the session, call `write_html` through
those directly instead of shelling out.

- `insert-children` — adds under the target. **Default. Safe.**
- `replace` — **deletes the target node** and puts the HTML in its place. Only on
  explicit instruction.

Writing to a page `rootNodeId` is fine: Paper wraps the result in a single
artboard automatically.

### 5. Confirm

```bash
node scripts/paper-mcp.mjs get_screenshot '{"nodeId": "<artboardId>"}'
```

Screenshot from Paper itself, not the local preview — that's the only proof the
parse landed. Then:

```bash
node scripts/paper-mcp.mjs finish_working_on_nodes '{}'
```

## The two things that make capture work

Both were found the hard way. Do not remove them from `capture.mjs`.

**`reducedMotion: "reduce"`** — Most modern sites start entrance animations
at `opacity: 0`. Without it a source page returns nearly empty. Framer often
ignores it, so this is not sufficient by itself.

**Full-height scroll pass before serializing** — triggers IntersectionObserver
reveals and lazy images. Then scroll back to top and let it settle.

**Wait for painted opacity, then force rest.** In-flow appear leftovers
(`opacity: 0` + `translateY`) used to land in Paper at 0% blending. The
serializer now rest-paints those to 1. `settle-page.mjs` waits (bounded) then
snaps the same leftover tweens on the live page so source-section screenshots
are not mid-fade. `serializeSelector` / source shots call that immediately
before capture. Absolute/fixed overlays stay dropped.

## Known limits

**Images must be local before Paper write.** The serializer still emits
`<img src="https://…">` and CSS data-URI wordmarks as
`background-image: url('data:image/svg+xml…')`. `assemble-lander.mjs` (every `writeLayer`, including `--prepend`) /
`import-sections.mjs` run `localize-html-images.mjs`: remote URLs become
`paper-asset:///abs/path`, and empty data-URI boxes (footer logo) become
an inline SVG or `<img>`. Repair with `repair-paper-images.mjs`. Remote
CDN writes and CSS data-URI fills both go blank while the write still
reports success. Disk copies live in `rebuild/images/` and `capture/assets/`.
Unavailable display faces (`General Sans Semibold`) are remapped to
this scrape's bold face + `font-weight: 700` in the same pass — Paper otherwise falls
back to system-ui Regular and headlines look too light.

**No `@font-face`.** Font *names* carry into Paper (confirmed: whatever faces this scrape actually loaded,
Newsreader all landed), but the webfont files don't. Resolution differs **per
file** — the same capture rendered its display serif correctly in one file and
substituted a sans in a freshly created one. If type looks wrong, check
`get_font_family_info` for what's actually available.

**Paper font tokens ≠ build stacks (Pitfall #88).** `create_tokens` /
`set_tokens` must store a catalog face Paper can run. Sending
a CSS stack is the “can't run font” error. Rebuild
`tokens.css` / utilities keep the full stack plus installed / `@font-face`
files. Do not copy a Paper token value into the HTML build as a bare
catalog family with no stack. Sheet / lander `write_html` is the same split —
catalog face on Paper, stack in `library.json` (Pitfall #89).

**Auth'd pages need a real profile.** The default context is logged out. Anything
behind a login won't render.

**One breakpoint per capture process.** `--width` sets the viewport (default
1600, which matches common Paper artboards). The live site serves a different DOM per
breakpoint. For `web-responsive` / homepage-only landers, captures at
`--width 768` and `--width 390` are **required** (separate out-dirs +
artboards). Skipping either leaves a frozen desktop for `website-to-html`
2.3 section loop.

**Pitfall #57 · Every new scrape reuses btn-primary.** Name controls by visual pattern on THIS site; do not reuse the last URL's token map.

Related capture: serializer output often has `border-*-width` + `border-*-color` with no style, or
`border: 1px solid rgba(42, 42, 42, 0)` on nav/footer text links. CSS
paints nothing. Paper invents a stroke. Always run
`trimPaperStyles` before `write_html`. Do not strip real CTA/card
shorthands that include a visible color. (Same helper as Pitfalls #40 / #56.)

**Pitfall #70 · Live images vanish before Paper import.** A prior run dropped images because `write_html` hung and nobody had
a live inventory to diff. Run `pre-pesticide.mjs` first. The HUD must
stay `x-paper-` prefixed.

**Pitfall #71 · One tall source screenshot instead of per-section clips.**
Pesticide outlines on the live URL are useful only when each 1.2
section is its own shot, numbered the same as lander layers (`01 · hero`).
Never write `full-page.png` into `source-sections/`. Never park `Source · home`
on the lander. Same red ruler/badge (`#E11D2E`). Disk clips at **1600 / 768 / 390**.
The Paper Screenshots board remains 1600 at **50% opacity** so it does not compete with `home-desktop`.

**Pitfall #58 · Hover pills import top-left instead of centered.** 1.3 cells must keep the lander's alignment (`centerDesktopFlex`); leave `flex-end` / `space-between` alone.

Related capture (Pitfalls #24 / #68): the 768/390 serializer often emits a host-specific asset-reference data URI instead of the desktop image URL. Paper cannot
fetch that scheme, so cards land as empty
Rectangles while desktop still has the bitmap. `localizeHtml` must
resolve the hash against `rebuild/images`. `qa-paper` must fail
`empty-image` (hollow Rectangle ≥80×80) and `breakpoint-image-gap`
(same section has fewer Images on a narrower lander). Repair by writing
the desktop `paper-asset://` file into the slot — do not recapture
desktop-only.

**Pitfall #64 · Design Library census.** Do not tally every node's
`fontSize` / gap / radius / shadow into tokens. Mine colors, families,
weights, and styles. Type sizes, spacing, radius, and elevation are
Tailwind defaults. Rebuild maps closest class.

**Pitfall #67 · Fixed section height clips titles after insert.**
`write_html` insert-children does not grow a captured fixed-px
section. The taller stack recenters inside the old box and an
`overflow: clip` artboard shears the H1. After any insert into a named
section, `update_styles` that section only to `height: min-content`.
Do not guess a new px height. Artboards may stay `fit-content`. If
768/390 already have the row as its own `feature-section`, do not
stuff it into the hero.

**Pitfall #68 · Image QA is visual, not only empty-image.** Hollow
dashboard Rectangles are not the only gap. Flag empty `deferred-image`
Frames and empty `SVG` / `file` overlays on ~50–107px circles. Never
put `paper-asset://` or `file://` in `write_html` — landers use
the live image URL; `Source · {page}` uses `data:image`
with pinned width/height. `paper-asset://` paints hover-pair badges on white
frames (past example, not a spec). Insert the `<img>` into the parent
Frame (Rectangle targets fail). Screenshot the section; a still-blank
face means an overlay is still on top. Landers only unless asked.
Match icon **box metrics** (size, container, gap) from the live
inventory at that width — do not “fix” a desktop 3-col row by copying
tablet wrap (Pitfall #75).

**Pitfall #69 · Source line-box titles split into stacked Text siblings.**
Display headings often land as several row Text nodes — or as **row Frames that each wrap one Text**, with a scribble SVG nested under one word.
Past example (not a spec): a hero title split word-by-word with the underline sitting in flow instead of under the word (same split on 768 and 390). That is a capture/serializer artifact
of source line boxes, not a design system. Detect both shapes.
A heading that is visually one title must be **one Text node** with the
full copy, `text-align: center` when the live heading is centered.
Keep a split **only** when you can detect a real constraint: an explicit
`max-width` that would wrap a single block differently, or two genuinely
different type styles that are not one sentence. Default is merge.
Decorations / SVGs on the heading (underline scribble, oval, highlight)
must be `position: absolute` on the heading wrapper, marked decorative
(`data-decorative`), and `pointer-events: none`. Do not leave them as
in-flow siblings that shove the title lines apart. `qa-paper` flags
leftovers as `split-heading` (high; optional later `qa-paper`, not the 1.2 postflight). Repair with
`merge-split-headings.mjs` (`--artboard <id>` or whole-file landers).
Do not recapture the site to fix this.

**Pitfall #75 · Desktop icon row copied tablet 2+1 wrap.** A 1600/1440
hero icon row must stay **3 columns, no wrap** when source /
pre-pesticide says so. What must match across breakpoints is **icon
size + icon container box + gap**, not `flex-wrap` / `round(46%)` /
2+1 from 768. Tablet/mobile wrap is breakpoint-correct. Detect and
assemble write each `--width` as-is — there is no wrap-copy helper;
do not invent one.

**Pitfall #76 · Token-pass rebounds a sample and misses the rest.**
A large lander can look done after the easy type/color nodes rebound
while raw hex/px stay on the rest. Token bind is not best-effort.
`apply-theme-tokens.mjs` must exist; walk every node on scoped artboards;
write `qa/token-pass-qa.json`; fail if any id is missing or a tokenable
literal is still raw and unlisted.

**Pitfall #84 · Overlay serialized after content; type unreadable.**
CRITICAL — gold is image → dim overlay → type last. After `write_html`, `move_nodes` so the abs overlay sits after the image and before in-flow type on every breakpoint. Do **not** clone the overlay on top. Clone-on-top is for *content* (CTA forms) when the overlay already covers them. Fallback: overlay `z-index: -1` if honored. `update_styles` often cannot set `position` on flex-grow children.

Serializer emits absolute full-bleed overlays AFTER in-flow content. Gold on every breakpoint is image → overlay (abs 100%, dim) → type last. Clone-on-top is for covered *content* (CTA forms), not for burying the headline.

Catch-at-write: `reorderOverlayPaintOrder` in `assemble-lander` / `import-sections` after flatten+trim, before `write_html`. `qa-paper` flags leftovers as `overlay-covers-type`. Repair already-written landers with `fix-overlay-paint-order.mjs` (`--dry-run`; `--apply` on the current file). Do not merge with overlay-nav (#87), fixed-nav stack (#97), or opacity-0 settle (#85 / `settle-page.mjs`).

**Pitfall #88 · Paper fontFamily token is a CSS stack.** `create_tokens`
must not send `"Face", system-ui, sans-serif`. Paper font variables are not CSS
strings — they must resolve to a catalog / local / Google face. Call
`get_font_family_info` on the bare name first. Write the catalog face from this scrape. Keep the
stack in `library.json` `value` and in rebuild `tokens.css`. Unavailable
faces skip or fall back; do not invent a font. Not #25 (weight-suffixed
`write_html` faces).

**Pitfall #89 · Sheet / lander Text stays System Sans-Serif after #88.**
Catalog tokens exist, but Design Library chrome and family Aa still
`write_html` a stack or `var(--font-serif)` that Paper does not bind.
Inspector: Font family = System Sans-Serif; caption still names the intended face.
`theme.sans` / `display` / `mono` must be catalog faces from this scrape. Family Aa uses
that face + `data-font-token`. After `create_tokens` /
`write_html`, bind unbound Text (`bind-paper-fonts.mjs` / token-pass).
`qa-paper` `unbound-font` (high) fails 1.4. Do not skip the
bind because a previous URL was refused. See
`references/paper-font-bind.md`.

## Fallback: quota

Paper's MCP can return **"Weekly MCP limit reached"**. Treat it as retry-worthy,
not terminal — it has been observed on `create_artboard` while `write_html`
succeeded moments later.

If writes really are blocked, go through the clipboard — the mechanism the
extension itself uses, which has no quota:

```bash
{ printf '<x-paper-html>'; cat full.html; printf '</x-paper-html>'; } > wrapped.html
osascript -e 'set the clipboard to (read (POSIX file "'"$PWD"'/wrapped.html") as «class HTML»)'
```

Then the **user** presses Cmd+V in Paper. Do not try to send the keystroke —
`osascript` is blocked from synthetic input without Accessibility permission
(error 1002).

## Rules

1. Read `get_basic_info` before any write. Always.
2. Preview the capture before writing. Always.
3. Default to `insert-children`. `replace` destroys the target.
4. Never write to a page that has the user's work on it without saying so first.
5. Confirm with a screenshot pulled **from Paper**, not the local render.

## Provenance

`scripts/serializer.js` is Paper Snapshot **v0.3.12** (`lidfahaahiogmnlccifabccgplofocck`),
ported from Paper-Bridge `content/paper-snapshot.js` @ `fda64f2` (0.3.8 base)
plus the 0.3.12 upstream deltas: throttled frame yield, positioned-element
baseline resets, canvas/video PNG rasterization, in-page reduced-motion
emulation, and `::before`/`::after` `content: url()` images. 1.2 keeps its
SVG `<use>` fragment ids, shadow-root lookup, HTML host promotion,
`checkVisibility` fallbacks, and layer-name / sidecar / dryRun adaptations
on top. See `references/paper-snapshot-architecture.md`.
