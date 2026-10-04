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

## Phase 5 — the same hunt on the built pages (5.4+, Pitfall #247)

`author-nav-dropdown.py` only edits `rebuild/index.html` — it is a 3.2
homepage gate and NEVER the phase-5 path. Phase 5 interiors get the same
hidden-item hunt through the **5.4+ interior /compare pass**
(`compare` skill, `/compare {slug}`) plus the machine audit:

```sh
python3 "$SKILLS/web2html/scripts/phase_5_nav_audit.py" .   # qa/phase-5-nav.json
```

- Inventory per page: hover-reel `dropdown` / `nav-mobile-*` manifests,
  scrape submenus (the page's own `source-site/{slug}.html`, falling back to
  home), painted triggers in the raw dumps. Home's inventory applies to
  EVERY page — the Header is shared.
- Each inventoried item is checked against the BUILT page
  (`astro/dist/{slug}/index.html`) and `astro/src/components/Header.astro`:
  `wired` needs trigger + panel + wired CSS/JS; a trigger without a panel is
  `unwired`; no trace of a painted trigger is `missing`.
- `ok:true` only when every item on every page is `wired`.
  `wire-astro-routes.py` (5.5) refuses without a fresh ok receipt.
- The fix obeys the same interaction contract above (Pitfall #241) and lands
  ONCE in `astro/src/components/Header.astro` + `astro/public/styles|scripts/`
  for chrome triggers; in `src/pages/{slug}.astro` for page-local ones.
  Never `rebuild/` in phase 5. Rebuild with `build-astro-dist.py`, re-shoot
  patched bands, then rerun the audit.
