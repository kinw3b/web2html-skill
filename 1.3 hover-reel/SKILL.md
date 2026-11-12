---
name: hover-reel
description: Capture a live site's interactive COMPONENTS on the homepage (`/`) as default/hover state pairs of Paper-ready inline-styled HTML, then rebuild them in Paper as real editable layers. No GIFs. Default is one page. Extra routes need an explicit user request. Uses visible Chrome so live whileHover fires. Inside website-to-html, 1.3 fills FRAME Buttons + Components from desktop (`pull-desktop-specimens.mjs`) and authors button hover from source CSS (`author-button-hover.mjs`); this Capture Tool is leftover 1.4 hover only. Public 4.1–4.4 are the later optional Phase 4 page import. Triggers - "hover reel", "capture hover states", "navbar hover states", "component states to paper", "A/6", "capture the navbar", "hover parity".
version: 1.1.111
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hover, interaction, component, states, paper, cdp, serializer, parity]
    related_skills:
      - website-to-html       # umbrella — 1.3 pull + optional 1.4 Capture Tool
      - url-to-paper          # supplies scripts/serializer.js and the Paper MCP client
      - emil-design-eng       # Step 8 — implements motion craft on top of this evidence
      - impeccable            # Step 8 — audit pass, reads qa/animation-parity.md
---

> `$SKILLS` — the directory your agent loads skill packages from.
> Set it once: `export SKILLS=~/.claude/skills` (or wherever you keep them).

# Hover Reel — capture components as default/hover state pairs in Paper

## Capture Tool extension (1.4 leftover · OPTIONAL · 1.1.111)

