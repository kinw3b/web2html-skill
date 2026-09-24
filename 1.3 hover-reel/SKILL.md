---
name: hover-reel
description: Capture a live site's interactive COMPONENTS on the homepage (`/`) as default/hover state pairs of Paper-ready inline-styled HTML, then rebuild them in Paper as real editable layers. No GIFs. Default is one page. Extra routes require --allow-multi-page and an explicit user request. Uses visible Chrome so live whileHover fires. Inside website-to-html, 1.3 fills FRAME Buttons + Components from desktop (`pull-desktop-specimens.mjs`) and authors button hover from source CSS (`author-button-hover.mjs`); this Capture Tool is leftover 1.4 hover only. Public 4.1–4.4 are the later optional Phase 4 page import. Triggers - "hover reel", "capture hover states", "navbar hover states", "component states to paper", "A/6", "capture the navbar", "hover parity".
version: 1.1.109
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

## Capture Tool extension (1.4 leftover · OPTIONAL · 1.1.106)

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
per kind. `--auto` is CI / leftover only.
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

**Homepage only.** Default `--pages home` and `--max-pages 1`. Extra routes
require `--allow-multi-page` **and** an explicit user request. **Exit** if
more than one page is selected without the flag.

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

## Place in the pipeline — A/6 internals (not public 4.1–4.4)

These run **after Stage P has captured every contract page and named section**.
In web2html, Design Library mine + seed is **1.3**, then the agent pulls unique
buttons and cards from token-seeded `home-desktop` onto FRAME `Buttons` and
FRAME `Components`. This Capture Tool path is leftover **1.4** live hover
(`open-capture`). 1.4's required half is the human Paper walk.

| Step | What |
|---|---|
| **A/6.0** | **Skip floating fixed chrome** — "builder watermark", "Remix for free", template purchase badges, cookie bars. Not part of the design being rebuilt. |
| **A/6.1** | **Navbar links** → Paper, **max 2** default\|hover **link** pairs — not the whole bar. Hover-to-open dropdowns (opt-in) and click burgers (768 / 390) go to FRAME `Interactive components` — not this board. |
| **A/6.2** | **Buttons, CTAs, text links with icons** → Paper, default + hover each. Walk Stage P sections one by one |
| **A/6.3** | **Form fields + their buttons** (`--kind forms`) → Paper. **Do not hunt accordions.** A human says if a missing hover belongs on A/6. |
| **A/6.4** | **Footer links** → Paper, **max 2** default\|hover **link** pairs — not the footer section |

### Max 2 states for nav and footer

Nav and footer links repeat one pattern. Capturing all six produces near-identical
states that cost time and read as noise — **two is the rule** (`--max-states`,
default 2).

Which two matters. Controls are grouped by visual pattern (tag, solid background,
corner radius, height bucket) and the groups are ordered by **how often the
pattern repeats**, then the first two controls are taken from the largest group
inward. Picking in DOM order instead lands on the logo and the submit button —
which usually have no hover state at all, producing two `changed: false` rows and
zero information.

### 4.1 is the nav LINKS, not the navbar

Serializing the header container (logo + links + trial CTA) is the wrong
component. 4.1 writes **element** pairs: two representative **links**, each
`default | hover`. Pill CTAs that live in the header belong in 4.2.

### 4.2 walks every Stage P section

Do not sample buttons from the first matching label on the page. Walk the
Stage P section manifest **in order**. The same CTA copy in two sections
("Get 14 Days Free Trial" on the hero, the purple band, and the dark
footer-CTA) is **three components**. Dedup is per-section (`section|label|size`),
never page-wide. Do not classify list heads as accordions.
Header pill CTAs stay in 4.2 even when they sit inside nav chrome.

**Label by desktop section ID.** A/6 rows are `01 · Get 14 Days Free Trial`,
not `… · header`. IDs come from the **desktop** Stage P manifest
(`capture/home/section-ids.json`). Say “fix 08” and the purple-band CTA
is the one. Tablet/phone slugs are not the review handle.

### 4.4 is the footer LINKS, not the footer

A whole `<footer>` carries a newsletter CTA, a blurb, a logo and a copyright line,
none of which have hover states. 4.4 writes **element** pairs for two
representative **text links**, not the footer block and not the link-column
container. Pill CTAs in a nearby CTA band are 4.2. Anchoring on "a share of
the footer's total links" fails when the columns are siblings; smallest-area
wins when finding the footer root, then the **links** are what get serialized.

