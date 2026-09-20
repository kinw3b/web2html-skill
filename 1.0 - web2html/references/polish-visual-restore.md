> **3.0 still runs after 2.4.** Hover is 1.3 source CSS + 3.2 `hover.css`, not 2.2.c.
> Paper frames are gold for *structure*. 2.3 already signed paint.
> 3.x does **not** restore geometry.

# 3.x fidelity freeze — what polish may touch

Load this **before** 3.1 on every website-to-html run. Pitfall #196.

2.3 measured each homepage section against Paper 1600 / 768 / 390.
2.4 is the human acceptance of that ship. `qa/fidelity-freeze-24.json`
is snapshotted at 2.4 done (and again if missing when 3.1 goes active).
`seed_index_polish.py` copies `rebuild/index.html` to
`rebuild/index-polish.html` when **3.1 goes active**, not at 2.4 done.
That copy is unpolished until 3.1–3.3 finish. **3.x writes only the polish file.**

**3.x may not undo that freeze.** Pixel-perfect is 2.3 only. Do not
reload it here. Do not “restore” gaps, icons, type, or radius that 2.3
already signed — that pass is how last-run polish broke accepted 2.3
fixes.

## Scope by step

| Step | In | Out |
|---|---|---|
| **3.1** Impeccable + Taste | Contrast / readability on **existing** tokens. `:focus-visible` on existing controls. Anti-AI-slop (invented chrome, em-dashes, peeking skip-links, generic glow). Residual a11y defects. Console errors that do not require a restyle. | Font-size / type scale / `--text-*`. Design Library class rename or replace. Gap, padding, width, radius, icons, imagery, absolute overlays, section order. Visual restore vs Paper. Taste redesign. Writing `hover.css`. |
| **3.2** Emil + guidelines | Hover CSS from **1.3 source CSS** (`apply-hover-css.py` → `rebuild/css/hover.css` on the **same** `library.json` class names). **Painted burger drawer** (`author-nav-drawer.py` — same desktop links stacked; Capture Tool is not required). **FAQ accordion** (`author-faq.py` — scrape answers onto painted rows). **Nav dropdowns** (`author-nav-dropdown.py` — scrape submenus). Guidelines a11y (focus, reduced-motion, contrast). **Mandatory GSAP in-view** on `index-polish.html` (`inject-gsap-reveal.py`, `start: "top 75%"`, parent groups stagger children). | Skipping GSAP from a 1.4 archive. Skipping hover, the burger drawer, FAQ, or dropdowns because Capture Tool did not run. Skipping FAQ for empty Paper bodies. Invented hover. Inventing a burger / FAQ section / nav label Paper never painted. Layout / type / class changes. `apply-library-classes.py`. Paper icon/gap restore. CSS hide / `class="reveal"`. 3.1 writing `hover.css`. |
| **3.3** Semantics | Scrape-only SEO head. `alt`, `lang`, sr-only labels, form names, eager hero / lazy below-fold. `semantics_pass.py --freeze-structure`. | Heading / section / footer retag. Type-align census that mutates size. Skip-link. Marketing meta. Hover edits. |
| **3.4** Human | Compare `index.html` (2.4) with `index-polish.html` (QA) + polish report. Confirm 2.4 paint still holds on the lock. | Tidying before sign-off. Applying library classes. Writing `index.html`. |

## Forbidden (fail the pass)

1. Changing `font-size` or `--text-*` token uses on the ship.
2. Replacing a Design Library class (`btn-primary` → `hero-cta` / `button-1`).
3. Re-running pixel-perfect, visual restore, or type-align *mutation*.
4. Hiding signed 2.4 paint with CSS reveal, `class="reveal"`, or a
   pre-measure hide. GSAP inject is **mandatory** on `index-polish.html`
   and must keep above-fold visible (Pitfall #1). Skipping it because
   1.4 did not record motion is a process failure (Pitfall #204).
5. Diverging from Paper “for taste” (retired 2.8.86 apply-even-if-diverge).
6. Invented skip-link / peeking chrome (Pitfall #81).

## Allowed contrast

If a label fails WCAG AA against its **existing** fill, recolor the
**label** to another token already in `tokens.css`. Do not repaint the
section, do not invent a colour, do not bump type size to pass contrast.

## Receipts

3.1 / 3.2 applied JSON lists a11y, contrast, anti-slop, and hover work.
`no_op_fidelity` is valid when the freeze is clean and there is nothing
in scope to apply — list the skipped findings. Empty applied + empty
skipped still fails.

`verify-polish-passes.py` checks the freeze file when it exists.
Drift → revert the 3.x edit, do not “fix” type to match a new census.