> **This is leftover 1.4 hover (web2html 2.12.0).** 1.3 already mines the
> Design Library and pulls unique buttons + components from token-seeded
> `home-desktop` onto FRAME `Buttons` and FRAME `Components`. Run this
> extension only for live hover pairs 1.2/1.3 could not serialize.
> `mark 1.4 active` opens Paper **and** the browser on the source URL stamped
> with `paperFileId` + `projectRoot`; `pipeline-progress.py open-capture`
> re-opens that tab and `capture-doctor` checks the native bridge (web2html
> Pitfall #217). A skip JSON is not required.
>
> **The goal is that this extension becomes unnecessary.** A run that needed
> it is a signal to improve the 1.2/1.3 capture, not the norm.

`capture-extension/` is the Manifest V3 **1.4 launcher**. Package it
with `npm run package:extension`, unzip it, run
`install-native-host.command`, then load the unpacked folder in Chrome with
Developer mode on. Its side-panel order is fixed:

1. **Navbar + Dropdowns** — Navbar is required; dropdowns are manual
   closed/open pairs. Manual targeting starts on the exact hovered DOM node;
   ↑/↓ traverses parents explicitly, while Auto selects the full navbar.
   Auto seeds from logos, menu links, dropdowns, and CTAs, then climbs to the
   smallest compact parent that still contains that set. It never picks
   `html`/`body`/`main` or a page-sized `<header>`/`<section>`. A missing
   `data-framer-name="logo"` or semantic `<nav>` is not a miss if the top band
   has three+ menu links plus a CTA or dropdown.
   The confirmed desktop selection fingerprints the Navbar. Two inactive
   background tabs rematch it at 768 and 390, serialize those responsive
   wrappers, and park all three takes on `Navigation`. Full-page or hero shells
   are rejected.    If the desktop pick was the links/CTA row, 768/390 rematch the
   compact logo + hamburger bar instead of requiring those hidden links.
   Those widths open a short-lived sized popup so the page actually lays out
   at 768 and 390; hidden background tabs stay 0×0 and match nothing. Continue stays locked until Paper confirms every width.
   While locked, the side panel must show Desktop / Tablet / Mobile capture and
   Paper-confirmation status, an active loader, and an exact `n/3` count.
   Continue labels the wait and unlocks automatically at `3/3`; failures expose
   `Retry needed` rather than leaving an unexplained disabled control.
2. **Hover** — trusted Chrome pointer input records default/hover and parks on
   `Buttons`.
3. **Multi-state** — two manual states park on `Components`.
4. **Single** — one exact clicked element parks on `Components`. **Done**
   is available here. It writes `source-site/components/capture-extension-session.json`
   and `human-hover-done.json`, then pings the pipeline agent. Closing Chrome
   without Done is still 1.4. Do not require a Tags pass first.
   Starting capture locks the source tab to the **1600** desktop lander,
   zoom 100%, via `Emulation.setDeviceMetricsOverride`. Keep that lock
   while Nav or Hover is running (Pitfall #150). Semantic tags are the 1.2
   `layer-ids.json` census; **2.2.a** applies that map. There is no Tags Scan
   step and no enrich write from the extension.

The local bridge creates only `Navigation`, `Buttons`, and `Components`;
it never creates `Design Library`. Those empty frames are created with
`width: fit-content` / `height: fit-content` — never a fixed 1400px board. Prefill is not a machine-local file
inside the GitHub extension. When opening Chrome for 1.4, open the
**source site** with `paperFileId` and `projectRoot` query params. A
document-start content script copies those into `chrome.storage` and the
side panel; then it strips them from the address bar. Do not ask the
person to paste those fields when this run already has a Paper file.
If both fields are present, the side panel starts capture by itself.
Confirmed-take wrappers and state cells use
`width: fit-content` / `height: fit-content`, so each receipt hugs its widest
serialized state instead of inheriting a fixed review-board width. A green
check payload begins at the exact selected DOM root: never inject a
`capture-context`, sampled background, padding shell, or other presentation
wrapper. Referenced SVG symbols and computed borders/outlines must be preserved
so icons and button strokes arrive in Paper with the component. A green
check requires Paper to return the
 created node ID. Failed writes stay retryable. Done writes
 `source-site/components/human-hover-done.json`, then leaves the panel open.
 The pipeline does not wait on this file. 1.4 is the Paper walk;
 Capture Tool is leftover hover only.

This extension is leftover live hover. **1.2** must already
have captured 1600 / 768 / 390, parked serializer chrome on Navigation at all
three widths, and passed geometry + screenshot QA. There is no Playwright HUD
any more: `capture-session.mjs` is the headless 1.2 collect + geometry
postflight and opens no window. 1.3 already mined the Design Library from
those frames. For 1.4: stamp the source URL with
`?paperFileId=&projectRoot=`, and use the toolbar **Paper Capture Tool**
side panel.

**UI source of truth:** open `capture-tool-ui.html` in the browser (`file://`).
Do not run a demo to restyle the panel. Specimens match
`capture-extension/sidepanel/panel.html` + `panel.css`.

**Human-led capture is the only capture path.** **1.2** (`capture-session.mjs`,
headless) captures `home-desktop` / `home-768` / `home-390`, clips
`source-sections/NN-slug.png` at 1600 / 768 / 390 (Screenshots board stays 1600 at 50% opacity),
parks serializer chrome on `Navigation` at all three widths, and ports that bar
onto `home-desktop` when the lander has no navbar. Collect seeds FRAME
`Buttons`, FRAME `Components`, and FRAME `Navigation`. Then it runs the
geometry postflight. Missing any destination blocks the Capture Tool.
**Then the Chrome extension** opens Capture Tool for **1.4**:
capture the full navbar and any dropdown menus first. Paper numbers **content** only —
**01 is always the hero**, never a navbar. Click the navbar or a dropdown — never the page, hero, or a `Desktop` /
`main` shell. Page-sized clicks are rejected so Navigation cannot hang on a
full lander serialize. Continue stays available once Navbar is on Paper.
`parkNavbarOnLanders` stamps a **compact** overlay last on `home-desktop`
(links) and `home-768` / `home-390` (hamburger) at `0,0` — never the live
Framer header dump. **2.2.c** then ships that overlay as `position: fixed`
on the rebuild so it follows scroll (Pitfall #115). Capture stays Absolute
on the lander; the ship CSS is fixed. FRAME `Navigation` writes are
`position: relative` (Absolute off). **Record (R)** must be on before a
click counts. That exact element parks on Paper immediately; the HUD
locks until it lands, then the row shows **✓ added to paper**. Repeat
one take at a time. **Continue** parks Navigation when chrome is on Paper,
then the same 1.4 session continues on **Hover**. Record (R), hold a control until 100%, then
that pair parks on FRAME `Buttons` immediately — HUD locks until
the row shows **✓ added to paper**. New takes **stack** below the last
Component row. Multi-state and single component takes park on FRAME
`Components` immediately. The human session calls the Components writer
directly and marks the manifest receipt; startup backfills saved component
takes that have no Paper receipt. FRAME `Buttons` is hover-only. Skip if the bar sits in the hero or there are no dropdowns.
Reopen the side panel to resume leftover Capture Tool when Paper is already on the canvas.
**After** source shots are on Paper, the review sequence is `01, 02, 03…`
(`review-sequence.json`). `01` is the hero. Navbars are never numbered.
The last content band is **FOOTER** — never heading copy.
Then Hover walks that list. Do not invent a second numbering.
The side-panel title is **Capture Tool**, with a gold **✦ Auto** chip beside it.
Modes are Nav / Hover / Multi-state Component / Single Components / Done.
The whole header drags the panel. It opens top-left.
An empty list is the dashed **Waiting for takes** well — navbar
pick, dropdowns, and Hover. Once a take lands, the well goes away. Breakpoint pills stay unchecked until
Continue writes Navbar at that width — landers already on Paper do not
count as a check. Takes for the **current** Paper section
get a red inset so they read as **here**; other rows dim. **Next** goes to the next content band. The person
aims the red circle, toggles **Record**, and reviews the list. The
agent does **not** hunt hover targets and does **not** spawn one Chrome
per kind.
Already captured live elements keep a red `x-paper-captured-outline`
overlay as the person scrolls. The overlay is tool chrome, not a source
style, so it cannot serialize into Paper.
While Record is on, the header lamp and captured-element outlines blink
in sync; reduced-motion keeps both steady red.

**Optional leftover hover (1.4).** Nav → Hover → Multi → Single → Done is
**not** the 1.3 path. 1.3 fills FRAME `Buttons` and FRAME `Components` from
desktop. First action of 1.4 is `mark --step 1.4 --status active` (opens
Paper). Capture Tool is `pipeline-progress.py open-capture` only.

```bash
# 1.2 — headless collect + board seed + geometry postflight. Opens no window.
node "$SKILLS/hover-reel/scripts/capture-session.mjs" \
  --url "https://example.com/" --page home \
  --out source-site/components \
  --capture capture
# omit --file — first 1.2 create_file's one Paper document; a retry reopens qa/paper-file.json

# 1.3 pull after Design Library + seed. Red NN badge = home-desktop section.
# Then author-button-hover.mjs mines source CSS :hover onto those Buttons.
# node "$SKILLS/hover-reel/scripts/pull-desktop-specimens.mjs" \
#   --project . --file-id $PAPER_FILE_ID --plan qa/buttons-components-plan.json

# 1.4 leftover hover only:
python3 "$SKILLS/web2html/scripts/pipeline-progress.py" open-capture "$PWD"
```

R = record on/off · **1 / 2 / 3 / 4** = capture mode · N / ] = next Paper section ·
[ = previous · Backspace = undo · **Continue** opens the next mode · **Done** on Single writes manifests and exits.
Four modes — swap them to see that mode’s takes only. An Ideal / How card
under Mode explains the active mode. Footer repeats the shortcut.
Right-click cancels in every mode.
- **Capture Hover Buttons** — Key [ R ] Record → Hover ( 2s ). Bar
  at 100% writes Default|Hover and stops Record. Leave earlier cancels.
- **Multi-state Component** — [R] Record → First Click ( 01 ) › Second
  Click ( 02 ). Parks two cells even when CSS looks the same.
- **Single Components** — [R] Record → click any element.
  Default-only. The exact clicked element is accepted without tag, role,
  size, or example-based filtering.
  **Clear list** empties the HUD for the active mode. Paper layers
  already parked stay.
Tags are not a 1.3 rail step. `capture/home-desktop/layer-ids.json` from 1.2
is the pc-id + tag census; 2.2.a applies that map. Do not Scan, write
`qa/layer-ids-enrich.json`, or rename `home-desktop` from the Capture Tool.
A completed take always stops Record. Hit Record again for the next object.
Paper type labels follow the mode: hover → **buttons**, single click →
**component**, click 01→02 → **objects** (stacked, no Default/Hover labels).

**AI ✦** walks every Paper section in this same Chrome. In Hover it
records painted CTAs and at most **one** text link in a unique
featured box or text block. It skips repeating product grids, blog
lists, and collection cards — those do not land on Paper. Footer
keeps one specimen (a CTA if present, else one text link). Navbar links stay on the
navbar pick. Skip already-saved labels. **Stop AI** or Escape
cancels. This is the human opt-in speed-up — not `--auto`. Review the
list. **Done** on Single is still required. The agent does not start 1.4 because
AI ran.

The hover bar is hidden when Record is off. Page `<a href>` / `<area href>`
do not navigate for the whole HUD session — Record on or off. The live
`href` stays on the serialized HTML. New tabs and off-page document loads
are closed or aborted.

**Agent listens.** Each take writes `source-site/components/<page>/<kind>/`
through the native bridge (`capture-extension/bridge/host.mjs`).
The agent reads those files — **never ask the person to paste JSON**.
 **Done** in the side panel is the only receipt. After Done, the bridge writes
 `human-hover-done.json`. The panel **stays open** with a manual-continue cue.
 The pipeline starts 1.4 only after the user types **Continue** in chat. Do
 not close the side panel on Done.

The extension calls url-to-paper `serializer.js` (`fe(sel)`). That returns
`{ status, html }`. `__hrSerialize` unwraps `.html` before disk / Paper.
Never `String()` the object — that writes `[object Object]` and Paper
shows an empty `object` frame instead of a painted `button`.

Walk a live site's **interactive components** and record each one twice: at rest
and under a real pointer. Every state is serialized to **inline-styled HTML** and
written into **Paper as real editable layers**, side by side, so the hover design
is something you can look at, measure, and copy — not something you infer.

**Homepage only.** Extra routes need an explicit user request.

**No Components sheet. No A/6 states board.** Buttons and footer pairs
park on FRAME `Buttons` (stacked Component rows). Screenshots stay on their own board.
Nav, forms, FAQ, dropdowns, and 768/390 burgers park on FRAME
`Interactive components` (closed | open). That is a review board, not a
Design Library catalog. Do **not** seed `A/6 · {page} · states`. Do **not**
create `LIBRARY — Components`, a Theme Library catalog of isolated
buttons/cards/FAQ atoms, or `site-components` / `kit-components` dumps.

**Source hover column (1.1.41).** Gold is one large `section-number`
plus a `list` of `object`s — never a badge per CTA. The **Buttons**
heading and each row column are **fixed `780px`** with grey fill
`#E8E8E8` and **24px** padding (gold `3JJ-0`). That review ground
shows dark-mode CTAs whose fill is missing or baked-in wrong. Do **not**
paint the live ancestor onto the button. Layers: `section-number` → `list` → `object` → type →
`States` → `default` / `hover` → `label` + `button`. `button` **is** the
painted CTA (`layer-name` on that root). Never wrap it in an unnamed
Frame or a 24px Slot. Never `position: absolute` to fake a fill.
Default|Hover stay a pair inside one object (row, gap 12). Do not lay
two CTAs side by side. Source board gap is **16px**. Pin Source's right
edge just left of `home-desktop`.

**Interactive pair rows (1.1.35).** `paperPairRowHtml` States is a **column** (closed | open stacked), not a side-by-side row.

**390 is nav only.** `nav-mobile-390` stays narrow (captured width /
`max-width: 390px`). `nav-mobile-768` caps at 768. Forms, FAQ, desktop
dropdown, and navbar links keep their own width — do not clamp them to
390. Open hamburger/dropdown HTML is `position: relative` (drop
`top`/`left`) so the panel sits in-flow. `Interactive components` is
`height: fit-content` so later sections stack below.

**One capture per button label** on the page, not every instance. Keep a
real serialized fill when measured bg is transparent (do not wash a green
CTA to white).

**No visible hover → Default only.** If a button CTA is detected and
default/hover look the same (`changed: false`, same fill, or only a
color tick on a transparent root), still park **Default** and omit the
Hover cell. Do not skip the CTA. Process cards / blog titles that are
not CTAs stay off. Closed|open (nav / FAQ) still writes.
`hasVisibleHoverDelta` gates the Hover cell, not the whole item.
Footer / nav `text-link` color change **is** a visible Hover (grey →
indigo). Buttons keep the paint-only rule.

**Ghost pills are buttons.** A rounded control with a visible stroke and
no fill (Hire An Expert) is a CTA. Do not require a solid
`background-color` to capture it.

## No GIFs

Earlier versions recorded looping GIFs. They are gone from the pipeline.

| | GIF | State pair |
|---|---|---|
| Size, one hover | ~350–420 KB | **2–4 KB** (WebP) or a few KB of HTML |
| Readable by the model | **No** — reading a GIF yields one frame | Yes |
| Directly implementable | Eyeball it | Exact computed values |
| Wasted frames | ~20 of 27 identical | none |

A measured hover is a **state change plus a duration**. The intermediate frames
are interpolation; the browser regenerates them from `transition`. Recording them
costs two orders of magnitude in bytes and cannot be read back. Capture the two
endpoints, measure the timing, and let CSS do the tween.

**When motion genuinely needs frames** — overshoot/bounce keyframes, canvas or
WebGL pointer effects, marquees, staged multi-step reveals — capture compressed
**WebP stills** at the interesting moments and say so in the notes. Never GIF.

## Place in the pipeline (not public 4.1–4.4)

In web2html, Design Library mine + seed is **1.3**, then the agent pulls unique
buttons and cards from token-seeded `home-desktop` onto FRAME `Buttons` and
FRAME `Components` (`pull-desktop-specimens.mjs`, then
`author-button-hover.mjs`). This Capture Tool path is leftover **1.4** live
hover (`open-capture`). 1.4's required half is the human Paper walk.

What the extension captures, and the rules a take follows:

- **Skip floating fixed chrome** — "builder watermark", "Remix for free",
  template purchase badges, cookie bars are not part of the design.
- **Navbar links and footer links: max 2** default | hover **link** pairs each
  — not the whole bar or footer. Nav and footer links repeat one pattern, so
  more states read as noise. Pill CTAs that sit in a header or footer band are
  buttons.
- **Buttons, CTAs, text links with icons** — default + hover each. Dedup is per
  section (`section|label|size`), never page-wide: the same CTA copy in the
  hero, a band and the footer is three components. Label rows by the
  **desktop** section ID (`01 · Get 14 Days Free Trial`), from
  `capture/home-desktop/layer-ids.json` / `section-ids.json`.
- **Form fields + their buttons.** Do not hunt accordions; a human says if a
  missing hover belongs on the board.
- Hover-to-open dropdowns and click burgers (768 / 390) go to FRAME
  `Interactive components`, never a navbar-container serialize.

## Why a real, visible Chrome

The extension runs in the person's own Chrome with trusted pointer input, so a
live `whileHover` fires. Motion `whileHover` is **not** CSS `:hover`: headless
Chromium plus `prefers-reduced-motion: reduce` either no-ops the variant or
applies a reduced one (kp-subba: a purple-band white pill changed type to
near-white and kept a white fill, instead of going black). CSS `:hover` can
still flip `el.matches(':hover')` and a text color, so `hoverConfirmed: true`
is not proof the designed fill landed. Settle entrance animations with
`reducedMotion: 'reduce'` on load, then `no-preference` **before** any hover,
and measure the live pill fill (often an inner frame) for the hover
`backgroundColor` — never restore the default `sourceBackground` onto the
hover file.

**Hover-slot chrome must not ship (1.1.36).** Source · Hover States
DEFAULT/HOVER cards, 780 column padding, `section-number`, and `list`
wrappers are documentation frames. `get_jsx` / rebuild HTML ships only
the actual component (the painted `button`). The rebuild interactive
node is that pill, not the card. Pitfall #90.

**Park states (P-0 first).** `Ruler · desktop` must exist first. Buttons and
footer text links park as stacked Component rows on FRAME `Buttons`.
Screenshots stay on their own board and are number + shot only. Do **not**
repeat a "States + hover" title on every section. Label by object type only
(`Button`, `Text link`, `Pill`, `Social icon`) — never a class or component
name. Default | Hover. Same button **label** = one capture, not every
instance. At 1.5 the human fails the file when a captured button or footer
link has no pairs on that Source row. Other review frames park in a
**horizontal row** **≥100px** under the ruler. Pin Source's right edge just
left of `home-desktop` and grow left. Ignore `Interactive components` when
computing lander `rightEdge`.

### Rotated icons — Paper rotates about the top-left corner

A browser rotates an element about its **centre** (`transform-origin: 50% 50%`).
Paper rotates about its **top-left** and pins `transform-origin: 0% 0%` — it is
not settable through `write_html` **or** `update_styles`, both of which report
success and change nothing. Any rotated element therefore lands somewhere else
after import.

This is not exotic. Icons are routinely built as one rotated glyph: Storm's FAQ
close mark is a `+` rotated 45°, and it imported 12px left and 5px down, half
out of its circle and clipped by the row.

`trim-styles.mjs` compensates geometrically. For a `w×h` box rotated by θ about
its top-left, the centre moves from `c` to `R(θ)·c`, so the element is shifted
by `c − R(θ)·c` using the independent `translate` longhand — which Paper does
honour, and which composes with whatever `left`/`top` the source used, including
`calc()`. Elements that already declare `translate`, or that carry no explicit
px box, are left alone.

**The captures are Paper-targeted, not browser-targeted.** Opened in a browser —
which already rotates about the centre — the extra translate shifts the glyph.
Same bargain as the `line-height` rewrite; these files exist to be imported.

### Phone burger overlay (C/3)

Walk parents of the first appeared link to measure the overlay (position,
fill, padding, gap, radius). **Do not freeze `box[2]` / capture width** —
phone overlays stretch with the viewport (`left`/`right` gutters, `width:
auto`). Largest-area `position:absolute` on the page picks footer/offscreen
layers. `mark_decorative` sets `pointer-events: none` on the three bars —
retag the **42×42** hit box as `<button>` before JS. Implement in
`rebuild/` (`js/nav-mobile.js`) for **every** matching header.
Pitfalls #43 #44 #45 #74.

## Output contract (runner manifests)

The extension bridge writes a per-folder `manifest.json` of `{ version, takes[] }`
under `source-site/components/<page>/<kind>/`. The richer `states[]` shape below
was written by the deleted state-capture runners; `validate-component-captures.mjs`
and `phase_5_nav_audit.py` still read it when it exists.

```
source-site/components/
├── home/
│   ├── nav/                      # two links × default|hover (not the bar)
│   ├── nav-mobile-768/           # 4.1-M closed|open → Interactive components
│   ├── nav-mobile-390/           # 4.1-M closed|open → Interactive components
│   ├── buttons/                  # each component's default + hover pair
│   ├── forms/ · faq/ · footer/   # FAQ → Interactive; footer → Source
│   ├── dropdown/                 # 01 · navbar-dropdown → Interactive components
│   └── <kind>/manifest.json
└── contact/ · about/ · …         # extra routes (explicit user request only)
```

`manifest.json` per kind:

| Field | Meaning |
|---|---|
| `mode` | `elements` (nav/buttons/forms/footer: many components, 2 states each), `accordion` (FAQ on A/6), `dropdown` / `hamburger` (closed\|open on `Interactive components`), or legacy `container` |
| `pageSlug` / `sectionLabel` | Stage P page and named section owning the interaction |
| `coverage` | candidate/selected counts and `truncated`; truncation blocks A/7 |
| `skipped` | what 4.0 removed, by label — proof the badge really was excluded |
| `states[].hoverConfirmed` | `el.matches(':hover')` asserted at serialize time |
| `states[].changed` | **content** comparison against the default; not a byte-length test |
| `states[].styleDelta` | Changed inline declarations by serialized node position |
| `states[].heightDelta` | FAQ measured growth; every open must be at least 8px |

`validate-component-captures.mjs` is the A/7 mechanical gate. It rejects
missing state files, root HTML without positive px width/height (FAQ
roots must be `width: 100%` / `max-width: 100%` and `height: fit-content`,
not a captured px box), truncated
candidate pools, unconfirmed hovers, and FAQ opens without measured growth. A
confirmed `changed: false` hover is retained as evidence, not rejected. Empty
`forms`/`faq`/`dropdown` kinds are allowed only when their manifest records a
reason. Paper geometry is the second, independent read-only lens; fixes and
reimports stay serial.

### `changed` is a content comparison, never a length comparison

Two serializations of the same component frequently have **identical byte
length** and different content — `rgb(255, 255, 255)` and `rgb(111, 142, 255)`
are both 18 characters. Comparing lengths reports "no hover effect" for a button
that visibly changes colour. The script compares trimmed content. Do the same in
any analysis you write by hand.

A `changed: false` row is a real finding, not a failure: it means the control was
verified to have no hover state. Keep the row; label it in Paper.

## Reading the delta

To state exactly what changed between two states, diff the two HTML files and
report the computed values — that is the implementable spec:

```
background-color  transparent      → rgb(26, 26, 26)
color             rgb(173,173,173) → rgb(255, 255, 255)
```

For a pixel-level answer (what moved, and where), screenshot both states and
compare decoded pixels — never compressed bytes, which scramble wholesale on any
change. A changed-pixel **bounding box** localises the effect to the element and
catches changes a computed-style diff misses, such as a border painted by a
pseudo-element.

Mechanism vocabulary for notes: `css-transition`, `css-hover`, `css-animation`,
`js-class-change`, `dom-added`, `pseudo-element`, `canvas`, `none`.

## Feeding Paper

The bridge (`capture-extension/bridge/host.mjs`) and `park-capture-boards.mjs`
read the HTML **off disk** and write it through the Paper MCP, so a large
payload never passes through the agent's context. Token-pass the written nodes
with `apply-theme-tokens.mjs`.

Four things the serializer output needs before Paper renders it correctly, all
handled by `trim-styles.mjs`:

1. **Phantom borders.** The source page leaves `border-<side>-width` and `-color` with no
   `border-<side>-style`, and hover/default text links often carry
   `border: 1px solid rgba(42, 42, 42, 0)`. Both render nothing in CSS. Paper
   paints a 3px black box or a `#2A2A2A` outline. Strip them. Stage P must run
   the same rules (`trimPaperStyles`) — A/6 looking clean is not enough.
2. **Fixed px line-height → `120%`.** A `line-height: 32px` on a 16px font inside
   a 20px-tall box pushes the glyphs off centre once Paper re-measures the text,
   and the label no longer sits in its field. A relative line-height is computed
   from the font size, so the box always hugs the text. This is the single most
   common cause of broken vertical alignment on imported inputs and buttons.
3. **Logical duplicates.** `border-block-*`, `inline-size`, `block-size` etc.
   duplicate the physical properties already present.
4. **Paint-only noise.** `caret-color`, `outline-color`, `text-emphasis-color`,
   `appearance`, `unicode-bidi` — Paper does not render them.

Together these cut the payload to **~25–35%** of the raw serialization.

**Cost of the line-height rule, stated plainly:** a paragraph whose source leading
was 150% arrives tighter. Alignment correctness is what is being protected;
screenshot multi-line text after import and raise it locally if it reads cramped.

### Always double-check alignment after import

Do not take the screenshot's word for it. For at least one text node inside a
field or button, confirm with `get_computed_styles` that:

- `lineHeight` is a **percentage**, not a px value;
- the text node's `height` ≈ `fontSize × 1.2`;
- the parent frame's `height` = text height + its vertical padding, and the
  parent has `alignItems: center`.

If the numbers do not add up the text is not centred, no matter how it looks at
low zoom.

**Always pass `--file <paperFileId>` explicitly.** The MCP client opens its own
session whose "sticky" file is not necessarily the one you are working in;
without it, writes land in whichever file was last opened.

### Paper quirks worth knowing

- Paper cannot evaluate `calc()`. Positions using it need explicit pixel values.
- `transform-origin` defaults to `0% 0%`, so a rotated element (a tooltip caret)
  swings out of place. Pin it to `50% 50%`.
- A negative `z-index` can paint an element behind its own row background.
- Children are clipped to their frame even with `overflow: visible` — give a
  wrapper enough height for anything that overhangs.

## Gotchas

- **Scroll the container into view before capturing its default state.** Hovering
  a child auto-scrolls; without an explicit scroll first, the default is captured
  while the component is off-screen with reveal children still at `opacity: 0`
  (which the serializer drops), producing a default far smaller than every hover
  state. The footer is where this bites.
- **The source page unmounts hover-opened panels on close**, destroying any element tags.
  Re-open and re-tag before each item rather than tagging once.
- **The serializer injects an overlay** that can steal the pointer mid-capture
  and close a hover-opened panel.
- The serializer **drops zero-opacity nodes** — settle the first paint with
  `reducedMotion: 'reduce'`, then turn it **off** before hover so live `whileHover`
  `whileHover` can run (Pitfall #30).
- An active nav item often shows no hover delta because it is already in the
  hovered style. Record it as `changed: false` and note why.
- Cross-origin iframes are skipped. Open shadow DOM is traversed.

## Step 8a consumption

**Implement from hover HTML, not `styleDelta[0]`.** The implementable fill
and type live on the painted control in the hover HTML file (the `<a>` with
`border-radius` + `padding` + `background-color`). `manifest.styleDelta[0]`
is often the Slot or ancestor (Pitfall #33, sibling of #30). Ignore
`hoverColor` / computed `color` of `rgb(0,0,238)` — that is the UA unvisited
link, not the design. Same CTA label in two Stage P sections is two recipes;
do not emit one global `a[data-component=BtnDark]:hover`.

Walk each take folder (and any `manifest.json` with `states[]`) and implement every `changed: true` state in the
rebuild, using the measured values verbatim. Record the outcome per row in
`qa/animation-parity.md`:

```markdown
| # | component | control | change | rebuild selector | status | notes |
|---|---|---|---|---|---|---|
| 1 | navbar | Features | bg → rgb(26,26,26); text → #FFF | .nav a:hover | implemented | 200ms ease |
```

`status` ∈ `implemented` / `partial` / `accepted_drift` / `blocked` / `n-a`.
`changed: false` rows are `n-a` with the reason. Step 8's gate blocks on any row
left `partial` or blank.

## Removed paths

The GIF recorder (`extension/`, `scripts/capture-hover-reel.mjs`) and the
Playwright HUD (`human-hover-session.mjs`, `human-hover-hud.mjs`, `hud-phases.mjs`,
`hud-ai-walk.mjs`, `navbar-picker.mjs`, `capture-nav-breakpoints.mjs`,
`listen-human-hover.mjs`, `park-human-to-paper.mjs`) are **deleted**, not
deprecated. Nothing in the pipeline may reopen an in-page HUD: 1.2 is headless
and 1.3 is `capture-extension/`. If you find a doc or script still naming one of
those files, that reference is stale — fix it rather than restoring the file.

Tests: `npm test`. One-time setup: `npm i && npx playwright install chromium`.
