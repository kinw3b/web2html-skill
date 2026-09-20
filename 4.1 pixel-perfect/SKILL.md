---
name: pixel-perfect
description: >-
  Reproduce a UI as exactly as possible from a reference (Figma, live source, screenshot, or image).
  TRIGGER when: user wants to copy a design exactly, reproduce a screen from a screenshot, clone a
  Figma design, match spacing/colors/typography in detail, port a design to another framework
  without changing the look, or web2html / website-to-html 2.3 as a one-pass assist (disk-clip gold).
  DO NOT TRIGGER for redesigns, loose "something like this" requests, or UX improvement tasks.
---

# pixel-perfect

A skill for reproducing a UI as exactly as possible from a screenshot, image, Figma preview/export, clickable demo, or live website.

The result is not just code. The result is:

- a measurement-based implementation plan
- a detailed visual specification
- the code that implements that specification
- an iterative validation loop until the rendered result matches the reference closely

This skill is for exact copying, not for inspiration, redesign, cleanup, normalization, or stylistic interpretation.

## When to use this skill

Use this skill when the user wants to:

- copy a design exactly
- reproduce a screen from a screenshot
- clone a Figma site or demo accurately
- match spacing, padding, colors, typography, and layout in detail
- port a design into another framework without changing the look

## FIDELITY LOCK — website-to-html / web2html 2.3

When 4.1 pixel-perfect is called from website-to-html / web2html **2.3**, it is
a **one-pass assist**, not the 2.3 driver, not a from-scratch rebuild, and not
a 3.x polish pass. The driver is
`web2html/references/section-23-paper-loop.md`. Follow that file.

1. You are called for **one** homepage section, after that worker already
   MEASURED from disk. Widths: **1600 / 768 / 390** only. Do not invent 1024 / 1320.
2. **Disk gold** is the 1.2 source-section PNGs plus `rebuild/index-raw.html`.
   Do not call Paper MCP (`get_computed_styles` / `get_screenshot` /
   `get_guide`). Not the live URL, not Figma, not `source-site/screenshots/`.
   The worker already wrote `qa/paper-measure/<id>.json` — do not restyle
   without those numbers.
3. **Actual** is `file://` `rebuild/index.html` via
   `paper_23_rebuild_shots.py`. Never a local HTTP server. Propose a patch
   for this section; do not write `rebuild/` yourself.
4. Check **only** the watch list: layout, line-height, typography, layout
   shifts, geometry, missing icons, button/card radius, imagery,
   `position: absolute` floating infographics, 2.2 hallucinations.
5. **Cap: 1 compare + 1 fix.** Then stop. Do not run a refine loop. Do not
   write a 10-section spec. Do not ask the user to verify.
6. Gate receipts stay `qa/paper-measure/_index.json` + `section_22_gate.py`.
   Do not substitute this skill's `validation/*.json` for those receipts.

**STOP — in-pipeline 2.3 callers.** If website-to-html / web2html 2.3 called
you, do not read or apply the standalone studio body below. Do not take an
aesthetic risk. Do not open TAGS (that is 2.4). Do not load this skill in
3.x. One pass on this section, then return. Do not walk the rest of the page.

Do not use this skill when the user wants:

- a redesign
- a design critique
- a looser "something like this" implementation
- UX improvements instead of replication

## Prerequisites

- Browser tooling (see `~/AGENTS.md`):
  - **Live rebuild preview:** harness **internal preview / Simple Browser** first;
    **Chrome** if preview is missing
  - **Measurement / deep QA** (`getComputedStyle` / boxes): **Chrome** DevTools MCP
    or Claude-in-Chrome first; Playwright Chromium fallback
  - See `references/measurement-chrome-devtools.md`
  - **Never** use **Pencil browser** (`pencil_browser`) for live sites or rebuild QA — Pencil is for `.pen` design files only
- Command-line tools:
  - `jq`
  - `awk`
  - ImageMagick: `magick` (v7) or `convert` + `compare` + `identify` (v6)

## How to use this skill

Use this skill as a strict execution loop:

1. measure the reference once and create a concrete specification
2. implement from that specification
3. verify against the reference artifacts
4. modify only the mismatched areas
5. verify again

