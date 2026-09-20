# Paper font bind (Pitfalls #88 + #89)

Paper `fontFamily` is a **catalog face**. Rebuild CSS is a **stack**. Mixing
them is how Design Library Aa said "Lora" while the inspector showed
System Sans-Serif.

## Two values, one token

| Surface | Field | Example |
|---|---|---|
| `library.json` / `tokens.css` / file:// rebuild | `value` / `buildFontFamilyValue` | `"Inter", system-ui, sans-serif` |
| Paper `create_tokens` / `set_tokens` | `paperValue` / `paperCreateTokens` | `Inter` |
| Design Library + lander `write_html` | `theme.sans` / `theme.display` / `theme.mono` / family Aa | `Inter` / `Lora` / `SF Mono` |

Never send a comma stack to Paper. `write_html` cannot run
`Inter, system-ui, sans-serif` or `'SF Mono', Menlo, monospace` — the Text
picker falls back to System Sans-Serif. `var(--font-serif)` on first write
is also unbound if Paper does not resolve font vars in HTML.

Helpers: `paperFontFamilyValue`, `paperThemeFonts`, `resolvePaperFontFamily`,
`bindInlinePaperFonts`, `bindPaperFontUpdates`, `findUnboundFonts` in
`scripts/library-tokens.mjs`.

## Sheet (1.4)

`NEUTRAL_THEME` and `foundationsSheetContext` set:

- `theme.sans` = paper face of `--font-sans` (Inter)
- `theme.display` = paper face of serif/display (Lora) or the same as sans
- `theme.mono` = catalog mono (SF Mono / Menlo / ui-monospace) or Inter

Family card Aa uses `font-family: {{.paperValue}}` plus
`data-font-token="--font-serif"`. The caption still shows the token name.
SCALE / WEIGHTS / chrome use `{{theme.sans}}` — now a face, not a stack.

Type scale stays Tailwind `--text-xs` … `--text-12xl`. No `--text-display`.

## Lander bind

After `create_tokens` and after `write_html` of library or landers:

1. Catch-at-write: `bindInlinePaperFonts` in
   `assemble-lander` / `import-sections` collapses stacks to the first
   named catalog face.
2. Token-pass: `themeTokenPass` / `bind-paper-fonts.mjs` maps empty,
   System Sans-Serif, `system-ui`, `sans-serif` / `serif` / `monospace`,
   or a CSS stack to `var(--font-xxx)` (catalog face if var is not honored).
3. Unavailable faces follow #88 — skip or recorded fallback. Do not invent
   a font.

```bash
node scripts/bind-paper-fonts.mjs --file-id $PAPER_FILE_ID \
  --library design-library/library.json --dry-run
```

`--apply` (default without `--dry-run`) refuses hotelsix, techty, and
prior-run. Do not fire this against those live files.

## QA

`qa-paper` finding `unbound-font` (high) fires on System Sans-Serif /
generic family / CSS stack on Text when font tokens exist — and on any
Design Library typography Text that is still unbound.

1.4 / Stage L cannot pass while any library typography Text is unbound.
`qa-paper` used to record `fontFamily` and stay green.

## Not this pitfall

- #25 — weight-suffixed faces in `write_html` (`Satoshi-Bold`)
- #76 — token-pass sample vs census
- #88 — `create_tokens` payload was the stack (token value)
- Homepage-only file:// rebuild keeps stacks in `library.json` / `tokens.css`
- Never `paper-asset://` in `write_html`
