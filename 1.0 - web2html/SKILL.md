---
name: web2html
description: "Convert a live URL to pixel-perfect static HTML via Paper. Invoke as /web2html or Convert <URL> to HTML. First tool: pipeline-progress.py start for a NEW run, resume for a continued session. Never write rebuild HTML before 2.1. Never scrape-to-site, Firecrawl-to-HTML, Tailwind CDN, or freehand a homepage. If rebuild/index.html exists without a live board and 1.4 sign-off, quarantine it and start from 1.1. 2.1 emits the Design System page from 1.3 tokens; 2.2 authors rebuild/index-semantic.html from Paper using those tokens. A run spans three sessions (1 capture / 2 build / 3 QA) plus optional Phase 4 (Paper) and Phase 5 (Astro site: shared chrome pulled once from the 3.4 polish, then each page's body); 2.0 and optional 5.0 are recommended on the strong model; the tier is advice, never a gate — run any session on whichever model the operator chose. Homepage only until 3.4. file:// preview. No GIFs, no local server."
version: 2.23.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [website, rebuild, static, html, css, js, paper, semantic, astro]
    related_skills:
      - frontend-design
      - hover-reel
      - url-to-paper
      - design-tokens
      - design-taste-frontend
      - impeccable
      - emil-design-eng
      - find-animation-opportunities
      - apple-design
      - pixel-perfect
      - orchestration
      - orca-cli
---

> `$SKILLS` — the directory your agent loads skill packages from.
> Set it once: `export SKILLS=~/.claude/skills` (or wherever you keep them).
> Compat alias: `$SKILLS/website-to-html` is this same package.

# web2html: any site → Paper → semantic HTML

**This file is the index (~200 lines). Do not page it. Do not say it is huge.
Do not read it twice.** Detail lives in `references/` and is loaded **per
step** — see the table below. `read_file` that one file, then act.

## Summon — first tool, before anything else

**Invoke:** `/web2html`  
**Trigger:** `Convert <URL> to HTML`

```sh
# NEW run — writes AND opens <project>/pipeline.html (once)
python3 $SKILLS/web2html/scripts/pipeline-progress.py start /path/to/templates/<project>
# continued session 2 or 3 — never start, it resets the board
# resume does not reopen the board; the start tab stays open
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --at 2.1 --owner session-2
```

