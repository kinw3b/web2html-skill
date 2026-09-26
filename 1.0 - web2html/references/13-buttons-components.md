# 1.3 — Pull Buttons + Components from desktop

Run **after** Design Library mine + token seed (`qa/design-library-step.json` +
`qa/library-seed-qa.json` green). Still inside **1.3**. Do not wait for 1.4.

1.2 seeded empty FRAME `Buttons` (legacy name `Hover States`) and FRAME
`Components`. This pass fills them from token-seeded `home-desktop`. The
Capture Tool is **not** this step.

## What to pull

Walk every named `NN ·` section on `home-desktop` (`get_children` /
`get_tree_summary`). Identify autonomously. One of a repeating pattern.
`get_node_info` the candidate before it goes in the plan. The script refuses
a section shell and refuses a copy whose read-back width or height does not
match that measurement (Pitfall #230). Do not hand-duplicate.

**Pick the compact painted node, then stop.**

- Skip `NN ·` bands and anything whose measured width is the section
  (~1600). That is the shell, not a specimen.
- If the node is a list of equal tiles, park **one tile**, not the list.
- If the node also holds a sibling cluster (logo grid, a second card, a
  banner plus the card), park the child that is the card. Do not park the row.
- If the node is only text or an icon, climb to the parent that owns the
  border, fill, or image (the ring, the card chrome). Do not stop on the
  inner text — that is how a counter loses its circle.
- Do not park a node you have not measured. A percentage width
  (`round(24%, 1px)`, `width: 100%`) reflows when reparented. The script
  stamps the measured pixel width. Without that number it fails the pull.

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
Capture Tool takes use this same grey row. Do not write a white
`confirmed take` card.

**The row hugs the specimen (Pitfall #212 #230).** Width and height are
`fit-content` on the row, the states wrapper, and the slot. Never a fixed
`1600px` stage and never `width: 100%` on the slot — that stretches a portrait
or a `width: 100%` image across the row. The duplicated node keeps the
**source pixel width** (`get_node_info` before the copy). Never set
`width: fit-content` on the specimen: wrapping text collapses to one character
and the row grows to that letter stack. Do not `duplicate_nodes` without a
parent — an unparented copy lands beside the row as a second card. Delete any
row child that is not `title` or `states`.

Pick the compact component, not the section row that also holds a sibling
logo grid or a second copy of the same card.

**Order is section `NN` ascending.** `duplicate_nodes` inserts the new row
immediately after the template, and a flex board ignores `top`, so later
inserts paint above earlier ones. After the pull, `restackReviewBoard` moves
rows into section order. Do not leave `07` above `03`.

**Height must hug the specimen (Pitfall #212).** Set the parked specimen root
and its content-hugging slot / review wrapper to Paper **Fit** height
(`height: fit-content`), never **Fill** / `height: 100%` or a cloned template
height (`1832px`). A blown-out first row must not be the template for the
next. Preserve intentional fixed-size internals and source paint; apply sizing
corrections only to parked copies, not `home-desktop`. After placement,
including hover copies, read back sizing and inspect the frame screenshot:
each wrapper must enclose its full specimen, without clipping or overlapping
adjacent rows. Do not mask overflow with `overflow: hidden` or arbitrary
extra height.

**Components must clear Buttons.** Place FRAME `Components` at the measured
Buttons right edge plus 160px (`REVIEW_BOARD_GAP`). The empty-frame reserve
is 1400px; a 1600px row plus padding is 1696px, and using the reserve overlaps
the next frame (Pitfall #230). `clearReviewBoardOverlap` runs at the end of
the pull. Do not write `board.width = 1400` over a wider measured frame.

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