Repeat steps 3 to 5 until every required issue is resolved (`fixed`, `accepted_by_user`, or `renderer_only_drift`) and the validation gates pass.

## Core rules

1. The reference is ground truth.
2. Do not redesign.
3. Do not simplify.
4. Do not "improve" the design.
5. Do not replace measured values with rounded or nicer values unless explicitly asked.
6. Do not substitute theme defaults for measured colors, font sizes, spacing, radius, or shadows.
7. If the source is inspectable, measure it.
8. Always finish with screenshot-based visual validation.
9. Do not stop at "close enough" if obvious differences remain.
10. Prefer fidelity over framework convention.
11. Stable capture: two consecutive observations must agree on scroll + target bbox before any screenshot; verify identity in the same observation; never label from the requested scroll target alone.
12. `actual` values MUST come from a fresh rendered-DOM extraction (`source.kind=rendered-dom`); never copy desired into actual. Run `scripts/section-audit.mjs` on geometry JSON.
13. Share tokens only when measurements prove components are identical.
14. Never call the result pixel-perfect if a required check failed or lacks current evidence.

## Normative terms

- `MUST` and `MUST NOT` are hard requirements.
- `SHOULD` is a strong default that may be overridden only with explicit justification in the report.

## Priority order

When tradeoffs must be made, prioritize in this order:

1. overall layout structure
2. outer margins and section spacing
3. inner padding and gaps
4. typography, font size, weight, line height
5. colors, borders, radius, shadows
6. asset parity for fonts and icons
7. icon size and placement
8. interaction states and minor details

## Input preference order

Accepted input types in priority order:

1. Figma inspectable source
2. live website
3. clickable demo
4. image export
5. screenshot

Rules:

- use the highest-priority available source as the primary measurement source
- use lower-priority sources only as supplemental visual confirmation when needed
- use runtime sources for behavior and state confirmation when those details are not represented in Figma
- if only one source is provided, use that source

## Required output

This skill must produce four things during execution:

1. a short execution plan
2. a detailed measurement-based UI specification
3. the implementation in code
4. validation results and remaining mismatches, if any

The agent must not jump straight into coding without first creating the specification.

Use the report heading schema in `references/report-template.md`.

Use two reporting modes:

- `iteration` mode during refine loops (compact summary projection, changed/failing items only)
- `final` mode at completion handoff (full-fidelity report)

Do not enforce fixed token limits. Keep intermediate output concise by using artifact projections instead of repeating full report content.

When the agent believes the task is complete, it MUST provide a final user-verification handoff that includes all of the following:

1. an explicit statement that it believes the implementation is done
2. a side-by-side visual comparison showing:
   - one image of the reference/design
   - one image of the actual rendered app
3. a direct request for user verification that asks whether anything is still missing
4. an explicit prompt to list missed details if the user does not approve

## References

Use these references for detailed execution guidance:

- `references/report-template.md`
- `references/responsive-scope-playbook.md`
- `references/measurement-playbook.md` (index)
- `references/measurement-chrome-devtools.md`
- `references/measurement-image.md`
- `references/measurement-figma.md`
- `references/specification-playbook.md`
- `references/validation-playbook.md`
- `references/stable-capture-contract.md`
- `references/geometry-provenance.md`
- `references/region-manifest.md`
- `references/asset-ledger.md`
- `references/state-artifacts.md`
- `scripts/section-audit.mjs` — provenance-gated geometry audit

## Workflow

### Phase 1, identify source type

Determine which of these applies:

- live inspectable source
- Figma inspectable source
- static visual source only

If there is a live inspectable source, use that as the primary measurement source.
If there is a Figma inspectable source, use Figma inspect data as the primary measurement source.
If there is only an image, use screenshot-based measurement.

Source selection MUST follow the Input preference order.
Lower-priority sources SHOULD be used only as supplemental confirmation unless no higher-priority source is available.

### Phase 2, select responsive validation scope

Select required viewports before implementation starts.
Use the deterministic scope and classification rules in `references/responsive-scope-playbook.md`.

Minimum requirements:

- if the user provides explicit viewports or devices, use exactly those
- otherwise classify source and choose the default viewport set from the playbook
- source classification, selected viewport set, and selection reason MUST be recorded in the plan
- validation MUST pass at every required viewport in the selected set
- any deviation from defaults MUST be explicitly justified in the report

