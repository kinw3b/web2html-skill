# Paper Snapshot — how the serializer works

Teardown of the Paper Snapshot Chrome extension (`lidfahaahiogmnlccifabccgplofocck`,
v0.3.12), which is where `scripts/serializer.js` comes from. Paper-Bridge
`content/paper-snapshot.js` @ `fda64f2` (v0.3.8) is the base implementation
reference; the 0.3.10→0.3.12 deltas were re-extracted from the installed
extension (see the diff notes below). Read this before changing the serializer.

## What it is

Not a screenshotter. It walks the live DOM and emits **self-contained
inline-styled HTML**, which Paper parses into layers. No canvas, no rasterizing,
no `fetch`. The extension makes **zero network calls** — it is entirely local.

## Extension shape

| File | Role |
|---|---|
| `manifest.json` | MV3. Permissions: `scripting`, `activeTab`, `clipboardWrite`, `offscreen`. No declared content scripts. |
| `background.js` | Everything. Picker overlay + serializer, injected on demand. |
| `offscreen.js` | 59 lines. Writes `text/html` to the clipboard. |
| `popup.js` | 192 KB of React. UI shell only — nothing load-bearing. |

Original flow: toolbar click / Cmd+Shift+P → inject picker → hover-highlight →
click → serialize → wrap in `<x-paper-html>` → offscreen doc → clipboard → user
pastes into Paper.

The offscreen document exists because MV3 service workers have no DOM and so
cannot touch the clipboard. It creates a `contentEditable` div, selects it,
intercepts the `copy` event, and calls `clipboardData.setData("text/html", …)`.

## The core trick: computed-style diffing

Dumping every computed property per node would mean ~340 declarations on every
element. Instead the serializer:

1. Creates a throwaway `<link>` element as a **style baseline**.
2. Forces known values on it with `!important` (transparent background, zero
   border, `font-size: 1px`, `margin: 0`, …).
3. Reads *its* computed style.
4. Emits only the properties where the target element **differs** from that baseline.

`<link>` is the right choice because it is inert, renders nothing, and is valid
almost anywhere in the DOM. This diff is the entire compression strategy.

## Edge cases it handles

This is where the real work is, and why the code is lifted rather than rewritten.

- **Shadow DOM** — `elementsFromPoint` pierces shadow roots in a loop; the
  serializer recurses into `shadowRoot.childNodes`.
- **Slots** — `assignedNodes({flatten: true})`.
- **SVG `<use>`** — `svgHrefId()` takes the decoded fragment after the final
  `#` (Framer `https://site/#svg-123`, `url(#id)`, or `#id`). Lookup searches
  the current root, the document, then open shadow roots. `elementId()` never
  calls `startsWith` on a non-string SVG `id`. Direct SVG/path/use selections
  promote to the nearest `HTMLElement` host so Paper imports `SVG → Path`,
  not an empty frame.
- **`::before` / `::after`** — parses the `content` string, emits real `<div>`s.
- **`::placeholder`** — stashed in `data-paper-placeholder-styles`.
- **Whitespace** — uses `Range.getBoundingClientRect().width > 0` to decide
  whether a collapsed leading/trailing space actually *renders*.
- **Form state** — input `value`/`checked`/`type`, textarea contents, the
  selected `<option>`.
- **Tables → `<div>`** — rewritten with a `paper-snapshot-original-tag`
  attribute, since Paper's layout model has no table algorithm.
- **Skips** invisible nodes via `checkVisibility()`, `display:none`,
  `opacity:0`, and zero-size-clipped elements.
- **Two-pass** — a `dryRun` pass counts nodes for the progress bar, then the
  real pass yields between nodes so the page never freezes.
  `AbortController` wired to Escape.

## New in 0.3.12 (vs the 0.3.8 base)

- **Throttled yield** — the per-node `requestAnimationFrame` became a yield at
  most every 16 ms, skipped entirely while `document.hidden`. Large pages
  serialize dramatically faster.
- **Baseline positioning resets** — the throwaway `<link>` baseline now also
  forces `position: static`, `top/right/bottom/left/inset: auto`, and
  `transform/translate/rotate/scale: none`, so positioned and transformed
  elements emit those properties in the diff.
- **Canvas/video rasterization** — the dry run collects `<canvas>` and
  `<video>` elements; between passes each is drawn to PNG (`toBlob` →
  `FileReader` data URI) and emitted as an `<img>` with
  `paper-snapshot-original-tag`. Tainted canvases fail silently and fall
  through to the old empty-frame behavior. Their subtrees are not walked.
- **In-page reduced-motion emulation** — walks every stylesheet (including
  `@import`, adopted sheets, and open shadow roots; recursing through
  `@supports`/`@container`/`@scope`/`@layer`), extracts
  `prefers-reduced-motion: reduce` rules, injects them as unconditional
  adopted sheets, and finishes running `CSSTransition`s. Cross-origin sheets
  are skipped; failure logs a warning and captures as-is; cleanup restores the
  original adopted sheets in `finally`. This complements (does not replace)
  the Playwright `reducedMotion: "reduce"` emulation in `capture.mjs` —
  Framer often ignores the media query but cannot ignore injected CSS.
- **`content: url()` pseudo-elements** — `::before`/`::after` content is now
  tokenized into strings and `url()` parts; a single-url content emits a
  styled `<img>`, mixed content a `<div>` with inline `<img>`s. Previously
  image content was dropped.
- **Wider opacity-0 drop** — an `opacity: 0` element is now also dropped when
  it is its parent's only element child (modal/menu shells parked at
  opacity 0), not just when absolute/fixed. The 1.2 rest-paint pass
  (`settlePainted`) still runs first, so in-flow Framer appear leftovers have
  live opacity 1 by serialization time and are unaffected.

## Consequences for this skill

**`opacity: 0` overlays are dropped** (absolute/fixed). In-flow appear
leftovers (`opacity: 0` + `translateY`) are **rest-painted to 1** so Paper
does not import 0% blending. `reducedMotion: "reduce"` plus `settlePainted`
(force rest) plus the scroll pass — Framer often ignores reduced motion.

**Images are emitted as remote `src` URLs**, never inlined, with explicit
width/height pinned from computed style. Anything behind auth, hotlink
protection, or a signed CDN URL breaks. Inlining as data URIs is the obvious
upgrade and the one place this skill could beat the original.

**No `@font-face`.** `<style>` and `<link>` are skipped, so font *names* survive
but webfont files do not.

## Extraction

`scripts/serializer.js` is Paper Snapshot 0.3.12 plus 1.2 layer-name / sidecar
behavior. The 0.3.8 base came from Paper-Bridge `content/paper-snapshot.js`;
the 0.3.10→0.3.12 deltas were diffed out of the installed extension's minified
`background.js` (identifier names churn per release — diff string literals and
structure, not raw text). Keep 1.2 adaptations in `fe()`. Do not call the file
“lifted verbatim.”

To re-extract from a newer version:

```bash
EXT="$HOME/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions/lidfahaahiogmnlccifabccgplofocck"
npx prettier@3 --parser babel "$EXT/<version>/background.js" > background.pretty.js
# find the `async function fe(n)` boundaries — they will have moved
```