## Why this uses visible Chrome

Headed Chrome is required so a person can watch the run.

- A **drawn cursor** MUST travel to each control. Playwright/CDP has no OS
  pointer — `x-paper-cursor` is the arrow you see.
- A **HUD** MUST show the pass, `n/N`, and the current label for the whole
  run (e.g. `hover-reel · 3/18 · Navbar · Pricing`). That is `x-paper-cursor-hud`.
- `--headless` skips both the pointer and the HUD. CI only.
- If you cannot see the pointer move, the run is broken — fix the overlay, do
  not keep capturing blind.

A/6 uses the **same visible Chrome launch as Stage P**
(`launchOptions({ visible: true })` → `channel: "chrome"`, `headless: false`).
The overlay is skipped by the serializer (`x-paper-` prefix).

Motion `whileHover` is **not** CSS `:hover`. Headless Chromium plus
`prefers-reduced-motion: reduce` either no-ops the variant or applies a
reduced one (kp-subba: purple-band white pill changed type to near-white and
kept a white fill, instead of going black). CSS `:hover` can still flip
`el.matches(':hover')` and a text color, so `hoverConfirmed: true` is not
proof the designed fill landed.

Settle entrance animations with `reducedMotion: 'reduce'` on load, then
`emulateMedia({ reducedMotion: 'no-preference' })` **before** any hover.
Drive a real pointer to the painted box centre (`mouse.move` with steps, not
`locator.hover({ force: true })`) and call `__hrCursor.move()` so the drawn
arrow travels with it. Measure the live pill fill (often an
inner frame) and pass that as hover `backgroundColor` — never restore the
default `sourceBackground` onto the hover file.

## Run it

```sh
# A/6 — homepage only, serially; 4.3 is forms only
node $SKILLS/hover-reel/scripts/capture-site-component-states.mjs \
  --pages-json source-site/pages.json --pages home \
  --capture-dir capture --out source-site/components --max 40

# A/7 — mechanical coverage gate before any Paper state artboard is accepted
node $SKILLS/hover-reel/scripts/validate-component-captures.mjs \
  --dir source-site/components --expected-pages home \
  --json qa/component-state-coverage.json

# Build each page/kind into one A/6 · {page} · states board (sections, not new frames)
node $SKILLS/hover-reel/scripts/build-paper-states.mjs \
  --dir source-site/components/home/nav --file "$PAPER_FILE_ID"
```

| Flag | Default | Meaning |
|---|---|---|
| `--url` | — | Page to capture |
| `--kind` | `nav` | `nav` \| `buttons` \| `forms` \| `footer` (`faq` only with `--allow-faq`; `dropdown` / `navbar-dropdown` only with `--allow-dropdown`; `nav-mobile-768` / `nav-mobile-390` run when the icon is painted) |
| `--page` | — | Single-page override; writes `<out>/<page>/<kind>/` |
| `--section-manifest` | — | Stage P `capture/<page>/manifest.json`; maps each state to a section |
| `--out` | `source-site/components` | Output root; the page runner nests `<page>/<kind>/` |
| `--max` | 40 | Cap on components/controls per kind; A/7 fails if the pool is truncated |
| `--width` / `--height` | 1440 / 1000 (dropdown: **1600** / 1100) | Capture viewport. Dropdowns use the Stage P desktop lander, not A/6's 1440. |
| `--headless` | off | CI-only. Default is visible Chrome, same as Stage P. |

`build-paper-states.mjs` flags: `--dir`, `--file` (**required** Paper file id),
`--board` (default `A/6 · {page} · states`; dropdowns and burgers default to
`Interactive components`), `--section` (Navbar / Buttons /
Accordion / Forms / Footer / Dropdown / Nav mobile from `kind`), `--title` (legacy; ignored for the
artboard name), `--dark` for dark sites, `--cols N` for a wrapped grid —
**container mode only**. A/6 kinds append as **sections of one board**.
Dropdowns and burgers never append onto A/6 — they own the `Interactive components`
frame. After that write, **token-pass is required**
(`apply-theme-tokens.mjs --only "Interactive components"`). New review frames
park in a **horizontal row** under `Ruler · desktop`.
`capture-site-component-states.mjs` accepts `--pages-json`, `--pages`,
`--capture-dir`, `--kinds`, `--max`, `--max-states`, `--width`, `--height`,
`--allow-faq`, `--allow-dropdown`, and `--headless`.
`validate-component-captures.mjs` is read-only and writes a gate report; it
accepts `--dir`, `--expected-pages`, and `--json`. When `--expected-pages`
is set (homepage-only: `home`), leftover first-run folders
(`about/`, `pricing/`, …) are **ignored** and warned, not walked as extra
pages. `--pages home` on capture does not delete those folders.

