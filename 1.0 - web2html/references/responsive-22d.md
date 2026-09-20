> **RETIRED as a live 2.2.d step.** There is no 2.2.d letter. Do not mark
> `2.2.d`. Do not `join-responsive-pc-ids` or `get_jsx` tablet/phone as the
> build. 768 / 390 are live in **2.1 (born responsive)** and proven in the
> **2.3 Paper section loop**.

# 768 / 390 — born in 2.1, signed in 2.3

Gold is the **homepage Paper frames**, not a guessed stack and not a
pc-id census:

| Width | Paper / disk | Band |
|------:|---|---|
| 1600 | `home-desktop` | Desktop |
| 768 | `capture/home-768` + Paper `home-768` | Tablet |
| 390 | `capture/home-390` + Paper `home-390` | Phone |

**2.2** writes `rebuild/index-semantic.html` that is already responsive.
2.3 seeds `rebuild/index.html` from that file.
Do not freeze 1600 and “teach reflow later.” Do not invent a 1024 / 1320.

**2.3** self-validates **each homepage section** against the 1.2
source-section clips at those three widths plus `index-raw.html` (serial
or at most two disk-only workers; no Paper MCP; pixel-perfect is a
one-pass assist). Section list from `rebuild/index.html`, not
`layer-ids.json`. Fail is revert-that-section, then the VALIDATE walk
re-shoots and Reads each band (≤3 rounds, Pitfall #216). Receipts:
`qa/section-align-22.json` + `qa/paper-measure/<id>.validate.json`. Do not yield mid-2.3. Session 2 yields only at
**2.4**.

## What 2.1 must already do

- Real `@media` (or equivalent) so 768 and 390 are not a 1600 squeeze
- Tablet band that applies at 768 and not at 1600
- Phone band that applies at 390 and not at 768
- Landmarks kept (`header` / `nav` / `main` / `section` / `footer`)
- If Paper paints a hamburger, open = the same desktop links stacked.
  3.2 **must** author that sheet (`author-nav-drawer.py`). Capture Tool
  is not required (Pitfall #208).

Clip overflow if the authored page grows a horizontal scrollbar
That is hygiene, not a 2.2.d preflight join.

## Forbidden (retired dump-era)

- a pc-id join as the 2.0 key (those scripts are deleted, 2.10.0)
- `get_jsx` of the whole tablet/phone frame on every loop
- Mapping leaf pc-ids from desktop onto 768/390
- `width: 100% !important` on `#paper-root` or every section as the recipe
- Writing `qa/responsive-22d.md` and jumping to a 2.2.e review
- Marking 2.2.d done
- Inventing a hamburger Paper never painted

## Exit

`section_22_gate.py` green. Every homepage section Paper-signed at
1600 / 768 / 390. Then **2.4** human TAGS checkpoint — not 2.2.e.
Pitfalls #136 #140–#147 still apply as watch items inside 2.1 / 2.3.
