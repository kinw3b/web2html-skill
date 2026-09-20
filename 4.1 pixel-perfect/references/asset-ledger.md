# Asset ledger

For every visual asset used in the implementation, record recovery status.
Include photographs, **embedded SVGs**, masks, icons, and **fonts** — not only raster images.

## File

`qa/asset-ledger.json` (website-to-html) or `validation/asset-ledger.json` (pixel-perfect).

```json
{
  "updatedAt": "2026-01-01T12:00:00Z",
  "assets": [
    {
      "id": "hero-bg",
      "kind": "image",
      "sourceUrl": "https://example.com/hero.webp",
      "localPath": "rebuild/images/hero.webp",
      "intrinsic": { "width": 2400, "height": 1600 },
      "rendered": {
        "width": 1280,
        "height": 720,
        "objectFit": "cover",
        "objectPosition": "50% 30%",
        "cropNotes": "top-weighted"
      },
      "status": "exact",
      "fallbackReason": null
    },
    {
      "id": "icon-check",
      "kind": "svg",
      "sourceUrl": "https://example.com/check.svg",
      "localPath": "rebuild/images/icons/check.svg",
      "intrinsic": null,
      "rendered": { "width": 24, "height": 24 },
      "status": "exact",
      "fallbackReason": null
    },
    {
      "id": "ff-display",
      "kind": "font",
      "sourceUrl": "https://fonts.example/Display.woff2",
      "localPath": "rebuild/fonts/Display.woff2",
      "intrinsic": null,
      "rendered": { "family": "Display", "weight": "700" },
      "status": "exact",
      "fallbackReason": null
    }
  ]
}
```

## Status values

| status | Meaning |
|---|---|
| `exact` | Recovered authorized source bytes / equivalent self-host |
| `fallback` | Substitute used — `fallbackReason` required |
| `missing` | Needed but not recovered — blocks “pixel-perfect” until fixed or accepted |
| `decorative-omitted` | Intentionally skipped with user/contract approval |

## Rules

1. Never substitute Unicode/generic icons when an exact source SVG/image is recoverable.
2. Every `fallback` needs a reason and should appear on the fidelity ignore/allowed-drift list if accepted.
3. Fonts: record family, weight, file path, and license/source.
4. website-to-html Step 1 / 1.5 exit: ledger seeded for all images copied and fonts self-hosted; update when paths change.
