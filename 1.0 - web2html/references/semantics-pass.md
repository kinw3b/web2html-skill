# Semantics pass — website-to-html 3.3 companion

Last automated sweep before the human checkpoint. Encode **patterns**,
not one lifestyle page's class names. Paper is the brief. No restyle,
no new palette / fonts / layout / copy.

This is the ship-page **SEO, accessibility, and lock-safe performance**
pass. It does not invent marketing copy, skip-links, or a bundler.

2.2 already authored semantic HTML. 2.3 already signed each section
against Paper. 2.4 already accepted that paint (`qa/fidelity-freeze-24.json`).
**3.3 re-runs after polish with `--freeze-structure`.** Do not retag
headings, wrap landmarks, or promote checklists — those moves undo 2.3
type and layout (Pitfall #196). SEO head is scrape-only: title /
description / OG / Twitter / canonical / favicon stay from the live
scrape or stay omitted with a skipped receipt.

Do **not** invent skip-links or peeking chrome (Pitfall #81).
Do **not** invent marketing meta.
Do **not** run type-align mutation or `apply-library-classes.py`.
Do **not** touch hover states already authored earlier in the run.

## Board

| Id | When |
|---|---|
| **3.3 Semantics** | After 3.2, **before 3.4** (`open-human-review.py`) |

`pipeline-progress.py` id: `("3.3", "Semantics + SEO sweep")`. Scope is
SEO / a11y / lock-safe perf only — it does not touch hover states already
authored earlier in the run (A/6, 1.4, C/3.2).

**5.4** runs the same freeze-structure pass on each `rebuild/{slug}.html`
after hrefs are wired. Scrape meta is that page's live URL (or
`capture/{slug}-desktop` HTML), never the homepage `qa/scrape-meta.json`
title / description / OG. `index.html` and `index-polish.html` stay
href-only — 3.3 already did the homepage.

## Commands

```sh
# 3.3 — SEO / a11y after polish; freeze file auto-enables structure lock
python3 "$SKILLS/website-to-html/scripts/semantics_pass.py" rebuild/index-polish.html -o rebuild/index-polish.html --freeze-structure
python3 "$SKILLS/website-to-html/scripts/verify-semantics.py" rebuild/index-polish.html
python3 "$SKILLS/website-to-html/scripts/fidelity_freeze.py" verify .

# 5.5 — Astro site: routes + per-page scrape-only SEO into each page's frontmatter (BaseLayout props), then astro build
python3 "$SKILLS/website-to-html/scripts/wire-astro-routes.py" .
```

Retired: running this as a 2.2.b first sweep before a dump-era Chrome
review. 2.2.b is not a live step. Retired: 3.3 type-align mutation
(`census-type-align.py` as a fix pass) — type was signed at 2.3.
