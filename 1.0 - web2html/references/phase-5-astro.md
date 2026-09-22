# 5.0 — bind the site into Astro (chrome once, then page bodies)

Phase 5 turns the 3.4 homepage lock plus the 4.4 Paper pages into `astro/`.
The move that makes it one phase: **Header, Footer, and every shared
component are pulled ONCE from `rebuild/index.html` at 5.1** (the 3.4
promote; falls back to `index-polish.html` if that file is still on disk). Every
later page reuses them, so 5.2 authors only the `<main>` body (the sections
that page actually has). Homepage 1.1–3.4 stays the lock. `rebuild/` stays
the static homepage ship and is never replaced. No React. No Tailwind CDN.
No new `--color` / `--font` names. The agent never starts `astro dev`.

```
5.1 scaffold + chrome   →  5.2 author bodies  →  5.3 desktop QA  →  5.4 responsive
→  5.5 routes + SEO + build  →  5.6 human checkpoint (tidy)
```

## 5.1 — scaffold astro/ + shared chrome (machine)

```sh
python3 "$SKILLS/web2html/scripts/scaffold-astro.py" .              # qa/phase-5-scaffold.json
python3 "$SKILLS/web2html/scripts/extract-astro-components.py" .    # qa/phase-5-components.json
python3 "$SKILLS/web2html/scripts/convert-astro-home.py" .          # qa/phase-5-home.json
```

- `scaffold-astro.py` copies `rebuild/css` (tokens, fonts, site, hover),
  `rebuild/js`, images, fonts into `astro/public/` and writes `package.json`,
  `astro.config.mjs` (static, trailing slash), `src/layouts/BaseLayout.astro`.
  BaseLayout takes `title / description / lang / canonical / ogImage` props —
  5.5 SEO is props, never markup. QA overlay CSS/JS never copies in.
- `extract-astro-components.py` lifts `<header>` → `Header.astro` and
  `<footer>` → `Footer.astro` from the polish homepage, then every
  Paper-backed control (Design Library names, Capture Tool
  `source-site/components`, FRAME Components / Buttons / Navigation) and
  comment nomination (`<!-- component: Name -->`, Paper comments that call a
  block a reusable component) that appears in signed HTML. One-off sections
  stay inlined. Hrefs inside the chrome become routes (`about.html` → `/about/`).
- `convert-astro-home.py` writes `src/pages/index.astro` from the polish
  `<main>` on that chrome, swapping matching component markup for the
  extracted components. Interiors are **not** converted here.

All three receipts are the 5.1 done-gate.

## 5.2 — author interior bodies (self, T1)

Paper MCP is serial. Never `create_file` / `list_files`.

```sh
python3 "$SKILLS/web2html/scripts/rebuild_write_gate.py" . --allow pages   # raw dumps only
node "$SKILLS/web2html/scripts/dump-interior-raw.mjs" --project .
# or: node "$SKILLS/url-to-paper/scripts/dump-interior-raw.mjs" --project .
# writes rebuild/{slug}-raw.html + qa/phase-5-raw.json
```

Then fan out **at most two** author workers (`frontend-design`). Each gets:

- `astro/src/components/Header.astro` + `Footer.astro` (read-only — this is the chrome)
- `astro/src/components/*.astro` extracted at 5.1 (reuse, do not restyle)
- `rebuild/design-system.html` + `astro/public/styles/tokens.css`
- `rebuild/{slug}-raw.html` (structure reference)
- Paper `{slug}-desktop` as the visual brief

Each worker writes **only** `astro/src/pages/{slug}.astro` in this shape:

```astro
---
import BaseLayout from '../layouts/BaseLayout.astro';
import Header from '../components/Header.astro';
import Footer from '../components/Footer.astro';
import BtnPrimary from '../components/BtnPrimary.astro';   // only what the page uses
const title = `About`;
const description = ``;
const lang = `en`;
---
<BaseLayout title={title} description={description} lang={lang}>
  <Header />
  <main>
    <section id="about-hero">…</section>     <!-- only this page's sections -->
  </main>
  <Footer />
</BaseLayout>
```