Both print a **probe** line (`harness_probe.py <project> --brief`): the harness, whether
Orca is reachable, the same-source agent id, and the rungs `waves orca|subagent|serial` /
`relay orca-terminal|print-prompt`. `orca reachable` → read `references/orca-relay.md`
once and load `orchestration` + `orca-cli` (stubs; `orca skills get …`) before the
first Orca verb. At **2.3**, `wave.py` is required on every rung — Orca terminals
when `waves orca`, this harness's subagent tool when `subagent`, the printed specs
when `serial`. Anything else → never load `orchestration` / `orca-cli`; still run
`wave.py` at 2.3 (Pitfall #219 #220 #221).

`start` is the only command that opens the live board. If **that** tab does
not open, **stop**. Print the `file://` URI. `resume` / `mark` / later
sessions never reopen it. Then read
`references/live-board.md` once (todos, mark, never-reuse). Derive `<project>`
from the URL slug under `Documents/templates/<project>`. Never overwrite the
spec `web2html/pipeline.html`.

**Writing `rebuild/*.html` now is a failed run.** Gate:

```sh
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project>
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project> --allow design-system  # 2.1
python3 $SKILLS/web2html/scripts/rebuild_write_gate.py /path/to/templates/<project> --allow index           # 2.2+
```

Red means stop. Do not polish a quarantined file (Pitfall #148).

## Hard rules

1. Never skip a numbered step (1.1 → 3.4). `skip` fails on required steps. Capture Tool is optional leftover hover at 1.4 (tab opened by `mark 1.4 active`; `open-capture` re-opens). Phase 4 is optional after 3.4 (`qa/phase-4-opted.json` or `qa/phase-4-skipped.json`). Phase 5 is optional after 4.4 (`qa/phase-5-opted.json` or `qa/phase-5-skipped.json`).
2. No `rebuild/*.html` until 1.4 is signed and 2.1 is open. First rebuild HTML is 2.1 `design-system.html` (token contract). First authored write is 2.2 `index-semantic.html` — never scrape-to-site, never a get_jsx dump. 2.3 seeds `index.html` from that file.
3. Homepage only through 3.4. Extra routes stay out of 1.2. Phase 4 is Paper-only. Phase 5 binds the site into `astro/` after 4.4 opt-in: 5.1 pulls Header / Footer / components **once** from the 3.4 polish, 5.2 authors only each page's `<main>` as `astro/src/pages/{slug}.astro`. 5.5 is the one post-3.4 href exception, plus 3.3-style scrape-only SEO per page. Exit if `plan.pages.length > 1` at 1.2 without `--allow-multi-page`.
4. Stage L is never skippable. No ship HTML until Paper has a `Design Library` artboard (foundations only), `get_tokens` is non-empty, and `design-library/library.json` exists. Disk-only does not count.
5. One `rebuild/`. 2.2 first pass is `index-semantic.html`. 2.4 lock is `index.html`; 3.x writes `index-polish.html` only (created when 3.1 starts, not at 2.4). Optional Phase 5 writes `astro/` and does not replace `rebuild/`. No local HTTP server. Preview is `file://` — in **Orca's browser** when the probe says `orca reachable` (`open_doc.py`: the board, 2.4 review, 3.4 compare + polish report, 5.6 routes), else Chrome; `WEB2HTML_BROWSER=default|orca` overrides. 5.3+ relativizes `astro/dist` so built pages open on `file://`. The agent verifies with `astro build`, never `astro dev`; the human may run `npm run preview`.
6. Human stops: **1.4**, **2.4**, **3.4**, optional **4.4**, optional **5.6**. Session 2 does not yield until **2.4**. **3.4** is finish vs Phase 4. **4.4** is finish vs Phase 5. **5.6** is finish (tidy). CTA only at those yields (Pitfall #190 #192). A **relay** (`pipeline-progress.py relay`, when `mark` prints `RELAY armed`) is a change of agent at a receipt boundary, not a yield: same-source agent, Orca terminal when reachable, else print the prompt; never a CTA (Pitfall #218 #219 #220).
7. Silent shell 20s → kill (Pitfall #112). Gate evidence must be truthful.
8. **1.2 always `create_file` a new Paper document.** Never `list_files` / never open a similarly-named existing file (Pitfall #187).

Versioned rows: `references/pillars.md`. Findings: `references/pitfalls.md`.
Spine: `references/stage-spine.md`. Gates / folders: `references/gates.md`.

## Pipeline

```
HOMEPAGE · required · / only
SESSION 1 · operator   1.1 → 1.2 → 1.3 → 1.4  → handoff-2.0.md
SESSION 2 · strong     2.1 → 2.2 → 2.3 → 2.4  → handoff-3.0.md
SESSION 3 · operator   3.1 → 3.2 → 3.3 → 3.4

ALL PAGES · optional
SESSION 4 · operator   4.1 → 4.2 → 4.3 → 4.4
SESSION 5 · strong     5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6
```

2.0 and optional 5.0 are recommended on the strong tier. The tier is advice, never a
gate: run any session on whichever model the operator chose, and never stop to ask for a
switch. `mark --step 1.4/2.4 --status done` releases the lease and prints the next prompt. 4.4 opted in prints `qa/handoff-5.0.md`.
Resume with `resume`, never `start`.

**Homepage vs all pages.** Phases **1–3** are the required homepage run (`/` only):
capture at 1600 / 768 / 390, mine one Design Library, author `rebuild/index-semantic.html`,
seed `index.html` at 2.3, polish `index-polish.html` starting at 3.1. **3.4 can stop the run.** Phases **4–5** are optional
all-pages work that reuse those tokens and chrome. They do not recapture `/`,
do not mine a second library, and do not rewrite 2.3 geometry.

- **4.x Paper:** extra sitemap URLs into the same file, desktop only, bind existing tokens.
- **5.x Astro site:** scaffold `astro/` and pull Header / Footer / components once from the 3.4 polish, author each Paper page's `<main>` as `src/pages/{slug}.astro`, clip-QA the built pages (desktop, then live 768/390 — no extra Paper frames), wire routes + SEO, `astro build`. Never replaces `rebuild/`.

## Before each step — read that row, not this file

| Step | Do | Read |
|---|---|---|
| **1.1** | `scrape-web.sh` — URL + images + Latin fonts. Stub contract. | `references/step-11.md` |
| **1.2** | Headless `hover-reel/scripts/capture-session.mjs` — **always `create_file` a new Paper document**. Never `list_files` / never open a similarly-named existing file. Then 1600/768/390 + Navigation + stretch-root. | `references/12-desktop-source.md` + `references/stage-p-notes.md` |
| **1.3** | `run-design-library-step.mjs` once. Foundations only. Then pull unique buttons + components from token-seeded `home-desktop` onto FRAME `Buttons` and FRAME `Components`, and author button hover from source CSS. | `references/pillars.md` (1.3 rows) + `references/13-buttons-components.md` |
| **1.4** | Required Paper sign-off. `mark 1.4 active` opens Paper **and** the browser on the stamped source URL (Capture Tool connects off that tab; `capture-doctor` FAIL = OFFLINE, relay its fix). Optional leftover hover only. Fire the two-option question modal. Stop. | `references/live-board.md` + pillars 1.4 row |
| **2.1** | `emit-design-system.mjs` writes `rebuild/design-system.html` + `tokens.css` + `fonts.css`. Not the ship. | `references/paper-design-to-code.md` |
| **2.2** | `get_jsx` → `dump_index_raw.py` → `rebuild/index-raw.html`. `frontend-design` authors `rebuild/index-semantic.html`. | same |
| **2.3** | Pull numbered 1.2 `NN-slug.png` clips at 1600/768/390, side-by-side vs rebuild. Measure/APPLY is serial (controller is the only `rebuild/` writer). **No Paper MCP.** Never skip. Then VALIDATE: `paper_23_validate.py . --shoot-open`, **MUST** `wave.py prepare/start/wait/apply` for LOOK, apply printed patches, `--record` from the findings; ≤3 rounds per band, then `--residual`. Adapter from the probe: `orca` opens Orca terminals, `subagent` dispatches this harness's subagents, `serial` means the controller does each printed spec. Do not Read the sides yourself on the orca/subagent rungs (Pitfall #216 #221). | same + `references/responsive-22d.md` + `references/section-23-paper-loop.md` + `references/orca-relay.md` |
| **2.4** | `open-build-review.py . --stage 2.4` (TAGS on). Stop. Continue starts Session 3 polish. `index-polish.html` does not exist yet. | same |
| **3.1** | `mark --step 3.1 --status active` copies `index.html` → `index-polish.html` (unpolished). Then Impeccable + Taste on that copy. Freeze the lock. | `references/polish-visual-restore.md` |
| **3.2** | Hover from 1.3 source CSS (`apply-hover-css.py`) + **painted burger drawer** (`author-nav-drawer.py`) + **FAQ accordion** (`author-faq.py`) + **nav dropdowns** (`author-nav-dropdown.py`) + guidelines a11y + **mandatory GSAP in-view** on `index-polish.html`. Never skip hover, the drawer, FAQ, or dropdowns because Capture Tool did not run. Companion receipts `qa/web-design-guidelines.md` / `qa/find-animation-opportunities.md` / `qa/apple-design.md` before `mark --step 3.2 --status done` (Pitfall #215). | `references/gsap-inview.md` + `references/hover-22c.md` + `references/nav-drawer.md` + `references/faq.md` + `references/nav-dropdown.md` + `references/orca-relay.md` (companion wave) |
| **3.3** | Semantics + scrape-only SEO on `index-polish.html` (`--freeze-structure`). | `references/semantics-pass.md` |
| **3.4** | Compare `index.html` vs `index-polish.html`. Two-option: finish (`qa/phase-4-skipped.json`, tidy) or continue to Phase 4 (`qa/phase-4-opted.json`, no tidy). | `references/live-board.md` (handoff) |
| **4.1** | Scrape sitemap.xml for extra URLs. Homepage stays out. Near-duplicate dynamic detail slugs (blog posts, case studies — a parent with 3+ children) collapse to ONE sample per template; never import every slug. | `references/scripts.md` |
| **4.2** | Desktop capture each URL onto the HOME canvas of the 1.2 file — one horizontal row under a single `Ruler · pages` below the existing frames. NEVER `create_page` / a Paper page per URL. | same |
| **4.3** | Serial bind of existing Design Library tokens. No second library. | same |
| **4.4** | Human review of the extra Paper pages. Two-option: finish (`qa/phase-5-skipped.json`, tidy) or continue to Phase 5 (`qa/phase-5-opted.json`, no tidy). | `references/live-board.md` |
| **5.1** | `scaffold-astro.py` → `extract-astro-components.py` → `convert-astro-home.py`. Scaffold `astro/` from the 3.4 rebuild CSS / fonts / images / scripts, pull Header + Footer + Paper-backed / comment-nominated components **once** from `index-polish.html`, convert the homepage to `src/pages/index.astro`. | `references/phase-5-astro.md` |
| **5.2** | Serial `get_jsx` dumps + at most two author workers, each writing **only** the `<main>` of `astro/src/pages/{slug}.astro` on the 5.1 chrome. `record-phase-5-pages.py`. | same + `references/orca-relay.md` (page wave) |
| **5.3** | `build-astro-dist.py`, then desktop clip compare of `astro/dist/{slug}/index.html` vs `capture/{slug}-desktop/source-sections/` (1600). | `references/section-23-paper-loop.md` + same |
| **5.4** | Live 768/390 clips, rebuild, then the same compare on `astro/dist`. No extra Paper frames. | same |
| **5.5** | `wire-astro-routes.py`: sitemap paths / labels → routes, per-page scrape-only SEO into frontmatter, `astro build`. Geometry, type, and library classes stay frozen. | `references/phase-5-astro.md` + `references/semantics-pass.md` |
| **5.6** | `open-phase-5-review.py` — review built routes on `file://`, then tidy. Keeps `rebuild/` + `astro/`. | `references/live-board.md` |

Commands and edge cases: `workflow.html`. Public lander is human copy only.

**Do not** `skill_view` this package again mid-run. **Do not** load
`url-to-paper` / `hover-reel` SKILL.md unless you are stuck — their scripts
are enough; the refs above carry the pipeline rules.

## Companion skills (by step)

| When | Skill |
|---|---|
| 2.1 | `url-to-paper` `emit-design-system.mjs` |
| 2.2 / 5.2 | `frontend-design` |
| 2.3 / 5.3 | `pixel-perfect` (one-pass assist; disk-clip gold). Not a refine loop. Not 3.x. |
| **2.3 VALIDATE LOOK** | **MUST** `wave.py` after `--shoot-open`. When the probe says `waves orca`, load `orchestration` + `orca-cli` (stubs; `orca skills get …`) before `wave.py start` (Pitfall #221). |
| 1.2 scripts | `url-to-paper` (scripts only) |
| 1.3 pull | `hover-reel` `pull-desktop-specimens.mjs` then `author-button-hover.mjs` |
| 1.4 optional extension | `hover-reel` Capture Tool |
| 1.2 session + 5.4 | `hover-reel` (scripts / extension) |
| 1.3 tokens | `design-tokens` (folder ≠ 2.1 Author) |
| 3.1 | `impeccable`, `design-taste-frontend` |
| 3.2 | `emil-design-eng`, `find-animation-opportunities`, `apple-design` |
| any step, only when the probe says `orca reachable` | `orchestration` + `orca-cli` (stubs; guide via `orca skills get …`) — 2.3 wave terminals + relay, same-source agent (Pitfall #219 #220 #221) |

Script index: `references/scripts.md`.

## What this skill does not do

No React, no Tailwind CDN, no JSX, no CMS, no analytics, no
local server, no GIFs, no second `rebuild-*` tree, no invented skip-link,
no extra Paper frames that only serve a join. No bundler until optional
Phase 5, which writes `astro/` only.

Deliverable: plain semantic HTML/CSS/JS in `rebuild/` plus a reusable CSS
token system. Optional Phase 5 adds a static Astro app in `astro/` — chrome pulled once, one `.astro` body per page.
