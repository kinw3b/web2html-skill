---
name: design-tokens
description: Merge source-mined tokens (CSS variables + inline styles) with computed-style extraction (Playwright/dembrandt) to produce a complete, validated design system from a scraped site. Outputs both W3C tokens.json and Core Framework tokens.css. Sits in website-to-html before the Paper build.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [design-tokens, css-variables, computed-styles, w3c, core-framework]
    related_skills:
      - website-to-html             # downstream — consumes tokens.css + tokens.json
      - local-dev-server          # for verification
---

# Design Tokens — Merge Source + Computed Extraction

## Why this skill exists (lead with the result)

On a prior test capture, running
`extract-design-system` (the Playwright/dembrandt tool) **produced wrong
tokens**:

| Token | `extract-design-system` (dembrandt) | Actual live site | Source of truth |
|---|---|---|---|
| Primary color | `rgb(227, 11, 11)` (`#e30b0b`) | `#ff1818` | `--token-3e609ac1` |
| Heading font | `Inter` (only) | `Figtree` | `--framer-font-family-bold` |
| Body font | `Inter` | `Inter` | `--framer-font-family` |
| Border radius | (empty) | `12px` | inline styles |
| Box shadows | (empty) | `0 4px 84px #00000040` | inline styles |

**The dembrandt/computed-style approach gets the live site wrong on three out of
five token categories.** Why:
- Role inference is by frequency — picks the loudest color as "primary",
  not the designer's actual choice
- Custom fonts (loaded from Google Fonts or Fontshare) often don't show up
  in the first 1000 rendered text elements the tool scans
- The source CSS uses inline styles + `<style>` blocks that Playwright's
  `getComputedStyle()` doesn't fully surface

**Source-mining wins for CSS-variable-rich sites** because the live page SSRs the entire DOM, so
the `framer-reverse-engineer` Python tools can read all CSS variables,
inline styles, and CSS rules directly from the HTML. No browser needed.

This skill exists to merge both — use source as ground truth, use computed
for role inference and W3C format export, and produce a `comparison.md` that
shows every disagreement so a human can review.

## Overview

Two independent approaches exist for extracting design tokens from live sites:

1. **Source-mining** (`scrape-tokens.md` + `css_extract.py` from `framer-reverse-engineer`)
   - Reads CSS `:root` variables, inline styles, and CSS rules directly from the SSR HTML
   - Fast, no Playwright needed
   - Gives you the **design intent** (variable names, semantic tokens, fallback chains)
   - Misses: runtime-applied styles, computed values, role inference

2. **Computed-style extraction** (`dembrandt` via `extract-design-system`)
   - Runs Playwright to capture what's **actually rendered**
   - Gives you: color role inference (primary/accent/background), W3C token format
   - Misses: semantic variable names, component-specific tokens, animation data

This skill **merges both** into one validated design system output:
- `tokens.css` — Core Framework convention (`--c-accent`, `--ff-display`, etc.)
- `tokens.json` — W3C Design Tokens format (machine-readable)
- `comparison.md` — reconciliation report showing where they agree/disagree

## When to Use

- After `framer-reverse-engineer` produces `analysis/css/css_rules.json` and `analysis/sections/`
- Before `website-to-html` builds the static site
- When you want **both** the semantic source tokens AND the computed rendered values

## Pipeline position

```
1. scrape-web.sh              → source-site/ + analysis/
2. framer-reverse-engineer       → analysis/css/ + analysis/html-mine/ + analysis/sections/
3. design-tokens (THIS)   → tokens → rebuild/css/tokens.css (+ optional design-system/ for W3C json)
4. website-to-html                → rebuild/ with css/tokens.css from step 3
```

## Prerequisites

- `analysis/html-mine/component_tree.json` from `framer-reverse-engineer`
- `analysis/css/css_rules.json` from `framer-reverse-engineer`
- `site/scraped-tokens.md` from the scrape phase
- `dembrandt` CLI installed: `npm install -g dembrandt`
- `extract-design-system` CLI installed: `npm install -g extract-design-system`

