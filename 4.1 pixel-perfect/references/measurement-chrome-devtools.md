# Measurement Playbook: Browser DOM Inspection (Live Inspectable Source)

## Browser preference (user rule)

**Live rebuild preview (localhost while building):** harness **internal preview /
Simple Browser** first (if the tool has one). **Chrome** second if preview is missing.

**Measurement / deep QA (this playbook):** **Chrome** DevTools MCP / Claude-in-Chrome
first, then Playwright Chromium. Internal preview is weaker for computed-style work.

**Forbidden for live URLs / localhost QA:** Pencil browser (`pencil_browser`).
Pencil is only for `.pen` design files.

The tool names below are written against Chrome DevTools MCP. Measurement is
programmatic DOM inspection (`getComputedStyle` / `getBoundingClientRect`), not
the DevTools UI panel. Map as:

| Step | Chrome DevTools MCP (preferred) | Claude in Chrome | Claude browser pane (last resort) |
|---|---|---|---|
| Open/navigate | `new_page` / `navigate_page` | `navigate` | `preview_start {url}` / `navigate` |
| Set viewport | `resize_page` | `resize_window` | `resize_window` |
| DOM snapshot | `take_snapshot` | `read_page` | `read_page` |
| Screenshot | `take_screenshot` | `computer {action:"screenshot"}` | `computer {action:"screenshot"}` |
| Evaluate JS (all measurement) | `evaluate_script` | `javascript_tool` | `javascript_tool` |
| Console errors | `list_console_messages` | `read_console_messages` | `read_console_messages` |

If none of these are available, fall back to a local Playwright script
(`page.evaluate` for the same JS) — do not fall back to eyeballing screenshots
or Pencil.

## Preconditions
1. Source is live and inspectable.
2. Target viewport set is already selected.

## Procedure
1. Open or navigate to the source with `mcp__chrome-devtools__new_page` or `mcp__chrome-devtools__navigate_page`.
2. Set target viewport with `mcp__chrome-devtools__resize_page`.
3. Wait for stable DOM/render state before measurement and capture (stable capture contract).
   - Ensure initial loading has completed.
   - Ensure no visible layout shifts are occurring.
   - Take two consecutive observations of scrollY + target bounding box; proceed only when they match and images report complete.
   - Verify target identity (id, text, or landmark) in the same observation used for the screenshot. Never infer position from the requested scroll target alone.
4. Capture a page snapshot with `mcp__chrome-devtools__take_snapshot` to identify major containers/components.
5. Capture baseline screenshots for full viewport and major sections with `mcp__chrome-devtools__take_screenshot`.
6. Measure geometry using `mcp__chrome-devtools__evaluate_script` with `getBoundingClientRect`.
   - Record `x`, `y`, `width`, `height`.
   - Record parent-child offsets.
7. Measure styling using `mcp__chrome-devtools__evaluate_script` with `getComputedStyle`.
   - Typography: family, size, weight, line-height, letter-spacing, color.
   - Visual: background, gradient, border, radius, shadow, opacity.
8. Measure spacing rules.
   - Margins, padding, and inter-element gaps.
   - Alignment and distribution rules.
9. Measure behavior-related layout factors.
   - Scroll behavior.
   - Sticky/fixed positioning.
10. Capture section-level screenshots for dense or fragile areas.
11. Build the measurement spec from measured values before coding.

## Required Measurement Record (minimum fields)
- `element_id`
- `selector`
- `x`, `y`, `width`, `height`
- `margin` / `padding` / `gap`
- `typography`
- `colors` / `borders` / `radius` / `shadows`
- `positioning_behavior`
- `notes`

## Notes
1. Prefer measured DOM/computed values over visual estimates.
2. If a value appears inconsistent, re-measure before implementing.
3. Use the latest snapshot before element interactions to avoid stale `uid` references.

Normative rules:
1. Measurements MUST use DOM/computed values when available.
2. Inconsistent values SHOULD be re-measured before implementation.
