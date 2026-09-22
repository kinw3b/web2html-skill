# Model routing — three sessions, two handoffs

**Orchestrator version (web2html):** **2.25.0**

A run spans three homepage sessions so the model can change per phase, plus optional all-pages Phase 4 (Paper) and Phase 5 (Astro site — chrome once, then page bodies).

**The tier is advice, never a gate.** Nothing in the tooling reads or checks the
model: `resume` has no `--model` / `--tier` flag, and the handoff prompt only
*names* the recommended tier. Any model may run any session. A session that
finds itself on a different tier than the one recommended proceeds — it never
stops to ask for a switch. The routing below says where a cheaper model's
mistakes are caught by a script versus by the human checkpoint; it is a cost
recommendation for the operator, not a rule for the model.

```text
HOMEPAGE (required, `/` only)
SESSION 1 · 1.1 → 1.4   capture      operator tier
   └── 1.4 done ──► emits qa/handoff-2.0.md
SESSION 2 · 2.1 → 2.4   build        STRONG tier
   └── 2.4 done ──► emits qa/handoff-3.0.md
SESSION 3 · 3.1 → 3.4   QA / polish  operator tier
   └── 3.4 can STOP, or opt into all-pages 4.0

ALL PAGES (optional; reuse homepage tokens + chrome)
SESSION 4 · 4.1 → 4.4   extra Paper  operator tier (optional after 3.4)
   └── 4.4 opted ──► emits qa/handoff-5.0.md
SESSION 5 · 5.1 → 5.6   Astro site   STRONG tier (optional after 4.4)
   └── 5.6 done ──► tidy (keeps rebuild/ + astro/ + pipeline.html)
```

## The rule

Route on one question: **does the step end in a gate that inspects a real
artifact, or in a receipt the model wrote about its own work?**

| | |
|---|---|
| **Machine-checked** → cheap tier is safe | `token-geometry-guard.mjs` diffs pre/post geometry. `stretch-root.mjs --prove` proves the stretch. `library-seed-qa.json` fails colour-spill with no retry. `verify-rebuild-trees.py` catches a raster nav. `verify-semantics.py` reads the real markup. A weaker model that gets it wrong **fails red and loops** — the cost of a bad attempt is one more attempt. |
| **Self-certified** → strong tier recommended | `author_21_gate.py` rejects `get_jsx` metadata, block content in `<p>`, an invented skip-link, and source/external `<a href>`. Every check is *contamination*, never fidelity. `section_22_gate.py` confirms `qa/section-align-22.json` lists the three widths, every row reads `"aligned"`, **and** `qa/paper-measure/_index.json` has a `measured: true` + `diskCompared` receipt per section — **it never opens an image**. The model still has to run the disk-gold loop (`references/section-23-paper-loop.md`); the gate only grades that the receipts exist. |

**2.0 and optional 5.0 are the phases recommended on the strong tier.**
2.0 authors HTML no earlier artifact contains; 5.0 authors each interior's `<main>` as an
Astro body on chrome pulled once from the 3.4 polish. Before 2.0, everything is machine-verified
capture. After it, the homepage has passed the 2.4 human checkpoint, so a weaker
polish pass costs craft, not fidelity — and 3.4 puts a human in front of it.
Phase 5 repeats that authoring job for interiors — body only, the chrome is already signed.

`verify-polish-passes.py` at 3.1–3.2 also only checks that receipts exist, so
those two steps are technically self-certified as well. They stay on the operator
tier anyway. Bounded by the 2.4 fidelity freeze and the session 3 prompt: if a
fix would change layout, type size, library class names, section order, or the
colour system, stop and hand back.

## Tiers

| Tier | Role | What it does | Claude |
|---|---|---|---|
| **T1** | Author | Long-horizon work over heavy visual context where the output is a fidelity or taste judgment no script can re-check. | Opus 5 |
| **T2** | Operator | Bounded judgment with a real mechanical check on the other side: token binds, hover parity, semantics, comment remediation, monitored script runs. | Sonnet 5 |
| **T3** | Runner | Stamp the board, run the command, read the exit code, hold at the human stop. Almost no judgment — but strict rule-following, so keep the step's rules in context. | Haiku 4.5 |

Keep the tier abstract in `SKILL.md`; a tier name survives running this across
Claude, Codex, Cursor and Grok, a model id does not.

## Per-step