Verify dembrandt is available:
```sh
export PATH="/opt/homebrew/bin:$HOME/.local/claude/bin:$PATH"
dembrandt --help
```

**If `dembrandt` / `extract-design-system` are not installed and cannot be
installed** (no npm access, offline, permissions): skip Phase 2 entirely and
proceed with Phase 1 (source-mining) only. Source-mining alone still produces
a usable `tokens.css` — it's the more reliable of the two methods for CSS-variable-rich sites
anyway (see "Why this skill exists" above). In that case:
- Skip `design-system/comparison.md` (nothing to compare against)
- Write `rebuild/css/tokens.css` (or temp design-system/ then copy into rebuild/css/)
- Note in `tokens.css`'s header comment that computed-style cross-checking was skipped

## Workflow

### Phase 1 — Source-mined tokens (from framer-reverse-engineer)

Read these existing files:
- `site/scraped-tokens.md` — CSS custom property values (the `--token-*` declarations)
- `analysis/css/css_summary.md` — most-decorated property names per component
- `analysis/css/css_rules.json` — per-component CSS rule details

From these, extract:

```python
# Pseudo-code for source token extraction
tokens = {}
# 1. Colors from scraped-tokens.md (the --token-* variables)
#    These are the DESIGN INTENT colors
for token_line in scraped_tokens:
    if token_line starts with '--token-':
        tokens['colors'][token_name] = token_value

# 2. Font families from css_rules.json
for component, rules in css_rules.items():
    for rule in rules:
        if 'font-family' in rule:
            tokens['fonts'].add(extract_font_name(rule))

# 3. Spacing from CSS rules
for component, rules in css_rules.items():
    for rule in rules:
        if 'padding' in rule or 'margin' in rule or 'gap' in rule:
            tokens['spacing'].add(parse_padding_value(rule))

# 4. Border-radius from css_rules.json
for component, rules in css_rules.items():
    for rule in rules:
        if 'border-radius' in rule:
            tokens['radius'].add(rule['border-radius'])

# 5. Box-shadows from css_rules.json
for component, rules in css_rules.items():
    for rule in rules:
        if 'box-shadow' in rule:
            tokens['shadows'].add(rule['box-shadow'])
```

Output: `design-system/source-tokens.json`

### Phase 2 — Computed-style extraction (dembrandt)

Run the extract-design-system wrapper:

```sh
export PATH="/opt/homebrew/bin:$HOME/.local/claude/bin:$PATH"
cd <project-root>
extract-design-system <url> 2>&1 | tee design-system/computed-raw.txt
```

This produces:
- `.extract-design-system/raw.json` — raw extraction
- `.extract-design-system/normalized.json` — cleaned data
- `design-system/tokens.json` — W3C format (generated, may need updating)
- `rebuild/css/tokens.css` (or `design-system/tokens.css` intermediate) — CSS custom properties

### Phase 3 — Cross-reference and merge

The merge logic:

```python
# Colors: source wins for exact hex, computed wins for role inference
# e.g., source says "token-1a99e361 → rgb(0,149,255)"
#        computed says "primary → rgb(227,11,11)"
# MERGE: keep both as --c-accent: #e30b0b (primary) and --c-link: #0095ff

# Fonts: source wins (semantic names like Figtree)
# computed may miss Figtree → Inter fallback
# MERGE: --ff-display: Figtree, --ff-body: Inter

# Spacing: source wins for exact scale
# computed may give non-standard values (1px, 47px, 290px)
# MERGE: filter to 8-pt scale (4,8,12,16,20,24,32,40,48,64,80,96,120,160)

# Radius: source wins entirely (computed often returns 0 or empty)
# computed: empty scale → source: 50px pill, 20px card, etc.

# Shadows: source wins entirely
# computed: empty → source: sm/md/lg from CSS rules
```

Output: `design-system/merged-tokens.json`

### Phase 4 — Produce final outputs

#### tokens.css (Core Framework convention)

Convert `merged-tokens.json` into the 4-file CSS structure:

