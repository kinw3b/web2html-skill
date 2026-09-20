# Responsive Scope Playbook

## Selection Rules
1. If the user specifies viewports/devices, they MUST be used exactly as specified.
2. If unspecified, classify source and use default set.
3. Classification and selected viewport set MUST be recorded in the plan before coding.
4. All required viewports MUST pass validation.

## Source Classification
1. Use `web-responsive` when structure changes with width.
   Examples: nav collapse, column count changes, major reflow.
2. Use `web-fixed` when structure appears fixed-size and does not reflow.
3. Use `mobile-adaptive` when adaptive behavior is visible or requested.
4. Otherwise use `mobile-nonadaptive`.

## Default Viewport Sets
- `web-responsive`: `390x844`, `768x1024`, `1280x800`, `1920x1080`
- `web-fixed`: reference viewport + `1920x1080`
- `mobile-nonadaptive`: one canonical viewport
- `mobile-adaptive`: one phone viewport + one larger-class viewport

## Canonical Mobile Viewports
- iOS phone: `390x844`
- Android phone: `412x915`
- iOS larger class: `1024x1366`
- Android larger class: `1280x800`

## Deviation Handling
If you deviate from defaults, document:
1. What changed
2. Why it changed
3. Who requested/approved it
