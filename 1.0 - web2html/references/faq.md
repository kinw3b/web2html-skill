# FAQ accordion — website-to-html 2.17.0 companion

Companion recipe for the Emil / tracker **3.2** pass.

If `rebuild/index.html` paints FAQ rows, **wire open/close** and fill empty
answers from `source-site/index.html`. Capture Tool is leftover and is
**not** a gate. Scrape copy is not invented copy (Pitfall #79 #209).

## Command (mandatory at 3.2)

```sh
python3 "$SKILLS/web2html/scripts/author-faq.py" .
```

Receipt: `qa/faq.json` with `"ok": true` and `"writer": "author-faq.py"`.
Empty `applied` is valid only when no FAQ rows are painted. A skip that
says empty Paper bodies / do not invent copy / Capture Tool **fails**
when rows are painted.

Edits `rebuild/index.html` in place. Does not undo paint the
2.4 `qa/fidelity-freeze-24.json` lock guards.

## What it does

1. Detect painted FAQ rows on `rebuild/index.html` (heading/id/class
   FAQ|accordion, `[data-faq-item]`, or two+ `?` rows).
2. Stamp `[data-faq-item]` / `[data-action=toggle-faq]` /
   `[data-faq-answer]`. Inner button is the control — no nested
   `role=button` on the card (Pitfall #79).
3. Fill empty answers from the scrape by question key. Do not clone
   one answer onto every row.
4. Write `rebuild/css/faq.css` (closed answers hidden, answer width
   100%) and `rebuild/js/faq.js`.
5. Link both from `rebuild/index.html`.

Do **not** invent a FAQ section Paper / the ship never painted.
If scrape has no matching answer, still wire the toggle.

## Forbidden

- Skipping because Paper signed empty bodies / “do not invent copy”
  when scrape has the answers
- Skipping because Capture Tool did not run / detect-only
- Cloning one captured answer onto every row
- Inventing a FAQ section
- Undoing the 2.4 `qa/fidelity-freeze-24.json` paint
- Changing font-size, library class names, or 2.3 section geometry

## Exit

`verify-polish-passes.py` and `mark --step 3.2 --status done` require
`qa/faq.json`. Pitfall #209.
