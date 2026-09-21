> **Dump-era get_jsx / 2.2.a–e content in this file is retired.** Live 2.0
> is 2.1 Design System page → 2.2 Author from Paper → 2.3 → 2.4 TAGS. Do not
> teach a JSX dump, pc-id join, or the Design System page as the ship.

# Paper is the 2.2 brief. The Design System is the 2.1 contract.

The old 2.0 treated Paper as a JSX dump to replay. The new 2.0 treats Paper
as a visual brief and the 1.3 Design Library as a token contract. 2.1 emits
that contract as HTML+CSS. 4.8 frontend-design then writes one semantic
homepage from Paper desktop using those tokens. 2.3 checks it against the
three homepage artboards.

**2.1 Design System.** Script, not the model. Input: signed 1.3
`design-library/library.json` + Paper Design Library. Emit
`rebuild/css/tokens.css` and `rebuild/design-system.html` (foundations
sheet). Chrome paints `var(--color-*)` from those tokens, not `#1A1A1A`.
`emit_fonts.py` writes `rebuild/css/fonts.css` (`@font-face` → local woff2).
**Preserve face identity:** 1.1 records font style; 2.1 keeps family + weight +
style + source bytes distinct in filenames, CSS, and `qa/fonts-21.json`.
Legacy tables recover style from the exact saved source `@font-face`; unknown
hashed styles or missing exact files stop emission rather than guessing.
Never infer a variable `100 900` range from one static file. The 2.1 gate
checks emitted descriptors and file hashes against the saved source, not
just whether fonts.css exists. `verify-fonts.py` runs the same check.

**Diagnose slant before restyling:** computed `font-style: normal` can still
render italic glyphs if an italic binary was mislabeled. A family/weight-only
copy path lets italic overwrite upright. Fix the emitted font mapping, not
`body { font-style: normal !important }`. Preserve source italic accents,
and compare rendered text with 1.2 clips after `document.fonts.ready`;
index-raw is not independent font evidence because it shares fonts.css.

Not the ship. No new palette, fonts, or copy. Folder
`2.1 design-tokens` is the token skill, not a second Author. Gate:
`design_system_21_gate.py` — page links `tokens.css`, receipt from
`emit-design-system.mjs`, no invented `--color` / `--font` names.

**2.2 author.** Three files in `rebuild/`:

1. `index-raw.html` — Paper `get_jsx` of `home-desktop` run through
   `dump_index_raw.py` (JSON/JSX → file:// HTML, expand `<div />`,
   link `css/tokens.css` + `css/fonts.css`). Reference dump, not the ship. Do not overlay it.
2. `index-semantic.html` — `/frontend-design` authors semantic HTML+CSS from Paper
   desktop + 2.1 tokens. Aesthetic-risk OFF. No dump metadata on this file.
   This is the 2.2 first pass. Do not write `index.html` here.
3. `index.html` — seeded at 2.3 from `index-semantic.html` (`seed_index.py`,
   never overwrite). 2.3 patches this file. 2.4 freezes it.

Paper 1600 / 768 / 390 + the 2.1 page are the visual brief. `file://`
homepage only. No new palette, fonts, or copy. No skip-link. **No source
or external `<a href>`** on `index-semantic.html`. Gate: `author_21_gate.py` — raw +
semantic exist, `index-semantic.html` is not a dump, links `tokens.css`.

