# Nav dropdown — website-to-html 2.17.0 companion

Companion recipe for the Emil / tracker **3.2** pass.

If the polish file paints a dropdown trigger, or a nav label whose
scrape submenu exists, **wire hover/click**. Capture Tool and
`--allow-dropdown` are leftover and are **not** a gate (Pitfall #210).

## Command (mandatory at 3.2)

```sh
python3 "$SKILLS/web2html/scripts/author-nav-dropdown.py" .
```

Receipt: `qa/nav-dropdown.json` with `"ok": true` and
`"writer": "author-nav-dropdown.py"`. Empty `applied` is valid only when
there is no painted trigger and no scrape submenu matching a polish nav
label. A skip that says Capture Tool / `--allow-dropdown` / “do not hunt”
**fails**.

Writes polish only (`rebuild/index-polish.html`). Does not mutate the
2.4 `index.html` lock.

## What it does

1. Detect painted triggers (chevron / `aria-haspopup` / dropdown class /
   nested `ul`) **or** match a polish nav label to a scrape submenu of
   two+ child links.
2. Stamp `[data-nav-dropdown-trigger]` + insert
   `[data-nav-dropdown-panel]` as a sibling when missing.
3. Fill empty panels from scrape labels. Ship hrefs stay `#` (no live
   URLs).
4. Write `rebuild/css/nav-dropdown.css` and `rebuild/js/nav-dropdown.js`.
5. Link both from `index-polish.html`. Compact widths stay on the burger
   drawer — dropdown panels hide at `max-width: 768px`.

Do **not** invent a nav label Paper never painted.

## Forbidden

- Skipping because Capture Tool did not run / `--allow-dropdown` / “do
  not hunt”
- Inventing a new top-level nav item
- Mutating `rebuild/index.html`
- Changing font-size, library class names, or 2.3 section geometry

## Exit

`verify-polish-passes.py` and `mark --step 3.2 --status done` require
`qa/nav-dropdown.json`. Pitfall #210.
