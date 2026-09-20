# Install paths, layout, conventions, glossary

Split out of `AGENTS.md`. Read when installing, adding a skill, or unsure of a term.

### Installed names are never numbered

This repo's folders carry a stage prefix (`1.2 url-to-paper`) so the pipeline
order is visible when browsing. **That prefix exists only here.** Installed
packages keep plain names — the directory name *is* the skill identifier agents
invoke, and a space or digit in it breaks discovery and every symlink.
`scripts/install-skills.sh` strips the prefix for you; add new skills by
dropping a package folder in, not by renaming installed directories.

## Agent install paths

Nothing in these packages depends on where the checkout lives. Install by
symlinking each package into the skills directory your agent reads:

```bash
./scripts/install-skills.sh                  # -> ~/.claude/skills
./scripts/install-skills.sh ~/.hermes/skills # -> any other skills directory
export SKILLS=~/.claude/skills               # what $SKILLS means in every skill
```

| Agent | Skills directory |
|---|---|
| **Claude Code** | `~/.claude/skills/*` |
| **Hermes** | `~/.hermes/skills/*` |
| **OpenCode** | (runtime + `~/AGENTS.md`) |

The installer strips the stage prefix, so `1.2 url-to-paper/` installs as
`url-to-paper` and `web2html/` installs as `/web2html` (compat alias `website-to-html`).
Symlinks, never copies: an edit in the
checkout is live immediately.

`$SKILLS` appears throughout the skills and means exactly that directory. Scripts
that call a sibling package resolve it from their own location first, so they run
with no environment set at all.

## Layout

