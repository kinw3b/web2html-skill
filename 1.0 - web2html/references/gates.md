# Fidelity gates, folder contract, documentation contract

Split out of `AGENTS.md`. Read before a gate check or a skill fix.

## Documentation contract (MANDATORY on every skill fix)

You edit the skill package. Update a **doc surface only when that surface's
role changed**. Do not restamp files that still match. There is no wiki.

| File | Role | Touch when |
|---|---|---|
| `AGENTS.md` or `web2html/references/*.md` | Agent rules | A version, gate, or hard rule changed |
| `pipeline.html` | Run order | Step IDs, cards, or order changed |
| `workflow.html` | Commands, gates, edge cases | A command or gate copy changed |
| `index.html` | Public lander one-liners | A public step label or overview sentence changed |

`README.md` (repo root and `1.0 - web2html/README.md`) is a pointer at those
four. It carries no versions, stage numbers, skill lists, or pipeline rules.
**Never edit it for a skill fix.**

### Agent checklist after a skill fix

```text
[ ] Edited the skill package in this checkout (SKILL.md and/or scripts)
[ ] Updated AGENTS.md or the matching web2html/references/*.md if agent rules changed
[ ] Updated pipeline.html if the run order changed
[ ] Updated workflow.html if commands / gates / edge cases changed
[ ] Updated index.html if public lander copy changed
[ ] ./scripts/sync-from-agents.sh
[ ] ./scripts/test-all.sh   (every suite + check-skill-artifacts; same as `npm test`)
[ ] git commit + push origin main
```

Skipping a surface **that actually changed** is a **process failure** — that is
how map drift happens. Touching a surface that did not change is also a failure.

## Folder contract (projects)

```
capture/   design-library/   source-site/   rebuild/   astro/   qa/
```

| Folder | From | Role |
|---|---|---|
| `capture/` | Stage **P** (`url-to-paper`) | Per-section serialized DOM **+** `fullpage.png` (required). `pre-pesticide.json` (live DOM contract, before capture). `fullpage-paper.jpg` only if opting into a Paper sibling |
| `design-library/` | Stage **L** (not P alone) | Paper Design Library mirror: `library.json`, optional `exports-inline/` |
| `source-site/` | Step **0** | Sitemap + assets + fonts |
| `source-site/components/` | A/6 Steps **4.0-4.4** (`hover-reel`, after all Stage P pages) | `<page>/<kind>/` (`nav/ buttons/ forms/ faq/ footer/ dropdown/ nav-mobile-768/ nav-mobile-390/`) — state HTML + `manifest.json` → Paper artboards + C/3 hover parity; `capture-run.json` records the page matrix. Dropdowns and burgers land on `Interactive components`, not A/6. |
| `rebuild/` | Steps **2a–9** | **Ship** — only after Stage L passes. `index-semantic.html` is the 2.2 first pass; `index.html` is the 2.4 lock until 3.4 done, then the promoted polish (outlines off). `index-polish.html` is 3.x QA and is archived at 3.4 done (`rebuild/archive/`). Do not write `NEXT.html` |
| `astro/` | Optional **5.x** | Static Astro app: Header / Footer / components pulled once from the signed homepage, one `.astro` body per Paper page, `dist/` built and `file://`-relativized. Does not replace `rebuild/`. |
| `qa/` | Gates | Contracts, export log, diffs, ledgers, `b2b-r-evidence.md`, `runs/<run-id>/STOP-*.md`, `component-state-coverage.json`, `component-paper-qa.json`. `agent-findings/` and `agent-runs/` are noncanonical reviewer evidence/leases only; **deleted when 3.4 is marked done** (lean handoff). After that sweep the project root keeps `rebuild/` plus the finished `pipeline.html`, `run-report.md` (the portable run log — sessions, durations, agent + model, checkpoint notes, captured Paper comments), and `astro/` when Phase 5 ran. |

`first-pass/` appears only on the Stage H fallback, when no URL is reachable.

Do **not** use `site/` or `v1/` as ship paths. Tokens land in **`rebuild/css/tokens.css`**.

## Fidelity gates

