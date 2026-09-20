# Library kit — layout templates

`Design Library` does not exist before 1.4. After every Paper frame exists and
the 1.3 HUD has written Done, `run-design-library-step.mjs` mines all eligible
frames once and `render-library.mjs` creates the foundations-only artboard once.
Layout gold ships in this directory. Use the local shell; never clone a public
Paper file or copy another run's branding.

Reusable shells so a run does **not** re-author the same sheet from scratch
for every site.

The first build of these frames cost two agents ~75k tokens and ~50 tool calls
each to produce a layout that is identical every time. Only the *data* changes.

## How it works

`scripts/run-design-library-step.mjs` inventories and mines each eligible frame
once, writes one canonical token set, then calls `scripts/render-library.mjs`.
The renderer reads `library.json` (from `extract-library.mjs`), derives a theme,
and creates the artboard in one paced pass. Every run must satisfy the
foundations contract: five Tailwind SEMANTIC colors, `--text-10xl` / `11xl` /
`12xl`, scale large → small, `Aa` in the primary sans, four colour
swatches per row. Family names (`Inter`) are ink at `--text-xl`; FAMILIES
is ink at `--text-sm`. Exact matches are then bound back
under a pre/post geometry guard. **No agent authoring involved.**

```bash
# preview to disk, no Paper calls at all
node scripts/render-library.mjs --library library.json --kind foundations \
  --dry-run --out-dir rendered/

# render straight into Paper
node scripts/render-library.mjs --library library.json --kind foundations \
  --file-id <id>
```

## Template syntax

- `{{path.to.value}}` — substitution
- `{{#each list}} … {{/each}}` — repeat; fields inside use `{{.field}}`, and
  `{{theme.x}}` still resolves
- `{{#if path}} … {{/if}}` — omit a section when there's no data (e.g. a site
  with no radii)

## The theme is derived, never hard-coded

`deriveTheme()` pulls `ink`, `accent`, `surface`, `border`, `muted`, plus the
display and sans families, out of the mined tokens. Templates reference
`{{theme.*}}` only. Hard-coding a hex here would make every future library look
like the first site this was built from.

## The directories

| Dir | `--kind` | What it renders |
|---|---|---|
| `kit-foundations/`, `kit-components/` | `kit-*` | Neutral starting base — greyscale, placeholders, names only. No `library.json` needed. |
| `site-components/` | `site-components` | Real components cloned from the import, clean name-only labels. Driven by an inventory file. |
| `foundations/` | `foundations` | Scale specimens (token + value + swatch) plus mined colors/fonts. |
| `components/` | `components` | Legacy shells with `<!-- SLOT: … -->` containers. Superseded by `site-components/`; kept for the case where an agent must hand-place something unusual. |

## site-components/ — the default for a finished library

Feed it `{id, name, dark}` per atomic group. The renderer resolves each node's
real geometry from Paper, so it can size containers correctly.

**Containers fit their component; never use a fixed cell.** An earlier version
used uniform boxes with `overflow:hidden` and silently cropped anything larger —
a 627×252 testimonial card lost its right third. Container is
`component + padding`, with `flex:none` on both container and clone. Regions get
no minimum height so a 46px announcement bar isn't padded to a footer's box.

**Labels are the component name only.** Ids, sizes, instance counts, page counts
and correction notes belong in `library.json` and the agent's report, not on the
canvas.

**Buttons are their own section**, each with a live `default` beside an empty
dashed `hover` slot sized to match. A static DOM capture cannot record hover —
leave the slot empty rather than inventing one.

Mark near-white components `dark: true`; they are invisible on a light card.

## Sizing knobs

`render-library.mjs` computes `cw`/`ch` (container), `bw` (a button's
default+hover pair) and `pad` per item. Templates must consume those rather than
hard-coding dimensions — hard-coded cells are how the cropping bug happened.
