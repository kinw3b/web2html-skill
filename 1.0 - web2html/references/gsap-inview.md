# GSAP in-view reveal — website-to-html 2.10.11 companion

Companion recipe for the Emil pass (`templates/gsap-reveal.js`).

**Mandatory in tracker step 3.2.** Every run injects sequential fade + rise
as each **parent group**'s top crosses **25% of the viewport from the bottom**
(`expo.out`, ~950ms, 28px, `start: "top 75%"`). Heads stagger their
children; grids stagger sibling articles/divs/lis. Not a heading-leaf dump.
**Never skip because 1.4 did not record in-view motion.** That archive
rule is retired (Pitfall #204). Write polish only
(`rebuild/index-polish.html`). Do not mutate the 2.4 `index.html` lock
(Pitfall #203). Do not hide first paint with CSS or `class="reveal"`
(Pitfall #1 / #196).

Pointed at from `4.4 emil-design-eng` and `4.5 find-animation-opportunities`.

## Why this exists

Static rebuilds used to ship without motion, then a 1.4 archive skip
left every later run dead. GSAP in-view is now a required 3.2 pass.
Above-fold stays visible; below-fold staggers as each section crosses
the 25%-from-bottom line so the cascade is readable.

## Commands (Emil / tracker 3.2 — always)

```sh
python3 "$SKILLS/website-to-html/scripts/inject-gsap-reveal.py" rebuild/index-polish.html
python3 "$SKILLS/website-to-html/scripts/verify-gsap-reveal.py" .
```

`verify-polish-passes.py` always calls `verify-gsap-reveal.py`. Missing
inject fails the gate. `mark --step 3.2 --status done` needs
`qa/gsap-reveal-qa.json` with `"ok": true`.

Do **not** run inject against a live NEO test tree (for example, a project's `rebuild/`)
from this skill change — scripts + skills only until a later apply pass.

## Vendor (file:// only)

Official minified GSAP 3.15.0 lives in the skill:

- `templates/vendor/gsap/gsap.min.js`
- `templates/vendor/gsap/ScrollTrigger.min.js`

Inject copies them to `rebuild/js/vendor/` and writes
`rebuild/js/gsap-reveal.js` from `templates/gsap-reveal.js`. Script tags
go on `rebuild/index-polish.html` (and other rebuild html except the 2.4
`index.html` lock and skip-list pages) after existing JS.

Never CDN at runtime. Never `paper-asset://`.

## Candidates

Mark with **`data-reveal`** on **parent groups** (keep that attribute —
Pitfall #1 grep still works):

- section-level hosts (`section`, `article`, `footer`)
- section heads (`header.section-head`, `div.section-head`, `*-head`, `*-intro`)
- mixed inners (`about-inner`, `*-banner` — copy + media). Not `section-inner`
- grids / collections (`*-grid`, `*features`, cards)

Do **not** mark heading leaves (`h1`–`h6`). The runtime walks each parent
and staggers **first children + siblings**:

- Head only → eyebrow / title / lead (unwrap `.stack`)
- Grid / collection → sibling `article` / `.card` / `li` items
- Mixed inner → flatten copy + media wrappers, expand a nested feature
  list, keep photo / badge

Skip:

- `nav`, site `header` (`site-header` / navbar). Section heads are not site chrome.
- already-visible hero (class/id `hero`) — runtime also leaves anything
  with `top < 92vh` visible
- decorative SVGs / paws / watermarks / `data-decorative`
- qa-overlay
- skip-links (do not invent skip-links)

**Do not** use `class="reveal"` (Pitfall #1 bans it).

## Runtime (`gsap-reveal.js`)

- GSAP + ScrollTrigger only. **No** `window` scroll listeners.
- On boot: measure. Above-fold (`top < 92vh`) → immediately visible
  (no `is-prep`). Below-fold parent groups → hide their members with
  `gsap.set({ opacity: 0, y: 28 })`.
- One ScrollTrigger per **parent group** (head, grid, mixed inner, or
  fallback section/footer). `start: "top 75%"` — that group's top is
  25% of the viewport up from the bottom. That is when the cascade
  starts, so the stagger is on screen.
- Motion: fade + rise (`y` 28), `expo.out`, **950ms**. Members inside
  that parent stagger **80ms** in document order (not a one-shot dump
  of the whole page, and not each heading on its own).
- Nested `[data-reveal]` hosts are not tweened — only the resolved
  children — so a section and its cards do not double-translate.
  Cards inside a grid are members, not inner groups. `__gsapRevealInspect()`
  returns `{ host, members }[]` for QA.
- `once: true` (do not replay on scroll-back).
- `prefers-reduced-motion`: no hide, no tween.
- QA / headless skip prep (everything stays visible) when:
  - `?qa-outlines=` is present (query or hash), **or**
  - `html[data-qa-outlines]` is set and not `off`, **or**
  - `prefers-reduced-motion: reduce`
- Scroll-walk in existing Playwright still works: below-fold becomes
  visible on trigger.
- Expose `window.__gsapRevealReady` and
  `document.documentElement.dataset.gsapReveal = "on"`.
- Do not pin, do not scrub, do not hijack scroll, no parallax, no
  bounce/elastic, no scale-from-0.
- Cleanup: `gsap.context` + `revert` on `pagehide` /
  `window.__gsapRevealTeardown`.

No CSS hide. First paint of hero/header is visible because nothing is
hidden until JS measures, and above-fold is never prepped.

## Pitfall #1 must survive

- `data-reveal` stays
- `class="reveal"` still banned
- above-fold never starts hidden
- headless first paint of hero/header is visible
- scroll-walk still reveals below-fold
- no skip-links invented

## 4.5 cap

The in-view pass is **mandatory** and does **not** count against the
5–7 extras cap. Motion `whileInView` is for React apps; this static
`file://` rebuild uses GSAP ScrollTrigger. Do not expand 5.A / 5.B
sticky-stack / horizontal-pan unless the source recorded it.
