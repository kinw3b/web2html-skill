> **RETIRED as a dump-era promote companion.** Gold is Paper 1600 / 768 /
> 390 in the 2.3 section loop, not a geometry-lock + Tailwind size fence.
> Do not retag a lock dump.

# Visual alignment / typography QA — website-to-html companion

Semantic retag (`div`/`p` → `h1`–`h6`) lets **UA heading styles** win:
`text-align: start`, different size/weight. Alignment often lived on a
parent flex (`justify-center` / `text-center`), not the text node.
Catch it at promote time, then prove it with a computed-style QA.

Gold is **lock alignment + Tailwind size tokens**. The skill does
not lock fonts. Never a site-specific ID list.

## What we refused from an external review

Gemini's feminine QA is a **fidelity fail**. Do not copy it into the
skill or any other template.

| Refused | Why |
|---|---|
| `qa/fix-typography-inline.py` stamps every `h1`/`h2` with a site face, 48px, letter-spacing `-1.5px`, line-height `55.2px` | Site paint, not a pattern. The skill does not lock fonts. |
| Hardcoded center/left ID list (`#mission-heading` center, `#hero-heading` left, …) | One lifestyle page's ids are not gold. |
| `qa/verify-visual-alignment.mjs` asserting a site face + those IDs | Same. Playwright at 1600/768/390 is useful; the gold is align + size. |
| Hardcoded user-specific skill path | Resolve from `$SKILLS/url-to-paper` or hover-reel. |
| Any baked face list / `fontFamily` assert in this skill | Fonts stay per-project (Pitfall #88/#89). This QA does not lock or assert faces. |
| `--text-display` | Type sizes snap to Tailwind `--text-xs`…`--text-12xl` only (Pitfall #66). |
| Assume every title is centered | `text-align` comes from the lock node’s style/class **or** the immediate text-column parent. Never assume center. |

Do **not** write Paper. Do **not** write hotelsix / techty / feminine
rebuild HTML or CSS to “fix” this.

## Board

Fold into existing steps. **No new board id.**

| Id | When |
|---|---|
| **2.2.b** | After heading / semantics promote. Census lock (or ship) → `qa/type-align-census.json`. Verify if Playwright is present. |
| **3.3** | **Do not re-run as a fix pass.** Type was signed at 2.3. 3.3 is SEO/a11y with `--freeze-structure`. `fidelity_freeze.py verify` catches font-size drift. |
| **verify-polish** | Soft: fail only when Playwright ran and checks failed. Missing Chrome / Playwright = skip receipt, do not crash the semantics gate. |

`open-build-review.py` (2.2.b initial and 2.2.e final) does **not** require Playwright.

## Commands

```sh
# After 2.2.b heading / semantics promote
python3 "$SKILLS/website-to-html/scripts/census-type-align.py" rebuild/index.html
node "$SKILLS/website-to-html/scripts/verify-visual-alignment.mjs" rebuild/index.html

# 3.3 — same pair after polish
python3 "$SKILLS/website-to-html/scripts/census-type-align.py" rebuild/index.html
node "$SKILLS/website-to-html/scripts/verify-visual-alignment.mjs" rebuild/index.html
```

Census prefers `qa/fixtures/geometry-lock-home.html` (or
`rebuild/geometry-lock.html`) when present; otherwise the ship
`rebuild/index.html` plus class/style signals.

`verify-visual-alignment.mjs` opens `file://rebuild/index.html` at
1600×1000 / 768×1024 / 390×844. For each census row it finds the
element (id, then heading/`p` text) and reads `getComputedStyle`
`fontSize` / `textAlign`.

If Playwright is missing, it writes `qa/visual-align-qa.json` with
`skipped: true` and exits 0.

## Promote rule (heading + p)

When retagging, if the new heading/`p` would lose alignment, stamp
`text-align` from the node or parent:

- node class `text-center` / `text-left` / `text-right` / `text-start`
- inline `text-align`
- immediate text-column parent: those classes, or `justify-center` +
  a full-width title

Keep existing class + leftover style. Do **not** invent a font, px,
letter-spacing, or color.

## Census row

`{ text, tag, selector?, align, fontSize, source }`

- `fontSize` = token (`text-5xl`) snapped to `--text-xs`…`--text-12xl`
- `align` = from lock node or parent. Never a default of center
- `source` = `lock` or `ship`
- no `fontFace` — this skill does not lock fonts

No feminine IDs.

## Fail the verify when

1. `textAlign` is not in the expected family (center vs start/left vs
   right — `start≈left`, `end≈right`)
2. `fontSize` is off the token snap by more than ~1px

## Gates

- `qa/type-align-census.json`
- `qa/visual-align-qa.json`
- Pitfall #94
- Helpers: `type_align.py`, `heading_promote.retag`,
  `semantics_pass._promote_paragraphs`

## Hard locks

- Homepage only. `file://` only.
- Paper is the brief. No restyle.
- Do not copy a one-off page's feminine / lifestyle ids as gold.
- Do not make either 2.2.b or 2.2.e human review require Playwright.
