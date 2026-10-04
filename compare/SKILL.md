---
name: compare
description: >
  Side-by-side self-validation of the captured source against the rebuild at
  1600 / 768 / 390 — full viewport windows at the same scroll stop, source
  left, rebuild right, native scale, one PNG per band per breakpoint. Invoke
  as /compare at ANY point in a run (2.3 loop, 3.x polish, 3.4 review) whenever
  the rebuild still looks inconsistent with the source. Targets one band
  (/compare pricing) or every band, fans the pair reads out to read-only wave
  workers (orca / subagent / serial — the same adapters as 2.3), names what
  differs, and lands scoped fixes under the current phase's write rules, then
  re-shoots only patched bands until the pairs match — hard cap 2 rounds per
  band. Triggers - "compare", "/compare", "side-by-side",
  "source vs rebuild", "still looks off", "doesn't match the source",
  "self-validate", "check this section against the source".
argument-hint: "[section-id …] [--live] [--widths 1600,768,390]"
metadata:
  short-description: "Source-vs-rebuild viewport pairs at 3 breakpoints, any phase"
---

# compare — source left, rebuild right, at every breakpoint

A self-validation lens, not a pipeline step. It wraps
`web2html/scripts/paper_23_side_by_side.py`, which shoots **full viewport
windows** (not cropped element clips) of the captured source and of
`rebuild/index.html` at the same scroll stop and stitches them native-scale:
source pane left, 2px divider, rebuild pane right, label bar on top. One PNG
per band per breakpoint at `qa/side-by-side/<width>/NN-slug-side.png`, plus a
contact sheet at `qa/side-by-side/index.html` and a receipt at
`qa/side-by-side/report.json`.

What the viewport window catches that a cropped clip cannot: heading **wrap
count**, cards **clipped or bleeding at the pane edge**, column count, band
spacing, sticky chrome, overlays that float outside the band box.

The pair READS fan out through `wave.py --phase compare` — one read-only
worker per band on the probe's adapter rung (`orca` supervised terminals of
the same agent, this harness's `subagent`, or `serial` specs). The controller
does not read the pairs itself on the orca/subagent rungs; it shoots, waits,
applies patches serially, re-shoots only patched bands, and reports. Same lane
as 2.3 VALIDATE LOOK (`references/orca-relay.md`): SHA snapshot, one finding
file per worker, stale findings rejected, only the controller writes
`rebuild/`.

## Summon

```
/compare                      every <section id> band, run-config widths
/compare pricing              one band (repeat ids for several)
/compare pricing --live       live source panes (sticky-nav parity; needs network)
/compare --widths 1600,390    subset of breakpoints
/compare about                phase 5: interior page — pairs the BUILT
                              astro/dist/about/index.html (--ship), pairs at
                              qa/side-by-side/about/
```

Flags pass through to the script: `--id <section>` (repeatable),
`--widths 1600,768,390`, `--height 1000`, `--source disk|live`,
`--source-url <url>`, `--page <slug>`, `--ship <rel-path>`,
`--fail-over <pct>`.

## Run

1. **Root.** The run folder is the cwd that contains `rebuild/index.html`.
   If several runs are open, ask which one. Never guess.
2. **Shoot once.**
   `python3 "$SKILLS/web2html/scripts/paper_23_side_by_side.py" . [--id …]`
   Default source is **disk**: a crop of the 1.2 `capture/home-*/fullpage.png`
   at the band's sidecar `bbox.y` — the captured, 1.4-signed source, offline.
   `--live` re-shoots the live URL instead (index-paired top-level sections).
   No Playwright → the script writes `qa/side-by-side/skip.json` and says so;
   fall back to reading the 1.2 clip side-by-sides
   (`qa/paper-measure/compare/NN-slug-<width>-side.png`).
