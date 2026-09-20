# W3C Design Tokens Format Example

The [W3C Design Token Community Group](https://design-tokens.github.io/community-group/format/)
defines a standard JSON format for design tokens. The `design-tokens`
skill outputs both this W3C format and our Core Framework convention.

## W3C types used in `tokens.json`

| `$type` | Example value | Notes |
|---|---|---|
| `color` | `#e30b0b` | Hex or rgb() |
| `fontFamily` | `"Inter"` | Quoted, single family |
| `dimension` | `"16px"` | Px, rem, em — must have unit |
| `fontWeight` | `400` | Numeric |
| `boxShadow` | `"0 4px 16px rgba(0,0,0,.1)"` | Full shadow string |
| `duration` | `"200ms"` | With ms unit |
| `cubicBezier` | `[.25, .1, .35, 1]` | 4-tuple array |
| `number` | `1.5` | Unitless |

## Minimal example

```json
{
  "color": {
    "primary": {
      "$value": "#e30b0b",
      "$type": "color",
      "$description": "Renova accent red, from --token-3e609ac1"
    }
  },
  "font": {
    "display": {
      "$value": "Figtree",
      "$type": "fontFamily"
    },
    "body": {
      "$value": "Inter",
      "$type": "fontFamily"
    }
  },
  "space": {
    "1": { "$value": "4px", "$type": "dimension" },
    "2": { "$value": "8px", "$type": "dimension" },
    "section-py": { "$value": "clamp(60px, 8vw, 120px)", "$type": "dimension" }
  },
  "radius": {
    "pill": { "$value": "9999px", "$type": "dimension" }
  }
}
```

## Differences from our Core Framework CSS

| | W3C `tokens.json` | Core Framework `tokens.css` |
|---|---|---|
| Format | JSON | CSS custom properties |
| Use case | Design tool import (Figma, Style Dictionary) | Direct browser/runtime use |
| Semantic | `$description` field | Comments in CSS |
| Extensions | `$extensions: { source: 'dembrandt' }` | Comments |

Both files are produced by `merge-tokens.py` from the same source data.
`tokens.json` is for tools; `tokens.css` is for browsers.
