# Live board, todos, never-reuse

Read **once at summon**. Then mark as you walk. Do not reload `SKILL.md`.

## First action

New run:

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py start /path/to/templates/<project>
```

Continued session 2 or 3 — **never `start`** (it resets the board, Pitfall #179):

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --at 2.1 --owner session-2
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --owner session-2   # --at detected from the board
```

Without `--at`, `resume` detects where the run sits (the active step, else
the first pending one), prints `detected <step>`, logs this session under
`sessions[]`, and prints the run total so far. This is how every fresh
terminal finds its place and keeps the step clocks honest — do it before any
work, then `mark --status active` (Pitfall #227 #228).

**Right after `start`, run the intake** (2.26.0). `start` prints the questions.
Question 1 is one choice: `Live URL — author from Paper` or `Webflow / HTML source`.
If they choose the folder, the next question is `Paste the absolute path to the HTML folder.`
The answer is that path, typed in the text field. Then full or fast.
Record with `run_config.py intake <project> --source none|/abs/path --speed full|fast`.
A clean HTML folder is copied to `source-html/` and that copy is the ship:
do not create `rebuild/`, Phase 2 is marked off, Phase 3 is accessibility
attributes only, and Phase 4 is required through 4.4 (do not ask at 3.4).
`mark 1.1 active` refuses without `qa/run-config.json`.

`start` writes **and opens** `<project>/pipeline.html` **once**. `resume`,
`mark`, and later sessions never reopen it — assume that tab is still open.
If **start** does not open the board, **stop**. Print the `file://` URI. Never overwrite the spec
`web2html/pipeline.html`. Never pass the web2html repo as `start` root.
Derive `<project>` from the URL slug under `Documents/templates/<project>`.

The open board refreshes every 15 seconds. As soon as 1.2 writes
`qa/paper-file.json`, the Capture Tool row stores the stamped URL. **Copy**
and **Open** stay hidden until that URL exists and step **1.4** is active.
They hide again once 1.4 is no longer the current step. The link, if opened,
is a new tab.

Stamp every boundary:

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.2 --status active
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.2 --status done
```

`mark` cannot open 2.1+ while 1.1–1.4 are unfinished. `skip` fails.

## Timing (2.27.0)

Every step is timed by its own marks, and the run total is the **sum of step
durations** — never wall clock. A pause between sessions or terminals adds
nothing.

- `mark --status active` stamps `started` and prints `1.2 started 01:41:05`.
- `mark --status done` stamps `ended` + `durationSeconds` and prints
  `1.2 finished 26 Sep 01:44   took 2m 57s` followed by the run total line
  (`run total … agent … · human … N steps timed   last finished …`). Human
  checkpoints (1.4 / 2.4 / 3.4 / 4.4 / 5.6) count in `human`, everything else in `agent`.
- A step marked done **without** a prior `mark active` still lands in the total:
  `started` is inferred from the tightest lower bound (previous step's end, this
  session's claim, run start) and flagged `startedInferred` — the board shows a
  `*` and the mark prints `start inferred — mark active next time`. Do not rely
  on it; mark active when you enter a step.
- `skipped` is not work: no inference, no duration.
- `start` and `resume` append `{kind, owner, at, startedAt}` to `sessions[]`.
- The board stamps finished / took on every grid row and timeline item, the
  phase sum on each card head, and `total … · agent …` in the HUD.
- `python3 $SKILLS/web2html/scripts/pipeline-progress.py timing <project> [--json]`
  prints the per-step table, per-phase sums, the total, and the session log.
  Put that total in the 3.4 / 4.4 / 5.6 hand-back so the human sees the cost.

Rule for every new agent session: `resume` first (it prints where the run
sits and the total so far), then `mark active` before touching the step. A
`mark` is the only thing that adds time. Pitfall #227 #228.

## Agent + model (2.28.0)

Each session records who ran it, so every step can be attributed to an agent and
a model. The run spans three sessions and the model may change at each phase;
the board makes that visible instead of guessing.

- `resume` / `start` take `--agent` and `--model`:
  `resume . --owner session-2 --model claude-fable-5.1`. `--agent` defaults to
  the harness probe (`opencode` / `claude-code` / `codex` …). `--model` falls
  back to `WEB2HTML_MODEL`. Neither flag is a gate — they only record.
- `mark --status active` stamps the step with the recording session's agent and
  model (`--agent` / `--model` override per mark). `mark --status done` only
  fills a blank, so it never overwrites the agent that actually ran the step.
- The HUD names the current session after the total (`… · AGENT 2H 16M | OPENCODE · GPT-5.9`).
- Each phase card carries a status line: `56m 56s · opencode · deepseek-v4.1-flash`.
  When a phase mixed agents it lists each one with the time it accounts for:
  `1h 51m · claude-code · claude-fable-5.1 (1h 44m) + opencode · deepseek-v4.1-flash (6m 20s)`.
  A phase with no timed work yet shows nothing.
- `timing` prints an `agent` column per step, the agent on each phase line, and
  each session's agent/model. Pitfall #229.

## Capture Tool block (2.28.0)

The panel above the spine never prints the stamped address — a long
`?paperFileId=…&projectRoot=…` query made the board noisy.

- **Copy** copies the stamped address; the label flips to `Copied`.
- **Open** opens it in a new window (`window.open`).
- Both buttons stay hidden, and a `Waiting for Paper` line shows, until
  `qa/paper-file.json` yields a URL **and** step 1.4 is active. Then the line
  reads `Optional way to capture dropdowns, buttons or components back to paper.design.`
  Once 1.4 is done or skipped, the buttons hide again. The sentence can stay.
- The address itself lives on a hidden `<a data-pipeline-capture-url>`, which is
  what both buttons read. Pitfall #229.

## Todos

One todo per child. IDs **are** the board IDs. Prefer `TodoWrite`.

| Parent | Child | Name |
|---|---|---|
| 1.0 | 1.1 | Light scrape (URL + images + Latin fonts) |
| 1.0 | 1.2 | Homepage, breakpoints + geometry postflight |
| 1.0 | 1.3 | Mine once + create Design Library + Buttons/Components + source-CSS hover |
| 1.0 | 1.4 | Human checkpoint |
| 2.0 | 2.1 | Design System |
| 2.0 | 2.2 | Author semantic responsive page |
| 2.0 | 2.3 | Validate each section vs Paper |
| 2.0 | 2.4 | Sign-off → 3.0 polish |
| 3.0 | 3.1 | QA pass 1 — a11y + contrast + anti-slop |
| 3.0 | 3.2 | QA pass 2 — 1.3 source-CSS hover + painted burger drawer + FAQ accordion + nav dropdowns + mandatory GSAP in-view + guidelines a11y |
| 3.0 | 3.3 | Semantics + SEO sweep (freeze-structure) |
| 3.0 | 3.4 | Human checkpoint |
| 4.0 | 4.1 | Sitemap (optional) |
| 4.0 | 4.2 | Capture pages (optional) |
| 4.0 | 4.3 | Seed tokens (optional) |
| 4.0 | 4.4 | Human review (optional) |
| 5.0 | 5.1 | Scaffold Astro (optional) |
| 5.0 | 5.2 | Author pages (optional) |
| 5.0 | 5.3 | Desktop QA (optional) |
| 5.0 | 5.4 | Responsive (optional) |
| 5.0 | 5.5 | Wire routes + SEO (optional) |
| 5.0 | 5.6 | Human checkpoint (optional) |

Exactly one foreground child `in_progress`. Enter → `mark --status active` +
todo. Exit → `done` then next `in_progress`. Banner:

```
▶ 1.2 — Breakpoints · Paper + geometry   [1.1✓ ▶1.2 1.3 1.4 | 2.0 | 2.4]
NEXT  3.1  QA pass 1                     [after 2.4 done — Session 3 polish not started]
```

Idle (no active step, run not finished) is **NEXT** on the progress bar, never Ready. After 2.4
done the bar reads `NEXT  3.1`. There is no Here/Next strip.

Human stops: **1.4**, **2.4**, **3.4**, optional **4.4**, and optional **5.6**. Everything else runs.

## Session yield

Each session returns to the human at **exactly one** checkpoint. Do not
stop, ask, or fire a Continue CTA anywhere else.

| Session | Runs without yielding | Yields at |
|---|---|---|
| 1 · capture | 1.1 → 1.2 → 1.3 → 1.4 | **1.4** (auto-accepted when `checkpoints=auto`) |
| 2 · build | 2.1 → 2.2 → 2.3 → 2.4 | **2.4** (auto-accepted when `checkpoints=auto`) |
| 3 · QA | 3.1 → 3.2 → 3.3 → 3.4 | **3.4** — human stop on a URL run. A Webflow / HTML folder run does not stop here |
| 4 · pages | 4.1 → 4.2 → 4.3 → 4.4 | **4.4** — optional after a URL run's 3.4. Required on a Webflow / HTML folder run |
| 5 · astro site (optional) | 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 | **5.6** |

**Session 2:** do not stop after emitting 2.1, after authoring 2.2, or
mid-2.3. Sign every homepage section at 1600 / 768 / 390 in this session
(disk clips; VALIDATE LOOK is `wave.py`; no Paper MCP). The only stop is
2.4 (TAGS Chrome + Continue). Pitfall #192 #195.

## Human stop CTA (any harness)

Do **not** ask for a paragraph. Fire one native blocking choice / CTA /
question tool if this session has one (Hermes `clarify`, Claude Code
`AskUserQuestion`, Cursor `AskQuestion`, Codex approval cards). Do **not**
invent a tool this harness does not expose. If it does not: print the
same labels and wait. Timeout or a dismissed card → stay stopped. Human
checkpoints are not "use best judgement." Pitfall #190.

### 1.4 — two-option question modal

Session 1 yields **once**. After `mark --step 1.4 --status active` (Paper
open, browser open on the stamped source URL, `qa/paper-human-review.md`
written), fire **one** question. If the mark printed `capture doctor: FAIL`,
relay the printed fix command in the question text.

**Instructions in the question (required — not extra choices):**

- Walk 1600 / 768 / 390, FRAME `Navigation`, FRAME `Buttons`, FRAME
  `Components`, and the Design Library. Pin comments on anything wrong.
  2.0 will not start until those threads are handled.
- Capture Tool is optional leftover live hover. The stamped tab is already
  open; `pipeline-progress.py open-capture` re-opens it. Do not treat it as
  required.

**Choices, in this order, with these labels:**

1. `Done & continue to next step`
3. `Provide hand-off prompt to start fresh session`

Typed equivalents: `Continue` / the first label → choice 1. `handoff` /
the second label → choice 3.

| Choice | Agent does |
|---|---|
| **1 · Done & continue to next step** | `mark --step 1.4 --status done` and continue into 2.1 **in this session**. The mark still writes `qa/handoff-2.0.md`. |
| **3 · Provide hand-off prompt** | Do not start 2.1. If `qa/paper-human-review.md` exists, `mark --step 1.4 --status done` (that prints the prompt). If not, `pipeline-progress.py handoff` (draft) and stay stopped. |

### 2.4 — Continue to 3.0 polish

Last action is a blocking **Continue to 3.0 polish (3.1–3.4)**. The resume
token is still the word `Continue` in every harness. Do not mark the step
done until Continue (or a clear equivalent). Polish has not run. Do not
create `index-polish.html` here — 3.1 copies the lock when it goes active.

The live board after 2.4 done must read **NEXT 3.1** (Session 3 polish —
not started), never a vague Ready, and must not show a polish file that
has not been worked.

### 3.4 — URL run: two-option. Folder run: do not ask

**Webflow / HTML folder** (`clean-html` adopt): do not fire a question. Ship stays
`source-html/index.html`. `mark --step 3.4 --status done` writes
`qa/phase-4-opted.json`. Continue at 4.1 in this session. The next human stop
is 4.4. `qa/phase-4-skipped.json` fails. Pitfall #225.

**URL run**, after the polish compare, fire **one** question:

1. `Done — finish homepage run` → write `qa/phase-4-skipped.json`, `mark --step 3.4 --status done` (promotes polish to `index.html`, archives the other homepage HTML, tidy).
2. `Continue to optional Phase 4` → write `qa/phase-4-opted.json`, `mark --step 3.4 --status done` (same promote, no tidy), then `mark --step 4.1 --status active`.

### 4.4 — two-option (Paper finish vs optional Phase 5)

Walk the extra Paper pages, pin comments, write `qa/phase-4-review.md`. Then fire **one** question:

1. `Done — finish Paper run` → write `qa/phase-5-skipped.json`, `mark --step 4.4 --status done` (tidy).
2. `Continue to optional Phase 5` → write `qa/phase-5-opted.json`, `mark --step 4.4 --status done` (no tidy, prints `qa/handoff-5.0.md`), then `mark --step 5.1 --status active`.

### 5.6 — single Continue

`open-phase-5-review.py` writes `qa/phase-5-review.md` and opens the built home + first interior from `astro/dist` on `file://`. Walk every route (shared chrome = 3.4 polish; bodies = Paper). Then **Continue** and `mark --step 5.6 --status done` (tidy). Keeps `rebuild/` + `astro/` + `pipeline.html`.

Stops:

| Stop | When the CTA fires | Choice does |
|---|---|---|
| **1.4** after Paper open | `qa/paper-human-review.md` written, Paper open | see the two 1.4 choices above |
| **2.4** after TAGS Chrome | `qa/build-checkpoint-opened.json` | `mark --step 2.4 --status done` |
| **3.4** after 2.4 lock + QA polish + report | `open-human-review.py` opened Chrome on both HTML files | `mark --step 3.4 --status done` |
| **4.4** after extra Paper pages | `qa/phase-4-review.md` written, Paper open | see the two 4.4 choices above |
| **5.6** after the built Astro routes open | `qa/phase-5-review.md` | `mark --step 5.6 --status done` |

## Never reuse another project

Every run builds from **this** project's capture. Forbidden: `cp`/`rsync` of
another `rebuild/`, `tokens.css`, `capture/`, `design-library/`, Paper file,
`source-site/assets/`, or stale `qa/`. Skills (this package) are reusable;
project evidence is not. Paper files are not reusable either — 1.2 always
`create_file` once (Pitfall #187). A retry of the same run reopens `qa/paper-file.json` and does not create a second document (Pitfall #224).

Before 1.1 writes: `pwd`, `ls`, `ls ..` — similarly-named siblings are the trap.

## Do not ask

Once you have a URL, run. Do not ask to capture extra pages, skip the library,
skip QA, or pick a browser. Chrome. Homepage only. Stage L is work, not a prompt.

Folder contract: `references/gates.md`.