### Do not hunt accordions

Feature lists, insight cards, and date chips are not FAQs. Default A/6
kinds are `nav,buttons,forms,footer`. `--kind faq` writes an empty
manifest unless the human passed `--allow-faq`. If a hover is missing
from the board, the human says so — the agent does not guess accordion
rows.

**One of a repeating pattern.** Identical CTAs, pills, and links share
one token. A newly scraped visual pattern (size + paint + hover) gets a
new name (`pill`, `text-link`, `navbar-dropdown`), never a reused
`btn-primary`. On Source · {page}, show the type (`Button`, `Text
link`), not that token. If a section has more than two of the same
pattern, keep one specimen. One-of-a-pattern **FAQ / accordion cards
are fluid** in the `A/6 · {page} · states` parent — same column as
Navbar / Forms. Footer text links park on Source. Slot and imported root are `width: 100%`,
`max-width: 100%`, `height: fit-content`. Never pin the captured rect
(`width: 99px` or whatever the live row measured). Label wrap is fine.
`--allow-faq` is still required.

**Accordion top-align (1.1.21).** Collapsed vs open differ in height, so
FAQ cards, Slots, and both inners use `align-items: flex-start` (and
`align-self: flex-start`) — never `center`. Do not size the Slot from
`heightAfter` / `openH`. After `write_html`, force the capture root to
`height: fit-content` so a leftover open height (190px on a 99px
collapsed row) cannot vertically center the title. Strip source
plus→minus `translate` / `rotate` so the icon stays in the 35×35
circle on the title row. Width stays `100%`.

**Slots auto-fit.** Paper clips children to a fixed-px Slot even with
`overflow: visible`. `build-paper-states.mjs` sets Slot `height:
fit-content`, then re-asserts after `write_html`. FAQ slots stay
`width: 100%` of the section column and are not sized from
`heightAfter`. Screenshot the artboard;
if anything still clips, `update_styles` the Slot and artboard to
`height: "fit-content"` again.

**Ancestor fill (kp-subba).** Serializer often omits the parent band. Hero
CTA and footer links arrive as white type with no background; a white Paper
cell makes them invisible. Capture records `ancestorBackground`;
`build-paper-states.mjs` paints the Slot and the imported root when the
root is transparent and the type is light. Do not strip that fill.

