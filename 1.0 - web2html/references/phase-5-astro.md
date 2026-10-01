# 5.0 — bind the site into Astro (chrome once, then page bodies)

Phase 5 turns the 3.4 homepage lock plus the 4.4 Paper pages into `astro/`.
The move that makes it one phase: **Header, Footer, and every shared
component are pulled ONCE from `rebuild/index.html` at 5.1** (the
3.4-finalized ship — `rebuild/index.html` with the overlay stripped in place at 3.4 done;
no polish-file fallback exists). Every
later page reuses them, so 5.2 authors only the `<main>` body (the sections
that page actually has). Homepage 1.1–3.4 stays the lock. `rebuild/` stays
the static homepage ship and is never replaced. No React. No Tailwind CDN.
No new `--color` / `--font` names. The agent never starts `astro dev`.

```
5.1 scaffold + reuse plan + chrome/shared sections  →  5.2 build-first sections, then bodies
→  5.3 desktop QA  →  5.4 responsive  →  5.5 routes + SEO + build  →  5.6 human checkpoint (tidy)
```

**Reuse before authoring (Pitfall #244).** A band that appears on two or more
pages is ONE component. Nobody re-authors it per page. `shared_sections.py`
inspects the whole sitemap on disk before any body is written and writes
`qa/phase-5-reuse.json`:

| Group origin | Who builds it | When |
|---|---|---|
| `home`: the homepage already ships the band | `extract-astro-components.py` lifts it from `rebuild/index.html`; `convert-astro-home.py` renders `<{Name} />` | 5.1 (machine) |
| `interior` (`buildFirst`): repeats only on interior pages | the controller, once, from the group's `anchor` member | 5.2, before any page worker |

Bands match on **copy + image overlap**, not section names. Each member
is `identical` (render as-is) or `variant` (same band with different copy;
add a prop or slot to the component, and keep it one component).

## 5.1 — scaffold astro/ + shared chrome (machine)

```sh
python3 "$SKILLS/web2html/scripts/scaffold-astro.py" .              # qa/phase-5-scaffold.json
python3 "$SKILLS/web2html/scripts/extract-astro-components.py" .    # qa/phase-5-components.json
python3 "$SKILLS/web2html/scripts/convert-astro-home.py" .          # qa/phase-5-home.json
```

- `scaffold-astro.py` copies `rebuild/css` and `rebuild/js` (**recursively —
  `js/vendor/` rides along**), images, and fonts into `astro/public/`, then
  derives BaseLayout's stylesheet + script wiring from the **ship's own
  head** (`rebuild/index.html`): every `<link>` / `<script src>` the signed
  page carries, in order, emitted `is:inline` so Astro bundles nothing.
  Each inline `<style>` is its own sheet (`public/styles/site.css`, then
  `site-2.css`; `site-inline.css` when `rebuild/css/site.css` already
  exists) linked at that block's position — concatenating them would let a
  later `<link>` win over rules that belonged after it. Inline `<script>`
  bodies are written to `public/scripts/ship-inline-N.js` and linked, never
  pasted into `BaseLayout.astro` (`{` there is an Astro expression and the
  build fails). A script that lived in `<head>` stays in `<head>`. Author
  runs also link any copied sheet/script the ship forgot; adopt
  runs record those as `unreferenced` instead. The receipt **fails when
  BaseLayout references an asset that does not exist under `public/`**
  (Pitfall #240). BaseLayout takes `title / description / lang / canonical /
  ogImage` props — 5.5 SEO is props, never markup. QA overlay CSS/JS never
  copies in.
- `astro.config.mjs` is `output: 'static'` and nothing else (Pitfall #245).
  **No `trailingSlash`**: Astro's default `'ignore'` serves `/about` and
  `/about/` alike, so no host or CMS is forced into one URL shape. Default
  `build.format` (`dist/{slug}/index.html`) is what the `file://` relativizer
  expects. `astro` is `^7.3.5` (Node ≥22.12).
- Live content collections are pre-wired for a future CMS:
  `src/live.config.ts` defines a `pages` live collection on the REST loader in
  `src/loaders/cms.ts`, which reads `CMS_API_URL` (`.env.example`; `.env` is
  gitignored). Static pages never query it, so the build is unchanged. A page
  goes dynamic with `export const prerender = false`, an adapter, and
  `getLiveCollection('pages')` / `getLiveEntry('pages', id)`. These files are
  written only when missing; a re-scaffold never clobbers a wired loader.
- `extract-astro-components.py` lifts `<header>` → `Header.astro` and
  `<footer>` → `Footer.astro` from `rebuild/index.html`, runs the sitemap
  reuse plan (`shared_sections.plan` → `qa/phase-5-reuse.json`) and lifts
  every `home`-origin band → `src/components/{Name}Section.astro`. It prints
  `BUILD FIRST: …` for the interior-only groups. Then every
  Paper-backed control (Design Library names, Capture Tool
  `source-site/components`, FRAME Components / Buttons / Navigation) and
  comment nomination (`<!-- component: Name -->`, Paper comments that call a
  block a reusable component) that appears in signed HTML. One-off sections
  stay inlined. Hrefs inside the chrome become routes (`about.html` → `/about/`).
- `convert-astro-home.py` writes `src/pages/index.astro` from the homepage
  `<main>` on that chrome. Shared bands are swapped for their whole-section tags
  first, then the remaining matching component markup is swapped for the
  extracted components. Interiors are **not** converted here.

All three receipts are the 5.1 done-gate. `bind_source_images.py .` must also
be green: every raster the homepage references is a byte-copy of the source
original, not a Paper file-asset or a `scale-down-to` thumb (Pitfall #243).

## 5.2 — author interior bodies (self, T1)

Paper MCP is serial. Never `create_file` / `list_files`.

```sh
python3 "$SKILLS/web2html/scripts/rebuild_write_gate.py" . --allow pages   # raw dumps only
node "$SKILLS/web2html/scripts/dump-interior-raw.mjs" --project .
# or: node "$SKILLS/url-to-paper/scripts/dump-interior-raw.mjs" --project .
# writes rebuild/{slug}-raw.html + qa/phase-5-raw.json
python3 "$SKILLS/web2html/scripts/shared_sections.py" .   # re-plan with every dump on disk
```

**Build first (controller, serial).** For each `buildFirst` group in
`qa/phase-5-reuse.json`, write `astro/src/components/{Name}.astro` **once**
from the group's `anchor` (Paper `{anchor.page}-desktop` + that band in
`rebuild/{page}-raw.html`). Expose props or a `<slot />` for whatever the
`variant` members change. If the re-plan lists a new `home`-origin group under
`missingComponents`, re-run `extract-astro-components.py` +
`convert-astro-home.py` first. No page worker starts until every group's file
exists.

Then fan out **at most two** author workers (`frontend-design`). Each gets:

- `astro/src/components/Header.astro` + `Footer.astro` (read-only — this is the chrome)
- `qa/phase-5-reuse.json` → `byPage[slug]`: the shared sections this page
  **must** import and render in place. The worker does not re-author them, and
  a variant passes props.
- `astro/src/components/*.astro` extracted at 5.1 (reuse, do not restyle)
- `rebuild/design-system.html` + `astro/public/styles/tokens.css`
- `rebuild/{slug}-raw.html` (structure reference)
- Paper `{slug}-desktop` as the visual brief
- Photos: copy bytes from `source-site/assets/` (the unscaled file). Do not download Paper `file-assets` or `?scale-down-to=`. Run `bind_source_images.py .` before `record-phase-5-pages.py` (Pitfall #243).

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
imports, inlines chrome, carries a get_jsx dump, or links off-site. It also
rejects a page that skips a shared section listed for it, renders a shared
section and also pastes its copy, a missing build-first component, and a
reuse plan older than a page's section source (Pitfall #244).

### Workers

- MUST NOT call Paper write tools.
- MUST NOT edit `astro/src/components/*`, `BaseLayout.astro`, `tokens.css`,
  `index.astro`, or another slug. A variant that needs a new prop goes back
  to the controller, which edits the component once.
- MUST NOT re-author a band listed in `byPage[slug]`. Import it.
- MUST NOT invent copy, palette, or fonts.

## 5.3 / 5.4 — clip QA on the BUILT pages (self, T1)

The ship is `astro/dist/{slug}/index.html`, not the `.astro` source. Build,
then shoot the built page on `file://` exactly like 2.3:

```sh
python3 "$SKILLS/web2html/scripts/build-astro-dist.py" .       # astro build + file:// relativize → qa/phase-5-build.json
```

`qa/phase-5-build.json` also resolves every local stylesheet/script
reference in each built page against disk and fails on a dangling one — a
404'd sheet can never ride a green `astro build` again (Pitfall #240).

```sh
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

Walk the routes. Shared chrome must match the 3.4 ship; bodies must match
Paper. Human preview server is optional (`cd astro && npm run preview`).
Then `mark --step 5.6 --status done` — that tidies and keeps `rebuild/` +
`astro/` + `pipeline.html`.

## Layout

```
astro/
  package.json
  astro.config.mjs          # output: static (no trailingSlash, default build.format)
  .env.example              # CMS_API_URL for live collections
  src/live.config.ts        # live content collections (CMS seam, request time)
  src/loaders/cms.ts        # REST live loader (loadCollection / loadEntry)
  src/layouts/BaseLayout.astro
  src/components/Header.astro     # pulled once at 5.1
  src/components/Footer.astro
  src/components/{Name}.astro     # Paper buttons + comment-nominated blocks
  src/components/{Name}Section.astro  # bands shared across pages (qa/phase-5-reuse.json)
  src/pages/index.astro           # 5.1 from rebuild/index.html
  src/pages/{slug}.astro          # 5.2 authored bodies
  public/styles/                  # every sheet the ship links + site.css
                                  # (materialized from the inline <style>)
  public/images/  public/fonts/
  public/scripts/                 # rebuild/js copied recursively (vendor/ too)
  dist/                           # 5.3+ built ship, file:// friendly
```
