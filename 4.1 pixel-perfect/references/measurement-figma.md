# Measurement Playbook: Figma Source

## Preconditions
1. A Figma file or preview is available and the target frame is identified.
2. Figma inspect data is accessible for the target frame/components.
3. Target viewport/device for implementation is selected.

## Procedure
1. Lock target frame and variant.
   - Record page, frame name, and variant/state.
   - Record frame width/height and constraints.
2. Measure structure from frame tree.
   - Record parent/child hierarchy with stable ids.
   - Record auto-layout direction, alignment, spacing, and padding.
3. Measure geometry and spacing.
   - Record `x`, `y`, `width`, `height` for major sections/components.
   - Record margins/gaps/insets from layout metadata.
4. Measure typography.
   - Record family, size, weight, line-height, letter spacing, case, color.
   - Record text role ids for later validation mapping.
5. Measure surface styling.
   - Record fills (solid/gradient), borders, radii, shadows, opacity.
   - Record corner-by-corner radius when not uniform.
6. Measure iconography and assets.
   - Record icon source/component, size, placement, spacing.
   - Record required fonts and icon assets for parity checks.
7. Capture visual references.
   - Export or capture full-frame and section-level images for validation.
8. Convert to measurement spec.
   - Mark values as `measured` when obtained directly from Figma inspect.
   - Mark values as `estimated` only when inspect data is unavailable.

## Required Measurement Record (minimum fields)
- `element_id`
- `figma_node_id_or_name`
- `x`, `y`, `width`, `height`
- `auto_layout` (direction/alignment/spacing/padding when applicable)
- `typography`
- `fills` / `borders` / `radius` / `effects`
- `asset_requirements` (fonts/icons/components)
- `confidence`
- `notes`

## Notes
1. Prefer inspect values over visual approximation.
2. If preview and inspect disagree, treat inspect values as source of truth and confirm visually.
3. If a required asset is unavailable in target runtime, request explicit user decision per asset parity policy.

Normative rules:
1. Inspect values MUST be primary when available.
2. Asset gaps MUST trigger explicit user decision before substantial implementation.
