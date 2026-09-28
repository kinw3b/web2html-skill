# Burger open drawer — website-to-html 2.16.0 companion

Companion recipe for the Emil / tracker **3.2** pass.

If `rebuild/index.html` paints a hamburger, **open = the same desktop links
stacked**. Capture Tool is leftover and is **not** a gate. Inventing a
sheet of those existing links is not new chrome (Pitfall #145 #183 #208).

## Command (mandatory at 3.2)

```sh
python3 "$SKILLS/web2html/scripts/author-nav-drawer.py" .
```

Receipt: `qa/nav-drawer.json` with `"ok": true` and
`"writer": "author-nav-drawer.py"`. Empty `applied` is valid only when
no hamburger is painted. A skip that says Capture Tool / “inventing a
sheet is new chrome” **fails**.

Edits `rebuild/index.html` in place. Does not undo paint the
2.4 `qa/fidelity-freeze-24.json` lock guards.

## What it does

1. Detect a painted hamburger on `rebuild/index.html` (`.burger` /
   `.nav-toggle` / `[data-nav-toggle]` / “Open menu”).
2. Collect desktop header links + CTAs (skip the logo).
3. Stamp `[data-nav-toggle]` + `aria-controls="nav-panel"`.
4. Author or fill `#nav-panel` with those same links stacked.
5. Write `rebuild/css/nav-drawer.css` (Emil drawer curve, compact
   breakpoint from `site.css`) and `rebuild/js/nav-drawer.js`.
6. Link both from `rebuild/index.html`. If an inline script already
   binds `nav-open`, do not double-bind.

Do **not** invent a burger Paper / the ship never painted.

## Forbidden

- Skipping because Capture Tool did not run / no open-nav pair
- Calling the stacked-link sheet “new chrome”
- Inventing a desktop hamburger
- Undoing the 2.4 `qa/fidelity-freeze-24.json` paint
- Changing font-size, library class names, or 2.3 section geometry

## Exit

`verify-polish-passes.py` and `mark --step 3.2 --status done` require
`qa/nav-drawer.json`. Pitfall #208.
