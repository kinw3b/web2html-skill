# Missing-elements (optional diagnostic)

**Not a pipeline step.** After 1.4 the run goes straight to **1.5** human
review. The human compares `capture/home-desktop/source-sections/NN-*.png`
to the named Paper section and pins comments. Do not run this inventory
unless a person asks for it.

`qa-paper` can be green while Paper is still wrong: empty named frames,
sourceless maps, 0×0 SVG ring text, 1px hidden-variant towers, and a
**displaced named section** (leftover `top`, mid-page hole) are not
high findings there. A per-section white-ratio match is not a page-order
pass — isolated `get_screenshot` of the node still looks full.

## Optional runner (only if asked)

```bash
node "$SKILLS/url-to-paper/scripts/run-missing-elements.mjs"   --capture capture/home-desktop   --out-dir qa   --project <name>   --live https://…   --paper https://app.paper.design/file/…   --file-id $PAPER_FILE_ID
```

Writes `qa/missing-elements-fix.{json,md,html}`. This is not a 1.5
prerequisite and must not delay the human walk.

## Auto-apply (if the runner is used)

| Kind | Do |
|---|---|
| empty-named-section / hollow-section | `write_html` insert-children from capture HTML. **No delete_nodes.** Hug `height: min-content`. |
| missing-chrome | `--prepend` nav / serialize header from landmarks + `fullpage.png`. |
| empty-iframe | Crop the source-section / prepesticide clip. `write_html` an `https://` `<img>`. Never `paper-asset://`. |
| dead-svg-text | Replace 0×0 SVG text with the scrape PNG. |
| hidden-variant-stack | Collapse `width≈1` / `display:none` towers. |
| date-chrome | Mock `dd/mm/yyyy` + calendar. Keep `type=date` in rebuild. |
| source-empty | Leave empty. Do not invent copy. |
| blank-source-shot | Re-seed `Source · {page}` with `data:image` rows. Never `paper-asset://` / `file://`. Never skip an existing blank board. |
| displaced-section | Clear leftover `top`, `position: relative`, hug `height: min-content` on named `NN ·` layers. Then re-check monotonic y and gaps. After prepend-nav, always restack. |

## Do not

- Re-run `merge-split-headings.mjs` on nav links, CTA pairs, body paragraphs, or icon rows.
- Treat identical CMS copy as a miss.
- Fill a live-empty card with new marketing text.
- Start 2.0 / `get_jsx` because `qa-paper` was 0 findings.
- Treat `childCount > 0` or a per-section white-ratio match as proof the page stack is correct.
- Treat this HTML report as a substitute for 1.5 Paper comments.