```css
:root {
  /* Colors (from source + computed role mapping) */
  --c-white:        #ffffff;        /* source: token-85bb05d6 */
  --c-bg-soft:      #fafafa;        /* computed: background */
  --c-accent:       #e30b0b;        /* source: token-1a99e361 */
  --c-near-black:   #0c0e17;        /* source: token-deb92e3d */
  --c-text-mute:    #5e6075;        /* source: computed frequency */
  --c-border:       #e4e4e4;        /* source: inline style frequency */

  /* Typography */
  --ff-display: "Figtree", sans-serif;   /* source: css_rules.json */
  --ff-body:    "Inter", sans-serif;     /* source: scraped-tokens.md */

  /* Spacing (8-pt scale, source wins) */
  --s-1: 4px; --s-2: 8px; --s-3: 12px; ...
  --section-py: clamp(60px, 8vw, 120px); /* from css_rules.json */

  /* Radius (source only) */
  --r-sm: 8px; --r-md: 12px; --r-lg: 16px; --r-xl: 24px;
  --r-pill: 9999px;                       /* source: ×8 inline styles */

  /* Shadows (source only) */
  --shadow-sm: 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 6px 24px rgba(0,0,0,.06);
  --shadow-lg: 0 12px 48px rgba(0,0,0,.10);

  /* Container */
  --container-max: 1280px;
  --container-px:  clamp(20px, 4vw, 30px);
}
```

#### tokens.json (W3C format)

The W3C Design Token Format Community Group (DTCG) uses this structure:

```json
{
  "$type": "color",
  "color": {
    "white": { "$value": "#ffffff", "$description": "source: token-85bb05d6" },
    "accent": { "$value": "#e30b0b", "$description": "source: token-1a99e361" },
    "near-black": { "$value": "#0c0e17", "$description": "source: token-deb92e3d" },
    "text-mute": { "$value": "#5e6075", "$description": "computed: secondary text" }
  },
  "font": {
    "display": { "$value": "Figtree", "$description": "source: css_rules.json" },
    "body": { "$value": "Inter", "$description": "source: scraped-tokens.md" }
  },
  "space": {
    "1": { "$value": "4px" },
    "2": { "$value": "8px" },
    ...
    "section-py": { "$value": "clamp(60px, 8vw, 120px)" }
  },
  "radius": {
    "sm": { "$value": "8px" },
    "pill": { "$value": "9999px", "$description": "source: inline ×8 occurrences" }
  }
}
```

#### comparison.md

Document where the two methods agree/disagree:

| Token | Source-mined | Computed (dembrandt) | Winner | Reason |
|---|---|---|---|---|
| Primary color | `rgb(0,149,255)` (token-1a99e361) | `rgb(227,11,11)` (role=primary) | Source | Source is exact CSS var; computed assigned roles by frequency |
| Heading font | Figtree | Inter | Source | Computed missed Figtree because it's only in CSS rules, not on rendered text in first frame |
| Accent color | — | `rgb(227,11,11)` | Computed | No accent token in source, but dembrandt detected the red as "primary" |
| Card radius | 20px (from css_rules) | (empty) | Source | Computed didn't detect border-radius from the source CSS |

## Safety boundaries

- Do NOT overwrite source-mined tokens with computed values without manual review
- Do NOT treat dembrandt's "primary/accent/background" labels as authoritative — live sites may have 5+ colors and the role inference is approximate
- Always preserve the `--token-*` → `--c-*` name mapping in comments for traceability
- Generated `tokens.css` should be checked in to version control — not auto-applied

## Anti-normalization (share tokens only when proven)

Measure / mine components **independently**. Promote a shared scale step
(radius, shadow, spacing, button height, type size) **only when evidence shows
identical values** across instances — not because an 8-pt scale or "one card
recipe" is convenient.

| Do | Do not |
|---|---|
| Keep `12px` and `16px` as separate `--r-*` if both appear | Collapse both to `--r-md: 12px` |
| Record per-corner radii when they differ | Assume uniform radius |
| Leave odd values (23px padding) until N instances match | Round to 24px for cleanliness |
| Tokenize after repeated identical measurements | Invent a universal button/card from the first instance |

