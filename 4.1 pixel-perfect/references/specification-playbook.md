# Specification Playbook

Use this playbook for Phase 5 to produce a concrete, implementation-ready UI specification.

## Overall Concept
The Phase 5 specification is an implementation contract.
1. It MUST allow implementation without reopening the source.
2. It MUST separate direct measurements from estimates.
3. It MUST surface unresolved risk before coding starts.

## Spec Requirements
1. Every major visible element MUST be represented.
2. Every critical value MUST be tagged as `measured` or `estimated`.
3. Every estimated value MUST have a refinement note.
4. Missing assets MUST have an explicit user decision recorded.

## Required Sections, Detailed Guidance, and Example Outputs

### 1. Screen metadata
Purpose: define target environment and global behavior.

Required fields:
- `target_viewport_or_device`
- `orientation`
- `safe_area_behavior`
- `background`
- `scroll_behavior`
- `positioning_modes`

Example output:
```yaml
screen_metadata:
  target_viewport_or_device: "390x844"
  orientation: "portrait"
  safe_area_behavior: "content starts below top inset"
  background: "#F8FAFC"
  scroll_behavior: "vertical scroll"
  positioning_modes:
    header: "static"
    cta_bar: "fixed-bottom"
```

### 2. Component hierarchy
Purpose: define screen structure and stable naming.

Required fields:
- visual tree (screen -> sections -> components)
- stable ids used across spec, implementation, and validation

Example output:
```text
Screen
 ├ Header[id=header]
 │  ├ BackButton[id=header_back]
 │  ├ Title[id=header_title]
 │  └ SettingsButton[id=header_settings]
 ├ BalanceCard[id=balance_card]
 │  ├ Label[id=balance_label]
 │  └ Amount[id=balance_amount]
 └ ActionRow[id=action_row]
    ├ SendButton[id=action_send]
    └ ReceiveButton[id=action_receive]
```

### 3. Section-by-section measurements
Purpose: define geometry, spacing, alignment, and surface styling.

Required fields per section:
- `id`
- `x`, `y`, `width`, `height` (or responsive rule)
- all margins and paddings
- `child_gap`
- `alignment`
- `border`
- `radius`
- `background`
- `shadow`
- `confidence`

Example output:
```yaml
sections:
  - id: "balance_card"
    frame: { x: 20, y: 112, width: 350, height: 164, confidence: "measured" }
    margin: { top: 24, right: 20, bottom: 0, left: 20, confidence: "measured" }
    padding: { top: 24, right: 24, bottom: 24, left: 24, confidence: "measured" }
    child_gap: { value: 8, confidence: "measured" }
    alignment: { horizontal: "start", vertical: "center", confidence: "measured" }
    border: { width: 0, color: "transparent", confidence: "measured" }
    radius: { all: 24, confidence: "measured" }
    background: { type: "gradient", from: "#5B5CE6", to: "#7A3FF2", confidence: "estimated" }
    shadow: { x: 0, y: 6, blur: 18, color: "rgba(17,24,39,0.18)", confidence: "estimated" }
    refinement_note: "Recheck gradient hue after first diff pass"
```

### 4. Typography spec
Purpose: define exact text rendering behavior.

Required fields per key text element:
- `id_or_role`
- `content_or_label_role`
- `font_family`
- `font_size`
- `font_weight`
- `line_height`
- `letter_spacing`
- `color`
- `alignment`
- `casing`
- `baseline_method`
- `confidence`

Example output:
```yaml
typography:
  - id_or_role: "balance_amount"
    content_or_label_role: "primary numeric value"
    font_family: "Inter"
    font_size: 34
    font_weight: 700
    line_height: 40
    letter_spacing: 0
    color: "#FFFFFF"
    alignment: "left"
    casing: "as-entered"
    baseline_method: "text-block-center"
    confidence: "measured"
```

### 5. Color palette
Purpose: define concrete color system used by the screen.

Required fields:
- named colors with exact values
- gradient stops + direction where applicable
- confidence tag

Example output:
```yaml
colors:
  - name: "text_primary"
    value: "#111827"
    confidence: "measured"
  - name: "accent_gradient"
    value:
      type: "linear"
      angle: 135
      stops: ["#5B5CE6", "#7A3FF2"]
    confidence: "estimated"
```

### 6. Border and radius spec
Purpose: define edges and corner treatments.

Required fields:
- border widths/colors by component type
- radius values by component type
- asymmetrical corner rules when present

Example output:
```yaml
borders_and_radius:
  card: { border_width: 0, border_color: "transparent", radius: 24, confidence: "measured" }
  button_primary: { border_width: 0, border_color: "transparent", radius: 12, confidence: "measured" }
  button_secondary: { border_width: 2, border_color: "#7A3FF2", radius: 12, confidence: "measured" }
```

### 7. Iconography spec
Purpose: define icon identity and placement details.

Required fields:
- `icon_id_or_role`
- `pack_and_glyph`
- `size`
- `placement`
- `icon_text_spacing`
- `stroke_or_fill`
- `confidence`

Example output:
```yaml
icons:
  - icon_id_or_role: "send_icon"
    pack_and_glyph: "feather/arrow-up-right"
    size: 20
    placement: "left of send label"
    icon_text_spacing: 8
    stroke_or_fill: "stroke"
    confidence: "estimated"
```

### 8. Asset parity + user decisions
Purpose: resolve missing fonts/icons before implementation.

Required fields:
- exact assets found
- availability in target environment
- fallback options shown to user
- explicit user decision
- expected visual impact

Example output:
```yaml
asset_parity:
  fonts:
    required: ["Inter-Regular", "Inter-Bold"]
    available: ["Inter-Regular"]
    unavailable: ["Inter-Bold"]
  icons:
    required: ["feather@4.29.0"]
    available: []
    unavailable: ["feather@4.29.0"]
  missing_assets: ["Inter-Bold", "feather@4.29.0"]
  options_presented:
    - "User provides exact files"
    - "Use Material Symbols fallback"
    - "Temporary placeholder icons"
  user_decision: "Approved Material Symbols fallback for now"
  expected_visual_impact: "Icon stroke differs slightly from reference"
```

### 9. Interaction and state notes
Purpose: capture state-dependent visual/layout changes.

Required fields:
- visible state list
- state-dependent style deltas
- transitions that affect measured appearance

Example output:
```yaml
interaction_states:
  send_button:
    default: { background: "gradient", text_color: "#FFFFFF" }
    pressed: { opacity: 0.92 }
  receive_button:
    default: { background: "#FFFFFF", border: "2px #7A3FF2" }
    pressed: { background: "#F8FAFC" }
```

### 10. Platform translation notes
Purpose: document renderer constraints without redesign.

Required fields:
- known mapping constraints
- explicit non-redesign rule
- known remaining renderer differences

Example output:
```yaml
platform_translation:
  target: "react-native"
  constraints:
    - "CSS blur shadows approximated via RN shadow props"
    - "Web gradient angle mapped to LinearGradient start/end"
  no_redesign: true
  known_renderer_differences:
    - "Subpixel text rasterization differs from browser"
```

## Quality Checks Before Implementation
1. Every required section exists.
2. Every major section has dimensions and spacing.
3. Every key text element has full typography fields.
4. Colors are concrete values, not theme-token guesses.
5. Unknown assets are resolved with user decision, not auto fallback.
6. Estimated values are explicitly marked and queued for refinement.