Rules for the body: no `<header>` / `<footer>` inline (chrome comes from
5.1), exactly one `<main>`, asset paths `/images/…` `/styles/…`, hrefs stay
`#` until 5.5, aesthetic-risk OFF, no invented copy / palette / fonts.

```sh
python3 "$SKILLS/web2html/scripts/record-phase-5-pages.py" .   # qa/phase-5-pages.json
```

`"ok": true` is the 5.2 receipt. It rejects a page that skips the chrome
imports, inlines chrome, carries a get_jsx dump, or links off-site.

### Workers

- MUST NOT call Paper write tools.
- MUST NOT edit `astro/src/components/*`, `BaseLayout.astro`, `tokens.css`,
  `index.astro`, or another slug.
- MUST NOT invent copy, palette, or fonts.

## 5.3 / 5.4 — clip QA on the BUILT pages (self, T1)

The ship is `astro/dist/{slug}/index.html`, not the `.astro` source. Build,
then shoot the built page on `file://` exactly like 2.3:

```sh
python3 "$SKILLS/web2html/scripts/build-astro-dist.py" .       # astro build + file:// relativize → qa/phase-5-build.json
python3 "$SKILLS/web2html/scripts/paper_23_rebuild_shots.py" . \
  --page {slug} --ship astro/dist/{slug}/index.html --widths 1600 --all
python3 "$SKILLS/web2html/scripts/phase_5_compare.py" . --mode desktop      # 5.3 → qa/phase-5-clip-compare.json

node "$SKILLS/hover-reel/scripts/capture-interior-breakpoints.mjs" --project .   # live 768/390 source clips
python3 "$SKILLS/web2html/scripts/paper_23_rebuild_shots.py" . \
  --page {slug} --ship astro/dist/{slug}/index.html --widths 768,390 --all
python3 "$SKILLS/web2html/scripts/phase_5_compare.py" . --mode responsive   # 5.4 → qa/phase-5-responsive.json
```

Gold is `capture/{slug}-desktop/source-sections/` (4.2) and
`capture/{slug}-768|390/source-sections/` (5.4 live clips). Fixes go into
`src/pages/{slug}.astro`, then rebuild and reshoot. Serial or max two
disk-only workers. **No Paper MCP.** No extra Paper frames. Real media
queries, never `width:100% !important`.

## 5.5 — wire routes + SEO + build (machine)

```sh
python3 "$SKILLS/web2html/scripts/wire-astro-routes.py" .    # qa/phase-5-links.json
```

- Sitemap paths and nav / footer labels → routes across `astro/src`
  (Header, Footer, pages): `/` home, `/about/` interiors. Leftover `.html`
  hrefs → routes. External / mailto / tel stay `#`.
- Per-page scrape-only SEO into that page's frontmatter (BaseLayout props):
  title / description / lang / canonical / og:image from the page's own
  live URL or 4.x local copy. Homepage takes its own `qa/scrape-meta.json`.
  Never merge homepage meta onto an interior. No heading / section retag.
  Receipts `qa/phase-5-semantics/{slug}.json`.
- `astro build`, then relativize `astro/dist` for `file://`. Build log in
  `qa/phase-5-build.log`. `--skip-build` only for tests.

## 5.6 — human checkpoint

```sh
python3 "$SKILLS/web2html/scripts/open-phase-5-review.py" .   # qa/phase-5-review.md, opens built home + first interior
```

Walk the routes. Shared chrome must match the 3.4 polish; bodies must match
Paper. Human preview server is optional (`cd astro && npm run preview`).
Then `mark --step 5.6 --status done` — that tidies and keeps `rebuild/` +
`astro/` + `pipeline.html`.

## Layout

```
astro/
  package.json
  astro.config.mjs          # output: static, trailingSlash: always
  src/layouts/BaseLayout.astro
  src/components/Header.astro     # pulled once at 5.1
  src/components/Footer.astro
  src/components/{Name}.astro     # Paper buttons + comment-nominated blocks
  src/pages/index.astro           # 5.1 from the polish homepage
  src/pages/{slug}.astro          # 5.2 authored bodies
  public/styles/                  # tokens.css, fonts.css, site.css, hover.css
  public/images/  public/fonts/  public/scripts/
  dist/                           # 5.3+ built ship, file:// friendly
```