**Native paint, no floating chrome (1.1.17 / 1.1.38).** Default and hover
HTML must look like the Stage P lander buttons: native `border` /
`background-color` / `background-image` on the pill. Never a
`position:absolute` Frame, Rectangle, stroke, or gradient overlay sitting
on the label (Pitfall #95). A Frame whose only child is a paint Rectangle
is still a floater — hoist the fill onto the pill and drop it.
`prepareStateHtml` runs `flattenDecorativeAbs` then `trim()` before the
file is written and again in `build-paper-states.mjs`. A leftover overlay
fails A/7 (`validate-component-captures.mjs`) and will leak into `get_jsx`.
`trim()` also drops invisible source link outlines so A/6 does not grow
`#2A2A2A` boxes the lander just had stripped.

**One label, not a text-swap stack (1.1.17).** Source slide/swap label
animations serialize both copies. Collapse consecutive siblings with the
same text so Paper and the rebuild do not show a vertical double label.
This is also an A/7 error.

**Hover-slot chrome must not ship (1.1.36).** Source · Hover States
DEFAULT/HOVER cards, 780 column padding, `section-number`, and `list`
wrappers are documentation frames. `get_jsx` / rebuild HTML ships only
the actual component (the painted `button`). The rebuild interactive
node is that pill, not the card. Pitfall #90.

**Even button inset (1.1.8).** The ancestor-color `button` layer hugs the
control with **24px** padding on all sides (`width: fit-content`,
`border-radius: 12px`). Never `position: absolute` / `inset: 0` to paint
the fill.
Never `width: 100%` + `flex-start` on nav / button / footer pills — that
pins the control to the top-left and leaves a empty trail on the right
(Pitfall #38). **FAQ is the exception (1.1.20):** accordion cards are
full-width patterns and must stay `width: 100%` of the A/6 parent.
Keep the section band color; only the inset changes.

**Park states (P-0 first).** `Ruler · desktop` must exist first. Do **not**
seed `A/6 · {page} · states`. **Buttons (4.2) and footer text links**
park as stacked Component rows on FRAME `Buttons`. Screenshots
stay on their own board. Nav / forms /
FAQ / dropdowns / 768/390 burgers are **sections** on FRAME
`Interactive components`. Open hamburger/dropdown HTML must be
`position: relative` (drop captured `top`/`left`) so the board can hug
the open panel. The `Screenshots` board is number + shot only.
Hover pairs stack on FRAME `Buttons`. Do **not** repeat a "States + hover"
title on every section. Label by object type only (`Button`, `Text
link`, `Pill`, `Social icon`) — never a class or component name.
Default | Hover. Same button **label** = one capture, not every
instance. At 1.5 the human fails the file when a captured
button or footer link has no pairs on that Source row. Other review
frames park in a **horizontal row** **≥100px** under the ruler. Pin
Source's right edge just left of `home-desktop` and grow left. Ignore
`Interactive components` when computing lander `rightEdge`.

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

**Design-system eyebrows (1.1.13).** Cell labels are tokens a rebuild can
keep: `navbar-link`, `navbar-link:hover`, `navbar-dropdown`, `btn-primary`,
`btn-secondary`, `pill`, `text-link`, `footer-link`. Do not print the
marketing string (`PRODUCT — DEFAULT`, `01 · GET 14 DAYS FREE TRIAL`).
Variants follow the visual pattern (height + paint + hover delta), not
the marketing label. Transparent gradient CTAs and date chips must not
share `btn-primary`. Cell labels and Slots are Autoflex, center-aligned. Compact
pill/button roots that serialize as `flex-start` are rewritten to
`center` so A/6 matches the desktop lander (Paper top-left is not the
page).
The red section badge still maps the instance to a Stage P layer.
Pitfalls #46 #56 #57 #58.

**Buttons/CTAs/forms always lay out as `default | hover` pairs, two per row.**
Each component gets its own row holding both of its states. An N-column grid is
wrong here: with three columns a component's default lands at the end of one row
and its hover at the start of the next, which breaks exactly the comparison the
artboard exists to make. `--cols` is ignored in element mode for that reason.

### 4.1 dropdowns → `Interactive components` (1.1.24)

Navbar dropdowns and 768/390 burgers generate onto the **`Interactive
components`** frame (not a section on `A/6 · {page} · states`). After
`write_html`, catch-at-write binds `var(--token)` for type, color, space,
and radius — do not land raw px/hex and hope 1.4 finds it. Accordion /
dropdown / burger still emit `width: 100%` / `height: fit-content` /
`align-items: flex-start`, then token-pass those nodes in the same write.

Then run the census gate:

```sh
node $SKILLS/url-to-paper/scripts/apply-theme-tokens.mjs \
  --file-id $PAPER_FILE_ID --library design-library/library.json \
  --json qa/token-pass.json --qa qa/token-pass-qa.json
```

`apply-theme-tokens.mjs` must exist (fail if missing). Every node on
landers, A/6, Interactive components, and Design Library is
`rebound` | `leftover` (with why) | `skip-image` | `skip-scribble`.
`coverage.missing.length > 0` or an unlisted raw hex/px **fails**.
Pitfall #76.

### Hover-triggered dropdown navs

Navbar hover-to-open menus are **not** a section on `A/6 · {page} · states`.
They get their own FRAME named exactly **`Interactive components`**. FAQ
stays on A/6 (`--allow-faq`). Do **not** hunt dropdowns on every site.

**Opt-in.** `--allow-dropdown` (alias kind `navbar-dropdown`). Without the
flag, `--kind dropdown` writes an empty manifest. With the flag, capture
runs only when a real hover-to-open panel of links appears at the
**desktop lander (1600)** — not A/6's historic 1440. A page-jump link is
not a dropdown. A hamburger at 768 / 390 is **4.1-M** on **this same
frame** — not a second board, not A/6. Do not invent a burger on desktop
when the icon is absent. Spec board (Yearning orchard `6IW-0`) is
2800×684, right of A/6; do not write that live file from this package.

**One of a pattern.** Closed | open, two cards, same fidelity as FAQ
collapsed | open: Slot + cards + inners are `width: 100%` /
`max-width: 100%` / `height: fit-content`, `align-items: flex-start`
(closed vs open differ in height — never center). Never size the Slot
from `openH` / captured px. After `write_html`, force the capture root
to `height: fit-content`. Strip source chevron `translate` / `rotate`
leftovers. Red `#E11D2E` 36px badge with the section id.

**Park.** Under `Ruler · desktop`, horizontal row, ≥100px below the
lintel, after Design Library (slot 6 A/6, slot 7 Interactive components).
Ignore this board when computing lander `rightEdge` (same exemption as
Design Library / A/6 — not Source · home).

```sh
node $SKILLS/hover-reel/scripts/capture-site-component-states.mjs \
  --pages-json source-site/pages.json --pages home \
  --capture-dir capture --out source-site/components \
  --allow-dropdown
node $SKILLS/hover-reel/scripts/build-paper-states.mjs \
  --dir source-site/components/home/dropdown --file "$PAPER_FILE_ID"
# → artboard "Interactive components" (refuses --board "A/6 · …")
```

The detector reuses `capture-menu-states.mjs` / `dropdown-capture.mjs`:
diff visible labels closed vs open, scoped ancestor, hover that sticks.
`capture-menu-states.mjs` writes the same **closed | open** HTML pair
(default `--width 1600`). `--out foo.json` still dumps JSON, plus HTML
in `foo/`. It is no longer JSON-only.

### 4.1-M — click hamburger on the same `Interactive components` frame (1.1.24)

`capture-menu-states.mjs` is **hover-to-open at 1600** (`01 · navbar-dropdown`).
A burger is a **click**. Paper `get_jsx` of a collapsed header is the
**closed** icon only. Run `capture-hamburger-states.mjs` at **each**
artboard width that paints the icon (typically **768 and 390** — the 768
tree is what you see at 1099). Closed | open, same FAQ fidelity (width
100%, flex-start, fit-content, strip transforms, red badge). Rows:

| Width | Label |
|---|---|
| 1600 hover mega-menu | `01 · navbar-dropdown` |
| 768 click | `02 · nav-mobile-768` |
| 390 click | `03 · nav-mobile-390` |

`--allow-dropdown` stays for hover mega-menus. Burgers run when the icon
is visible at that width — do **not** invent a burger on desktop. Do
**not** dump burgers onto A/6 or a second board. After `write_html`,
**token-pass** (`apply-theme-tokens.mjs`) walks this frame the same way
it walks landers + A/6. Specimens and imported roots use `var(--token)`,
not raw `16px` / `#0A073B`. generate → token-pass. Pitfall #74.

```sh
node $SKILLS/hover-reel/scripts/capture-hamburger-states.mjs \
  --url "$URL" --width 768 --height 1024 --kind nav-mobile-768 \
  --out source-site/components/home/nav-mobile-768
node $SKILLS/hover-reel/scripts/capture-hamburger-states.mjs \
  --url "$URL" --width 390 --height 844 --kind nav-mobile-390 \
  --out source-site/components/home/nav-mobile-390
node $SKILLS/hover-reel/scripts/build-paper-states.mjs \
  --dir source-site/components/home/nav-mobile-768 --file "$PAPER_FILE_ID"
# → FRAME "Interactive components" + token-pass (refuses --board "A/6 · …")
```

Walk parents of the first appeared link to measure the overlay (position,
fill, padding, gap, radius). **Do not freeze `box[2]` / capture width** —
phone overlays stretch with the viewport (`left`/`right` gutters, `width:
auto`). Largest-area `position:absolute` on the page picks footer/offscreen
layers. `mark_decorative` sets `pointer-events: none` on the three bars —
retag the **42×42** hit box as `<button>` before JS. Implement in
`rebuild/` (`js/nav-mobile.js`) for **every** matching header.
Pitfalls #43 #44 #45 #74.

## Output contract

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
├── contact/ · about/ · …         # same five-page contract shape
└── capture-run.json              # page/kind commands and exit codes
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

`build-paper-states.mjs` reads the HTML **off disk** and writes it through the
Paper MCP, so a large payload never passes through the agent's context.
Catch-at-write binds `var(--token)` for type, color, space, and radius
before `write_html`. Accordion / dropdown / burger stay `width: 100%` /
`height: fit-content` / `align-items: flex-start`, then those nodes are
token-passed in the same write. `apply-theme-tokens.mjs` must exist.

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

Walk each `manifest.json` and implement every `changed: true` state in the
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
