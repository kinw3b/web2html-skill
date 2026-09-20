# Stable capture contract

Never label a screenshot from the requested scroll target alone. Capture is valid only after two consecutive observations agree and identity is verified in the same observation used for the shot.

## Procedure

1. Navigate or scroll the target into view.
2. Wait until animations in the target subtree are not `running`.
3. Observe: `scrollY`, target bounding box (`top`, `left`, `width`, `height`), `imagesComplete`, and an identity signal (`id`, `data-framer-name`, or `textSample`).
4. Observe again after a short delay (≈250ms).
5. Proceed only when both observations match on scroll + box and images report complete.
6. Capture a tightly bounded screenshot.
7. Optionally re-observe immediately after capture; discard if geometry shifted.
8. Label the artifact only after steps 5–6 succeed. Record `verified` on the manifest entry.

## Rules

- Full-page captures that repeat, freeze, smear, or shift content are discarded; use viewport or element clips instead.
- A nearby viewport size is not evidence for a target viewport — match sizes exactly.
- Scripts: `scrape-web.sh` Phase 3 and `section-diff-loop.py` implement this contract and write `verified` + `stable_capture: true` into manifests.

## Freeze interventions (mandatory when stability fails)

If any of the following **blocks two matching observations**, freeze or disable it
**the same way on reference and implementation**, then document the intervention:

| Blocker | Typical intervention |
|---|---|
| Sticky / fixed header covering the crop | Scroll offset, temporary `position: static`, or clip below header |
| Looping animation / marquee | `animation: none`, pause via JS, or wait for a known frame |
| Lazy-load / blur-up images | Force load, scroll-walk pre-pass, disable lazy |
| Scroll-snap fighting scroll-into-view | Temporary `scroll-snap-type: none` |
| Carousel autoplay | Pause / go to fixed index before capture |
| Video / Lottie background | Pause or poster frame |

Document every intervention in **`qa/capture-interventions.md`**:

```markdown
| id | target | blocker | intervention | applies-to |
|---|---|---|---|---|
| CI-1 | reviews | autoplay carousel | force index 0, autoplay off | reference + build |
```

Also note the intervention on the affected region in `qa/region-manifest.json` `notes[]`.
Never freeze only the build (or only the reference) — comparisons become invalid.