| # | Gate | Where |
|---|---|---|
| 1 | Stable two-observation capture | scrape / section-diff |
| 2 | Provenance actuals | section-audit.mjs |
| 3 | Fidelity contract | Stage F → `qa/fidelity-contract.md` |
| 4 | Interaction parity | Stage 5c → `qa/interaction-results.md` |
| 5 | Regression IDs | `qa/regressions.json` |
| 6 | Anti-normalization | tokens + CSS |
| 7 | Retired — `client-first-spacing` package is retired. Spacing uses theme tokens (`var(--spacing-*)`, closest Tailwind class) from 1.3 / `design-tokens`. |
| 8 | Live stage tracker | todos enter/exit/pulse |
| 9 | Browser | `file://` always. Pipeline documents (board, 2.4 review, 3.4 compare + polish report, 5.6 routes) open in **Orca's embedded browser** when the session runs inside a reachable Orca (`open_doc.py` → `orca tab create`), else Chrome / the default opener; `WEB2HTML_BROWSER=default\|orca`. Capture Tool stays in a Chromium with the extension; Paper stays in its app. HTTP **user-opt-in** only (Pesticide); never Pencil |
| 10 | URL capture baseline | Stage P → Paper page artboards + `capture/` |
| **10b** | **Design Library in Paper** | **Stage L HARD STOP** — blocks all of 2a/2b/3 (Pitfall #17) |
| **10c** | **Full-page PNG on disk** | Stage P — `capture/<page>/fullpage.png` required. Paper `{page} — source screenshot` artboard is **opt-in** (Pitfall #19). `qa-paper` does not use JPEG pixels |
| **10d** | **Paper source-shot geometry** | Opt-in only — if a sibling is requested, pin explicit px width/height; never `height:auto` |
| **1.2 / A/5-R** | **Automatic geometry postflight (runs inside 1.2)** | After the 1600 / 768 / 390 landers land, `hover-reel/scripts/capture-session.mjs` runs `run-geometry-postflight.mjs`, which calls `stretch-root.mjs --prove --artboard home-desktop` only — not `qa-paper` or `merge-split-headings`. Failure keeps 1.2 open. Optional Capture Tool does not open until this postflight is green. Evidence: `qa/stretch-root-evidence.md`. |
| **A/4-I** | **Local Paper images** | Capture still downloads binaries. **Never** put `paper-asset://` in `write_html` — it hangs Paper (Pitfall #68). Repair inserts use live remote asset URLs. Pitfall #24 remains the localize/download step. |
| **A/4-T** | **Paper display type** | `General Sans Semibold` (and other weight-in-name faces Paper cannot load) remap to Satoshi 700 before `write_html` (Pitfall #25). system-ui Regular headlines fail |
| **2.1** | **Design System** | Emit `rebuild/design-system.html` + `css/tokens.css` from signed 1.3 `library.json`. Chrome uses `var(--color-*)`. Script, not the model. Not the ship. `design_system_21_gate.py` green. |
| **2.2** | **Author semantic responsive page** | Two files: `rebuild/index-raw.html` (`dump_index_raw.py` HTML + tokens, not JSON) + `rebuild/index-semantic.html` (frontend-design). No dump metadata on the first pass. Do not write `index.html` here. `author_21_gate.py` green. Pitfall #199 #206. |
| **2.3** | **Validate each section vs Paper** | **Never skip.** Seed `index.html` from `index-semantic.html`. Pull numbered 1.2 `NN-slug.png` clips at 1600 / 768 / 390 (`paper_23_clip_compare.py`) and compare them to rebuild shots + `index-raw.html`. Measure/APPLY serial. No Paper MCP. Then VALIDATE: `--shoot-open` + **MUST** `wave.py` LOOK + `--record` from findings, ≤3 rounds per band. `clip-compare.json` + `disk-gold.json` + `raw-census.json` + every `<id>.validate.json` (last round match or capped residual, ship unchanged since that round was shot) + applied `qa/agent-runs/<run>/2.3/wave.json` + `section_22_gate.py` green. Pitfall #185 #195 #198 #201 #202 #216 #221. |
| **2.4** | **Sign-off → 3.0 polish** | QA overlay pesticide outlines ON by default in TAGS mode. Overlay default is TAGS, not off and not a hidden query. Human receipt. Continue starts Session 3 polish. `index-polish.html` is created when 3.1 starts, not at 2.4. |
| **20a** | **Reviewer-wave provenance** | The controller holds the only mutation lease and snapshots inputs by SHA. Named reviewers may write schema-validated reports under `qa/agent-findings/`; `sync` and gates ignore them. Any controller change makes prior reports stale. Canonical receipts and final gates remain controller-only; 3.4/finish reject active reviewer leases. |
| 11 | Mandatory polish C/3.1–3.3 | Receipts + `qa/polish-report.html` + `rebuild/index-polish.html`; `verify-polish-passes.py`; `verify-gsap-reveal.py`; `apply-hover-css.py`; `author-nav-drawer.py`; `author-faq.py`; `author-nav-dropdown.py`; `fidelity_freeze.py verify`; companion receipts `qa/web-design-guidelines.md` / `qa/find-animation-opportunities.md` / `qa/apple-design.md`; a11y/SEO/contrast/anti-slop + mandatory GSAP (Pitfall #196 #203 #204 #207 #208 #209 #210 #215) |
| 12–15 | Region / asset / states / freezes | `qa/*` manifests |
| 16 | Hover parity | 1.3 `qa/button-hover.json` → 3.2 `apply-hover-css.py` → `rebuild/css/hover.css`. Leftover Capture Tool manifests may refine the same `library.json` names. `changed` is a **content** comparison, never a byte-length one |
| 17 | Rotated icons | Paper rotates about the **top-left** and pins `transform-origin: 0% 0%` — unsettable via `write_html` *or* `update_styles`, both of which report success and change nothing. `trim-styles.mjs` shifts by `c − R(θ)·c` via the `translate` longhand. Captures are **Paper-targeted**: re-rendered in a browser the glyph shifts |
| **17** | **No freehand 2.2** | First `index-semantic.html` is frontend-design from Paper + 2.1 tokens — Pitfall #15 #109 #206 |
| **17b** | **No pipeline bypass** | Live board exists. 1.1–1.4 done before `rebuild/index-semantic.html`. Tailwind CDN / React / get_jsx dump fails. `rebuild_write_gate.py` green. `start` quarantines leftover ship HTML. `mark` cannot jump to Build. Pitfall #148. 2.1 may write `design-system.html`. |
| **18** | **Dump is not the ship** | A get_jsx dump is `rebuild/index-raw.html` only. It is not `index-semantic.html` or `index.html`. 2.3 measures against it + the 1.2 source clips. Pitfall #198 |
| **19** | **Stage P anti-freeze** | No `--keep-open` in multi-page loops; no `\| tail`/`head` on capture; bounded settle — Pitfall #18 |
| **19b** | **Component coverage** | `validate-component-captures.mjs` — every **expected** page/kind manifest exists, no target pool is truncated, roots have px geometry, hovers are confirmed, `changed: false` states are retained as parity evidence, and FAQ opens have measured growth. `--expected-pages home` ignores leftover first-run folders |
| **20** | **Step 7 two passes** | Pass 1 find+fix; pass 2 re-capture + re-verify vs source screenshots — stopping after one pass fails |