Downstream `website-to-html` Step 3 and `components.css` follow the same rule:
global utilities must not stomp component-specific measured values.

## Known limitations of `dembrandt` on live sites

The Playwright-based `dembrandt` engine (called by `extract-design-system`)
has specific failure modes on these sites. Document them so future agents know
what to fix in the comparison:

| Failure | What dembrandt returns | What's actually in the source | Where to look in source |
|---|---|---|---|
| **Misses custom display fonts** | Only `Inter` (the body font) | `Figtree`, `Supreme`, or other custom display | `--framer-font-family-bold` in `<style>` block |
| **Wrong "primary" color** | Most-frequent saturated color | `--token-{X}` with role `primary` or `accent` (often darker/more muted) | `--token-*` declarations in `:root` |
| **Empty radius scale** | `[]` | `12px`, `20px`, `50px` (pill) etc. | `border-radius` in inline styles + CSS rules |
| **Empty shadow scale** | `[]` | `box-shadow: 0 4px 16px ...` | inline styles + CSS rules |
| **Confuses `--token-*` with role names** | Reports `rgb(12,14,23)` as `bg-color` (because it's near-black) | `--token-1e123b81` is `near-black`, not `bg` | Look at semantic name, not frequency |
| **Sees `placeholder` fonts as real** | Sometimes reports "Inter Display" as a separate font | `Inter Display` is a fallback placeholder, not a real load | Strip `"X Placeholder"` strings from output |

**Workaround for the radius/shadow issue:** the `framer-reverse-engineer`
Python tools (`css_extract.py`) capture all inline `border-radius` and
`box-shadow` declarations from `style="..."` attributes and CSS rules in
the SSR HTML. Use that as ground truth; ignore dembrandt's empty
scales.

## Integration with website-to-html

**Canonical output for the rebuild pipeline:** `rebuild/css/tokens.css` (sole `:root`).

When this skill finishes:
1. Prefer writing tokens straight to `rebuild/css/tokens.css` if `rebuild/` exists.
2. Or write `design-system/tokens.css` + `tokens.json` + `comparison.md`, then  
   `cp design-system/tokens.css rebuild/css/tokens.css`.

`website-to-html` Step 3 expects tokens already in `rebuild/css/tokens.css` (or copies from this skill's output). Do not leave tokens only under a permanent `v1/` path.

## Reference files

- `scripts/merge-tokens.py` — the merger. Reads `site/scraped-tokens.md`,
  `analysis/css/css_rules.json`, `analysis/html-mine/component_tree.json`,
  and `design-system/tokens.json` (dembrandt output). Cross-references and
  produces `tokens.css` + `tokens.json` (W3C) + `comparison.md`.
- `references/w3c-format-example.md` — W3C DTCG token structure reference,
  with side-by-side comparison to Core Framework convention.
- `references/dembrandt-mapping.md` — generic guidance for mapping computed
  role labels to source semantics. Do not store site names, URLs, or UUIDs.

## Paper Design Library — replace, do not append

The Paper writer lives in `1.2 url-to-paper` (`library-sheet.mjs` /
`render-library.mjs`). A 1.5 token pull that `write_html`s foundations with
`insert-children` **appends** a second `colour` / `typography` / `spacing`
set on top of the P-0 greyscale seed. Live landers bind the new tokens; the
old unused scale stays on the board.

**Rule:** `writeFoundationSections` must delete an existing same-named
section (`colour`, `header`, …) before insert. `updateDesignLibrary` still
passes `replace: true` (wipe all children). Never seed + update without
that replace-by-name gate. The 1.5 sheet contract (url-to-paper 1.2.69) always
includes five Tailwind SEMANTIC colors, `--text-10xl`…`--text-12xl`, large →
small `Aa` specimens, and a 4-up colour grid. 2.1 must not drop those
tokens when writing `rebuild/css/tokens.css`.
