# Geometry provenance (desired vs actual)

`actual` values MUST come from a fresh rendered-DOM extraction after the latest edit. Never copy `desired` into `actual`.

## geometry.json

```json
{
  "source": {
    "kind": "rendered-dom",
    "capturedAt": "2026-01-01T12:10:00Z",
    "viewport": { "width": 1280, "height": 800 },
    "implementationRevision": "working-tree-optional"
  },
  "items": [
    {
      "id": "primary-action",
      "critical": true,
      "properties": {
        "width": { "desired": 156, "actual": 156, "tolerance": 1 },
        "height": { "desired": 52, "actual": 52, "tolerance": 1 },
        "borderRadius": { "desired": "12px", "actual": "12px", "tolerance": 0 }
      }
    }
  ]
}
```

## Audit

```bash
node scripts/section-audit.mjs validation/<viewport>-geometry.json
```

Exit code `0` only when:

1. `source.kind === "rendered-dom"`
2. `source.capturedAt` is present
3. `source.viewport.width` and `.height` are numeric
4. Every `critical` property is within tolerance

## Extraction

Populate `actual` with `getBoundingClientRect` / `getComputedStyle` in the implementation at the declared viewport. Record one item per independently styled component. Do not validate a component family through one representative unless every instance was measured and proved identical.

When border radii differ by corner, record **per-corner** properties
(`borderTopLeftRadius`, …) — do not collapse to a single `borderRadius` unless
all four match.