3. **Wave the reads — do NOT read the pairs yourself.** One round:

   ```sh
   W=$SKILLS/web2html/scripts/wave.py
   python3 $W prepare . --phase compare --run-id c1   # one task per band in the report
   python3 $W start   . --phase compare --run-id c1   # orca: worker-start per band
   python3 $W wait    . --phase compare --run-id c1   # ONE check --wait
   python3 $W ready   . --phase compare --run-id c1
   python3 $W apply   . --phase compare --run-id c1   # prints patch + re-shoot per band
   ```

   Adapter from the probe (`qa/harness-probe.json`): `orca` opens supervised
   terminals of the **same agent**, `subagent` prints specs for this harness's
   subagent tool, `serial` means you do each printed spec yourself — always
   through the same finding files. When the probe says `waves orca`, load
   `orchestration` + `orca-cli` (stubs; `orca skills get …`) before `start`.
   Each worker reads only its band's pairs and writes one finding: verdict per
   width (`match|miss`), `seen` (≥12 words), misses, a patch proposal
   scoped to `#<band>`, and a **mandatory `nav` list** — one row per
   hidden-until-interaction nav affordance the band's chrome shows
   (dropdown / megamenu / drawer / submenu), each `wired|missing|unwired`.
   A `missing`/`unwired` row forces a `miss` verdict and a patch proposal —
   `wave.py check` rejects a finding without it (Pitfall #247).
   `miss` is only for a glance-level difference (wrap
   count, column count, missing element, pane-edge bleed, wrong radius class,
   >8px gap drift, sticky chrome over the band, a nav affordance the source
   paints that the rebuild lacks); everything else is `match`.
4. **Apply serially.** Only the controller writes `rebuild/`. Apply each
   printed `patch` under the current phase's write rules (table below), one
   band at a time, selectors scoped to that band (`#pricing …`). No global
   token restyle, no unrelated band, no Paper MCP, no re-capture.
5. **Re-shoot ONLY patched bands** — `paper_23_side_by_side.py . --id <band>`
   per patched band, not the whole page — then **one** confirm wave over those
   bands with a NEW `--run-id` (`c2`). Read the confirm findings and check the
   named difference is gone. **Hard cap 2 rounds per band**: a difference that
   survives the confirm wave is a **residual** — report it and stop. Never
   prepare a third wave for the same band.
6. **Report.** Band, widths, what differed, what you patched, final state
   (match / residual). In a 2.3 session also fold the finding into the normal
   measure receipt + wave; `/compare` never bypasses `section_22_gate.py`.

### Loop-stoppers (ORCA > OPENCODE especially)

- **Shoot once per round.** The pairs are on disk. A worker re-shooting or
  re-reading a pair it already saw is a loop — the spec's BUDGET caps reads.
- **`wait` is ONE `check --wait`.** An empty result is a checkpoint, not a
  failure — re-run `wait` once, then `ready`; never poll in a tight loop.
  Exit 4 means a worker asked: `orca orchestration reply --id <id> --body …`,
  then `wait … --ack <delivery>`.
- **Worker `check` exit 3 (STALE) = stop.** The controller changed `rebuild/`
  after the snapshot — the worker reports `failed` and exits; never re-read,
  never rewrite, never relaunch.
- **`worker-start` non-zero → never relaunch.** The remaining tasks drop a
  rung (`wave.py start` already does this); continue on the lower rung.
- **diffPct never triggers a pass.** It only ranks where workers look; a 0.4%
  diff can be a wrong radius and a 30% diff can be font hinting + image crop.
- **A prepared wave that was never started is dead.** After ANY `rebuild/`
  write its findings would be stale — do not resume it; prepare a NEW
  `--run-id` on the fresh shoot.
- **Two rounds per band, then residual.** A third wave on the same band is a
  loop — report the residual and stop.

## Phase write rules — how the fix lands

| Where you are | How the patch lands |
|---|---|
| **2.2 / 2.3** | Controller patches `rebuild/index.html` in place (the one homepage file). Measure/APPLY serial; the 2.3 gate re-runs and now also demands a **fresh** `qa/side-by-side/report.json` (ship fingerprint unchanged since the pairs were shot) — so re-shoot the pairs after the last patch. Inside an active 2.3 loop prefer the step's own `wave.py --phase 2.3`; `/compare` is for a targeted re-look. |
| **3.1–3.3** | Polish edits `rebuild/index.html` in place. After the patch, `fidelity_freeze.py verify` and `verify-polish-passes.py` must stay green — a visual fix must not drift type / library-class / section-id. |
| **3.4 (before done)** | Same as 3.x. If the review tab is open, refresh it (`open-human-review.py`) after the patch so the human sees the fixed ship. |
| **After 3.4 done / tidied** | `capture/` may be gone: disk mode falls back to the numbered 1.2 clips, then to `--live`. Patch `rebuild/index.html` in place and re-shoot the pairs; note the fix in `run-report.md`. |
| **Phase 4** | Pairs validate the homepage ship only. Interior pages use their own `--page <slug>` (ship at `rebuild/<slug>.html`, clips under `capture/<slug>-*/`). |
| **Phase 5 (5.4+ interior pass)** | The ship is the BUILT page `astro/dist/{slug}/index.html` — pass `--ship`. Pairs land at `qa/side-by-side/{slug}/`. Chrome fixes land ONCE in `astro/src/components/Header.astro` / `Footer.astro` (controller only); page-local fixes in `astro/src/pages/{slug}.astro`. Never touch `rebuild/`. After every patch: `build-astro-dist.py`, then re-shoot. See the interior pass below. |

## 5.4+ interior pass — /compare on the built pages (Pitfall #247)

Runs after 5.4, before 5.5. Stage 5 QA'd interiors with static `<main>` clips
only — a closed dropdown and a MISSING dropdown look identical there, so
subnavs, megamenus, and burger drawers vanished on interior runs while the
homepage's 3.2 pass caught them. This pass is the stage-5 equivalent of the
3.2 hidden-item hunt, over every built page.

1. **Build first.** `build-astro-dist.py .` — the ship is
   `astro/dist/{slug}/index.html`, never the `.astro` source.
2. **Shoot per page** (once per round):

   ```sh
   python3 "$SKILLS/web2html/scripts/paper_23_side_by_side.py" . \
     --page {slug} --ship astro/dist/{slug}/index.html [--widths 1600,768,390]
   # → qa/side-by-side/{slug}/report.json + pairs + contact sheet
   ```

   Gold is `capture/{slug}-desktop|768|390/` (4.2 + 5.4 clips). Homepage pairs
   stay at `qa/side-by-side/` — the per-slug folder never clobbers them.
3. **Wave with `--page`** — same lane, same loop-stoppers, one round:

   ```sh
   python3 $W prepare . --phase compare --run-id c1 --page {slug}
   python3 $W start   . --phase compare --run-id c1 --page {slug}
   python3 $W wait    . --phase compare --run-id c1 --page {slug}
   python3 $W ready   . --phase compare --run-id c1 --page {slug}
   python3 $W apply   . --phase compare --run-id c1 --page {slug}
   ```

   Every worker spec carries the **NAV block**: on any band whose pair shows
   the navbar, the worker must inventory hidden-until-interaction items —
   dropdown menus, mega/super-nav panels, burger drawers, submenu links — and
   report each as `wired|missing|unwired` in the finding's `nav` list. A
   closed panel and a missing panel look the same in a static pair, so the
   worker checks the TRIGGER: chevron/caret, `aria-haspopup`, or a nav label
   the source paints with children. A `missing`/`unwired` row forces a `miss`
   verdict + patch; `check` rejects the finding otherwise.
4. **Wire what's missing.** A broken `nav` row is fixed per
   `references/nav-dropdown.md` (desktop: hover/click only **opens**; touch:
   click toggles; ≤768px: the burger drawer owns navigation — Pitfall #241).
   The fix lands in the shared component (`Header.astro`) when the trigger is
   chrome, in the page body when it is page-local, plus
   `astro/public/styles|scripts/` for the panel css/js. Never invent a nav
   label the source never painted.
5. **Rebuild + confirm.** `build-astro-dist.py .`, re-shoot ONLY patched bands
   (`--page {slug} --ship … --id <band>`), one confirm wave with a NEW
   `--run-id`. Hard cap 2 rounds per band, then residual.
6. **Machine audit — the pass is not done until this is green:**

   ```sh
   python3 "$SKILLS/web2html/scripts/phase_5_nav_audit.py" .   # qa/phase-5-nav.json
   ```

   It inventories every hidden nav item per page (hover-reel
   `dropdown`/`nav-mobile-*` manifests, scrape submenus, painted triggers in
   the raw dumps — home's inventory applies to every page, the Header is
   shared) and checks each against the BUILT page. `ok:true` only when every
   item is `wired`. **`wire-astro-routes.py` (5.5) refuses to run without a
   fresh ok receipt** — a stale or missing `qa/phase-5-nav.json` blocks route
   wiring. Capture-Tool-style "do not hunt" skips fail, exactly like Pitfall
   #210.
7. **The loop must actually run (Pitfall #248).** `mark 5.4 done` and the 5.5
   gate check, per slug, that the report has side-by-sides and that an
   APPLIED compare wave covers every band. Fill empty dropdown panels with
   `author-nav-dropdown.py --astro .` (reads Framer `Mega Menu` layers too)
   before the audit.

## Hard rules

- **No Paper MCP.** The source of truth here is pixels on disk, not the board.
- **Never invent a breakpoint.** 1600 / 768 / 390 (or the run-config subset).
  No 1024, no 1320, no 1440.
- **The pair is the evidence.** Do not claim a fix landed without a confirm
  wave over the re-shot pair at every width you changed.
- **diffPct never gates.** It ranks where to look; a 0.4% diff can be a wrong
  radius and a 6% diff can be font hinting.
- **Workers stay read-only.** Children Read the pair PNGs and return findings;
  only the controller writes `rebuild/`.
