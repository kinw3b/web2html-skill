# Nav dropdown — website-to-html 2.17.0 companion

Companion recipe for the Emil / tracker **3.2** pass.

If `rebuild/index.html` paints a dropdown trigger, or a nav label whose
scrape submenu exists, **wire hover/click**. Capture Tool and
`--allow-dropdown` are leftover and are **not** a gate (Pitfall #210).

## Command (mandatory at 3.2)

```sh
python3 "$SKILLS/web2html/scripts/author-nav-dropdown.py" .
```

Receipt: `qa/nav-dropdown.json` with `"ok": true` and
`"writer": "author-nav-dropdown.py"`. Empty `applied` is valid only when
there is no painted trigger and no scrape submenu matching a
homepage nav label. A skip that says Capture Tool / `--allow-dropdown` / “do not hunt”
**fails**.

Edits `rebuild/index.html` in place. Does not undo paint the
2.4 `qa/fidelity-freeze-24.json` lock guards.

## What it does

1. Detect painted triggers (chevron / `aria-haspopup` / dropdown class /
   nested `ul`) **or** match a homepage nav label to a scrape submenu of
   two+ child links.
2. Stamp `[data-nav-dropdown-trigger]` + insert
   `[data-nav-dropdown-panel]` as a sibling when missing.
3. Fill empty panels from scrape labels. Ship hrefs stay `#` (no live
   URLs).
4. Write `rebuild/css/nav-dropdown.css` and `rebuild/js/nav-dropdown.js`.
5. Link both from `rebuild/index.html`. Compact widths stay on the burger
   drawer — dropdown panels hide at `max-width: 768px`.

Do **not** invent a nav label Paper never painted.

## Interaction contract (Pitfall #241)

`templates/nav-dropdown.js` (copied to `rebuild/js/nav-dropdown.js`) and any
agent-authored nav JS (`nav-menu.js` et al.) must obey:

- **Desktop (hover-capable, >768px):** `mouseenter` on trigger or panel
  opens; a click on the trigger only **opens** — never toggles closed. A
  pointer click always arrives after hover already opened the panel, so a
  toggle slams it shut on every click. Escape, leaving the host, and
  outside clicks close.
- **Touch (`(hover: none), (pointer: coarse)`):** click toggles; the hover
  handlers stay off (tap fires emulated `mouseenter` and would fight the
  toggle).
- **≤768px:** the burger drawer owns navigation; the dropdown panel is
  `display: none !important` and the click handler returns without
  intercepting.

## Forbidden

- Skipping because Capture Tool did not run / `--allow-dropdown` / “do
  not hunt”
- Inventing a new top-level nav item
- Undoing the 2.4 `qa/fidelity-freeze-24.json` paint
- Changing font-size, library class names, or 2.3 section geometry

## Exit

`verify-polish-passes.py` and `mark --step 3.2 --status done` require
`qa/nav-dropdown.json`. Pitfall #210.