**2.3 validation.** **Never skip.** First action: `seed_index.py` copies
`index-semantic.html` → `index.html` (never overwrite). Self-validate each section against
**disk gold**: the 1.2 source-section clips at 1600 / 768 / 390 plus
`rebuild/index-raw.html`. Controller runs `raw_23_census.py`,
`paper_23_disk_gold.py`, then `paper_23_clip_compare.py` so the numbered
1.2 `NN-slug.png` clips at 1600 / 768 / 390 land as side-by-sides under
`qa/paper-measure/compare/`. Measure/APPLY is serial (controller is the only
`rebuild/` writer). **No Paper MCP** — do not fan out `get_computed_styles`
/ `get_screenshot` (Pitfall #202). Dump SVG/icon fills
(`background-image: url(….svg)`) the author dropped get ported onto
`index.html`, not invented Lucide icons. Pixel-perfect is a **one-pass assist**.
After APPLY, **VALIDATE LOOK**: `--shoot-open`, then **MUST** `wave.py
prepare/start/wait/apply` (adapter from the probe), then apply printed
patches and `--record` from the findings; ≤3 rounds; a band still off at
round 3 gets a residual line. Receipt `qa/paper-measure/<id>.validate.json`
plus an applied `qa/agent-runs/<run>/2.3/wave.json`. Recipe:
`references/section-23-paper-loop.md`. Missing `index-raw.html`,
`raw-census.json`, `disk-gold.json`, `clip-compare.json`, `rawCompared`,
`diskCompared`, `clipCompared`, or the wave keeps 2.3 open. Receipts: `qa/paper-measure/_index.json` +
`qa/section-align-22.json`. **Do not return to chat until 2.4 is open.**
Pitfall #185 #192 #195 #198 #201 #202 #216 #221.

**2.4 checkpoint.** QA overlay pesticide outlines ON by default in TAGS
mode. Human receipt. Overlay default is TAGS, not off and not a hidden
query. Then 3.x.

Same `rebuild/`. Plain HTML/CSS. `file://`. No React runtime. No Tailwind
CDN. `rebuild_write_gate.py --allow design-system` at 2.1;
`--allow index` at 2.2 (keeps the Design System page and allows
`index-semantic.html`). A scrape-to-site
homepage is a failed run (Pitfall #148). A get_jsx dump is not the ship
(`index-semantic.html` / `index.html`). It **is** the 2.2 raw reference (`index-raw.html`) that
2.3 measures against it + the 1.2 source clips (Pitfall #198). Shipping
`design-system.html` as the homepage is a failed run (Pitfall #193).

## Fidelity lock (frontend-design from web2html)

- Paper desktop is gold
- Use 2.1 tokens as-is
- No new palette, fonts, or copy
- Aesthetic-risk / new identity OFF
- Homepage only, `file://`
- No source or external `<a href>` — `#` / `#id` only (Pitfall #189)
- Do not lock the next URL to a past site's headings, tel numbers,
  treatment lists, or class names

## Keep in Paper

- Homepage 1600 / 768 / 390 artboards (source of truth for 2.3)
- Design Library tokens (1.3 mined; 1.4 human review stays)
- Hover / state frames if live has them (feeds 3.x / hover, not a 2.2 restyle)
- Nothing else is required for 2.0

## Retired — dump era

Do not teach as live 2.0:

- pc-id stamp / layer-ids join / paper-semantic-tree as a 2.0 input
- get_jsx / Copy-as-Tailwind / geometry-lock / exports-inline soup as the ship
- Extra Paper frames that existed only for that join
- Source home when it is redundant with the lander
- 2.1 gallery as the **ship** (the 2.1 page is the token contract only)
- 2.2.a–e and 2.2.b Grok Cleanup as the spine — Gated-ladders and Grok Cleanup stay historical plans, not the live recipe
- stamp-pc-id-then-retag / apply-semantic-tree-is-the-ship as a required 2.0 path

1.2 does not stamp pc-path trees as Paper `layer-name`. Sidecars are optional and invisible. They are not a ship key.

**3.0** does **not** restore Paper geometry. 2.3 signed each section;
2.4 froze that ship (`qa/fidelity-freeze-24.json`) as `rebuild/index.html`.
3.x writes `rebuild/index-polish.html` only. 3.x is a11y,
scrape-only SEO, contrast on existing tokens, anti-slop, hover-if-live,
a painted burger drawer, and mandatory GSAP in-view
(`references/polish-visual-restore.md`, `references/gsap-inview.md`,
`references/nav-drawer.md`,
Pitfall #196 #203 #204 #208 #209 #210).
