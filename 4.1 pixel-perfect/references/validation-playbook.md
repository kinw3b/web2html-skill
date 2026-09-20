# Validation Playbook

## Validation Sequence
1. Select validation profile (`lenient`, `portable`, `strict`, `ultra`) using skill rules.
2. Confirm validation artifact priority.
3. Run validation at every required viewport.
4. Wait for stable DOM/render state using the two-observation capture contract, then capture full screen and major sections at each viewport. Match viewport sizes exactly.
5. Compare implementation vs reference and compute required metrics.
6. For geometry tables, populate `actual` only via fresh rendered-DOM extraction and run `scripts/section-audit.mjs` (provenance gate).
7. Resolve marked issues with explicit statuses and stable regression IDs when used in website-to-html Step 7.
8. Report pass/fail per viewport and overall status.
9. Refine until all required thresholds pass.
10. Do not treat mobile as compressed desktop — re-measure stacking, reordering, sticky, and menus at each breakpoint.

## Canonical Tooling
Use the script `../scripts/validate-visual.sh` as the canonical metric computation path.
Use `../scripts/summarize-validation.sh` as the canonical projection path for LLM-facing updates.

Dependencies:
- ImageMagick CLI:
  - `magick` (v7), or
  - `convert` + `compare` + `identify` (v6)
- `jq`
- `bash`

Run pattern:
```bash
./scripts/validate-visual.sh \
  --reference /path/to/reference.png \
  --implementation /path/to/implementation.png \
  --profile strict \
  --sections /path/to/sections.json \
  --text-checks /path/to/text_checks.json \
  --spacing-checks /path/to/spacing_checks.json \
  --color-checks /path/to/color_checks.json \
  --output /path/to/report.json
```

Minimal run (global metric only):
```bash
./scripts/validate-visual.sh \
  --reference /path/to/reference.png \
  --implementation /path/to/implementation.png \
  --profile strict
```

Projection run (compact LLM-facing summary):
```bash
./scripts/summarize-validation.sh \
  --report /path/to/report.json \
  --mode iteration \
  --format md
```

Projection rule:
1. Validator JSON is the source of truth.
2. Iteration updates SHOULD use summary projections (failed checks + deltas only).
3. Full-fidelity report sections are still required for final handoff.

## Validation Artifact Priority
When user-marked comparison screenshots are provided:

1. They MUST be treated as primary validation artifacts.
2. Marked issues MUST be explicitly tracked and resolved.
3. Generic visual impression SHOULD only be used as supplemental context.

## Portable Strictness
`portable` mode:

1. MUST allow renderer-level drift only.
2. MUST NOT relax annotated design decisions from the `Must-match list`.

## Input Schemas
`sections.json`
```json
[
  {"id":"header","x":0,"y":0,"width":390,"height":88},
  {"id":"balance_card","x":20,"y":112,"width":350,"height":164}
]
```

`text_checks.json`
```json
[
  {"id":"header_title_baseline","reference":54,"implementation":55}
]
```

`spacing_checks.json`
```json
[
  {"id":"header_to_card","reference":24,"implementation":25}
]
```

`color_checks.json`
```json
[
  {"id":"text_primary","x":36,"y":140}
]
```

## Metric Computation Rules
The script computes and reports these metrics:

1. Global pixel difference
- Diff pixels: `AE(reference, implementation)` from ImageMagick compare.
- Percentage: `(diff_pixels / total_pixels) * 100`.

2. Per-section pixel difference
- Crop each section box from both images.
- Diff pixels: `AE(reference_crop, implementation_crop)`.
- Percentage: `(section_diff_pixels / section_pixels) * 100`.

3. Text drift (baseline or text-block)
- For each text check item: `abs(reference - implementation)` in pixels.

4. Spacing drift
- For each spacing check item: `abs(reference - implementation)` in pixels.

5. Color deltaE checks
- Sample pixel at `(x, y)` in both images.
- Convert RGB to Lab.
- Compute CIE76 deltaE.

## Dynamic Region Handling
If a region cannot be stabilized (for example live clocks, tickers, or remote dynamic content):

1. Document the region explicitly with coordinates and reason.
2. Exclude that region from metric computation inputs (`sections.json`, `text_checks.json`, `spacing_checks.json`, `color_checks.json`).
3. Keep the same validation profile; do not downgrade profile strictness because of dynamic regions.

For data-driven screens:

1. Copy/content differences SHOULD be excluded unless they affect layout, spacing, overflow, or wrapping.
2. Every exclusion MUST be listed in the `Ignore list`.

## Required Metrics
- Global pixel difference
- Per-section pixel difference
- Key text baseline or text-block drift
- Key spacing deltas
- Key color deltaE checks

## Profile Thresholds

### lenient
- Global: `<= 3.5%`
- Per-section: `<= 2.5%`
- Text drift: `<= 3px`
- Spacing drift: `<= 2px`
- Color deltaE: `<= 4`

### portable
- Global: `<= 1.5%`
- Per-section: `<= 1.0%`
- Text drift: `<= 2px`
- Spacing drift: `<= 1px`
- Color deltaE: `<= 2.5`

### strict
- Global: `<= 0.8%`
- Per-section: `<= 0.5%`
- Text drift: `<= 1px`
- Spacing drift: `<= 1px`
- Color deltaE: `<= 1.5`

### ultra
- Global: `<= 0.4%`
- Per-section: `<= 0.25%`
- Text drift: `<= 0.5px`
- Spacing drift: `<= 0.5px`
- Color deltaE: `<= 1.0`

## Reporting Rule
For each required viewport, report:
1. Measured values
2. Thresholds used
3. Pass/fail result
4. Top mismatches and next action

The script output JSON is the source of truth for numeric values.
Iteration-mode updates SHOULD reference projection output and avoid reprinting unchanged passing details.

## Component-Property Validation Table
For each required viewport, the report MUST include a component-property validation table.

Required columns:

- `component`
- `property`
- `desired_value`
- `actual_value`
- `drift`
- `result`
- `reason`

Result values:

- `good`
- `bad`
- `bad_with_reason`

Rules:

1. `reason` is required when result is `bad_with_reason`.
2. `drift` MUST be explicit (numeric or clearly bounded textual drift if numeric is not possible).
3. Properties that drive must-match design decisions SHOULD be represented as rows in this table.
4. `actual_value` MUST be sourced from rendered DOM after the latest edit — never copied from desired. Prefer serializing rows into `geometry.json` and running `node scripts/section-audit.mjs <file>` so provenance (`source.kind=rendered-dom`, `capturedAt`, viewport) is machine-checked.
5. One row per independently styled component; do not validate a family via a single representative unless every instance was measured identical.

## Marked-Issue Resolution Protocol
Each marked issue MUST end in exactly one status:

- `fixed`
- `accepted_by_user`
- `renderer_only_drift`

Rules:

1. `renderer_only_drift` MUST include a brief reason.
2. The validation report MUST include a yes/no checklist item for each marked issue.
3. A report MUST NOT claim `validated` unless every marked issue has a final status.

## Validation Freshness and Final Loop
1. A report MUST NOT claim `validated` if it predates the latest visual changes.
2. At least one full `capture -> compare -> fix -> re-capture` loop MUST occur after the last substantive UI edit.