- Full packages: `web2html/` (scripts + refs)
  - **2.0 author + section gates:** `scripts/design_system_21_gate.py`, `scripts/author_21_gate.py` and `scripts/section_22_gate.py`. Paper is the brief, not a JSX dump. No get_jsx, no pc-id join. 2.1 emits the Design System page; 2.2 authors `index-semantic.html`; 2.3 seeds `index.html` and signs each homepage section at 1600 / 768 / 390; 2.4 overlay default is TAGS. `scripts/paper_layer_names.py` remains a 3.3 helper. Dump-era converters are retired from the live recipe. Gated-ladders and Grok Cleanup stay historical plans.
  - **Stage spine (tight context):** `references/stage-spine.md`
  - **Prior-run gotchas:** homepage-only + required 1600 / 768 / 390 (Pitfall #22); lock QA before semantic tags (Pitfall #61); hover from the painted pill (Pitfall #33); invent hover CSS only when Paper default and hover are identical (Pitfall #152)
- **url-to-paper** `1.2.86`: **pre-pesticide** live inventory before capture (`pre-pesticide.mjs`, `x-paper-prepesticide` HUD, `pre-pesticide.json`, Pitfall #70); **per-section SOURCE shots** at 1600 / 768 / 390 on disk (`source-sections/01-slug.png`; Paper `Screenshots` stays 1600 at 50% opacity, A/6 badge, never a full-page source shot, Pitfall #71 / #188; clipped at `scale: "css"` and every `Screenshots` row capped at 1600 so the board matches `home-desktop`, no title row, Pitfall #119); **P-0 creates one ruler only** (`draw-rulers.mjs --init`; `Design Library` does not exist before 1.3); Stage P capture + Paper import; **`fullpage.png` on disk required**; Paper `{page} — source screenshot` is **opt-in** (`--screenshots-only`); `qa-paper` default depth 4 flags `clip-content` / `clipped-section` plus `frozen-root` and **`split-heading`** (Pitfall #69; repair `merge-split-headings.mjs`); after insert, named sections hug `height: min-content` (Pitfall #67); `empty-image` also flags `deferred-image` and circular `SVG`/`file` overlays (Pitfall #68 — visual vs live; never `paper-asset://` in `write_html`); **icon box metrics** (size, container, gap) from the live inventory at that width — do not copy `flex-wrap` / `round(46%)` / 2+1 from 768 onto 1600/1440 (Pitfall #75); overlay `hide()`/`show()` for section JPEGs; 768 / 390 are **captured** through the same path as desktop — nothing authored (Pitfall #168) — and FRAME `Navigation` is captured at all three widths (`01 · nav-1600` / `02 · nav-768` / `03 · nav-390`); arrange capture frames in one row, then 1.3 creates `Design Library` once and it heads the row; a live **fixed** nav is the last lander child at `x: 0` / `y: 0` (Pitfall #97); **A/5-R** `stretch-root.mjs --prove`; Linux capture via `PW_CHROME`; **1.3 / Stage L** runs `run-design-library-step.mjs` straight after the 1.2 capture (never waiting on the optional 1.4 extension) to inventory and mine all eligible frames once, create the foundations sheet once, replace tokens canonically, bind exact matches only, keep opaque vs alpha fills distinct (Pitfall #154), restore collapsed fills from capture HTML on a re-run only when Paper already has a fill, never invent paint on an unpainted 1.2 frame (Pitfall #157), and prove unchanged geometry with `token-geometry-guard.mjs` (Pitfall #108); then pair each 1600 / 768 / 390 `source-sections/NN-*.png` with the matching lander band and rebind up to 3 times on color / font / layout drift (`validate-library-seed.mjs`, Pitfall #156). Extra saturation vs a quiet source clip fails 1.3 with no retry. Every foundations render also upserts all Paper-supported tokens before painting; semantic colour bars are 15px and mined brand swatches remain 104px. Tailwind default type-size / spacing / radius / elevation remain (Pitfall #64); type sheet always shows `--text-7xl`…`9xl` as **DISPLAY** (Pitfall #66). Do not add `--text-display` 160 / `--text-display-xl` 192. **Token-pass** (`apply-theme-tokens.mjs` / `token-pass-targets.mjs`) walks `{page}-(desktop|768|390)` landers (not only `home-*`) + Design Library + A/6 **and** FRAME `Interactive components`. **1.3 token-pass is a census** — every node in `qa/token-pass-qa.json`, fail on any miss (Pitfall #76).
- Component states: `1.3 hover-reel/` **1.1.106** — **1.3 fills FRAME `Buttons` and FRAME `Components` from token-seeded `home-desktop`** (`pull-desktop-specimens.mjs`, then `author-button-hover.mjs` from source CSS, Pitfall #205 #207). Capture Tool is leftover 1.4 live hover (`pipeline-progress.py open-capture`). Package `capture-extension/` with `npm run package:extension`, install the native host, load unpacked. After **1.2** landers + geometry postflight, one session runs Navbar + Dropdowns → Hover → Multi-state → Single → Tags. Reopen the side panel to resume when Paper already exists. Reject page / `Desktop` / `#main` shells (never serialize the lander). **Continue** parks Navbar on FRAME `Navigation`, then `parkNavbarOnLanders` stamps a **compact** overlay last on `home-desktop` (links) and `home-768` / `home-390` (hamburger) at `0,0` — do not `write_html` the live Framer header onto landers (Pitfall #110). No second Chrome (Pitfall #107). FRAME `Navigation` writes the Navbar row on first park (then duplicates that structure for extra dropdowns). Sending stays up until lander + Navigation writes finish. List **Navbar** last as captured. Hide every `x-paper-*` overlay before source clips (Pitfall #104 / #105). **1.4 leftover Capture Tool** writes `human-hover-done.json` only if it ran. Paper numbers **01 = hero**; navbars are never sections. Send to Paper after 768/390; Design Library remains absent until 1.3. Extension modes are Nav / Hover / **Multi-state Component** / **Single Components** / Tags. Single Components is `R` → click any exact element, accepts every element type, and parks on FRAME `Components`; Multi-state Component takes also park there. Panel **Tags** locks the tab to 1600 / zoom 100%, attaches outlines to the live elements, and names `home-desktop` from the 1.2 pc-id tree (Pitfall #150); writes `qa/source-semantics.md` + `-map.json`. **AI ✦** walks sections in that Chrome and skips product / blog loops (Pitfall #106). Page `<a href>`s stay on this URL. Paper review sequence first (`01` = hero); the panel walks `review-sequence.json`. Agent listens on disk — do not paste JSON. Unwrap `fe()` `{status, html}` (Pitfall #100). `--auto` only for CI. — 4.2 buttons **and footer text links** park on `Source · {page}` (one `section-number` + `list` of `object`s). `button` is the painted CTA — no unnamed Frame, no 24px Slot. Footer/nav `text-link` **color** change is a visible Hover; buttons still require paint. Never `position: absolute` button fills. Nav/forms stay on A/6. — `prepareStateHtml` flattens abs stroke/gradient overlays and stacked text-swap labels (Pitfall #56). page-aware `capture-site-component-states.mjs` → `<page>/<kind>/`, `capture-component-states.mjs`, `build-paper-states.mjs`, `validate-component-captures.mjs`, `component-state-utils.mjs`, `capture-menu-states.mjs`, `dropdown-capture.mjs`, `write-dropdown-pair.mjs`, `hamburger-capture.mjs`, `capture-hamburger-states.mjs`, `visible-cursor.mjs`, `trim-styles.mjs` (`npm i` once for Playwright). **Visible Chrome by default** (Stage P `launchOptions`); `--headless` is CI-only. Settle with reduced-motion, then turn it off so live `whileHover` fires; pin the live hover fill (Pitfall #30). **C/3 implements from the hover HTML painted `<a>`, not `styleDelta[0]` or UA `rgb(0,0,238)` (Pitfall #33).** **Desktop section names** (`01 · slug`) label the layer and A/6 rows — no legend artboard (Pitfall #41); repeating lists capture one representative (Pitfall #34). Nav/footer are **element** link pairs, not container bars. Buttons walk Stage P sections (same label in two sections = two components). **Do not hunt accordions**; new patterns get unique names (Pitfall #57). **FAQ / accordion cards are fluid** in the `A/6 · {page} · states` parent (`width: 100%` / `max-width: 100%` / `height: fit-content`) — never the captured rect px. Accordion cards/Slots/inners are `flex-start` (not center); do not pin `heightAfter` on the collapsed root; strip icon `translate`/`rotate`. `--allow-faq` still required. **Dropdowns** (`--allow-dropdown`, alias `navbar-dropdown`) write closed \| open onto FRAME `Interactive components` at **1600** (not A/6, not 1440). **4.1-M burgers** (`02 · nav-mobile-768`, `03 · nav-mobile-390`) share that frame — not A/6, not a second board. FAQ stays on A/6. Do not hunt. Do not invent a desktop burger. Fluid width / flex-start / fit-content + red badge. **generate → token-pass** (`apply-theme-tokens.mjs` walks this board with landers + A/6). Catch-at-write binds `var(--token)` on A/6 / Interactive components, then the 1.3 coverage gate (Pitfall #76). Pitfalls #73 #74. Slots `height: fit-content` + post-write QA refit. Off-canvas carousel clones are excluded; confirmed `changed: false` states remain valid parity evidence. `--expected-pages` scopes the validator. Transparent light-text roots get `ancestorBackground` on the Slot and imported root. The GIF recorder and the Playwright HUD are **deleted** (Pitfall #121)
- **1.2 geometry postflight:** after desktop lands, `run-geometry-postflight.mjs` runs `stretch-root.mjs --prove --artboard home-desktop`. Evidence: `qa/stretch-root-evidence.md` + `qa/breakpoint-shot-qa.json`. A red QA blocks 1.3.
- **Capture Tool boundary:** **1.2** is `hover-reel/scripts/capture-session.mjs`, **headless** — desktop assemble + 768/390 shots + serializer chrome + screenshot QA + postflight, no window and no in-page HUD (Pitfall #121). The collect seeds FRAME `Buttons` + `Components` + `Navigation`. **1.3** mines the Design Library then pulls unique buttons/cards from desktop onto those frames. **1.4** is the human Paper checkpoint (`mark --step 1.4 --status active` opens Paper). Capture Tool is leftover live hover via `open-capture`. Semantic tags are the 1.2 layer-ids census, not a Tags Scan.
- Tokens: `2.1 design-tokens/` (installed name `design-tokens`)
- Spacing: Tailwind / theme tokens (`var(--spacing-*)`) from 1.3 / `design-tokens`. `3.1 instatic-html-prep` and `3.2 client-first-spacing` are retired from the live build.
- Parked CMS/video trees have left this repo.

## Sync

```bash
./scripts/sync-from-agents.sh      # agents → this repo
./scripts/check-skill-artifacts.sh # claimed scripts must exist
# Then: update only the matching surface (AGENTS.md / pipeline.html /
# workflow.html / index.html) if that surface's role changed. Never README.
```

## Repo layout

Agents load these packages from wherever `./scripts/install-skills.sh` linked
them; the checkout itself can sit anywhere.

Folders carry a stage-number prefix so the pipeline order is readable at a
glance. That prefix exists **only here**: installed directories keep plain names
because the installed name *is* the identifier agents invoke (`/web2html`),
and a space or digit in it breaks discovery and every symlink.

```
web2html/                         # local checkout; GitHub remote may still be kinw3b/flow-skills
├── AGENTS.md                     # this file — install paths, gates, glossary
├── pipeline.html                 # run order
├── index.html                    # the visual workflow map / public lander
├── scripts/                      # install, sync, artifact check
│
├── web2html/                     # Orchestrator — any site → Paper → semantic HTML
├── 1.2 url-to-paper/             # Stage P: live URL -> Paper + design-library/
├── 1.3 hover-reel/               # Steps 4.0-4.4: component default+hover states -> Paper
├── 2.1 design-tokens/            # -> rebuild/css/tokens.css
├── 4.1 pixel-perfect/            # 2.3 one-pass assist vs Paper
├── 4.2 impeccable/               # Polish (3.1)
├── 4.3 design-taste-frontend/    # Polish (3.1)
├── 4.4 emil-design-eng/          # Motion craft (3.2)
├── 4.5 find-animation-opportunities/  # 3.2 discover
└── 4.6 apple-design/             # 3.2 motion principles
```

**Coverage:** any site → Paper → semantic static HTML, design tokens, pixel-perfect
and polish. Parked CMS/video trees have left this repo.
Private repository; all rights reserved.

---

## Conventions

### Skill package shape

Executable skills start with YAML frontmatter — `name`, `description`,
`version`, `author`, `license`, `platforms`, and `metadata.hermes` carrying
`tags` and `related_skills`. Not every skill uses every optional field.
`description` is the behaviour/trigger field; some carry an explicit `TRIGGER`
clause.

The body normally runs purpose -> triggers -> inputs -> workflow phases ->
outputs -> safety boundaries -> integration notes. Exact headings vary.

Support directories: `scripts/` (executables), `references/` (playbooks, maps,
postmortems), `templates/`. A bundle-level `README.md` is optional and describes
that bundle only — it is not a second pipeline doc.

### Adding a new skill

```text
[ ] Create the package folder + SKILL.md in this repo
[ ] Accurate frontmatter with explicit triggers
[ ] Document inputs, outputs, phases, scripts, references, related skills
[ ] No absolute paths — use $SKILLS, or resolve from the script's own location
[ ] Add it to the Repo layout tree above
[ ] Add a branch/step in index.html using the existing visual system
[ ] ./scripts/sync-from-agents.sh && ./scripts/check-skill-artifacts.sh
```

Never silently duplicate or rename an existing pipeline artifact.

### The map's HTML/CSS system

`index.html` is one standalone document: a single inline `<style>`
block, no external stylesheet, one `.page` body wrapper.

- Tokens: `--bg`, `--surface`, `--ink`, `--text`, `--muted`, `--line`,
  `--line-strong`, `--accent`, status colours (`--req`, `--imp`, `--opt`,
  `--skip`), `--mono`, `--sans`, `--r`, `--ease-out`, `--t`.
- Light mode is default; `@media (prefers-color-scheme: dark)` overrides it.
- `@media (prefers-reduced-motion: reduce)` disables entrance animation,
  transitions, and hover scaling.
- Navigation: `.nav-shell`, `.nav`, `.nav-pills`, `.nav-pill` (+ `--orchestrator`,
  `--hub`, `--dep`, `--ship`), `.nav-pill__dot`, `.nav-divider`, `.nav-legend`.
- Content: `.top`, `.kicker`, `.lead`, `.priority`, `.sec`, `.phase`, `.step`,
  `.dot`, `.rail`, `.callout`, `.hint`, `.io`, `.need`, `.out`, `.chip`,
  `.pill`, `.skill-list`, `.skill-row`.
- Step cards use numbered circular markers; gates and loops take the accent
  treatment; skipped steps use dashed markers and struck-through headings.

---

## Glossary

- **Instatic** — the CMS the import pipeline targets.
- **Super Import** — Instatic's static HTML/CSS/JS import flow.
- **Core Framework** — Instatic's token, utility, visual-component and
  layout-section system.
- **Data -> Import site** — the required Instatic UI surface for Super Import;
  distinct from dashboard Core Framework Import.
- **dembrandt** — the computed-style extraction tool used by
  `design-tokens`.
- **W3C design tokens** — the machine-readable token format emitted as
  `tokens.json`.
- **`rebuild/`** — default clean ship folder produced by `website-to-html`.
- **Sole `:root`** — the contract that every global design variable lives in one
  `:root`, in `rebuild/css/tokens.css`.
- **`data-component` / `data-prop` / `data-slot`** — mark a reusable visual
  component, an editable property/content zone, and a rich-content slot.
- **`DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`** — design-taste
  dials: symmetry -> artful asymmetry, static -> cinematic, gallery air ->
  cockpit density.
- **Pixel-perfect acceptance contract** — the pre-implementation agreement on
  what must match and which issue states are allowed.
- **Source-mined tokens** — CSS variables, inline styles and rules read from the
  SSR source. **Computed extraction** — runtime values from the rendered page,
  used for role inference and gap filling.
- **A/B/C tracker** — the orchestration hierarchy: A = evidence and capture,
  B = build from Paper, C = verify and handoff. Children use `A/1`, `B/2`,
  etc. **B/2b get_jsx is deleted.** Live B/2 is 2.1 Design System / 2.2
  author / 2.3 validate / 2.4 TAGS. Technical stage names remain in
  parentheses for commands and files.
- **Steps 4.0-4.4** — `hover-reel` component capture, after Stage P has pulled
  every page/section and **before the Paper build**: 4.0 skip floating chrome ·
  4.1 navbar · 4.2 buttons/CTAs/icon links · 4.3 form fields (`--kind forms`)
  · 4.4 footer links. Do not hunt accordions.
  Produces `source-site/components/<page>/<kind>/` and one Paper artboard per
  step/page. **No GIFs** — default/hover state pairs. A/7 validates coverage
  and Paper geometry; C/3 implements the states.
- **Paper source-shot (opt-in)** — only if a person asks for a sibling JPEG in Paper. Pin explicit px geometry. Default is disk `fullpage.png` only.
- **Responsive Paper geometry** — folded into **2.1 (born responsive)** and
  the **2.3** section loop. Not a B/2b-R / 2.2.d letter. Gold is Paper
  `home-desktop` / `home-768` / `home-390`. Named sections and full-bleed
  layers use `width: 100%`; inner containers keep measured `max-width`.
  A `!important` 100% CSS hack is not this gate. Evidence:
  `qa/section-align-22.json`.
- **Homepage-only / lander** — A/1 path when the user asks for the landing
  page / home only: one route (`/`) plus required viewports. Does not expand
  to five pages. 390 remains a Stage P capture when classified `web-responsive`.
- **Stop-at-every-level** — user-requested pause after A/1, A/2, A/4, B/1,
  B/2a, B/2 (2.1 / 2.3 / 2.4), B/3, C/1. Each stop writes
  `qa/runs/<run-id>/STOP-<stage>.md`.
- **A/7 component QA** — two read-only reviewer lenses (manifest coverage and
  Paper geometry) may run in parallel; one foreground writer performs fixes and
  reimports. This is separate from C/1–C/2 Step 7, which remains one agent and
  two visual passes.
- **Step 7** — per-section visual QA: one vision-capable agent, two passes,
  every section of every page.
- **Step 8** — **8a hover parity first** (1.3 `qa/button-hover.json` via 3.2 `apply-hover-css.py` on `library.json` names; leftover Capture Tool manifests may refine the same names, not `styleDelta[0]`; section-scope
  same-label CTAs; write `rebuild/css/hover.css` →
  `qa/button-hover-css.json`), then polish C/3.1 impeccable → C/3.2 design-taste →
  C/3.3 emil with `qa/polish-passes/` receipts and `verify-polish-passes.py`, in that order.
- **Step 9** — rebuild documentation and component/design-system handoff.
- **CMS** — parked in `archive/`. Not part of website-to-html.
