> **RETIRED as a live 2.0 step.** There is no 2.2.c. Do not mark `2.2.c`.
> Hover is **1.3 source CSS** on pulled Buttons, then **3.2**
> (`rebuild/css/hover.css`). Optional Capture Tool pairs remain leftover
> 1.4 live hover. 2.1 authors the page; 2.3 signs sections vs Paper.

# Hover — 1.3 source CSS + 3.2 `hover.css`

Captured hover is not a 2.2 letter. **1.3** mines source CSS `:hover` for
the Buttons specimens it just pulled (`qa/button-hover.json`) and parks a
hover cell when that CSS has paint. **3.2** writes `rebuild/css/hover.css`
from that receipt after the 2.4 TAGS checkpoint (`apply-hover-css.py`).
Do not skip 3.2 hover because Capture Tool did not run (Pitfall #207).
GSAP in-view is a **separate mandatory 3.2 pass** (`references/gsap-inview.md`)
and does not wait on hover capture (Pitfall #204).

## What 1.3 does

After `pull-desktop-specimens.mjs`, `author-button-hover.mjs` reads
`source-site/index.html` plus linked stylesheets, matches each pulled
button label, and keeps paint-only `:hover` declarations. It does **not**
use Playwright. Bare `a:hover` / `button:hover` is dropped. Color-only
ticks on filled buttons are dropped. Empty `applied` is valid.

## What 3.2 does

1. Read `qa/button-hover.json` and `design-library/library.json` names
   (`btn-primary`, `btn-ghost`, `text-link`, `navbar-link`, …). Those names
   are the API. Do not invent `.hero-cta` / `.button-1`. Do not **replace**
   a class 2.3 already applied — add `hover.css` on the existing name.
2. Run:

   ```sh
   python3 $SKILLS/web2html/scripts/apply-hover-css.py .
   ```

   That writes `rebuild/css/hover.css` as `.{library-name}:hover`
   (section-scope if the same label has two skins: `#hero .btn-primary:hover`),
   links it from `index-polish.html`, and writes `qa/button-hover-css.json`.
   Map hex onto `var(--color-*)` when `tokens.css` already has that value.
3. If a matching `<a>` / `<button>` is missing the library class, **add**
   it alongside existing classes. Never strip `btn-primary` for a new label.
4. Compare Paper **Buttons** default vs hover when a hover cell exists:
   - **Different paint** — copy that hover pill (`background` / `border` /
     `box-shadow` / `color`). Do not invent `filter: brightness`, opacity,
     or scale on top of a real capture (Pitfall #152).
   - **No 1.3 source paint and identical Paper cells** (including a 1–2
     channel RGB tick) — then you may invent a visible `:hover`. Still not
     `styleDelta[0]` / UA link blue (#33).
   **Label contrast (Pitfall #139):** a filled hover must recolor the
   label so it reads on the new fill — inverse/white on ink, ink on lime.
   Always also set (swap `background` for the captured hover fill when
   Paper default ≠ hover):

   ```css
   .btn-primary:hover {
     background: var(--color-ink);
     color: var(--color-text-inverse-2);
     -webkit-text-fill-color: var(--color-text-inverse-2);
   }
   .btn-primary:hover p,
   .btn-primary:hover span {
     color: var(--color-text-inverse-2);
     -webkit-text-fill-color: var(--color-text-inverse-2);
   }
   ```

   Use `!important` when the pill still has inline `background` / `color`.
5. Optional Capture Tool pairs (`source-site/components/.../manifest.json`)
   may refine the same `library.json` names. They do not replace 1.3.
6. Bind a painted hamburger only if Paper shows one. **3.2 must author
   the open drawer** (`author-nav-drawer.py`) from the same desktop links
   stacked. Do not skip because Capture Tool did not run (Pitfall #208).
7. If FAQ rows are painted, **3.2 must author the accordion**
   (`author-faq.py`) and fill empty answers from the scrape. Do not skip
   empty Paper bodies (Pitfall #209).
8. If a nav dropdown is painted or the scrape has a matching submenu,
   **3.2 must author the panel** (`author-nav-dropdown.py`). Do not skip
   for Capture Tool / `--allow-dropdown` (Pitfall #210).
9. **3.1 must not** be the writer of `hover.css`.

## Forbidden

- Teaching 2.2.c as a live spine step
- Bare `a:hover` / `button:hover` as the recipe for a painted CTA
- A second hover sheet or renamed class that is not in `library.json`
- Inventing hover CSS while 1.3 source CSS or Paper default/hover differ
- Skipping 3.2 hover because Capture Tool did not run
- Flattening a button to a `div` so hover “does not need” a class

## Exit

C/3.3 (`emil-design-eng`) hover parity, not `hover_22c_gate.py` and not
`mark --step 2.2.c`. Receipt is `qa/button-hover-css.json` (and
`qa/animation-parity.md` when leftover Capture Tool hover exists) — not
the numbered 3.3 semantics sweep, which is SEO-only and does not touch hover.
Pitfalls #137 #152 #207 #208 #209 #210. See `references/nav-drawer.md`,
`references/faq.md`, and `references/nav-dropdown.md`.