### Phase 3, inspect and measure

#### Mode A, live inspectable source

Use browser tooling such as Chrome DevTools MCP to inspect the rendered UI directly.
Use the exact measurement sequence in `references/measurement-chrome-devtools.md`.

Measure and record:

- viewport size
- page width and visible content width
- safe area or browser insets if relevant
- bounding boxes of key elements
- x and y positions relative to parent and viewport
- width and height of sections and controls
- padding on all sides
- margins on all sides
- layout gaps between siblings
- computed font family
- computed font size
- computed font weight
- computed line height
- letter spacing if relevant
- text color
- background color
- gradients
- border width
- border color
- border radius
- box shadow
- opacity if used
- icon size
- alignment rules
- scroll behavior
- sticky or fixed positioning, if present

Also capture screenshots of:

- full viewport
- each major section
- each area with dense visual detail

**Stable capture (mandatory):** before each region shot, require two consecutive
observations agreeing on scrollY + target bounding box, with images complete;
verify target identity in that same observation; label only after verify. See
`references/stable-capture-contract.md`.

Do not eyeball values from the screenshot first if the DOM can be inspected.
Measure first.

#### Mode B, screenshot or image only

When the design is only available as an image, infer structure and measure visually.
Use the screenshot-only procedure in `references/measurement-image.md`.

Determine:

- target viewport size, or estimate it
- main layout containers
- relative spacing between sections
- padding inside cards and containers
- text hierarchy
- likely font size relationships
- approximate border radius
- approximate icon sizes
- color samples from pixels
- gradient stops when visible
- alignment pattern and grid rhythm

Use repeated screenshot comparison during implementation to refine uncertain values.

#### Mode C, Figma source

When the source is a Figma preview or file with inspect access, measure from Figma inspect data.
Use the Figma procedure in `references/measurement-figma.md`.

Measure from inspect values first, then use exported or captured frame images for visual confirmation.

### Phase 4, write the execution plan

Before writing the detailed specification, write a concise execution plan.

This plan MUST include:

- source type
- measurement approach
- implementation target
- validation approach
- known risks or uncertainties

Example:

```
Source: clickable demo
Measurement: Chrome DevTools MCP DOM inspection plus screenshots
Target: React Native screen on iPhone-sized viewport
Validation: simulator screenshots matched against reference
Risk: native font rendering may differ slightly from browser rendering
```

Keep the plan short. It is an execution plan, not the full specification.

### Phase 5, write the detailed implementation specification

Create a measurement-based UI spec before coding.

The specification must be concrete enough that another engineer could implement the screen without seeing the original reference.
Use the field-level schema and quality checks in `references/specification-playbook.md`.

Phase 5 concept:
- produce a complete, measurement-driven implementation contract before coding

Required sections:

1. `Screen metadata`: defines target environment and global layout behavior.
2. `Component hierarchy`: defines structural tree and naming used across implementation and validation.
3. `Section-by-section measurements`: defines geometry, spacing, alignment, and surface styling per major section.
4. `Typography spec`: defines exact text rendering rules for key text elements.
5. `Color palette`: defines concrete color values and gradients used by the screen.
6. `Border and radius spec`: defines borders, corner radii, and divider treatments.
7. `Iconography spec`: defines icon asset, size, placement, and style details.
8. `Asset parity + user decisions`: records font/icon availability and user-approved fallback decisions.
9. `Interaction and state notes`: defines visible state-dependent styling/layout behavior.
10. `Platform translation notes`: documents renderer translation constraints without redesign.

For required fields and example outputs for each section, use `references/specification-playbook.md`.
All 10 required specification sections MUST be present before implementation starts.

### Phase 6, acceptance contract (mandatory before implementation)

Before implementation starts, the report MUST include an acceptance contract with:

- `Must-match list`: annotated design decisions that are non-negotiable
- `Ignore list`: explicitly allowed mismatches
- `Portable-allowed drift`: renderer-only drift allowances

Rules:

- implementation MUST NOT start before this contract is recorded
- if user-marked comparison screenshots are provided, those annotations MUST be reflected in the `Must-match list`
- if the screen is data-driven, copy/content mismatches SHOULD be excluded unless they affect layout, spacing, overflow, or wrapping
- all exclusions MUST be explicitly listed in the `Ignore list`

