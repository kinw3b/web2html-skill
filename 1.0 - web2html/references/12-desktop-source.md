# 1.2 · Capture — Paper is the source of truth

Collect writes the live lander `home-desktop` plus `home-768` and `home-390`,
all captured through the same `url-to-paper` path. Tablet and phone also keep
gold **screenshots** on disk, and one screenshot pass signs 1.2 off.

**One Paper file per run.** The first `capture-session.mjs` calls `create_file` with a
timestamped name (`kp-thrive 2026-08-30 1205`). A retry reopens the `fileId` in
this project's `qa/paper-file.json`. Do **not** `list_files` and
open a similarly-named existing document. Do **not** pass `--file`.
`start` clears a leftover receipt so a new run still gets one new file.
`--new-file` is the only second document. Pitfall #187 #224.

**Nothing on 1.2 is model-authored.** This was an authoring step once; it is a
plain capture now. FRAME `Navigation` is captured at all three widths in the
same pass, which is what makes the 1.4 Capture Tool optional.

## Collect (headless)

`capture-session.mjs` / `collectHomepageToPaper`:

1. Serialize + assemble `home-desktop`, then capture `home-768` and `home-390`
   through the same path. **Nothing on this step is model-authored** — if a
   breakpoint frame is wrong, fix the capture, do not hand-build the frame.
   Capture FRAME `Navigation` at all three widths in the same pass
   (`01 · nav-1600` / `02 · nav-768` / `03 · nav-390`).
2. Clip `source-sections/NN-slug.png` at 1600 / 768 / 390. Screenshots board stays 1600 at **50% opacity** so it recedes next to `home-desktop`.
3. Write `capture/home-{768,390}/fullpage.png` as QA reference.
4. Serialize compact chrome (`00-header.html` / `00-nav.html`) at **each** width
   and park all three on FRAME `Navigation` as `01 · nav-1600` / `02 · nav-768` /
   `03 · nav-390`. Each take is serialized with the viewport actually at that
   width, so the compact bar and the burger are captured paint, not a guess.
   A missing take at any width keeps 1.2 open.
5. If `home-desktop` has no header/nav, prepend that same compact stack. Never the live Framer page/hero shell (Pitfall #110 / #168).
6. `stretch-root --prove --artboard home-desktop` must be green. `layer-ids.json` / census sidecars are optional and invisible — not a 1.2 gate.
7. A CSS background photo whose frame aspect disagrees with the Fill file: reset the frame to the file's intrinsic size, then scale width to the parent (Pitfall #226).

`--desktop-only` skips 768/390 **shots** too. That is leftover / experiment, not the default.

## Capture 768 / 390

> **Retired: the authored-breakpoint pass.** 768 and 390 used to be cloned from
> desktop and reflowed by the model. They are captured now. If a breakpoint
> frame is wrong the fix is in the capture, never a hand-built frame — and never
> a `write_html` reflow on top of a captured one.

1. Capture `home-768` (768 × fit-content) and `home-390` (390 × fit-content)
   through the same `url-to-paper` path as desktop, each at its own viewport.
2. Place them on the same Y as `home-desktop`, to its right. Shift Buttons /
  Components / Navigation if they sit in the way.
3. Capture the compact chrome at each width onto FRAME `Navigation`
   (`01 · nav-1600` / `02 · nav-768` / `03 · nav-390`). The burger at 768 / 390
   is a real serialize at that width — open the menu where the live site opens
   it, so both closed and open paint reach Paper.
4. Reuse the existing fills, type, images, and tokens the capture produced. Do
   not invent a second visual system.
5. `arrange-artboards.mjs` after all frames exist: Screenshots → desktop → 768 →
   390 → Buttons → Components → Navigation. Empty Buttons / Components / Navigation
   frames are `width`/`height: fit-content` from create — never a fixed 1400px.

## Screenshot QA (one pass)

```sh
node "$SKILLS/url-to-paper/scripts/breakpoint-shot-qa.mjs" \
  --project /path/to/project --file-id "$PAPER_FILE_ID"
```

Pairs each `capture/home-{768,390}/source-sections/NN-*.png` with that named Paper band. Blank-vs-content fails. Missing `home-768` / `home-390` fails. Receipt: `qa/breakpoint-shot-qa.json`. `mark --step 1.2 --status done` stays red until that file is `ok: true`.

2.3 golds Paper `home-768` / `home-390`. Those frames are **captured** and
screenshot-validated. The Navigation board at all three widths is the reason the
1.4 Capture Tool is optional — every capability added here should shrink what
the extension is still needed for.
