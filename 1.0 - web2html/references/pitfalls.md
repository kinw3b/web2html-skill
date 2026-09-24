# Pitfalls — quick lookup

Use this only after a gate fails. Find the number cited by `SKILL.md`, then inspect the project evidence. Keep customer URLs, Paper IDs, and local paths inside the ignored project folder.

## Eight rules

1. Capture before rebuilding.
2. Keep each viewport's evidence separate.
3. Trust source assets and authored CSS.
4. Get human approval on Paper structure.
5. Build from approved Paper output.
6. Compare at identical viewports.
7. Fix the largest mismatch first.
8. Save proof with the project.

## Numbered lookup

| # | Watch for |
|---:|---|
| 0 | Don't hardcode tokens.css from a previous build |
| 1 | Reveal-on-scroll + headless screenshots = false "missing content" bug |
| 2 | Wrong image for wrong section |
| 3 | Re-typing text instead of copying |
| 4 | Inline styles on hero bg image |
| 5 | Viewport-meta missing or wrong |
| 6 | Font loading FOUT |
| 7 | Apple `meta[name=apple-mobile-web-app-capable]` deprecation |
| 8 | Header transparent over hero, solid on scroll |
| 9 | Reviews: grid vs carousel |
| 10 | Reveal scope: inner elements vs whole sections |
| 11 | Rules copied from the skill's origin sites, not the current one |
| 12 | A declared custom font that was never actually loaded |
| 13 | De-duplicating text while extracting content hides real structure |
| 14 | Fixed chrome outside the section list never lands in Paper |
| 15 | Freehand HTML instead of a Paper brief ships a different site |
| 16 | Conversion failures: self-closing divs, unescaped styles, Tailwind-on-file://, remote images |
| 17 | Building before the Design Library exists in Paper |
| 18 | 1.2 Paper serialize comes in frozen |
| 20 | Frozen desktop geometry-lock |
| 21 | One-row arrange orphans source shots |
| 22 | Tablet listed as sanity, or 768/390 live-assembled instead of authored from desktop |
| 23 | Frozen section roots ignore a stretched artboard |
| 24 | Remote CDN images go blank in Paper |
| 25 | Display headers fall back to system-ui Regular |
| 26 | A token/BEM page or a get_jsx dump ships as the first build |
| 27 | Hover pair cells drop the ancestor fill |
| 28 | Hover capture gets chrome and misses section CTAs |
| 29 | Semantic pass links the label, not the button |
| 30 | Live hover is whileHover, not CSS :hover |
| 31 | Wrapper divs inspect as Times |
| 32 | Decorative absolute layers steal CTA hits |
| 33 | Hover from `styleDelta[0]` / UA link blue, not the painted pill. Invent CSS only when Paper default and hover are identical (#152) |
| 34 | Hover labels use slugs; repeating lists get captured N times |
| 35 | A shared nav-link hover selector hits the wrong instance |
| 36 | A Bold family name pointed at the regular font file |
| 37 | Content frames before canvas rulers |
| 38 | Hover slot stretches and pins the pill top-left |
| 39 | A leftover hover artboard gets invented |
| 40 | Paper stroke overlay clipped by `overflow: clip` |
| 41 | Desktop section IDs legend artboard |
| 42 | Ruler 8px above frames / 5600 lintel too short |
| 43 | Phone hamburger is click, not hover — dump the open state |
| 44 | Overlay menus freeze capture width |
| 45 | Hamburger JS bound only to the 390 header |
| 46 | Hover eyebrows are marketing copy, not a control |
| 47 | Paper photos ship as `background-image` on empty `div`s |
| 48 | Promoted `<img>` still inspects as `div` |
| 49 | Multi-page Paper import |
| 50 | Broken Paper homepage exported |
| 51 | Triple navbar + short sections |
| 52 | Extra rebuild folders, or ship missing layers |
| 53 | Polish trio claimed without receipts |
| 54 | An extra polish stage gets invented after the real passes |
| 55 | Section clips content; agent skips human Paper review |
| 56 | Hover buttons keep floating borders / stacked labels |
| 57 | Every new scrape reuses btn-primary |
| 58 | Hover pills import top-left instead of centered |
| 59 | First source `@font-face` hash is not Latin |
| 60 | Design system snapshots are not components |
| 61 | Layout shells become `<a>` after semantic wrap |
| 62 | Lock page never received design-library class names |
| 63 | 3.4 Chrome never shows the polish report |
| 64 | Design Library census of spacing / type sizes |
| 65 | Heading orphans vs source line breaks |
| 66 | Type sheet stops at `--text-6xl` |
| 67 | Fixed section height clips titles after insert |
| 68 | qa-paper empty-image misses real image gaps |
| 69 | Source line-box titles split into stacked Text siblings |
| 70 | Live images vanish before Paper import |
| 71 | One tall source screenshot instead of per-section clips at 1600 / 768 / 390 (Screenshots board stays 1600) |
| 72 | Design Library appears before the 1.3 mine |
| 73 | Navbar dropdowns land on the lander or Design Library |
| 74 | Burgers get mixed into hover pairs instead of Interactive components |
| 75 | Desktop icon row copied tablet 2+1 wrap |
| 76 | Token-pass rebounds a sample and misses the rest |
| 77 | Layer names come from Paper by **pc-id**; copy matching lands on the wrong node |
| 79 | FAQ answer 85% gutter / missing closed answers / nested role=button |
| 80 | Flattening absolute image stacks to flex |
| 81 | 3.0 skip-link peeks at the top-left |
| 82 | Isolated section shot is green, page stack has a hole |
| 84 | Overlay serialized after content; type unreadable |
| 87 | Overlay navbar parked relative on Paper |
| 88 | Paper fontFamily token is a CSS stack |
| 90 | Painted CTA pill stays a div; tags mode outlines the label |
| 91 | Nav ships as a full-bleed screenshot |
| 92 | Footer stays a div; socials and About are not links |
| 93 | Human checkpoint sees leftover div landmarks / unlabeled fields |
| 94 | Semantic retag snaps titles left |
| 95 | Hover fill is a floating Frame+Rectangle over the label |
| 96 | Live pipeline board left on an old step |
| 97 | Fixed navbar sits behind the hero on Paper |
| 98 | Agent ships a lock and skips the rest |
| 99 | One Chrome per kind floods the desktop |
| 100 | Human hover parked `[object]` instead of a painted button |
| 101 | Hover numbered 03 because capture reserved 01 for nav |
| 102 | Agent starts the 1.4 sign-off half before the HUD says Done |
| 103 | Semantic wrap invents tags because Paper leaves were unnamed |
| 104 | Two Chromes / HUD before navbar / Capture Tool in source shots |
| 105 | Navbar on the list is not on Paper |
| 106 | Auto Mode harvests product and blog loops |
| 107 | Second Chrome for 768 / 390 navbar |
| 108 | `width: 100%` on a flex child instead of Fill |
| 109 | Raw get_jsx dump or React/Tailwind CDN shipped as the page. The dump is not even a lock assistant. 2.1 authors the page. |
| 110 | Capture Tool parks the full Desktop / page shell |
| 111 | Hover HUD opens without Hover States / Components frames |
| 112 | Silent shell: agent waits minutes instead of killing the stall |
| 113 | Theme gallery does not look like FRAME Design Library |
| 114 | Polish treats missing Paper icons and gaps as out of scope |
| 115 | Overlay navbar uses `absolute` and scrolls away |
| 117 | Capture Tool HUD clipped off-screen / navbar pick does nothing on hover |
| 118 | Framer tags every lander band `<header>`; the real navbar is an unnamed top flex row. Header/nav selectors miss it (or grab the dismissed template promo). Paper then gets an empty Navigation slot |
| 119 | Visible Chrome on a Retina Mac ignores the context `deviceScaleFactor: 1`, so source clips land at 3200px and the `Screenshots` board towers over `home-desktop` at 2x width. Clip with `scale: "css"` and cap every row at 1600 |
| 120 | Navbar Auto said “No visible candidate found” on a compact Framer bar (logo + links + dropdown + CTA) because it required a named logo/`<nav>`/`<header>` and rejected every parent that was not one. Score compact top flex rows from those children; skip html/body/main and oversized header/section shells |
| 211 | Desktop Navbar reached Paper, then 768/390 said “No safe Navbar match”: hidden background tabs often layout at 0×0, so every node looks invisible. Capture those widths in a sized popup, wait until `innerWidth` matches, and rematch Framer `Phone`/`Tablet` + `Burger` bars instead of the hidden desktop link row |
| 121 | Step 1.2 opened a visible Playwright window, an in-page HUD, or a navbar picker. 1.2 is headless: assemble desktop, clip 768/390 shots, park serializer chrome, author 768/390 from desktop, screenshot-QA, geometry postflight, exit. Navbar refine / dropdown / hover / component capture is 1.3 in `capture-extension/`. The Playwright HUD is deleted, not deprecated |
| 122 | RETIRED (2.8.140). Do not run `flatten-paper-buttons.mjs` to clean wrapper soup | The 1.2 pc-id import is the structure. See #131 |
| 123 | 1.4 phase 4 collapsed stat numbers, captions, and 56px section headings as if they were buttons | Two gates. (a) A candidate must read as a control: paint, a `btn`/`cta`/`link` name hint, or a chain ≥3 frames deep. (b) Phase 4 runs after the token pass, so font sizes come back as `var(--text-4xl)` — resolve them via `get_tokens` then the Tailwind default text scale, and **fail closed** when unresolvable. An unresolved size read as "no font size" and let every heading through. Always `--dry-run` a new site first and read the label list before writing |
| 124 | 1.4 phase 4 hoisted an inner wrapper's `justifyContent: flex-start` onto a button that was already centered, de-centering every label | The survivor (OUTER frame) is authoritative — inner values fill only props it leaves visually null. `get_computed_styles` resolves everything, so "unset" arrives as `transparent` / `0px`, not as a missing key. Never innermost-wins |
| 125 | A collapsed button lost its fill and radius entirely: the plan hoisted `display: contents` from a Framer wrapper, which deletes the box the pill paints on. `overflow: clip` likewise sheared labels | Treat `display: contents` as a null value so the `flex` default wins, and never hoist `overflow`. Both were found only by diffing a hand-built reference button against its unflattened twin — do that on any new site before trusting the plan |
| 126 | An icon CTA (`Get Started Now →`) was skipped entirely by phase 4: it is a fork, not a chain, so nothing was cleaned. Reparenting its SVG naively then blew the arrow up to full button width | `branchOf` walks each branch to its leaf and accepts a media leaf; the control keeps exactly one Text leaf plus ≤4 branches and must be painted or button-named. Pin percentage-sized leaves (`width: 100%` measured against a 16px wrapper) to their measured px BEFORE the move. Scope a single suspect with `--node <id> --dry-run` |
| 127 | Phase 4 produced a clean `button` that was still buried under two unnamed pass-through frames — collapsing only ever looked downward | `unwrapAncestors` walks UP while each parent is an unnamed, single-child, unpainted, unlocked frame with no flex intent, then lifts the control `before` its outermost wrapper (sibling-relative, so a second unwrap in the same parent cannot shift it) and deletes that wrapper. Stops at the first real container — it does not flatten section layout, and never passes a named frame. Compare bounds in **world** coordinates: re-parenting legitimately changes parent-relative x/y. A control already lean inside needs the `lean` shape or it can never be unwrapped |
| 128 | The painted button was the INNER frame, sized `width/height: 100%` inside a bare pass-through. Lifting it into the 700px column re-measured 100% and the pill swallowed the section | `pinNodeSize` pins any percentage-sized node to its measured px BEFORE it moves — leaves entering the control and the control leaving its wrapper. Never assume the node you were handed is the button; the planner picks the painted frame and treats the bare wrapper as an ancestor. Under `--node` the scoped node is not the unwrap ceiling (that silently suppressed every unwrap) — load its ancestor spine and stop at the top |
| 129 | Retired — dump era. Stamp-pc-id-then-retag / paper-semantic-tree as a required 2.0 path. 2.0 does not join on capture ids. |
| 130 | Retired — dump era. apply-semantic-tree-after-semantics_pass is not a required 2.0 path. 2.0 does not join on capture ids. |
| 131 | 1.3 `flatten-paper-buttons` collapsed imported frames: navbar Sign In + Get Started merged into one label, feature grids collapsed (predates the 1.3 renumber, was mislabeled 1.4) | Never run button cleanup. 1.2 keeps scrape / Paper names; 1.3 is mine + tokens only. The retired script now exits 1 |
| 132 | Build started at 2.1 while Paper still had open comments, because the user said “build” and never mentioned the pins | First action of 2.1 is `list-paper-comments.mjs`. Exit 2 = apply every thread, resolve it, re-run. The user prompt does not waive this |
| 133 | Chrome opened the 2.1 draft, or 2.4 completed without TAGS on | Do not preview 2.1. After the 2.3 loop, inject the overlay and run `open-build-review.py . --stage 2.4` (`?qa-outlines=tags`). Overlay default is TAGS. |
| 134 | Retired — dump era. apply-semantic-tree-is-the-ship is not a required 2.0 path. 2.0 does not join on capture ids. |
| 135 | Capture Tool badges say 00/01 while Paper is `01 · hero` | Framer paints the hero as `<header>`, so treating every header as chrome numbered takes as 00. Load `review-sequence.json` / `section-ids.json` and treat only a compact top bar as 00 |
| 136 | Retired — dump era. 2.2.d / `responsive_22d_gate.py` is not the live spine. 2.3 is one section at a time vs Paper 1600 / 768 / 390. |
| 137 | Hover is 1.3 source CSS + 3.2 `apply-hover-css.py`, not a 2.2 letter. Reuse `library.json` names. Do not invent `.hero-cta`. |
| 138 | Retired — dump era. extract-inline / token-utilities is not the live 2.0 spine. Paper is the brief. 2.1 authors the page. |
| 139 | Hover fill must recolor the label (`color` and `-webkit-text-fill-color`). Hover is 1.3 source CSS + 3.2. |
| 140 | Retired — dump era. `responsive_22d_gate.py` is not live. Only `width: 100% !important` is the frozen-root hack. |
| 141 | Viewport meta may list `content` before `name`. Accept either order. |
| 142 | Stacking a Framer lock: abs hero photo, `width: 1px` + grow, blanket `width: auto` | `position: relative` + Paper px on photos. Do not `[style*="width: Npx"] { width: auto }` |
| 143 | A testimonials track with `overflow: visible` expands `scrollWidth`. Clip the carousel (`overflow-x: clip`). |
| 144 | Compact 768/390 bar is logo + menu. Hide every header link and CTA. Do not hang a dropdown off the first nav label. |
| 145 | If Paper paints a hamburger, open = the same desktop links stacked. Do not invent a burger. |
| 146 | Retired — dump era. 2.0 does not join on capture ids. 2.3 section list comes from homepage Paper frames. |
| 147 | Clip page overflow before scoring 768/390. `html, body { overflow-x: clip }`. Then clip carousels (#143). |
| 148 | Agent skipped start / capture / 1.4 and shipped a hand-authored or get_jsx `rebuild/index.html` | First tool is `pipeline-progress.py start`. `rebuild_write_gate.py` before any ship HTML. First allowed write is 2.1. A dump is not a lock assistant. `mark` cannot open 2.1+ while 1.1–1.4 are open. `start` quarantines leftover ship pages. Do not polish the freehand file |
| 149 | Agent marked 1.4 and waited for Chrome | `mark --step 1.4 --status active` opens **Paper**. Capture Tool is leftover live hover: `pipeline-progress.py open-capture` prints the stamped URL. Do not leave only `pipeline.html` open |
| 150 | Tags pills drift when the person resizes or scales Chrome | Do not chase overlay coordinates. Lock the source tab to **1600 / zoom 100%** with `Emulation.setDeviceMetricsOverride` (same as 768/390 Navbar). Attach outlines to the live elements. Do not rename Paper from pc-ids. A window that is not 1600 is a different DOM. |
| 151 | 3.4 tidy deleted the live board, or `finish` wiped `capture/` / `qa/` before 1.1–3.4 were done | Tidy only after every step is done. Keep `rebuild/` plus the finished `pipeline.html`. Do not write `NEXT.html`. A leftover `rebuild/index.html` is not permission to sweep |
| 152 | Copy the captured hover pill. Invent CSS only when 1.3 source CSS and Paper default/hover are identical. Hover is 1.3 source CSS + 3.2 `apply-hover-css.py`. |
| 153 | Done claimed to wake an idle agent session, but the workflow still required a manual prompt | Capture Tool **Done** writes `human-hover-done.json` only. 1.4 is the Paper walk; do not wait on Extension Done to mine 1.3. |
| 154 | 1.4 merged solid CTA `#EF4B3C` into a 10% wash `#EF4B3C1A` because merge ignored alpha; `--color-accent` became the ghost fill and seeding recast Book A Schedule buttons (predates the 1.3 renumber — this is the Design Library bind step, now 1.3) | Do not merge colors that differ by alpha. Name opaque saturated fills `--color-accent` before washes (`--color-accent-soft`). Bind with RGB **and** alpha so a solid fill cannot snap to a tint of the same hue. A re-run restores fills from capture HTML when the Paper node already has a fill. Sidecars are optional. |
| 155 | Tags Scan run twice retitled hero wrappers and buried the 1.2 tree | There is no Tags Scan step. 1.2 does not stamp pc-path trees as `layer-name`. Leave scrape / Paper names alone. |
| 156 | 1.4 marked done after bind while Paper sections no longer matched the source-section clips (washed CTAs, system-font fallback, leftover top) (predates the 1.3 renumber — bind is the Design Library step, now 1.3) | After apply, stop. Do not loop `validate-library-seed.mjs` / `apply-theme-tokens.mjs`. Color-wash, system-font fallback, or layout shift is a 1.4 human pin on the layer. Do not `write_html` PNGs into Paper. The human missing-elements walk lives in 1.4's sign-off half |
| 157 | 1.3 finished Design Library then spilled a CTA/brand fill onto quiet bands (footer, wrappers) that 1.2 left unpainted (predates the 1.3 renumber, was mislabeled 1.4) | Do not assume a frame should be filled. Capture HTML may carry an ancestor `background-color` from serializer `F()`; that is not a license to paint Paper. Restore a capture color only when the node already has a fill. Bind exact RGB + alpha only — no nearest-hue snap. A wrapper with two+ named `NN ·` sections stays unpainted. Extra saturation vs the source-section clip is `color-spill` and fails 1.3 with no retry |
| 158 | Agent freehanded Design Library via write_html after extract-library / render-library was blocked | Only `run-design-library-step.mjs` → `render-library.mjs --kind foundations` (`templates/library/foundations`). If node cannot run, STOP and say so. Never a custom colour/type catalog. `library_14_foundations_gate.py` + `qa/design-library-step.json` |

| 159 | Retired — dump era. 2.1 authors the page. Local `fonts.css` still loads woff2 on `file://`. Never tokens-before-reset. |
| 160 | No Play CDN. Local reset only. Omit Preflight’s universal border rule (`box-sizing` only on `*`). |
| 161 | 1–2 word labels inside `<a>` / `<button>` stay `<p>` and UA 1em blows the pill | Unstyled `p`/`h1` get 1em UA margin. Proven fix: labels of **1–2 words** inside `<a>` or `<button>` → `<span>`. Any paragraph with **more than 3 words** stays `<p>` across the document (article titles, dates, body). A hero h1 with full inline already overrides UA (font-size 100px). Preflight is still needed when we retag nodes that omitted margin |
| 162 | Retired — dump era. 2.0 does not join on capture ids. Do not merge split hero h1s. Paper is the brief. |
| 163 | stretch-root used align-self:stretch + max-width and killed flex-center | Site containers: width 100% + maxWidth + alignSelf center. Never align-self:stretch + max-width |
| 164 | `file://` cannot load a Google Fonts `@import`. Link local `css/fonts.css` with `@font-face` to `rebuild/fonts/*.woff2`. |
| 165 | Retired — dump era. stamp-pc-id-then-retag is not a required 2.0 path. |
| 166 | Retired — dump era. apply-semantic-tree-is-the-ship / unwrap-after-retag is not a required 2.0 path. |
| 167 | Retired — dump era. layer-ids census is not a 2.0 join key. Sidecars are optional and invisible. |
| 168 | 1.2 wrote the Framer page/hero shell onto a lander as "navbar", or captured Navigation at desktop only | 1600 / 768 / 390 are all **captured** — nothing authored (the authored-breakpoint pass is retired, 2.10.0). Serializer chrome (`00-header` / `00-nav`) parks on FRAME `Navigation` at **all three widths** (`01 · nav-1600` / `02 · nav-768` / `03 · nav-390`), each serialized with the viewport actually at that width. A missing take at any width keeps 1.2 open. Port that compact stack onto desktop only when the lander has no navbar. Never `write_html` the live page shell (Pitfall #110). |
| 169 | 1.2 marked done after desktop collect without authored `home-768` / `home-390` or screenshot QA | Author both frames from desktop, then `breakpoint-shot-qa.mjs`. `qa/breakpoint-shot-qa.json` must be `ok: true`. `mark --step 1.2 --status done` stays red until that receipt exists. |
| 170 | Retired — dump era. extract-inline-to-css as the 2.2.b spine is not live. |
| 171 | Retired — dump era. 2.2.b Grok Cleanup is not the live spine. Gated-ladders and Grok Cleanup stay historical plans. |
| 172 | Retired — dump era. Five 2.2 letters (a–e) as the build path. Live children are 2.1 / 2.3 / 2.4. |
| 173 | 2.0 joins on capture ids (pc-id / layer-ids / paper-semantic-tree) | 2.0 does not join on capture ids. 1.2 does not stamp pc-path trees as Paper `layer-name`. |
| 174 | Paper treated as a JSX / get_jsx dump to replay | Paper is the brief, not a JSX dump. 2.1 authors the page. |
| 175 | Extra Paper frames added only so a join had something to read | Do not add Paper frames that only serve a join. Keep homepage 1600 / 768 / 390, Design Library tokens, and hover/state frames if live has them. |
| 176 | 2.3 restyles the whole page or invents 1024 / 1320 to pass one band | Patch that section only vs Paper 1600 / 768 / 390. Controller applies serially. Fail reverts that section. |
| 177 | 2.4 overlay starts off, or TAGS is a hidden query | 2.4 overlay default is TAGS. |
| 178 | frontend-design from web2html invents a new identity | frontend-design from web2html keeps the fidelity lock. Aesthetic-risk OFF. Paper gold. No new palette / fonts / copy. |
| 179 | A session 2 or 3 ran `pipeline-progress.py start` and reset a run in flight | `start` force-writes empty progress and quarantines ship HTML — it is for a **new run only**. A continued session uses `resume . --at <step> --owner <session>`, which never resets. The handoff prompts emitted at 1.4 and 2.4 already say this; do not "helpfully" substitute `start`. |
| 180 | A new session could not stamp the board: "controller lease belongs to …" | The previous session ended without releasing its lease. `mark --step 1.4/2.4 --status done` releases it automatically; if a session died mid-flight, `release-controller --owner <held> --expected-revision <n>` clears it. Never edit `qa/pipeline-progress.json` by hand to force it. |
| 181 | 1.3 waited for the Capture Tool before mining the Design Library | 1.3 mines the frames 1.2 just wrote, then pulls Buttons/Components from desktop. Capture Tool is leftover 1.4 hover only. |
| 182 | Agent treated Capture Tool as a 1.4 done-gate | Buttons + Components are filled in 1.3. Capture Tool is optional leftover hover. `qa/paper-human-review.md` is the 1.4 receipt. A skip JSON is not required. |
| 183 | Compact nav left All Pages / Pricing / Sign In / Get Started in the bar and added a chevron menu | Functional 768/390 bar is logo + `[data-nav-toggle]` only. Original link/CTA groups `display: none`. Panel is a vertical list |
| 184 | 1.2 serializer stamped `layer-name="pc-<section>-<child-index-path>"` onto every imported node | Do not mutate layer names. Keep scrape / HTML names or omit and let Paper name the layer. Sidecars are optional and invisible. Never write a pc-path tree onto frames. |
| 185 | 2.3 signed `"aligned"` from a zoomed screenshot without numbers | Measure first from `rebuild/index-raw.html` (desktop dump styles) and the 1.2 source-section sidecar bbox. Census heading line-height, button radius (10 vs pill), absolute overlay cards on photos, and list-vector px. Write `qa/paper-measure/<id>.json` + `_index.json`. `section_22_gate.py` fails without `measured: true` and `diskCompared: true`. Do not re-query Paper MCP for those numbers (Pitfall #202). Pixel-perfect is optional and one-pass — skip it when the watch list is already clean. Recipe `references/section-23-paper-loop.md`. |
| 186 | Agent opened `/web2html` and narrated “skill file is huge” / paged `SKILL.md` | `SKILL.md` is the index. Read **one** per-step file from its table (`references/step-11.md`, …). Do not dump the package. Do not say it is huge. |
| 187 | 1.2 opened an existing Paper file because the name looked similar (Thrive / kp-thrive leftover) | Never `list_files` / never `open_file` a similarly-named existing file. `capture-session.mjs` `create_file`s once, then reopens **this** project's pinned `qa/paper-file.json` on retry (§#224).
| 188 | `Screenshots` board at full opacity next to `home-desktop` | The 1.2 Screenshots artboard is **50% opacity** so the review clips recede and desktop stays the hero. `sourceBoardFrameStyles` / `buildSourceBoardHtml` set `opacity: 0.5`. Do not restamp it to 1. |
| 189 | 2.1 copied live-site `<a href>` (Calendly, `/pricing`, socials, mailto) onto the authored page | The ship is a `file://` homepage, not the live site. Painted nav / CTA / social / footer stay `<a>` for look. Destinations are `#` or an in-page `#id`. `author_21_gate.py` fails on `https?://`, `mailto:`, `tel:`, and source `/paths` on `index-semantic.html`. Do not unwrap to `<span>`. |
| 190 | Human stop asked them to type a paragraph, or assumed a Hermes-only popup | Use this session’s native blocking choice/CTA tool if it has one (Hermes `clarify`, Claude `AskUserQuestion`, Cursor `AskQuestion`, Codex cards). **1.4** is a two-option modal: instruct them to add missing dropdowns/buttons/components with the Capture Tool and to pin Paper comments; choices are `Done & continue to next step` and `Provide hand-off prompt to start fresh session`. **2.4 / 3.4** stay a single `Continue`. No native tool → print those labels and wait. Timeout → stay stopped. Do not invent a harness API. |
| 191 | `resume` / a later session / a human checkpoint opened `pipeline.html` in a new browser tab | Only `start` opens the live board, once, at the beginning of the run. Assume that tab is still open. `resume` rewrites the HTML and prints the `file://` URI; it does not call `open`. Do not `open` the URI yourself on session 2 or 3. |
| 192 | Session 2 stopped after 2.1, after 2.2, or mid-2.3 and waited for the human | Session 2 is one run: 2.1 Design System → 2.2 Author → 2.3 → 2.4. 2.3 is an agent loop, not a checkpoint. Do not fire a Continue CTA except at 1.4 / 2.4 / 3.4. Sign every homepage section at 1600 / 768 / 390 before opening 2.4. |
| 193 | 1.1 downloaded every `@font-face` unicode-range subset (200+ woff2) and the agent rewrote a long fidelity contract | `scrape-web.sh` is the whole step. Parallel-download images + Latin `U+0000-00FF` only. Stub contract, no font-name-table inspection, no copy into `rebuild/` at 1.1. 1.2 `localize-html-images.mjs` reuses `source-site/assets/` and fetches remaining live images. Self-host fonts at 2.1. |
| 194 | 2.1 Design System page shipped as the homepage, or 2.2 authored without it | 2.1 emits `rebuild/design-system.html` from `library.json` (script). That page is the token contract, not the ship. 2.2 authors `rebuild/index-semantic.html` from Paper desktop using those tokens. Do not freehand the gallery. Do not skip 2.1. |
| 195 | 2.3 loaded `/pixel-perfect` as the driver and ran its refine loop on every band (hour+) | 2.3 self-validates each section vs disk gold. Measure/APPLY is serial. VALIDATE LOOK is `wave.py` (Pitfall #221). Pixel-perfect is a **one-pass assist** for layout / type / geometry / icons / radius / imagery / absolute overlays / 2.2 hallucinations. Cap 1 compare + 1 fix per section **for the assist**; VALIDATE is capped at 3 looked-at rounds per band (Pitfall #216). Workers do not write `rebuild/`. Recipe `references/section-23-paper-loop.md`. |
| 196 | 3.x polish undid 2.3/2.4 fidelity: renamed Design Library classes, changed font-size, restored gaps/icons, or hid signed paint with CSS reveal / `class="reveal"` | 2.4 freezes the ship (`qa/fidelity-freeze-24.json`). 3.1–3.3 are a11y, scrape-only SEO, contrast on existing tokens, anti-slop, hover-if-live, and mandatory GSAP on `index-polish.html` (Pitfall #1: no CSS hide, above-fold visible). No type-scale, no class replace, no visual restore. `fidelity_freeze.py verify` + `semantics_pass.py --freeze-structure`. Drift → revert, do not restyle. |
| 197 | 2.4 wrote `css/qa-overlay.css` + `js/qa-overlay.js` next to the project (sibling of `kp-*`) instead of inside `rebuild/` | `inject-qa-overlay.py .` or `rebuild/index.html` only. Assets always land in `rebuild/css` + `rebuild/js`. A cwd of `Documents/templates` must not grow a sibling `css/` / `js/`. `verify-rebuild-trees.py` fails on leaked overlay files. |
| 198 | 2.2 shipped `index.html` instead of `index-semantic.html`, or 2.3 skipped / signed without `index-raw.html` | Three files: `rebuild/index-raw.html` = Paper `get_jsx` of home-desktop (reference). `rebuild/index-semantic.html` = 2.2 first authored pass. `rebuild/index.html` = 2.3 working copy / 2.4 lock, seeded from the first pass. 2.3 never skips; compare index-raw + 1.2 source clips, patch index.html. `author_21_gate.py` fails without the semantic + raw files. `section_22_gate.py` fails without the raw file. Pitfall #206. |
| 199 | 2.2 wrote Paper `get_jsx` JSON (`style={{}}` + 69 self-closing `<div />`) as `index-raw.html` | A browser treats those divs as unclosed tags → blank page. Save the MCP JSON to `qa/index-raw.jsx.json`, then `dump_index_raw.py . --from qa/index-raw.jsx.json`. Converter expands non-void self-closing tags and links `css/tokens.css` + `css/fonts.css`. JSON / JSX leftovers fail `author_21_gate.py`. Design System chrome is `var(--color-*)`, not `#1A1A1A`. |
| 200 | `index-raw.html` linked `tokens.css` but type fell back to system-ui | `tokens.css` only names `--font-sans-*`. `emit_fonts.py` writes `@font-face` in `css/fonts.css` pointing at `rebuild/fonts/*.woff2`. Dump + Design System must link `fonts.css`. Pitfall #164. |
| 201 | 2.3 signed aligned without reading `index-raw.html`, so dump SVG/icon fills never landed on the ship | Controller runs `raw_23_census.py` first. Workers set `rawCompared: true` and port missing `background-image` SVG assets / inline `<svg>` from the dump. Do not invent Lucide icons. Gate fails without the census. |
| 202 | 2.3 spawned one Paper-bound worker per section; desktop MCP timed out and the batch never returned | Gold is already on disk: 1.2 `capture/home-{desktop,768,390}/source-sections/NN-slug.png` (same number at every breakpoint) plus `rebuild/index-raw.html`. Run `paper_23_disk_gold.py` then `paper_23_clip_compare.py` so those numbered clips land in `qa/paper-measure/compare/` as source / rebuild / side-by-side. Read those PNGs. Do not compare against 1.1 `source-site/screenshots/` (that is 3.x). Measure is serial. VALIDATE LOOK is `wave.py` (Pitfall #221). No Paper MCP. Recipe `references/section-23-paper-loop.md`. |
| 203 | 3.x polished `rebuild/index.html` in place, so 3.4 had no 2.4 baseline to compare | 3.1 active seeds `rebuild/index-polish.html` from the lock. Do not seed that file at 2.4 — an unpolished copy on disk reads as polish already done. 3.1–3.3 write only that file. `fidelity_freeze.py` hashes `index.html`. `open-human-review.py` opens both plus the polish report. Mutating the lock fails. |
| 204 | 3.2 / Emil skipped `inject-gsap-reveal.py` because 1.4 did not record in-view motion | Retired. Every run injects GSAP on `rebuild/index-polish.html`. `verify-gsap-reveal.py` is a hard gate (`qa/gsap-reveal-qa.json` `"ok": true`). `start: "top 75%"` — parent group past 25% of the viewport from the bottom, then stagger first children + siblings 80ms (not heading leaves). A 1.4 archive is not a skip. Pitfall #1 still forbids CSS hide / `class="reveal"`. Recipe `references/gsap-inview.md`. |
| 205 | 1.3 marked done after Design Library without filling FRAME Buttons / Components | After seed QA, walk every `NN ·` section on token-seeded `home-desktop`, write `qa/buttons-components-plan.json` (each row has `sectionId` = that section), run `pull-desktop-specimens.mjs` (it also runs `author-button-hover.mjs`). Parked cards keep the review layout: red badge is the source section `NN`, not dump order. Receipts `qa/buttons-components-pull.json` and `qa/button-hover.json` are required. Capture Tool is not this step. Recipe `references/13-buttons-components.md`. |
| 206 | 2.2 wrote `rebuild/index.html` as the first pass, so 2.3 had no authored baseline | 2.2 writes `rebuild/index-semantic.html` only. `seed_index.py` copies it to `index.html` (2.2 done and 2.3 active). 2.3 patches the copy. Do not mutate `index-semantic.html` after 2.2. `author_21_gate.py` requires the semantic file. |
| 207 | 3.2 skipped button hover because Capture Tool did not run (`0 applied / 4 skipped`) | 1.3 authors hover from source CSS on the pulled Buttons (`author-button-hover.mjs`, `qa/button-hover.json`). 3.2 **must** run `apply-hover-css.py .` so `rebuild/css/hover.css` is linked from `index-polish.html` (`qa/button-hover-css.json`). Empty `applied` is valid only when 1.3 found no `:hover` paint. Do not invent UA-blue `a:hover`. Recipe `references/hover-22c.md`. |
| 208 | 3.2 / Emil skipped `burger open drawer` because Capture Tool had no open-nav pair | Capture Tool is leftover. If the polish file paints a hamburger, **author the open sheet** from the same desktop links stacked (`author-nav-drawer.py`, `qa/nav-drawer.json`). That is not new chrome. Do not invent a burger that was never painted. Recipe `references/nav-drawer.md`. |
| 209 | 3.2 / Taste skipped FAQ because Paper signed empty bodies / Capture Tool did not run | If FAQ rows are painted, **wire the accordion** (`author-faq.py`, `qa/faq.json`) and fill empty answers from `source-site/index.html`. Scrape copy is not invented copy. Still wire the toggle when scrape has no match. Do not invent a FAQ section. Do not clone one answer onto every row. Recipe `references/faq.md`. |
| 210 | 3.2 skipped nav dropdown because Capture Tool / `--allow-dropdown` / “do not hunt” | If polish paints a trigger or a nav label matches a scrape submenu, **wire hover/click** (`author-nav-dropdown.py`, `qa/nav-dropdown.json`). Capture Tool is leftover. Do not invent a nav label. Recipe `references/nav-dropdown.md`. |
| 214 | 1.2 Navigation wrote only `nav-1600` because 768/390 chrome lookup required `Top Bar` or visible Services/Contact links | Framer compact bars are named `Header` / `Tablet` / `Phone` / `Mobile` (logo + hamburger). `findChromeBarsInPage` must pick the first compact named bar, then burger/logo climb. Hidden nav links are not a miss. Re-serialize `00-header.html` at that width and re-park FRAME Navigation (three takes). |
| 212 | 1.3 parked Buttons / Components overflowed their review wrappers because height used Fill instead of Fit | Set the parked specimen root and its content-hugging slot / review wrapper to Paper **Fit** height (`height: fit-content`), not Fill / `height: 100%` or vertical flex growth inherited from the source section. Preserve intentional fixed-size internals and source paint; change only the parked copy, never `home-desktop`. After placement (including hover copies), read back sizing and inspect the frame screenshot: the wrapper must enclose the full specimen without clipping or overlapping the next row. Do not hide the defect with `overflow: hidden` or arbitrary extra height. Recipe `references/13-buttons-components.md`. |
| 213 | 1.3 Navigation overlapped Components as the specimen board grew | After the Buttons / Components pull and hover pass, move the existing FRAME `Navigation` to the left of `Design Library`, top-aligned with a 100px gap. Use current canvas bounds, not guessed coordinates; if occupied, move farther left until clear of every other frame. Preserve all three navbar captures and their internal geometry. Read back bounds and inspect the canvas before finishing 1.3. Recipe `references/13-buttons-components.md`. |
| 215 | 3.2 companion findings vanished: `web-design-guidelines` / `find-animation-opportunities` / `apple-design` ran with no receipt, `record-polish-pass.py` refused their names, and the Emil receipt rendered on a card titled “Semantics and SEO” | C/3 receipt ids are sub-pass ids, not board steps (C/3.1 impeccable + C/3.2 taste = board 3.1; C/3.3 emil = board 3.2). Emil's card is hover + drawer + FAQ + dropdowns + GSAP; semantics has its own 3.3 card. Each companion writes `qa/<skill>.md` with `applied` / `skipped` / `n-a` rows — a lock (Pitfall #81 #152 #196 #203) makes a skipped row, never a missing row. `verify-polish-passes.py` and `mark --step 3.2 --status done` fail without all three files. Guidelines audit `index-polish.html`, never the 2.4 lock. Emil skips its greeting under pipeline 3.2. |
| 216 | 2.3 signed `aligned` after one compare; stacked columns, wrong band order, and dropped overlays surfaced at 2.4 and were fixed by hand from screenshots, one section at a time | After APPLY, VALIDATE: `--shoot-open`, then **MUST** `wave.py prepare/start/wait/apply` for LOOK, then apply printed patches and `--record` from the findings until every width is `match` or round 3, then `--residual`. Controller shoots/applies/records. LOOK is the wave (Pitfall #221). No Paper MCP, no pixel-perfect inside VALIDATE. `section_22_gate.py` fails a band without `qa/paper-measure/<id>.validate.json`, with an empty `seen`, an open last round, more than 3 rounds, a residual before round 3, a missing applied 2.3 wave, or a ship (`rebuild/index.html` + `rebuild/css`, minus the QA overlay and 3.x sheets) that changed after the last round was shot. Recipe `references/section-23-paper-loop.md`. |
| 217 | Capture Tool side panel showed **OFFLINE** on a fresh install, and 1.4 never opened the browser on the stamped source URL | Offline = `connectNative` failed. Causes seen: `install-skills.sh` never installed the native host; `install-native-host.command` died from Finder because node is not on Finder's bare PATH; the launcher pinned a node symlink that later moved; the manifest was written for Chrome only while the extension was loaded in Brave; the installed `host.mjs` lagged the repo; test runs clobbered the global `active-session.json` with a tmp path; `qa/paper-file.json` `url` still pointed at `app.paper.design`. Fix: `install-skills.sh` runs the installer (`--quiet`), which finds node off-PATH, pins the resolved binary, writes a manifest per Chromium browser, and PINGs the host. `mark 1.4 active` runs `capture-doctor` and **opens the browser on the stamped URL** (non-fatal, URL always printed). `write_capture_tool_session` skips the global file for temp roots. `paper_source_url` prefers `sourceUrl` over a Paper-app `url`. |
| 218 | Session 2 ran out of context mid-2.3 and either stopped to ask the human or got auto-compacted with an unshot patch on disk (two `kp-*` runs sat stale-active for 70 and 755 minutes) | A **relay** is a change of agent, never a yield. `context_budget.py` prints the budget on every `mark`; at the arm threshold (50 %) finish the current unit (record the band, write the receipt) and run `pipeline-progress.py relay <project> --owner <held>`. It writes `qa/handoff-<step>.relayN.md`, releases the lease, and on a reachable Orca opens a terminal for the **same agent** and sends the prompt; else it prints the block. Never a CTA, never a question. It refuses with a shot-but-unrecorded round or a wave with running workers (`--force`). If the terminal never accepts the prompt, the lease comes back and you continue in place. Successor: `resume <project> --at <step> --owner session-2b`. Recipe `references/orca-relay.md`. |
| 219 | The run stopped, asked, or failed because `orca` was missing, the runtime was unreachable, `worker-start` exited non-zero, or the harness was not Claude Code | Orca is an accelerator, never a dependency. `harness_probe.py` always exits 0 and only picks the rung: `waves orca → subagent → serial`, `relay orca-terminal → print-prompt`. Every rung keeps the same lease, gates, receipts, and human stops. 2.3 still runs `wave.py` on `serial` / `subagent` (Pitfall #221). A failed `worker-start` is never relaunched — the remaining tasks drop a rung. Do not load `orchestration` / `orca-cli` unless the probe says `orca reachable`. |
| 220 | An Orca wave or relay launched `--agent claude` (or any hardcoded agent) under a Codex / other orchestrator, so the run changed LLM source mid-flight | Same-source rule. The Orca agent id is Orca's own `terminal show` → `agentIdentity` for the coordinator's terminal, else the harness marker, else `WEB2HTML_ORCA_AGENT`. Unknown → Orca rungs are off. `wave.py` and `relay` pass exactly that `--agent` / launch command and never `--model` (the tier stays advice; `WEB2HTML_WAVE_MODEL` is the operator's explicit override). Workers are read-only reviewers in the `agent_loop.py` lane: SHA snapshot, one lease and one finding file per task; the controller shoots, applies, and records. |
| 221 | 2.3 VALIDATE walked LOOK in the controller session (shoot → Read three sides → patch CSS → next band) even though the probe said `waves orca`; no Orca terminals appeared and `qa/agent-findings/` was never written | VALIDATE LOOK **MUST** run `wave.py` after `--shoot-open`. Adapter from the probe: `orca` → `run-create` + `worker-start` (new terminals of the same agent, up to 4); `subagent` → this harness's subagent tool; `serial` → controller does each printed spec and writes the same finding file. Do not load `/orchestration` unless `orca reachable`; do not substitute this harness's subagent tool for Orca `worker-start` when the adapter is `orca`. `section_22_gate.py` fails without an applied `qa/agent-runs/<run>/2.3/wave.json` covering every band. Recipe `references/orca-relay.md` + `references/section-23-paper-loop.md`. |
| 222 | 1.3 parked desktop Buttons / Components on a white review card, so transparent specimens and white type disappeared | The review row stage is neutral grey `#6F6F6F`. The specimen title is `#F2F2F2`. Leave the duplicated desktop node's own paint alone — the grey is the card behind it, not a fill on the specimen. `parkDesktopNodeOnBoard` stamps that grey on every row, including a duplicate of an older white template. Recipe `references/13-buttons-components.md`. |
| 223 | A Vercel / GitHub deploy of `rebuild/` served `index-raw.html`, `index-semantic.html`, `index.html` (2.4 lock), and `index-polish.html` as sibling entry points, and the demo URL painted QA outlines | 3.1–3.3 still write only `index-polish.html`. The 3.4 review compares both files with outlines off (`?qa-outlines=tags` turns them on). **Marking 3.4 done** runs `promote_ship.py`: polish becomes `rebuild/index.html`, the other homepage HTML moves to `rebuild/archive/`, `data-qa-ship="final"` keeps outlines off unless the query param is set, and `rebuild/.vercelignore` lists `archive` so a rebuild-rooted deploy does not upload the old files. Do not delete the archive. Do not promote before the human has compared. Phase 5 reads `index.html` once polish is gone. |
| 224 | 1.2 created two Paper files: the first `create_file` succeeded, then capture died (missing `playwright-core`), and the retry called `create_file` again | Probe `playwright-core` before any Paper document. A retry reopens the `fileId` in this project's `qa/paper-file.json` (`generatedFrom: url-to-paper/create-paper-file`). Never `list_files`. Never open a similarly-named file from another project (Pitfall #187). `--new-file` is the only way to start a second document. `start` clears a leftover receipt so a new run still gets one new file. |
| 225 | A Webflow / HTML folder run asked "finish homepage or continue to optional Phase 4", and the intake choice had no place to paste the folder path | Folder / Webflow (`clean-html` adopt) does not ask at 3.4. `mark 3.4 done` writes `qa/phase-4-opted.json` and the run continues through 4.4. `qa/phase-4-skipped.json` and `skip` on 4.x fail. Phase 5 stays optional at 4.4. Intake question 1 is `Live URL — author from Paper` or `Webflow / HTML source`. Choice 2 is followed by a question whose answer is the absolute folder path, typed in the text field, before full or fast. | |
| 226 | Paper sized a CSS background photo to the element's layout box, so the bitmap came out cropped or stretched. The Fill panel showed the file (2560×1432, 1000×667) while the frame stayed the CSS box (1600×716, 1600×400). Short `background-size: cover` banners do this on a lot of captured sites | Reset the image frame to the file's intrinsic pixels, then scale it uniformly until the width matches the parent. Height follows the file ratio (`width × fileHeight / fileWidth`). `scaledImageDimensions` in `1.2 url-to-paper/scripts/paper-image-geometry.mjs` is that math; source shots already call it. Apply the same reset to bitmap `background-image` fills before the lander is signed. Leave gradients and SVG icons on their own boxes. |

For any item: correct the smallest root cause, rerun its gate, and save fresh proof.