### Phase 7, implement from the specification

Write code using the specification as the source of truth.

Rules:

- implement one section at a time
- use explicit values
- avoid framework defaults when they change the appearance
- do not normalize arbitrary measured values into a spacing scale
- do not replace actual colors with nearby theme colors
- do not change font sizes to "more standard" values
- do not make buttons more balanced or modern
- do not remove or add detail
- do not auto-select fallback fonts or icon packs when exact assets are missing
- implement fallback assets only after explicit user approval is recorded in the specification
- if the reference uses a recognizably different icon family, you MUST either adopt that icon family or obtain explicit user approval before substantial implementation

If the source uses odd values such as 23px or 18px, keep them.

### Phase 8, run and capture

Run the implementation in the correct target environment.

Use the environment setup defined in the execution plan. Do not switch target environment during validation.

Run checklist:

- confirm the target type from the plan (`web`, `react-native`, or other declared target)
- start the target in a stable run mode suitable for screenshot capture
- ensure target fonts and icon assets match the approved asset parity decision
- disable animations/transitions before capture when possible to reduce frame variance
- set each required viewport exactly as declared in the plan
- capture all required screenshots for each viewport

For each required viewport in the selected viewport set, capture screenshots of:

- the full screen
- each major section
- any area that visually differs from the reference

Use the exact viewport size declared in the plan for each pass.
Viewport sizes MUST match the plan exactly.
Required screenshots for each viewport MUST be captured.

Artifact output requirements:

- for each viewport, save capture artifacts and validation input files to disk
- for each viewport, run `./scripts/validate-visual.sh` and save JSON output (for example `validation/<viewport>.json`)
- when recording component geometry desired/actual tables, write `validation/<viewport>-geometry.json` with `source.kind=rendered-dom` and run `node ./scripts/section-audit.mjs` — zero critical failures required
- treat validator JSON artifacts as the numeric source of truth

### Phase 9, visual validation

Compare the implementation screenshots against the reference for each required viewport.

Check specifically for:

- top spacing
- horizontal page padding
- card width
- section spacing
- inner card padding
- text size differences
- text weight differences
- line-height differences
- incorrect colors
- overly rounded or insufficiently rounded corners
- shadow mismatch
- button height mismatch
- icon placement mismatch
- row density mismatch
- alignment drift

Also run objective diff checks and record numeric results.
Use the validation flow and reporting format in `references/validation-playbook.md`.
For LLM-facing updates, first project validator artifacts into a compact summary with `./scripts/summarize-validation.sh`.

Validation profiles:

- `lenient` (allowed only when explicitly justified)
- `portable` (default for cross-renderer work)
- `strict` (default for same-renderer work)
- `ultra` (opt-in only, never default)

Profile selection rules:

- use `strict` by default when source and target use effectively the same renderer and font stack
- use `portable` by default when source and target render differently, such as browser to React Native
- use `ultra` only when the user explicitly asks for it and conditions are controlled (same renderer version, same OS, same DPR, same fonts, same capture pipeline)
- use `lenient` only when hard constraints prevent higher-fidelity matching; record the exact blocker and why higher profiles are not achievable

Portable interpretation:

- `portable` MUST allow only renderer-level drift
- `portable` MUST NOT relax annotated design decisions in the `Must-match list`

Validation artifact priority:

- if user-marked comparison screenshots are provided, they MUST be treated as primary validation artifacts
- generic visual impression SHOULD be used only as supplemental context

Marked issue resolution:

- every marked issue MUST end in exactly one status: `fixed`, `accepted_by_user`, or `renderer_only_drift`
- the validation report MUST include a yes/no checklist entry for each marked issue
- the validation report MUST include a component-property table with columns: component, property, desired value, actual value, drift, result, reason
- each table row result MUST be one of: `good`, `bad`, `bad_with_reason`
- `renderer_only_drift` MUST include a brief reason
- a report MUST NOT claim `validated` unless all marked issues have one of the required statuses
- a report MUST NOT claim `validated` if it has not been updated after the latest visual changes

