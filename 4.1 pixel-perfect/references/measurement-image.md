# Measurement Playbook: Image (Screenshot-Only Source)

## Preconditions
1. Source is an image or frame without inspectable DOM.
2. Target viewport set is selected or estimated.

## Procedure
1. Use the source image dimensions as the coordinate space.
   - Treat image as `0..W` by `0..H` pixels.
   - Record `W` and `H` in the report.
2. Build an initial region map.
   - Mark major containers (header, cards, sections, footer).
   - Mark text blocks and icon regions.
   - Mark repeated rows/components.
3. Measure geometry with pixel coordinates.
   - For each major element, record `x`, `y`, `width`, `height`.
   - Compute gaps from coordinate differences.
   - Compute container padding from child-to-parent insets.
4. Sample color values from pixels.
   - Sample from flat interior regions, away from anti-aliased edges.
   - For gradients, sample at least start/mid/end points.
   - Record sampled colors as hex (optional RGB).
5. Derive typography from measurable text blocks.
   - Measure text block boxes for width/height.
   - Estimate line height from line spacing when multiline text exists.
   - Infer hierarchy from repeated label/value patterns.
6. Handle baseline carefully.
   - If baseline is not reliably measurable, use text-block top/center drift.
   - Record method per key text element.
7. Label every value with confidence.
   - `measured`: direct pixel-coordinate or sample read.
   - `estimated`: inferred from pattern when direct measurement is unreliable.
8. Do not use LLM-only visual estimates as final numeric values.
   - LLM vision may propose structure.
   - Final values must come from pixel-coordinate measurements and sampling.
9. Refine iteratively.
   - Implement first pass.
   - Compare screenshots against source.
   - Update measurement table and repeat.

## Required Measurement Record (minimum fields)
- `element_id`
- `x`, `y`, `width`, `height`
- `spacing_to_prev` / `padding_in_parent`
- `color_samples`
- `typography_notes`
- `baseline_method`
- `confidence` (`measured` or `estimated`)
- `notes`

Normative rules:
1. Final numeric values MUST NOT rely on LLM-only visual estimation.
2. Confidence tags (`measured` or `estimated`) MUST be present for each critical value.
