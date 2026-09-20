# Region manifest contract

Create `qa/region-manifest.json` (website-to-html) or `validation/region-manifest.json`
(pixel-perfect standalone) with **one record per page-derived region and viewport**.

Use names discovered from the reference (live DOM, `data-framer-name`, landmarks).
**Do not** force a landing-page taxonomy (`hero` / `features` / `footer` only).
A page ending may be separate zones: pre-footer surface, decoration, identity,
nav grid, legal row — each its own region when visually distinct.

```json
{
  "viewport": { "width": 1280, "height": 800 },
  "capturedAt": "2026-01-01T12:00:00Z",
  "regions": [
    {
      "id": "feature-grid",
      "locator": "[data-region='feature-grid']",
      "referenceScreenshot": "qa/diffs/ref_feature-grid.png",
      "verified": {
        "scrollY": 920,
        "top": 36,
        "textSample": "Example heading"
      },
      "frame": { "x": 0, "y": 884, "width": 1280, "height": 640 },
      "layout": { "display": "grid", "overflow": "visible" },
      "surface": { "background": "#ffffff", "radius": "0px" },
      "children": ["feature-heading", "feature-item-1"],
      "states": ["default"],
      "notes": []
    }
  ]
}
```

## Rules

1. **Page-derived IDs** — `site-header`, `intro`, `content-section-1`, not a fixed template list.
2. **Per viewport** — either separate files (`region-manifest-1280.json`) or a top-level `viewport` with one file per size.
3. **Verified identity** — `verified` must come from the same observation as the screenshot (stable capture contract).
4. **Children** — internal zones listed when they are independently styled or validated.
5. **States** — list every visually distinct state this region exposes (`default`, `hover`, `open`, …). State screenshots live under `qa/states/` (see state-artifacts).
6. **Freeze notes** — if sticky/animation/lazy-load was frozen for capture, document under `notes` and in `qa/capture-interventions.md`.

## When to write

| Pipeline | When |
|---|---|
| website-to-html | Stage M (seed from scrape `sections.json`) → update through Step 7 |
| pixel-perfect | Phase 3–5 before coding; refresh after capture |

Ground truth for site rebuilds remains source screenshots + DOM; the manifest is the inventory and locator map for QA.
