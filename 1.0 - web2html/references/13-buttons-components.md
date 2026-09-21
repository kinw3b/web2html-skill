# 1.3 — Pull Buttons + Components from desktop

Run **after** Design Library mine + token seed (`qa/design-library-step.json` +
`qa/library-seed-qa.json` green). Still inside **1.3**. Do not wait for 1.4.

1.2 seeded empty FRAME `Buttons` (legacy name `Hover States`) and FRAME
`Components`. This pass fills them from token-seeded `home-desktop`. The
Capture Tool is **not** this step.

## What to pull

Walk every named `NN ·` section on `home-desktop` (`get_children` /
`get_tree_summary`). Identify autonomously. One of a repeating pattern.

**FRAME `Buttons`** — CTAs and painted pills, including outlined ghosts.

- Hero / nav / footer trial buttons, primary and secondary skins
- Same label + size in two sections = two specimens if the paint differs
- Skip text-only nav links (those live on FRAME `Navigation`)
- Skip logos

**FRAME `Components`** — cards, widgets, snippets.

- Feature / process / integrate cards, testimonials, stats tiles, review clusters
- Smallest compact parent that still reads as the component
- One tile from a repeating grid
- Skip full section bands, the hero shell, nav, and whole footer columns

Label like the board: `Primary - Get Started Now`, `Feature Card Medium`.
Every row needs `sectionId` matching a scanned `NN ·` (`"02"` or `"02 · features"`).

## Card layout

Parked rows reuse the review card: red 36px `section-number` badge, specimen
title, and a **neutral grey stage** (`#6F6F6F`) behind the specimen. The badge
is the **home-desktop section `NN`**, not dump order — two cards from
`02 · features` both show `02`. The title is the specimen name
(`Content Widget`) in `#F2F2F2` so it stays readable on that grey. Paper layer
names stay `Object 01` / `Component 01` for stack order.

The grey is review chrome only. Duplicate the desktop node as-is — do not
paint a fill onto a transparent specimen. A white card hides white type and
anything with no background of its own (Pitfall #222). `parkDesktopNodeOnBoard`
stamps `#6F6F6F` on every row, including a duplicate of an older white template.

**Height must hug the specimen (Pitfall #212).** Set the parked specimen root
and its content-hugging slot / review wrapper to Paper **Fit** height
(`height: fit-content`), never **Fill** / `height: 100%` or vertical flex growth
inherited from the source section. Preserve intentional fixed-size internals
and source paint; apply sizing corrections only to parked copies, not
`home-desktop`. After placement, including hover copies, read back sizing and
inspect the frame screenshot: each wrapper must enclose its full specimen,
without clipping or overlapping adjacent rows. Do not mask overflow with
`overflow: hidden` or arbitrary extra height.

## Navigation placement — after the pull

Before finishing **1.3**, move the existing FRAME `Navigation` to the **left
of `Design Library`**, never above / on top of FRAME `Components`. Do this
after the Buttons / Components pull and hover pass so their final bounds
are known. Read the frames' current canvas bounds; place Navigation with
its right edge 100px left of Design Library's left edge and align their top
edges. Move the existing frame only — do not duplicate it, reparent its
contents, or change the three captured navbar variants' internal geometry.

Read back the resulting bounds and verify Navigation does not intersect
Components, Buttons, Design Library, or the captured landers. If another
frame occupies that position, move Navigation farther left until there is
at least 100px clearance, keeping the top alignment. Inspect the canvas
before marking 1.3 done; placement is not complete merely because the move
call succeeded. Pitfall #213.

## How to park

Write `qa/buttons-components-plan.json`, then run the script. Do not
`write_html` a restyled copy — `duplicate_nodes` keeps the 1.3 tokens.

```json
{
  "scannedSections": ["01 · hero", "02 · features"],
  "buttons": [
    { "sourceNodeId": "<id>", "label": "Primary - Get Started Now", "sectionId": "01" }
  ],
  "components": [
    { "sourceNodeId": "<id>", "label": "Feature Card Medium", "sectionId": "02" }
  ]
}
```

```sh
node $SKILLS/hover-reel/scripts/pull-desktop-specimens.mjs \
  --project . --file-id $PAPER_FILE_ID \
  --plan qa/buttons-components-plan.json
```

Empty `buttons` / `components` is allowed when every section was scanned and
the page truly has none. Missing `scannedSections` fails 1.3.

Receipt: `qa/buttons-components-pull.json` (`ok: true`,
`writer: pull-desktop-specimens.mjs`).

## Source CSS hover (light pass)

Still inside **1.3**, after the pull. Mine `:hover` paint from
`source-site/index.html` (`<style>` plus linked stylesheets) and match it
to the pulled Buttons labels. Bare `a:hover` / `button:hover` is not a CTA
recipe. Buttons still need paint (`background` / `border` / `box-shadow`),
not a color tick. When paint exists, duplicate the parked default into the
Hover cell and apply that paint.

`pull-desktop-specimens.mjs` already runs this. Re-run:

```sh
node $SKILLS/hover-reel/scripts/author-button-hover.mjs \
  --project . --file-id $PAPER_FILE_ID
```

Receipt: `qa/button-hover.json` (`ok: true`, `writer: author-button-hover.mjs`,
`applied[]` / `skipped[]`). Empty `applied` is allowed when source CSS has
no button hover. **3.2** turns `applied` into `rebuild/css/hover.css`
(`apply-hover-css.py`). Do not wait for Capture Tool. Pitfall #207.

If a duplicate shows raw hex instead of `var(--token)`, bind only the new
frames — never a second Design Library:

```sh
node $SKILLS/url-to-paper/scripts/apply-theme-tokens.mjs \
  --file-id $PAPER_FILE_ID --library design-library/library.json \
  --exact-only --only Buttons
node $SKILLS/url-to-paper/scripts/apply-theme-tokens.mjs \
  --file-id $PAPER_FILE_ID --library design-library/library.json \
  --exact-only --only Components
```

## Not this step

- Capture Tool / live hover pairs — optional at **1.4** via
  `pipeline-progress.py open-capture`
- A second Design Library
- Flattening button wrapper chains (`flatten-paper-buttons.mjs` is banned)