| Step | Gate | Tier |
|---|---|---|
| 1.1 light scrape (URL + images + Latin fonts) | machine — `scrape-web.sh` | T2 |
| 1.2 capture 1600/768/390 + Navigation | machine — `stretch-root --prove`, `breakpoint-shot-qa.mjs`, census | T3 |
| 1.3 Design Library + tokens + Buttons/Components pull + source-CSS hover | machine — library + seed QA + `qa/buttons-components-pull.json` + `qa/button-hover.json` | T2 |
| 1.4 Human Paper checkpoint | human — walk Paper, `qa/paper-human-review.md`; `mark 1.4 active` opens Paper + the stamped Capture Tool tab (`open-capture` re-opens, `capture-doctor` checks the bridge) | T2 |
| 2.1 Design System | machine — `emit-design-system.mjs` + `design_system_21_gate.py` | T2 *(inside the session)* |
| **2.2 author the page** | **self** — `author_21_gate.py` is contamination-only | **T1** |
| **2.3 section loop** | **self** — `section_22_gate.py` reads the receipts only (measure + VALIDATE rounds + applied 2.3 wave), never an image; LOOK is `wave.py` (workers Read the side PNGs; the controller shoots, applies, records) | **T1** |
| 2.4 TAGS checkpoint | human — `build-checkpoint-opened.json` + receipt | T1 *(inside the session)* |
| 3.1 QA pass 1 | self — `verify-polish-passes.py` checks receipts exist | T2 |
| 3.2 QA pass 2 | machine — `inject-gsap-reveal.py` + `verify-gsap-reveal.py` + receipts | T2 |
| 3.3 semantics + SEO | machine — `verify-semantics.py` | T2 |
| 3.4 handoff | human — compare 2.4 index vs index-polish, no active lease | T3 |
| 4.1–4.3 extra Paper pages | machine — sitemap / capture / token-seed receipts | T2 |
| 4.4 Paper review | human — `phase-4-review.md` + Phase 5 opted/skipped | T3 |
| 5.1 scaffold Astro + shared chrome | machine — `phase-5-scaffold.json` + `phase-5-components.json` + `phase-5-home.json` | T2 |
| **5.2 author interior bodies** | **self** — `record-phase-5-pages.py` is contamination-only | **T1** |
| **5.3 / 5.4 clip loops on astro/dist** | **self** — receipts exist; the model still has to compare | **T1** |
| 5.5 wire routes + SEO + build | machine — `phase-5-links.json` + `astro build` | T2 |
| 5.6 Astro review | human — `phase-5-review.md` then tidy | T1 *(inside the session)* |

## Handoff mechanics

A model recommendation that depends on remembering it will eventually be
forgotten, and a session 2 that silently ran on the cheap tier looks exactly like
one that did not. So the boundary produces the artifact: the handoff prompt names
the recommended tier where the operator will read it. Whether to follow it is the
operator's call — the model that receives the prompt runs the session regardless.

`pipeline-progress.py` is the chokepoint every step boundary already crosses, so
both prompts live there:

- `mark --step 1.4 --status done` → writes and prints `qa/handoff-2.0.md`
- `mark --step 2.4 --status done` → writes and prints `qa/handoff-3.0.md`
- `mark --step 4.4 --status done` with `qa/phase-5-opted.json` → writes and prints `qa/handoff-5.0.md`
- `relay <project> --owner <held>` (mid-session, context budget armed) → writes and prints `qa/handoff-<step>.relayN.md`, releases the lease, and on a reachable Orca opens a terminal for the **same agent** that is running the predecessor (Pitfall #220). It never passes `--model`: the tier stays advice on every rung. Recipe `references/orca-relay.md`.

Each fires only after the human has approved that checkpoint — exactly when the
visuals are corrected and signed. Each also **releases the controller lease**, so
the next session can claim it. The prompt is printed to stdout inside a delimited
block (selectable in the terminal you are already in) and written to the file.

The prompt carries the project root, source URL, Paper file id, board URI, what
is already signed off, the exact first commands, and the fidelity lock.

## `start` vs `resume`

**`start` is for a new run only.** It force-writes empty progress
(`save_progress(..., force=True)`) and quarantines ship HTML. A session 2 that
runs it wipes 1.1–1.4 back to pending and throws the run away (Pitfall #179).

A continued session resumes:

```sh
python3 "$SKILLS/web2html/scripts/pipeline-progress.py" resume . --at 2.1 --owner session-2
```

`resume` loads existing progress and fails if there is none; refuses if the
target step's predecessors are unfinished; claims the controller lease under the
new owner; rewrites the board HTML. It never resets, never quarantines, and
**never reopens** `pipeline.html` — that tab was opened at `start`. Pitfall #191.

The lease matters: `mark` refuses to stamp when an active controller lease has a
different owner. If a session died mid-flight without releasing, clear it with
`release-controller --owner <held> --expected-revision <n>` — never by editing
`qa/pipeline-progress.json` (Pitfall #180).

## Attribution

`agent_findings_schema.json` sets `additionalProperties: true` at both the root
and the finding level, so `"tier"` and `"model"` land with zero schema change.
The controller lease owner in `qa/pipeline-progress.json` already records which
session did the work. Without attribution you cannot tell a routing regression
from an ordinary bad run.

## Reviewer lane

`agent_loop.py` implements the safe shape for pushing verbose reading down a
tier: hashed immutable snapshot, reviewers that write only to
`qa/agent-findings/`, controller owns Paper, `rebuild/`, progress and every
canonical receipt. Reviewers are read-only, so a cheap model there cannot corrupt
anything — the worst case is a suggestion the controller declines.

That matters more than the token saving. The steps you *cannot* downgrade (2.2
and 2.3) are also the ones carrying the screenshot load. The real prize is the
one `lean-run.md` names: a run that "exhausted its context before Steps 8–10."
Every verbose read a cheap agent absorbs is context the T1 controller still has
when it reaches 2.1.