For every run, report the selected profile and why it was selected before reporting metrics.
For every run, report viewport-level metrics for every required viewport.

LLM input projection rules:

- during iterative loops, provide the model only the projection summary (failed checks, top drifts, deltas, and next actions)
- do not re-feed full validation JSON unless a targeted slice is required to resolve a specific mismatch
- when additional detail is needed, load only targeted slices (single viewport, single issue id, or specific check type)

### Phase 10, refine

Adjust the code to remove visible mismatches.

If a mismatch reveals the specification was incomplete or wrong, update the specification.

Repeat:

- implement
- run
- capture
- compare
- refine

until obvious differences are gone or a hard platform limitation blocks perfect replication.

At least one full `capture -> compare -> fix -> re-capture` loop MUST occur after the last substantive UI edit.
The refine loop MUST run at least once and MUST NOT run more than 10 times.

If unresolved mismatches remain after 10 loops, the report MUST include a detailed unresolved section with:

- each unresolved issue
- current desired vs actual state
- what was tried
- why the issue is hard to fix
- whether it is likely renderer-only, asset-limited, data-limited, or implementation-limited
- the recommended next action for each unresolved issue

If blocked, document the limitation and the remaining discrepancy.

Iteration reporting rules:

- each refine loop MUST produce an `iteration` report block from projection output
- iteration report SHOULD include changed statuses and failing rows only
- full report sections and exhaustive tables are required only in the `final` report mode at handoff

## Definition of done

The skill is done only when all of the following are true:

1. A concise execution plan exists.
2. A detailed measurement-based UI specification exists.
3. The UI is implemented in code.
4. The rendered output has been compared visually to the reference.
5. A validation profile is selected using the profile selection rules and is recorded in the report.
6. Objective validation metrics are recorded and all required thresholds pass for the selected profile.
7. If `lenient` is used, the blocker and reason are explicitly documented.
8. Asset parity status for fonts and icons is documented, and any fallback usage has explicit user approval recorded.
9. The acceptance contract exists and includes `Must-match list`, `Ignore list`, and `Portable-allowed drift`.
10. If user-marked comparison screenshots are provided, they are used as the primary validation artifact.
11. Every marked issue is resolved as `fixed`, `accepted_by_user`, or `renderer_only_drift` with reason.
12. The validation report is updated after the latest visual changes.
13. At least one full `capture -> compare -> fix -> re-capture` loop has run after the last substantive UI edit.
14. The validation report includes a component-property table with desired value, actual value, drift, and result for each validated property.
15. All required viewports in the selected viewport set pass validation.
16. No obvious mismatches remain in spacing, typography, colors, border radius, alignment, or section sizing.
17. The final response includes an explicit "I believe this is done" statement.
18. The final response includes side-by-side reference and actual-app images for user review.
19. The final response asks the user to verify completion and, if not complete, to specify what was missed.

"Roughly similar" is not done.
"Good enough" is not done.
"Framework-idiomatic but slightly different" is not done.

## Failure modes to avoid

Do not do any of the following:

- implement from memory after a quick glance at the design
- skip the specification
- use generic spacing like 16 everywhere because it feels right
- use default font sizes because they are close
- replace measured colors with theme colors
- auto-pick font or icon fallbacks without user approval
- claim validation using a stale report from before the latest visual changes
- ignore marked comparison screenshot issues without resolving them as `fixed`, `accepted_by_user`, or `renderer_only_drift`
- make subjective UX improvements
- (standalone) stop after the first pass on a section
- (web2html 2.3) run more than one compare+fix pass, walk every homepage section yourself, or write `rebuild/`
- declare success without screenshot comparison
- (standalone) end without explicit user verification request and missed-detail prompt

## Example invocation phrases

```
Use pixel-perfect to copy this screen exactly
Use pixel-perfect to recreate this Figma preview in React Native
Use pixel-perfect to clone this clickable demo without redesigning it
Use pixel-perfect to port this web design into native while preserving the look
```

## Expected behavior summary

This skill turns a vague prompt like "copy this design" into a strict process:

- inspect the source
- measure the source
- write a plan
- write a detailed specification
- implement from the specification
- run the target
- capture screenshots
- compare against the reference
- refine until matched

This skill does not ask the agent to be creative. It asks the agent to be precise.
