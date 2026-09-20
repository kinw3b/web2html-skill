# FAQ accordion — website-to-html 2.17.0 companion

Companion recipe for the Emil / tracker **3.2** pass.

If the polish file paints FAQ rows, **wire open/close** and fill empty
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

Writes polish only (`rebuild/index-polish.html`). Does not mutate the
2.4 `index.html` lock.

## What it does

1. Detect painted FAQ rows on `index-polish.html` (heading/id/class
   FAQ|accordion, `[data-faq-item]`, or two+ `?` rows).
2. Stamp `[data-faq-item]` / `[data-action=toggle-faq]` /
   `[data-faq-answer]`. Inner button is the control — no nested
   `role=button` on the card (Pitfall #79).
3. Fill empty answers from the scrape by question key. Do not clone
   one answer onto every row.
4. Write `rebuild/css/faq.css` (closed answers hidden, answer width
   100%) and `rebuild/js/faq.js`.
5. Link both from `index-polish.html`.

Do **not** invent a FAQ section Paper / the polish file never painted.
If scrape has no matching answer, still wire the toggle.

## Forbidden

- Skipping because Paper signed empty bodies / “do not invent copy”
  when scrape has the answers
- Skipping because Capture Tool did not run / detect-only
- Cloning one captured answer onto every row
- Inventing a FAQ section
- Mutating `rebuild/index.html`
- Changing font-size, library class names, or 2.3 section geometry

## Exit

`verify-polish-passes.py` and `mark --step 3.2 --status done` require
`qa/faq.json`. Pitfall #209.
