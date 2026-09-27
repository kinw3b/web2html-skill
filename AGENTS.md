# Skills source of truth

This repo is **website-to-html**: any live site → Paper → semantic HTML.
Install with `node scripts/npx-install.js` (what `npx github:kinw3b/web2html-skill`
runs), which **symlinks** each package into every agent's skills directory and
installs the skills' npm dependencies. From a checkout it links the checkout;
never `cp`: a copy goes stale the moment you edit. The Capture Tool extension
and its native bridge are NOT installed — they are a separate download
(https://github.com/kinw3b/paper-bridge); `INSTALL_CAPTURE_HOST=1
./scripts/install-skills.sh` opts in. `pipeline-progress.py capture-doctor`
reports a bridge that would show OFFLINE (Pitfall #217).

**Orchestrator version (web2html):** **2.33.0**

**This file is the repo index.** The agent-facing run rules live in
`1.0 - web2html/SKILL.md` (summon, intake, hard rules, per-step table) and the
versioned per-step detail lives in `1.0 - web2html/references/*.md`, read **per
step**, not on every turn. A run loads `SKILL.md` and the one reference for the
step being worked — none of that is duplicated here. This file covers what
working **in this repo** requires: the doc surfaces, the sync/publish flow,
and the edit contracts.

| Need | Read |
|---|---|
| Agent summon + per-step load table | `1.0 - web2html/SKILL.md` (do not page; do not say it is huge) |
| Run rules — hard rules, pipeline, sessions, stops | `1.0 - web2html/SKILL.md` + `web2html/references/pillars.md` |
| Step detail (1.1 … 5.6) | the `references/*.md` row wired to that step in `1.0 - web2html/pipeline.json` |
| Findings from real runs | `web2html/references/pitfalls.md` |
| Fidelity gates, folder contract, documentation contract | `web2html/references/gates.md` |
| Install paths, repo layout, package conventions, glossary | `web2html/references/repo-conventions.md` |
| Script catalog | `web2html/references/scripts.md` |
| Run order (human surface) | `pipeline.html` |
| Commands, gates, edge cases | `workflow.html` |
| Branching skill encyclopedia | `index.html` |
| Single source of truth (steps, tiers, refs, version) | `1.0 - web2html/pipeline.json` |

**Before editing a step's rules, read that step's accordion on `pipeline.html`
and its rows in `pillars.md`.** Do not act on memory of a rule — the numbers move.

## Pipeline shape (orientation only)

```
1 capture (1.1–1.4) → 2 build (2.1–2.4) → 3 QA (3.1–3.4)
  → optional 4 pages (4.1–4.4) → optional 5 astro site (5.1–5.6)
```

Sessions 2 and 5 are recommended on the strong tier; 1, 3, and 4 on the
operator tier. The tier is advice, never a gate. Human checkpoints: **1.4**,
**2.4**, **3.4** (URL run), **4.4** (folder run / opted-in), **5.6**. The
binding rules, gates, hard stops, and receipts for every step live in
`1.0 - web2html/SKILL.md` and `web2html/references/pillars.md` — when they
disagree with something you remember, the files win.

## Documentation contract (MANDATORY on every skill fix)

You edit the skill package. Update a **doc surface only when that surface's
role changed**. Do not restamp files that still match.

| File | Role | Touch when |
|---|---|---|
| `web2html/pipeline.json` | Single source of truth (step ids, tiers, references, orchestrator version) | A step, tier, reference wiring, or the orchestrator version changed — `web2html/scripts/lint-docs.py` fails any surface that drifts from it |
| `AGENTS.md` or `web2html/references/*.md` | Agent rules | A version, gate, or hard rule changed |
| `pipeline.html` | Run order | Step IDs, cards, or order changed |
| `workflow.html` | Commands, gates, edge cases | A command or gate copy changed |
| `index.html` | Public lander one-liners | A public step label or overview sentence changed |

`README.md` (repo root and `1.0 - web2html/README.md`) is a pointer at those
four. It carries no versions, stage numbers, skill lists, or pipeline rules.
**Never edit it for a skill fix.**

```text
[ ] Edited the skill package in this checkout (SKILL.md and/or scripts)
[ ] Updated web2html/pipeline.json if a step, tier, reference, or version changed
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

## Installed names are never numbered

Folders here carry a stage prefix (`1.2 url-to-paper`) so the pipeline order is
visible when browsing. **That prefix exists only here.** The installed directory
name *is* the skill identifier; a space or digit breaks discovery and every
symlink. `scripts/install-skills.sh` strips it.

## Sync

```bash
./scripts/sync-from-agents.sh      # agents → this repo
./scripts/check-skill-artifacts.sh # claimed scripts must exist
./scripts/test-all.sh              # all three suites + artifact check (also `npm test`)
git config core.hooksPath .githooks # once per clone: test-all runs before every push
```
