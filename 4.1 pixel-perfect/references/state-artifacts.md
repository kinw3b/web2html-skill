# Interactive state artifacts

Behavior checklists are not enough. Capture **visually distinct** control states
as separate screenshots so Step 7 / pixel-perfect can compare them.

## Layout

```text
qa/states/
├── manifest.json
├── mobile-nav-default.png
├── mobile-nav-open.png
├── header-transparent.png
├── header-scrolled.png
├── carousel-slide-0.png
├── carousel-slide-1.png
└── …
```

## Naming

`{control-id}-{state}.png`

Examples: `mobile-nav-open`, `accordion-item-2-expanded`, `tab-pricing-active`,
`btn-primary-hover` (only if hover is visually distinct and capturable).

## manifest.json

```json
{
  "updatedAt": "2026-01-01T12:00:00Z",
  "controls": [
    {
      "id": "mobile-nav",
      "inventoryRow": "burger",
      "states": [
        {
          "name": "default",
          "file": "mobile-nav-default.png",
          "reference": true
        },
        {
          "name": "open",
          "file": "mobile-nav-open.png",
          "reference": true
        }
      ],
      "buildStates": [
        {
          "name": "default",
          "file": "build-mobile-nav-default.png"
        },
        {
          "name": "open",
          "file": "build-mobile-nav-open.png"
        }
      ]
    }
  ]
}
```

## Rules

1. Every control in the Step 4 behavior inventory / interaction-results table that
   has a **visible** state change needs default + at least one other state.
2. Sequential controls (carousel, steppers): default + **at least two transitions**.
3. Capture reference states from the live site (or source) and build states from
   localhost with the **same crop** when possible.
4. Use stable capture (two observations) before each state shot.
5. Link state names on the matching region in `qa/region-manifest.json` `states[]`.
6. `qa/interaction-results.md` rows should reference state files when present.

## When

| Pipeline | When |
|---|---|
| website-to-html | After Step 4 inventory; refresh build states in Step 5/7 |
| pixel-perfect | During measurement for any interactive reference |
